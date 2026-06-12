# OpenCopilot UI 交互设计稿

> 版本 v1.0 | 2026-06-09 | 基于当前 v5 实现 + v5.0 改版方案 + PPT 共创 E2E 设计整合

---

## 一、设计总览

### 1.1 产品定位

OpenCopilot 是一款 **macOS 系统级 AI 右键菜单应用**，核心理念是"AI 是鼠标右键的延伸，不是另一个窗口"。用户在任何 macOS 应用中选中内容，右键即可召唤 AI 助手。

### 1.2 三大核心窗口

```
┌─────────────────────────────────────────────────────────────────┐
│                        macOS 系统层                              │
│                                                                 │
│   双击右键 ──→ Smart Copilot (680×520)                          │
│                    │                                            │
│                    ├── Tab 1: Work    (快速操作)                  │
│                    ├── Tab 2: Chat    (连续对话)                  │
│                    └── Tab 3: Studio  (PPT 共创入口)              │
│                            │                                    │
│                            └──→ StudioWindowV5 (~1200×800)       │
│                                   (PPT 共创工作台)                │
│                                                                 │
│   三击右键 ──→ Agent Workspace (1000×700)                        │
│                    │                                            │
│                    ├── Panel 1: Task     (任务定义)               │
│                    ├── Panel 2: Chat     (会话列表)               │
│                    ├── Panel 3: Files    (文件管理)               │
│                    ├── Panel 4: Memory   (知识记忆)               │
│                    └── Panel 5: Settings (配置摘要)               │
│                                                                 │
│   System Tray ──→ Smart Copilot / Workspace / Settings           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 交互姿态

| 姿态 | 触发方式 | 意图 | 形态 |
|------|----------|------|------|
| **瞬时参谋** | 双击右键 | "这里帮我看看" | 轻量浮层窗口，贴近鼠标出现，不抢焦点 |
| **深度工作台** | 三击右键 | "我有复杂的任务" | 独立工作台窗口，支持多面板切换 |
| **PPT 共创** | Studio Tab → 打开 | "帮我做 PPT" | 独立 IDE 式工作台窗口 |

### 1.4 设计原则

| 原则 | 含义 | 体现 |
|------|------|------|
| **清晰优于巧妙** | 减少选项、区分层级 | 5 Tab → 3 Tab，Primary/Secondary 按钮分层 |
| **上下文感知** | 界面随用户环境自适应 | Header 显示当前 App + 文件名，Context Strip 切换数据源 |
| **渐进式展示** | 简单开始，高级按需展开 | Studio 空状态引导 → 3 阶段 E2E 流程按需展开 |
| **一致性** | 统一视觉语言 | Design Token 替代硬编码颜色 |
| **人在回路中** | 高影响操作需确认 | AI 修改先 Diff 预览再 Accept/Reject |

---

## 二、Smart Copilot (680×520)

### 2.1 窗口规格

| 属性 | 值 |
|------|-----|
| 尺寸 | 680×520 (可微调) |
| 窗口类型 | Frameless + StayOnTop + ShowWithoutActivating |
| 阴影 | QGraphicsDropShadowEffect, blur=40, offset=(0,5) |
| 背景 | 半透明，圆角 12px |
| 唤起方式 | 双击右键 / System Tray |
| 焦点策略 | 默认不抢焦点，用户点击输入框后才交互 |

### 2.2 窗口结构

```
┌─ Header Bar (36px) ──────────────────────────────────────────┐
│ ✨ Smart Copilot    [Microsoft Word] Q3_Report.docx  ● Online │
│                               [🎭] [⚙️] [─] [✕]              │
├─ Tab Bar ────────────────────────────────────────────────────┤
│  [Work]    [Chat]    [Studio]                                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    Tab Content Area                           │
│                      (动态内容)                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Tab 1: Work — 快速操作

**设计理念**：最高频的 AI 操作（Explain/Fix/Polish）一次点击完成。

```
┌─ Header Bar ─────────────────────────────────────────────────┐
│ [Microsoft Word] Q3_Report.docx · Page 4  ● Online           │
├─ Context Strip ──────────────────────────────────────────────┤
│ [Selection] [Active Doc] [Browser] [Clipboard] [File]         │
├─ Primary Actions (大按钮 36px, 高频操作) ────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ 📖 Explain │  │ 🔧 Fix    │  │ ✨ Polish │                   │
│  └──────────┘  └──────────┘  └──────────┘                    │
├─ Secondary Actions (小按钮 22px, 次高频) ────────────────────┤
│  [🌐 Translate]  [💻 Code Review]  [⋯ More]                   │
├─ Result Area (可滚动, Markdown 渲染) ────────────────────────┤
│  AI 分析结果...                                               │
│  - 设计模式：Observer Pattern                                 │
│  - 复杂度：中等 (CC=12)                                       │
│  - 建议：拆分 handle_event 方法                               │
├─ Action Bar ─────────────────────────────────────────────────┤
│              [📋 Copy]  [📊 Export PPT]  [↩ Apply]            │
└──────────────────────────────────────────────────────────────┘
```

**交互说明**：

