# Public Node Bridge Testkit

A tiny local-first testkit for verifying light-task Agent-to-Agent node flow.

It is designed for people who want to test the idea without trusting a private
server or installing a full agent runtime.

## What It Proves

This public testkit proves only:

```text
relay can accept a light task
mock node can poll the task
mock node can return a structured result
caller can verify the exact result
```

It does not prove:

```text
real Codex Desktop IPC
real external node connection
formal ACK
external message sending
file execution
long-running autonomy
```

## Quickstart

Requirements:

```text
Python 3.10+
No third-party packages
```

Run the full local demo:

```bash
python3 run_local_demo.py
```

Expected output includes:

```json
{
  "ok": true,
  "claim": "local_public_testkit_l0_l1_passed"
}
```

Run the Node-C local adapter preflight:

```bash
python3 run_node_c_preflight.py
```

On Windows, `py` is also fine:

```powershell
py run_node_c_preflight.py
```

Expected output includes:

```json
{
  "ok": true,
  "node_id": "node-c",
  "claim": "node_c_local_adapter_preflight_passed"
}
```

Install and run the local-only Node-C avatar:

```bash
python3 install_node_c_avatar.py
python3 run_node_c_avatar.py
```

On Windows:

```powershell
py install_node_c_avatar.py
py run_node_c_avatar.py
```

Expected output from the run step includes:

```json
{
  "ok": true,
  "node_id": "node-c",
  "claim": "node_c_avatar_installer_local_run_passed"
}
```

Run the remote relay simulation locally:

```bash
python3 run_remote_relay_demo.py
```

This proves token-protected remote relay semantics on localhost before using a
real public relay.

## Want To Help Test?

If you want to help test external AI node collaboration, open a GitHub issue
using the `Tester sign-up` template.

You do not need to understand the full project. The first useful test is only:

```bash
python3 run_local_demo.py
```

The second useful test is:

```bash
python3 run_node_c_preflight.py
```

The third useful test is:

```bash
python3 install_node_c_avatar.py
python3 run_node_c_avatar.py
```

The fourth useful test, when the maintainer provides a relay URL and token, is:

```bash
python3 run_node_c_remote_client.py --relay-url RELAY_URL --token TOKEN
```

On Windows:

```powershell
py run_node_c_remote_client.py --relay-url RELAY_URL --token TOKEN
```

Please include:

```text
OS
Python version
Whether the demo prints ok=true
Any error output
```

Do not post WeChat QR codes, phone numbers, private tokens, account cookies,
private screenshots, or internal endpoint details in GitHub issues. If a test
needs private coordination, the maintainer will follow up after reviewing the
issue.

## Manual Local Run

Terminal 1:

```bash
python3 -m node_bridge_testkit.relay --port 8765
```

Terminal 2:

```bash
python3 -m node_bridge_testkit.mock_node --node-id node-b
```

Terminal 3:

```bash
curl -sS -X POST http://127.0.0.1:8765/tasks \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "target_node": "node-b",
    "task_type": "reply_exactly",
    "payload": {
      "marker": "L0-OK",
      "text": "OK"
    }
  }'
```

Then read the returned `task_id`:

```bash
curl -sS http://127.0.0.1:8765/tasks/TASK_ID
```

## Safe Task Types

V0.1 supports:

```text
reply_exactly
file_deliver
```

Example:

```json
{
  "target_node": "node-b",
  "task_type": "reply_exactly",
  "payload": {
    "marker": "PUBLIC_L1",
    "text": "STATUS=READ_OK; MARKER=PUBLIC_L1; NEXT=SMALL_TASK"
  }
}
```

The mock node returns exactly:

```json
{
  "status": "ok",
  "agent_message": "STATUS=READ_OK; MARKER=PUBLIC_L1; NEXT=SMALL_TASK",
  "execution": "mock_reply_exactly"
}
```

The Node-C adapter can be run manually too:

```bash
python3 -m node_bridge_testkit.node_adapter --node-id node-c
```

It supports `reply_exactly` and sandboxed `file_deliver`. It still denies shell
execution, file execution, arbitrary file access, external sends, and private
endpoint routing.

For `file_deliver`, Node-C writes only the provided small payload into:

```text
.node_c_avatar/inbox/<task_id>/
```

The result returns filename, byte count, SHA-256, and saved path.

## Node-C Avatar Installer

The installer creates only local testkit state in `.node_c_avatar/`:

```text
.node_c_avatar/config.json
.node_c_avatar/state.json
```

The run step returns:

```text
health
heartbeat
capabilities
allowed_task_types
denied_capabilities
structured light-task results
```

It is not a persistent background service yet. It is a user-like installer
preflight for the next stage.

## Remote Relay Preflight

The remote preflight uses two scripts:

Maintainer side:

```bash
python3 send_node_c_remote_probe.py --relay-url RELAY_URL --token TOKEN
```

Tester side:

```bash
python3 run_node_c_remote_client.py --relay-url RELAY_URL --token TOKEN
```

The relay can be started with token protection:

```bash
NODE_BRIDGE_TOKEN=TOKEN python3 -m node_bridge_testkit.relay --host 0.0.0.0 --port 8765
```

The maintainer can also queue a file-channel preflight:

```bash
python3 send_node_c_file_probe.py --relay-url RELAY_URL --token TOKEN
```

The tester still runs the same client command. This proves only sandboxed file
delivery with SHA-256 verification. It does not prove real Codex IPC, formal
ACK, external send, file execution, persistent service, or long-running
autonomy.

## Codex CLI Local Probe

After remote relay and sandbox file-channel tests pass, a tester can check
whether their machine has a callable Codex CLI:

```bash
python3 run_node_c_codex_cli_probe.py
```

On Windows:

```powershell
py run_node_c_codex_cli_probe.py
```

If detection passes and the tester agrees to run a tiny model call:

```bash
python3 run_node_c_codex_cli_probe.py --execute
```

On Windows:

```powershell
py run_node_c_codex_cli_probe.py --execute
```

Expected exact reply:

```text
NODEC_CODEX_CLI_OK_001
```

This proves only local Codex CLI availability and one exact tiny reply. It does
not prove Codex Desktop IPC, frontstage session injection, formal ACK, external
send, file execution, persistent service, or long-running autonomy.

## Codex Desktop Manual Bridge Probe

If the tester uses Codex Desktop instead of Codex CLI, the next safe preflight is
manual:

```bash
python3 run_node_c_desktop_manual_client.py --relay-url RELAY_URL --token TOKEN
```

On Windows:

```powershell
py run_node_c_desktop_manual_client.py --relay-url RELAY_URL --token TOKEN
```

The script prints a prompt. The tester manually sends that prompt to Codex
Desktop, then pastes the exact Desktop reply back into the script.

This proves only that a relay task can be handed to a human-operated Codex
Desktop session and returned through Node-C. It does not prove Codex Desktop
IPC, automatic frontstage injection, formal ACK, external send, file execution,
persistent service, or long-running autonomy.

## Boundaries

This testkit intentionally does not:

```text
run shell commands
open arbitrary local files
execute received files
send external messages
install packages
touch private data
connect to Yuanjie private infrastructure
expose Aliyun routes, tokens, or IPC internals
```

## How To Report A Result

Open an issue with the `L0/L1 local demo result` template and include:

```text
OS
Python version
Command run
Full output
Whether ok=true appeared
```

Do not include private tokens, screenshots with private data, or credentials.

## Roadmap

```text
V0.1 local relay + mock node + L0/L1 demo
V0.2 Node-C local adapter preflight
V0.3 Node-C avatar installer preflight
V0.4 remote relay token preflight
V0.5 real agent adapter interface
V0.6 download-only file channel preflight
```

The public testkit stays separate from Yuanjie core.
