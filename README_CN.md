# OpenCopilot 🚀

> **macOS 系统级 AI 右键菜单** — 在任何软件里，选中、双击右键、AI 就来了。
>
> 不是 IDE 插件 · 不是聊天窗口 · 不是自主 Agent · 是你和 AI 之间最短的路径

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%2012%2B-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-green" alt="python">
  <img src="https://img.shields.io/badge/version-v5.0-orange" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
  <a href="README.md">English</a>
</p>

---

## 定位：你和 AI 之间的最短路径

### 当前 AI 助手格局

2025-2026 年，桌面 AI 工具分化为四条路线：

| 路线 | 代表产品 | 模式 | 局限 |
|------|----------|------|------|
| **IDE 内嵌** | Cursor / Trae / Windsurf / Copilot | AI 嵌入编辑器，Tab 补全 + Chat 面板 | 离开 IDE 就失效；写邮件、做 PPT、看网页时无用 |
| **独立对话窗口** | Claude Desktop / ChatGPT Desktop | 独立 App + 文件/MCP 接入 | 工具虽强，但你需要把内容"喂"给它——复制粘贴或上传文件 |
| **桌面办公 Agent** | WorkBuddy / QoderWork / DuMate | AI 操作桌面，生成 Word/PPT/Excel | 快速出草稿，但充满幻觉——虚构数据、格式错乱、逻辑断裂 |
| **自主桌面 Agent** | OpenClaw / Hermes / Solo | AI 接管桌面，自主操作 | 强大但黑盒；出错时你插不上手；安全风险高 |

### OpenCopilot 的第五路线：系统级审查修正

OpenCopilot 不走上述任何一条。它的设计哲学是：**AI 是鼠标右键的延伸，不是另一个窗口。** 而它的杀手场景是：**当 WorkBuddy 生成了一份充满幻觉的草稿，OpenCopilot 帮你在不离开 Office 的情况下逐段审查、交叉验证、修正每一个问题。**

```
Cursor / Trae：
  你 → 切换到 IDE → 提问 → 等待 → 手动应用结果
  覆盖范围: ████████░░  仅 IDE 内

Claude Desktop：
  你 → ⌘Tab 切到 Claude → 打字描述 → ⌘C⌘V 内容 → 等待 → ⌘C⌘V 结果 → ⌘Tab 切回
  覆盖范围: ████████████ 任意软件，但需要你搬运内容

WorkBuddy / QoderWork：
  AI → 生成全量 PPT/文档 → 你打开审阅 → 发现幻觉 → ???
  覆盖范围: ████████████ 快速出稿，但审稿靠你自己

OpenClaw / Hermes：
  AI → 自主操作桌面 → 你旁观
  覆盖范围: ████████████ 任意软件，但你是乘客

OpenCopilot：
  WorkBuddy 出稿 → Office 打开 → 选中可疑内容 → 双击右键 → AI 审查并修正
  覆盖范围: ████████████ 任意软件，你审阅、AI 修正
```

**一句话区分**：
- Cursor 问你"你想写什么代码"——**你在 IDE 里**
- Claude Desktop 问你"把内容贴给我"——**你在聊天窗口里**  
- WorkBuddy 说"草稿给你"——**你一个人面对满篇幻觉**
- OpenClaw 说"我来操作"——**你在副驾驶**
- OpenCopilot —— WorkBuddy 生成，你审阅，OpenCopilot 修正——**AI 打稿，你把关**

### 办公 AI 时代：他们生成，你审查修改

2026 年的办公 AI 格局已经很清晰：**WorkBuddy / QoderWork / DuMate 在「快速出草稿」上趋于成熟**——输入一句话，3-10 分钟吐出一份 PPT/文档。但问题在于：

> 生成的草稿充满 AI 幻觉——虚构的数据、捏造的引用、逻辑矛盾、格式错乱。你需要一个工具来**审查和修正**这份草稿，而不是再生成一遍。

这正是 OpenCopilot 的位置：

```
传统工作流：
  WorkBuddy 出稿 → 你在 Office 里手动逐页审 → 发现可疑数字 → ???

OpenCopilot 工作流：
  WorkBuddy 出稿 → Office 打开审阅
    → 看到"Q2 营收 3800 万"→ 选中 → 双击右键 → "和 Excel 里的数据对得上吗？"
    → 看到逻辑断裂 → 选中 → 双击右键 → "检查这段话和前面第 3 页是否矛盾"
    → 表达不专业 → 选中 → 双击右键 → "润色，B2B 正式风格"
```

