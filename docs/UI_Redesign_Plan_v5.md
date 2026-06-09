# OpenCopilot v5.0 改版方案与当前落地对照

> 版本 v5.0 | 2026-06-09 | 方案对照当前实现 · 去除过时描述 · 明确已落地/演进边界

---

## 0. 文档定位与实施状态

本文档不再把 v5 设计目标直接等同于“已交付事实”，而是区分：

- **设计目标**：v5 想达到的完整交互状态
- **当前落地**：仓库代码里已经存在并可运行的部分
- **演进项**：已经有基础实现，但未来仍可继续增强的能力

### 0.1 当前实施状态总览

| 模块 | 当前落地 | 演进项 |
|------|----------|--------|
| **Smart Copilot 3-Tab** | 已落地 `Work / Chat / Studio` 主壳、Tab 跳转、拖放共享、统一导航 | 更丰富的命令面板、结果渲染和交互细节 |
| **NavigationManager** | 已成为 v5 窗口生命周期中枢 | 继续收敛旧版兼容路径 |
| **Work Tab** | 上下文来源切换、按钮分层、Agent 流式调用、Copy/Apply、发送到 Studio 的 UI 闭环已接通 | 更丰富的结果渲染和命令面板 |
| **Chat Tab** | 多会话基础 UI、流式输出、停止生成、上下文注入、共享内容可视化与清空已落地 | 更完整的历史管理和引用体系 |
| **Studio Window** | PPT 共创工作台已完整实现：包含 Source/Outline/Preview/底部 AI 区、缩略图导航、可视化预览、撤销流及完整导出链路 | 已完成（新设计升级为 3 阶段 E2E 流程 + IDE 式布局，详见 `PPT_CoCreation_E2E_Design.md`） |
| **Workspace 2.0** | Sidebar + 5 Panel 已完整贯通；Task 支持模板/剪贴板/最近文件导入，Files 支持筛选/预览/导入任务/发送 Studio/发送聊天/复制内容与路径，Memory 支持概览卡片/详情切换/注入任务与聊天，Settings 展示摘要并支持导出配置/复制摘要/重置外观 | 更细粒度的文件操作与知识浏览器 |
| **Unified Settings** | Engine / Appearance / Shortcuts / Advanced 四分区已落地，Workspace Settings 面板也可显示配置摘要 | 更全面的数据校验 |

### 0.2 当前入口现实

当前代码实际入口关系：

- **双击右键** → `NavigationManager.show_smart_copilot()` → v5 Smart Copilot
- **三击右键** → `NavigationManager.show_workspace()` → v5 Workspace
- **Studio / Settings** 由 `NavigationManager` 统一管理

也就是说，v5 已经进入主交互路径，当前是“核心 UI 闭环已可用，后续进入体验增强”的阶段。

### 0.3 当前日志与埋点覆盖

本轮 UI 补齐后，以下交互已纳入既有 `V5Telemetry` 体系：

- `Work Tab`：`V5_WORK_CONTEXT_LOADED`、`V5_WORK_MORE_SHOW`、`V5_WORK_COPY_DONE`、`V5_WORK_APPLY_DONE`、`V5_WORK_EXPORT_STUDIO`
- `Chat Tab`：`V5_CHAT_CTX_UPDATE`、`V5_CHAT_CTX_CLEAR`，以及原有 `V5_CHAT_SEND / STOP / LLM_*`
- `Workspace`：`V5_WS_FILES_REFRESH`、`V5_WS_FILE_SELECT`、`V5_WS_FILE_OPEN_STUDIO`、`V5_WS_FILE_COPY_PATH`、`V5_WS_MEMORY_REFRESH`、`V5_WS_SETTINGS_REFRESH`、`V5_WS_TASK_IMPORT_*`

这些事件统一通过 `gui/v5/telemetry.py` 输出结构化日志，便于继续沿用现有观测链路。

### 0.4 当前验收基线

当前 `V5 UI` 已经完成一轮面向真实生产代码的功能验收与质量验收基线确认：

- 已接真实 AI 的主链路：`Work Tab` 主操作、`Chat Tab`、`Workspace Chat`、`Studio Tab`、`Studio Window` 页内共创
- 尚未接真实 AI 的主要是工作流/资料面板或设计未落地项：`Workspace Files/Memory/Settings/Task`、`Work More`、`Skill Panel`、`Cmd+K`、右键推荐技能菜单
- 完整 UI/AI 组合回归基线：`427 passed`
- 真实生产链路验证：`27/27 PASS`
- 当前统一设置已支持在固定一套 UI 下，通过配置切换 `Self Agent` 与第三方智能体
- 当前第三方智能体接入先支持 `Hermes Local`，并通过统一 `V5AgentWorker -> /vnext/* -> Agent Gateway` 链路执行

这意味着当前 v5 的主要架构变化已经从“UI 直接贴着智能体实现写”收敛为：

- `UI` 负责交互与状态呈现
- `V5AgentWorker` 负责统一运行时入口与路由选择
- `/vnext/*` 负责任务协议
- `Agent Gateway / Provider Adapter` 负责承接自研与第三方智能体差异

因此新增或替换智能体时，当前主要改动点已经下沉到 Runtime / Gateway / Adapter，而不是要求 UI 重做入口。

当前质量量化已形成统一口径：

- 总分结构：`Reliability 30 + Quality 40 + UX 20 + Safety 10`
- 硬门槛：`协议错误率 = 0`、`JSON 解析失败率 = 0`、`think 泄露率 = 0`
- 建议上线门槛：整体 `>= 4.3/5.0`，高价值模块 `Explain / Code Review / PPT >= 4.5/5.0`

当前实现事实与量化指标以 `docs/CURRENT_UI_AI_ACCEPTANCE_20260609.md` 为准。

---

## 一、改版背景与设计初衷

### 1.1 产品定位

OpenCopilot 是一款 **macOS 系统级 AI 右键菜单应用**，基于 PyQt6 构建。核心交互：

- **双击右键** → Smart Copilot（680×520，快速 AI 操作）
- **三击右键** → Agent Workspace（当前代码已升级为 1000×700 的 v5 侧边栏工作台骨架）

用户在任何 macOS 应用中选中文本/代码/文件，右键即可召唤 AI 助手，无需切换窗口。

### 1.2 为什么要改版

当前 v4.x 存在以下核心问题：

| 问题类别 | 具体表现 | 影响 |
|---------|---------|------|
| **功能入口混乱** | Smart Copilot 有 5 个 Tab，其中 Tab 3 和 Tab 5 都是 PPT 入口 | 用户困惑，不知道哪个是"正确的"PPT 入口 |
| **设置分散** | 2 个独立设置弹窗（引擎设置 131 行 + 个性化设置 390 行），无共享状态 | 用户需要打开两个窗口才能完成初始配置 |
| **代码大量重复** | Skill 系列 3 个文件（~2600 行）中搜索算法复制粘贴 3 次（~150 行/处） | 维护成本高，修一处漏两处 |
| **硬编码颜色** | ~40 个硬编码颜色值（#3498db、#27ae60、#ecf0f1 等） | 无法支持 Dark/Light 主题切换 |
| **Workspace 太小** | 520×480，比 Smart Copilot 还小，只有任务输入+聊天 | 名不副实，不像"工作台" |
| **缺乏上下文感知** | 无论用户在 Word、Excel、浏览器还是 IDE，界面一模一样 | 用户不知道 AI 能"看到"什么 |
| **PPT 工作台交互粗糙** | 无缩略图导航、无流式反馈、无差异预览、无统一撤销 | 与主流 AI 创作工具的交互水平差距大 |

