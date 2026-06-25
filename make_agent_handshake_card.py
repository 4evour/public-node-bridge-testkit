#!/usr/bin/env python3
"""Create an agent-readable Yuanjie handshake card.

The card is plain text on purpose. A QR code can carry the same text later, but
the protocol should not depend on image recognition.
"""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote


DEFAULT_CAPABILITIES = "reply_exactly,file_deliver,task_package"
DEFAULT_BOUNDARY = "no_shell,no_file_execution,no_external_send,no_formal_ack"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def compact_payload(values: dict[str, str]) -> str:
    parts = ["YJ1"]
    for key in (
        "session_id",
        "relay",
        "node_id",
        "role",
        "connect_code",
        "capabilities",
        "boundary",
        "expires_at",
    ):
        parts.append(f"{key}={quote(values[key], safe='')}")
    return "|".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Yuanjie agent handshake card.")
    parser.add_argument("--relay-url", required=True)
    parser.add_argument("--connect-code", required=True)
    parser.add_argument("--node-id", default="node-c")
    parser.add_argument("--role", default="external_node")
    parser.add_argument("--capabilities", default=DEFAULT_CAPABILITIES)
    parser.add_argument("--boundary", default=DEFAULT_BOUNDARY)
    parser.add_argument("--expires-minutes", type=int, default=30)
    parser.add_argument("--out-dir", default=".yuanjie_handshake")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    session_id = f"yj_{utc_now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
    expires_at = (utc_now() + timedelta(minutes=args.expires_minutes)).isoformat(timespec="seconds")
    values = {
        "session_id": session_id,
        "relay": args.relay_url.rstrip("/"),
        "node_id": args.node_id,
        "role": args.role,
        "connect_code": args.connect_code,
        "capabilities": args.capabilities,
        "boundary": args.boundary,
        "expires_at": expires_at,
    }
    card = "\n".join([
        "YUANJIE_HANDSHAKE_V1",
        f"session_id={values['session_id']}",
        f"relay={values['relay']}",
        f"node_id={values['node_id']}",
        f"role={values['role']}",
        f"connect_code={values['connect_code']}",
        f"capabilities={values['capabilities']}",
        f"boundary={values['boundary']}",
        f"expires_at={values['expires_at']}",
        "",
    ])
    qr_payload = compact_payload(values) + "\n"
    card_path = out_dir / "yuanjie_handshake_card.txt"
    qr_payload_path = out_dir / "qr_payload.txt"
    command_path = out_dir / "run_connect_node.txt"
    manifest_path = out_dir / "manifest.json"

    write_text(card_path, card)
    write_text(qr_payload_path, qr_payload)
    write_text(command_path, f"py connect_node.py --card-file {card_path} --timeout 90\n")
    write_text(manifest_path, json.dumps({
        "ok": True,
        "schema": "yuanjie_handshake_card_manifest_v0.1",
        "session_id": session_id,
        "card_path": str(card_path),
        "qr_payload_path": str(qr_payload_path),
        "command_path": str(command_path),
        "expires_at": expires_at,
        "claim": "agent_handshake_card_created",
        "cannot_claim": [
            "qr_code_created",
            "agent_qr_read",
            "real_codex_ipc",
            "formal_ack",
            "external_send",
            "production_ready_connection",
        ],
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "ok": True,
        "session_id": session_id,
        "card_path": str(card_path),
        "qr_payload_path": str(qr_payload_path),
        "command_path": str(command_path),
        "manifest_path": str(manifest_path),
        "claim": "agent_handshake_card_created",
        "cannot_claim": [
            "qr_code_created",
            "agent_qr_read",
            "real_codex_ipc",
            "formal_ack",
            "external_send",
            "production_ready_connection",
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
