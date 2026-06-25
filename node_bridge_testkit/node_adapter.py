#!/usr/bin/env python3
"""Safe local node adapter for the public node bridge testkit.

This adapter is intentionally narrow. It handles only allowlisted light tasks
and never executes shell commands, opens local files, sends messages, or touches
private data.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DENIED_CAPABILITIES = [
    "shell_execution",
    "file_read",
    "file_write",
    "external_send",
    "private_endpoint_routing",
]


def http_json(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"ok": False, "error": str(exc)}
        return payload


def execute_task(task: dict[str, Any], node_id: str) -> dict[str, Any]:
    task_type = task.get("task_type")
    payload = task.get("payload") or {}
    if task_type == "reply_exactly":
        text = payload.get("text")
        if not isinstance(text, str):
            return {"status": "error", "error": "missing payload.text"}
        return {
            "status": "ok",
            "node_id": node_id,
            "marker": str(payload.get("marker", "")),
            "agent_message": text,
            "execution": "local_adapter_reply_exactly",
            "safe_mode": True,
            "denied_capabilities": DENIED_CAPABILITIES,
        }
    return {"status": "error", "error": f"unsupported task_type: {task_type}"}


def run_once(relay_url: str, node_id: str) -> dict[str, Any]:
    poll_url = f"{relay_url.rstrip('/')}/poll?{urlencode({'node_id': node_id})}"
    polled = http_json("GET", poll_url)
    task = polled.get("task")
    if not task:
        return {"ok": True, "handled": False, "node_id": node_id}

    result = execute_task(task, node_id)
    task_id = task["task_id"]
    result_url = f"{relay_url.rstrip('/')}/tasks/{task_id}/result"
    posted = http_json("POST", result_url, {"node_id": node_id, "result": result})
    return {"ok": bool(posted.get("ok")), "handled": True, "task_id": task_id, "posted": posted}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a safe local node adapter.")
    parser.add_argument("--relay", default="http://127.0.0.1:8765")
    parser.add_argument("--node-id", default="node-c")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--max-iterations", type=int, default=0)
    args = parser.parse_args()

    iterations = 0
    while True:
        result = run_once(args.relay, args.node_id)
        print(json.dumps(result, ensure_ascii=False))
        iterations += 1
        if args.once:
            return 0 if result.get("ok") else 1
        if args.max_iterations and iterations >= args.max_iterations:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