**设计初衷：从"能用"升级到"好用"——减少选择成本、消除重复入口、建立视觉一致性、让 AI 能力触手可及。**

---

## 二、核心设计思想

### 2.1 四大设计原则

| 原则 | 含义 | 在本方案中的体现 |
|------|------|----------------|
| **清晰优于巧妙** | 减少选项、区分层级、不隐藏功能 | 5 Tab → 3 Tab，Primary/Secondary 按钮分层 |
| **上下文感知** | 界面随用户当前应用/文件/选区自适应 | Header 显示当前 App + 文件名，Context Strip 切换数据源 |
| **渐进式展示** | 简单开始，高级功能按需展开 | Studio 空状态引导输入 → 3 阶段 E2E 流程按需展开 |
| **一致性** | 统一的视觉语言、交互模式、组件规格 | Design Token 替代硬编码颜色，统一 Typography/Button 规格 |

### 2.2 三条设计主线

1. **入口精简**：合并重复功能（PPT Tab 3+5 → Studio），统一设置（2 弹窗 → 1 弹窗）
2. **上下文串联**：Smart Copilot ↔ Agent Workspace 双向数据流通，任务上下文自动注入
3. **代码治理**：提取共享层（skill_registry_ui.py），消除重复，建立 Design Token 体系

---

## 三、模块一：Smart Copilot 改版（3-Tab 架构）

### 3.1 架构变更：5 Tab → 3 Tab

| 旧版 Tab | 新版去向 | 理由 |
|----------|---------|------|
| Tab 1 Quick | → **Tab 1 Work** | 保留快速操作，增加上下文感知和视觉层级 |
| Tab 2 Chat | → **Tab 2 Chat** | 保留连续对话，增加 Context Panel |
| Tab 3 PPT 助手 | → **删除** | 与 Tab 5 功能重复，合并到 Studio |
| Tab 4 Skill Center | → **融入 Chat Tab 底部** | 技能不应是独立 Tab，而应是上下文可用的工具 |
| Tab 5 CoCreation | → **Tab 3 Studio** | 保留入口，运行 3 阶段 E2E 流程（详见 `PPT_CoCreation_E2E_Design.md`） |

**为什么 3 个 Tab？** 用户的操作路径本质上只有三条：快速处理（Work）、深度对话（Chat）、内容创作（Studio）。5 个 Tab 中有 2 个是 PPT 入口（困惑）、1 个是技能浏览（应融入上下文而非独立存在）。

### 3.2 Tab 1: Work — 快速操作

**交互方式：**

```
┌─ Header Bar ──────────────────────────────────────┐
│ [Microsoft Word] Q3_Report.docx · Page 4  ● Online │
├─ Context Strip ───────────────────────────────────┤
│ [Selection] [Active Doc] [Browser] [Clipboard] [File] │
├─ Primary Actions (大按钮，高频操作) ──────────────┤
│ [Explain]  [Fix]  [Polish]                        │
├─ Secondary Actions (小按钮，次高频) ──────────────┤
│ [Translate]  [Code Review]  [More...]             │
├─ Result Area ─────────────────────────────────────┤
│ AI 结果（Markdown 渲染）...                       │
├─ Action Bar ──────────────────────────────────────┤
│                    [Copy]  [Export PPT]  [Apply]   │
└───────────────────────────────────────────────────┘
```

**为什么这么设计：**
- **Context Strip**（数据源切换）：让用户清楚知道 AI 正在"看"什么。默认选中"Selection"（当前选区），可切换到活动文档、浏览器内容、剪贴板、文件
- **Primary/Secondary 分层**：旧版 6 个按钮同一排同样式，用户需要逐个阅读。新版通过按钮大小区分使用频率——Explain/Fix/Polish 是最常用的三个操作（占 80% 使用量），视觉上一眼就能定位
- **Context-Aware Header**：显示当前应用名称和文件路径，让用户确认 AI 的"视野范围"。支持 Word、Excel、PowerPoint、Safari、Mail、Notes 等任意 macOS 应用

### 3.3 Tab 2: Chat — 连续对话

**交互方式：**

```
┌─ Context Panel (可折叠) ──────────────────────────┐
│ Context ▸  3 sources                              │
│ [IDE Selection: main.py:42-58]                     │
│ [Browser: docs.python.org]  [Clipboard: traceback] │
├─ Conversation ────────────────────────────────────┤
│ User: Explain this function...                    │
│ AI: This is a recursive function that...          │
├─ Input ───────────────────────────────────────────┤
│ [Type a message...]              [Send]            │
└───────────────────────────────────────────────────┘
```

**为什么这么设计：**
- **Context Panel**：旧版 Chat 完全不知道用户"在哪里"。新版顶部显示当前可引用的上下文来源（IDE 选区、浏览器页面、剪贴板内容），可折叠不占空间
- **Skill Panel 融入 Chat 底部**：不再需要单独的 Skill Tab，在聊天输入框中输入 `/` 即可触发技能搜索（Command Palette 模式）

### 3.4 Tab 3: Studio — PPT 共创工作台

**入口逻辑（已升级）：**
- 点击 Studio 入口 → `NavigationManager.open_studio()` → 打开 `StudioWindowV5`
- **有文本**（选中文本/剪贴板/拖放文件/Chat 传递）→ 自动填入并**跳过 Stage 1，直接进入 Stage 2 策略发现**
- **无文本** → 显示 **Stage 1 空状态页**（TextArea 引导输入），输入后进入 Stage 2
- 完整 3 阶段流程详见 [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)

**为什么合并 Tab 3 + Tab 5：** 两个 PPT 入口是历史遗留问题——Tab 3 是"PPT 助手"（三个按钮的启动器），Tab 5 是"CoCreation"（另一个启动器）。用户测试中 100% 的人会困惑。统一为一个 Studio 入口，内部运行 3 阶段 E2E 流程（输入→策略发现→编辑打磨）。

---

## 四、模块二：Agent Workspace 2.0（Sidebar + 5-Panel）

### 4.1 核心变更：从"对话框"到"工作台"

| 属性 | 旧版 | 新版 | 理由 |
|------|------|------|------|
| 尺寸 | 520×480 | 1000×700（最小 800×550） | 工作台需要足够空间放 sidebar + 内容 |
| 导航 | 无 | 左侧 Sidebar（180px） | 多面板切换需要持久导航 |
| 面板数 | 2（任务+聊天） | 5（Task/Chat/Files/Memory/Settings） | 文件管理、知识记忆、设置配置一站式 |
| 可调整 | 不可调 | 可拖拽边缘调整大小 | 用户控制工作区大小 |

### 4.2 五个面板