| 组件 | 交互方式 | 说明 |
|------|----------|------|
| **Context Strip** | 点击切换数据源 | 默认选中 Selection，让用户清楚 AI "在看"什么 |
| **Primary Actions** | 单击执行 | 36px 大按钮，占 80% 使用量的高频操作 |
| **Secondary Actions** | 单击执行 | 22px 小按钮，次高频操作 |
| **More** | 展开二级菜单 | 包含 Auto/Summarize/Explain Code 等 |
| **Copy** | 复制结果到剪贴板 | 执行后 Toast 提示 |
| **Export PPT** | 跳转到 Studio Tab | 自动携带当前结果文本 |
| **Apply** | 回写到宿主应用 | 仅当有可应用修改时显示 |

**Context Strip 数据源**：

| 数据源 | 图标 | 获取方式 | 说明 |
|--------|------|----------|------|
| Selection | 📝 | AXUIElement API | 当前选中文本（默认） |
| Active Doc | 📄 | AppleScript 桥接 | 当前活动文档全文 |
| Browser | 🌐 | AppleScript 桥接 | 浏览器当前页面 |
| Clipboard | 📋 | NSPasteboard | 剪贴板内容 |
| File | 📁 | 文件选择器 | 选择本地文件 |

### 2.4 Tab 2: Chat — 连续对话

**设计理念**：多轮对话 + 上下文可见 + Skill 可用。

```
┌─ Context Panel (可折叠, 48px) ───────────────────────────────┐
│ ▼ Context (3 sources)                                         │
│ [IDE: main.py:42-58] [Browser: docs.python.org] [Clipboard]   │
├─ Conversation Area (可滚动) ─────────────────────────────────┤
│  👤 User: Explain this function...                            │
│                                                              │
│  🤖 AI: This is a recursive function that computes the        │
│     Fibonacci sequence. Key observations:                     │
│     - Base cases: n=0 → 0, n=1 → 1                           │
│     - Time complexity: O(2^n) without memoization             │
│                                                              │
│  👤 User: How to optimize it?                                 │
│                                                              │
│  🤖 ●●● Streaming... (打字指示器)                              │
├─ Input Area ─────────────────────────────────────────────────┤
│  [Type a message... or / for skills]    [⏹ Stop] [▶ Send]    │
├─ Skill Panel (可折叠, 底部卡片条) ───────────────────────────┤
│  [Code Executor] [Knowledge Search] [Web Search] [...]         │
│  Type / in chat to search skills                              │
└──────────────────────────────────────────────────────────────┘
```

**交互说明**：

| 组件 | 交互方式 | 说明 |
|------|----------|------|
| **Context Panel** | 折叠/展开 | 显示当前可引用的上下文来源 |
| **对话区域** | 滚动浏览 | Markdown 渲染，代码块语法高亮 |
| **输入框** | 键盘输入 | Enter 发送，Shift+Enter 换行 |
| **/ 技能触发** | 输入 "/" 前缀 | 弹出 Cmd+K 命令面板 |
| **Stop 按钮** | 点击中断 | 取消当前 AI 流式输出 |
| **Skill Panel** | 卡片点击 | 展示已安装技能，点击执行 |

### 2.5 Tab 3: Studio — PPT 共创入口

**设计理念**：统一入口，内部运行 3 阶段 E2E 流程。

```
┌─ Studio Launcher ────────────────────────────────────────────┐
│                                                              │
│           🎨 PPT 共创工作台                                   │
│                                                              │
│    AI 驱动的人机协同 PPT 创作体验                               │
│    从文本输入到策略发现，再到可视化编辑打磨                       │
│                                                              │
│                    [打开 Studio ▶]                             │
│                                                              │
│    💡 请先导入文本，或点击按钮直接粘贴内容                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**入口逻辑**：

| 场景 | 有文本? | 行为 |
|------|---------|------|
| 无上下文打开 Tab 3 | 无 | 显示启动器页面 |
| 有选中文本打开 Tab 3 | 有 | 状态文案："📄 已导入 N 字文本"，点击按钮直接进入 |
| 从 Work Tab 跳转 | 有 | 自动携带文本，直接打开 Studio 窗口 |
| 从 Chat 传递文本 | 有 | 自动填入，直接打开 Studio 窗口 |
| 文件拖入 Tab 3 | 有 | 解析文件内容，直接打开 Studio 窗口 |

### 2.6 窗口行为

| 行为 | 说明 |
|------|------|
| **定位** | 贴近鼠标位置弹出，自动避开屏幕边缘 |
| **拖拽** | 标题栏可拖拽移动 |
| **关闭** | 点击 ✕ 或 ESC 隐藏（不销毁实例） |
| **焦点** | 默认不抢焦点 (WA_ShowWithoutActivating) |
| **置顶** | WindowStaysOnTopHint |
| **半透明** | WA_TranslucentBackground + 圆角阴影 |

---

## 三、Agent Workspace (1000×700)

### 3.1 窗口规格

| 属性 | 值 |
|------|-----|
| 尺寸 | 1000×700 (最小 800×550) |
| 窗口类型 | Frameless + StayOnTop |
| 唤起方式 | 三击右键 / System Tray |
| 可调整 | 可拖拽边缘调整大小 |

### 3.2 窗口结构

```
┌─ Workspace ──────────────────────────────────────────────────┐
│ ┌─ Sidebar (180px) ──┐ ┌─ Content Area (820px) ────────────┐ │
│ │                    │ │                                    │ │
│ │  📋 Task           │ │      (动态 Panel 内容)              │ │
│ │  💬 Chat           │ │                                    │ │
│ │  📁 Files          │ │                                    │ │
│ │  🧠 Memory         │ │                                    │ │
│ │  ⚙️ Settings       │ │                                    │ │
│ │                    │ │                                    │ │
│ │  ──────────────    │ │                                    │ │
│ │  📊 Status         │ │                                    │ │
│ │  Pipeline: Online  │ │                                    │ │
│ │  Skills: 7 active  │ │                                    │ │
│ │                    │ │                                    │ │
│ └────────────────────┘ └────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Panel 1: Task — 任务定义与管理

