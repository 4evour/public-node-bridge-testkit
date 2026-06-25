# Roadmap

## V0.1 Local Proof

Goal:

```text
Anyone can run local relay + mock node + L0/L1 tasks.
```

Status:

```text
implemented
```

## V0.2 Node-C Local Adapter Preflight

Goal:

```text
Anyone can run a second-stage node-c adapter preflight locally.
```

Rules:

```text
reply_exactly only
no file channel
no IPC internals
no external send
no formal ACK
```

## V0.3 Public Relay Preflight

Goal:

```text
Optional public relay with test token.
```

Rules:

```text
reply_exactly only
rate limit
no file channel
no IPC internals
no external send
no formal ACK
```

## V0.4 Real Agent Adapter Interface

Goal:

```text
Let users connect their own agent runtime behind the same task protocol.
```

Adapters should implement:

```text
poll
execute_allowlisted_light_task
submit_result
heartbeat
```

## V0.5 Download-Only File Channel Preflight

Goal:

```text
Transfer a file manifest and sha256, then download-only verify.
```

Still forbidden:

```text
auto install
auto execute
permission change
external send
```

## V1.0 Criteria

```text
3 independent users run local demo
2 independent OS results
1 external public relay preflight
clear security boundary accepted by testers
no core Yuanjie route exposed
```