> **当前代码状态说明**：5 Panel 已全部具备实际交互。Task 支持模板、剪贴板与最近文件导入；Files 支持筛选、最近文件列表、预览、导入任务、发送到 Studio、发送到聊天、复制内容和复制路径；Memory 展示知识图谱/翻译记忆/术语库概览卡片与详情，并支持注入任务/聊天；Settings 面板可显示配置摘要，并支持导出配置、复制摘要和重置外观后跳转统一设置弹窗。

#### Panel 1: Task — 任务定义与管理

**交互方式：**
- 左侧显示当前任务详情（描述 + 创建时间 + 消息数 + 统计数据）
- 右侧显示任务历史（可搜索、可恢复）
- 支持「新建任务」「从模板加载」「从文件导入」

**为什么这么设计：** 旧版任务设置后只显示为一个绿色小标签，很快就忘了"当前在做什么"。新版 Task Panel 让任务定义始终可见，且自动注入到 Smart Copilot 的所有 AI 请求中，实现跨窗口上下文串联。

#### Panel 2: Chat — 会话列表 + 对话 + 输入

**交互方式：**
- 左侧会话列表（支持多会话切换）
- 右侧对话区域 + 底部输入框
- 保留完整的 Markdown 渲染和代码块支持

**为什么这么设计：** 旧版只有单会话，关掉就丢失。新版支持会话持久化和历史浏览。

#### Panel 3: Files — 最近文件 + 拖放区

**交互方式：**
- 最近处理文件列表（带文件类型标签）
- 拖放区：拖入文件自动添加到当前任务上下文
- 支持格式：.py .js .ts .md .txt .docx .pdf

**为什么这么设计：** 旧版没有文件管理能力。用户处理代码审查或文档翻译时，需要反复在 Finder 和 Workspace 之间切换。

#### Panel 4: Memory — 知识与上下文

**交互方式：**
- 三个卡片入口：知识图谱（264 实体 / 166 关系）、翻译记忆（128 条）、术语库（45 条）
- 点击可展开浏览和管理

**为什么这么设计：** 知识图谱、翻译记忆、术语库是 OpenCopilot 的核心差异化能力，但旧版中它们深埋在 API 层，用户完全感知不到。Workspace Memory Panel 让这些能力可见、可触达。

#### Panel 5: Settings — 引擎 / 主题 / 快捷键 / 角色

**交互方式：**
- 四宫格卡片：Engine / Theme / Shortcuts / Persona
- 每张卡片显示当前配置摘要 + 操作按钮
- 点击按钮打开对应的 Unified Settings 弹窗

**为什么这么设计：** 旧版设置藏在齿轮图标弹窗后面。新版作为 Workspace 的一级面板，配置一目了然。

### 4.3 Smart Copilot ↔ Workspace 双向集成

| 方向 | 集成方式 |
|------|---------|
| **Workspace → Smart Copilot** | Task 定义自动注入所有 AI 请求；Chat 历史通过 Memory 系统可被引用；Files 拖放的文件可作为上下文 |
| **Smart Copilot → Workspace** | 结果可「发送到 Workspace」继续讨论；快速操作创建隐式任务上下文；PPT Studio 导出可附加到 Workspace 文件 |

---

## 五、模块三：Settings 统一 & Skills 重构

### 5.1 Unified Settings — 统一设置弹窗（600×500）

> **当前代码状态说明**：本节是 v5 里落地度最高的部分之一。`SettingsDialogV5` 已具备四分区、导航、基础保存与连接测试能力，因此这里的描述基本可视为“已接近当前实现”。

**现状问题：**
- `gui/dialogs/settings.py`（131 行）— 只管引擎配置（MiniMax/Local LLM）
- `widgets/settings_dialog.py`（390 行）— 只管个性化（外观/行为/办公/高级）
- 两个独立窗口，无共享状态，用户需打开两次

**改版方案：**

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

**四个分区：**

| 分区 | 内容 | 来源 |
|------|------|------|
| **Engine** | Backend（Cloud/Local 卡片切换）、API Key、API Base URL、Model 下拉+扫描、连接状态 | 原 `gui/dialogs/settings.py` |
| **Appearance** | Theme（Dark/Light/System）、Font Size（8-24px 滑块）、Font Family、Language、Accent Color | 原 `widgets/settings_dialog.py` |
| **Shortcuts** | 双击右键→Smart Copilot、三击右键→Workspace、Cmd+T→翻译、Cmd+P→润色、Cmd+K→技能搜索 | 原 `core/shortcut_manager.py` |
| **Advanced** | Auto Save、Recent Files 数量、Export Format、Office Mode、Config Path、Export/Import JSON、Reset | 原 `widgets/settings_dialog.py` |

**为什么 Sidebar 导航而不是 Tab：** 设置项数量多且层级明确，Sidebar 比 Tab 更适合"扫描式浏览"——用户一眼看到所有分区名称，不用逐个点击 Tab 寻找。这与 macOS System Preferences、VS Code Settings 等主流应用的设计模式一致。

**三个入口，同一弹窗：**
1. Smart Copilot Header 齿轮图标
2. Workspace Sidebar Settings Panel
3. System Tray 右键 → Settings

### 5.2 Skill 体系重构

**现状问题：**

| 文件 | 行数 | 重复问题 |
|------|------|---------|
| `skill_panel.py` | 956 | 搜索逻辑、卡片渲染、图标映射 |
| `skill_search_dialog.py` | 888 | 同样的搜索 + 同样的图标 + 同样的评分 |
| `skill_context_menu.py` | 733 | 同样的搜索 + 同样的图标 + 同样的评分 |
| **合计** | **2577** | 搜索算法复制 3 次（~450 行重复代码） |

**改版方案：提取共享层**

```
旧：3 个文件各自包含完整搜索逻辑      新：提取共享层，各组件专注 UI
┌──────────────────┐               ┌─────────────────────────┐
│ skill_panel.py   │               │ skill_registry_ui.py    │ ← 新建共享层
│  (搜索+UI 956行) │               │  SkillSearchEngine      │
├──────────────────┤               │  SkillIconProvider      │
│ skill_search.py  │               │  SkillScoreCalculator   │
│  (搜索+UI 888行) │               │  format_skill_item()    │
├──────────────────┤               └────────┬────────────────┘
│ skill_context.py │                        │ 引用
│  (搜索+UI 733行) │    ┌───────────────────┼──────────────────┐
└──────────────────┘    ▼                  ▼                  ▼
                   skill_panel.py     skill_search.py    skill_context.py
                    (~400行,纯UI)     (Cmd+K,~250行)     (~300行,纯菜单)

旧：5 文件 ~3100 行               新：4 文件 ~1200 行
```

**代码减少 60%+，且每处逻辑只维护一份。**

### 5.3 三个 Skill UI 组件

#### 组件 1: Skill Panel（嵌入式，Chat Tab 底部）

**交互方式：**
- 水平可滚动的紧凑卡片条
- 顶部 Filter Tabs：All / Coding / Knowledge / PPT / File
- 2 列紧凑卡片网格（80px 高），每张卡片：图标 + 名称 + 描述 + 状态标签 + 操作按钮
- 底部提示：「Type / in chat to search」

**为什么嵌入而不是独立 Tab：** 技能是"工具"，不是"目的地"。用户不会为了"浏览技能"而打开一个 Tab——他们是在对话/操作过程中需要调用某个技能。嵌入 Chat Tab 底部让技能"在需要的地方可见"。

