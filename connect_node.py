#!/usr/bin/env python3
"""One-entry Node-C connector for safe preflight.

The user should only need to paste a Yuanjie connect card or pass relay/token
arguments. This script installs the local avatar, reports health, then polls the
relay for a small number of queued safe tasks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from node_bridge_testkit.avatar_runtime import (
    DEFAULT_INSTALL_DIR,
    DEFAULT_NODE_ID,
    health_packet,
    install_avatar,
    load_avatar,
    update_state,
)
from node_bridge_testkit.node_adapter import run_once


def parse_connect_card(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "YUANJIE_CONNECT_V1":
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_card_from_stdin() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Connect Node-C with one safe entrypoint.")
    parser.add_argument("--relay-url", default="")
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--node-id", default=DEFAULT_NODE_ID)
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--max-tasks", type=int, default=1)
    parser.add_argument("--card", default="", help="Inline YUANJIE_CONNECT_V1 card text.")
    args = parser.parse_args()

    card_text = args.card or read_card_from_stdin()
    card = parse_connect_card(card_text)
    relay = (args.relay_url or card.get("relay") or "").rstrip("/")
    token = args.token or card.get("connect_code") or card.get("token") or ""
    node_id = card.get("node_id") or args.node_id
    install_dir = card.get("install_dir") or args.install_dir

    if not relay:
        print(json.dumps({
            "ok": False,
            "stage": "config",
            "error": "missing relay_url; pass --relay-url or paste YUANJIE_CONNECT_V1 relay=...",
        }, ensure_ascii=False, indent=2))
        return 1
    if not token:
        print(json.dumps({
            "ok": False,
            "stage": "config",
            "error": "missing connect_code/token; pass --token or paste YUANJIE_CONNECT_V1 connect_code=...",
        }, ensure_ascii=False, indent=2))
        return 1

    install = install_avatar(node_id=node_id, install_dir=install_dir)
    root, config, state = load_avatar(install_dir)
    health = health_packet(config)
    deadline = time.monotonic() + args.timeout
    completed: list[dict[str, Any]] = []

    while time.monotonic() < deadline and len(completed) < args.max_tasks:
        result = run_once(relay, node_id, token=token, sandbox_dir=root)
        if not result.get("ok"):
            updated_state = update_state(root, state, "node_c_connect_poll_failed")
            print(json.dumps({
                "ok": False,
                "stage": "poll_or_submit",
                "install": install,
                "health": health,
                "result": result,
                "state": {
                    "last_heartbeat_at": updated_state["last_heartbeat_at"],
                    "last_run_claim": updated_state["last_run_claim"],
                },
                "claim": "node_c_connect_poll_failed",
            }, ensure_ascii=False, indent=2))
            return 1
        if result.get("handled"):
            posted = result.get("posted") if isinstance(result.get("posted"), dict) else {}
            task = posted.get("task") if isinstance(posted.get("task"), dict) else {}
            task_result = task.get("result") if isinstance(task.get("result"), dict) else {}
            completed.append({
                "task_id": result.get("task_id"),
                "task_type": task.get("task_type"),
                "marker": task_result.get("marker"),
                "agent_message": task_result.get("agent_message"),
                "filename": task_result.get("filename"),
                "bytes": task_result.get("bytes"),
                "sha256": task_result.get("sha256"),
                "saved_to": task_result.get("saved_to"),
                "execution": task_result.get("execution"),
            })
        else:
            time.sleep(args.interval)

    ok = bool(completed)
    claim = "node_c_one_step_connect_completed_task" if ok else "node_c_one_step_connect_online_no_task"
    updated_state = update_state(root, state, claim)
    print(json.dumps({
        "ok": ok,
        "relay": relay,
        "node_id": node_id,
        "install_dir": str(Path(install_dir).resolve()),
        "health": health,
        "completed": completed,
        "state": {
            "last_heartbeat_at": updated_state["last_heartbeat_at"],
            "last_run_claim": updated_state["last_run_claim"],
        },
        "claim": claim,
        "cannot_claim": [
            "real_codex_ipc",
            "frontstage_auto_injection",
            "formal_ack",
            "external_send",
            "file_execution",
            "persistent_service",
            "long_running_autonomy",
            "production_ready_connection",
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
