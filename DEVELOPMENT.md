# OpenCopilot 开发指南

> 版本 v5.0 | 2026-06-02 | 按当前实现修订 · 统一开发入口与目录边界

---

## 一、文档目的

本指南只描述当前仓库的真实开发实践，重点解决三个问题：

- 新功能应该加在 `gui/v5/` 还是旧版 `gui/`
- 桌面端 AI 调用到底走哪条链路
- 本地开发时应该启动哪些服务

当前的总原则是：

- **新增桌面交互默认落在 `gui/v5/`**
- **新增 AI 能力默认接入共享 Pipeline**
- **只有兼容旧入口时，才继续修改旧版 `gui/window.py` / `gui/workspace.py`**

---

## 二、开发环境

### 2.1 前置要求

| 项目 | 要求 |
|------|------|
| OS | macOS 12+ |
| Python | 3.11 ~ 3.13 |
| 权限 | 辅助功能 + 屏幕录制 |
| 安装方式 | `pip install -e .` |

### 2.2 推荐开发启动方式

```bash
# 终端 1：Broker（必须用原生终端）
bash start_broker.sh

# 终端 2：Agent 服务（推荐，便于探活与 HTTP 兼容链路）
python3 asu_custom_agent.py

# 终端 3：API Gateway（调 /api/*、Swagger、Studio API 时需要）
python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 终端 4：UI
bash scripts/start_ui.sh
```

### 2.3 最小桌面开发组合

如果你只调 v5 桌面交互本身，最小组合通常是：

```bash
bash start_broker.sh
bash scripts/start_ui.sh
```

但为了保持健康检查、兼容链路与服务侧行为一致，开发时仍然**推荐同时启动**：

```bash
python3 asu_custom_agent.py
```

---

## 三、当前架构下的开发边界

### 3.1 UI 层

当前 UI 分两层：

| 层 | 目录 | 说明 |
|----|------|------|
| **v5 主交互层** | `gui/v5/` | 新增窗口、Tab、Settings、Studio、导航逻辑默认放这里 |
| **旧版兼容层** | `gui/window.py`、`gui/workspace.py`、`gui/workers/` | 历史路径和兼容行为，除非是修兼容 Bug，否则不建议继续扩展 |

**开发准则**：

- 新的 Smart Copilot 交互，改 `gui/v5/smart_copilot.py`
- 新的 Work 行为，改 `gui/v5/work_tab.py`
- 新的 Chat 行为，改 `gui/v5/chat_tab.py`
- 新的 Studio 行为，优先改 `gui/v5/studio_tab.py` / `gui/v5/studio_window.py`
- 新的统一设置行为，改 `gui/v5/settings_dialog.py`
- 新的跨窗口跳转，改 `gui/v5/navigation.py`

### 3.2 AI 调用层

当前所有 AI 调用应统一收敛到共享 Pipeline 实现：

```text
UI / API
  -> opencopilot.agent.caller
  -> PipelineContext
  -> MiddlewarePipeline
  -> LLM / capability modules
```

关键规则：

- 不允许在业务代码里直接绕过 Pipeline 调用底层 provider
- 不要在新功能里复制一套 prompt 拼接逻辑
- 如果需要新增 AI 行为，优先考虑：
  - 新 `action_type`
  - 新 capability 路由
  - 新 middleware

### 3.3 服务层

当前服务分工如下：

| 服务 | 端口 | 作用 |
|------|------|------|
| `asu_custom_agent.py` | `18888` | 独立 Agent 服务、健康检查、HTTP/SSE 兼容链路 |
| `asu_broker` | `18889` | 系统级选区/文档/浏览器/回写 |
| `smart_copilot_api.py` | `8000` | OpenAPI、HTTP 路由、部分 v5 API |

---

## 四、代码组织

### 4.1 当前推荐理解方式

```text
OpenCopilot/
├── gui/
│   ├── main.py                  # CopilotManager + 主入口
│   ├── v5/                      # v5 主交互层
│   │   ├── navigation.py        # 窗口中枢
│   │   ├── smart_copilot.py     # 3-Tab 主壳
│   │   ├── work_tab.py          # 快速处理
│   │   ├── chat_tab.py          # 连续对话
│   │   ├── studio_tab.py        # Studio 入口
│   │   ├── studio_window.py     # 独立 Studio 窗口
│   │   ├── workspace.py         # Workspace v5
│   │   ├── settings_dialog.py   # 统一设置
│   │   ├── bridge.py            # 非 AI 操作桥接
│   │   └── agent_worker.py      # v5 AI 调用封装
│   ├── window.py                # 旧版卡片（兼容）
│   ├── workspace.py             # 旧版工作台（兼容）
│   └── workers/                 # 旧版 Worker / 探活
├── opencopilot/
│   ├── agent/                   # caller / pipeline / observability / log_store
│   ├── capabilities/            # coding / knowledge / ppt / skill / search / memory / state
│   ├── safety/                  # security / immune / planner
│   ├── broker/                  # broker client / abstraction
│   └── providers/               # LLM providers
├── api/
│   └── routers/                 # chat / config / studio / workspace / system ...
├── asu_custom_agent.py          # 独立 Agent 服务入口
├── asu_broker/                  # 独立 Broker 服务入口
├── smart_copilot_api.py         # API Gateway
└── tests/
```

### 4.2 典型调用链

#### v5 Work / Chat 的 AI 调用

```text
gui/v5/work_tab.py 或 gui/v5/chat_tab.py
  -> V5AgentWorker
  -> opencopilot.agent.caller.call_agent_pipeline_sync()
  -> 7 层 Pipeline
  -> chunk 流式回传 UI
```

#### v5 非 AI 操作

