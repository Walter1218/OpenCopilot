# OpenCopilot 启动方式说明

> 本文档已按当前桌面主链路更新。  
> 当前系统级入口是 `V5 UI`，底层智能体执行已经统一收口到 `V5AgentWorker`；默认仍走 `vnext/Hermes`，但已支持通过 `agent_runtime` 配置切到自研智能体，不再按旧 `18888` Agent Pipeline 口径理解。

## 零、先记住当前真实链路

系统级双击右键当前走的是：

```text
smart_copilot.py
  -> gui/main.py
  -> gui/v5/navigation.py
  -> SmartCopilotV5
  -> gui/v5/agent_worker.py
  -> /vnext/context/* + /vnext/tasks/*
  -> hermes_local provider
  -> Hermes API Server
```

当前关键事实：

- 双击右键弹出的仍然是 `SmartCopilotV5`
- `WorkTabV5 / ChatTabV5 / StudioTabV5` 交互保持 `V5` 形态
- `V5AgentWorker` 是统一 AI 入口：默认把请求转发到 `vnext/Hermes`，也可按配置切到 `self_agent`
- `V5` 埋点继续沿用，并额外标注：
  - `ui_version=v5`
  - `ui_surface=desktop`
  - `agent_backend=<运行时动态值>`
  - `provider=<运行时动态值>`
- `StudioTabV5` 的“快速创建”当前只会在用户输入极短时才尝试剪贴板兜底，避免把明确输入的主题误替换成历史日志或其他脏数据
- `PPT` 共创第一批收口已完成：
  - 当前页命中与标题位约束已补强
  - 旧 `action/update` JSON 数组已兼容
  - 图文页指令会同步落 `slide.layout`
  - 共创报错文案会按运行时路由自适应：默认 Hermes 路由仍提示 `Hermes 共创链路`，切到自研时不再误报 Hermes

## 一、推荐启动方式

### 1. 验证系统级 V5 UI

这是当前最重要的验证方式，用来确认“`V5 UI + Hermes execution`”是否正常：

```bash
# 终端 1：Broker（必须在 macOS 原生 Terminal.app / iTerm2 中运行）
bash start_broker.sh

# 终端 2：UI
bash scripts/start_ui.sh
```

说明：

- `Broker :18889` 负责选区读取、活动文档读取、文本回写
- `V5AgentWorker` 会优先探测 `http://127.0.0.1:8010`
- 若 `:8010` 已存在但不是当前 `vnext` 路由，再回退探测 `:8000`
- 若本机没有可用 `vnext API`，会自动拉起 `smart_copilot_api:app`
- 若 Hermes API Server 未在线，`hermes_local` provider 会按 profile 自动尝试拉起 gateway
- `V5AgentWorker` 会按输入体量动态估算 UI 侧 read timeout；当前默认下限约 `45s`，`translate` 不低于 `60s`，`ppt` 不低于 `90s`，并对超长文本继续上调
- `/vnext/tasks/{id}/events` 现已改为返回后台线程已落库的事件，不再在请求线程里同步长时间等待 Hermes 流完成
- `Studio` 共创窗口中的 AI 编辑、重新生成、建议分析也已复用同一个 `V5AgentWorker` 路由入口，不再单独走旧 `asu_custom_agent.pipeline`

### 1.1 可选：通过配置切换智能体后端

默认情况下，`agent_runtime` 不配置时会继续走当前 `Hermes/vnext` 主链路。

如果要切到自研智能体，可在 `config.json` 中加入：

```json
{
  "agent_runtime": {
    "default_backend": "self_agent",
    "default_provider": "self_agent"
  }
}
```

如果要按能力路由，例如仅把 `chat` 切到自研、`ppt` 继续走 Hermes：

```json
{
  "agent_runtime": {
    "default_backend": "vnext_provider",
    "default_provider": "hermes_local",
    "capability_routes": {
      "chat": {
        "backend": "self_agent",
        "provider": "self_agent"
      }
    }
  }
}
```

说明：

- 当前默认值仍是 `vnext_provider + hermes_local`
- `V5 UI` 入口不变，切换只发生在运行时路由层
- `Studio/PPT/Chat/Work` 都通过同一个 `V5AgentWorker` 入口受这个配置影响
- 当前也可以直接在 `Settings -> Engine` 中配置：
  - `Agent Mode`: `Third-Party Agent` / `Self Agent`
  - `Agent Provider`: `Hermes Local` / `Self Agent`
  - `Agent Model`: 默认为 `default`
  - `Capability Routes`: 可对 `chat / explain / coding / ppt / translate` 单独指定 `Default / Self Agent / Hermes Local`
  - `Fallback Policy`: 可开启自动 fallback，并分别配置 `On Timeout` 与 `On Protocol Error`

