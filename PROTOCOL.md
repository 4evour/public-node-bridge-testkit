# Node Bridge Public Protocol V0.1

## Scope

V0.1 is a light-task protocol for local verification.

It has three roles:

```text
caller -> relay -> node
```

## State Flow

```text
created -> queued -> in_progress -> completed
created -> pending_approval -> approved -> sent_to_codex -> running -> result_pending_review -> completed
created -> pending_approval -> rejected
created -> pending_approval -> approved -> failed
created -> pending_approval -> approved -> canceled
```

## Endpoints

### Health

```http
GET /health
```

### Create Task

```http
POST /tasks
Content-Type: application/json
```

Body:

```json
{
  "target_node": "node-b",
  "task_type": "reply_exactly",
  "payload": {
    "marker": "L0-OK",
    "text": "OK"
  }
}
```

### Node Poll

```http
GET /poll?node_id=node-b
```

### Submit Result

```http
POST /tasks/{task_id}/result
Content-Type: application/json
```

Body:

```json
{
  "node_id": "node-b",
  "result": {
    "status": "ok",
    "agent_message": "OK",
    "execution": "mock_reply_exactly"
  }
}
```

### Approve Or Reject Collaborative Task

```http
POST /tasks/{task_id}/approval
Content-Type: application/json
```

Approve body:

```json
{
  "node_id": "node-c",
  "decision": "approve"
}
```

Reject body:

```json
{
  "node_id": "node-c",
  "decision": "reject",
  "reason": "Need clearer scope."
}
```

### Read Task

```http
GET /tasks/{task_id}
```

## Acceptance Rule

For `reply_exactly`, the acceptance rule is:

```text
task.status == completed
task.result.agent_message == task.payload.text
```

For `file_deliver`, the acceptance rule is:

```text
task.status == completed
task.result.execution == local_adapter_file_deliver_sandbox_write
task.result.marker == task.payload.marker
task.result.filename == task.payload.filename
task.result.sha256 == task.payload.sha256
```

`file_deliver` payload:

```json
{
  "target_node": "node-c",
  "task_type": "file_deliver",
  "payload": {
    "marker": "NODEC-FILE-001",
    "filename": "nodec_file_preflight_001.txt",
    "content_b64": "base64-encoded-small-file",
    "sha256": "expected-sha256"
  }
}
```

Node-C writes only into its own sandbox:

```text
.node_c_avatar/inbox/<task_id>/
```

## Node-C Local Adapter Preflight

`run_node_c_preflight.py` uses the same relay and the same `reply_exactly`
acceptance rule, but targets `node-c` through `node_bridge_testkit.node_adapter`.

Expected result:

```json
{
  "status": "ok",
  "node_id": "node-c",
  "marker": "NODEC-PREFLIGHT",
  "agent_message": "STATUS=NODEC_PREFLIGHT_OK; MARKER=NODEC_PREFLIGHT; NEXT=READY_FOR_REVIEW",
  "execution": "local_adapter_reply_exactly",
  "safe_mode": true
}
```

## Collaborative Bridge Relay Lifecycle Preflight

`collaborative_bridge` is the first relay-side task type for the planned
Host-approved collaborative bridge. It proves only task creation, capability
validation, Host approval/rejection state, and approved result submission.

Payload:

```json
{
  "target_node": "node-c",
  "task_type": "collaborative_bridge",
  "payload": {
    "requester": "yuanjie-controller",
    "target_project": "D:\\work\\repo-b",
    "prompt": "Inspect the failing test summary and propose a minimal fix.",
    "capabilities": [
      "send_prompt_to_codex",
      "read_task_result",
      "return_artifact_summary"
    ]
  }
}
```

Allowed capabilities:

```text
send_prompt_to_codex
read_task_result
return_artifact_summary
read_project_manifest
run_project_command
```

Forbidden capability requests, such as `shell_execution`, are rejected before
approval.

Allowlisted command execution uses an explicit execution request. The Controller
supplies only `command_id`; the Host worker resolves that id from its local
allowlist.

```json
{
  "execution_request": {
    "kind": "allowlisted_command",
    "command_id": "local_demo"
  }
}
```

The relay rejects command execution requests that do not include the
`run_project_command` capability. It also rejects command ids that look like
paths or command strings.

Expected lifecycle:

```text
POST /tasks -> pending_approval
GET /poll?node_id=node-c -> task=null
POST /tasks/{task_id}/approval decision=approve -> approved
POST /tasks/{task_id}/result -> completed
```

Rejected lifecycle:

```text
POST /tasks -> pending_approval
POST /tasks/{task_id}/approval decision=reject -> rejected
```

Run:

```bash
python3 run_collaborative_bridge_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_preflight.py
```

This does not prove real Codex IPC, remote desktop control, hidden background
control, shell execution, arbitrary file read, external send, or
production-ready collaboration.

## Collaborative Bridge Audit Log

Collaborative relay lifecycle events are written as append-only JSONL records.
By default, the relay writes:

```text
.node_c_avatar/audit/collaborative_audit.jsonl
```

