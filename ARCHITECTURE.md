# OpenCopilot 系统架构

> 版本 v4.0 | 2026-06-04 | 分层架构 · OpenClaw 单进程 · Agent Loop 混合范式

---

## 一、总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     PyQt6 UI Layer                            │
│  smart_copilot.py · AICardWindow · AgentWorkspace             │
│  鼠标监听 · 光标特效 · 悬浮卡片 · 拖拽投喂                       │
└──────────────────────────┬───────────────────────────────────┘
                           │ opencopilot/agent/caller.py
                           │ (统一调用器 sync/async)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  API Gateway (:8000)                          │
│  smart_copilot_api.py · FastAPI + uvicorn                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              7 层异步 Pipeline                          │  │
│  │  SessionSetup → SecurityGuard → ImmuneSystem            │  │
│  │  → Planner → StateTracking → CapabilityRouter           │  │
│  │  → LLMProviderMiddleware                                │  │
│  │                                                         │  │
│  │  LLMAgentMiddleware 内部:                                │  │
│  │  ┌─────────────────────────────────────────────────┐   │  │
│  │  │        Agent Loop (动态范式选择)                   │   │  │
│  │  │  复杂度判断 (_is_complex) → 选择范式               │   │  │
│  │  │  · SIMPLE  → One-Shot (直接 LLM 回答)             │   │  │
│  │  │  · MEDIUM  → Plan-and-Solve (计划→执行→汇总)       │   │  │
│  │  │  · COMPLEX → Plan + ReAct (偏差回退纠错)           │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Lane Semaphore: chat:10 · coding:3 · ppt:5                  │
└──────────────────────────┬───────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│   Broker     │  │  知识图谱     │  │  Capability       │
│   :18889     │  │  :8090       │  │  Modules          │
│              │  │              │  │  ├─ CodeExecutor  │
│  系统探针    │  │  264 实体    │  │  ├─ KnowledgeRetr │
│  无感划词    │  │  166 关系    │  │  ├─ SearchEngine  │
│  沙盒穿透    │  │  27 API      │  │  ├─ MemorySystem  │
│  屏幕抓取    │  │              │  │  └─ StateManager  │
└──────────────┘  └──────────────┘  └──────────────────┘
```

---

## 二、核心设计

### 2.1 Pipeline 管线

Pipeline 采用责任链模式，5 层异步中间件顺序执行：

| 层 | 中间件 | 职责 |
|----|--------|------|
| 1 | SessionSetupMiddleware | 创建/恢复会话，加载 memory、persona |
| 2 | SecurityGuardMiddleware | 权限校验、速率限制 (Lane Semaphore) |
| 3 | ImmuneSystemMiddleware | 内容安全检测、危险命令过滤 |
| 4 | PlannerMiddleware | 任务复杂度判断、执行计划生成 |
| 5 | StateTrackingMiddleware | 会话状态追踪 |
| 6 | CapabilityRouterMiddleware | 能力路由（coding/knowledge/search等） |
| 7 | LLMProviderMiddleware | Agent Loop 执行、LLM 调用 |

每层均可提前返回（短路）或 `await next_fn()` 传递到下一层。

### 2.2 Agent Loop 混合范式

**复杂度判断**（规则驱动，不调 LLM）：

```python
def _is_complex(text, action_type):
    if action_type in ("coding", "ppt"):
        return TaskComplexity.MEDIUM if len(text) > 200 else TaskComplexity.SIMPLE
    if any(kw in text for kw in ["先", "然后", "接着", "第一步"]):
        return TaskComplexity.MEDIUM
    return TaskComplexity.SIMPLE
```

**三种范式**:

| 范式 | 适用 | Token 倍数 | 延迟 | 说明 |
|------|------|-----------|------|------|
| One-Shot | 80% 简单任务 | 1x | 2-4s | 翻译、对话、简单问答 |
| Plan-and-Solve | 中等复杂 | 2-3x | 8-15s | 多步数据处理、代码审查 |
| Plan+ReAct | 少数复杂 | 3-5x | 15-30s | 探索性任务、需要纠错 |

### 2.3 统一调用器

所有模块通过 `opencopilot/agent/caller.py` 调用 Agent：

```python
# 同步版（供 QThread / CLI 使用）
# 通过全局持久化 event loop + asyncio.run_coroutine_threadsafe 桥接异步 Pipeline
# 取消通过 task.cancel() 传播 CancelledError，无需硬超时
from opencopilot.agent import call_agent_pipeline_sync
for chunk in call_agent_pipeline_sync(text, action_type="chat"):
    print(chunk)

# 异步版（供 FastAPI 使用）
from opencopilot.agent.caller import call_agent_pipeline_async
async for chunk in call_agent_pipeline_async(text, action_type="coding"):
    await response.write(chunk)
```

**同步桥接架构**（参考 OpenClaw 单进程持久化 loop）：

```
QThread (sync) ──→ call_agent_pipeline_sync()
                       ↓
              _EventLoopBridge (全局单例 loop, run_forever)
                       ↓
              asyncio.run_coroutine_threadsafe(_run_pipeline)
                       ↓
              Pipeline.execute(ctx) [在全局 loop 中 asyncio 并发]
                       ↓
              asyncio.Queue → queue.Queue → Generator[yield chunk]
