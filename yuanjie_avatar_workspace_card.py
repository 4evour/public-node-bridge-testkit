#!/usr/bin/env python3
"""Build a minimal Yuanjie avatar workspace card.

The workspace card is a read-only summary of one avatar's working seat:
identity, local workspace, input queue, artifact outbox, audit sources, and
experience candidates. It does not start services, send tasks, execute files,
or write to a global experience pool.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from node_bridge_testkit.avatar_runtime import DEFAULT_INSTALL_DIR, read_json, resolve_install_dir
from run_node_c_connection_state import list_cache


CANNOT_CLAIM = [
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
        return {"error": "invalid_json", "path": str(path)}


def list_recent_files(root: Path, relative: str, limit: int = 8) -> list[dict[str, Any]]:
    base = root / relative
    if not base.exists():
        return []
    files = [path for path in base.rglob("*") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    items: list[dict[str, Any]] = []
    for path in files[:limit]:
        items.append({
            "path": str(path),
            "bytes": path.stat().st_size,
            "mtime": path.stat().st_mtime,
        })
    return items


def module_slots(root: Path, cache: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    latest_task = cache.get("latest") if isinstance(cache, dict) else None
    return {
        "frame_source": {
            "status": "slot_ready",
            "input": "current_task + session_binding + local cache summary",
            "output": "thin task frame for the next slice",
            "claim": "module_slot_defined",
        },
        "task_slicer": {
            "status": "implemented_local",
            "entrypoint": "yuanjie_task_slicer.py",
            "latest_marker": (latest_task or {}).get("marker") if isinstance(latest_task, dict) else None,
            "claim": "local_tool_available",
        },
        "sensor": {
            "status": "implemented_local",
            "entrypoint": "run_node_c_connection_state.py",
            "signals": ["installed", "session_bound", "session_zombie", "task_cache"],
            "claim": "local_sensor_available",
        },
        "posture_equation": {
            "status": "slot_ready",
            "decision_values": ["advance", "brake", "recheck_evidence", "compress_frame", "observe"],
            "claim": "module_slot_defined",
        },
        "experience_yinyang": {
            "status": "candidate_only",
            "positive_source": "completed_local / task_complete_seen",
            "negative_source": "failed_local / timeout / zombie / boundary block",
            "global_pool_write": False,
            "claim": "candidate_slot_defined",
        },
        "low_cost_reuse": {
            "status": "slot_ready",
            "reuse_sources": ["task_cache", "rollout observation", "workspace card"],
            "claim": "module_slot_defined",
        },
        "reality_anchor": {
            "status": "active_boundary",
            "rule": "claims must follow machine evidence and cannot_claim",
            "claim": "boundary_rule_attached",
        },
        "immune_recovery": {
            "status": "slot_ready",
            "triggers": ["session_zombie", "in_progress_timeout", "sha256_mismatch", "missing_task_complete"],
            "claim": "module_slot_defined",
        },
        "workspace_paths": {
            "task_cache": str(root / "task_cache"),
            "task_inbox": str(root / "inbox"),
            "artifact_outbox": str(root / "artifact_outbox"),
            "session_binding": str(root / "session_binding.json"),
            "conversation_bound": bool(binding.get("conversation_id")),
        },
    }


def build_workspace_card(
    install_dir: str | Path = DEFAULT_INSTALL_DIR,
    avatar_id: str = "",
    project_id: str = "",
    owner: str = "",
    role: str = "external_node",
) -> dict[str, Any]:
    root = resolve_install_dir(install_dir)
    config = safe_read_json(root / "config.json") or {}
    state = safe_read_json(root / "state.json") or {}
    binding = safe_read_json(root / "session_binding.json") or {}
    node_id = str(config.get("node_id") or state.get("node_id") or avatar_id or "unknown")
    card_avatar_id = avatar_id or f"YJ-{node_id.upper()}"
    cache = list_cache(root)
    recent_inbox = list_recent_files(root, "inbox")
    recent_cache = list_recent_files(root, "task_cache")
    recent_artifacts = list_recent_files(root, "artifact_outbox")

    current_task = None
    latest = cache.get("latest") if isinstance(cache, dict) else None
    if isinstance(latest, dict):
        current_task = {
            "task_id": latest.get("task_id"),
            "task_type": latest.get("task_type"),
            "marker": latest.get("marker"),
            "status": latest.get("status"),
            "updated_at": latest.get("updated_at"),
        }

    return {
        "schema": "yuanjie_avatar_workspace_card_v0.1",
        "avatar_id": card_avatar_id,
        "project_id": project_id,
        "owner": owner,
        "role": role,
        "node_id": node_id,
        "workspace_path": str(root),
        "status": {
            "installed": bool((root / "config.json").exists()),
            "last_heartbeat_at": state.get("last_heartbeat_at"),
            "last_run_claim": state.get("last_run_claim"),
            "session_bound": bool(binding.get("conversation_id")),
            "conversation_id": binding.get("conversation_id"),
            "session_zombie": bool(binding.get("zombie")),
        },
        "allowed_tools": config.get("capabilities") or [],
        "permission_boundary": config.get("boundary") or {
            "external_send": False,
            "formal_ack": False,
            "file_execution": False,
        },
        "current_task": current_task,
        "input_queue": {
            "task_cache": cache,
            "recent_cache_files": recent_cache,
        },
        "task_inbox": {
            "path": str(root / "inbox"),
            "recent_files": recent_inbox,
        },
        "artifact_outbox": {
            "path": str(root / "artifact_outbox"),
            "recent_files": recent_artifacts,
            "note": "reserved; not used by this preflight unless future adapters write artifacts here",
        },
        "audit_log": {
            "session_binding": str(root / "session_binding.json"),
            "task_cache_dir": str(root / "task_cache"),
            "codex_rollout_source": ".codex/sessions (read by completion probe)",
        },
        "modules": module_slots(root, cache, binding),
        "experience_candidates": [],
        "claim": "yuanjie_avatar_workspace_card_created",
        "cannot_claim": CANNOT_CLAIM,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Yuanjie avatar workspace card.")
    parser.add_argument("--install-dir", default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--avatar-id", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--owner", default="")
    parser.add_argument("--role", default="external_node")
    parser.add_argument("--out", default="", help="Optional path to write the card JSON.")
    args = parser.parse_args()

    card = build_workspace_card(
        install_dir=args.install_dir,
        avatar_id=args.avatar_id,
        project_id=args.project_id,
        owner=args.owner,
        role=args.role,
    )
    if args.out:
        path = Path(args.out).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        card["written_to"] = str(path)
    print(json.dumps(card, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
