# OpenCopilot v5.3 精简版交互设计

> 版本 v5.3 | 2026-06-12 | 精简版交互重设计 | Canvas SDK 组件化

---

## 0. 文档定位

本文档基于最新 Canvas SDK 组件化设计稿，描述 OpenCopilot v5.3 精简版交互方案。核心目标是**减少 48% UI 元素**，提升用户体验和可维护性。

### 0.1 设计目标量化

| 指标 | 旧版 | 精简版 | 改善 |
|------|------|--------|------|
| UI 元素总数 | 101 | 52 | **-48%** |
| Smart Copilot Tab 数 | 5 | 1 (极简) | **-80%** |
| Workspace Panel 数 | 5 | 4 | **-20%** |
| Settings 入口数 | 4 | 2 | **-50%** |
| Navigation Flows | 10 | 7 | **-30%** |

---

## 1. Smart Copilot (v3) — 极简版

### 1.1 窗口规格

- **召唤方式**：双击右键
- **窗口尺寸**：35% x 45% 屏幕
- **设计原则**：Header 极简化、对话历史增强、输入框简化

### 1.2 Header 极简化

**设计变更**：
- 移除所有非必要元素（Source chips、字数统计、角色选择器、关闭按钮）
- 仅保留：**Selection 指示器** + **翻译/设置** 两个 icon

**为什么这么设计**：
- 旧版 Header 包含 5+ 个元素，用户注意力分散
- 精简后用户一眼看到核心信息：当前选区 + 快速操作

```
┌─ Header (极简) ─────────────────────────────────────┐
│ [Selection]                              [翻译] [设置] │
└──────────────────────────────────────────────────────┘
```

### 1.3 对话历史增强

**设计变更**：
- AI 回复下方添加 **复制/应用** 操作按钮
- 来源信息可点击跳转（如 `q2_sales_data.xlsx 第 15 行`）

**为什么这么设计**：
- 旧版 AI 回复只能看不能用，用户需要手动复制
- 新版让结果可操作，减少用户额外步骤

```
┌─ AI 回复 ────────────────────────────────────────────┐
│ Q2 营收 3800 万，与 Excel 原始数据一致。               │
│ 📄 q2_sales_data.xlsx 第 15 行                        │
│ [复制] [应用]                                         │
└──────────────────────────────────────────────────────┘
```

### 1.4 输入框简化

**设计变更**：
- placeholder 简化为 `问点什么...`
- 移除复杂的快捷标签和功能按钮

**为什么这么设计**：
- 旧版输入框周围有 8+ 个功能标签，新用户困惑
- 精简后降低认知负担，高级功能通过 Settings 开启

---

## 2. Agent Workspace — 4 Panel 工作台

### 2.1 窗口规格

- **召唤方式**：三击右键
- **窗口尺寸**：60% x 65% 屏幕
- **Panel 数量**：4 个（Task / Chat / Files / Memory）
- **Settings 处理**：删除独立 Panel，改为 Sidebar 齿轮图标

### 2.2 四个核心 Panel

| Panel | 职责 | 关键交互 |
|-------|------|----------|
| **Task** | 任务定义与管理 | 模板加载、剪贴板导入、最近文件 |
| **Chat** | 连续对话 | 多会话切换、流式输出、停止生成 |
| **Files** | 文件管理 | 筛选、预览、导入任务、发送 Studio/Chat |
| **Memory** | 知识与上下文 | 知识图谱、翻译记忆、术语库概览 |

### 2.3 意图路由 UI (Chat Panel)

**设计变更**：
- 新增意图选择器：Auto + 8 个意图（Chat/Research/PPT/Translate/Explain/Fix/Polish/Review）
- Auto 模式自动检测用户意图，显示置信度和命中词

**为什么这么设计**：
- 旧版 Chat 只有纯对话，用户需要手动说明意图
- 新版通过意图路由自动优化 AI 响应质量

