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

Create small Yuanjie task slices:

```bash
python3 yuanjie_task_slicer.py --goal "Verify Node-C file channel and Codex rollout evidence"
```

On Windows:

```powershell
py yuanjie_task_slicer.py --goal "Verify Node-C file channel and Codex rollout evidence"
```

The slicer turns one broad goal into small observable task cards with markers,
expected outputs, acceptance gates, and `cannot_claim` boundaries. It is only a
local planning helper. It does not send tasks, call a model, prove ACK, execute
files, or update any global experience pool.

Preflight the slicer shape:

```bash
python3 run_yuanjie_task_slicer_preflight.py
```

On Windows:

```powershell
py run_yuanjie_task_slicer_preflight.py
```

Build an avatar workspace card:

```bash
python3 yuanjie_avatar_workspace_card.py --avatar-id YJ-NODEC-001 --project-id public-node-bridge-testkit
```

On Windows:

```powershell
py yuanjie_avatar_workspace_card.py --avatar-id YJ-NODEC-001 --project-id public-node-bridge-testkit
```

This is the minimal "avatar working seat" layer inspired by persistent agent
workspaces. It summarizes identity, workspace path, permissions, current task,
task cache, sandbox inbox, reserved artifact outbox, audit sources, and
experience candidates. It is read-only. It does not start services, send tasks,
execute files, claim formal ACK, or write to a global experience pool.
The card also exposes module slots for frame source, task slicing, sensors,
posture decisions, yin-yang experience candidates, low-cost reuse, reality
anchors, and immune recovery. Some slots are implemented local tools; others
are explicit candidate slots so the project does not confuse design with
runtime proof.

Preflight the workspace card:

```bash
python3 run_avatar_workspace_card_preflight.py
```

On Windows:

```powershell
py run_avatar_workspace_card_preflight.py
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

The collaborative bridge relay lifecycle preflight is:

```bash
python3 run_collaborative_bridge_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_preflight.py
```

This verifies only the relay-side Host approval lifecycle for
`collaborative_bridge`: capability validation, `pending_approval`, explicit
approve/reject, and approved result submission. It does not prove real Codex
IPC, remote desktop control, hidden background control, shell execution,
arbitrary file read, external send, or production-ready collaboration.

The collaborative bridge audit preflight is:

```bash
python3 run_collaborative_bridge_audit_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_audit_preflight.py
```

This verifies local append-only JSONL audit events for collaborative task
creation, approval, execution state changes, result review, rejection, and
completion. Completion audit entries store result metadata and message length,
not the full agent message. It does not prove durable multi-user storage,
tamper resistance, Codex IPC, shell execution, arbitrary file read, external
send, or production security compliance.

The collaborative bridge UI shell preflight is:

```bash
python3 run_collaborative_bridge_ui_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_ui_preflight.py
```

When the relay is running, the bilingual UI shell is available at:

```text
http://127.0.0.1:8765/controller?lang=zh
http://127.0.0.1:8765/controller?lang=en
http://127.0.0.1:8765/host?lang=zh
http://127.0.0.1:8765/host?lang=en
```

This shell currently proves only role-specific page rendering and Chinese /
English labels. It does not yet prove task submission UI, Host approval UI,
Codex IPC, remote desktop control, or production-ready UI.

The collaborative bridge UI form-flow preflight is:

```bash
python3 run_collaborative_bridge_ui_flow_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_ui_flow_preflight.py
```

This verifies the first local visual collaboration loop:

```text
Controller UI form -> relay pending_approval task
Host UI form -> approve or reject
Host UI form -> return manual result for approved task
Controller UI -> displays completed or rejected task
```

It does not prove Codex IPC, remote desktop control, hidden background control,
durable hosted collaboration, or production-ready UI.

The collaborative bridge allowlisted-command preflight is:

```bash
python3 run_collaborative_bridge_command_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_command_preflight.py
```

This verifies the first real Host-side execution loop:

```text
Controller creates allowlisted command task
Host approves the task
Host worker runs the local allowlist command
Controller reads exit_code/stdout/stderr
```

It does not allow Controller-provided shell commands. The Host worker resolves
`command_id` from a local allowlist and executes inside the Host-selected
project root.

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

Run the local Host Approval Gate task-package preflight:

```bash
python3 run_approval_gate_task_package_preflight.py
```

On Windows:

```powershell
py run_approval_gate_task_package_preflight.py
```

This proves only that `approval_gate` metadata can travel inside a safe
task-package and return as a scrubbed result summary. It does not prove a real
approval UI, formal ACK, external send, file execution, or production-ready
connection.

The maintainer can queue the same safe remote probe:

```bash
python3 send_approval_gate_task_package_probe.py --relay-url RELAY_URL --token TOKEN --node-id node-c
```

Run the local task-cache preflight:

```bash
python3 run_node_c_local_cache_preflight.py
```

On Windows:

```powershell
py run_node_c_local_cache_preflight.py
```

Remote tasks pulled by `connect_node.py` are now first written to the local
avatar sandbox under `.node_c_avatar/task_cache/`, then executed by the local
adapter, then updated with the result and submit status. This makes the node
flow more observable and gives later Codex IPC adapters a local cache to read
from instead of depending on a live relay response. It still does not prove real
Codex IPC, external send, formal ACK, or arbitrary file execution.

Pull a completed relay task result back into a local caller-side inbox:

```bash
python3 pull_relay_result.py --relay-url RELAY_URL --token TOKEN --task-id TASK_ID
```

On Windows:

```powershell
py pull_relay_result.py --relay-url RELAY_URL --token TOKEN --task-id TASK_ID
```

This writes `.node_bridge_returns/TASK_ID.json` with the relay result, marker,
execution metadata, and explicit `cannot_claim` boundaries. It is only a local
return inbox for evidence collection. It does not contact Codex Desktop, use
the input box, execute returned files, send messages, or claim formal ACK.

Preflight the return inbox locally:

```bash
python3 run_relay_result_inbox_preflight.py
```

On Windows:

```powershell
py run_relay_result_inbox_preflight.py
```

Run the next cached task locally:

```bash
python3 run_next_cached_task.py
```

On Windows:

```powershell
py run_next_cached_task.py
```

This is the manual wakeup path. It reads the next pending task already stored in
`.node_c_avatar/task_cache/`, checks the local state sensor for busy/zombie
conditions, executes only the existing allowlisted local adapter actions, and
updates the same cache record to `completed_local` or `failed_local`. It does
not poll the relay, use the Codex input box, send messages, claim formal ACK, or
execute arbitrary files.

Preflight the cached-task wakeup path without a relay:

```bash
python3 run_next_cached_task_preflight.py
```

On Windows:

```powershell
py run_next_cached_task_preflight.py
```

Inspect the local connection state:

```bash
python3 run_node_c_connection_state.py
```

On Windows:

```powershell
py run_node_c_connection_state.py
```

This reads only `.node_c_avatar/` and reports a Bluetooth-like state:

```text
disconnected -> discovered -> paired -> bound -> ready -> busy/zombie
```

It combines local install state, heartbeat, `session_binding.json`, and
`task_cache/` so the tester can see whether the node is ready, busy, or blocked
by a bad conversation before another task is sent.

Inspect local loop readiness:

```bash
python3 run_node_c_loop_readiness.py
```

On Windows:

```powershell
py run_node_c_loop_readiness.py
```

This is the "Loop sensor" layer. It reads only local avatar state and reports
whether the node has a fresh heartbeat, a non-zombie session binding, an
accessible task cache, a pending cached task, and observed `approval_gate`
metadata. The positive local state is `local_loop_ready`. This still does not
claim real Codex IPC, task delivery to Codex, frontstage UI injection, formal
ACK, external send, long-running autonomy, or production readiness.

Preflight the loop-readiness sensor with a temporary sandbox:

```bash
python3 run_node_c_loop_readiness_preflight.py
```

On Windows:

```powershell
py run_node_c_loop_readiness_preflight.py
```

Build the six Yuanjie acceptance cards:

```bash
python3 yuanjie_acceptance_cards.py --avatar-id YJ-NODEC-001 --project-id public-node-bridge-testkit --out-dir .yuanjie_acceptance_cards
```

On Windows:

```powershell
py yuanjie_acceptance_cards.py --avatar-id YJ-NODEC-001 --project-id public-node-bridge-testkit --out-dir .yuanjie_acceptance_cards
```

This folds the existing local state into a product-facing review layer:

```text
node_card
task_card
run_log
evidence_card
review_panel
reuse_template
```

The cards reuse the avatar workspace card, task cache, loop sensor, result
evidence, approval-gate summary, and reuse-candidate boundary. They do not
replace those modules. They also do not prove real Codex IPC, frontstage
injection, formal ACK, external send, file execution, full loop, production
readiness, or global experience write.

Preflight the acceptance-card layer with a temporary sandbox:

```bash
python3 run_yuanjie_acceptance_cards_preflight.py
```

On Windows:

```powershell
py run_yuanjie_acceptance_cards_preflight.py
```

Run the local handshake-card parser preflight:

```bash
python3 run_agent_handshake_card_preflight.py
```

On macOS, after opening Codex Desktop, run the Node-B read-only Codex IPC
discovery probe:

```bash
python3 run_node_b_codex_ipc_discovery.py
```

This initializes the local Codex Desktop Unix socket and listens briefly for
scrubbed thread metadata. It does not send a prompt, use the input box, read
conversation content, execute files, or claim formal ACK. If no live broadcast
is observed, it also prints the newest local rollout `conversation_id` candidates
from filenames only, without reading message content.

If a `conversation_id` is known or selected from the newest rollout candidate,
a maintainer may ask for one tiny macOS IPC start-turn probe:

```bash
python3 run_node_b_codex_ipc_start_turn_probe.py --conversation-id CONVERSATION_ID
```

If Codex Desktop visibly completed a manual idle check but discovery still
reports `active/inProgress`, pass that completed manual marker as a rollout
fallback:

```bash
python3 run_node_b_codex_ipc_start_turn_probe.py --conversation-id CONVERSATION_ID --preflight-completed-marker NODEB_IDLE_CHECK_002
```

This does not ignore busy state blindly. It proceeds only when the local rollout
file already proves the marker has `user_message`, `agent_message`, exact
assistant text, and `task_complete`.

The default prompt is only `Reply exactly: NODEB_IPC_OK_001` plus a boundary
line. The probe sends through `thread-follower-start-turn`, then observes local
Codex rollout evidence for `user_message`, `agent_message`, exact marker, and
`task_complete`. It does not use the input box, paste, press enter, execute
files, or send anything externally.

The macOS output uses the same four-gate language:

```text
target_thread_ok -> start_turn_ok -> completion_observed -> refresh_after_ok
```

`refresh_after_ok` is not claimed by this public macOS probe. If the Codex UI
still looks delayed while rollout completion is true, treat it as a frontstage
refresh/hydration issue instead of sending duplicate prompts.

Before sending the turn, the macOS probe checks scrubbed runtime metadata when
available. If the target conversation is still `active/inProgress`, it stops
with `conversation_busy_or_zombie` and sends no task. Open or create an idle
Codex Desktop conversation, then rerun discovery and start-turn with that
conversation id.

After Node-B macOS IPC start-turn has passed, the tester can join the relay
polling path to Codex IPC for safe `reply_exactly` tasks:

```bash
python3 run_node_b_relay_ipc_client.py --relay-url RELAY_URL --token TOKEN --node-id node-b --conversation-id CONVERSATION_ID --preflight-completed-marker LAST_COMPLETED_MARKER
```

This polls one relay task, writes it to the local task cache, sends only the
expected `reply_exactly` text into Codex Desktop through IPC, observes rollout
completion, and submits the result back to the relay. It does not support file
execution, task-package execution, external send, formal ACK, or persistent
service mode.

Local glue preflight without contacting Codex Desktop:

```bash
python3 run_node_b_relay_ipc_client_preflight.py
```

This uses `--dry-run-ipc`, so it proves only relay polling, task cache, result
submission, and output shape. It does not prove real Codex Desktop IPC.

From the caller side, enqueue one Node-B relay-to-Codex IPC light task and wait
for the relay result:

```bash
python3 send_node_b_relay_ipc_probe.py --relay-url RELAY_URL --token TOKEN --node-id node-b
```

Local sender plus dry-run client preflight:

```bash
python3 run_node_b_relay_ipc_sender_preflight.py
```

This proves the caller-side task enqueue and result wait path, paired with the
dry-run client. It still does not prove real Codex Desktop IPC.

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

For a more stable local flow, first bind the currently observed Codex Desktop
conversation into the local avatar sandbox:

```powershell
py run_node_c_bind_current_session.py --cwd C:\path\to\project
```

This writes `.node_c_avatar/session_binding.json` with scrubbed conversation
metadata. A later start-turn probe can read that file:

The binder refuses to write a binding when the observed frontstage conversation
looks like a stuck/zombie thread. Open or create an idle Codex Desktop
conversation and rerun it, or pass a known idle `--conversation-id`.

```powershell
py run_node_c_codex_ipc_start_turn_probe.py --session-binding .node_c_avatar\session_binding.json
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
After the exact marker is observed, it keeps the IPC connection open only
briefly (`--settle-timeout`, default 8 seconds) and exits early when a terminal
runtime hint is observed. This avoids making the tester wait behind a diagnostic
settle loop while still reporting scrubbed post-marker stream diagnostics.
The JSON output includes four gates:

