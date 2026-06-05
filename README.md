# OpenCopilot 🚀

> **macOS 系统级 AI Copilot** — 任何软件中，选中、双击右键，AI 就来了。
>
> 不切换窗口 · 不复制粘贴 · 不打断心流

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%2012%2B-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-green" alt="python">
  <img src="https://img.shields.io/badge/version-v4.0-orange" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
</p>

---

## 交互哲学

OpenCopilot 的核心理念是**零上下文切换**。传统 AI 助手要求你离开当前工作、打开聊天窗口、组织 prompt、再切回来——这个"心流断层"是效率杀手。

我们重新设计了人机交互路径：

```
传统 AI 助手工作流：
  编辑器 → ⌘C → ⌘Tab 切到浏览器 → 打开 ChatGPT → ⌘V → 输入指令 → 等待 → ⌘C 结果 → ⌘Tab 切回 → ⌘V
  断裂次数: 6 次上下文切换

OpenCopilot 工作流：
  编辑器 → 选中文字 → 双击右键 → 选指令 → 看结果
  断裂次数: 0
```

### 三种交互姿态

| 姿态 | 触发方式 | 意图 | 卡片形态 |
|------|----------|------|----------|
| **瞬时参谋** | 双击右键 | "这里帮我看看" | 半透明悬浮卡片，鼠标旁弹出 |
| **深度工作台** | 三击右键 | "我有复杂的任务" | 独立工作台窗口，支持多轮对话 |
| **拖拽投喂** | 选中 → 拖入卡片 | "就这段，帮我改" | 接收任意软件拖入的文本 |

**没有搜索框。没有聊天窗口。AI 在你需要的时候出现，不需要的时候消失。**

### 设计原则

- **不抢占焦点**：悬浮卡片不抢键盘焦点，打字不被中断
- **目光不离开**：卡片在鼠标旁弹出，不用移动视线
- **上下文自动携带**：选中的文字自动注入，不用解释"就上面那段"
- **多模态感知**：支持文字、截图、IDE 全文、浏览器网页、Office 文档

---

## 核心能力

### 🎯 智能分析（Auto）

选中任意内容，AI 自动判断内容类型并给出分析。

- 选中代码 → 架构师视角解析（设计模式、复杂度、改进建议）
- 选中新闻 → 提取要点、分析背景
- 选中数据表格 → 数据解读、趋势分析
- 不确定选什么指令？点「✨ 自动」就对了

```mermaid
graph LR
  A[选中文字] --> B[双击右键]
  B --> C[卡片弹出]
  C --> D[✨ 自动分析]
  D --> E[AI 判断类型]
  E --> F[结构化输出]
```

### 🌐 智能翻译

选中文本 → 双击右键 → 🌐 翻译。支持 8 种语言双向互译（中/英/日/韩/法/德/西/俄）。

**设计亮点**：翻译方向由系统自动判断，不是简单的"中→英"。从翻译对话框切换语言后，Pipeline 内部的 SessionSetup 中间件会动态注入翻译方向到 System Prompt，确保 LLM 准确理解目标语言。

### 💻 代码解析

不仅是语法高亮，而是**架构师级别**的代码审视：

- **设计模式识别**：自动识别 Factory、Strategy、Observer 等模式
- **复杂度分析**：圈复杂度、耦合度评估
- **改进建议**：性能瓶颈、安全风险、可读性问题
- **联动修订**：修改一段代码后，自动扫描全文找出需要同步调整的位置

配合 IDE 伴生插件，支持「选中代码 → AI 修改 → 回写到 IDE」的闭环。

```python
# 联动修订示例
# 你修改了函数签名：
def process(data: list[str], timeout: int = 30) -> dict:
    ...

# AI 自动发现需要同步的位置：
# ⚠️ L142: process(items) → 缺少新参数 timeout
# ⚠️ L287: result = process(data).get("key") → 返回值改为 dict，建议改为 result["key"]
```

### 📝 文档联动修订

修改文档中的一段话时，AI 自动扫描全文检查矛盾。

**输出三段结果**：
1. **修订后文本**：你要的那段改好了
2. **联动影响分析**：文档中其他需要同步调整的位置（带行号/段落引用）
3. **修订说明**：本次修改的逻辑依据

