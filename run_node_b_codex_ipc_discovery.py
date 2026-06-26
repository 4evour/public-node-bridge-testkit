#!/usr/bin/env python3
"""macOS Codex Desktop IPC discovery probe for Node-B.

This probe only initializes against the local Codex Desktop Unix socket and
listens for scrubbed thread metadata. It does not send a prompt, use the input
box, paste, press keys, read conversation content, execute files, or send
anything externally.
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
        "thread_follower_start_turn_usable",
        "task_sent_to_codex",
        "codex_reply_read",
        "conversation_content_read",
        "frontstage_auto_injection",
        "input_box_automation",
        "formal_ack",
        "external_send",
        "file_execution",
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


def write_frame(sock: socket.socket, message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sock.sendall(struct.pack("<I", len(payload)) + payload)


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


def scrub_thread_broadcast(frame: dict[str, Any]) -> dict[str, Any] | None:
    if frame.get("type") != "broadcast":
        return None
    method = str(frame.get("method") or "")
    if method != "thread-stream-state-changed":
        return {"method": method}
    params = frame.get("params")
    if not isinstance(params, dict):
        return {"method": method}
    change = params.get("change")
    change_type = None
    revision = None
    runtime = None
    turn_count = None
    last_turn_status = None
    if isinstance(change, dict):
        change_type = change.get("type")
        revision = change.get("revision")
        state = change.get("conversationState")
        if isinstance(state, dict):
            runtime_status = state.get("threadRuntimeStatus")
            if isinstance(runtime_status, dict):
                runtime = runtime_status.get("type")
            turns = state.get("turns")
            if isinstance(turns, list):
                turn_count = len(turns)
                if turns and isinstance(turns[-1], dict):
                    last_turn_status = turns[-1].get("status")
    return {
        "method": method,
        "conversationId": params.get("conversationId"),
        "hostId": params.get("hostId"),
        "version": params.get("version"),
        "change_type": change_type,
        "revision": revision,
        "runtime": runtime,
        "turn_count": turn_count,
        "last_turn_status": last_turn_status,
    }


def read_response_for(sock: socket.socket, request_id: str, timeout: float) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    deadline = time.monotonic() + timeout
    side_frames: list[dict[str, Any]] = []
    discovery_replies = 0
    while time.monotonic() < deadline:
        try:
            frame = read_frame(sock, max(0.1, deadline - time.monotonic()))
        except socket.timeout:
            continue
        if respond_discovery_false(sock, frame):
            discovery_replies += 1
            continue
        if frame.get("type") == "response" and frame.get("requestId") == request_id:
            return frame, side_frames, discovery_replies
        scrubbed = scrub_thread_broadcast(frame)
        if scrubbed:
            side_frames.append(scrubbed)
    raise TimeoutError(f"Timed out waiting for response {request_id}")


def recent_rollouts(limit: int) -> list[dict[str, Any]]:
    if not SESSIONS_DIR.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in SESSIONS_DIR.rglob("rollout-*.jsonl"):
        match = re.search(r"rollout-([0-9a-f-]{36})\.jsonl$", path.name)
        if not match:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append({
            "conversation_id": match.group(1),
            "path": str(path),
            "mtime": int(stat.st_mtime),
            "bytes": stat.st_size,
        })
    items.sort(key=lambda item: item["mtime"], reverse=True)
    return items[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover macOS Codex Desktop IPC metadata without sending a task.")
    parser.add_argument("--socket", default="", help="Unix socket path. Defaults to current user's codex-ipc socket.")
    parser.add_argument("--client-type", default="yuanjie-node-b-conversation-probe")
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=8.0)
    parser.add_argument("--listen-seconds", type=float, default=8.0)
    parser.add_argument("--recent-rollouts", type=int, default=5)
    args = parser.parse_args()

    if platform.system().lower() != "darwin":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "error": "node_b_codex_ipc_discovery_is_macos_only",
            "claim": "node_b_codex_ipc_discovery_not_run",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    candidates = [args.socket] if args.socket else socket_candidates()
    socket_path = candidates[0] if candidates else default_socket_path()
    output: dict[str, Any] = {
        "ok": False,
        "platform": "macOS",
        "socket": socket_path,
        "socket_exists": os.path.exists(socket_path),
        "socket_candidates": candidates,
        "initialize_ok": False,
        "conversation_id_count": 0,
        "conversation_ids": [],
        "observations": [],
        "recent_rollouts": recent_rollouts(args.recent_rollouts),
        "claim": "node_b_codex_ipc_discovery_incomplete",
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
        request_id = f"init-{uuid.uuid4()}"
        write_frame(sock, {
            "type": "request",
            "requestId": request_id,
            "method": "initialize",
            "params": {"clientType": args.client_type},
        })
        response, side_frames, replies = read_response_for(sock, request_id, args.read_timeout)
        discovery_replies += replies
        output["initialize_response_type"] = response.get("type")
        output["initialize_result_type"] = response.get("resultType")
        output["initialize_ok"] = response.get("type") == "response" and response.get("error") is None
        result = response.get("result")
        if isinstance(result, dict):
            output["client_id_present"] = bool(result.get("clientId"))
        output["observations"].extend(side_frames)

        deadline = time.monotonic() + args.listen_seconds
        while time.monotonic() < deadline:
            try:
                frame = read_frame(sock, max(0.1, min(1.0, deadline - time.monotonic())))
            except (TimeoutError, socket.timeout):
                continue
            if respond_discovery_false(sock, frame):
                discovery_replies += 1
                continue
            scrubbed = scrub_thread_broadcast(frame)
            if scrubbed:
                output["observations"].append(scrubbed)
    except Exception as exc:  # noqa: BLE001 - emitted as diagnostic JSON for remote testers.
        output["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1
    finally:
        sock.close()

    ids = []
    for item in output["observations"]:
        conversation_id = item.get("conversationId")
        if conversation_id and conversation_id not in ids:
            ids.append(conversation_id)
    output["conversation_ids"] = ids
    output["conversation_id_count"] = len(ids)
    output["client_discovery_replies_sent"] = discovery_replies
    output["ok"] = bool(output["initialize_ok"])
    output["claim"] = (
        "node_b_codex_ipc_discovery_initialized"
        if output["ok"]
        else "node_b_codex_ipc_discovery_incomplete"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