```
┌─ 意图选择器 ─────────────────────────────────────────┐
│ [Auto] [Chat] [Research] [PPT] [Translate] [Explain] │
│ [Fix] [Polish] [Review]                               │
├─ Auto 模式检测结果 ───────────────────────────────────┤
│ 识别意图: PPT | 置信度: 92% | 命中词: 共创、PPT、演示 │
└──────────────────────────────────────────────────────┘
```

### 2.4 Settings 删除理由

**设计变更**：
- 删除 Workspace Settings Panel
- Settings 功能移至 Sidebar 齿轮图标，点击后弹出 Settings Dialog

**为什么这么设计**：
- Settings 是低频操作，不值得占用一级 Panel
- 齿轮图标是行业标准入口，用户直觉明确

---

## 3. V5Plus CoCreate — 核心动线

### 3.1 三阶段 E2E 流程

| Stage | 窗口尺寸 | 核心任务 |
|-------|----------|----------|
| **Stage 1: 输入原文** | 45% x 50% | 粘贴/导入文档内容 |
| **Stage 2: 生成** | 60% x 60% | 文档分析 + 策略推荐 + 生成 PPT |
| **Stage 3: 编辑导出** | 80% x 80% | 60/40 布局：PPT 预览 + 原文对照 |

### 3.2 Stage 1: 输入原文

**交互方式**：
- 有文本时自动跳过，直接进入 Stage 2
- 无文本时显示输入区域，支持粘贴或文件导入

**为什么这么设计**：
- 用户经常从 Chat/Work Tab 带着文本进入，无需重复输入
- 空状态引导用户明确输入

### 3.3 Stage 2: 生成

**交互方式**：
- 文档分析：显示字数、段落数、内容类型标签
- 策略推荐：默认推荐金字塔式（结论先行，数据支撑），可折叠查看
- 生成按钮：点击后进入 Stage 3

**为什么这么设计**：
- 策略推荐帮助用户理解 AI 如何组织内容
- 可折叠设计让高级用户可以自定义策略

### 3.4 Stage 3: 编辑导出

**布局结构**：
- **左侧 60%**：PPT 预览区
  - 幻灯片缩略图导航
  - AI 建议修改（Diff Preview，可接受/拒绝）
  - 版式选择器（center/text/3-col/chart/timeline）
- **右侧 40%**：原文区
  - 段落与幻灯片对应关系（如 S2、S3 标签）
  - 指令输入框（改标题、调版式...）

**为什么这么设计**：
- 60/40 布局是 IDE 风格标准，用户熟悉
- 原文与 PPT 并排对照，方便内容核对

### 3.5 多表达方式选择器

**设计变更**：
- 新增 6 种表达模式：纯文本、图文混排、表格、图表、流程图、三栏布局
- 选择后 AI 自动调整幻灯片布局和内容组织方式

**为什么这么设计**：
- 旧版只有固定模板，用户无法控制表达方式
- 新版让用户根据内容类型选择最佳表达方式

---

## 4. Settings Dialog — 分层引擎

### 4.1 窗口规格

- **召唤方式**：SC Header 齿轮 + WS Sidebar 齿轮
- **窗口尺寸**：45% x 55% 屏幕
- **分区数量**：4 个（Engine / Appearance / Shortcuts / Advanced）

### 4.2 设计变更

**入口收敛**：
- 旧版 3-4 个入口 → 新版 2 个入口（SC Header + WS Sidebar 齿轮）
- 减少入口混乱，明确触发路径

**UI 元素可配置**：
- Smart Copilot 显示元素（Source chips、字数统计、角色选择器、关闭按钮）默认隐藏
- 快捷功能标签（Explain、Summarize、Polish、修订）默认隐藏
- 用户可通过 Settings 开启这些高级功能

**主题迁移**：
- 原 Studio 底部 4 主题按钮移至 Settings Appearance
- 支持 Dark / Light / Auto 三种模式

