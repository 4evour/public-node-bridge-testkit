#!/usr/bin/env python3
"""Bind the currently observed Codex Desktop conversation to the local avatar.

This sensor listens only for scrubbed Codex IPC thread metadata. It does not
send a prompt, use the input box, read conversation text, or execute files.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
import uuid
from pathlib import Path
from typing import Any

from node_bridge_testkit.avatar_runtime import DEFAULT_INSTALL_DIR, install_avatar, now_utc, resolve_install_dir, write_json
from run_node_c_codex_ipc_conversation_probe import (
    Kernel32,
    cannot_claim as conversation_probe_cannot_claim,
    open_pipe,
    read_frame,
    read_response_for,
    scrub_thread_broadcast,
    write_frame,
)
from run_node_c_codex_ipc_start_turn_probe import extract_runtime_status, is_zombie_conversation, runtime_status_summary


def request_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def choose_latest_thread(
    observations: list[dict[str, Any]],
    runtime_statuses: dict[str, dict[str, Any]],
    preferred: str = "",
    allow_zombie: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, bool, str]:
    thread_observations = [
        item for item in observations
        if item.get("method") == "thread-stream-state-changed" and item.get("conversationId")
    ]
    if preferred:
        preferred_items = [item for item in thread_observations if item.get("conversationId") == preferred]
        if preferred_items:
            selected = preferred_items[-1]
            status = runtime_statuses.get(str(selected["conversationId"]))
            zombie, reason = is_zombie_conversation(status) if status else (False, "")
            return selected, status, zombie, reason

    latest_zombie: tuple[dict[str, Any], dict[str, Any] | None, bool, str] | None = None
    for item in reversed(thread_observations):
        conversation_id = str(item["conversationId"])
        status = runtime_statuses.get(conversation_id)
        zombie, reason = is_zombie_conversation(status) if status else (False, "")
        if not zombie or allow_zombie:
            return item, status, zombie, reason
        latest_zombie = latest_zombie or (item, status, zombie, reason)
    if latest_zombie:
        return latest_zombie
    return None, None, False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind current Codex Desktop conversation metadata.")
    parser.add_argument("--pipe", default=r"\\.\pipe\codex-ipc")
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--node-id", default="node-c")
    parser.add_argument("--conversation-id", default="", help="Prefer this conversationId if observed.")
    parser.add_argument("--cwd", default="", help="Optional expected cwd to record with the binding.")
    parser.add_argument("--allow-zombie-bind", action="store_true", help="Write a binding even when the observed conversation looks stuck.")
    parser.add_argument("--open-timeout", type=float, default=3.0)
    parser.add_argument("--read-timeout", type=float, default=3.0)
    parser.add_argument("--listen-seconds", type=float, default=8.0)
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "error": "node_c_bind_current_session_is_windows_only",
            "claim": "node_c_session_binding_not_run",
            "cannot_claim": conversation_probe_cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    root = resolve_install_dir(args.install_dir)
    if not (root / "config.json").exists():
        install_avatar(node_id=args.node_id, install_dir=root)
    k = Kernel32()
    handle, open_error = open_pipe(k, args.pipe, args.open_timeout)
    if handle is None:
        print(json.dumps({
            "ok": False,
            "platform": "Windows",
            "pipe": args.pipe,
            "opened": False,
            "windows_error_code": open_error,
            "claim": "node_c_session_binding_open_failed",
            "cannot_claim": conversation_probe_cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 1

    observations: list[dict[str, Any]] = []
    runtime_statuses: dict[str, dict[str, Any]] = {}
    try:
        init_id = request_id("bind-init")
        write_frame(k, handle, {
            "type": "request",
            "requestId": init_id,
            "method": "initialize",
            "params": {"clientType": "yuanjie-node-c-session-binder"},
        })
        init_response, ignored = read_response_for(k, handle, init_id, args.read_timeout)
        observations.extend(ignored)
        init_ok = (
            init_response.get("type") == "response"
            and init_response.get("requestId") == init_id
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
                conversation_id = str(scrubbed["conversationId"])
                status = extract_runtime_status(frame, conversation_id)
                if status is not None:
                    runtime_statuses[conversation_id] = status
            if args.conversation_id:
                status = extract_runtime_status(frame, args.conversation_id)
                if status is not None:
                    runtime_statuses[args.conversation_id] = status

        selected, runtime_status, zombie, zombie_reason = choose_latest_thread(
            observations,
            runtime_statuses,
            preferred=args.conversation_id,
            allow_zombie=args.allow_zombie_bind,
        )
        if not init_ok or not selected:
            print(json.dumps({
                "ok": False,
                "platform": "Windows",
                "opened": True,
                "initialize_ok": init_ok,
                "conversation_id_count": len({str(item.get("conversationId")) for item in observations if item.get("conversationId")}),
                "claim": "node_c_session_binding_no_conversation_observed",
                "cannot_claim": conversation_probe_cannot_claim(),
            }, ensure_ascii=False, indent=2))
            return 1

        conversation_id = str(selected["conversationId"])
        if zombie and not args.allow_zombie_bind:
            print(json.dumps({
                "ok": False,
                "platform": "Windows",
                "opened": True,
                "initialize_ok": init_ok,
                "conversation_id": conversation_id,
                "runtime_status": runtime_status_summary(runtime_status),
                "zombie": True,
                "zombie_reason": zombie_reason,
                "error": "refusing_to_bind_zombie_conversation",
                "remedy": "Open or create an idle Codex Desktop conversation, then rerun this binder. You may pass --conversation-id for a known idle conversation.",
                "claim": "node_c_session_binding_zombie_blocked",
                "cannot_claim": conversation_probe_cannot_claim(),
            }, ensure_ascii=False, indent=2))
            return 1

        binding = {
            "schema": "node_c_session_binding_v0.1",
            "node_id": args.node_id,
            "conversation_id": conversation_id,
            "cwd": args.cwd,
            "bound_at": now_utc(),
            "source": "codex_ipc_thread_stream_state_changed",
            "runtime_status": runtime_status_summary(runtime_status),
            "zombie": zombie,
            "zombie_reason": zombie_reason,
            "last_observation": selected,
            "cannot_claim": conversation_probe_cannot_claim(),
        }
        binding_path = root / "session_binding.json"
        write_json(binding_path, binding)
        print(json.dumps({
            "ok": True,
            "platform": "Windows",
            "opened": True,
            "initialize_ok": init_ok,
            "conversation_id": conversation_id,
            "binding_path": str(binding_path),
            "runtime_status": runtime_status_summary(runtime_status),
            "zombie": zombie,
            "claim": "node_c_session_binding_created",
            "cannot_claim": conversation_probe_cannot_claim(),
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        k.close_handle(handle)


if __name__ == "__main__":
    raise SystemExit(main())
