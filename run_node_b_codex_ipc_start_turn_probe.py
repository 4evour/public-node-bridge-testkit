#!/usr/bin/env python3
"""macOS Codex Desktop IPC start-turn probe for Node-B.

This sends one tiny prompt to an already observed Codex Desktop conversation
through the local Unix socket. It does not use the input box, click, paste,
press keys, execute files, or send anything outside Codex Desktop.

Success requires two gates:
1. thread-follower-start-turn returns without an IPC error.
2. The local Codex rollout file later contains the expected assistant marker
   and a task_complete record for the same marker.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import socket
import struct
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


MAX_FRAME_BYTES = 256 * 1024 * 1024
SESSIONS_DIR = Path.home() / ".codex" / "sessions"


def cannot_claim() -> list[str]:
    return [
        "formal_ack",
        "external_send",
        "file_execution",
        "persistent_service",
        "long_running_autonomy",
        "production_ready_connection",
        "input_box_automation",
        "frontstage_auto_injection",
    ]


def default_socket_path() -> str:
    return os.path.join(tempfile.gettempdir(), "codex-ipc", f"ipc-{os.getuid()}.sock")


def socket_candidates() -> list[str]:
    paths = [default_socket_path()]
    paths.extend(glob.glob("/var/folders/**/codex-ipc/ipc-*.sock", recursive=True))
    seen: set[str] = set()
    out: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        if os.path.exists(path):
            out.append(path)
    return out


def write_frame(sock: socket.socket, message: dict[str, Any]) -> int:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    frame = struct.pack("<I", len(payload)) + payload
    sock.sendall(frame)
    return len(frame)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("socket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(sock: socket.socket, timeout: float) -> dict[str, Any]:
    sock.settimeout(timeout)
    header = recv_exact(sock, 4)
    (length,) = struct.unpack("<I", header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"Invalid frame length: {length}")
    payload = recv_exact(sock, length)
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("IPC frame JSON was not an object")
    return data


def respond_discovery_false(sock: socket.socket, frame: dict[str, Any]) -> bool:
    if frame.get("type") != "client-discovery-request":
        return False
    write_frame(sock, {
        "type": "client-discovery-response",
        "requestId": frame.get("requestId"),
        "response": {"canHandle": False},
    })
    return True


def read_response_for(
    sock: socket.socket,
    request_id: str,
    timeout: float,
    progress: bool = False,
) -> tuple[dict[str, Any], int, list[dict[str, Any]]]:
    deadline = time.monotonic() + timeout
    discovery_replies = 0
    side_frames: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        try:
            frame = read_frame(sock, max(0.1, deadline - time.monotonic()))
        except socket.timeout:
            continue
        if progress:
            marker = frame.get("type") or "?"
            method = frame.get("method")
            print(f"[{marker}{':' + str(method) if method else ''}]", end="", flush=True)
        if respond_discovery_false(sock, frame):
            discovery_replies += 1
            continue
        if frame.get("type") == "response" and frame.get("requestId") == request_id:
            return frame, discovery_replies, side_frames
        side_frames.append(frame)
    raise TimeoutError(f"Timed out waiting for response {request_id}")


def iter_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(iter_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(iter_strings(item))
    return found


def scrub_start_response(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    turn_id = None
    if isinstance(result, dict):
        nested = result.get("result")
        if isinstance(nested, dict):
            turn = nested.get("turn")
            if isinstance(turn, dict):
                turn_id = turn.get("id")
        turn = result.get("turn")
        if isinstance(turn, dict):
            turn_id = turn_id or turn.get("id")
    return {
        "type": response.get("type"),
        "requestId": response.get("requestId"),
        "resultType": response.get("resultType"),
        "method": response.get("method"),
        "error": response.get("error"),
        "turn_id": turn_id,
    }


def extract_runtime_status(frame: dict[str, Any], conversation_id: str) -> dict[str, Any] | None:
    if frame.get("type") != "broadcast" or frame.get("method") != "thread-stream-state-changed":
        return None
    params = frame.get("params")
    if not isinstance(params, dict) or params.get("conversationId") != conversation_id:
        return None
    change = params.get("change")
    if not isinstance(change, dict) or change.get("type") != "snapshot":
        return None
    conversation_state = change.get("conversationState")
    if not isinstance(conversation_state, dict):
        return None
    runtime_status = conversation_state.get("threadRuntimeStatus")
    turns = conversation_state.get("turns")
    if not isinstance(runtime_status, dict) or not isinstance(turns, list):
        return None
    last_turn = turns[-1] if turns and isinstance(turns[-1], dict) else {}
    active_flags = runtime_status.get("activeFlags") or []
    if not isinstance(active_flags, list):
        active_flags = []
    duration = last_turn.get("durationMs") or 0
    return {
        "runtime_type": str(runtime_status.get("type") or "?"),
        "active_flags": [str(flag) for flag in active_flags],
        "total_turns": len(turns),
        "last_turn_status": str(last_turn.get("status") or "?"),
        "last_turn_duration_ms": int(duration) if isinstance(duration, (int, float)) else 0,
        "last_turn_id": str(last_turn.get("turnId") or last_turn.get("id") or "?"),
    }


def is_busy_or_zombie(status: dict[str, Any] | None) -> tuple[bool, str]:
    if not status:
        return False, ""
    runtime_type = str(status.get("runtime_type") or "")
    last_turn_status = str(status.get("last_turn_status") or "")
    active_flags = status.get("active_flags") or []
    if runtime_type != "active":
        return False, ""
    if last_turn_status in {"inProgress", "interrupted"}:
        return True, f"runtime=active last_turn={last_turn_status}"
    if not active_flags and last_turn_status not in {"streaming", "completed"}:
        return True, "runtime=active with empty activeFlags"
    return False, ""


def find_rollout_path(conversation_id: str) -> Path | None:
    if not SESSIONS_DIR.exists():
        return None
    matches = sorted(
        SESSIONS_DIR.rglob(f"rollout-*{conversation_id}.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def payload_text(payload: dict[str, Any]) -> str:
    pieces: list[str] = []
    for key in ("message", "last_agent_message", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            pieces.append(value)
    content = payload.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                pieces.append(item["text"])
    pieces.extend(iter_strings(payload.get("record")))
    return "\n".join(pieces)


def poll_rollout_completion(
    conversation_id: str,
    rollout_path: Path | None,
    start_offset: int,
    marker: str,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "rollout_path": str(rollout_path) if rollout_path else None,
        "user_message_seen": False,
        "assistant_answer_seen": False,
        "expected_answer_seen": False,
        "task_complete_seen": False,
        "last_agent_message": None,
        "observed": False,
        "timeout_s": timeout,
    }
    deadline = time.monotonic() + timeout
    offset = max(0, start_offset)
    path = rollout_path
    while time.monotonic() < deadline:
        if path is None:
            path = find_rollout_path(conversation_id)
            if path is not None:
                state["rollout_path"] = str(path)
                offset = 0
        if path is None:
            time.sleep(poll_interval)
            continue
        try:
            size = path.stat().st_size
        except OSError as exc:
            state["status"] = f"rollout_stat_failed:{type(exc).__name__}"
            return state
        if size > offset:
            with path.open("rb") as handle:
                handle.seek(offset)
                chunk = handle.read(size - offset)
            offset = size
            for raw in chunk.splitlines():
                try:
                    item = json.loads(raw.decode("utf-8"))
                except Exception:
                    continue
                payload = item.get("payload") if isinstance(item, dict) else {}
                payload = payload if isinstance(payload, dict) else {}
                kind = str(payload.get("type") or item.get("type") or "")
                text = json.dumps(payload, ensure_ascii=False)
                direct_text = payload_text(payload)
                if marker in text:
                    if kind == "user_message" or '"role": "user"' in text:
                        state["user_message_seen"] = True
                    if kind == "agent_message" or '"role": "assistant"' in text:
                        state["assistant_answer_seen"] = True
                        state["last_agent_message"] = direct_text or text[:500]
                    if kind == "task_complete":
                        state["task_complete_seen"] = True
                        state["last_agent_message"] = str(payload.get("last_agent_message") or state["last_agent_message"] or "")
                if any(line.strip() == marker for line in direct_text.splitlines()):
                    state["expected_answer_seen"] = True
                if (
                    state["user_message_seen"]
                    and state["assistant_answer_seen"]
                    and state["expected_answer_seen"]
                    and state["task_complete_seen"]
                ):
                    state["observed"] = True
                    state["status"] = "completion_observed_in_rollout"
                    return state
        time.sleep(poll_interval)
    state["observed"] = (
        state["user_message_seen"]
        and state["assistant_answer_seen"]
        and state["expected_answer_seen"]
        and state["task_complete_seen"]
    )
    state["status"] = "completion_timeout"
    return state


def build_prompt(marker: str) -> str:
    return "\n".join([
        f"Reply exactly: {marker}",
        "",
        "Boundary: do not use tools, do not access network, do not write files, do not send externally, do not claim formal ACK.",
    ])


def conversation_id_from_latest_rollout() -> str:
    if not SESSIONS_DIR.exists():
        return ""
    matches = sorted(SESSIONS_DIR.rglob("rollout-*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in matches:
        match = re.search(r"rollout-([0-9a-f-]{36})\.jsonl$", path.name)
        if match:
            return match.group(1)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one tiny start-turn to macOS Codex Desktop IPC.")
    parser.add_argument("--socket", default="")
    parser.add_argument("--conversation-id", default="", help="Target Codex conversationId. Defaults to newest rollout id if omitted.")
    parser.add_argument("--marker", default="NODEB_IPC_OK_001")
    parser.add_argument("--cwd", default=os.getcwd(), help="Thread cwd. Use 'null' to send null.")
    parser.add_argument("--approval-policy", default="never")
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=10.0)
    parser.add_argument("--start-timeout", type=float, default=120.0)
    parser.add_argument("--completion-timeout", type=float, default=180.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--preflight-seconds", type=float, default=5.0)
    parser.add_argument("--no-preflight", action="store_true")
    parser.add_argument("--no-wait-completion", action="store_true")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    if platform.system().lower() != "darwin":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "error": "node_b_codex_ipc_start_turn_is_macos_only",
            "claim": "node_b_codex_ipc_start_turn_probe_not_run",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    conversation_id = args.conversation_id or conversation_id_from_latest_rollout()
    if not conversation_id:
        parser.error("--conversation-id is required when no rollout id can be discovered")
    socket_path = args.socket or (socket_candidates()[0] if socket_candidates() else default_socket_path())
    marker = args.marker.strip()
    prompt = build_prompt(marker)
    cwd = None if args.cwd.strip().lower() in {"", "none", "null"} else os.path.abspath(args.cwd)
    rollout_path = find_rollout_path(conversation_id)
    rollout_start_offset = rollout_path.stat().st_size if rollout_path and rollout_path.exists() else 0
    output: dict[str, Any] = {
        "ok": False,
        "platform": "macOS",
        "socket": socket_path,
        "socket_exists": os.path.exists(socket_path),
        "conversation_id": conversation_id,
        "cwd": cwd,
        "marker": marker,
        "rollout_path": str(rollout_path) if rollout_path else None,
        "rollout_start_offset": rollout_start_offset,
        "initialize_ok": False,
        "task_sent_to_codex": False,
        "codex_exact_reply_observed": False,
        "agent_message": None,
        "gates": {
            "target_thread_ok": bool(conversation_id),
            "start_turn_ok": False,
            "completion_observed": False,
            "refresh_after_ok": None,
        },
        "claim": "node_b_codex_ipc_start_turn_probe_incomplete",
        "cannot_claim": cannot_claim(),
    }
    if not output["socket_exists"]:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(args.open_timeout)
    discovery_replies = 0
    try:
        sock.connect(socket_path)
        init_id = f"init-{uuid.uuid4()}"
        write_frame(sock, {
            "type": "request",
            "requestId": init_id,
            "method": "initialize",
            "params": {"clientType": "yuanjie-node-b-start-turn-probe"},
        })
        init_response, replies, side_frames = read_response_for(sock, init_id, args.read_timeout, args.progress)
        discovery_replies += replies
        result = init_response.get("result")
        client_id = str(result.get("clientId") or "") if isinstance(result, dict) else ""
        output["initialize_ok"] = init_response.get("type") == "response" and init_response.get("error") is None and bool(client_id)
        output["client_id_present"] = bool(client_id)
        if not output["initialize_ok"]:
            raise RuntimeError("initialize_failed")

        runtime_status = None
        if not args.no_preflight:
            for frame in side_frames:
                runtime_status = extract_runtime_status(frame, conversation_id)
                if runtime_status is not None:
                    break
            deadline = time.monotonic() + args.preflight_seconds
            while runtime_status is None and time.monotonic() < deadline:
                try:
                    frame = read_frame(sock, max(0.1, min(1.0, deadline - time.monotonic())))
                except socket.timeout:
                    continue
                if respond_discovery_false(sock, frame):
                    discovery_replies += 1
                    continue
                side_frames.append(frame)
                runtime_status = extract_runtime_status(frame, conversation_id)
            busy, reason = is_busy_or_zombie(runtime_status)
            output["preflight_runtime_status"] = runtime_status
            output["preflight_busy_or_zombie"] = busy
            output["preflight_reason"] = reason
            if busy:
                output["error"] = "conversation_busy_or_zombie"
                output["suggestion"] = "Open or create an idle Codex Desktop conversation, then rerun with that conversation id."
                output["claim"] = "node_b_codex_ipc_start_turn_preflight_blocked"
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 1

        start_id = f"start-{uuid.uuid4()}"
        start_message = {
            "type": "request",
            "requestId": start_id,
            "sourceClientId": client_id,
            "method": "thread-follower-start-turn",
            "version": 1,
            "params": {
                "conversationId": conversation_id,
                "turnStartParams": {
                    "input": [{"type": "text", "text": prompt, "text_elements": []}],
                    "cwd": cwd,
                    "approvalPolicy": args.approval_policy,
                    "attachments": [],
                    "commentAttachments": [],
                    "serviceTier": None,
                },
            },
            "timeoutMs": int(args.start_timeout * 1000),
        }
        write_frame(sock, start_message)
        start_response, replies, more_side_frames = read_response_for(sock, start_id, args.read_timeout, args.progress)
        discovery_replies += replies
        side_frames.extend(more_side_frames)
        output["start_turn_response"] = scrub_start_response(start_response)
        task_sent = start_response.get("type") == "response" and start_response.get("error") is None
        output["task_sent_to_codex"] = task_sent
        output["gates"]["start_turn_ok"] = task_sent

        buffered_marker_seen = any(marker in iter_strings(frame) for frame in side_frames)
        output["diagnostics"] = {
            "buffered_frames_before_start_response": len(side_frames),
            "marker_seen_in_buffered_frames": buffered_marker_seen,
            "completion_timeout_seconds": args.completion_timeout,
            "client_discovery_replies_sent": discovery_replies,
        }
        if task_sent and not args.no_wait_completion:
            completion = poll_rollout_completion(
                conversation_id=conversation_id,
                rollout_path=rollout_path,
                start_offset=rollout_start_offset,
                marker=marker,
                timeout=args.completion_timeout,
                poll_interval=args.poll_interval,
            )
            output["completion_observation"] = completion
            output["codex_exact_reply_observed"] = bool(completion.get("observed"))
            output["agent_message"] = marker if completion.get("observed") else completion.get("last_agent_message")
            output["gates"]["completion_observed"] = bool(completion.get("observed"))
        elif task_sent:
            output["completion_observation"] = {"status": "skipped_by_no_wait_completion", "observed": False}

        output["ok"] = bool(output["task_sent_to_codex"] and output["codex_exact_reply_observed"])
        output["claim"] = (
            "node_b_codex_ipc_start_turn_exact_reply_passed"
            if output["ok"]
            else "node_b_codex_ipc_start_turn_probe_incomplete"
        )
    except Exception as exc:  # noqa: BLE001 - emitted as diagnostic JSON for remote testers.
        output["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        sock.close()

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