#### 组件 2: Skill Search（Cmd+K 命令面板，650×550）

**交互方式：**
- **触发**：在输入框中输入 `/` 或全局快捷键 Cmd+K
- **搜索**：实时模糊匹配，300ms 防抖，按名称/标签/意图评分排序
- **导航**：↑↓ 方向键，首项自动选中
- **执行**：Enter 运行选中技能，关闭面板
- **详情**：Tab 键展开内联详情（描述、版本、意图、作者）
- **取消**：Esc 关闭面板
- **Footer**：显示快捷键提示（↑↓ 导航 / Enter 执行 / Tab 详情）

**为什么是 Command Palette 而不是传统搜索框：** Command Palette（命令面板）是当前 AI 工具的主流交互范式（VS Code、Linear、Notion、Raycast 均采用），它比传统搜索框更快（即时出现、键盘优先、无需鼠标点击）。

#### 组件 3: Skill Context Menu（右键原生菜单增强）

**交互方式：**
- 根据选区类型（文本/代码/文件）动态构建菜单项
- 菜单分为三区：常用操作 → 分隔线 → 推荐技能 → 分隔线 → 「更多技能... [Cmd+K]」
- 推荐技能基于 `IntentRouter` 的上下文分析

**为什么保留原生菜单：** 右键菜单是操作系统级别的交互，用户期望它"立即出现、无需等待"。使用 QMenu 原生渲染保证零延迟和系统一致性。

### 5.4 Design Token 体系

替代所有硬编码颜色，支持 Dark/Light 主题切换：

| 旧硬编码 | 新 Token | 语义 |
|---------|----------|------|
| `#3498db` | `tokens.accent.control` | 主色调 |
| `#27ae60` | `tokens.status.success` | 成功/在线 |
| `#ecf0f1` | `tokens.bg.elevated` | 提升背景 |
| `#dcdde1` | `tokens.stroke.tertiary` | 边框 |
| `#2c3e50` | `tokens.text.primary` | 主文本 |
| `#7f8c8d` | `tokens.text.secondary` | 次文本 |
| `#95a5a6` | `tokens.text.tertiary` | 三级文本 |

### 5.5 统一排版规格

| 层级 | 字号 | 字重 | 使用场景 |
|------|------|------|---------|
| Title | 14px | bold | 窗口标题、Tab 选中标签 |
| Heading | 13px | bold | 面板标题、区域头部 |
| Body | 12px | normal | 内容文本、聊天消息、输入框 |
| Caption | 11px | normal | 状态信息、标签、辅助文字 |
| Tiny | 10px | normal | 时间戳、快捷键、状态点 |

| 按钮尺寸 | 高度 | 内边距 | 使用场景 |
|---------|------|--------|---------|
| Large | 36px | 10px 20px | 主 CTA：打开 Studio、发送、保存 |
| Medium | 28px | 6px 14px | Primary Actions：Explain/Fix/Polish |
| Small | 22px | 4px 10px | Secondary Actions、内联操作 |
| Icon | 24px | 4px | Header 图标：persona/settings/close |

---

## 六、模块四：PPT 共创工作台（3 阶段 E2E）

### 6.1 布局结构

> **当前代码状态说明**：PPT 共创功能已完整实现，包含 `Outline` 表单编辑、`Preview` 差异预览、底部 AI 对话式修改及统一撤销链路。
> 新设计已升级为 3 阶段 E2E 流程（输入→策略发现→编辑打磨），Stage 3 采用 IDE 式双面板布局（60/40）。详见 [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)。

```
┌─ Title Bar ──────────────────────────────────────────────┐
│ 🚦 PPT 人机共创工作台  |  幻灯片:8  要点:24  原文:67%  │
├────────────┬──────────────┬──────────────────────────────┤
│ Source     │ Outline      │ Preview                      │
│ (25%)      │ + Thumbs     │ (45%)                        │
│            │ (30%)        │                              │
│ 原文文本    │ [缩略图导航]  │ WYSIWYG 预览                 │
│ 高亮已用    │ 标题/副标题   │ Click-to-Edit                │
│            │ 版式/要点     │                              │
├────────────┴──────────────┴──────────────────────────────┤
│ AI Chat (可分离)                                         │
│ 🤖 AI 助手  ● Pipeline 在线  ↩3 ↪0                      │
│ [上下文快捷指令] [输入框] [发送]                          │
├─────────────────────────────────────────────────────────┤
│                        [取消]  [全屏预览]  [导出 PPT]     │
└─────────────────────────────────────────────────────────┘
```

### 6.2 十项交互改进

> 以下 10 项主要是 **v5 目标交互清单**。当前仓库中，后端已准备了部分支撑 API（如缩略图渲染、差异预览、全屏预览），但桌面端尚未把这些体验完整接到主链路。

| # | 改进项 | 交互方式 | 为什么这么设计 | 优先级 |
|---|--------|---------|---------------|--------|
| 1 | **Thumbnail Strip 缩略图导航** | 80×45px 迷你幻灯片预览，支持拖拽排序 | 替代纯文字 QListWidget，鸟瞰全局而非逐条阅读 | P1 |
| 2 | **Streaming AI Feedback 流式反馈** | 打字指示器 + 进度条 + 部分结果实时渲染 | 用户不应在 AI 处理时面对空白等待，减少焦虑感 | P0 |
| 3 | **Click-to-Edit 预览直接编辑** | 双击预览中的标题/副标题 → 内联编辑器 | 所见即所得，不需要在 Outline Panel 和 Preview 之间来回对照 | P1 |
| 4 | **Contextual Quick Actions 上下文指令** | 快捷按钮根据当前幻灯片内容类型自适应 | 表格内容显示表格操作，图表内容显示图表操作，不再硬编码 5 个按钮 | P2 |
| 5 | **Detachable AI Chat 可分离对话** | 拖拽 Chat Header 可分离为浮动窗口 | 释放垂直空间，让 Preview/Edit 区域更大 | P3 |
| 6 | **Diff Preview 差异预览** | AI 修改前显示 before/after 对比，可 Accept/Reject/Edit | 建立用户对 AI 修改的信任感，不再"盲改" | P1 |
| 7 | **Quality Badges 质量徽章** | 非侵入式警告：「内容较密，建议拆分」「文字过长」 | 帮助用户在导出前发现质量问题，而不是导出后才发现 | P2 |
| 8 | **Theme Picker 主题选择器** | 工具栏内联色块选择器，Hover 实时预览 | 替代 Ctrl+T 循环切换（不可见、不可预测） | P2 |
| 9 | **Coverage Heatmap 覆盖率热力图** | Source Panel 顶部进度条，显示原文被利用比例 | 可视化内容覆盖缺口，驱动用户补充遗漏要点 | P3 |
| 10 | **Unified Undo Stack 统一撤销栈** | 时间线显示手动编辑(蓝)和 AI 编辑(紫)，点击回滚 | 手动和 AI 操作在同一撤销栈中，不再"AI 改了无法撤销" | P0 |

### 6.3 架构变更要求

