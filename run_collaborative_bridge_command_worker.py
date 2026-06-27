#!/usr/bin/env python3
"""Run one approved collaborative allowlisted command task as the Host worker."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


NODE_ID = "node-c"
DEFAULT_COMMANDS = {
    "local_demo": [sys.executable, "run_local_demo.py"],
    "node_c_preflight": [sys.executable, "run_node_c_preflight.py"],
    "collaborative_bridge_preflight": [sys.executable, "run_collaborative_bridge_preflight.py"],
}


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
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"ok": False, "error": str(exc)}
        payload["http_status"] = exc.code
        return payload


def load_commands(path: str) -> dict[str, list[str]]:
    if not path:
        return dict(DEFAULT_COMMANDS)
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("command allowlist must be a JSON object")
    commands: dict[str, list[str]] = {}
    for command_id, command in data.items():
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("command allowlist ids must be non-empty strings")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise ValueError(f"command allowlist entry must be a non-empty string list: {command_id}")
        commands[command_id] = list(command)
    return commands


def find_approved_task(relay_url: str, node_id: str, token: str = "") -> dict[str, Any] | None:
    tasks = http_json("GET", f"{relay_url.rstrip('/')}/tasks?node_id={node_id}", token=token)
    if not tasks.get("ok"):
        raise RuntimeError(f"task list failed: {tasks}")
    for task in tasks.get("tasks", []):
        if not isinstance(task, dict):
            continue
        payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
        execution_request = payload.get("execution_request") if isinstance(payload, dict) else {}
        if (
            task.get("task_type") == "collaborative_bridge"
            and task.get("status") == "approved"
            and isinstance(execution_request, dict)
            and execution_request.get("kind") == "allowlisted_command"
        ):
            return task
    return None


def post_state(relay_url: str, task_id: str, node_id: str, status: str, token: str = "") -> dict[str, Any]:
    return http_json(
        "POST",
        f"{relay_url.rstrip('/')}/tasks/{task_id}/state",
        {"node_id": node_id, "status": status},
        token=token,
    )


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def run_command(command: list[str], cwd: str, timeout: float, output_limit: int) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": truncate_text(completed.stdout, output_limit),
        "stderr": truncate_text(completed.stderr, output_limit),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one approved collaborative allowlisted command.")
    parser.add_argument("--relay-url", required=True)
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--node-id", default=NODE_ID)
    parser.add_argument("--project-root", default=os.getcwd())
    parser.add_argument("--commands-file", default="")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output-limit", type=int, default=12000)
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        print(json.dumps({
            "ok": False,
            "error": "project_root_not_found",
            "project_root": str(project_root),
        }, ensure_ascii=False, indent=2))
        return 1

    commands = load_commands(args.commands_file)
    task = find_approved_task(args.relay_url, args.node_id, token=args.token)
    if task is None:
        print(json.dumps({
            "ok": True,
            "task": None,
            "claim": "collaborative_bridge_command_worker_no_task",
            "cannot_claim": ["command_executed"],
        }, ensure_ascii=False, indent=2))
        return 0

    task_id = str(task.get("task_id"))
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    execution_request = payload.get("execution_request") if isinstance(payload, dict) else {}
    command_id = str(execution_request.get("command_id") if isinstance(execution_request, dict) else "")
    command = commands.get(command_id)
    if command is None:
        post_state(args.relay_url, task_id, args.node_id, "result_pending_review", token=args.token)
        print(json.dumps({
            "ok": False,
            "task_id": task_id,
            "command_id": command_id,
            "error": "command_id_not_allowlisted",
            "claim": "collaborative_bridge_command_worker_denied",
            "cannot_claim": ["command_executed"],
        }, ensure_ascii=False, indent=2))
        return 1

    post_state(args.relay_url, task_id, args.node_id, "sent_to_codex", token=args.token)
    post_state(args.relay_url, task_id, args.node_id, "running", token=args.token)
    try:
        result = run_command(command, str(project_root), args.timeout, args.output_limit)
    except subprocess.TimeoutExpired as exc:
        result = {
            "exit_code": None,
            "stdout": truncate_text(exc.stdout or "", args.output_limit) if isinstance(exc.stdout, str) else "",
            "stderr": "command_timeout",
        }
    except Exception as exc:  # noqa: BLE001 - returned as task result.
        result = {"exit_code": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}

    post_state(args.relay_url, task_id, args.node_id, "result_pending_review", token=args.token)
    posted = http_json(
        "POST",
        f"{args.relay_url.rstrip('/')}/tasks/{task_id}/result",
        {
            "node_id": args.node_id,
            "result": {
                "status": "ok" if result.get("exit_code") == 0 else "failed",
                "agent_message": f"Command {command_id} exited with {result.get('exit_code')}",
                "execution": "host_allowlisted_command",
                "command_id": command_id,
                "command": command,
                "project_root": str(project_root),
                **result,
            },
        },
        token=args.token,
    )
    if not posted.get("ok"):
        print(json.dumps({
            "ok": False,
            "task_id": task_id,
            "command_id": command_id,
            "response": posted,
            "claim": "collaborative_bridge_command_worker_submit_failed",
        }, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "ok": True,
        "task_id": task_id,
        "command_id": command_id,
        "exit_code": result.get("exit_code"),
        "claim": "collaborative_bridge_command_worker_executed",
        "cannot_claim": [
            "arbitrary_shell_execution",
            "hidden_background_control",
            "unapproved_execution",
            "production_ready_remote_control",
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
