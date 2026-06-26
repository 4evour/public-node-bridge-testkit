#!/usr/bin/env python3
"""Preflight the caller-side relay result inbox."""

from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path
from typing import Any

from node_bridge_testkit.node_adapter import http_json, run_once
from node_bridge_testkit.relay import make_server
from pull_relay_result import DEFAULT_CANNOT_CLAIM, pull_result


def main() -> int:
    token = "local-return-token"
    node_id = "node-b"
    server = make_server("127.0.0.1", 0, quiet=True, token=token)
    port = server.server_address[1]
    relay = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            created = http_json(
                "POST",
                f"{relay}/tasks",
                {
                    "target_node": node_id,
                    "task_type": "reply_exactly",
                    "payload": {
                        "marker": "RETURN-INBOX-001",
                        "text": "STATUS=RETURN_INBOX_OK; MARKER=RETURN_INBOX_001; NEXT=RESULT_PULL_READY",
                    },
                },
                token=token,
            )
            task_id = str((created.get("task") or {}).get("task_id", ""))
            adapter_result = run_once(relay, node_id, token=token, sandbox_dir=root / ".node_avatar")
            pulled = pull_result(
                relay,
                task_id,
                token=token,
                node_id=node_id,
                out_dir=root / ".node_bridge_returns",
            )
            saved_to = Path(str(pulled.get("saved_to", "")))
            record: dict[str, Any] = {}
            if saved_to.exists():
                record = json.loads(saved_to.read_text(encoding="utf-8"))
            ok = (
                bool(created.get("ok"))
                and bool(adapter_result.get("ok"))
                and bool(pulled.get("ok"))
                and saved_to.exists()
                and (record.get("result") or {}).get("agent_message")
                == "STATUS=RETURN_INBOX_OK; MARKER=RETURN_INBOX_001; NEXT=RESULT_PULL_READY"
            )
            print(json.dumps({
                "ok": ok,
                "relay": relay,
                "node_id": node_id,
                "task_id": task_id,
                "saved_to": str(saved_to) if saved_to.exists() else "",
                "agent_message": (record.get("result") or {}).get("agent_message"),
                "claim": "relay_result_inbox_preflight_passed" if ok else "relay_result_inbox_preflight_failed",
                "cannot_claim": DEFAULT_CANNOT_CLAIM,
            }, ensure_ascii=False, indent=2))
            return 0 if ok else 1
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