| 变更 | 内容 | 理由 |
|------|------|------|
| **Centralized State Store** | 用 PresentationState 观察者模式替代直接修改 json_data | 4 个面板共享同一数据源，避免状态不同步 |
| **Event Bus / Mediator** | 通过事件总线下线跨面板信号 | 降低 `_connect_signals` 的接线复杂度 |
| **Deprecate Legacy PPT Preview Dialog** | 当前主入口已统一到 `StudioWindowV5`，移除旧 `PPTPreviewDialog` / `CoCreationDialog` 口径 | 消除重复入口与过时命名 |
| **Design Token System** | QSS 硬编码迁移到 JSON/YAML Token | ThemeEngine 统一分发样式变更 |

---

## 七、跳转逻辑与导航管理

### 7.1 窗口层级与召唤关系

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

**窗口互斥规则（按当前实现修正）：**
- Smart Copilot 和 Workspace **可同时存在**（用户可能一边在 Workspace 定义任务，一边用 Smart Copilot 快速操作）
- Studio 窗口由 `NavigationManager` 独立持有，**关闭 Smart Copilot 不会自动关闭 Studio**
- Settings 弹窗是模态的，**同一时间只允许一个实例**（无论从哪个入口打开）
- 当前实现里 `hide_all()` 只自动隐藏 Smart Copilot / Workspace；Studio 和 Settings 保持独立生命周期，不会跟随一起隐藏

### 7.2 跨窗口跳转完整链路

#### 链路 A：Smart Copilot → Studio（PPT 共创）

```
触发条件：用户点击 Tab 3 Studio 的「打开 Studio」按钮

┌─ Smart Copilot Tab 3 ──────────────────────────────┐
│                                                     │
│  ┌─ Studio Launcher ─────────────────────────────┐ │
│  │  🎨 Studio                                    │ │
│  │  AI 驱动的 PPT 共创工作台                       │ │
│  │                              [打开 Studio ▶]   │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  status: "💡 请先导入文本，或点击按钮粘贴内容"        │
└─────────────────────────────────────────────────────┘
                         │
                         ▼ 点击「打开 Studio」
            ┌─ 检查 self.current_text ─┐
            │                          │
      有文本(>0字符)              无文本(空)
            │                          │
            ▼                          ▼
  打开独立 Studio 窗口         弹出输入对话框
            │                   (500×400, QTextEdit)
            │                          │
            │                   用户输入/粘贴内容
            │                   或从 .txt/.md 导入
            │                          │
            │                   [确定] / [取消]
            │                     │       │
            │               有内容  │   取消→关闭对话框
            │                     │   返回 Tab 3
            ▼                     ▼
  ┌─ StudioWindowV5 (~1200×800) ───────────────┐
  │                                              │
  │  1. 窗口 show() + 居中显示                    │
  │  2. QTimer.singleShot(100ms) 异步触发         │
  │     _load_cocreation_data(text)              │
  │  3. Source Panel 加载原文 + 高亮已提取内容     │
  │  4. AI Pipeline 生成大纲：                    │
  │     - 显示 Streaming 打字指示器               │
  │     - 进度条 0% → 100%                       │
  │     - 生成 json_data (slides 数组)            │
  │  5. Outline Panel 填充表单数据                │
  │  6. Thumbnail Strip 渲染缩略图                │
  │  7. Preview Panel 渲染第一页预览              │
  │                                              │
  │  ⚠ AI 生成失败兜底：                          │
  │  _generate_fallback_outline(text) → 智能模板  │
  └──────────────────────────────────────────────┘
```

**关键交互细节：**
- 打开 Studio 时先检查现有 `StudioWindowV5` 实例是否已存在且可见；若已存在，则直接 `raise_() + activateWindow()`，不重复创建
- 如果旧窗口对象仍在但已关闭，则先清理后重新创建
- Smart Copilot 在 Studio 打开后**保持可见**，Tab 3 状态文案更新为「✅ 共创工作台已打开，切换回去即可继续编辑」
- 如果之前已有编辑（`slides_data` 存在），状态文案为「上次编辑：N 页幻灯片 — 点击按钮继续编辑」

#### 链路 B：Smart Copilot Work Tab → Chat Tab（上下文跳转）

```
触发条件：用户在 Work Tab 完成操作后点击「Chat」Tab，
         或点击 Result Area 的「Continue in Chat」按钮

Work Tab 状态                    Chat Tab 状态
┌──────────────────┐            ┌──────────────────────┐
│ current_text     │            │ chat_display 清空     │
│ context_source   │ ──跳转──→ │ 系统消息自动注入：     │
│ result_text      │            │ "已将上下文带入..."    │
│                  │            │ 📄 当前上下文(N字符,   │
│                  │            │  来源: xxx):          │
│                  │            │  preview前150字符...   │
└──────────────────┘            │                      │
                                │ chat_input.setFocus()│
                                └──────────────────────┘
```

**代码对应**：`jump_to_chat()` 方法 — 清空 chat_display，注入上下文摘要（前 150 字符 + 来源），切换到 Tab index 1，聚焦输入框。

#### 链路 C：Smart Copilot ↔ Workspace（双向串联）

```
┌─ Workspace → Smart Copilot ────────────────────────────────┐
│                                                            │
│  用户在 Workspace Task Panel 定义任务：                     │
│  "审查支付模块安全漏洞"                                     │
│         │                                                  │
│         ▼ task_changed signal                              │
│  CopilotManager._sync_task_context(task)                   │
│         │                                                  │
│         ▼                                                  │
│  Smart Copilot.ai_card.task_context = task                 │
│         │                                                  │
│         ▼                                                  │
│  所有后续 AI 请求自动注入：                                  │
│  "当前任务背景：审查支付模块安全漏洞\n\n用户消息..."          │
└────────────────────────────────────────────────────────────┘

┌─ Smart Copilot → Workspace ────────────────────────────────┐
│                                                            │
│  用户在 Work Tab 获得 AI 结果后，                            │
│  点击 Action Bar 的「Send to Workspace」按钮                │
│         │                                                  │
│         ▼                                                  │
│  workspace.receive_from_copilot(result_text, context)       │
│         │                                                  │
│         ▼                                                  │
│  Workspace Chat Panel 自动追加消息 + 切换到 Chat Panel     │
│  如果没有 Workspace 实例 → show_workspace() 先召唤          │
└────────────────────────────────────────────────────────────┘
```

#### 链路 D：Studio → Smart Copilot（结果回传）

```
Studio 导出 PPT 后：
  1. dialog.exec() == Accepted → 获取 output_path
  2. 如果 output_path 存在：
     - 弹出 QMessageBox 提示「PPT 已导出至：/path/to/file.pptx」
     - 提供两个按钮：[打开文件夹] [在 Chat 中继续讨论]
     - 点击「在 Chat 中继续讨论」→ 自动切换到 Smart Copilot Chat Tab
       并注入消息："刚刚导出了 PPT：file.pptx，有什么需要调整的吗？"
```

### 7.3 Tab 切换状态管理

