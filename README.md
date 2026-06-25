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

V0.1 supports only:

```text
reply_exactly
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

It still supports only `reply_exactly` and still denies shell execution, file
access, external sends, and private endpoint routing.

## Boundaries

This testkit intentionally does not:

```text
run shell commands
open local files
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
V0.3 public relay token preflight
V0.4 real agent adapter interface
V0.5 download-only file channel preflight
```

The public testkit stays separate from Yuanjie core.