支持 `.md`、`.txt`、`.py`、`.docx`、`.pptx` 等格式。Word/PPT 文件通过 Privileged Broker 自动解析为纯文本进行交叉扫描。

### 📊 PPT 共创

从零到演示，AI 全流程参与：

| 阶段 | AI 角色 | 产出 |
|------|---------|------|
| 内容输入 | 拖入文档 / 输入主题 | 结构化素材 |
| 大纲生成 | AI 分析内容 → 规划幻灯片结构 | JSON 大纲（标题 + 每页要点） |
| 共创编辑 | 自然语言对话修改（"把这页改成左右对比布局"） | 实时幻灯片更新 |
| 内容分析 | 选中单页 → AI 分析逻辑、数据、表达 | 分析面板 |
| 优化建议 | AI 审视全片 → 提出 1-2 条优化建议 | 建议气泡 |

### 🔍 多源上下文感知

OpenCopilot 不只是"选文字查 AI"，它能主动获取你正在看的内容：

| 来源 | 触发方式 | 获取内容 |
|------|----------|----------|
| 任意软件高亮文字 | 双击右键（自动） | 系统级 AXUIElement 无感读取 |
| IDE 全文 | 点击「📥 读取全文」 | 整个代码文件 |
| 浏览器网页 | 点击「🌐 读取网页」 | 当前页面全文（Chrome/Safari/Brave/Edge/Arc） |
| 屏幕截图 | 点击「👁️ 视觉分析」 | 前台窗口截图 → 多模态分析 |
| 文件选择 | 点击「📝 全文修订」 | .docx / .pptx 自动解析 |

**你不需要告诉 AI "我刚才在看什么"——它已经知道了。**

### 🎭 角色工坊

点击卡片标题栏 🎭 图标，创建自定义 AI 角色。每个角色是一个 Markdown 文件（存放在 `personas/` 目录），即时编辑生效：

```markdown
# 小红书文案专家
你是小红书爆款文案专家。风格要求：
- 每段不超过 3 行
- 大量 emoji ✨🔥💯
- 多用感叹号和反问
- 结尾加 3-5 个话题标签
```

### 💬 连续对话

点击「💬 连续对话」进入多轮模式。AI 记住整个对话历史，支持逐步深入分析。配合任务工作台的「任务背景」功能，所有对话共享同一个上下文锚点。

---

## 技术架构

### 为什么是 Pipeline + Agent Loop？

传统 AI 助手直接拼接 prompt 扔给 LLM。OpenCopilot 引入**7 层异步 Pipeline**，每层独立可观测、可拦截、可降级：

```
用户请求
  │
  ▼
SessionSetup   ← 会话恢复、Persona 加载、上下文信封
  │
  ▼
SecurityGuard  ← 权限校验、速率限制（Lane Semaphore）
  │
  ▼
ImmuneSystem   ← 内容安全检测、危险命令过滤
  │
  ▼
Planner        ← 任务复杂度判断、执行计划生成
  │
  ▼
StateTracking  ← 会话状态追踪、任务创建
  │
  ▼
CapabilityRouter ← 能力路由（代码执行 / 知识检索 / 搜索 / LLM）
  │
  ▼
LLMAgent       ← Agent Loop 混合范式
  │
  ├─ SIMPLE  → One-Shot（~2s）：80% 的简单任务
  ├─ MEDIUM  → Plan-and-Solve（~10s）：多步骤任务
  └─ COMPLEX → Plan+ReAct（~20s）：需要纠错的复杂任务
```

**Pipeline 带来的好处**：
- 中间件高度可重用：新增能力只需加一个中间件
- 短路机制：安全检查不通过直接返回，不浪费 LLM Token
- 全链路可观测：24 个 Timer 埋点按 `action_type` 分类追踪
- 取消传播：用户发新消息 → `CancelledError` 沿异步栈干净传播，无粗暴截断

### OpenClaw 单进程架构

借鉴 Anthropic OpenClaw 的设计理念：

- **全局持久化 Event Loop**：全进程共享一个 `asyncio` 事件循环，不走 per-call daemon 线程
- **会话级序列化锁**：`asyncio.Lock` 确保同一 Session 同时只有一个 Pipeline
- **CancelledError 取消**：用户中断通过 `task.cancel()` 传播，无 5 秒硬超时

### 全链路可观测