**设计理念**：任务始终可见，自动注入所有 AI 请求。

```
┌─ Task Panel ─────────────────────────────────────────────────┐
│ ┌─ Current Task ───────────────────────────────────────────┐ │
│ │ 📌 审查支付模块安全漏洞                                    │ │
│ │ Created: 2026-06-09 22:30  Messages: 12                  │ │
│ │ Status: In Progress                                      │ │
│ │                                                         │ │
│ │ "请重点检查 SQL 注入和 XSS 攻击向量"                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Task Templates ─────────────────────────────────────────┐ │
│ │ [📄 Code Review]  [📝 Doc Translation]  [🔍 Bug Hunt]    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Recent Tasks ───────────────────────────────────────────┐ │
│ │ • API 文档翻译           3 hours ago    8 messages        │ │
│ │ • 前端组件重构           Yesterday      24 messages       │ │
│ │ • 性能测试报告           2 days ago     6 messages        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [+ New Task]  [📂 Import from File]  [📋 From Clipboard]     │
└──────────────────────────────────────────────────────────────┘
```

**交互说明**：

| 操作 | 说明 |
|------|------|
| 新建任务 | 点击 [+ New Task]，输入任务描述 |
| 从模板加载 | 点击模板卡片，自动填充任务描述 |
| 从文件导入 | 选择文件，提取内容作为任务上下文 |
| 从剪贴板 | 读取剪贴板内容作为任务描述 |
| 任务切换 | 点击历史任务恢复上下文 |
| 任务注入 | 任务描述自动注入到 Smart Copilot 的所有 AI 请求 |

### 3.4 Panel 2: Chat — 会话列表 + 对话

**设计理念**：多会话支持，持久化历史。

