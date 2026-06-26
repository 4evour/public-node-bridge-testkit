#!/usr/bin/env python3
"""Build the six Yuanjie acceptance cards from existing local node state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from node_bridge_testkit.avatar_runtime import DEFAULT_INSTALL_DIR, read_json, resolve_install_dir
from run_node_c_loop_readiness import build_loop_readiness
from yuanjie_avatar_workspace_card import build_workspace_card


CANNOT_CLAIM = [
    "real_codex_ipc",
    "task_sent_to_codex",
    "codex_reply_read",
    "frontstage_auto_injection",
    "formal_ack",
    "external_send",
    "file_execution",
    "persistent_service",
    "long_running_autonomy",
    "production_ready_connection",
    "full_loop",
    "global_experience_write",
]


def safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def latest_cache_record(root: Path) -> dict[str, Any] | None:
    cache_dir = root / "task_cache"
    if not cache_dir.exists():
        return None
    latest: dict[str, Any] | None = None
    latest_mtime = 0.0
    for path in cache_dir.glob("*.json"):
        record = safe_read_json(path)
        if not record:
            continue
        mtime = path.stat().st_mtime
        if mtime >= latest_mtime:
            latest_mtime = mtime
            latest = dict(record)
            latest["_cache_path"] = str(path)
    return latest


def approval_gate_from_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    result = record.get("result")
    if isinstance(result, dict) and isinstance(result.get("approval_gate"), dict):
        return result["approval_gate"]
    return None


def build_acceptance_cards(
    install_dir: str | Path = DEFAULT_INSTALL_DIR,
    avatar_id: str = "",
    project_id: str = "",
    owner: str = "",
) -> dict[str, Any]:
    root = resolve_install_dir(install_dir)
    workspace = build_workspace_card(
        install_dir=root,
        avatar_id=avatar_id,
        project_id=project_id,
        owner=owner,
    )
    readiness = build_loop_readiness(root)
    record = latest_cache_record(root)
    task = record.get("task") if isinstance(record, dict) else None
    result = record.get("result") if isinstance(record, dict) else None
    task_payload = task.get("payload") if isinstance(task, dict) else {}
    result_dict = result if isinstance(result, dict) else {}
    task_dict = task if isinstance(task, dict) else {}
    approval_gate = approval_gate_from_record(record)
    latest_status = str(record.get("status") or "") if isinstance(record, dict) else ""
    completed = latest_status in {"completed", "completed_local"} or result_dict.get("status") == "ok"
    blocked = readiness.get("readiness") in {"blocked_zombie_session", "busy"}

    node_card = {
        "schema": "yuanjie_node_card_v0.1",
        "avatar_id": workspace.get("avatar_id"),
        "node_id": workspace.get("node_id"),
        "project_id": workspace.get("project_id"),
        "owner": workspace.get("owner"),
        "role": workspace.get("role"),
        "workspace_path": workspace.get("workspace_path"),
        "status": workspace.get("status"),
        "allowed_tools": workspace.get("allowed_tools"),
        "permission_boundary": workspace.get("permission_boundary"),
    }

    task_card = {
        "schema": "yuanjie_task_card_v0.1",
        "task_id": record.get("task_id") if isinstance(record, dict) else None,
        "task_type": task_dict.get("task_type"),
        "target_node": task_dict.get("target_node"),
        "marker": record.get("marker") if isinstance(record, dict) else task_payload.get("marker"),
        "status": latest_status or None,
        "payload_summary": {
            "has_text": isinstance(task_payload.get("text"), str),
            "has_file": isinstance(task_payload.get("content_b64"), str),
            "filename": task_payload.get("filename"),
            "sha256": task_payload.get("sha256"),
        },
        "boundary": {
            "formal_ack": False,
            "external_send": False,
            "file_execution": False,
            "shell_execution": False,
        },
        "acceptance": {
            "expected_marker": task_payload.get("marker") or (record or {}).get("marker"),
            "requires_human_review": True,
        },
    }

    run_log = {
        "schema": "yuanjie_run_log_v0.1",
        "readiness": readiness.get("readiness"),
        "connection_state": readiness.get("connection_state"),
        "checks": readiness.get("checks"),
        "heartbeat_age_seconds": readiness.get("heartbeat_age_seconds"),
        "task_cache": readiness.get("task_cache"),
        "latest_cache_path": record.get("_cache_path") if isinstance(record, dict) else None,
        "latest_status": latest_status or None,
    }

    evidence_card = {
        "schema": "yuanjie_evidence_card_v0.1",
        "proof_level": "task_completed" if completed else "artifact_created" if record else "design_defined",
        "result_status": result_dict.get("status"),
        "agent_message": result_dict.get("agent_message"),
        "filename": result_dict.get("filename"),
        "bytes": result_dict.get("bytes"),
        "sha256": result_dict.get("sha256"),
        "saved_to": result_dict.get("saved_to"),
        "action": result_dict.get("action"),
        "line_count": result_dict.get("line_count"),
        "text_sha256": result_dict.get("text_sha256"),
        "execution": result_dict.get("execution"),
        "formal_ack": False,
        "cannot_claim": CANNOT_CLAIM,
    }

    review_panel = {
        "schema": "yuanjie_review_panel_v0.1",
        "review_state": "blocked" if blocked else "needs_human_review" if completed else "needs_more_evidence",
        "approval_gate": approval_gate,
        "options": [
            "pass",
            "need_more_evidence",
            "fail",
            "reject",
        ],
        "default_decision": "need_more_evidence",
        "reason": (
            "busy_or_zombie"
            if blocked
            else "machine_result_present_but_human_review_required"
            if completed
            else "missing_completed_result"
        ),
    }

    reuse_template = {
        "schema": "yuanjie_reuse_template_v0.1",
        "candidate_only": True,
        "reuse_key": {
            "node_id": workspace.get("node_id"),
            "task_type": task_dict.get("task_type"),
            "action": result_dict.get("action"),
            "marker_prefix": str((record or {}).get("marker") or "").split("-")[0] if record else "",
        },
        "positive_conditions": [
            "same permission boundary",
            "same allowlisted task type",
            "machine result completed",
            "human review accepted",
        ],
        "negative_brakes": [
            "formal_ack requested",
            "external_send requested",
            "file_execution requested",
            "session zombie or busy",
            "sha256 mismatch",
        ],
        "global_experience_write": False,
    }

    return {
        "schema": "yuanjie_acceptance_cards_v0.1",
        "install_dir": str(root),
        "cards": {
            "node_card": node_card,
            "task_card": task_card,
            "run_log": run_log,
            "evidence_card": evidence_card,
            "review_panel": review_panel,
            "reuse_template": reuse_template,
        },
        "claim": "yuanjie_acceptance_cards_created",
        "cannot_claim": CANNOT_CLAIM,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Yuanjie six acceptance cards.")
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--avatar-id", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--owner", default="")
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()

    cards = build_acceptance_cards(
        install_dir=args.install_dir,
        avatar_id=args.avatar_id,
        project_id=args.project_id,
        owner=args.owner,
    )
    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, card in cards["cards"].items():
            (out_dir / f"{name}.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / "acceptance_cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cards["written_to"] = str(out_dir)
    print(json.dumps(cards, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
