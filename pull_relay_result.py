#!/usr/bin/env python3
"""Pull one completed relay task result into a local return inbox.

This is caller-side evidence collection. It does not contact Codex Desktop,
execute returned files, send messages, or claim formal ACK.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_OUT_DIR = ".node_bridge_returns"
RETURN_SCHEMA = "node_bridge_return_inbox_v0.1"
DEFAULT_CANNOT_CLAIM = [
    "codex_desktop_ipc",
    "frontstage_auto_injection",
    "formal_ack",
    "external_send",
    "file_execution",
    "persistent_service",
    "long_running_autonomy",
    "production_ready_connection",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_task_id(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    safe = "".join(char for char in value.strip() if char in allowed)
    if not safe:
        raise ValueError("invalid task_id")
    return safe[:120]


def http_json(method: str, url: str, token: str = "") -> dict[str, Any]:
    headers = {"accept": "application/json"}
    if token:
        headers["X-Node-Bridge-Token"] = token
    request = Request(url, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "error": str(exc)}


def build_return_record(relay: str, task: dict[str, Any], node_id: str = "") -> dict[str, Any]:
    result = task.get("result") if isinstance(task.get("result"), dict) else None
    return {
        "schema": RETURN_SCHEMA,
        "pulled_at": now_utc(),
        "source": "relay_tasks_task_id",
        "relay": relay,
        "node_id": node_id or task.get("target_node"),
        "task_id": task.get("task_id"),
        "target_node": task.get("target_node"),
        "task_type": task.get("task_type"),
        "status": task.get("status"),
        "created_at": task.get("created_at"),
        "claimed_at": task.get("claimed_at"),
        "completed_at": task.get("completed_at"),
        "result": result,
        "claim": "relay_result_pulled_to_local_inbox" if result else "relay_task_seen_no_completed_result",
        "cannot_claim": DEFAULT_CANNOT_CLAIM,
    }


def save_return_record(record: dict[str, Any], out_dir: str | Path) -> str:
    task_id = safe_task_id(str(record.get("task_id", "task_unknown")))
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{task_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def pull_result(
    relay_url: str,
    task_id: str,
    token: str = "",
    node_id: str = "",
    out_dir: str | Path = DEFAULT_OUT_DIR,
    write_incomplete: bool = False,
) -> dict[str, Any]:
    relay = relay_url.rstrip("/")
    response = http_json("GET", f"{relay}/tasks/{safe_task_id(task_id)}", token=token)
    if not response.get("ok"):
        return {
            "ok": False,
            "stage": "fetch_task",
            "relay": relay,
            "task_id": task_id,
            "response": response,
            "claim": "relay_result_pull_failed",
            "cannot_claim": DEFAULT_CANNOT_CLAIM,
        }

    task = response.get("task")
    if not isinstance(task, dict):
        return {
            "ok": False,
            "stage": "fetch_task",
            "relay": relay,
            "task_id": task_id,
            "error": "missing task object",
            "claim": "relay_result_pull_failed",
            "cannot_claim": DEFAULT_CANNOT_CLAIM,
        }

    record = build_return_record(relay, task, node_id=node_id)
    status = str(task.get("status", ""))
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    saved_to = ""
    if status == "completed" or write_incomplete:
        saved_to = save_return_record(record, out_dir)

    ok = status == "completed" and bool(result)
    return {
        "ok": ok,
        "relay": relay,
        "node_id": node_id or task.get("target_node"),
        "task_id": task.get("task_id"),
        "status": status,
        "saved_to": saved_to,
        "agent_message": result.get("agent_message"),
        "filename": result.get("filename"),
        "sha256": result.get("sha256"),
        "execution": result.get("execution"),
        "claim": "relay_result_pulled_to_local_inbox" if ok else "relay_task_not_completed_with_result",
        "cannot_claim": DEFAULT_CANNOT_CLAIM,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull one completed relay task result into a local return inbox.")
    parser.add_argument("--relay-url", required=True)
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--node-id", default="")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-incomplete", action="store_true")
    args = parser.parse_args()

    result = pull_result(
        args.relay_url,
        args.task_id,
        token=args.token,
        node_id=args.node_id,
        out_dir=args.out_dir,
        write_incomplete=args.write_incomplete,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
