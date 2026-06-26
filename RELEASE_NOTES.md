# Release Notes

## v0.2.0-dev

- Added `pull_relay_result.py` and `run_relay_result_inbox_preflight.py` so a
  caller can pull a completed relay task into a local `.node_bridge_returns/`
  inbox without relying on chat screenshots.
- Added macOS Node-B Codex Desktop IPC probes:
  `run_node_b_codex_ipc_discovery.py` and
  `run_node_b_codex_ipc_start_turn_probe.py`. They use the local Unix socket
  and rollout evidence, not the input box.
- Added `run_node_c_preflight.py` for a safe Node-C local adapter preflight.
- Added `node_bridge_testkit.node_adapter`, which only handles `reply_exactly`
  and denies shell execution, file access, external sends, and private routing.
- Added CI coverage and a GitHub issue template for Node-C preflight results.
- Updated package version to `0.2.0.dev0`.

## v0.3.0-dev

- Added `install_node_c_avatar.py` and `run_node_c_avatar.py`.
- Added local-only `.node_c_avatar/` config and state generation.
- Added structured health, heartbeat, capabilities, boundary, and light-task
  result output.
- Added CI coverage for the installer preflight.

## v0.4.0-dev

- Added token-protected relay mode via `NODE_BRIDGE_TOKEN` or `--token`.
- Added `send_node_c_remote_probe.py` for the maintainer side.
- Added `run_node_c_remote_client.py` for the tester side.
- Added `run_remote_relay_demo.py` to validate remote relay semantics locally.

## v0.1.0-local-proof

First public local proof for `public-node-bridge-testkit`.

## What This Release Includes

- Local in-memory relay
- Safe mock node
- `reply_exactly` light-task protocol
- L0 demo: returns `OK`
- L1 demo: returns structured text
- One-command local demo:

```bash
python3 run_local_demo.py
```

- Protocol document
- Security boundary
- Roadmap
- GitHub Actions workflow
- GitHub issue templates

## Verified Locally

Expected claim:

```text
local_public_testkit_l0_l1_passed
```

Expected L0 result:

```text
OK
```

Expected L1 result:

```text
STATUS=READ_OK; MARKER=PUBLIC_L1; NEXT=SMALL_TASK
```

## Claim Boundary

This release proves:

```text
local relay + mock node + L0/L1 light task protocol can run on a user's machine
```

This release does not prove:

```text
real Codex Desktop IPC
real external node connection
formal ACK
external message sending
file execution
long-running autonomy
Yuanjie core open source
```

## Requirements

```text
Python 3.10+
No third-party Python packages
```

## Safety

V0.1 does not run shell commands, open private files, send external messages,
install packages, or connect to Yuanjie private infrastructure.