```
┌─ Chat Panel ─────────────────────────────────────────────────┐
│ ┌─ Sessions (200px) ─┐ ┌─ Conversation (620px) ────────────┐ │
│ │ [🔍 Search...]     │ │                                   │ │
│ │                    │ │ 👤: 帮我审查这个函数的安全性         │ │
│ │ ● Active Session   │ │                                   │ │
│ │   "安全审查对话"    │ │ 🤖: 该函数存在以下安全问题：        │ │
│ │   12 messages      │ │ 1. SQL 注入风险 (Line 45)          │ │
│ │                    │ │ 2. 未验证输入长度 (Line 52)         │ │
│ │ ○ API 文档翻译     │ │ 3. 硬编码密钥 (Line 18)            │ │
│ │   8 messages       │ │                                   │ │
│ │                    │ │ 👤: 如何修复第 1 个问题？            │ │
│ │ ○ 前端组件重构     │ │                                   │ │
│ │   24 messages      │ │ 🤖: 使用参数化查询：               │ │
│ │                    │ │ ```python                         │ │
│ │ [+ New Session]    │ │ cursor.execute(                   │ │
│ │                    │ │   "SELECT * FROM users WHERE id=?",│ │
│ │                    │ │   (user_id,))                     │ │
│ │                    │ │ ```                               │ │
│ │                    │ │                                   │ │
│ │                    │ ├───────────────────────────────────┤ │
│ │                    │ │ [Type a message...]    [▶ Send]   │ │
│ └────────────────────┘ └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 3.5 Panel 3: Files — 最近文件 + 拖放区

**设计理念**：文件管理一站式，支持拖放导入。

```
┌─ Files Panel ────────────────────────────────────────────────┐
│ 🔍 [Search files...]           [🔄 Refresh]                  │
│                                                              │
│ ┌─ Recent Files ────────────────────────────────────────────┐ │
│ │ 📄 main.py              Python   2 hours ago   [👁] [📤]  │ │
│ │ 📄 config.json          JSON     5 hours ago   [👁] [📤]  │ │
│ │ 📄 README.md            Markdown Yesterday     [👁] [📤]  │ │
│ │ 📄 test_api.py          Python   Yesterday     [👁] [📤]  │ │
│ │ 📄 architecture.docx    Word     2 days ago    [👁] [📤]  │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Drop Zone ───────────────────────────────────────────────┐ │
│ │                                                          │ │
│ │              📁 Drop files here                           │ │
│ │         .py .js .md .txt .docx .pdf                       │ │
│ │                                                          │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ [📂 Open in Finder]  [📋 Copy All Paths]                      │
└──────────────────────────────────────────────────────────────┘
```

**文件操作**：

| 操作 | 说明 |
|------|------|
| 👁 预览 | 弹出文件预览窗口 |
| 📤 发送到 Studio | 将文件内容发送到 PPT 共创 |
| 📤 发送到 Chat | 将文件内容作为上下文注入 Chat |
| 📋 复制路径 | 复制文件绝对路径到剪贴板 |
| 📋 复制内容 | 复制文件内容到剪贴板 |
| 拖放导入 | 拖入文件自动添加到当前任务上下文 |

### 3.6 Panel 4: Memory — 知识与上下文

**设计理念**：让知识图谱、翻译记忆、术语库可见可触达。

```
┌─ Memory Panel ───────────────────────────────────────────────┐
│                                                              │
│ ┌─ Knowledge Graph ─────────┐ ┌─ Translation Memory ────────┐ │
│ │ 🧠                        │ │ 🌐                          │ │
│ │ 264 Entities              │ │ 128 Entries                 │ │
│ │ 166 Relations             │ │ 中↔英: 89  日↔中: 23       │ │
│ │                           │ │ 韩↔中: 16                  │ │
│ │ [Browse]  [Query]         │ │ [Browse]  [Export]          │ │
│ └───────────────────────────┘ └─────────────────────────────┘ │
│                                                              │
│ ┌─ Terminology ─────────────────────────────────────────────┐ │
│ │ 📖                                                        │ │
│ │ 45 Terms                                                  │ │
│ │ 技术: 28  业务: 12  通用: 5                                │ │
│ │                                                           │ │
│ │ [Browse]  [Add Term]                                      │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ [📥 Inject to Task]  [📥 Inject to Chat]                      │
└──────────────────────────────────────────────────────────────┘
```

### 3.7 Panel 5: Settings — 配置摘要

**设计理念**：配置一目了然，快速跳转设置。

```
┌─ Settings Panel ─────────────────────────────────────────────┐
│                                                              │
│ ┌─ Engine ────────────────┐ ┌─ Appearance ─────────────────┐ │
│ │ ⚙️                      │ │ 🎨                           │ │
│ │ Backend: Cloud LLM     │ │ Theme: Dark                  │ │
│ │ Model: MiniMax-M2.7    │ │ Font: 13px                   │ │
│ │ Status: ● Connected    │ │ Accent: Blue                 │ │
│ │                        │ │                              │ │
│ │ [Configure]            │ │ [Configure]                  │ │
│ └────────────────────────┘ └──────────────────────────────┘ │
│                                                              │
│ ┌─ Shortcuts ─────────────┐ ┌─ Agent Runtime ──────────────┐ │
│ │ ⌨️                      │ │ 🤖                           │ │
│ │ 双击右键: Smart Copilot │ │ Mode: Self Agent             │ │
│ │ 三击右键: Workspace     │ │ Provider: MiniMax            │ │
│ │ Cmd+T: Translate       │ │ Fallback: Enabled            │ │
│ │                        │ │                              │ │
│ │ [Configure]            │ │ [Configure]                  │ │
│ └────────────────────────┘ └──────────────────────────────┘ │
│                                                              │
│ [📤 Export Config]  [📋 Copy Summary]  [🔄 Reset Appearance]  │
└──────────────────────────────────────────────────────────────┘
```

### 3.8 Smart Copilot ↔ Workspace 双向集成

| 方向 | 集成方式 |
|------|----------|
| **Workspace → Smart Copilot** | Task 定义自动注入所有 AI 请求；Files 拖放可作为上下文；Memory 知识可被引用 |
| **Smart Copilot → Workspace** | Work 结果可「发送到 Workspace」继续讨论；Studio 导出可附加到 Workspace Files |

---

## 四、PPT 共创工作台 (StudioWindowV5, ~1200×800)

### 4.1 窗口规格

| 属性 | 值 |
|------|-----|
| 尺寸 | ~1200×800 (可调整) |
| 窗口类型 | 独立窗口，可脱离 Smart Copilot |
| 唤起方式 | Smart Copilot Tab 3 → 打开 Studio |
| 生命周期 | 由 NavigationManager 独立持有 |

### 4.2 端到端 3 阶段流程

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Stage 1: 输入原文 ──→ Stage 2: 策略发现 ──→ Stage 3: 编辑打磨   │
│  (空状态页)            (正则分析<500ms)       (IDE 式双面板)       │
│                                                                 │
│  条件路由:                                                       │
│  • 无文本 → Stage 1 → 2 → 3                                     │
│  • 有文本 → 跳过 Stage 1, 直接进入 Stage 2                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Stage 1: 输入原文 (空状态)

> 仅在无文本上下文时显示，本质是空状态引导页。

```
┌─────────────────────────────────────────────┐
│  🚦  PPT 共创工作台                          │
├─────────────────────────────────────────────┤
│                                             │
│  粘贴或输入你的原文                           │
│  ┌─────────────────────────────────────┐    │
│  │ 在此粘贴文档内容...                  │    │
│  │ 支持技术方案、工作报告、产品介绍...    │    │
│  │                                     │    │
│  │                                     │    │
│  └─────────────────────────────────────┘    │
│  已输入 2,847 字 / 检测到 6 个段落           │
│  [📂 从文件导入]           [分析文档结构 →]   │
└─────────────────────────────────────────────┘
```

**交互**：
- 实时字数统计 + 段落检测 (<50ms)
- 支持文件拖放 (.txt / .md) → 读取后自动跳转 Stage 2
- 唯一 CTA："分析文档结构" → 进入 Stage 2

### 4.4 Stage 2: 策略发现

> 纯正则驱动的结构分析 (<500ms)，不调用 LLM。

```
┌─────────────────────────────────────────────┐
│  🚦  PPT 共创 - 策略发现                     │
├─────────────────────────────────────────────┤
│                                             │
│  文档分析  [技术方案]  2,847 字               │
│  ┌──┬───┬──┬──┬───┬─┐                      │
│  │背│架│数│对│流│总│  ← 段落类型热力图       │
│  │景│构│据│比│程│结│                          │
│  └──┴───┴──┴──┴───┴─┘                      │
│                                             │
│  选择叙事策略  Agent 推荐，可自由调整          │
│  ┌──────┐ ┌──────┐ ┌──────┐                │
│  │ ▲    │ │ ◆    │ │ ◇    │                │
│  │金字塔│ │叙事式│ │对比式│  ← 策略卡片     │
│  │  ✓   │ │      │ │      │                │
│  └──────┘ └──────┘ └──────┘                │
│                                             │
│  目标受众: [________]    演讲时长: [10min ▼] │
│                                             │
│        [跳过，直接生成]  [开始生成 →]          │
└─────────────────────────────────────────────┘
```

**三种策略**：

| 策略 | 结构模板 | 适用场景 |
|------|----------|----------|
| ▲ 金字塔式 | 核心结论 → 支撑论据 → 数据证据 → 下一步 | 汇报、总结 |
| ◆ 叙事式 | 现状痛点 → 解决思路 → 技术实现 → 预期收益 | 方案介绍 |
| ◇ 对比式 | 背景需求 → 方案对比 → 推荐详解 → 实施风险 | 决策论证 |

### 4.5 Stage 3: 编辑打磨 (IDE 式双面板)

> 交互核心，采用 60/40 双面板布局。

```
┌─────────────────────────────────────┬──────────────────────────┐
│  PPT 编辑区 (60%)                    │  原文面板 (40%)           │
│  ┌───────────────────────────────┐  │  ┌────────────────────┐  │
│  │ Thumb1 Thumb2 Thumb3 ...      │  │  │ 📄 原文  ████ 72%  │  │
│  ├───────────────────────────────┤  │  ├────────────────────┤  │
│  │                               │  │  │ [↻ 重提炼] 更关注..│  │
│  │                               │  │  ├────────────────────┤  │
│  │       Slide Preview           │  │  │                    │  │
│  │      (Click-to-Edit)          │  │  │  [S2] 智能体技术... │  │
│  │                               │  │  │  [+]  未映射段落... │  │
│  │  ┌──────────────────┐         │  │  │  [S3] 多模态感知... │  │
│  │  │ 🤖 AI Diff       │         │  │  │  [S4] 端侧部署...   │  │
│  │  │ -旧标题           │         │  │  │  [S5] 团队建设...   │  │
│  │  │ +新标题           │         │  │  │  [S6] 展望2027...  │  │
│  │  │ [✓接受] [✗拒绝]  │         │  │  │                    │  │
│  │  └──────────────────┘         │  │  │                    │  │
│  │                               │  │  │                    │  │
│  ├───────────────────────────────┤  │  ├────────────────────┤  │
│  │ [center] [text] [3-col] ...   │  │  │ 🤖 AI ●            │  │
│  └───────────────────────────────┘  │  │ [指令...] [▶]      │  │
├─────────────────────────────────────┴──────────────────────────┤
│                    [↩ Undo] [↪ Redo]    [💾 导出 PPT]           │
└───────────────────────────────────────────────────────────────┘
```

### 4.6 Stage 3 各区域详解

#### 4.6.1 缩略图导航 (顶部)

| 特性 | 说明 |
|------|------|
| 尺寸 | 64×36px 迷你缩略图 |
| 布局 | 水平滚动 |
| 选中态 | 蓝色 2px 边框 + 高亮背景 |
| 质量徽章 | 橙色圆点角标 (⚠️ 内容过密等) |
| 拖拽排序 | 支持拖拽调整幻灯片顺序 |

#### 4.6.2 幻灯片预览 (主区域)

| 特性 | 说明 |
|------|------|
| 画布 | 16:9 白色画布，居中显示 |
| Click-to-Edit | 标题/要点区域显示蓝色虚线边框，双击进入内联编辑 |
| 页码 | 底部显示 `3 / 6` |
| AI Diff | 半透明浮层叠加在预览区，展示 `-旧/+新` 对比 |

#### 4.6.3 原文面板 (右侧)

| 组件 | 说明 |
|------|------|
| 原文头部 | 显示"📄 原文" + 覆盖率进度条 (如 72%) |
| 重新提炼栏 | 指令输入框 + [↻ 重新提炼] 按钮 |
| 映射可视化 | 每段原文右侧显示映射标签 [S2] [S3] [+] |
| AI 输入 | 底部一行输入框 + 发送按钮 |

**映射标签交互**：

| 标签 | 样式 | 交互 |
|------|------|------|
| 已映射 [S2] | 彩色圆角标签 | 点击跳转到对应 slide |
| 未映射 [+] | 虚线灰色标签 | 点击选择目标 slide 分配 |

**双向联动**：
- 选中 slide → 对应映射段落高亮
- 点击映射标签 → 跳转到对应 slide

#### 4.6.4 AI Diff Overlay

```
┌─ Diff Preview ──────────────────────────────┐
│ - 2026 年度发展总结                          │ ← 红色背景 + 删除线
│ + 2026 智能体发展报告：多模态与人机协同       │ ← 绿色背景
│                                              │
│ [✓ Accept]  [✗ Reject]  [✏ Edit First]      │
└──────────────────────────────────────────────┘
```

#### 4.6.5 版式标签栏 (底部)

```
[center] [text_only] [three_columns] [chart] [timeline]
```

当前版式高亮，点击切换。

### 4.7 AI 交互完整链路

```
用户输入"把第1页的标题改为更有吸引力的"
  ↓
