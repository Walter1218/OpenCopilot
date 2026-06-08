# Debug Session: v5-hermes-runtime

Status: [OPEN]

## Symptom

- `V5` UI 已恢复
- `V5AgentWorker` 已改为走 `vnext/Hermes`
- 真实执行时返回 `Hermes provider fallback result`
- 目标是 `V5 UI` 保持不变，底层真实命中 `Hermes local provider`

## Scope

- `gui/v5/agent_worker.py`
- `agents_next/providers/hermes_local/*`
- `platform_next/api/unified/*`

## Hypotheses

1. `V5AgentWorker` 启动的 `/vnext/*` API` 没有拿到正确的 Hermes runtime 配置，导致 `create_run()` 请求失败。
2. Hermes API Server 当前健康检查通过，但 `/v1/runs` 实际请求参数不兼容，导致 adapter 在 `create_run()` 里异常并触发 fallback。
3. `V5AgentWorker` 运行时启了新的本地 API 进程，但新进程环境变量与当前 shell 不一致，导致 Hermes 自动发现失效。
4. Hermes adapter 的 fallback 路径吞掉了关键错误，只返回占位 summary，掩盖了真实失败原因。

## Plan

1. 先加运行时 instrumentation，抓 `V5AgentWorker -> /vnext/tasks -> Hermes adapter` 的真实请求与失败原因
2. 复现一次 `V5 explain`
3. 根据证据判断是配置、协议还是运行时环境问题
4. 再做最小修复

## Evidence

- `V5AgentWorker` 当前命中 `http://127.0.0.1:8010`
- `Hermes create_run` 当前命中 `http://127.0.0.1:8642`
- `Hermes create_run success` 返回 `202`
- `/vnext/tasks/{id}` 最终状态为 `succeeded`
- `V5` 埋点当前带 `ui_version=v5`、`ui_surface=desktop`、`agent_backend=hermes_vnext`、`provider=hermes_local`

## Current Conclusion

- 系统级入口已恢复为 `V5 UI`
- `V5AgentWorker` 已真实接到 `vnext/Hermes`
- 当前仍保留调试插桩，等待用户确认后再清理
