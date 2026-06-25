#!/usr/bin/env python3
"""Send one Node-C desktop-manual exact-reply probe and wait for result."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_MARKER = "NODEC-DESKTOP-MANUAL-001"
DEFAULT_EXPECTED = "NODEC_DESKTOP_MANUAL_OK_001"
DEFAULT_PROMPT = f"Reply exactly: {DEFAULT_EXPECTED}"


def http_json(method: str, url: str, body: dict[str, Any] | None = None, token: str = "") -> dict[str, Any]:
    data = None
    headers = {"accept": "application/json"}
    if token:
        headers["X-Node-Bridge-Token"] = token
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one Node-C desktop-manual probe.")
    parser.add_argument("--relay-url", required=True)
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--node-id", default="node-c")
    parser.add_argument("--marker", default=DEFAULT_MARKER)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--expected", default=DEFAULT_EXPECTED)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    relay = args.relay_url.rstrip("/")
    created = http_json(
        "POST",
        f"{relay}/tasks",
        {
            "target_node": args.node_id,
            "task_type": "desktop_manual_exact",
            "payload": {
                "marker": args.marker,
                "prompt": args.prompt,
                "expected": args.expected,
            },
        },
        token=args.token,
    )
    if not created.get("ok"):
        print(json.dumps({"ok": False, "stage": "create_task", "response": created}, ensure_ascii=False, indent=2))
        return 1

    task_id = str(created["task"]["task_id"])
    deadline = time.monotonic() + args.timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = http_json("GET", f"{relay}/tasks/{task_id}", token=args.token)
        task = latest.get("task") or {}
        result = task.get("result") or {}
        if task.get("status") == "completed":
            ok = (
                result.get("status") == "ok"
                and result.get("marker") == args.marker
                and result.get("desktop_reply") == args.expected
                and result.get("execution") == "local_adapter_desktop_manual_exact"
            )
            print(json.dumps({
                "ok": ok,
                "relay": relay,
                "node_id": args.node_id,
                "task_id": task_id,
                "status": task.get("status"),
                "marker": result.get("marker"),
                "desktop_reply": result.get("desktop_reply"),
                "claim": "node_c_desktop_manual_preflight_passed" if ok else "node_c_desktop_manual_result_mismatch",
                "cannot_claim": [
                    "codex_desktop_ipc",
                    "frontstage_auto_injection",
                    "formal_ack",
                    "external_send",
                    "file_execution",
                    "persistent_service",
                    "long_running_autonomy",
                ],
            }, ensure_ascii=False, indent=2))
            return 0 if ok else 1
        time.sleep(args.interval)

    print(json.dumps({
        "ok": False,
        "relay": relay,
        "node_id": args.node_id,
        "task_id": task_id,
        "status": "timeout",
        "latest": latest,
        "claim": "node_c_desktop_manual_preflight_timeout",
        "cannot_claim": [
            "codex_desktop_ipc",
            "formal_ack",
            "external_send",
            "file_execution",
        ],
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