构造请求: message + current_slides + selected_slide_index + original_text
  ↓
Pipeline: SessionSetup → Security → Immune → Planner → LLMAgent
  ↓
流式反馈: ●●● AI 正在思考... ████████░░░░ 60%
  ↓
Diff Preview: -旧标题 / +新标题
  ↓
用户决策: [Accept] → 应用修改 → 所有面板同步
         [Reject] → 保持原状
         [Edit First] → 手动微调 → 确认
  ↓
Undo Stack: 记录操作 (紫色标记 = AI 编辑)
```

### 4.8 十项交互改进

| # | 改进项 | 说明 | 优先级 |
|---|--------|------|--------|
| 1 | Thumbnail Strip | 64×36px 缩略图导航，支持拖拽排序 | P1 |
| 2 | Streaming AI Feedback | 打字指示器 + 进度条 + 部分结果实时渲染 | P0 |
| 3 | Click-to-Edit | 双击预览中的标题/要点 → 内联编辑器 | P1 |
| 4 | Contextual Quick Actions | 快捷按钮根据内容类型自适应 | P2 |
| 5 | Detachable AI Chat | 拖拽 Chat Header 可分离为浮动窗口 | P3 |
| 6 | Diff Preview | AI 修改前显示 before/after 对比 | P1 |
| 7 | Quality Badges | 非侵入式警告："内容较密，建议拆分" | P2 |
| 8 | Theme Picker | 工具栏内联色块选择器，Hover 实时预览 | P2 |
| 9 | Coverage Heatmap | Source Panel 顶部进度条，显示原文利用比例 | P3 |
| 10 | Unified Undo Stack | 时间线显示手动(蓝)和 AI(紫)编辑，点击回滚 | P0 |

---

## 五、跨窗口导航逻辑

### 5.1 窗口层级

```
┌─────────────────────────────────────────────────────────┐
│                    macOS 系统层                          │
│                                                         │
│  双击右键 ──→ Smart Copilot (680×520, frameless)        │
│                    │                                    │
│                    ├──→ Studio Window (~1200×800)        │
│                    │      (独立窗口,可脱离)               │
│                    │                                    │
│                    └──→ Settings Dialog (600×500)        │
│                           (模态弹窗)                     │
│                                                         │
│  三击右键 ──→ Agent Workspace (1000×700, frameless)     │
│                    │                                    │
│                    └──→ Settings Dialog (600×500)        │
│                           (模态弹窗,同一实例)             │
│                                                         │
│  System Tray ──→ Smart Copilot / Workspace / Settings   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 窗口互斥规则

