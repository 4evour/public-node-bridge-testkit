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
python3 connect_node.py --relay-url RELAY_URL --token TOKEN
```

On Windows:

```powershell
py connect_node.py --relay-url RELAY_URL --token TOKEN
```

`connect_node.py` installs the local Node-C avatar if needed, reports health,
polls the relay, completes one queued safe task, and prints one JSON result.
It now prints progress lines to stderr by default (`[config]`, `[health]`,
`[poll #N]`, `[task]`, `[submit]`) so the terminal does not look stuck while it
waits for a relay task. Use `--quiet` when a machine-readable run needs only the
final JSON.

You can also connect from an agent-readable handshake card:

```bash
python3 connect_node.py --card-file yuanjie_handshake_card.txt --timeout 90
```

On Windows:

```powershell
py connect_node.py --card-file yuanjie_handshake_card.txt --timeout 90
```

Generate a plain-text handshake card:

```bash
python3 make_agent_handshake_card.py --relay-url RELAY_URL --connect-code TOKEN
```

This creates:

```text
.yuanjie_handshake/yuanjie_handshake_card.txt
.yuanjie_handshake/qr_payload.txt
.yuanjie_handshake/run_connect_node.txt
```

The card starts with `YUANJIE_HANDSHAKE_V1`. A QR code may later carry the exact
same text, but the protocol itself remains text-first so agents that cannot
read images can still connect.
`qr_payload.txt` contains the compressed single-line agent handshake form:

```text
YJ1|session_id=...|relay=...|node_id=...|connect_code=...|capabilities=...|boundary=...|expires_at=...
```

This is the intended QR payload. An agent can decode the QR into this text and
pass it directly to `connect_node.py --card "YJ1|..."` without changing the
connection protocol.

Run the local task-package preflight:

```bash
python3 run_node_c_task_package_preflight.py
```

On Windows:

```powershell
py run_node_c_task_package_preflight.py
```

This only executes allowlisted package actions on package-contained text. It
does not run shell commands, execute local files, read private files, or send
messages.

Run the local handshake-card parser preflight:

```bash
python3 run_agent_handshake_card_preflight.py
```

On Windows, after opening Codex Desktop, run the read-only desktop-visible
preflight:

```powershell
py run_node_c_desktop_visible_preflight.py
```

This only checks whether a visible window title matches `Codex`. It does not
click, type, inject a task, or read a conversation.

Run the read-only Windows Codex IPC discovery probe:

```powershell
py run_node_c_codex_ipc_discovery.py
```

Optional local listening-port hints:

```powershell
py run_node_c_codex_ipc_discovery.py --include-ports
```

This only reports process, path, and optional localhost port hints. It does not
use the input box, send a task, read a conversation, or claim IPC support.

If port hints exist, map localhost ports back to Codex process IDs:

```powershell
py run_node_c_codex_port_owner_probe.py
```

This only correlates PIDs and ports. It does not connect to any port or claim
IPC support.

If no Codex-owned port is found, inspect read-only IPC artifact hints:

```powershell
py run_node_c_codex_ipc_artifact_probe.py
```

This lists matching named-pipe names and shallow Codex/OpenAI directory entries.
It does not read file contents or connect to pipes.

If `codex-ipc` exists, test whether it can be opened without sending payload:

```powershell
py run_node_c_codex_pipe_open_probe.py
```

This opens and immediately closes `\\.\pipe\codex-ipc`. It sends no data and
does not claim the IPC protocol is usable.

If the pipe can be opened, test the Codex IPC router framing and initialize
handshake:

```powershell
py run_node_c_codex_ipc_router_probe.py
```

This writes one framed `initialize` request to `\\.\pipe\codex-ipc` and reads
the matching router response. It does not send a real prompt, use the input
box, or claim that `thread-follower-start-turn` is usable for task delivery.

There is an explicit dry-routing mode for maintainers:

```powershell
py run_node_c_codex_ipc_router_probe.py --dry-thread-follower
```

Dry-routing sends one empty-params `thread-follower-start-turn` request only to
observe routing/error behavior. It can receive unrelated IPC broadcasts, so do
not use it for public screenshots or logs.

After initialize passes, a maintainer may ask for a scrubbed conversation
metadata probe:

```powershell
py run_node_c_codex_ipc_conversation_probe.py
```

This listens briefly for Codex IPC broadcasts and prints only scrubbed thread
metadata such as `conversationId`, `hostId`, change type, and revision. It must
not print turns, messages, screenshots, files, or any conversation body.

If a `conversationId` is observed, a maintainer may ask for one tiny IPC
start-turn probe:

```powershell
py run_node_c_codex_ipc_start_turn_probe.py --conversation-id CONVERSATION_ID
```

This sends only `Reply exactly: NODEC_IPC_OK_001` through Codex Desktop IPC and
claims success only if the matching assistant reply is observed. It does not
use the input box or execute files. The probe now returns scrubbed diagnostics
after a bounded wait instead of hanging on a narrow reply-shape assumption. Add
`--progress` to print scrubbed wait markers to stderr during longer model runs.
The probe sends an explicit `cwd` in `turnStartParams` using the current working
directory by default. Pass `--cwd C:\path\to\project` to override it, or
`--cwd null` to send `cwd: null`. It also sends `approvalPolicy: never` by
default.
The start-turn request shape intentionally mirrors the known-good Mac Desktop
flow: `sourceClientId`, `version: 1`, `thread-follower-start-turn`, text input
with `text_elements: []`, `attachments: []`, `commentAttachments: []`, and a
separate `--start-timeout` for the model turn request. Use `--task-text` only
when a maintainer asks for a custom prompt; the default exact-reply marker is
the safest probe.
Before sending the turn, the probe checks recent scrubbed stream snapshots for
the target conversation runtime. If it detects an `active` conversation with an
interrupted or never-running turn, it stops with `conversation_is_zombie` instead
of sending another task into a stuck thread. Use another `--conversation-id` or
restart Codex Desktop; `--no-preflight` is available only for diagnostics.
After the exact marker is observed, it keeps the IPC connection open briefly
(`--settle-timeout`, default 30 seconds) and reports scrubbed post-marker stream
diagnostics to help distinguish early disconnects from frontstage turn-state
issues.
The JSON output includes four gates:

```text
target_thread_ok -> start_turn_ok -> completion_observed -> refresh_after_ok
```

`refresh_after_ok` is currently `null`; it is not claimed by this public probe.

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

Optional queue dashboard:

```text
http://127.0.0.1:8765/dashboard
```

The dashboard shows task ids, node ids, task types, status, and result details.
It does not execute tasks or bypass relay token checks.

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
task_package
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

## One-Step Connect

Preferred tester command:

```bash
python3 connect_node.py --relay-url RELAY_URL --token TOKEN
```

On Windows:

```powershell
py connect_node.py --relay-url RELAY_URL --token TOKEN
```

The same command can also read a Yuanjie connect card from stdin:

```text
YUANJIE_CONNECT_V1
node_id=node-c
relay=RELAY_URL
connect_code=TOKEN
mode=safe_preflight
boundary=no_shell,no_file_exec,no_external_send,no_formal_ack
```

It compresses install, health, polling, task handling, and result output into
one entrypoint. It still does not prove Codex Desktop IPC or production-ready
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