```text
target_thread_ok -> start_turn_ok -> completion_observed -> refresh_after_ok
```

`refresh_after_ok` is currently `null`; it is not claimed by this public probe.
`frontstage_status_hint=runtime_terminal_observed` means IPC saw the runtime
settle; it is still not a visual UI screenshot claim.

If the UI still shows "thinking", observe the local Codex rollout/session files
instead of sending another prompt:

```powershell
py run_node_c_codex_session_completion_probe.py --session-binding .node_c_avatar\session_binding.json --marker NODEC_IPC_OK_001
```

This probe sends nothing. It reads only local `.codex\sessions` rollout files
and checks for `user_message`, `agent_message`, and `task_complete` records that
contain the marker. If `assistant_answer_seen=true` and `task_complete_seen=true`
while the UI is still spinning, the model turn completed and the remaining
problem is frontstage refresh/hydration. If these gates remain false, the
start-turn did not produce a completed model turn.

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
collaborative_bridge
```

`collaborative_bridge` is pending-approval by default. It is not returned by
normal node polling; Host review is handled through the explicit approval
lifecycle. The relay supports the first lifecycle gate through:

```http
POST /tasks/{task_id}/approval
```

Allowed collaborative capabilities are:

```text
send_prompt_to_codex
read_task_result
return_artifact_summary
read_project_manifest
run_project_command
```

Requests for forbidden capabilities such as `shell_execution` are rejected at
the relay boundary.

Allowlisted command execution requests use:

```json
{
  "execution_request": {
    "kind": "allowlisted_command",
    "command_id": "local_demo"
  }
}
```

The relay accepts this only when `run_project_command` is present. The Host
worker maps `command_id` to local commands such as the current Python
interpreter running `run_local_demo.py`; the
Controller never sends raw shell strings.

Collaborative relay events are written to:

```text
.node_c_avatar/audit/collaborative_audit.jsonl
```

This path can be overridden with `NODE_BRIDGE_AUDIT_PATH` or with the
`audit_path` argument when creating an in-process relay through `make_server`.
State transitions through `/tasks/{task_id}/state` are also audited, and result
completion audit entries avoid storing full agent replies.

The first bilingual UI shell is served from the relay process:

```text
/controller?lang=zh
/controller?lang=en
/host?lang=zh
/host?lang=en
```

The first UI form endpoints are:

```http
POST /ui/controller/tasks
POST /ui/host/approval
POST /ui/host/result
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