| 规则 | 说明 |
|------|------|
| SC + WS 可同时存在 | 用户可能一边在 Workspace 定义任务，一边用 SC 快速操作 |
| Studio 独立生命周期 | 关闭 SC 不会自动关闭 Studio |
| Settings 模态 | 同一时间只允许一个实例 |
| hide_all() 范围 | 只隐藏 SC / WS；Studio 和 Settings 保持独立 |

### 5.3 核心跳转链路

#### 链路 A: Smart Copilot → Studio

```
Tab 3 Studio → 检查 current_text
  ├── 有文本 → 打开 StudioWindowV5 → 自动填入 → 直接进入 Stage 2
  └── 无文本 → 弹出输入对话框 → 用户输入/导入 → 打开 Studio → Stage 1
```

#### 链路 B: Work Tab → Chat Tab

```
Work Tab 完成操作 → 点击 Chat Tab
  → 清空 chat_display
  → 注入上下文摘要 (前 150 字符 + 来源)
  → 切换到 Tab index 1
  → 聚焦输入框
```

#### 链路 C: Workspace ↔ Smart Copilot

```
Workspace → SC: Task 定义自动注入所有 AI 请求
SC → Workspace: 结果可「发送到 Workspace」继续讨论
```

#### 链路 D: Studio → Smart Copilot

