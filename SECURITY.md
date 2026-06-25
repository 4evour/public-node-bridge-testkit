# Security Boundary

This project is a public light-task testkit. It is not a remote-control tool.

## Safe By Design

V0.1 uses:

```text
localhost relay
in-memory task queue
mock node
reply_exactly task
sandboxed file_deliver task
Python standard library only
```

`file_deliver` writes only the task payload into `.node_c_avatar/inbox/<task_id>/`
and returns SHA-256. It must not execute the file or read arbitrary local files.

## Not Included

```text
No shell command execution
No file execution
No arbitrary local file read/write
No browser control
No account login
No external message sending
No payment, deletion, approval, or authorization actions
No private Yuanjie endpoints
No Aliyun token or route
No Codex Desktop IPC implementation
No input-box automation
```

`run_node_c_codex_ipc_discovery.py` is read-only. It only reports local process,
path, and optional localhost port hints for deciding whether a future IPC
adapter is possible.

`run_node_c_codex_ipc_router_probe.py` is a protocol probe, not a task sender.
By default it can open `\\.\pipe\codex-ipc`, send one framed `initialize`
request, and wait only for the matching initialize response. Its optional dry
thread-follower mode is maintainer-only because any IPC client may receive
unrelated broadcasts. It must not use the input box, execute files, or claim
formal ACK/task delivery.

## Reporting Security Issues

Open a GitHub issue only for public testkit concerns.

Do not post:

```text
API tokens
private relay URLs
screenshots with personal data
private keys
cookies
internal company data
```

## Project Claim Boundary

Passing the local demo means:

```text
local_public_testkit_l0_l1_passed
```

It does not mean:

```text
external node connected
formal ACK completed
real Codex IPC validated
arbitrary file channel validated
autonomous agent collaboration completed
```