| 场景 | 切换行为 | 状态保持 |
|------|---------|---------|
| **Work → Chat** | `tabs.setCurrentIndex(1)` + `chat_input.setFocus()` | Work Tab 的 result_text 保留在显示区域，不清空 |
| **Chat → Work** | `tabs.setCurrentIndex(0)` | Chat 历史保留，不回滚。Work Tab 恢复上次操作结果 |
| **任意 → Studio** | `tabs.setCurrentIndex(2)` + `_on_tab_changed(2)` | 触发智能状态检测（见 7.2 链路 A） |
| **Studio → 任意** | `tabs.setCurrentIndex(N)` | Studio 窗口保持独立运行，不受 Tab 切换影响 |

**Tab 切换时的光标恢复**：`_on_tab_changed()` 第一行执行 `QApplication.restoreOverrideCursor()` + `setCursor(ArrowCursor)`，防止拖拽或耗时操作遗留的光标状态（如 WaitCursor）影响其他 Tab。

---

## 八、PPT 共创工作台完整交互流程

### 8.1 场景一：有文档上下文 → 直接进入共创

```
前置条件：用户在任意 macOS 应用中选中文本 → 双击右键 → Smart Copilot

Step 1: Broker 无感划词
  SystemProbeClient.get_selection() → 获取选中文本
  ↓
  smart_copilot.py 通过 show_card(x, y, selected_text=text) 传入
  ↓
  文本被存储到 Smart Copilot 当前会话状态

Step 2: 用户切换到 Studio Tab
  _on_tab_changed(2) 检测到 self.current_text 有值
  ↓
  状态文案："📄 已导入 N 字文本，正在打开共创工作台..."
  ↓
  QApplication.processEvents()  ← 确保 UI 刷新
  ↓
  自动打开独立 Studio 窗口

Step 3: 创建 StudioWindowV5
  StudioWindowV5(parent=self) → show()
  ↓
  QTimer.singleShot(100ms, _load_cocreation_data)  ← 延迟确保窗口渲染完成

Step 4: AI 生成大纲 (异步)
  _load_cocreation_data(text):
    QThread → call_agent_pipeline_sync(text, action_type="ppt")
    ↓
    Pipeline: SessionSetup → Security → Immune → Planner → LLMAgent
    ↓
    LLM 返回 json_data:
    {
      "title": "2026 智能体发展报告",
      "subtitle": "多模态与人机协同的未来",
      "slides": [
        {"title": "封面", "layout": "center", "items": [...]},
        {"title": "核心技术突破", "layout": "3-col", "items": [...]},
        ...
      ]
    }
    ↓
    主线程 _update_ui():
    - SourcePanel: 显示原文 + 高亮已提取段落（蓝色背景 #4da6ff33）
    - OutlinePanel: set_slides_data(slides) → 填充表单
    - ThumbnailStrip: 渲染缩略图（80×45px）
    - PreviewPanel: 渲染第一页 WYSIWYG 预览

Step 5: 用户进入编辑循环
  - 在 Outline Panel 修改标题/版式/要点 → _on_outline_slide_changed → push_undo
  - 在 Thumbnail Strip 拖拽排序 → 触发 slides 重排 → Preview 同步刷新
  - 在 Preview Panel 双击标题 → Click-to-Edit 内联编辑 → 同步到 Outline
  - 在 AI Chat 输入指令 → AI 修改 slides → Diff Preview → Accept/Reject

Step 6: 导出
  [导出 PPT] 按钮 → FormatSkill → Markdown→PPTX 转换 → 保存对话框
  或 [全屏预览] → 全屏幻灯片放映模式
```

### 8.2 场景二：无文档上下文 → 输入对话框

```
前置条件：用户未选中文本直接双击右键，或 current_text 为空

Step 1: 用户切换到 Studio Tab
  _on_tab_changed(2) 检测到 self.current_text 为空
  ↓
  状态文案："💡 请先在 Tab 1 导入文本，或点击按钮直接粘贴内容"

Step 2: 用户点击「打开 Studio」按钮
  打开 Studio 入口时检测到无文本
  ↓
  弹出输入对话框：
  ┌─ 📝 输入 PPT 内容 (500×400) ──────────────────┐
  │                                                 │
  │  请输入或粘贴 PPT 内容，AI 将自动生成大纲：      │
  │                                                 │
  │  ┌─────────────────────────────────────────────┐│
  │  │ 例如：                                      ││
  │  │                                             ││
  │  │ 一、项目背景                                 ││
  │  │ - 市场需求分析                               ││
  │  │ - 竞争格局                                   ││
  │  │                                             ││
  │  │ 二、技术方案                                 ││
  │  │ - 架构设计                                   ││
  │  │ - 核心技术                                   ││
  │  └─────────────────────────────────────────────┘│
  │                                                 │
  │  [从文件导入 📂]       [取消]  [确定 ▶]         │
  └─────────────────────────────────────────────────┘

Step 3a: 用户手动输入内容 → [确定]
  text = text_edit.toPlainText().strip()
  如果为空 → QMessageBox.warning("请输入内容后再创建 PPT") → 返回对话框
  如果有内容 → 进入 Step 4（同场景一的 Step 3-6）

Step 3b: 用户点击「从文件导入」
  QFileDialog.getOpenFileName(
    filter="文本文件 (*.txt *.md);;Word 文档 (*.docx);;所有文件 (*)"
  )
  ↓
  读取文件内容：
  - .txt/.md → 直接读取文本
  - .docx → 调用 FormatSkill 解析 → 提取纯文本
  ↓
  填充到 QTextEdit → 用户可预览/编辑 → [确定] → 进入 Step 4

Step 3c: 用户点击 [取消] 或按 Esc
  dialog.reject() → 关闭对话框 → 返回 Tab 3 → 状态不变

Step 4+: 同场景一的 Step 3-6
```

### 8.3 场景三：已有编辑会话 → 恢复编辑

```
前置条件：用户之前打开过 Studio 并编辑了幻灯片，关闭了 Smart Copilot，但独立 Studio 窗口仍存在

Step 1: 用户再次双击右键 → Smart Copilot 重新出现
Step 2: 切换到 Studio Tab
  _on_tab_changed(2) 检测逻辑：

  if studio_window exists and isVisible():
    状态: "✅ 共创工作台已打开，切换回去即可继续编辑"
    → 用户只需切回独立 Studio 窗口即可继续

  elif studio_window exists and has slides_data:
    slides_count = len(slides_data)
    状态: "上次编辑：N 页幻灯片 — 点击按钮继续编辑"
    → 用户点击「打开 Studio」→ 重新激活 StudioWindowV5
    → 检测到旧窗口 → raise_() + activateWindow() → 恢复编辑

  else:
    走场景一或场景二的正常流程
```

### 8.4 AI 交互完整链路（共创工作台内）

