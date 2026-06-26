# Publish Checklist

Use this before publishing `public-node-bridge-testkit` to GitHub.

## Repository Boundary

- [ ] Repository name does not imply Yuanjie core is open-sourced.
- [ ] README clearly says this is a public local testkit.
- [ ] README clearly says each Codex IPC probe only proves its own bounded gate.
- [ ] SECURITY.md contains the claim boundary.
- [ ] No private endpoint, token, cookie, or credential is present.
- [ ] No Aliyun route is present.
- [ ] No private Codex IPC token, private endpoint, or unsafe automation is present.
- [ ] No avatar hotfix implementation is present.

## Runnable Demo

- [ ] `python3 run_local_demo.py` passes locally.
- [ ] `python3 run_relay_result_inbox_preflight.py` passes locally.
- [ ] `python3 run_approval_gate_task_package_preflight.py` passes locally.
- [ ] `python3 run_node_c_loop_readiness_preflight.py` passes locally.
- [ ] `python3 run_yuanjie_acceptance_cards_preflight.py` passes locally.
- [ ] L0 returns `OK`.
- [ ] L1 returns `STATUS=READ_OK; MARKER=PUBLIC_L1; NEXT=SMALL_TASK`.
- [ ] No third-party Python dependency is required.

## GitHub Setup

- [ ] Add GitHub Actions CI for `python3 run_local_demo.py`.
- [ ] Enable issue templates.
- [ ] Add topics:
  - `agent`
  - `agent-to-agent`
  - `multi-agent`
  - `testkit`
  - `python`
- [ ] Add a short repo description:
  - `Local-first public testkit for safe Agent-to-Agent light-task flow.`

## First Release Boundary

- [ ] Release tag: `v0.1.0-local-proof`.
- [ ] Release notes include `cannot claim` list.
- [ ] No public relay token is included in v0.1.
- [ ] No file channel is included in v0.1.

## Success Signals

Track:

- issue result reports
- forks
- stars
- clone/download interest
- bug reports
- requests for real relay/token
- requests for Windows/Linux support

Do not judge only by stars.
