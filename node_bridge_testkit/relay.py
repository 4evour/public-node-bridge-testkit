#!/usr/bin/env python3
"""Local relay for the public node bridge testkit.

The relay is intentionally in-memory and local-first. It supports only
allowlisted light tasks so contributors can verify the protocol without using
Yuanjie private infrastructure.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import parse_qs, urlparse


ALLOWED_TASK_TYPES = {"reply_exactly", "file_deliver", "task_package", "desktop_manual_exact"}


@dataclass
class Task:
    task_id: str
    target_node: str
    task_type: str
    payload: dict[str, Any]
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    claimed_at: float | None = None
    completed_at: float | None = None
    result: dict[str, Any] | None = None


class RelayState:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()

    def create_task(self, target_node: str, task_type: str, payload: dict[str, Any]) -> Task:
        if task_type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"task_type not allowed: {task_type}")
        if task_type == "reply_exactly" and not isinstance(payload.get("text"), str):
            raise ValueError("reply_exactly requires payload.text")
        if task_type == "file_deliver":
            if not isinstance(payload.get("filename"), str):
                raise ValueError("file_deliver requires payload.filename")
            if not isinstance(payload.get("content_b64"), str):
                raise ValueError("file_deliver requires payload.content_b64")
            if not isinstance(payload.get("sha256"), str):
                raise ValueError("file_deliver requires payload.sha256")
        if task_type == "task_package":
            if not isinstance(payload.get("filename"), str):
                raise ValueError("task_package requires payload.filename")
            if not isinstance(payload.get("content_b64"), str):
                raise ValueError("task_package requires payload.content_b64")
            if not isinstance(payload.get("sha256"), str):
                raise ValueError("task_package requires payload.sha256")
        if task_type == "desktop_manual_exact":
            if not isinstance(payload.get("prompt"), str):
                raise ValueError("desktop_manual_exact requires payload.prompt")
            if not isinstance(payload.get("expected"), str):
                raise ValueError("desktop_manual_exact requires payload.expected")
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            target_node=target_node,
            task_type=task_type,
            payload=payload,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def poll(self, node_id: str) -> Task | None:
        with self._lock:
            for task in self._tasks.values():
                if task.target_node == node_id and task.status == "queued":
                    task.status = "in_progress"
                    task.claimed_at = time.time()
                    return task
        return None

    def complete(self, task_id: str, node_id: str, result: dict[str, Any]) -> Task:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            if task.target_node != node_id:
                raise PermissionError("node_id does not own task")
            task.status = "completed"
            task.completed_at = time.time()
            task.result = result
            return task

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, node_id: str = "", status: str = "", summary: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())
        rows: list[dict[str, Any]] = []
        for task in tasks:
            if node_id and task.target_node != node_id:
                continue
            if status and task.status != status:
                continue
            if summary:
                rows.append({
                    "task_id": task.task_id,
                    "target_node": task.target_node,
                    "task_type": task.task_type,
                    "status": task.status,
                    "created_at": task.created_at,
                    "claimed_at": task.claimed_at,
                    "completed_at": task.completed_at,
                })
            else:
                rows.append(asdict(task))
        return rows

    def stats(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {"queued": 0, "in_progress": 0, "completed": 0}
            for task in self._tasks.values():
                counts[task.status] = counts.get(task.status, 0) + 1
            return {"tasks": len(self._tasks), "by_status": counts}


def response_from_task(task: Task | None) -> dict[str, Any]:
    if task is None:
        return {"ok": True, "task": None}
    return {"ok": True, "task": asdict(task)}


class RelayHandler(BaseHTTPRequestHandler):
    state: RelayState = RelayState()

    server_version = "NodeBridgeTestkitRelay/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid json: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("json body must be an object")
        return data

    def _write_json(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _write_html(self, status: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _token(self) -> str:
        return str(getattr(self.server, "token", "") or "")

    def _authorized(self) -> bool:
        token = self._token()
        if not token:
            return True
        supplied = self.headers.get("X-Node-Bridge-Token", "")
        return supplied == token

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._write_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "forbidden"})
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._write_json(HTTPStatus.OK, {
                "ok": True,
                "service": "node-bridge-testkit-relay",
                "auth_required": bool(self._token()),
            })
            return
        if parsed.path == "/dashboard":
            self._write_html(HTTPStatus.OK, self._dashboard_html())
            return
        if parsed.path == "/stats":
            if not self._require_auth():
                return
            self._write_json(HTTPStatus.OK, {"ok": True, "stats": self.state.stats()})
            return
        if parsed.path == "/tasks":
            if not self._require_auth():
                return
            node_id = query.get("node_id", [""])[0]
            status = query.get("status", [""])[0]
            summary = query.get("format", [""])[0] == "summary"
            self._write_json(HTTPStatus.OK, {
                "ok": True,
                "tasks": self.state.list_tasks(node_id=node_id, status=status, summary=summary),
            })
            return
        if parsed.path == "/poll":
            if not self._require_auth():
                return
            node_id = query.get("node_id", [""])[0]
            if not node_id:
                self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing node_id"})
                return
            self._write_json(HTTPStatus.OK, response_from_task(self.state.poll(node_id)))
            return
        if parsed.path.startswith("/tasks/"):
            if not self._require_auth():
                return
            task_id = parsed.path.rsplit("/", 1)[-1]
            task = self.state.get(task_id)
            if task is None:
                self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "task_not_found"})
                return
            self._write_json(HTTPStatus.OK, {"ok": True, "task": asdict(task)})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def _dashboard_html(self) -> str:
        title = html.escape("Node Bridge Dashboard")
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #1f2937; }}
    header {{ display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; }}
    input {{ padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 260px; }}
    .stats {{ display: flex; gap: 10px; margin: 18px 0; flex-wrap: wrap; }}
    .pill {{ border-radius: 999px; padding: 6px 10px; background: #f1f5f9; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; position: sticky; top: 0; }}
    tr {{ cursor: pointer; }}
    .queued {{ color: #64748b; font-weight: 700; }}
    .in_progress {{ color: #2563eb; font-weight: 700; }}
    .completed {{ color: #059669; font-weight: 700; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 8px; max-height: 320px; overflow: auto; }}
    .muted {{ color: #64748b; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Node Bridge Dashboard</h1>
      <div class="muted">Local relay task queue. Refreshes every second.</div>
    </div>
    <label>Token <input id="token" placeholder="optional token"></label>
  </header>
  <div class="stats" id="stats"></div>
  <table>
    <thead><tr><th>task_id</th><th>node</th><th>type</th><th>status</th><th>created</th></tr></thead>
    <tbody id="tasks"><tr><td colspan="5">Loading...</td></tr></tbody>
  </table>
  <h2>Task detail</h2>
  <pre id="detail">Click a task row.</pre>
  <script>
    const tokenInput = document.getElementById('token');
    tokenInput.value = localStorage.getItem('node_bridge_token') || '';
    tokenInput.addEventListener('input', () => localStorage.setItem('node_bridge_token', tokenInput.value));
    function headers() {{
      const token = tokenInput.value.trim();
      return token ? {{'X-Node-Bridge-Token': token}} : {{}};
    }}
    function ts(value) {{
      return value ? new Date(value * 1000).toLocaleTimeString() : '';
    }}
    async function getJson(url) {{
      const res = await fetch(url, {{headers: headers()}});
      if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
      return await res.json();
    }}
    async function refresh() {{
      try {{
        const [stats, tasks] = await Promise.all([
          getJson('/stats'),
          getJson('/tasks?format=summary')
        ]);
        const s = stats.stats || {{}};
        const by = s.by_status || {{}};
        document.getElementById('stats').innerHTML =
          `<span class="pill">total: ${{s.tasks || 0}}</span>` +
          `<span class="pill queued">queued: ${{by.queued || 0}}</span>` +
          `<span class="pill in_progress">in_progress: ${{by.in_progress || 0}}</span>` +
          `<span class="pill completed">completed: ${{by.completed || 0}}</span>`;
        const rows = tasks.tasks || [];
        document.getElementById('tasks').innerHTML = rows.length ? rows.map(t =>
          `<tr data-id="${{t.task_id}}"><td>${{t.task_id}}</td><td>${{t.target_node}}</td><td>${{t.task_type}}</td>` +
          `<td class="${{t.status}}">${{t.status}}</td><td>${{ts(t.created_at)}}</td></tr>`
        ).join('') : '<tr><td colspan="5">No tasks</td></tr>';
        document.querySelectorAll('tr[data-id]').forEach(row => {{
          row.onclick = async () => {{
            const data = await getJson('/tasks/' + row.dataset.id);
            document.getElementById('detail').textContent = JSON.stringify(data.task.result || data.task, null, 2);
          }};
        }});
      }} catch (err) {{
        document.getElementById('stats').innerHTML = `<span class="pill">error: ${{err.message}}</span>`;
      }}
    }}
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>"""

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not self._require_auth():
            return
        try:
            body = self._read_json()
            if parsed.path == "/tasks":
                task = self.state.create_task(
                    target_node=str(body.get("target_node", "")),
                    task_type=str(body.get("task_type", "")),
                    payload=dict(body.get("payload", {})),
                )
                self._write_json(HTTPStatus.CREATED, {"ok": True, "task": asdict(task)})
                return
            if parsed.path.startswith("/tasks/") and parsed.path.endswith("/result"):
                parts = parsed.path.strip("/").split("/")
                task_id = parts[1]
                task = self.state.complete(
                    task_id=task_id,
                    node_id=str(body.get("node_id", "")),
                    result=dict(body.get("result", {})),
                )
                self._write_json(HTTPStatus.OK, {"ok": True, "task": asdict(task)})
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except KeyError:
            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "task_not_found"})
        except PermissionError as exc:
            self._write_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": str(exc)})


def make_server(host: str, port: int, quiet: bool = False, token: str = "") -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), RelayHandler)
    server.quiet = quiet  # type: ignore[attr-defined]
    server.token = token  # type: ignore[attr-defined]
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local node bridge relay.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.environ.get("NODE_BRIDGE_TOKEN", ""))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    server = make_server(args.host, args.port, quiet=args.quiet, token=args.token)
    print(f"relay_listening=http://{args.host}:{args.port}")
    print(f"auth_required={str(bool(args.token)).lower()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("relay_stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