```text
gui/v5/bridge.py
  -> Broker / 本地模块 / 配置系统
  -> 直接回 UI
```

#### API 路由

```text
api/routers/*
  -> 本地业务模块 或 call_agent_pipeline_async()
  -> JSON / SSE 输出
```

---

## 五、如何新增功能

### 5.1 新增桌面交互

先判断这个功能属于哪一类：

| 功能类型 | 放置位置 |
|----------|----------|
| Smart Copilot 主窗口行为 | `gui/v5/smart_copilot.py` |
| Work Tab 动作或展示 | `gui/v5/work_tab.py` |
| Chat Tab 会话或流式渲染 | `gui/v5/chat_tab.py` |
| Studio 入口或 PPT 生成入口 | `gui/v5/studio_tab.py` |
| Studio 独立窗口编辑能力 | `gui/v5/studio_window.py` |
| 新设置项 | `gui/v5/settings_dialog.py` + `gui/v5/bridge.py` |
| 跨窗口链路 | `gui/v5/navigation.py` |

### 5.2 新增 API 端点

在 `api/routers/` 中创建新路由模块，优先复用现有业务模块或 Pipeline：

```python
from fastapi import APIRouter
from opencopilot.agent.caller import call_agent_pipeline_async

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.post("")
async def my_endpoint(request: MyRequest):
    chunks = []
    async for chunk in call_agent_pipeline_async(
        request.text,
        action_type="my_feature",
    ):
        chunks.append(chunk)
    return {"response": "".join(chunks)}
```

### 5.3 新增 AI 能力

新增 AI 能力时，按这个顺序判断：

1. 只是已有能力的一个新动作：加 `action_type`
2. 需要新的执行分支：加到 capability router
3. 需要前置/后置控制：加 middleware
4. 需要对外 HTTP：再补 `api/routers/*`

不要做的事：

- 不要在 UI 层直接调用 provider
- 不要复制一套 prompt 拼接逻辑
- 不要在多个地方分别维护同一种 AI 行为

### 5.4 新增中间件

如果功能属于全链路能力，例如：

- 安全前置
- 上下文补充
- 任务规划
- 观测埋点
- 输出后处理

就应该做成 middleware，而不是塞进某个页面按钮逻辑里。

---

## 六、测试策略

### 6.1 运行方式

```bash
# 全量
python -m pytest tests/ -v

# 单元测试
python -m pytest tests/unit/ -v

# E2E
python -m pytest tests/e2e/ -v

# v5 相关测试
python -m pytest tests/unit/test_v5_* -v
```

### 6.2 当前重点

凡是改动以下模块，优先补或跑相关测试：

| 模块 | 建议测试 |
|------|----------|
| `gui/v5/*` | `tests/unit/test_v5_*` |
| `gui/v5/agent_worker.py` | `tests/unit/test_v5_agent_worker.py` |
| `gui/v5/navigation.py` | `tests/unit/test_v5_navigation.py` |
| `gui/v5/settings_dialog.py` | `tests/unit/test_v5_settings.py` |
| `gui/v5/workspace.py` | `tests/unit/test_v5_workspace.py` |
| `gui/v5/studio*` | `tests/unit/test_v5_studio*.py` |

### 6.3 测试原则

- 优先验证真实业务链路，而不是只测静态 helper
- UI 壳层改动优先补单元测试
- Pipeline 改动优先覆盖路由、短路、流式输出和错误恢复
- 文档更新不需要额外测试，但要保证与当前实现口径一致

---

## 七、调试技巧

### 7.1 端口与健康检查

```bash
lsof -i :18888   # Agent
lsof -i :18889   # Broker
lsof -i :8000    # API Gateway

curl http://127.0.0.1:18888/health
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health
```

### 7.2 直接测试共享 Pipeline

```bash
python - <<'PY'
from opencopilot.agent.caller import call_agent_pipeline_sync

for chunk in call_agent_pipeline_sync("Hello", action_type="chat"):
    print(chunk, end="")
PY
```

### 7.3 日志与观测

可重点关注：

- `PipelineObservability`
- `LogStore`
- `~/.opencopilot/logs/` 或相关 SQLite 日志库

如果是 UI 侧问题，优先看：

- `gui/v5/agent_worker.py`
- `gui/v5/bridge.py`
- `gui/v5/navigation.py`

---

## 八、当前开发注意事项

### 8.1 不要继续把旧版 gui 当主入口扩展

`gui/window.py` 和 `gui/workspace.py` 仍然存在，但新需求默认不要先加到那里，除非你明确是在修兼容行为。

### 8.2 Studio / Workspace 仍有骨架态

开发时要有这个预期：

- Studio 的独立窗口和生成入口已存在
- 但高级编辑体验还没完全补完
- Workspace 的结构已完成，但很多业务面板仍待接入

所以不要在文档或 PR 描述里把这些能力写成“全部完成”。

### 8.3 Agent 服务与共享 Pipeline 要区分

- 共享 Pipeline 实现是核心逻辑中心
- `:18888` 是独立服务形态

开发时不要把“服务进程”和“核心实现”混为一谈。

---

## 九、常见问题

| 问题 | 解决方式 |
|------|----------|
| 双击右键没反应 | 先检查辅助功能权限和 Broker 是否运行 |
| UI 能打开但 AI 不正常 | 检查 `gui/v5/agent_worker.py` 链路、LLM 配置和 Agent 探活状态 |
| API 路由正常但桌面行为异常 | 区分是 HTTP 路径问题还是桌面直调 Pipeline 问题 |
| Studio / Workspace 看起来“不完整” | 这是当前版本状态，不一定是 Bug，先核对是否属于占位功能 |
| Qt 插件或 UI 闪退 | 优先使用 `bash scripts/start_ui.sh` 启动 |