### 2. 验证 `gui_next` 交互测试窗

这只是 `vnext` 验证入口，不是系统级正式 UI：

```bash
bash scripts/start_vnext_smart_copilot.sh
```

这条链路会连接：

- `gui_next/smart_copilot/shell/interactive_window.py`
- `/vnext/context/snapshots`
- `/vnext/tasks`
- `/vnext/tasks/{id}/events`
- `/vnext/apply/preview`
- `/vnext/apply/commit`

默认行为：

- 默认连接 `http://127.0.0.1:8010`
- 若 `:8010` 已存在但未挂载 `vnext`，脚本会回退探测 `http://127.0.0.1:8000`
- 若目标地址不可用，会自动拉起 `smart_copilot_api:app`
- 当前默认仍使用 `Hermes local provider`，除非显式配置 `agent_runtime`

无界面冒烟方式：

```bash
python -m gui_next.smart_copilot.app --smoke-test
```

## 二、手动预热方式

如果你不希望 UI 在首次请求时自动拉起 API，可以先手动启动：

```bash
python3 -m uvicorn smart_copilot_api:app --host 127.0.0.1 --port 8010 --reload
```

如果你需要指定其他 API 地址：

```bash
SMART_COPILOT_API_BASE_URL=http://127.0.0.1:8012 bash scripts/start_ui.sh
```

如果你不希望 `gui_next` 测试脚本自动拉起 API：

```bash
bash scripts/start_vnext_smart_copilot.sh --no-start-api
```

## 三、当前进程关系

| 服务 | 端口 | 是否必需 | 当前职责 |
|------|------|----------|----------|
| **Broker** | `18889` | 系统级交互必需 | 获取选区、活动文档、浏览器内容、文本回写 |
| **vnext API** | `8010` 优先，`8000` 回退 | AI 执行必需 | 承载 `/vnext/*` 路由 |
| **Hermes API Server** | 按 profile 自动发现 | AI 执行必需 | 真正执行第三方智能体任务 |
| **UI** | - | 必需 | `smart_copilot.py` 启动桌面界面，进入 `V5` 导航层 |

注意：

- 当前系统级 Hermes 链路不再要求单独启动旧 `Agent Pipeline :18888`
- `:8000` 在这台机器上可能存在旧 API 进程，因此桌面主链路默认优先使用 `:8010`

## 四、日志与排查位置

关键日志位置：

- `V5` UI 结构化埋点：由 `gui/v5/telemetry.py` 写入现有 observability 链路
- 本地 `vnext API` 日志：`/tmp/opencopilot-vnext-api.log`
- OpenCopilot 自动拉起的 Hermes gateway 日志：`/tmp/opencopilot-hermes/opencopilot-gateway.log`
- 当前运行态调试日志：`.dbg/trae-debug-log-v5-hermes-runtime.ndjson`

当你要确认当前是否真的走了 `V5 UI -> Hermes`，重点看这些字段：

- `ui_version=v5`
- `ui_surface=desktop`
- `agent_backend=hermes_vnext`
- `provider=hermes_local`

## 五、常见问题

### Q1: 为什么现在不再写 `18888 Agent Pipeline`？

因为当前系统级主链路已经改成：

- `V5 UI`
- `V5AgentWorker`
- `/vnext/*`
- `hermes_local`

继续把桌面主链路写成依赖旧 `18888`，会误导排查方向。

### Q2: 我什么时候需要手动启动 API？

以下场景建议手动预热 `8010`：

- 你要联调 `/vnext/*` 接口
- 你要稳定抓 API 进程日志
- 你希望避免首次请求时的自动拉起等待

如果你只是验证桌面主链路，通常可以直接启动 `UI + Broker`。

### Q3: Broker 启动报权限不足怎么办？

Broker 需要 macOS 辅助功能权限：

1. 打开「系统设置 -> 隐私与安全性 -> 辅助功能」
2. 添加并勾选当前终端应用，如 `Terminal.app` 或 `iTerm2`
3. 如涉及截图/视觉能力，再补充授予「屏幕录制」
4. 完全退出终端后重新启动

### Q4: 怎么确认是不是又打到了旧 `:8000`？

优先检查：

```bash
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/vnext/tasks -X POST -H 'Content-Type: application/json' -d '{}'
```

如果 `:8010` 不可用，再检查 `:8000`。当前桌面主链路默认优先走 `:8010`，就是为了降低误撞旧分支 API 的风险。

### Q5: Broker / API / Hermes 分别怎么探活？

```bash
# Broker（需要 token）
curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health

# vnext API
curl http://127.0.0.1:8010/health

# Hermes API Server
curl http://127.0.0.1:8642/health
```