```
用户在底部 AI Chat 输入指令：
"把第1页的标题改为更有吸引力的"

Step 1: 请求构造
  AIChatWidget → 构造请求:
  {
    "message": "把第1页的标题改为更有吸引力的",
    "context": {
      "current_slides": [...],     // 当前所有幻灯片数据
      "selected_slide_index": 0,   // 当前选中页
      "original_text": "...",      // 原文
      "conversation_history": [...] // 对话历史
    }
  }

Step 2: Pipeline 处理
  call_agent_pipeline_sync(message, action_type="ppt")
  ↓
  Planner: 判断 SIMPLE → One-Shot
  ↓
  CapabilityRouter → PPTSkill
  ↓
  LLM 生成修改建议（流式输出）

Step 3: 流式反馈（P0 改进）
  ┌─ AI Chat 区域 ─────────────────────────────┐
  │ 🤖 AI 助手  ● Pipeline 在线                │
  │                                              │
  │ You: 把第1页的标题改为更有吸引力的            │
  │                                              │
  │ ●●● AI 正在思考...                           │
  │ ████████░░░░ 60%                             │
  │ 正在分析第1页内容结构...                      │
  └──────────────────────────────────────────────┘

Step 4: Diff Preview（P1 改进）
  AI 返回修改建议后：
  ┌─ Diff Preview ──────────────────────────────┐
  │ - 2026 年度发展总结                          │ ← 红色背景 + 删除线
  │ + 2026 智能体发展报告：多模态与人机协同       │ ← 绿色背景
  │                                              │
  │ [✓ Accept]  [✗ Reject]  [✏ Edit First]      │
  └──────────────────────────────────────────────┘

Step 5: 用户决策
  Accept → 应用修改 → _refresh_all → 所有面板同步
  Reject → 丢弃修改 → 状态恢复
  Edit First → 进入 Outline Panel 手动微调 → 确认后再应用

Step 6: Undo Stack 记录
  push_undo(action="AI: 优化标题", type="ai")
  → 撤销栈新增一条记录（紫色标记）
```

---

## 九、异常与边界场景处理

### 9.1 网络/API 异常

| 场景 | 检测方式 | 用户反馈 | 恢复路径 |
|------|---------|---------|---------|
| **API Gateway 离线** | `AgentHealthWorker` 定时探活 `/health` | Header Online 标签变红色 Offline + 所有按钮 disabled | 网络恢复后自动重连，Header 恢复绿色 |
| **AI 生成超时** | Pipeline 30s 无响应 | Chat 显示 "⏰ AI 响应超时，正在重试..." | 自动重试 1 次，仍失败则显示 [重试] 按钮 |
| **AI 返回空结果** | `json_data` 为 None 或空 | 不弹 QMessageBox（旧版问题），改用内联提示 | Outline Panel 显示空状态："AI 未能生成大纲，请尝试更详细的内容" |
| **PPT 大纲生成失败** | `_generate_ppt_outline_with_ai` 返回 None | 静默降级到 `_generate_fallback_outline(text)` | 使用智能模板（按文本结构自动分段），Toast 提示"使用模板生成，可手动调整" |

### 9.2 数据边界

| 场景 | 阈值 | 处理方式 |
|------|------|---------|
| **文本过短** | < 20 字符 | Studio 输入对话框提示"内容较短，建议至少 50 字以获得更好的 PPT 效果" |
| **文本过长** | > 50000 字符 | 截断到 50000 字符 + Toast "内容已截断，原文保留在 Source Panel" |
| **幻灯片过多** | > 30 页 | Quality Badge 在 Thumbnail Strip 显示"⚠️ 页面较多，考虑精简" |
| **单页要点过多** | > 8 个 items | Preview Panel 底部 Tag "8 items — consider splitting" |
| **导入文件过大** | > 10MB | QFileDialog 过滤 + 超限提示"文件过大，请选择较小的文档" |
| **导入非文本文件** | .png/.jpg/.pptx 等 | 提示"暂不支持此格式，请选择 .txt/.md/.docx 文件" |

### 9.3 窗口状态异常

| 场景 | 处理 |
|------|------|
| **Smart Copilot 被关闭时 Studio 仍打开** | Studio 保持独立运行。再次双击右键 → 新建 Smart Copilot，Studio Tab 检测到旧窗口 → 显示"已打开"状态 |
| **Workspace 和 Smart Copilot 同时显示** | 两者独立运行，互不遮挡。Workspace z-order 高于 Smart Copilot |
| **Settings 弹窗已打开时再次触发** | 忽略第二次触发（`_settings_dialog is not None` 检查），或 raise 已有弹窗 |
| **macOS 收回焦点（WA_ShowWithoutActivating 冲突）** | 非 Chat Tab 不调用 `setFocus()`，避免与 `WA_ShowWithoutActivating` 冲突 |
| **拖拽/耗时操作后切换 Tab** | `_on_tab_changed()` 第一行恢复光标 `restoreOverrideCursor()` |

---

## 十、Skill 调用完整交互链路

### 10.1 链路一：输入 `/` 触发命令面板

```
Step 1: 用户在 Chat Tab 输入框输入 "/"
  chat_input.textChanged → 检测 "/" 前缀
  ↓
  SkillSearchDialog (Cmd+K Palette, 650×550) 弹出
  初始状态：显示所有已安装技能（空查询）

Step 2: 继续输入 "/cod"
  300ms 防抖 → SkillSearchEngine.fuzzy_search("cod")
  ↓
  评分排序：
  - Code Executor (score: 0.95, name match "code")
  - Coding Skill (score: 0.80, tag match "coding")
  ↓
  结果列表实时更新，首项自动高亮

Step 3: 用户按 Enter
  选中 "Code Executor" → 关闭 Palette → 清空输入
  ↓
  _on_skill_execute("code_executor", {intent: "run", input_data: {...}})
  ↓
  Chat Tab 追加系统消息: "正在执行技能: Code Executor..."
  ↓
  异步执行：
  QThread → asyncio.run_coroutine_threadsafe(skill.execute(context))
  ↓
  结果回调：
  _on_skill_result(skill_name, result) → Chat Tab 追加 AI 消息

Step 3-alt: 用户按 Tab
  展开内联详情：
  ┌─ Code Executor ────────────────────────────────┐
  │ Version: 1.2.0 | Author: built-in              │
  │ Intents: run, debug, test                      │
  │ Description: Run code in sandboxed environment │
  └────────────────────────────────────────────────┘

Step 3-alt2: 用户按 Esc
  关闭 Palette → 清空输入 → 恢复 Chat 正常输入状态
```

### 10.2 链路二：右键菜单推荐技能

```
Step 1: 用户在 IDE 中选中一段代码 → 右键
  SkillContextMenu 构建菜单：
  - 系统操作区：Copy / Explain Code / Optimize / Find Bugs
  - 分隔线
  - 推荐技能区（IntentRouter 分析上下文）：
    - _get_recommended_skills(context_type="code")
    - asyncio → IntentRouter.route(code_snippet)
    - 返回: [Code Executor, Knowledge Search]
  - 分隔线
  - "更多技能... [Cmd+K]"

Step 2: 用户点击 "Code Executor"
  SkillContextMenu.skill_selected signal
  ↓
  Smart Copilot 自动出现 + 切换到 Chat Tab
  ↓
  执行技能（同链路一 Step 3 的异步流程）

Step 3: 用户点击 "更多技能..."
  直接打开 Cmd+K Palette
```

### 10.3 链路三：Skill Panel 卡片点击