### 4.3 Skill 体系 UI

**Skill Panel**：
- Sidebar 集成，展示所有已安装 Skill
- 表格形式：Skill 名称、状态（Active/Inactive）、操作（配置）

**Skill Search**：
- Cmd+K 快捷键触发
- 搜索框 + 最近使用列表
- 支持模糊匹配和意图识别

---

## 5. Navigation Flows — 精简版

### 5.1 窗口层级

| Level | 窗口 | 召唤方式 | 尺寸 |
|-------|------|----------|------|
| 0 | System Tray | 始终在菜单栏 | - |
| 1 | Smart Copilot | 双击右键 | 35% x 45% |
| 2 | Workspace | 三击右键 | 60% x 65% |
| 2 | V5Plus CoCreate | 输入 CoCreate | IDE 窗口 |
| 3 | Settings Dialog | SC/WS 齿轮 | 45% x 55% |

### 5.2 Navigation Flow Matrix

| ID | From -> To | Trigger | 保留? | 理由 |
|----|-----------|---------|-------|------|
| F1 | SC Work <-> Chat | Tab click | Yes | 核心 Tab 切换 |
| F2 | SC -> V5Plus CoCreate | Input CoCreate | Yes | PPT 入口 |
| F3 | SC -> Settings Dialog | Header gear | Yes | Settings 入口 |
| F4 | WS -> Settings Dialog | Sidebar gear | Yes | Settings 入口 |
| F5 | Work -> Chat (result) | Inline prompt | Yes | 自然流转 |
| F6 | Chat -> V5Plus | Send to CoCreate | Yes | Chat -> PPT |
| F7 | Tray -> SC / WS | Right-click | Yes | 主入口 |
| F8 | V5Plus -> SC Chat | After export | **Del** | 低频 |
| F9 | CoCreation -> SC | Stage 3 jump | **Del** | 低频 |
| F10 | WS Settings -> Dialog | Config btn | **Del** | 冗余层 |

### 5.3 Chat 统一化

**设计变更**：
- 旧版：2 个独立 Chat（SC Chat Tab + WS Chat Panel），会话不共享
- 新版：1 个统一 ChatWidget，共享会话和历史

**为什么这么设计**：
- 用户在 SC 和 WS 之间切换时，对话历史丢失是最大痛点
- 统一 ChatWidget 让上下文无缝传递

```
┌─ Before: 2 Isolated Chats ──────────────────────────┐
│ SC Chat Tab: Bubble UI / session A / No actions     │
│ WS Chat Panel: Plain HTML / session B / 9 actions   │
│ ❌ NOT connected                                    │
└─────────────────────────────────────────────────────┘

┌─ After: 1 Unified ChatWidget ───────────────────────┐
│ SC Chat Tab: ChatWidget                             │
│ WS Chat Panel: ChatWidget                           │
│ ✅ Shared session + history + actions               │
└─────────────────────────────────────────────────────┘
```

---

## 6. Design Token 体系

### 6.1 使用 `useHostTheme()` 获取 Token

```tsx
const { tokens } = useHostTheme();

// 使用示例
<Text style={{ color: tokens.text.secondary }}>次要文本</Text>
<Stack style={{ borderColor: tokens.stroke.tertiary }}>边框</Stack>
```

### 6.2 核心 Token 映射

| 用途 | Token | 语义 |
|------|-------|------|
| 主文本 | `tokens.text.primary` | 主要文本颜色 |
| 次文本 | `tokens.text.secondary` | 辅助说明文本 |
| 边框 | `tokens.stroke.tertiary` | 分隔线、卡片边框 |
| 成功状态 | `tokens.status.success` | 在线、完成 |
| 警告状态 | `tokens.status.warning` | 注意、进行中 |
| 信息状态 | `tokens.status.info` | 提示、说明 |

---

## 7. 实施路线图

