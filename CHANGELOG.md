# Changelog

## 2026-06-27 23:25 - 修复协作桥命令预检跨平台执行
### 变更内容 — 更新 `run_collaborative_bridge_command_worker.py`，将默认 allowlist 命令从 Windows 专用 `py` launcher 改为当前 Python 解释器，并让命令失败时先进入 `result_pending_review` 再提交失败结果；更新 `README.md` 和 `PROTOCOL.md` 中的默认命令说明。
### 原因 — GitHub Actions 的 Ubuntu runner 没有 `py` launcher，导致 `run_collaborative_bridge_command_preflight.py` 在 CI 中失败。
### 影响范围 — 影响协作桥 Host allowlist worker 的默认命令和失败结果回传；不扩大 Controller 权限，不允许任意 shell 命令。

## 2026-06-27 21:34 - 将协作桥预检纳入 CI
### 变更内容 — 更新 `.github/workflows/local-demo.yml`，把协作桥相关脚本加入 `py_compile` 编译检查，并新增 lifecycle、audit、UI、UI form flow、state、allowlisted command 六个协作桥预检步骤。
### 原因 — 准备向远端主仓库提交 PR，需要让新增协作桥能力在 GitHub Actions 中被自动验证，避免只依赖本地手动运行。
### 影响范围 — 影响 PR 和 push 时的本地 demo workflow；不改变运行时协议行为，不执行可选 Codex IPC 真实发送预检。

## 2026-06-27 01:14 - 增加 Host 真实 allowlist 命令执行
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，新增 `run_project_command` 能力、`execution_request.kind=allowlisted_command` 校验、Controller 真实执行按钮和 Host 执行请求展示；新增 `run_collaborative_bridge_command_worker.py`，在 Host 本地执行 allowlist 命令并回传 `exit_code/stdout/stderr`；新增 `run_collaborative_bridge_command_preflight.py` 验证创建任务、Host 批准、worker 真执行 `local_demo`、Controller 读取结果；更新 `run_collaborative_bridge_ui_flow_preflight.py` 验证命令按钮创建执行请求；更新 `PROTOCOL.md` 和 `README.md` 说明 allowlist 执行边界。
### 原因 — 你要求前端可视化按钮对应真实可跑任务能力，但不能落成任意远程 shell 或隐藏远控。
### 影响范围 — 影响协作桥任务校验、Controller/Host UI 和新增 Host worker；执行能力限定为 Host 本地 allowlist，不接受 Controller 提交任意命令字符串。

## 2026-06-27 00:42 - 收紧协作桥 IPC 失败路径
### 变更内容 — 更新 `run_collaborative_bridge_codex_ipc_backend.py`，让 opt-in Codex IPC backend 在发送、运行、结果待审和失败阶段推进 relay 状态；更新 `run_collaborative_bridge_codex_ipc_preflight.py`，在 backend 失败时输出结构化 JSON 诊断而不是抛出 traceback；更新 `PROTOCOL.md` 和 `README.md` 校准协作桥状态流说明。
### 原因 — 当前环境的 Codex IPC start-turn 可能因为会话不可路由或 busy/zombie 保护失败，预检需要明确暴露真实失败阶段，同时让 Host/审计可见失败状态。
### 影响范围 — 影响可选 IPC backend 与 IPC 预检的失败表现；不改变人工桥接 MVP，不绕过 Host 审批，不绕过 Codex 会话保护。

## 2026-06-27 00:36 - 完善协作桥状态审计
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，让 `/tasks/{task_id}/state` 的 `sent_to_codex`、`running`、`result_pending_review`、`failed`、`canceled`、`completed` 状态推进写入审计日志，并将完成审计中的完整 `agent_message` 改为长度摘要；更新 `run_collaborative_bridge_audit_preflight.py` 验证状态审计事件和不落完整回复；更新 `PROTOCOL.md`、`README.md` 说明状态审计与结果摘要边界。
### 原因 — 实施计划要求审计覆盖执行和结果审查阶段，且审计记录应避免写入完整协作结果内容。
### 影响范围 — 影响协作桥审计日志内容和审计预检；不改变 Host 审批要求、不增加远程桌面控制、不绕过 Codex 会话 busy/zombie 保护。

## 2026-06-27 00:03 - 实现协作桥 UI 表单闭环
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，在 `/controller` 页面加入协作任务提交表单，在 `/host` 页面加入待审批任务、批准/拒绝表单和手动结果回传表单；新增 `/ui/controller/tasks`、`/ui/host/approval`、`/ui/host/result` 表单端点；新增 `run_collaborative_bridge_ui_flow_preflight.py` 验证 Controller 创建任务、Host 批准、Host 回传结果、Controller 查看结果以及 Host 拒绝路径；更新 `PROTOCOL.md` 和 `README.md` 记录 UI 表单端点和预检命令。
### 原因 — 计划要求 Host + Controller 双端可视化界面，且第一版必须以 Host 人工审批为核心闭环；仅有 UI 骨架还不能完成实际协作流程。
### 影响范围 — 影响 relay HTML 页面和新增 UI 表单端点；仍不实现 Codex IPC、远程桌面控制、后台隐形控制或生产级 UI。

