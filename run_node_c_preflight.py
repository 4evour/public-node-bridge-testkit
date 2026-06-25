#!/usr/bin/env python3
"""Run a Node-C local adapter preflight.

This starts a local relay in-process, posts one structured light task to
``node-c``, lets the safe local adapter complete it, and verifies the exact
returned message. No network service outside localhost is used.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any
from urllib.request import Request, urlopen

from node_bridge_testkit.node_adapter import run_once
from node_bridge_testkit.relay import make_server


NODE_ID = "node-c"
MARKER = "NODEC-PREFLIGHT"
EXPECTED = "STATUS=NODEC_PREFLIGHT_OK; MARKER=NODEC_PREFLIGHT; NEXT=READY_FOR_REVIEW"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def create_reply_task(relay_url: str) -> str:
    created = http_json(
        "POST",
        f"{relay_url}/tasks",
        {
            "target_node": NODE_ID,
            "task_type": "reply_exactly",
            "payload": {
                "marker": MARKER,
                "text": EXPECTED,
            },
        },
    )
    return str(created["task"]["task_id"])


def assert_result(relay_url: str, task_id: str) -> dict[str, Any]:
    task = http_json("GET", f"{relay_url}/tasks/{task_id}")["task"]
    result = task.get("result") or {}
    agent_message = result.get("agent_message")
    if task.get("status") != "completed":
        raise AssertionError(f"{task_id} not completed: {task.get('status')}")
    if agent_message != EXPECTED:
        raise AssertionError(f"{task_id} expected {EXPECTED!r}, got {agent_message!r}")
    if result.get("execution") != "local_adapter_reply_exactly":
        raise AssertionError(f"{task_id} used unexpected execution: {result.get('execution')!r}")
    return task


def main() -> int:
    port = free_port()
    server = make_server("127.0.0.1", port, quiet=True)
    relay_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        health = http_json("GET", f"{relay_url}/health")
        if not health.get("ok"):
            raise AssertionError("relay health failed")

        task_id = create_reply_task(relay_url)
        handled = run_once(relay_url, NODE_ID)
        if not handled.get("handled"):
            raise AssertionError(f"node adapter did not handle {task_id}")

        task = assert_result(relay_url, task_id)
        result = task["result"]
        print(json.dumps({
            "ok": True,
            "relay": relay_url,
            "node_id": NODE_ID,
            "completed": {
                "marker": MARKER,
                "task_id": task_id,
                "agent_message": result["agent_message"],
                "execution": result["execution"],
            },
            "claim": "node_c_local_adapter_preflight_passed",
            "cannot_claim": [
                "real_codex_ipc",
                "external_node_connected",
                "formal_ack",
                "external_send",
                "file_execution",
                "long_running_autonomy",
            ],
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
