#!/usr/bin/env python3
"""Validate the avatar workspace card with a temporary local avatar."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from node_bridge_testkit.avatar_runtime import install_avatar
from node_bridge_testkit.node_adapter import write_task_cache
from yuanjie_avatar_workspace_card import build_workspace_card


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="yuanjie_workspace_card_"))
    try:
        install_avatar(node_id="node-c", install_dir=root)
        task = {
            "task_id": "task_workspace_card_001",
            "target_node": "node-c",
            "task_type": "reply_exactly",
            "payload": {
                "marker": "WORKSPACE-CARD-001",
                "text": "STATUS=WORKSPACE_CARD_OK",
            },
        }
        write_task_cache(root, task, "pulled")
        card = build_workspace_card(
            install_dir=root,
            avatar_id="YJ-NODEC-TEST-001",
            project_id="public-node-bridge-testkit",
            owner="tester",
        )
        ok = (
            card.get("schema") == "yuanjie_avatar_workspace_card_v0.1"
            and card.get("avatar_id") == "YJ-NODEC-TEST-001"
            and (card.get("current_task") or {}).get("marker") == "WORKSPACE-CARD-001"
            and (card.get("modules") or {}).get("task_slicer", {}).get("status") == "implemented_local"
            and (card.get("modules") or {}).get("experience_yinyang", {}).get("global_pool_write") is False
            and "formal_ack" in card.get("cannot_claim", [])
        )
        print(json.dumps({
            "ok": ok,
            "avatar_id": card.get("avatar_id"),
            "current_task": card.get("current_task"),
            "module_keys": sorted((card.get("modules") or {}).keys()),
            "claim": "yuanjie_avatar_workspace_card_preflight_passed" if ok else "yuanjie_avatar_workspace_card_preflight_failed",
            "cannot_claim": card.get("cannot_claim"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