Maintainers can override the path when creating an in-process relay through
`make_server(..., audit_path=...)` or with the `NODE_BRIDGE_AUDIT_PATH`
environment variable.

Audit records use:

```json
{
  "schema": "node_bridge_collaborative_audit_v0.1",
  "audit_id": "audit_...",
  "task_id": "task_...",
  "target_node": "node-c",
  "task_type": "collaborative_bridge",
  "event_type": "task_created",
  "timestamp": "2026-06-26T15:46:22+00:00",
  "status": "pending_approval",
  "details": {}
}
```

Current event types:

```text
task_created
task_approved
task_rejected
task_sent_to_codex
task_running
task_result_pending_review
task_failed
task_canceled
task_completed
```

Completion audit details include execution metadata and result length summary,
not the full agent message.

Run:

```bash
python3 run_collaborative_bridge_audit_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_audit_preflight.py
```

The audit preflight proves only local append-only event recording for the relay
lifecycle. It does not prove durable multi-user storage, tamper resistance,
Codex IPC, shell execution, arbitrary file read, external send, or production
security compliance.

## Collaborative Bridge UI Shell

The relay serves the first bilingual UI shell on the same local port:

```text
/controller?lang=zh
/controller?lang=en
/host?lang=zh
/host?lang=en
```

Run:

```bash
python3 run_collaborative_bridge_ui_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_ui_preflight.py
```

The UI shell preflight proves only that the Controller and Host pages render
with Chinese/English labels and role markers. It does not prove task submission
UI, Host approval UI, Codex IPC, remote desktop control, or production-ready UI.

## Collaborative Bridge UI Form Flow

The first UI form flow uses standard local HTML forms and the existing relay
state. It supports:

```text
Controller creates collaborative_bridge task
Host approves or rejects pending task
Host returns a manual Codex result for approved task
Controller sees completed or rejected task
```

UI form endpoints:

```http
POST /ui/controller/tasks
POST /ui/host/approval
POST /ui/host/result
```

Run:

```bash
python3 run_collaborative_bridge_ui_flow_preflight.py
```

On Windows:

```powershell
py run_collaborative_bridge_ui_flow_preflight.py
```

The UI form-flow preflight proves only the local Controller -> Relay -> Host
manual approval/result loop. It does not prove real Codex IPC, remote desktop
control, hidden background control, durable hosted collaboration, or
production-ready UI.

## Collaborative Bridge Allowlisted Command Execution

The first real execution path is a Host-side allowlist worker. It runs only
commands selected by Host configuration. The Controller cannot submit an
arbitrary shell command.

Default local command ids:

```text
local_demo -> current Python interpreter + run_local_demo.py
node_c_preflight -> current Python interpreter + run_node_c_preflight.py
collaborative_bridge_preflight -> current Python interpreter + run_collaborative_bridge_preflight.py
```

Run one approved command task as the Host worker:

```bash
python3 run_collaborative_bridge_command_worker.py --relay-url RELAY_URL --project-root PROJECT_ROOT
```

On Windows:

```powershell
py run_collaborative_bridge_command_worker.py --relay-url RELAY_URL --project-root PROJECT_ROOT
```

Run the local end-to-end preflight:

```powershell
py run_collaborative_bridge_command_preflight.py
```

This proves Host-approved allowlisted command execution with `exit_code`,
`stdout`, and `stderr` returned through the relay. It does not prove arbitrary
shell execution, hidden background control, unapproved execution, or production
remote control.

## Node-C Avatar Installer Preflight

`install_node_c_avatar.py` creates local testkit state:

```text
.node_c_avatar/config.json
.node_c_avatar/state.json
```

`run_node_c_avatar.py` then returns a structured packet with:

```text
health
heartbeat
capabilities
allowed_task_types
denied_capabilities
completed light tasks
```

The installer preflight supports `reply_exactly` and sandboxed `file_deliver`.
It remains local-only until a relay URL and token are provided.

## Remote Relay Token Preflight

When a relay is started with `NODE_BRIDGE_TOKEN` or `--token`, task endpoints
require:

```http
X-Node-Bridge-Token: <token>
```

Maintainer flow:

```text
send_node_c_remote_probe.py -> POST /tasks -> wait GET /tasks/{task_id}
```

Node-C flow:

```text
run_node_c_remote_client.py -> GET /poll?node_id=node-c -> POST /tasks/{task_id}/result
```

Acceptance rule remains:

```text
task.status == completed
task.result.agent_message == task.payload.text
```

For file-channel preflight:

```text
send_node_c_file_probe.py -> POST /tasks task_type=file_deliver -> wait GET /tasks/{task_id}
run_node_c_remote_client.py -> GET /poll?node_id=node-c -> sandbox write -> POST /tasks/{task_id}/result
```

Forbidden claims:

```text
formal ACK
real Codex Desktop IPC
external send
file execution
persistent service
long-running autonomy
```

## Forbidden In V0.1

```text
shell execution
file execution
external message sending
formal ACK
credential handling
private endpoint routing
```