```
Studio 导出 PPT 后:
  → Toast: "PPT 已导出至: /path/to/file.pptx"
  → [打开文件夹] [在 Chat 中继续讨论]
  → 点击后者 → 自动切换到 Chat Tab + 注入消息
```

---

## 六、统一设置弹窗 (600×500)

### 6.1 布局

```
┌─ Settings ────────────────────────────────────────┐
│ Sidebar(140px)  │  Content Area (460px)           │
│ ┌─────────────┐ │ ┌─────────────────────────────┐ │
│ │ ● Engine    │ │ │ Backend: [Cloud LLM] [Local]│ │
│ │   Appearance│ │ │ API Key: ************ [Show]│ │
│ │   Shortcuts │ │ │ Model: MiniMax-M2.7 [Scan]  │ │
│ │   Advanced  │ │ │ Status: ● Connected         │ │
│ │             │ │ │                             │ │
│ │             │ │ │ [Save]  [Test Connection]   │ │
│ └─────────────┘ │ └─────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

### 6.2 四个分区

| 分区 | 内容 |
|------|------|
| **Engine** | Backend (Cloud/Local)、API Key、API Base URL、Model、连接状态 |
| **Appearance** | Theme (Dark/Light/System)、Font Size、Font Family、Language、Accent Color |
| **Shortcuts** | 双击右键→SC、三击右键→WS、Cmd+T→翻译、Cmd+P→润色、Cmd+K→技能搜索 |
| **Advanced** | Auto Save、Recent Files 数量、Export Format、Office Mode、Config Path |

### 6.3 三个入口

| 入口 | 触发方式 |
|------|----------|
| Smart Copilot Header | 点击 ⚙️ 齿轮图标 |
| Workspace Sidebar | 点击 Settings Panel |
| System Tray | 右键 → Settings |

---

## 七、Skill 系统交互

### 7.1 Skill Panel (Chat Tab 底部)

```
┌─ Skill Cards ──────────────────────────────────────────────┐
│ [Code Executor ✓Active]  [Knowledge Search ✓Active]         │
│ [Web Search ✓Active]     [File Operations ○Disabled]        │
│ [PPT Generator ✓Active]  [Evaluation ✓Active]               │
│                                                             │
│ Type / in chat to search skills                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Cmd+K 命令面板 (650×550)

```
┌─ Skill Search ──────────────────────────────────────────────┐
│ 🔍 [Search skills...]                                       │
├─────────────────────────────────────────────────────────────┤
│  📊 Code Executor           score: 0.95                     │
│     Run code in sandboxed environment                       │
│                                                             │
│  💻 Coding Skill             score: 0.80                     │
│     Code review, refactoring, bug fixing                    │
│                                                             │
│  🔍 Knowledge Search         score: 0.75                     │
│     Query project knowledge graph                           │
├─────────────────────────────────────────────────────────────┤
│  ↑↓ Navigate  Enter Execute  Tab Details  Esc Cancel        │
└─────────────────────────────────────────────────────────────┘
```

**触发方式**：
- Chat 输入框输入 `/` 前缀
- 全局快捷键 `Cmd+K`

### 7.3 右键菜单增强

```
┌─ Context Menu ─────────────────────────────┐
│  Copy                                      │
│  Explain Code                              │
│  Optimize                                  │
│  Find Bugs                                 │
│  ──────────────────                        │
│  Recommended Skills:                       │
│  📊 Code Executor                          │
│  🔍 Knowledge Search                       │
│  ──────────────────                        │
│  More Skills... [Cmd+K]                    │
└────────────────────────────────────────────┘
```

---

## 八、Design Token 体系

### 8.1 颜色系统

| Token | Light Mode | Dark Mode | 语义 |
|-------|-----------|-----------|------|
| `accent.control` | `#3498db` | `#5dade2` | 主色调 |
| `status.success` | `#27ae60` | `#2ecc71` | 成功/在线 |
| `status.warning` | `#f39c12` | `#f1c40f` | 警告 |
| `status.error` | `#e74c3c` | `#ff6b6b` | 错误 |
| `bg.primary` | `#ffffff` | `#1a1a2e` | 主背景 |
| `bg.elevated` | `#ecf0f1` | `#252542` | 提升背景 |
| `stroke.border` | `#dcdde1` | `#3a3a5c` | 边框 |
| `text.primary` | `#2c3e50` | `#ecf0f1` | 主文本 |
| `text.secondary` | `#7f8c8d` | `#95a5a6` | 次文本 |
| `text.accent` | `#3498db` | `#5dade2` | 强调文本 |

### 8.2 排版规格