**4 个审查卖点**：

| 卖点 | 说明 |
|------|------|
| **Office 内直审** | 在 Word/WPS/PPT 里选中就分析，不切窗口 |
| **真实数据交叉验证** | 读取你手边的 Excel/文档做 ground truth 对比，不靠 LLM 记忆 |
| **Pipeline 多层审查** | ImmuneSystem 拦截危险输出 + CapabilityRouter 分类路由（数据核对/事实查证/风格检查） |
| **增量修改不动格式** | 只改你选中的文字，不动 python-pptx 生成的排版

### 为什么是系统级介入

OpenCopilot 通过 macOS **AXUIElement API**（辅助功能接口）在系统层面感知你的操作，不依赖任何特定软件的插件或 API：

- 选中文字 → 系统级事件监听，不依赖 ⌘C
- 读取浏览器网页 → AppleScript 桥接，不走扩展
- 读取 IDE 全文 → 伴生插件（可选），非强制
- 截图分析 → CGWindow API，无需软件支持

这意味着 OpenCopilot 在 **Word、PPT、浏览器、邮件、终端、Finder、任何文本编辑器** 中的交互体验完全一致。你不是在用一个"AI 写代码工具"或"AI 聊天工具"——你是在用一个"在任何软件里都能用的 AI 右键菜单"。

---

## 交互设计

### 三种交互姿态

| 姿态 | 触发方式 | 意图 | 形态 |
|------|----------|------|------|
| **瞬时参谋** | 双击右键 | "这里帮我看看" | 轻量浮层窗口，贴近鼠标出现，不抢焦点 |
| **深度工作台** | 三击右键 | "我有复杂的任务" | 独立工作台窗口，支持设定任务背景 + 多轮对话 |
| **拖拽投喂** | 选中 → 拖入卡片 | "就这段，帮我改" | 接收任意软件拖入的文本 |

**核心交互原则**：

- **不抢占焦点**：轻量浮层弹出不打断你的打字
- **目光不离开**：浮层贴近触发点出现，不强制视线跳转
- **上下文自动携带**：选中的文字自动注入，不需要解释"就是上面那段"
- **人始终在回路中**：每次交互由你触发，每条结果由你确认——不是黑盒 Agent，是增强你的"智能右键"

### v5.0 交互升级

**Smart Copilot 3-Tab 架构**：

| Tab | 功能 | 设计理念 |
|-----|------|---------|
| **Work** | 快速操作（Explain/Fix/Polish） | Primary/Secondary 按钮分层，Context Strip 数据源切换 |
| **Chat** | 连续对话 | Context Panel 显示可引用的上下文来源，Skill Panel 融入底部 |
| **Studio** | PPT 共创工作台 | 合并原 Tab 3 + Tab 5，直接打开 4-Panel 编辑器 |

**Agent Workspace 2.0**：

| 面板 | 功能 | 说明 |
|------|------|------|
| **Task** | 任务定义与管理 | 任务详情 + 历史 + 模板加载 |
| **Chat** | 会话列表 + 对话 | 多会话切换 + 持久化 |
| **Files** | 最近文件 + 拖放区 | 文件管理 + 上下文注入 |
| **Memory** | 知识与上下文 | 知识图谱 + 翻译记忆 + 术语库 |
| **Settings** | 引擎 / 主题 / 快捷键 / 角色 | 统一设置入口 |

**统一设置弹窗**：

- 4 个分区：Engine / Appearance / Shortcuts / Advanced
- 3 个入口：Smart Copilot Header / Workspace Sidebar / System Tray
- 替代原有 2 个独立设置弹窗

### v5.0 当前落地状态

v5 改版目前是**代码已部分落地，但尚未全部完工**。当前仓库中的真实状态如下：

| 区域 | 已在代码中落地 | 仍在进行中 |
|------|----------------|------------|
| **导航中枢** | `NavigationManager` 已统一管理 Smart Copilot / Workspace / Studio / Settings 生命周期 | 兼容路径里仍有部分旧窗口并存 |
| **Smart Copilot** | 3-Tab 主壳、拖拽共享、通过 `V5AgentWorker` 直连 Agent | 更完整的 Markdown 呈现、命令面板、上下文提示仍可继续打磨 |
| **Work / Chat** | 上下文获取、流式 AI 输出、会话基础能力、取消能力已具备 | 更复杂的上下文动作和会话管理仍待增强 |
| **Studio** | PPT 共创功能已完整实现：4-Panel 工作台、缩略图导航、差异预览编辑、AI 对话流、统一撤销栈、导出与全屏预览 | ✅ 已完成 |
| **Workspace** | Sidebar + 5 面板外壳、设置入口、Task/Chat/Files/Memory 业务面板已落地 | Files 显示最近文件列表；Memory 显示知识图谱/翻译记忆/术语库统计 |
| **统一设置** | Engine / Appearance / Shortcuts / Advanced 已统一到一个弹窗，并通过 bridge 持久化 | 更细的校验、更多配置项摘要和覆盖范围仍在完善 |

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

