#!/usr/bin/env python3
"""Windows Codex IPC router protocol probe.

This probe speaks the public shape observed from Codex Desktop's local IPC
router: 4-byte little-endian frame length followed by a UTF-8 JSON message.

It does not use the input box, click, paste, press keys, or send a real prompt.
By default it only initializes as a temporary IPC client and waits only for the
matching initialize response.

An optional dry thread-follower request exists behind an explicit flag. That
mode can receive unrelated IPC broadcasts, so it is not used by default.
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


def base_cannot_claim() -> list[str]:
    return [
        "thread_follower_start_turn_usable",
        "task_sent_to_codex",
        "codex_reply_read",
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
        handle = k.create_file(
            pipe,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
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
        else:
            time.sleep(0.05)
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
        ignored.append(scrub_response(frame))
    raise TimeoutError(f"Timed out waiting for response {request_id}")


def request_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def scrub_response(message: dict[str, object]) -> dict[str, object]:
    allowed = {
        "type",
        "requestId",
        "resultType",
        "method",
        "handledByClientId",
        "result",
        "error",
    }
    return {key: value for key, value in message.items() if key in allowed}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Codex Desktop IPC router framing and initialize handshake.")
    parser.add_argument("--pipe", default=r"\\.\pipe\codex-ipc")
    parser.add_argument("--client-type", default="yuanjie-node-c-ipc-probe")
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=3.0)
    parser.add_argument("--dry-thread-follower", action="store_true", help="Send an empty-params dry thread-follower request after initialize.")
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "stage": "platform",
            "error": "codex_ipc_router_probe_is_windows_only",
            "claim": "node_c_codex_ipc_router_probe_not_run",
            "cannot_claim": ["codex_desktop_ipc_usable", *base_cannot_claim()],
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
            "claim": "node_c_codex_ipc_router_open_failed",
            "cannot_claim": ["codex_desktop_ipc_usable", *base_cannot_claim()],
        }, ensure_ascii=False, indent=2))
        return 1

    close_ok = False
    try:
        init_request_id = request_id("init")
        init_message = {
            "type": "request",
            "requestId": init_request_id,
            "method": "initialize",
            "params": {"clientType": args.client_type},
        }
        init_frame_bytes = write_frame(k, handle, init_message)
        init_response, init_ignored = read_response_for(k, handle, init_request_id, args.read_timeout)
        init_ok = (
            init_response.get("type") == "response"
            and init_response.get("requestId") == init_request_id
            and init_response.get("resultType") == "success"
            and isinstance(init_response.get("result"), dict)
            and bool(init_response["result"].get("clientId"))
        )
        client_id = ""
        if isinstance(init_response.get("result"), dict):
            client_id = str(init_response["result"].get("clientId") or "")

        dry_response: dict[str, object] | None = None
        dry_error = ""
        if init_ok and args.dry_thread_follower:
            dry_request_id = request_id("dry")
            dry_message = {
                "type": "request",
                "requestId": dry_request_id,
                "sourceClientId": client_id,
                "method": "thread-follower-start-turn",
                "version": 1,
                "params": {},
                "timeoutMs": int(args.read_timeout * 1000),
            }
            try:
                write_frame(k, handle, dry_message)
                dry_response, dry_ignored = read_response_for(k, handle, dry_request_id, args.read_timeout + 1.0)
            except Exception as exc:  # noqa: BLE001 - surfaced as diagnostic JSON.
                dry_error = f"{type(exc).__name__}: {exc}"
                dry_ignored = []
        else:
            dry_ignored = []

        thread_follower_route_observed = bool(
            dry_response
            and dry_response.get("type") == "response"
            and dry_response.get("error") != "no-client-found"
        )
        ok = bool(init_ok)
        claim = "node_c_codex_ipc_router_initialize_passed" if init_ok else "node_c_codex_ipc_router_initialize_failed"
        if thread_follower_route_observed:
            claim = "node_c_codex_thread_follower_dry_route_observed"

        print(json.dumps({
            "ok": ok,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "initialize": {
                "ok": init_ok,
                "frame_bytes_written": init_frame_bytes,
                "response": scrub_response(init_response),
                "ignored_frames_before_response": init_ignored,
                "client_id_present": bool(client_id),
            },
            "dry_thread_follower": None if not args.dry_thread_follower else {
                "sent_empty_params_only": True,
                "route_observed": thread_follower_route_observed,
                "response": scrub_response(dry_response) if dry_response else None,
                "ignored_frames_before_response": dry_ignored,
                "error": dry_error,
            },
            "claim": claim,
            "cannot_claim": base_cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except Exception as exc:  # noqa: BLE001 - surfaced as diagnostic JSON.
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": True,
            "error": f"{type(exc).__name__}: {exc}",
            "claim": "node_c_codex_ipc_router_probe_error",
            "cannot_claim": ["codex_desktop_ipc_usable", *base_cannot_claim()],
        }, ensure_ascii=False, indent=2))
        return 1
    finally:
        close_ok = bool(k.close_handle(handle))
        _ = close_ok


if __name__ == "__main__":
    raise SystemExit(main())