### 7.1 Phase 0: Smart Copilot 极简化 (Sprint 1)

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| Header 精简为 Selection + 翻译/设置 | P0 | 低 |
| 对话历史添加复制/应用按钮 | P0 | 低 |
| 输入框 placeholder 简化 | P0 | 低 |
| 高级功能默认隐藏，Settings 开启 | P1 | 中 |

### 7.2 Phase 1: Workspace 4 Panel (Sprint 2)

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| 删除 Settings Panel | P0 | 低 |
| Sidebar 齿轮图标触发 Settings Dialog | P0 | 中 |
| 意图路由 UI (Auto + 8 意图) | P1 | 中 |
| Chat 统一化（共享会话） | P1 | 高 |

### 7.3 Phase 2: V5Plus CoCreate 优化 (Sprint 3)

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| Stage 2 策略推荐（可折叠） | P1 | 中 |
| Stage 3 版式选择器 | P1 | 中 |
| 多表达方式选择器（6 种模式） | P2 | 高 |
| AI Diff Preview（接受/拒绝） | P1 | 中 |

### 7.4 Phase 3: Settings & Flows 精简 (Sprint 4)

| 任务 | 优先级 | 工作量 |
|------|--------|--------|
| Settings 入口收敛（4→2） | P0 | 低 |
| UI 元素可配置（默认隐藏高级功能） | P1 | 中 |
| 删除低频 Navigation Flows (F8/F9/F10) | P0 | 低 |
| Design Token 全量替换 | P1 | 高 |

---

## 8. 与旧版文档对照

### 8.1 与 UI_Redesign_Plan_v5.md 的关系

- **v5.1 文档**：详细描述了 3-Tab 架构、5-Panel Workspace、10 项 PPT 改进
- **v5.3 本文档**：在此基础上精简，删除低频功能，聚焦核心动线

### 8.2 主要差异

| 模块 | v5.1 设计 | v5.3 精简版 | 变更理由 |
|------|----------|------------|----------|
| Smart Copilot | 3 Tab (Work/Chat/Studio) | 1 极简浮层 | 用户测试显示 80% 操作只需快速问答 |
| Workspace | 5 Panel + Settings | 4 Panel，Settings 删除 | Settings 低频，齿轮图标足够 |
| Navigation Flows | 10 条 | 7 条 | 删除 3 条低频跳转 |
| UI 元素 | 101 个 | 52 个 | 减少 48%，降低维护成本 |

---

## 9. Canvas SDK 组件化

### 9.1 使用的 SDK 组件

| 组件 | 用途 |
|------|------|
| `Stack` | 垂直布局容器 |
| `Row` | 水平布局容器 |
| `Grid` | 网格布局 |
| `Card / CardHeader / CardBody` | 卡片容器 |
| `Stat` | 统计数字展示 |
| `Tag` | 标签（Tab 替代） |
| `Pill` | 胶囊标签 |
| `Button` | 按钮 |
| `Table` | 表格 |
| `Callout` | 提示框 |
| `Switch` | 开关 |
| `Divider` | 分隔线 |
| `Spacer` | 间距 |
| `Text / H1-H3` | 文本 |

### 9.2 为什么使用 SDK 组件

- **编译兼容**：避免 Sucrase 解析器状态损坏
- **主题一致**：自动适配 `useHostTheme()` tokens
- **维护性**：组件库统一升级，无需逐文件修改
- **可读性**：语义化组件比手写 `<div style={{...}}>` 更清晰

---

## 10. 设计稿参考

- **Canvas 文件**：`opencopilot-interaction-redesign.canvas.tsx`
- **旧版文档**：`UI_Redesign_Plan_v5.md`
- **vNext 文档**：`VNEXT_SMART_COPILOT_UI_SPEC.md`

---

> **文档版本**：v5.3  
> **更新日期**：2026-06-12  
> **设计稿**：opencopilot-interaction-redesign.canvas.tsx (Canvas SDK 组件化版本)