```

**调用关系**:

```
smart_copilot.py (QThread) ──→ call_agent_pipeline_sync()
smart_copilot_api.py         ──→ call_agent_pipeline_async()
opencopilot/capabilities/ppt/──→ call_agent_pipeline_sync()
dialogs/translation_dialog.py ──→ call_agent_pipeline_sync()
```

### 2.4 Skill 系统

内置 7 个 Skill（自动注册），声明式 Skill 文件位于 `skills/` 目录：

| Skill | 类型 | 说明 |
|-------|------|------|
| KnowledgeSkill | 内置 | 知识检索 |
| CodingSkill | 内置 | 代码生成与执行 |
| PPTSkill | 内置 | PPT 生成与编辑 |
| EvaluationSkill | 内置 | 翻译/内容质量评估 |
| FileSkill | 内置 | 文件读写操作 |
| FormatSkill | 内置 | Markdown→DOCX/PPTX 转换 |
| PersonaSkill | 内置 | 人设角色管理 |

扩展 Skill：在 `skills/` 目录下创建 `SKILL.md`（YAML frontmatter + Markdown 格式）。

---

## 三、关键模块

### 3.1 代码组织 (v4.0)

```
opencopilot/                     # 主包
├── agent/            Agent 核心 (Pipeline + Loop + Caller + Context)
├── capabilities/     能力层 (coding · knowledge · search · memory · state · skill · ppt · tools)
├── safety/           安全层 (security · immune · planner)
├── providers/        LLM 提供者 (MiMo · MiniMax · Ollama)
├── broker/           系统代理 (探针 · 划词 · 沙盒 · 屏幕)
├── observability/    可观测性 (日志 · 指标 · 追踪 · 健康)
├── config/           配置管理
└── shared/           共享工具 (prompt · adapter · cursor · renderer)

api/
├── app.py            路由工厂
├── models.py         Pydantic 模型
└── routers/          12 个独立路由 (chat · system · file · config · persona · ppt · text · knowledge · coding · tasks · evaluation)

gui/
├── main.py           入口 + CopilotManager
├── window.py         AICardWindow
├── workspace.py      AgentWorkspace
├── workers/          7 个 QThread Worker
└── dialogs/          对话框
```

### 3.2 LLM Provider

`opencopilot/providers/` 支持多 Provider：

```
MiMo (默认) → MiniMax → Ollama (本地)
```

全链路原生异步（`httpx.AsyncClient`）。

---

## 四、数据流示例

### 用户选中文本 → 快捷 AI 分析

```
1. 用户选中文本 → 双击右键
2. smart_copilot.py 探活 API Gateway (:8000/health)
3. 用户点击快捷指令 → AIWorker.run()
4. call_agent_pipeline_sync(text, action_type, context_source)
5. Pipeline: SessionSetup → Security → Immune → Planner → LLMAgent
6. LLMAgentMiddleware:
   - _is_complex() → SIMPLE
   - One-Shot: 直接 LLM 流式输出
7. SSE chunk → AIWorker.text_updated → GUI 流式渲染
```

### 连续对话（AICardWindow / AgentWorkspace）

```
1. 用户输入文本 → send_chat_message()
2. append_chat_message("AI", "正在思考...") 写入占位符
3. 记录 _chat_stream_start = cursor.position()  ← 流式起点
4. ChatWorker.run() → call_agent_pipeline_sync(text, "chat")
5. 每个 chunk: ChatWorker.text_updated.emit(display_text)
6. on_chat_updated(text):
   - cursor.setPosition(_chat_stream_start)    ← 定位到流式起点
   - movePosition(End, KeepAnchor)             ← 选中区间
   - removeSelectedText()                      ← 删除旧内容
   - insertHtml(md_render(text))               ← 写入 Markdown 渲染结果
7. 完成: on_chat_finished() — 无输出时清除占位符
```

> **关键设计**：使用绝对光标位置 `_chat_stream_start` 而非 `StartOfBlock`，因为 `md_render()` 可能生成多个 `<p>` block（多段落 Markdown），`StartOfBlock` 只能删除最后一个 block，导致多段落内容重复显示。

### 复杂任务：代码审查

```
1. call_agent_pipeline_sync(code, action_type="coding")
2. _is_complex() → MEDIUM
3. Plan-and-Solve:
   - PLAN: LLM 生成审查计划（语法→逻辑→安全→性能）
   - EXECUTE: 逐步执行每个审查步骤
   - SUMMARIZE: 汇总生成审查报告
4. 流式输出报告 + 修复建议
```

---

## 五、部署架构

```
macOS LaunchAgent (开机自启)
├── Broker            :18889  (持续运行)
├── Knowledge Graph   :8090   (可选)
└── API Gateway       :8000   (通过 uvicorn 启动)

UI (smart_copilot.py)  按需启动，唤出时探活
```

**生产部署**: `bash scripts/install_unified_daemon.sh`
**开发模式**: `python3 -m uvicorn smart_copilot_api:app --port 8000` + `python3 opencopilot/broker/run.py` + `python3 smart_copilot.py`

---

## 六、设计原则

1. **分层可迭代**：表示层(gui/api) → 应用层(agent) → 领域层(capabilities) → 安全层(safety) → 基础设施，层间接口契约
2. **Hub-and-Spoke 单进程**：API Gateway 承载一切，子系统通过接口注册
3. **Agent Loop 优先**：LLM 自主决策工具调用时机，非 if-else 分发器
4. **声明优于命令**：Skills = Markdown + YAML，非硬编码
5. **原生异步**：全链路 `async/await`，`httpx.AsyncClient`
6. **渐进式迁移**：旧模块通过兼容入口 re-export，零破坏重构