## 2026-06-26 23:50 - 增加协作桥双语 UI 骨架
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，新增 `/controller` 和 `/host` 双语页面骨架，支持 `lang=zh`/`lang=en`、角色标识、任务队列占位和基础响应式布局；新增 `run_collaborative_bridge_ui_preflight.py` 验证中英文页面与角色标记；更新 `PROTOCOL.md` 和 `README.md` 记录 UI shell 路由、预检命令和不能声明的边界。
### 原因 — 你要求协作桥必须有可视化界面且支持中英文切换，需要先建立可回归验证的最小双端 UI 基础。
### 影响范围 — 影响 relay 的 HTML 页面输出；不改变现有 API 兼容性，也不实现任务提交 UI、Host 审批 UI 或 Codex IPC。

## 2026-06-26 23:48 - 增加协作桥审计日志
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，为 `collaborative_bridge` 增加 append-only JSONL 审计记录，覆盖 `task_created`、`task_approved`、`task_rejected`、`task_completed`；将 relay state 改为 server 实例级状态并让 `make_server` 支持 `audit_path`；新增 `run_collaborative_bridge_audit_preflight.py` 验证审计事件；更新 `PROTOCOL.md` 和 `README.md` 说明审计路径、事件类型和预检命令。
### 原因 — 协作桥必须具备可审计基础，Host 人工审批和结果回传需要留下本地证据，后续 UI 才能显示审计历史。
### 影响范围 — 影响 relay 内存状态挂载方式和协作任务事件记录；旧本地 demo 和 Node-C 预检路径保持兼容。

## 2026-06-26 23:36 - 实现协作任务审批生命周期
### 变更内容 — 更新 `node_bridge_testkit/relay.py`，新增 `collaborative_bridge` 任务类型、能力白名单校验、`pending_approval`/`approved`/`rejected` 生命周期和 `/tasks/{task_id}/approval` 端点；新增 `run_collaborative_bridge_preflight.py` 验证协作任务创建、禁止能力拒绝、待审批不被普通 poll 取走、批准/拒绝和批准后提交结果；更新 `PROTOCOL.md` 和 `README.md` 记录新任务类型、审批接口、允许能力和不能声明的边界。
### 原因 — 开始实现协作桥计划的 Phase 1，需要先建立 Host 人工审批的协议状态基础，后续双端可视化 UI 才能依赖稳定状态模型。
### 影响范围 — 影响 relay 任务创建、审批和结果提交逻辑；保留旧 `reply_exactly`、`file_deliver`、`task_package` 和 Node-C 预检路径兼容。

## 2026-06-26 23:28 - 补充协作桥实施计划
### 变更内容 — 新增 `docs/superpowers/specs/2026-06-26-collaborative-bridge-implementation-plan.md`，将双端可视化协作桥拆成协议状态、审计能力、双语 UI、人工桥接闭环和可选 IPC 自动化五个阶段。
### 原因 — 已确认协作桥中文架构方向，需要形成可执行、可验证、可分阶段推进的实施计划。
### 影响范围 — 影响后续开发顺序、验收标准和风险控制；不改变当前代码运行逻辑。

## 2026-06-26 23:25 - 补充协作桥设计文档
### 变更内容 — 新增 `docs/superpowers/specs/2026-06-26-collaborative-bridge-design.md`，记录 Host + Controller 双端可视化、Host 人工审批、中英文切换、任务生命周期、安全边界和首版闭环设计。
### 原因 — 你确认项目后续要走授权协作式 Codex 节点控制方向，并要求第一版具备双端界面和中英文切换，需要先沉淀为可评审设计。
### 影响范围 — 影响后续产品规划、实施拆分和安全边界判断；不改变当前代码运行逻辑。

## 2026-06-26 21:07 - 建立项目记忆
### 变更内容 — 新增 `AGENTS.md`，写入仓库定位、技术栈、核心模块、协议边界、本地状态目录和常用命令；补充 `CHANGELOG.md` 记录本次初始化工作。
### 原因 — 你要求先系统学习该仓库，并建立后续迭代可直接读取的项目记忆文件，避免之后重复摸索。
### 影响范围 — 影响后续 Codex 对仓库约定、入口脚本、状态目录和任务边界的理解，不改变运行逻辑。
