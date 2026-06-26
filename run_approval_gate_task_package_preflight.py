#!/usr/bin/env python3
"""Verify Host Approval Gate metadata survives a safe local task package."""

from __future__ import annotations

import base64
import hashlib
import json

from node_bridge_testkit.node_adapter import execute_task


def main() -> int:
    package = {
        "schema": "yuanjie_task_package_v0.1",
        "marker": "APPROVAL-GATE-PACKAGE-001",
        "action": "count_lines",
        "input_text": "gate\nboundary\nresult\n",
        "expected_line_count": 3,
        "boundary": {
            "shell_execution": False,
            "file_execution": False,
            "external_send": False,
            "formal_ack": False,
        },
        "approval_gate": {
            "gate_id": "HOST_APPROVAL_GATE_V1",
            "status": "approved_once",
            "avatar_id": "YJ-NODEB-KEZONG-001",
            "project_id": "KZ001",
            "risk_level": "low",
            "risk_summary": "Local preflight only; allowlisted task package; no file execution or external send.",
            "requested_capabilities": ["task_package"],
            "denied_capabilities": [
                "shell_execution",
                "arbitrary_file_write",
                "file_execution",
                "external_send",
                "formal_ack",
            ],
            "host_decision": {
                "decision": "approve_once",
                "reason": "local preflight only",
            },
            "cannot_claim": [
                "formal_ack",
                "external_send",
                "production_ready_connection",
                "long_running_autonomy",
            ],
        },
    }
    raw = json.dumps(package, ensure_ascii=False, indent=2).encode("utf-8")
    task = {
        "task_id": "task_approval_gate_package",
        "target_node": "node-c",
        "task_type": "task_package",
        "payload": {
            "marker": package["marker"],
            "filename": "approval_gate_task_package_001.json",
            "content_b64": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
    }
    result = execute_task(task, "node-c", sandbox_dir=".node_c_avatar")
    gate = result.get("approval_gate") if isinstance(result.get("approval_gate"), dict) else {}
    ok = (
        result.get("status") == "ok"
        and result.get("execution") == "local_adapter_task_package_execute_allowlist"
        and result.get("action") == "count_lines"
        and result.get("line_count") == 3
        and gate.get("present") is True
        and gate.get("gate_id") == "HOST_APPROVAL_GATE_V1"
        and gate.get("status") == "approved_once"
        and gate.get("decision") == "approve_once"
        and "formal_ack" in gate.get("cannot_claim", [])
        and "external_send" in gate.get("denied_capabilities", [])
    )
    print(json.dumps({
        "ok": ok,
        "result": result,
        "claim": "approval_gate_task_package_local_preflight_passed" if ok else "approval_gate_task_package_local_preflight_failed",
        "cannot_claim": [
            "real_approval_ui",
            "real_codex_ipc",
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