| 层级 | 字号 | 字重 | 使用场景 |
|------|------|------|----------|
| Title | 14px | bold | 窗口标题、Tab 选中标签 |
| Heading | 13px | bold | 面板标题、区域头部 |
| Body | 12px | normal | 内容文本、聊天消息、输入框 |
| Caption | 11px | normal | 状态信息、标签、辅助文字 |
| Tiny | 10px | normal | 时间戳、快捷键、状态点 |

### 8.3 按钮尺寸

| 尺寸 | 高度 | 内边距 | 使用场景 |
|------|------|--------|----------|
| Large | 36px | 10px 20px | 主 CTA：打开 Studio、发送、保存 |
| Medium | 28px | 6px 14px | Primary Actions：Explain/Fix/Polish |
| Small | 22px | 4px 10px | Secondary Actions、内联操作 |
| Icon | 24px | 4px | Header 图标：persona/settings/close |

---

## 九、异常与边界场景

### 9.1 网络/API 异常

| 场景 | 用户反馈 | 恢复路径 |
|------|----------|----------|
| API Gateway 离线 | Header Online 标签变红 Offline + 按钮 disabled | 网络恢复后自动重连 |
| AI 生成超时 | Chat: "⏰ AI 响应超时，正在重试..." | 自动重试 1 次 |
| AI 返回空结果 | 内联提示："AI 未能生成大纲，请尝试更详细的内容" | 降级到智能模板 |

### 9.2 数据边界

| 场景 | 阈值 | 处理 |
|------|------|------|
| 文本过短 | < 20 字 | 提示"内容较短，建议至少 50 字" |
| 文本过长 | > 50000 字 | 截断 + Toast |
| 幻灯片过多 | > 30 页 | Quality Badge 警告 |
| 单页要点过多 | > 8 个 | 建议拆分 |

### 9.3 窗口状态异常

| 场景 | 处理 |
|------|------|
| SC 关闭时 Studio 仍打开 | Studio 保持运行，再次打开 SC 可检测到 |
| WS 和 SC 同时显示 | 两者独立运行，互不遮挡 |
| Settings 已打开时再次触发 | 忽略或 raise 已有弹窗 |

---

## 十、技术架构映射

### 10.1 代码结构

```
gui/v5/
├── navigation.py       # NavigationManager 跳转中枢
├── smart_copilot.py    # SmartCopilotV5 主窗口 (3-Tab)
├── work_tab.py         # Tab 1: Work 快速操作
├── chat_tab.py         # Tab 2: Chat 连续对话
├── studio_tab.py       # Tab 3: Studio 入口
├── studio_window.py    # StudioWindowV5 PPT 共创工作台
├── workspace.py        # WorkspaceV5 工作台 (5-Panel)
├── settings_dialog.py  # SettingsDialogV5 统一设置
├── agent_worker.py     # V5AgentWorker 统一运行时入口
├── bridge.py           # Bridge 本地模块桥接
├── tokens.py           # Design Token 系统
├── telemetry.py        # V5Telemetry 遥测
└── env.py              # 环境配置
```

### 10.2 数据流

```
用户操作 → UI 组件
  ↓
V5AgentWorker (统一入口)
  ↓
/vnext/* API → Agent Gateway → Provider Adapter
  ↓
Pipeline: SessionSetup → Security → Immune → Planner → CapabilityRouter → LLM
  ↓
SSE 流式响应 → UI 渲染
```

### 10.3 统一运行时

```
UI 不直接依赖具体智能体实现
  ↓
V5AgentWorker 按 agent_runtime 动态路由
  ├── /vnext/* → hermes_local (默认)
  ├── self_agent (自研)
  └── capability 覆盖 + fallback policy
```

---

## 十一、质量验收基线

| 指标 | 值 |
|------|-----|
| 完整 UI/AI 组合回归 | 427 passed |
| 真实生产链路验证 | 27/27 PASS |
| 总分结构 | Reliability 30 + Quality 40 + UX 20 + Safety 10 |
| 硬门槛 | 协议错误率=0, JSON 解析失败率=0, think 泄露率=0 |
| 建议上线门槛 | 整体 >= 4.3/5.0, 高价值模块 >= 4.5/5.0 |

---

## 十二、相关文档索引

| 文档 | 内容 |
|------|------|
| `UI_Redesign_Plan_v5.md` | v5.0 改版方案（本文档的主要参考） |
| `PPT_CoCreation_Design.md` | PPT 共创架构设计（JSON Schema、系统架构） |
| `PPT_CoCreation_E2E_Design.md` | PPT 共创端到端交互设计（3 阶段流程） |
| `VNEXT_SMART_COPILOT_UI_SPEC.md` | vNext Smart Copilot UI 交互方案 |
| `VNEXT_REBUILD_BLUEPRINT.md` | vNext 重构总蓝图 |
| `ARCHITECTURE.md` | 当前仓库真实架构 |
| `USER_GUIDE.md` | 用户手册 |

---

> **文档版本**：v1.0
> **更新日期**：2026-06-09
> **基于**：v5.0 改版方案 + PPT 共创 E2E 设计 + 当前代码实现
