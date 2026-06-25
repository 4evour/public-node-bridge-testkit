#!/usr/bin/env python3
"""Windows Codex IPC conversation-id metadata probe.

This probe initializes against Codex Desktop's local IPC router, listens briefly
for IPC broadcasts, and prints only scrubbed thread metadata such as
conversationId, hostId, change type, and revision.

It must not print turns, messages, screenshots, files, or any conversation body.
It does not use the input box, click, paste, press keys, or send a task.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import struct
import time
import uuid
from ctypes import wintypes


GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1
ERROR_PIPE_BUSY = 231
ERROR_MORE_DATA = 234
MAX_FRAME_BYTES = 256 * 1024 * 1024


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


def write_frame(k: Kernel32, handle: object, message: dict[str, object]) -> int:
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


def read_frame(k: Kernel32, handle: object, timeout: float) -> dict[str, object]:
    header = read_available(k, handle, 4, timeout)
    (length,) = struct.unpack("<I", header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"Invalid frame length: {length}")
    payload = read_available(k, handle, length, timeout)
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("IPC frame JSON was not an object")
    return data


def read_response_for(k: Kernel32, handle: object, request_id: str, timeout: float) -> tuple[dict[str, object], list[dict[str, object]]]:
    deadline = time.monotonic() + timeout
    ignored: list[dict[str, object]] = []
    while time.monotonic() < deadline:
        frame = read_frame(k, handle, max(0.1, deadline - time.monotonic()))
        if frame.get("type") == "response" and frame.get("requestId") == request_id:
            return frame, ignored
        scrubbed = scrub_thread_broadcast(frame)
        if scrubbed:
            ignored.append(scrubbed)
    raise TimeoutError(f"Timed out waiting for response {request_id}")


def scrub_thread_broadcast(frame: dict[str, object]) -> dict[str, object] | None:
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
    if isinstance(change, dict):
        change_type = change.get("type")
        revision = change.get("revision")
    return {
        "method": method,
        "conversationId": params.get("conversationId"),
        "hostId": params.get("hostId"),
        "version": params.get("version"),
        "change_type": change_type,
        "revision": revision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Listen for scrubbed Codex IPC thread metadata.")
    parser.add_argument("--pipe", default=r"\\.\pipe\codex-ipc")
    parser.add_argument("--client-type", default="yuanjie-node-c-conversation-probe")
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=3.0)
    parser.add_argument("--listen-seconds", type=float, default=8.0)
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "stage": "platform",
            "error": "codex_ipc_conversation_probe_is_windows_only",
            "claim": "node_c_codex_ipc_conversation_probe_not_run",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    k = Kernel32()
    handle, open_error = open_pipe(k, args.pipe, args.open_timeout)
    if handle is None:
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": False,
            "windows_error_code": open_error,
            "claim": "node_c_codex_ipc_conversation_probe_open_failed",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    observations: list[dict[str, object]] = []
    try:
        request_id = f"init-{uuid.uuid4()}"
        write_frame(k, handle, {
            "type": "request",
            "requestId": request_id,
            "method": "initialize",
            "params": {"clientType": args.client_type},
        })
        init_response, ignored = read_response_for(k, handle, request_id, args.read_timeout)
        observations.extend(ignored)
        init_ok = (
            init_response.get("type") == "response"
            and init_response.get("requestId") == request_id
            and init_response.get("resultType") == "success"
        )

        deadline = time.monotonic() + args.listen_seconds
        while time.monotonic() < deadline:
            try:
                frame = read_frame(k, handle, max(0.1, min(0.5, deadline - time.monotonic())))
            except TimeoutError:
                continue
            scrubbed = scrub_thread_broadcast(frame)
            if scrubbed:
                observations.append(scrubbed)

        thread_observations = [
            item for item in observations
            if item.get("method") == "thread-stream-state-changed" and item.get("conversationId")
        ]
        unique_conversation_ids = sorted({str(item["conversationId"]) for item in thread_observations})
        print(json.dumps({
            "ok": bool(init_ok and unique_conversation_ids),
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "initialize_ok": init_ok,
            "conversation_id_count": len(unique_conversation_ids),
            "conversation_ids": unique_conversation_ids,
            "observations": observations[-20:],
            "claim": "node_c_codex_ipc_conversation_metadata_observed" if unique_conversation_ids else "node_c_codex_ipc_no_conversation_metadata_observed",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 0 if init_ok and unique_conversation_ids else 1
    except Exception as exc:  # noqa: BLE001 - returned as diagnostic JSON.
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "error": f"{type(exc).__name__}: {exc}",
            "claim": "node_c_codex_ipc_conversation_probe_error",
            "cannot_claim": cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1
    finally:
        k.close_handle(handle)


if __name__ == "__main__":
    raise SystemExit(main())
