#!/usr/bin/env python3
"""Read-only Windows probe that maps localhost ports to Codex processes.

This only correlates process IDs with listening TCP ports. It does not connect
to those ports, send tasks, read conversations, or automate the input box.
"""

from __future__ import annotations

import json
import platform
import subprocess


def run_powershell(command: str, timeout: float = 20.0) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            timeout=timeout,
            check=False,
            text=True,
            capture_output=True,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}


def main() -> int:
    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "stage": "platform",
            "error": "codex_port_owner_probe_is_windows_only",
            "claim": "node_c_codex_port_owner_probe_not_run",
            "cannot_claim": [
                "codex_desktop_ipc_found",
                "task_sent_to_codex",
                "codex_reply_read",
            ],
        }, ensure_ascii=False, indent=2))
        return 1

    command = r"""
$codex = Get-Process | Where-Object {
  ($_.ProcessName -match 'codex|openai') -or ($_.MainWindowTitle -match 'Codex|OpenAI')
} | Select-Object Id,ProcessName,MainWindowTitle,Path
$ports = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalAddress -eq '127.0.0.1' -or $_.LocalAddress -eq '::1' } |
  Select-Object LocalAddress,LocalPort,OwningProcess
$codexIds = @($codex | ForEach-Object { $_.Id })
$owned = @($ports | Where-Object { $codexIds -contains $_.OwningProcess })
$out = [PSCustomObject]@{
  codex_processes = $codex
  codex_owned_listen_ports = $owned
  localhost_listen_port_count = @($ports).Count
}
$out | ConvertTo-Json -Depth 5
"""
    result = run_powershell(command)
    raw = str(result.get("stdout") or "").strip()
    parsed: dict[str, object] = {}
    if raw:
        try:
            value = json.loads(raw)
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            parsed = {"raw": raw[-2000:], "parse_error": "json_decode_failed"}

    codex_processes = parsed.get("codex_processes") or []
    owned_ports = parsed.get("codex_owned_listen_ports") or []
    if isinstance(codex_processes, dict):
        codex_processes = [codex_processes]
    if isinstance(owned_ports, dict):
        owned_ports = [owned_ports]
    ok = bool(codex_processes)
    codex_port_owner_found = bool(owned_ports)

    print(json.dumps({
        "ok": ok,
        "platform": "Windows",
        "codex_process_count": len(codex_processes) if isinstance(codex_processes, list) else 0,
        "codex_port_owner_found": codex_port_owner_found,
        "codex_owned_listen_ports": owned_ports if isinstance(owned_ports, list) else [],
        "localhost_listen_port_count": parsed.get("localhost_listen_port_count", 0),
        "claim": "node_c_codex_owned_port_found" if codex_port_owner_found else "node_c_codex_process_seen_no_owned_port",
        "cannot_claim": [
            "codex_desktop_ipc_found",
            "thread_follower_start_turn_found",
            "task_sent_to_codex",
            "codex_reply_read",
            "frontstage_auto_injection",
            "input_box_automation",
            "formal_ack",
            "external_send",
            "file_execution",
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