SQLite 持久化日志 + stderr 实时输出，三层埋点覆盖所有入口：

- **入口层**：ChatWorker / AIWorker / TranslationDialog / PPT Widget → START / DONE / ERROR 事件
- **Caller 层**：`call_agent_pipeline_sync` / `async` → PIPELINE_START / DONE / TIMEOUT / CANCELLED
- **中间件层**：8 个中间件 24 个 Timer → 按 `action_type` 分类追踪耗时
- **AI 回复**：完整回复内容存入 `data_json`，可按 `session_id` 检索

---

## 快速开始

### 环境要求

- macOS 12+
- Python 3.11 ~ 3.13
- 终端程序需授予**辅助功能**和**屏幕录制**权限（系统设置 → 隐私与安全性）

### 安装

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -e .
```

### 启动

```bash
# 终端 1：API Gateway（自动带起知识图谱）
python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：Broker 特权代理（⚠️ 需 macOS 原生终端）
python3 opencopilot/broker/run.py

# 终端 3：UI
python3 smart_copilot.py
```

启动后，屏幕角落出现彩色光标特效。标题栏 🟢 表示就绪。

---

## 项目结构

```
OpenCopilot/
├── opencopilot/                  # 主包
│   ├── agent/                    #   Agent 核心 (Pipeline + Agent Loop + Caller)
│   │   ├── caller.py             #     统一调用器 (sync/async)，全局 Event Loop
│   │   ├── middlewares.py        #     7 层 Pipeline 中间件
│   │   ├── pipeline.py           #     Pipeline 引擎 + PipelineContext
│   │   ├── observability.py      #     全链路可观测性
│   │   └── log_store.py          #     SQLite 持久化日志
│   ├── capabilities/             #   能力层
│   │   ├── coding/               #     代码执行引擎
│   │   ├── knowledge/            #     知识检索 (知识图谱)
│   │   ├── search/               #     搜索引擎
│   │   ├── memory/               #     会话记忆管理
│   │   ├── skill/                #     声明式 Skill 系统
│   │   ├── ppt/                  #     PPT 共创引擎
│   │   └── state/                #     状态管理 (含 checkpoint/recovery)
│   ├── safety/                   #   安全层 (security/immune)
│   ├── broker/                   #   系统代理 (AXUIElement 无感划词/沙盒穿透)
│   ├── providers/                #   LLM 提供者
│   ├── observability/            #   可观测性模块
│   └── shared/                   #   共享工具 (prompt 构建/context 归一化)
├── api/                          # API 网关 (:8000)
│   ├── app.py                    #   路由工厂
│   └── routers/                  #   12 个独立路由模块
├── gui/                          # PyQt6 桌面应用
│   ├── main.py                   #   入口 + CopilotManager
│   ├── window.py                 #   AICardWindow 核心悬浮卡片
│   ├── workspace.py              #   AgentWorkspace 任务工作台
│   ├── workers/                  #   QThread Worker (ChatWorker/AIWorker)
│   └── dialogs/                  #   翻译/Persona 等对话框
├── personas/                     # AI 角色文件 (*.md)
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Trae/Cursor)
├── tests/                        # 测试 (unit / e2e / ablation)
├── scripts/                      # 守护进程/启动脚本
├── smart_copilot.py              # GUI 入口
├── smart_copilot_api.py          # API 入口
└── pyproject.toml
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [USER_GUIDE.md](USER_GUIDE.md) | 用户手册（交互方式、功能使用、权限配置、常见问题） |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构设计（Pipeline、Agent Loop、Skill 系统、Broker 协议） |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南（模块开发、测试体系、新增 Persona/Skill） |

---

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 基础交互、多引擎 AI、上下文感知 | ✅ |
| P1 | 特权 Broker、多模态视觉、无感划词 | ✅ |
| P2 | Persona 工坊、PPT 共创、知识图谱、Skill 架构 | ✅ |
| P3 | Agent Loop 重构、OpenClaw 单进程迁移、Pipeline 统一 | ✅ |
| P4 | v4.0 分层架构重构、代码治理、全链路可观测性 | ✅ |
| P5 | IDE Extension v2、Broker 产品化 | 🔶 进行中 |
| P6 | 上下文主动感知、多 Agent 协作 | 📋 计划中 |

---

## License

MIT © OpenCopilot Team
