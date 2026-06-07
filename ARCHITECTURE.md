# OpenCopilot 系统架构

> 版本 v5.0 | 2026-06-02 | 按当前实现修订 · 区分设计目标与已落地能力

---

## 一、文档定位

本文档描述的是当前仓库里的真实架构，而不是历史规划稿的目标态。

当前代码有两个需要同时理解的现实：

- `gui/v5/` 已经进入主交互入口，v5 的 `Smart Copilot / Workspace / Studio / Settings` 都有实际代码和运行链路。
- 旧版兼容路径仍然存在，桌面 UI 的 AI 调用与 HTTP 服务调用也还没有完全收敛成单一路径。

因此，OpenCopilot 当前是一个“v5 交互层已上线、核心 Pipeline 已统一、外围兼容层仍在收敛”的系统。

---

## 二、总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                         PyQt6 Desktop UI                        │
│  smart_copilot.py -> gui/main.py -> CopilotManager             │
│                                                                 │
│  v5 主交互层                                                    │
│  ├─ gui/v5/smart_copilot.py   (Work / Chat / Studio)           │
│  ├─ gui/v5/workspace.py       (Sidebar + 5 Panel)              │
│  ├─ gui/v5/studio_window.py   (4-Panel Studio shell)           │
│  ├─ gui/v5/settings_dialog.py (Unified Settings)               │
│  └─ gui/v5/navigation.py      (窗口生命周期与跳转中枢)            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
┌────────────────────────────┐  ┌────────────────────────────────┐
│ Desktop Direct Path         │  │ HTTP / Service Path            │
│ gui/v5/agent_worker.py      │  │ smart_copilot_api.py           │
│ gui/workers/*.py            │  │ api/routers/*                  │
│ -> opencopilot.agent.caller │  │ -> 调用独立 Agent 服务 :18888   │
│ -> 直接复用 Pipeline 实现    │  │ -> 对外提供 /api/* / docs      │
└───────────────┬────────────┘  └────────────────┬───────────────┘
                │                                 │
                └───────────────┬─────────────────┘
                                ▼
                  ┌──────────────────────────────┐
                  │ Agent Pipeline Core          │
                  │ SessionSetup                 │
                  │ -> SecurityGuard             │
                  │ -> ImmuneSystem              │
                  │ -> Planner                   │
                  │ -> StateTracking             │
                  │ -> CapabilityRouter          │
                  │ -> LLMProvider               │
                  └──────────────┬───────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
┌────────────────┐   ┌────────────────────┐   ┌────────────────────┐
│ Broker :18889  │   │ Capability Modules │   │ Knowledge / State  │
│ 系统探针        │   │ coding / search / │   │ memory / KG / logs │
│ 选区/文档/回写  │   │ ppt / translate   │   │ observability      │
└────────────────┘   └────────────────────┘   └────────────────────┘
```

### 2.1 核心结论

- 桌面 UI 的 AI 调用并不只依赖 HTTP，`V5AgentWorker` 和旧版 `AIWorker / ChatWorker` 都会通过 `opencopilot.agent.caller` 直接复用 Pipeline 实现。
- 独立 Agent 服务仍然重要，`AgentHealthWorker`、API Gateway、部分兼容链路和对外 HTTP 调用依赖 `:18888`。
- Broker 是系统级交互底座，选区读取、活动文档、浏览器内容、文本回写等能力都建立在 `:18889` 之上。

---

## 三、v5 交互层架构

### 3.1 NavigationManager 中枢

`gui/v5/navigation.py` 是 v5 的窗口中枢，职责包括：

- Smart Copilot / Workspace / Studio / Settings 的创建与单实例管理
- 跨窗口跳转，如 `Work -> Chat`、`Studio -> Chat`
- 生命周期控制，避免窗口间互相 import 导致循环依赖

这意味着窗口关系不再靠各个 widget 彼此直接调用来维护。

### 3.2 Smart Copilot v5

`gui/v5/smart_copilot.py` 当前已落地：

- 3 Tab 主壳：`Work / Chat / Studio`
- 顶部状态点、设置入口、关闭行为
- 文本拖放共享到多个 Tab
- 与 `NavigationManager` 的联动

当前仍在迭代：

- 更丰富的 Markdown 呈现
- 更完整的命令面板和技能整合
- 更细的状态与错误反馈

### 3.3 Workspace v5

`gui/v5/workspace.py` 已具备：

- Sidebar + 5 Panel 窗口壳
- `Task / Chat / Files / Memory / Settings` 切换结构
- 基础刷新钩子与设置入口

但要明确：当前更多是结构骨架，而不是全部业务完成态。Task / Chat / Files / Memory 面板仍有较多占位式内容和待接入逻辑。

### 3.4 Studio v5

Studio 由两层组成：

- `gui/v5/studio_tab.py`：Smart Copilot 中的 Studio 入口与快速创建器
- `gui/v5/studio_window.py`：独立的 4-Panel Studio 窗口

当前已落地：

- 独立窗口生命周期
- `Source / Outline / Preview / 底部 AI 区` 的窗口壳
- 文本/slides 加载
- PPT 导出和全屏预览钩子
- `/api/studio/*` 路由支撑缩略图渲染、差异预览、全屏预览、Studio 会话状态

当前未完整落地：

- 缩略图拖拽排序
- 真正的 WYSIWYG 预览编辑
- 可分离 AI 对话
- 统一撤销栈
- 完整的差异确认工作流

### 3.5 Unified Settings

`gui/v5/settings_dialog.py` 是当前 v5 落地度最高的模块之一：

- Sidebar + Content Area
- `Engine / Appearance / Shortcuts / Advanced` 四分区
- 配置持久化通过 `gui/v5/bridge.py`
- LLM 连接测试采用子线程，避免阻塞 UI

---

## 四、Agent Pipeline 架构

### 4.1 7 层中间件

当前主干 Pipeline 为 7 层：

| 层级 | 中间件 | 职责 |
|------|--------|------|
| 1 | `SessionSetupMiddleware` | 恢复会话、构建上下文、注入 persona / 翻译方向 |
| 2 | `SecurityGuardMiddleware` | 权限校验、速率限制 |
| 3 | `ImmuneSystemMiddleware` | 规则检查、危险内容拦截 |
| 4 | `PlannerMiddleware` | 复杂度判断与计划生成 |
| 5 | `StateTrackingMiddleware` | 状态追踪、任务记录 |
| 6 | `CapabilityRouterMiddleware` | 将请求分发到 coding / search / knowledge / ppt / llm |
| 7 | `LLMProviderMiddleware` | 最终执行 LLM 调用与流式输出 |

### 4.2 为什么不是单体 Prompt 拼接

OpenCopilot 当前坚持 Pipeline 化，而不是“把上下文都拼成一个 prompt 后一次性发给 LLM”，原因是：

- 安全可以前置短路
- 链路可观测
- 能力可替换
- 取消可沿链路传播

### 4.3 caller.py 的角色

`opencopilot.agent.caller` 是当前架构里的关键桥接层：

- 为桌面线程世界提供 `call_agent_pipeline_sync()`
- 为 FastAPI / async 世界提供 `call_agent_pipeline_async()`
- 用持久化全局 `event loop` 桥接同步与异步调用
- 提供 session 级串行锁，减少同一会话重复回复和竞争问题

这部分是当前“共用同一套 Pipeline 实现，但同时服务桌面 UI 和 HTTP 入口”的核心基础设施。

---

## 五、Bridge 与 Broker

### 5.1 Broker

Broker 不是普通业务 API，而是系统级探针。它负责：

- 获取当前选区
- 获取活动文档信息
- 获取浏览器内容
- 回写文本到当前应用或 IDE

没有 Broker，OpenCopilot 仍能显示 UI，但系统级上下文获取与回写能力会明显退化。

### 5.2 v5 Bridge

`gui/v5/bridge.py` 负责非 AI 操作的直接桥接：

- 获取上下文来源内容
- 复制到剪贴板 / 回写 IDE
- 导出 PPT
- 保存 Engine / Appearance / Shortcuts / Advanced 配置

因此当前 v5 的调用分工是：

- AI 请求：`V5AgentWorker -> caller.py -> Pipeline`
- 非 AI 操作：`bridge.py -> 本地 Python 模块 / Broker / 配置系统`

---

## 六、代码组织

```text
OpenCopilot/
├── gui/
│   ├── main.py                  # CopilotManager + 主入口
│   ├── v5/                      # v5 主交互层
│   │   ├── navigation.py
│   │   ├── smart_copilot.py
│   │   ├── work_tab.py
│   │   ├── chat_tab.py
│   │   ├── studio_tab.py
│   │   ├── studio_window.py
│   │   ├── workspace.py
│   │   ├── settings_dialog.py
│   │   ├── bridge.py
│   │   └── agent_worker.py
│   ├── window.py                # 旧版/兼容悬浮卡片
│   ├── workspace.py             # 旧版/兼容工作台
│   └── workers/                 # 旧版 worker + 健康检查
├── opencopilot/
│   ├── agent/                   # caller / pipeline / observability / log_store
│   ├── capabilities/            # coding / ppt / memory / search / skill / knowledge
│   ├── safety/                  # security / immune / planner
│   ├── broker/                  # Broker client / abstractions
│   └── providers/               # LLM providers
├── api/
│   └── routers/                 # chat / system / studio / workspace / config ...
├── asu_custom_agent.py          # 独立 Agent 服务入口 (:18888)
├── asu_broker/                  # 独立 Broker 服务入口 (:18889)
├── smart_copilot_api.py         # API Gateway (:8000)
└── docs/                        # 维护文档
```

---

## 七、关键数据流

### 7.1 v5 Work / Chat AI 请求

```text
用户操作
  -> gui/v5/work_tab.py 或 gui/v5/chat_tab.py
  -> V5AgentWorker
  -> opencopilot.agent.caller.call_agent_pipeline_sync()
  -> PipelineContext 构建
  -> 7 层 Pipeline
  -> 流式 chunk 回传 UI
```

### 7.2 v5 非 AI 操作

```text
用户操作
  -> gui/v5/bridge.py
  -> Broker / 配置系统 / 本地模块
  -> 结果直接回到 UI
```

### 7.3 API Gateway 路由

```text
HTTP Client
  -> smart_copilot_api.py / api/routers/*
  -> 独立 Agent 服务 :18888 或本地业务模块
  -> JSON / SSE 返回
```

---

## 八、部署与运行形态

### 8.1 当前真实运行形态

当前仓库不是“单一网关承载一切”的纯收敛架构，而是以下形态并存：

- 桌面进程内直调 Pipeline
- 独立 Agent 服务
- API Gateway
- 独立 Broker

### 8.2 推荐理解方式

- 关注桌面交互，看 `gui/v5/`、`bridge.py`、`agent_worker.py`
- 关注 AI 执行链路，看 `opencopilot/agent/`、`asu_custom_agent.py`
- 关注 HTTP 能力，看 `smart_copilot_api.py`、`api/routers/`
- 关注系统级采集与注入，看 `asu_broker/` 与 Broker client

---

## 九、当前架构判断

当前 OpenCopilot 的架构优点是：

- v5 交互层已经有清晰边界
- Pipeline 主链路已经形成统一语义中心
- 调用器桥接让桌面与服务端共享同一套核心逻辑
- Broker 让“系统级右键 AI”这个定位成立

当前仍需继续收敛的问题是：

- 新旧 UI 与兼容路径仍然并存
- 桌面直调与 HTTP 服务模式仍是双轨
- Studio / Workspace 的很多高级交互还停留在骨架态
- 部分文档与脚本仍保留历史口径，需要持续清理

一句话总结：

OpenCopilot 当前不是“所有 v5 目标都完成”的终态，而是一个 v5 交互层已上线、核心 Pipeline 已统一、外围兼容层仍在持续收敛的系统。