当前代码已经交付了**完整的 Studio PPT 共创工作台**：

- `NavigationManager` 管理的独立 `StudioWindowV5`
- `Source / Outline / Preview / 底部 AI 区` 四区域工作台
- 缩略图导航与拖拽支持
- 真正的 WYSIWYG 预览与差异预览编辑
- 支持高级图表与原生流程图 (Flowchart) 渲染
- AI 自然语言对话式修改
- 统一的 Undo/Redo 撤销栈
- 文本与 slides 加载、导出 PPT / 全屏预览完整链路

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

### 设计决策：Pipeline 中间件 vs 单体 Prompt 拼接

Cursor、Claude Desktop 等产品本质上是「对话窗口 + 能力插件」——获取上下文后拼接成一个大 prompt 扔给 LLM。这种模式的问题：

1. **安全无处安放**：内容过滤、权限校验嵌在 prompt 里，LLM 可能绕过
2. **不可观测**：出问题只能看 LLM 输出了什么，不知道中间发生了什么
3. **难以扩展**：加一个能力要在各处修改 prompt 拼接逻辑

OpenCopilot 对标 OpenClaw 的做法，引入**7 层异步 Pipeline**。每层是独立中间件，可拦截、可观测、可替换：

```
用户请求
  │
  ▼
SessionSetup   ← 会话恢复、Persona 加载、翻译方向动态注入
  │
  ▼
SecurityGuard  ← 权限校验、速率限制（Lane Semaphore 分 lane 限流）
  │
  ▼
ImmuneSystem   ← 内容安全检测、危险命令过滤（独立于 LLM）
  │
  ▼
Planner        ← 任务复杂度判断 → 选择 Agent 范式
  │
  ▼
StateTracking  ← 会话状态追踪、checkpoint
  │
  ▼
CapabilityRouter ← 能力路由（代码执行 / 知识检索 / 搜索 / LLM）
  │
  ▼
LLMAgent       ← Agent Loop 混合范式
  │
  ├─ SIMPLE  → One-Shot（~2s）：80% 场景
  ├─ MEDIUM  → Plan-and-Solve（~10s）：多步骤任务
  └─ COMPLEX → Plan+ReAct（~20s）：需纠错的复杂任务
```

**Pipeline 带来的关键能力**：

| 能力 | 说明 |
|------|------|
| **短路安全** | 安全检查不过 → 直接返回拒绝，LLM 永远看不到危险内容 |
| **全链路可观测** | 24 个 Timer 埋点按 `action_type` 分类，每层耗时可独立追踪 |
| **优雅取消** | 用户中断通过 `CancelledError` 沿异步栈传播，无粗暴截断 |
| **声明式扩展** | 新增能力 = 加一个中间件，不触碰已有代码 |

### 为什么借鉴 OpenClaw 的架构？

OpenClaw 的 Pipeline + Agent Loop 架构解决了 Agent 工程的三个核心问题：

1. **全局持久化 Event Loop**：不是每个请求起一个线程，全进程共享一个 `asyncio` loop，取消走 `task.cancel()` 而非线程强杀
2. **会话级序列化锁**：同一 Session 同时只有 1 个 Pipeline，杜绝数据竞争（重复回复的根源）
3. **中间件热插拔**：安全/路由/规划各自独立，不需要动 LLM prompt

**与 OpenClaw 的关键差异**：

| | OpenClaw | OpenCopilot |
|---|---|---|
| 交互模型 | Agent 自主决策 + 工具调用 | 用户触发 + 双击右键 |
| 运行模式 | 长时间自主任务 | 短交互、按需介入 |
| 安全模型 | Tool 权限白名单 | Pipeline 多层拦截 + ImmuneSystem |
| 能力侧重 | 文件/代码/Shell 自动化 | 多软件通用：Word/PPT/网页/IDE/截图 |
| 可观测性 | Node.js 生态 | Python + SQLite 持久化日志 + stderr 实时输出 |

