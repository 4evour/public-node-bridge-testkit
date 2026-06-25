#!/usr/bin/env python3
"""Poll one desktop-manual task and return the manually observed Desktop reply."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from node_bridge_testkit.avatar_runtime import DEFAULT_INSTALL_DIR, load_avatar, update_state


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


def poll_once(relay: str, node_id: str, token: str) -> dict[str, Any]:
    poll_url = f"{relay.rstrip('/')}/poll?{urlencode({'node_id': node_id})}"
    return http_json("GET", poll_url, token=token)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Node-C desktop-manual bridge client.")
    parser.add_argument("--relay-url", required=True)
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--desktop-reply", default="", help="Non-interactive reply for tests.")
    args = parser.parse_args()

    root, config, state = load_avatar(args.install_dir)
    node_id = str(config["node_id"])
    relay = args.relay_url.rstrip("/")
    deadline = time.monotonic() + args.timeout
    task: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        polled = poll_once(relay, node_id, args.token)
        if not polled.get("ok"):
            print(json.dumps({"ok": False, "stage": "poll", "response": polled}, ensure_ascii=False, indent=2))
            return 1
        maybe_task = polled.get("task")
        if isinstance(maybe_task, dict):
            task = maybe_task
            break
        time.sleep(args.interval)

    if not task:
        updated_state = update_state(root, state, "node_c_desktop_manual_timeout_no_task")
        print(json.dumps({
            "ok": False,
            "relay": relay,
            "node_id": node_id,
            "completed": [],
            "state": {
                "last_heartbeat_at": updated_state["last_heartbeat_at"],
                "last_run_claim": updated_state["last_run_claim"],
            },
            "claim": "node_c_desktop_manual_timeout_no_task",
        }, ensure_ascii=False, indent=2))
        return 1

    if task.get("task_type") != "desktop_manual_exact":
        print(json.dumps({"ok": False, "stage": "task_type", "task": task}, ensure_ascii=False, indent=2))
        return 1

    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    prompt = str(payload.get("prompt", ""))
    expected = str(payload.get("expected", ""))
    marker = str(payload.get("marker", ""))
    print("\n=== SEND THIS TO CODEX DESKTOP ===")
    print(prompt)
    print("=== END PROMPT ===\n")
    if args.desktop_reply:
        desktop_reply = args.desktop_reply.strip()
    else:
        desktop_reply = input("Paste Codex Desktop exact reply here: ").strip()

    ok = desktop_reply == expected
    result = {
        "status": "ok" if ok else "mismatch",
        "node_id": node_id,
        "marker": marker,
        "desktop_reply": desktop_reply,
        "expected": expected,
        "execution": "local_adapter_desktop_manual_exact",
        "safe_mode": True,
        "manual_step": True,
        "denied_capabilities": [
            "codex_desktop_ipc",
            "frontstage_auto_injection",
            "shell_execution",
            "file_execution",
            "external_send",
            "private_endpoint_routing",
        ],
    }
    result_url = f"{relay}/tasks/{task['task_id']}/result"
    posted = http_json("POST", result_url, {"node_id": node_id, "result": result}, token=args.token)
    updated_state = update_state(root, state, "node_c_desktop_manual_preflight_passed" if ok else "node_c_desktop_manual_preflight_mismatch")
    print(json.dumps({
        "ok": ok and bool(posted.get("ok")),
        "relay": relay,
        "node_id": node_id,
        "completed": [{
            "task_id": task.get("task_id"),
            "marker": marker,
            "desktop_reply": desktop_reply,
            "expected": expected,
            "execution": result["execution"],
        }],
        "state": {
            "last_heartbeat_at": updated_state["last_heartbeat_at"],
            "last_run_claim": updated_state["last_run_claim"],
        },
        "claim": updated_state["last_run_claim"],
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
    return 0 if ok and posted.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
