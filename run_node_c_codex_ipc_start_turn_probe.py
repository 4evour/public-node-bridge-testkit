#!/usr/bin/env python3
"""Windows Codex IPC start-turn probe.

This sends one fixed, tiny prompt to an already observed Codex Desktop
conversation through the IPC router. It does not use the input box, click,
paste, press keys, execute files, or send anything outside Codex Desktop.

The probe only claims success if the observed assistant message exactly matches
the expected marker.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import struct
import sys
import time
import uuid
from ctypes import wintypes
from typing import Any


GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1
ERROR_PIPE_BUSY = 231
ERROR_MORE_DATA = 234
MAX_FRAME_BYTES = 256 * 1024 * 1024


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


class Kernel32:
    def __init__(self) -> None:
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.create_file = self.kernel32.CreateFileW
        self.create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.create_file.restype = wintypes.HANDLE
        self.close_handle = self.kernel32.CloseHandle
        self.close_handle.argtypes = [wintypes.HANDLE]
        self.close_handle.restype = wintypes.BOOL
        self.wait_named_pipe = self.kernel32.WaitNamedPipeW
        self.wait_named_pipe.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        self.wait_named_pipe.restype = wintypes.BOOL
        self.write_file = self.kernel32.WriteFile
        self.write_file.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        self.write_file.restype = wintypes.BOOL
        self.read_file = self.kernel32.ReadFile
        self.read_file.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        self.read_file.restype = wintypes.BOOL
        self.peek_named_pipe = self.kernel32.PeekNamedPipe
        self.peek_named_pipe.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.peek_named_pipe.restype = wintypes.BOOL

    def last_error(self) -> int:
        return ctypes.get_last_error()


def open_pipe(k: Kernel32, pipe: str, timeout: float) -> tuple[object | None, int]:
    deadline = time.monotonic() + timeout
    last_error = 0
    while time.monotonic() < deadline:
        handle = k.create_file(pipe, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        if int(handle) != INVALID_HANDLE_VALUE:
            return handle, 0
        last_error = k.last_error()
        if last_error == ERROR_PIPE_BUSY:
            k.wait_named_pipe(pipe, 250)
        else:
            time.sleep(0.1)
    return None, last_error


def write_frame(k: Kernel32, handle: object, message: dict[str, Any]) -> int:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    frame = struct.pack("<I", len(payload)) + payload
    written = wintypes.DWORD(0)
    buf = ctypes.create_string_buffer(frame)
    ok = k.write_file(handle, buf, len(frame), ctypes.byref(written), None)
    if not ok:
        raise OSError(k.last_error(), "WriteFile failed")
    return int(written.value)


def available_bytes(k: Kernel32, handle: object) -> int:
    total = wintypes.DWORD(0)
    ok = k.peek_named_pipe(handle, None, 0, None, ctypes.byref(total), None)
    if not ok:
        raise OSError(k.last_error(), "PeekNamedPipe failed")
    return int(total.value)


def read_available(k: Kernel32, handle: object, n: int, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0 and time.monotonic() < deadline:
        avail = available_bytes(k, handle)
        if avail <= 0:
            time.sleep(0.05)
            continue
        size = min(remaining, avail)
        buf = ctypes.create_string_buffer(size)
        read = wintypes.DWORD(0)
        ok = k.read_file(handle, buf, size, ctypes.byref(read), None)
        error = k.last_error()
        if not ok and error != ERROR_MORE_DATA:
            raise OSError(error, "ReadFile failed")
        if read.value:
            chunks.append(buf.raw[: read.value])
            remaining -= int(read.value)
    if remaining:
        raise TimeoutError(f"Timed out reading {n} bytes")
    return b"".join(chunks)


def read_frame(k: Kernel32, handle: object, timeout: float) -> dict[str, Any]:
    header = read_available(k, handle, 4, timeout)
    (length,) = struct.unpack("<I", header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"Invalid frame length: {length}")
    payload = read_available(k, handle, length, timeout)
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("IPC frame JSON was not an object")
    return data


def request_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def progress(enabled: bool, message: str, end: str = "\n") -> None:
    if enabled:
        print(message, end=end, file=sys.stderr, flush=True)


def maybe_answer_discovery(k: Kernel32, handle: object, frame: dict[str, Any]) -> bool:
    if frame.get("type") != "client-discovery-request":
        return False
    write_frame(k, handle, {
        "type": "client-discovery-response",
        "requestId": frame.get("requestId"),
        "response": {"canHandle": False},
    })
    return True


def progress_frame(enabled: bool, frame: dict[str, Any]) -> None:
    if not enabled:
        return
    frame_type = frame.get("type")
    method = frame.get("method")
    if frame_type == "broadcast":
        marker = "[B]"
    elif frame_type == "response":
        marker = "[R]"
    elif frame_type == "client-discovery-request":
        marker = "[D]"
    else:
        marker = "[U]"
    progress(True, marker if not method else f"{marker}{method}", end="")


def read_response_for(
    k: Kernel32,
    handle: object,
    request_id_value: str,
    timeout: float,
    show_progress: bool = False,
) -> tuple[dict[str, Any], int, list[dict[str, Any]]]:
    deadline = time.monotonic() + timeout
    discovery_replies = 0
    side_frames: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        frame = read_frame(k, handle, max(0.1, deadline - time.monotonic()))
        progress_frame(show_progress, frame)
        if maybe_answer_discovery(k, handle, frame):
            discovery_replies += 1
            continue
        if frame.get("type") == "response" and frame.get("requestId") == request_id_value:
            return frame, discovery_replies, side_frames
        side_frames.append(frame)
    raise TimeoutError(f"Timed out waiting for response {request_id_value}")


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


def frame_belongs_to_conversation(frame: dict[str, Any], conversation_id: str) -> bool:
    params = frame.get("params")
    if isinstance(params, dict) and params.get("conversationId") == conversation_id:
        return True
    return conversation_id in iter_strings(frame)


def exact_expected_seen(frame: dict[str, Any], conversation_id: str, expected: str) -> bool:
    if not frame_belongs_to_conversation(frame, conversation_id):
        return False
    return any(text.strip() == expected for text in iter_strings(frame))


def bump_method_count(counts: dict[str, int], frame: dict[str, Any]) -> None:
    method = str(frame.get("method") or frame.get("type") or "unknown")
    counts[method] = counts.get(method, 0) + 1


def change_metadata(frame: dict[str, Any]) -> tuple[str | None, int | None]:
    params = frame.get("params")
    if not isinstance(params, dict):
        return None, None
    change = params.get("change")
    if not isinstance(change, dict):
        return None, None
    change_type = change.get("type")
    revision = change.get("revision")
    return (
        str(change_type) if change_type is not None else None,
        int(revision) if isinstance(revision, int) else None,
    )


def update_state_counts(counts: dict[str, int], frame: dict[str, Any]) -> None:
    for text in iter_strings(frame):
        normalized = text.strip().lower()
        if normalized in {"completed", "complete", "done", "idle", "finished"}:
            counts[normalized] = counts.get(normalized, 0) + 1
        if normalized in {"inprogress", "in_progress", "running", "streaming", "thinking"}:
            counts[normalized] = counts.get(normalized, 0) + 1


def inspect_observed_frame(
    frame: dict[str, Any],
    conversation_id: str,
    expected: str,
    methods: dict[str, int],
) -> tuple[bool, bool, bool]:
    bump_method_count(methods, frame)
    expected_seen = any(text.strip() == expected for text in iter_strings(frame))
    conversation_seen = frame.get("type") == "broadcast" and frame_belongs_to_conversation(frame, conversation_id)
    exact_seen = exact_expected_seen(frame, conversation_id, expected)
    return expected_seen, conversation_seen, exact_seen


def observe_settle(
    k: Kernel32,
    handle: object,
    conversation_id: str,
    timeout: float,
    show_progress: bool = False,
) -> tuple[dict[str, Any], int]:
    deadline = time.monotonic() + timeout
    discovery_replies = 0
    frames = 0
    conversation_frames = 0
    methods: dict[str, int] = {}
    change_types: dict[str, int] = {}
    revisions: list[int] = []
    state_keywords: dict[str, int] = {}
    progress(show_progress, "\n[settle] observing post-marker stream", end="")
    while time.monotonic() < deadline:
        try:
            frame = read_frame(k, handle, max(0.1, min(5.0, deadline - time.monotonic())))
        except TimeoutError:
            progress(show_progress, ".", end="")
            continue
        progress_frame(show_progress, frame)
        frames += 1
        if maybe_answer_discovery(k, handle, frame):
            discovery_replies += 1
            continue
        bump_method_count(methods, frame)
        if not frame_belongs_to_conversation(frame, conversation_id):
            continue
        conversation_frames += 1
        change_type, revision = change_metadata(frame)
        if change_type:
            change_types[change_type] = change_types.get(change_type, 0) + 1
        if revision is not None:
            revisions.append(revision)
        update_state_counts(state_keywords, frame)
    return {
        "settle_timeout_seconds": timeout,
        "frames_seen": frames,
        "conversation_frames_seen": conversation_frames,
        "methods_seen": methods,
        "change_types_seen": change_types,
        "revision_min": min(revisions) if revisions else None,
        "revision_max": max(revisions) if revisions else None,
        "state_keywords_seen": state_keywords,
        "terminal_state_hint_seen": any(
            state_keywords.get(key, 0) > 0 for key in ("completed", "complete", "done", "idle", "finished")
        ),
        "still_running_hint_seen": any(
            state_keywords.get(key, 0) > 0 for key in ("inprogress", "in_progress", "running", "streaming", "thinking")
        ),
    }, discovery_replies


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one tiny Codex Desktop IPC start-turn probe.")
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument("--pipe", default=r"\\.\pipe\codex-ipc")
    parser.add_argument("--marker", default="NODEC_IPC_OK_001")
    parser.add_argument("--task-text", default="", help="Optional full prompt text. Defaults to 'Reply exactly: MARKER'.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Thread cwd to send. Use 'null' to send null.")
    parser.add_argument("--approval-policy", default="never")
    parser.add_argument("--start-timeout", type=float, default=120.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--settle-timeout", type=float, default=30.0)
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=10.0)
    parser.add_argument("--progress", action="store_true", help="Print scrubbed wait progress to stderr.")
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "error": "codex_ipc_start_turn_probe_is_windows_only",
            "claim": "node_c_codex_ipc_start_turn_probe_not_run",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    expected = args.marker.strip()
    cwd = None if args.cwd.strip().lower() in {"", "none", "null"} else os.path.abspath(args.cwd)
    prompt = args.task_text or f"Reply exactly: {expected}"
    k = Kernel32()
    progress(args.progress, "[open] codex-ipc pipe")
    handle, open_error = open_pipe(k, args.pipe, args.open_timeout)
    if handle is None:
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "opened": False,
            "windows_error_code": open_error,
            "claim": "node_c_codex_ipc_start_turn_open_failed",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    discovery_replies = 0
    try:
        init_id = request_id("init")
        progress(args.progress, "[init] initialize", end="")
        write_frame(k, handle, {
            "type": "request",
            "requestId": init_id,
            "method": "initialize",
            "params": {"clientType": "yuanjie-node-c-start-turn-probe"},
        })
        buffered_frames: list[dict[str, Any]] = []
        init_response, replies, side_frames = read_response_for(
            k, handle, init_id, args.read_timeout, show_progress=args.progress
        )
        progress(args.progress, "\n[init] done")
        discovery_replies += replies
        buffered_frames.extend(side_frames)
        init_ok = init_response.get("resultType") == "success"
        client_id = ""
        if isinstance(init_response.get("result"), dict):
            client_id = str(init_response["result"].get("clientId") or "")
        if not init_ok or not client_id:
            raise RuntimeError("initialize_failed")

        start_id = request_id("start")
        progress(args.progress, "[start] thread-follower-start-turn", end="")
        start_message = {
            "type": "request",
            "requestId": start_id,
            "sourceClientId": client_id,
            "method": "thread-follower-start-turn",
            "version": 1,
            "params": {
                "conversationId": args.conversation_id,
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
        write_frame(k, handle, start_message)
        start_response, replies, side_frames = read_response_for(
            k, handle, start_id, args.read_timeout, show_progress=args.progress
        )
        progress(args.progress, "\n[start] response received")
        discovery_replies += replies
        buffered_frames.extend(side_frames)
        start_response_scrubbed = scrub_start_response(start_response)
        task_sent = start_response.get("type") == "response" and start_response.get("resultType") == "success"

        observed_exact = False
        expected_seen_anywhere = False
        conversation_broadcast_seen = False
        observed_frame_count = 0
        live_frame_count = 0
        observed_methods: dict[str, int] = {}
        for frame in buffered_frames:
            observed_frame_count += 1
            seen_marker, seen_conversation, seen_exact = inspect_observed_frame(
                frame, args.conversation_id, expected, observed_methods
            )
            expected_seen_anywhere = expected_seen_anywhere or seen_marker
            conversation_broadcast_seen = conversation_broadcast_seen or seen_conversation
            observed_exact = observed_exact or seen_exact

        deadline = time.monotonic() + args.timeout
        last_progress_at = time.monotonic()
        progress(args.progress, "[observe] waiting for exact marker", end="")
        while task_sent and not observed_exact and time.monotonic() < deadline:
            try:
                frame = read_frame(k, handle, max(0.1, min(5.0, deadline - time.monotonic())))
            except TimeoutError:
                now = time.monotonic()
                if args.progress:
                    if now - last_progress_at >= 10:
                        elapsed = args.timeout - max(0.0, deadline - now)
                        progress(True, f"\n[observe] elapsed={elapsed:.0f}s", end="")
                        last_progress_at = now
                    else:
                        progress(True, ".", end="")
                continue
            progress_frame(args.progress, frame)
            observed_frame_count += 1
            live_frame_count += 1
            if maybe_answer_discovery(k, handle, frame):
                discovery_replies += 1
                continue
            seen_marker, seen_conversation, seen_exact = inspect_observed_frame(
                frame, args.conversation_id, expected, observed_methods
            )
            expected_seen_anywhere = expected_seen_anywhere or seen_marker
            conversation_broadcast_seen = conversation_broadcast_seen or seen_conversation
            observed_exact = observed_exact or seen_exact

        settle_diagnostics: dict[str, Any] | None = None
        if task_sent and observed_exact and args.settle_timeout > 0:
            settle_diagnostics, replies = observe_settle(
                k,
                handle,
                args.conversation_id,
                args.settle_timeout,
                show_progress=args.progress,
            )
            discovery_replies += replies

        ok = bool(task_sent and observed_exact)
        print(json.dumps({
            "ok": ok,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "conversation_id": args.conversation_id,
            "cwd": cwd,
            "marker": expected,
            "start_timeout_ms": int(args.start_timeout * 1000),
            "initialize_ok": init_ok,
            "start_turn_response": start_response_scrubbed,
            "task_sent_to_codex": task_sent,
            "codex_exact_reply_observed": observed_exact,
            "agent_message": expected if observed_exact else None,
            "gates": {
                "target_thread_ok": bool(task_sent),
                "start_turn_ok": bool(task_sent),
                "completion_observed": bool(observed_exact),
                "refresh_after_ok": None,
            },
            "diagnostics": {
                "observe_timeout_seconds": args.timeout,
                "frames_observed_total_after_start_request": observed_frame_count,
                "buffered_frames_seen_before_start_response": len(buffered_frames),
                "live_frames_seen_after_start_response": live_frame_count,
                "methods_observed_after_start": observed_methods,
                "conversation_broadcast_seen": conversation_broadcast_seen,
                "expected_marker_seen_anywhere": expected_seen_anywhere,
                "post_marker_settle": settle_diagnostics,
            },
            "client_discovery_replies_sent": discovery_replies,
            "claim": "node_c_codex_ipc_start_turn_exact_reply_passed" if ok else "node_c_codex_ipc_start_turn_probe_incomplete",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except Exception as exc:  # noqa: BLE001 - returned as diagnostic JSON.
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "conversation_id": args.conversation_id,
            "error": f"{type(exc).__name__}: {exc}",
            "claim": "node_c_codex_ipc_start_turn_probe_error",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1
    finally:
        k.close_handle(handle)


if __name__ == "__main__":
    raise SystemExit(main())
