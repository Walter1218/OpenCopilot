# Debug Session: hermes-api-discovery
- **Status**: [OPEN]
- **Issue**: Hermes 进程看起来已启动，但 OpenCopilot 需要接入的 `/v1/models`、`/v1/runs`、`/v1/runs/{run_id}/events` API 目前无法从当前环境稳定访问到。
- **Debug Server**: not-started
- **Log File**: .dbg/trae-debug-log-hermes-api-discovery.ndjson

## Reproduction Steps
1. 检查本机 Hermes 相关监听端口。
2. 分别探测 `/health`、`/v1/health`、`/v1/models`、`/v1/runs`。
3. 结合 Hermes 配置、profile、启动脚本与运行进程，确认真实 API Server 的暴露方式。

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | 当前启动的是 Hermes WebUI，而不是 OpenAI-compatible API Server | High | Low | Confirmed |
| B | API Server 已启用，但绑定在非默认端口或某个 profile 独立端口 | High | Low | Rejected |
| C | API Server 已启用，但需要特定路径/反向代理，不是直接 `/v1/*` | Medium | Medium | Rejected |
| D | API Server 受鉴权或 Host 约束，当前探测方式命中了错误入口 | Medium | Medium | Rejected |
| E | Hermes gateway 在跑，但 API server feature 未对当前 profile 生效 | High | Low | Confirmed |

## Log Evidence
- `lsof -nP -iTCP -sTCP:LISTEN` 显示 `127.0.0.1:8643` 由 `venv/bin/python -m webui --localhost` 监听。
- 探测 `127.0.0.1:8643`：
  - `GET /health` 返回 Hermes WebUI HTML
  - `GET /v1/models` 返回 Hermes WebUI HTML
  - `POST /v1/runs` 返回 `405 Method Not Allowed`
- 探测 `127.0.0.1:8642`、`18790`、`18792`、`18793`：
  - 都未监听 OpenAI-compatible API Server
- `gateway/config.py` 中 `api_server` 平台仅在环境变量满足时注入：
  - `API_SERVER_ENABLED=true` 或 `API_SERVER_KEY` 非空
- 当前已读取到的 profile env：
  - `~/.hermes/.env` 无 `API_SERVER_ENABLED`
  - `~/.hermes/profiles/coder/.env` 无 `API_SERVER_ENABLED`
  - `~/.hermes/profiles/ops/.env` 无 `API_SERVER_ENABLED`

## Verification Conclusion
- 根因已基本确认：
  - 当前运行的是 Hermes WebUI 和 Hermes gateway
  - 但 OpenAI-compatible API Server 没有被当前 profile 环境启用
- 下一步应在实际运行的 Hermes profile `.env` 中显式启用：
  - `API_SERVER_ENABLED=true`
  - `API_SERVER_PORT=<目标端口>`
  - `API_SERVER_KEY=<可选但建议设置>`

## Post-Fix Verification
- 已修改 `~/.hermes/profiles/coder/.env`：
  - `API_SERVER_ENABLED=true`
  - `API_SERVER_PORT=8642`
- 已使用 `coder` profile 重启 gateway
- 复验结果：
  - `GET http://127.0.0.1:8642/health` -> `200 application/json`
  - `GET http://127.0.0.1:8642/v1/models` -> `200 application/json`
  - `POST http://127.0.0.1:8642/v1/runs` -> `202 {"run_id": "...", "status": "started"}`
  - `GET /v1/runs/{run_id}/events` 正常返回 `message.delta`、`reasoning.available`、`run.completed`

## OpenCopilot vNext Integration Validation
- 使用 `FastAPI TestClient` 验证：
  - `POST /vnext/context/snapshots`
  - `POST /vnext/tasks`
  - `GET /vnext/tasks/{id}/events`
  - `GET /vnext/tasks/{id}`
- 过程中发现一个真实问题：
  - `platform_next/api/unified/tasks.py` 里 `TaskResult` 是 `slots=True` dataclass，`get_task()` 使用 `task.result.__dict__` 会触发 `AttributeError`
- 已修复为：
  - `TaskResultResponse(**asdict(task.result))`
- 修复后复验结果：
  - `context -> task -> events -> task state` 整条链路成功
  - `provider_run_id` 正常映射到 Hermes `run_id`
  - `status` 最终为 `succeeded`