```
Step 1: 用户在 Chat Tab 底部 Skill Panel 浏览
  2 列紧凑卡片网格：
  [Code Executor ✓Active] [Knowledge Search ✓Active]
  [Web Search ✓Active]    [File Operations ○Disabled]

Step 2a: 点击 "Run" 按钮（Active 技能）
  同链路一 Step 3，直接在 Chat 中执行

Step 2b: 点击 "Enable" 按钮（Disabled 技能）
  skill_registry.enable_skill("file_operations")
  ↓
  卡片状态更新：Pill 从灰色(Disabled)变为绿色(Active)
  按钮从 "Enable" 变为 "Run"

Step 2c: 点击卡片本身（非按钮区域）
  展开内联详情（替换卡片内容为详情视图）：
  ┌─ Code Executor ──────────────────────────────┐
  │ Run code in sandboxed environment            │
  │ Version: 1.2.0 | Calls: 47                   │
  │ Supported: Python, JS, Bash                  │
  │ [▶ Run]  [⚙ Configure]  [✕ Close]           │
  └──────────────────────────────────────────────┘
```

---

## 十一、接入的能力与集成点

### 11.1 已接入的后端能力

| 能力层 | 模块 | 在新 UI 中的体现 |
|--------|------|----------------|
| **7 层 Pipeline** | SessionSetup → Security → Immune → Planner → State → CapabilityRouter → LLMAgent | Work Tab 的每次操作、Chat 的每条消息都经过完整 Pipeline |
| **Agent Loop 三范式** | One-Shot / Plan-and-Solve / Plan+ReAct | Work Tab 简单操作用 One-Shot（2-4s），Chat 复杂对话自动 Plan+ReAct |
| **7 个内置 Skill** | Knowledge / Coding / PPT / Evaluation / File / Format / Persona | Skill Panel 展示所有已安装技能，Cmd+K 搜索调用，右键菜单推荐 |
| **知识图谱** | 264 实体 / 166 关系 / 27 API | Workspace Memory Panel 可视化展示，Chat 中自动引用 |
| **Broker 系统** | 探针 / 划词 / 沙盒 / 屏幕 | Context Strip 切换数据源（Selection / Active Doc / Browser / Clipboard / File） |
| **LLM Provider** | MiMo → MiniMax → Ollama | Unified Settings Engine 分区配置，支持 Cloud/Local 切换 |
| **Lane Semaphore** | chat:10 / coding:3 / ppt:5 | 并发限制对用户透明，通过 Streaming AI Feedback 减少等待焦虑 |

### 11.2 集成入口映射

| 组件 | 入口 | 触发方式 | 上下文 |
|------|------|---------|--------|
| Unified Settings | Workspace Settings Panel | 点击 Sidebar Settings | 嵌入式面板 |
| Unified Settings | Smart Copilot Header | 点击齿轮图标 | Modal 弹窗 |
| Unified Settings | System Tray | 右键 → Settings | Modal 弹窗 |
| Skill Panel | Smart Copilot Chat Tab | 滚动到聊天底部 | 嵌入式卡片条 |
| Skill Search | Smart Copilot Input | 输入 `/` 前缀 | 内联命令面板 |
| Skill Search | 全局快捷键 | Cmd+K | 居中 Modal |
| Skill Context Menu | 任意应用选区 | 右键选中文本/代码/文件 | 原生菜单 |
| Studio | Smart Copilot Tab 3 | 点击「打开 Studio」 | StudioWindowV5 |
| Workspace | 三击右键 | 系统级手势 | 1000×700 工作台 |

---

## 十二、实施路线图

### Phase 0: 基础合并（P0，Sprint 1）

| 任务 | 涉及文件 | 工作量 |
|------|---------|--------|
| 合并 PPT Tab 3 + Tab 5 → Studio | `gui/window.py` | 低 |
| 创建 `widgets/unified_settings.py` | 新建 ~350 行 | 中 |
| 删除 `gui/dialogs/settings.py` | 删除 | 低 |
| 删除 `widgets/settings_dialog.py` | 删除 | 低 |
| 更新所有调用方 | `gui/window.py`, `gui/workspace.py` | 中 |
| Workspace 窗口尺寸升级到 1000×700 | `gui/workspace.py` | 低 |
| PPT 流式 AI 反馈 + Undo/Redo | `cocreation_widget.py` | 中 |

### Phase 1: 核心交互（P1，Sprint 2-3）

| 任务 | 涉及文件 | 工作量 |
|------|---------|--------|
| Work Tab Primary/Secondary 分层 | `gui/window.py` | 中 |
| Context-Aware Header | `gui/window.py` | 中 |
| Context Strip 数据源切换 | `gui/window.py` | 中 |
| Workspace Sidebar 导航 + 5 Panel | `gui/workspace.py` | 高 |
| 创建 `widgets/skill_registry_ui.py` | 新建 ~150 行 | 中 |
| Skill Panel 紧凑卡片重构 | `widgets/skill_panel.py` | 中 |
| Skill Search Cmd+K 命令面板 | `widgets/skill_search_dialog.py` | 中 |
| PPT Thumbnail Strip + Click-to-Edit + Diff Preview | `cocreation_widget.py` | 高 |

### Phase 2: 体验完善（P2，Sprint 3-4）

| 任务 | 涉及文件 | 工作量 |
|------|---------|--------|
| Chat Tab Context Panel | `gui/window.py` | 中 |
| 全局 Design Token 替换 | 所有 UI 文件 | 中 |
| Contextual Quick Actions | `cocreation_widget.py` | 低 |
| Quality Badges + Theme Picker | `cocreation_widget.py` | 低 |
| Session 持久化 | `memory.db` | 中 |
| Smart Copilot ↔ Workspace 双向集成 | `gui/main.py`, `gui/window.py` | 中 |

### Phase 3: 高级功能（P3，Sprint 4+）

| 任务 | 涉及文件 | 工作量 |
|------|---------|--------|
| Detachable AI Chat | `cocreation_widget.py` | 高 |
| Coverage Heatmap | `cocreation_widget.py` | 中 |
| Unified Undo Timeline UI | `cocreation_widget.py` | 中 |
| 键盘快捷键全覆盖 | `core/shortcut_manager.py` | 中 |
| 无障碍支持 | 所有 UI 文件 | 中 |

---

## 十三、改版效果预期

| 指标 | 旧版 v4.x | 新版 v5.0 | 改善 |
|------|----------|----------|------|
| Smart Copilot Tab 数 | 5 | 3 | -40% 选择成本 |
| PPT 入口数 | 2 | 1 | 消除困惑 |
| 设置弹窗数 | 2 | 1 | -50% 操作步骤 |
| Skill 代码行数 | ~2600 行 | ~1200 行 | -54% 维护成本 |
| 重复搜索逻辑 | 3 处 | 0 处 | 单一维护点 |
| 硬编码颜色 | ~40 个 | 0 个 | 支持主题切换 |
| Workspace 窗口面积 | 249,600 px² | 700,000 px² | +180% 工作空间 |
| Workspace 面板数 | 2 | 5 | +150% 功能覆盖 |
| PPT 交互改进项 | 0 | 10 | 对齐主流 AI 创作工具 |

---

> **文档版本**：v5.0  
> **更新日期**：2026-06-05  
> **设计稿参考**：smart-copilot-redesign.canvas / agent-workspace-redesign.canvas / settings-skills-redesign.canvas / ppt-cocreation-e2e-flow.canvas