**简单说**：OpenClaw 是"AI 替你干活"，OpenCopilot 是"AI 在你干活时随时搭把手"。两者共享 Pipeline 架构思想，但产品理念不同。

**当前 v5 UI 集成说明**：

- `Work` 和 `Chat` 已通过 `gui/v5/agent_worker.py` 直接调用共享的 Agent Pipeline 实现
- 非 AI UI 操作主要通过 `gui/v5/bridge.py` 直连本地 Python 模块
- `API Gateway (:8000)` 仍作为 HTTP/OpenAPI 对外入口，同时承载部分 v5 路由，例如 `/api/studio/*`

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
# 终端 1：Agent Pipeline (:18888) - 推荐启动，用于健康检查和 HTTP 兼容链路
python3 asu_custom_agent.py

# 终端 2：Broker 特权代理 (:18889) - 选区 / 活动文档 / 回写必需
bash start_broker.sh

# 终端 3：API Gateway (:8000) - 可选但建议启动，用于 OpenAPI + HTTP 路由 + /api/studio/*
python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 终端 4：UI
bash scripts/start_ui.sh
```

更完整的启动矩阵请参考 [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)。

启动后，v5 UI 通过 `smart_copilot.py` → `gui/main.py` 进入；Smart Copilot / Workspace / Studio 由 v5 导航层调度。

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
├── api/                          # API 网关 (:8000，统一入口)
│   ├── app.py                    #   路由工厂（统一注册中心）
│   └── routers/                  #   16+ 独立路由模块
│       ├── chat.py               #     聊天/流式/WebSocket
│       ├── system.py             #     系统状态
│       ├── file.py               #     文件操作
│       ├── config.py             #     配置管理
│       ├── persona.py            #     人设管理
│       ├── ppt.py                #     PPT 生成/分析/建议/质量检查
│       ├── text.py               #     文本处理
│       ├── knowledge.py          #     知识检索
│       ├── coding.py             #     代码审查
│       ├── tasks.py              #     任务管理
│       ├── evaluation.py         #     评估/评分/本地评估
│       ├── search.py             #     统一搜索 (NEW)
│       └── memory.py             #     记忆管理 (NEW)
├── gui/                          # PyQt6 桌面应用
│   ├── main.py                   #   入口 + CopilotManager
│   ├── v5/                       #   v5 交互层（Navigation / Work / Chat / Studio / Settings）
│   ├── window.py                 #   旧版/兼容悬浮卡片
│   ├── workspace.py              #   旧版/兼容工作台
│   ├── workers/                  #   QThread Worker
│   └── dialogs/                  #   翻译/Persona 等对话框
├── widgets/                      # PyQt6 控件 (技能面板、设置对话框等)
├── asu_custom_agent.py           # Agent Pipeline 服务 (:18888)
├── asu_broker/                   # Broker 特权代理服务 (:18889)
├── coding_agent/                 # 编码代理实现
├── context_manager/              # 上下文管理系统
├── core/                         # 核心工具和管理器
├── knowledge_graph/              # 知识图谱实现
├── docs/                         # 文档
│   ├── UI_Redesign_Plan_v5.md    # v5.0 UI 改版方案
│   ├── PPT_CoCreation_Design.md  # PPT 共创设计
│   ├── PPT_CoCreation_Iteration_Plan.md # PPT 迭代计划
│   ├── VNEXT_REBUILD_BLUEPRINT.md # vnext 重构总蓝图
│   ├── VNEXT_UNIFIED_AGENT_API.md # vnext 统一 Agent API 契约
│   ├── VNEXT_DOC_INDEX.md # vnext 文档总索引
│   ├── VNEXT_MODULE_BOUNDARIES.md # vnext 目录与依赖边界
│   ├── VNEXT_DATA_MODEL.md # vnext 数据模型与状态机
│   ├── VNEXT_PHASE1_IMPLEMENTATION_PLAN.md # vnext 第一阶段实施清单
│   ├── VNEXT_SMART_COPILOT_UI_SPEC.md # vnext Smart Copilot UI 交互方案
│   ├── VNEXT_AGENT_GATEWAY_DESIGN.md # vnext Agent Gateway 与 Provider Adapter 设计
│   ├── VNEXT_MIGRATION_PLAYBOOK.md # vnext 迁移作战手册
│   ├── VNEXT_TEST_AND_ACCEPTANCE.md # vnext 测试与验收方案
│   └── VNEXT_IMPLEMENTATION_BACKLOG.md # vnext 实施 backlog
├── personas/                     # AI 角色文件 (*.md)
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Trae/Cursor)
├── tests/                        # 测试 (unit / e2e / ablation)
├── scripts/                      # 守护进程/启动脚本
├── smart_copilot.py              # GUI 入口
├── smart_copilot_api.py          # API 入口（统一端口 8000）
└── pyproject.toml
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [USER_GUIDE.md](USER_GUIDE.md) | 用户手册（交互方式、功能使用、权限配置、常见问题） |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 架构设计（Pipeline、Agent Loop、Skill 系统、Broker 协议） |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南（模块开发、测试体系、新增 Persona/Skill） |
| [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md) | Agent / Broker / API Gateway / UI 的启动矩阵 |
| [docs/UI_Redesign_Plan_v5.md](docs/UI_Redesign_Plan_v5.md) | v5.0 UI 改版方案（3-Tab 架构、Workspace 2.0、统一设置） |
| [docs/VNEXT_REBUILD_BLUEPRINT.md](docs/VNEXT_REBUILD_BLUEPRINT.md) | vnext 重构总蓝图（聚焦双击右键 Smart Copilot、UI/API 解耦、新目录重建） |
| [docs/VNEXT_UNIFIED_AGENT_API.md](docs/VNEXT_UNIFIED_AGENT_API.md) | vnext 统一 Agent API 契约（Task/Event/Result/Apply/SSE） |
| [docs/VNEXT_DOC_INDEX.md](docs/VNEXT_DOC_INDEX.md) | vnext 文档总索引（阅读顺序、文档地图、审阅重点） |
| [docs/VNEXT_MODULE_BOUNDARIES.md](docs/VNEXT_MODULE_BOUNDARIES.md) | vnext 目录规划、依赖边界与迁移规则 |
| [docs/VNEXT_DATA_MODEL.md](docs/VNEXT_DATA_MODEL.md) | vnext 数据模型与状态机（Task/Session/Context/Event/Apply 真源定义） |
| [docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md](docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md) | vnext 第一阶段实施清单（按阶段拆分重构顺序、产出物、验收标准） |
| [docs/VNEXT_SMART_COPILOT_UI_SPEC.md](docs/VNEXT_SMART_COPILOT_UI_SPEC.md) | vnext Smart Copilot UI 交互方案（浮层结构、状态机、组件拆分） |
| [docs/VNEXT_AGENT_GATEWAY_DESIGN.md](docs/VNEXT_AGENT_GATEWAY_DESIGN.md) | vnext Agent Gateway 与 Provider Adapter 设计（网关职责、Adapter、标准化策略） |
| [docs/VNEXT_MIGRATION_PLAYBOOK.md](docs/VNEXT_MIGRATION_PLAYBOOK.md) | vnext 迁移作战手册（旧新模块映射、切主顺序、删旧策略） |
| [docs/VNEXT_TEST_AND_ACCEPTANCE.md](docs/VNEXT_TEST_AND_ACCEPTANCE.md) | vnext 测试与验收方案（契约测试、黄金链路、切主门槛） |
| [docs/VNEXT_IMPLEMENTATION_BACKLOG.md](docs/VNEXT_IMPLEMENTATION_BACKLOG.md) | vnext 实施 backlog（Epic/Story/任务拆解与优先级） |

---

## 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 基础交互、多引擎 AI、上下文感知 | ✅ |
| P1 | 特权 Broker、多模态视觉、无感划词 | ✅ |
| P2 | Persona 工坊、PPT 共创、知识图谱、Skill 架构 | ✅ |
| P3 | Agent Loop 重构、OpenClaw 单进程迁移、Pipeline 统一 | ✅ |
| P4 | 分层架构重构、代码治理、全链路可观测性 | ✅ |
| P4.1 | **AI 助手开发改革**：API 统一（双入口→单入口）、路由补全（+5模块）、空壳端点填充、ContextWindowManager 统一 | ✅ |
| P5 | v5.0 UI 改版：3-Tab 架构、Workspace 2.0、统一设置、Skill 重构 | 🔶 进行中 (Studio 已完成) |
| P6 | IDE Extension v2、Broker 产品化 | 📋 计划中 |
| P7 | 上下文主动感知、多 Agent 协作 | 📋 计划中 |

---

## License

MIT © OpenCopilot Team
