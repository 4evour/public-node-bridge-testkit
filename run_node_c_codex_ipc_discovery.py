#!/usr/bin/env python3
"""Read-only Codex Desktop IPC discovery for Windows.

This probe looks for process, port, and path hints only. It does not send a
task, read a Codex conversation, use the input box, click, paste, or press keys.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path


CODEX_PATTERNS = ("codex", "openai")


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


def ps_json(command: str, timeout: float = 20.0) -> list[dict[str, object]]:
    result = run_powershell(command, timeout=timeout)
    raw = str(result.get("stdout") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [{"raw": raw[-2000:], "parse_error": "json_decode_failed"}]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def redacted_path(path: str) -> str:
    text = str(path)
    home = str(Path.home())
    if home and text.lower().startswith(home.lower()):
        return "~" + text[len(home):]
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Windows Codex IPC discovery.")
    parser.add_argument("--include-ports", action="store_true", help="Also list listening localhost TCP ports.")
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        print(json.dumps({
            "ok": False,
            "platform": platform.system(),
            "stage": "platform",
            "error": "codex_ipc_discovery_is_windows_only",
            "claim": "node_c_codex_ipc_discovery_not_run",
            "cannot_claim": [
                "codex_desktop_ipc_found",
                "thread_follower_start_turn_found",
                "task_sent_to_codex",
                "codex_reply_read",
            ],
        }, ensure_ascii=False, indent=2))
        return 1

    process_query = r"""
$items = Get-Process | Where-Object {
  ($_.ProcessName -match 'codex|openai') -or ($_.MainWindowTitle -match 'Codex|OpenAI')
} | Select-Object Id,ProcessName,MainWindowTitle,Path
$items | ConvertTo-Json -Depth 3
"""
    processes = ps_json(process_query)
    for item in processes:
        if isinstance(item.get("Path"), str):
            item["Path"] = redacted_path(str(item["Path"]))

    path_query = r"""
$roots = @($env:APPDATA, $env:LOCALAPPDATA, $env:USERPROFILE)
$found = @()
foreach ($root in $roots) {
  if ($root -and (Test-Path $root)) {
    Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match 'Codex|OpenAI' } |
      ForEach-Object { $found += [PSCustomObject]@{ name=$_.Name; path=$_.FullName } }
  }
}
$found | ConvertTo-Json -Depth 3
"""
    paths = ps_json(path_query)
    for item in paths:
        if isinstance(item.get("path"), str):
            item["path"] = redacted_path(str(item["path"]))

    ports: list[dict[str, object]] = []
    if args.include_ports:
        port_query = r"""
$conns = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalAddress -eq '127.0.0.1' -or $_.LocalAddress -eq '::1' } |
  Select-Object LocalAddress,LocalPort,OwningProcess
$conns | ConvertTo-Json -Depth 3
"""
        ports = ps_json(port_query)

    process_seen = bool(processes)
    path_hint_found = bool(paths)
    ipc_hint_found = any(
        any(pattern in str(value).lower() for pattern in CODEX_PATTERNS)
        for item in processes + paths
        for value in item.values()
    )
    print(json.dumps({
        "ok": process_seen or path_hint_found,
        "platform": "Windows",
        "codex_process_seen": process_seen,
        "codex_path_hint_found": path_hint_found,
        "ipc_hint_found": ipc_hint_found,
        "candidate_processes": processes,
        "candidate_paths": paths,
        "candidate_local_listen_ports": ports,
        "claim": "node_c_codex_ipc_discovery_hints_found" if ipc_hint_found else "node_c_codex_ipc_discovery_no_hints",
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
    return 0 if process_seen or path_hint_found else 1


if __name__ == "__main__":
    raise SystemExit(main())
