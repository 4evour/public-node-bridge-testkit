#!/usr/bin/env python3
"""Validate six Yuanjie acceptance cards with a temporary local avatar."""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from node_bridge_testkit.avatar_runtime import install_avatar, now_utc, update_state, write_json
from node_bridge_testkit.node_adapter import execute_task, write_task_cache
from yuanjie_acceptance_cards import build_acceptance_cards


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="yuanjie_acceptance_cards_"))
    try:
        install_avatar(node_id="node-c", install_dir=root)
        state = json.loads((root / "state.json").read_text(encoding="utf-8"))
        update_state(root, state, "acceptance_cards_preflight_heartbeat")
        write_json(root / "session_binding.json", {
            "schema": "node_c_session_binding_v0.1",
            "node_id": "node-c",
            "conversation_id": "acceptance-card-conversation",
            "bound_at": now_utc(),
            "zombie": False,
            "runtime_status": {"runtime": "idle", "last_turn_status": "completed"},
        })
        package = {
            "schema": "yuanjie_task_package_v0.1",
            "marker": "ACCEPTANCE-CARDS-001",
            "action": "count_lines",
            "input_text": "node\ntask\nevidence\n",
            "approval_gate": {
                "gate_id": "HOST_APPROVAL_GATE_V1",
                "status": "approved_once",
                "host_decision": {"decision": "approve_once"},
                "cannot_claim": ["formal_ack", "external_send", "production_ready_connection"],
            },
        }
        raw = json.dumps(package, ensure_ascii=False, indent=2).encode("utf-8")
        task = {
            "task_id": "task_acceptance_cards_001",
            "target_node": "node-c",
            "task_type": "task_package",
            "payload": {
                "marker": "ACCEPTANCE-CARDS-001",
                "filename": "approval_gate_acceptance_cards_001.json",
                "content_b64": base64.b64encode(raw).decode("ascii"),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
        }
        write_task_cache(root, task, "pulled")
        result = execute_task(task, "node-c", sandbox_dir=root)
        write_task_cache(root, task, "completed_local", result=result, posted={"ok": True})
        cards = build_acceptance_cards(
            install_dir=root,
            avatar_id="YJ-NODEC-TEST-001",
            project_id="public-node-bridge-testkit",
            owner="tester",
        )
        card_map = cards.get("cards") or {}
        ok = (
            cards.get("schema") == "yuanjie_acceptance_cards_v0.1"
            and sorted(card_map.keys()) == [
                "evidence_card",
                "node_card",
                "reuse_template",
                "review_panel",
                "run_log",
                "task_card",
            ]
            and card_map["node_card"].get("avatar_id") == "YJ-NODEC-TEST-001"
            and card_map["task_card"].get("marker") == "ACCEPTANCE-CARDS-001"
            and card_map["evidence_card"].get("line_count") == 3
            and card_map["review_panel"].get("approval_gate", {}).get("gate_id") == "HOST_APPROVAL_GATE_V1"
            and card_map["reuse_template"].get("candidate_only") is True
            and "formal_ack" in cards.get("cannot_claim", [])
        )
        print(json.dumps({
            "ok": ok,
            "card_keys": sorted(card_map.keys()),
            "node_card": card_map.get("node_card"),
            "task_card": card_map.get("task_card"),
            "evidence_card": card_map.get("evidence_card"),
            "review_state": card_map.get("review_panel", {}).get("review_state"),
            "claim": "yuanjie_acceptance_cards_preflight_passed" if ok else "yuanjie_acceptance_cards_preflight_failed",
            "cannot_claim": cards.get("cannot_claim"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
