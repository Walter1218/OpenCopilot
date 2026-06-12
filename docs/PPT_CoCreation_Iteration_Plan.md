# PPT 人机共创工作台 — 交互迭代与功能迭代方案

> 基于当前代码实现（`opencopilot/capabilities/ppt/`）的深度审查，结合项目设计文档和产品目标，输出下一代交互设计方向。
>
> 交互稿 (Canvas Wireframe): `canvases/ppt-cocreation-e2e-flow.canvas.tsx`（3 阶段端到端版）
>
> 端到端设计文档: [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)

---

## 一、现状评估

### 1.1 当前架构总览

> **注意**：交互架构已重新设计为 3 阶段 E2E 流程（输入→策略→编辑打磨），
> Stage 3 采用 IDE 式双面板布局（60/40），旧的 4 面板架构保留为历史参考。
> 详见 [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)。

**旧版架构（4 面板，历史参考）：**

PPT 共创工作台是一个 PyQt6 桌面三面板编辑器：

| 面板 | 组件 | 职责 |
|------|------|------|
| 左侧 — 原文面板 | `source_panel.py` | 显示 AI 原始输出，蓝色高亮已提炼内容，支持选中/拖拽 |
| 中间 — 编辑大纲面板 | `outline_panel.py` | 幻灯片列表导航（文字）+ 表单编辑（标题/版式/要点） |
| 右侧 — 预览面板 | `preview_panel.py` | QPainter 自绘 WYSIWYG 预览，支持全屏 |
| 底部 — AI 对话框 | `ai_chat_widget.py` | 自然语言指令驱动修改，支持 Undo/Redo |
| 辅助组件 | `suggestion_bubble.py`, `content_analysis_panel.py`, `suggestion_engine.py` | AI 主动建议气泡、内容质量分析面板 |
| 数据层 | `source_matcher.py`, `content_converter.py`, `conversation_manager.py` | 双向映射、内容转换、多轮对话管理 |

### 1.2 已实现的核心能力

- ✅ 三阶段交互流程：Drafting → Interactive Editing → Export（新设计已升级为：输入→策略发现→编辑打磨）
- ✅ 对话驱动状态更新（JSON patch 局部修改模式）
- ✅ 双向联动：原文 ↔ 大纲 ↔ 预览
- ✅ Undo/Redo 操作栈（50 级历史，AI 对话驱动 + 撤销/重做按钮 + Ctrl+Z/Y 快捷键）
- ✅ 多轮对话上下文：同一对话框内共享稳定 session_id，AI 能记住历史操作
- ✅ 5 个上下文感知快捷指令：自动注入当前幻灯片标题/要点/版式信息
- ✅ 改动对比反馈：AI 修改后显示 `~~旧值~~ → **新值**` 的 before/after 对比
- ✅ 增量数据发送：仅发送当前页完整数据 + 前后各 1 页摘要，大幅降低 token 消耗
- ✅ 内容转换引擎 + 本地 ETL：表格、柱状图、折线图、饼图、流程图，自动校验补全
- ✅ 内容转换引擎：表格、柱状图、折线图、饼图、流程图
- ✅ 4 套主题切换（深色/浅色/蓝/绿）
- ✅ 丰富的快捷键体系（文件/预览/导航/编辑/AI/视图/面板/主题）

### 1.3 已识别的 UX 问题

| 编号 | 问题 | 影响 | 所在代码 |
|------|------|------|----------|
| U1 | AI 处理时无流式反馈，输入框禁用后用户无进度感知 | 用户焦虑，不知是否卡死 | `ai_chat_widget.py:_on_send` |
| U2 | 预览面板的 `SlideRenderer` 有 hit-test 和拖放信号，但未连接到编辑流程 | 用户必须切到大纲面板表单才能改内容，交互路径长 | `preview_panel.py` |
| U3 | 大纲面板用纯文字 `QListWidget` 做幻灯片导航，20+ 页时难以快速定位 | 大规模 PPT 可用性差 | `outline_panel.py` |
| U4 | 5 个快捷指令硬编码，不随幻灯片内容类型变化 | 表格/图表页面缺少对应操作入口 | `ai_chat_widget.py:_build_shortcut_command` |
| U5 | AI 对话框固定在底部 250px，不可分离或移动 | 挤占预览和编辑空间 | `cocreation_dialog.py:_init_ui` | ✅ **新设计已解决**：AI 输入移至右侧面板底部 |
| U6 | ~~AI 修改直接应用，无 before/after 对比~~ | ✅ 已解决：`_format_diff_message` 显示 `~~旧值~~ → **新值**` | `ai_chat_widget.py:_on_ai_response` |
| U7 | 主题切换通过 Ctrl+T 循环 + QMessageBox 弹窗 | 无法预览、无法直接选择、操作打断 | `cocreation_dialog.py:_on_toggle_theme` |
| U8 | 撤销/重做快捷键在 AI 对话层已接通，dialog 层待统一 | AI 对话层 Ctrl+Z/Y 可用，手动编辑层待统一 | `ai_chat_widget.py:keyPressEvent` |
| U9 | AI chat 的 undo stack 已实现，与手动编辑的变更待统一 | AI 编辑可撤销，手动编辑待接入统一栈 | `ai_chat_widget.py` vs `cocreation_dialog.py` |
| U10 | 原文面板在生成后沦为只读展示，价值快速衰减 | 30% 的屏幕空间利用率低 | `source_panel.py` | ✅ **新设计已解决**：原文面板升级为映射可视化+重新提炼 |

---

## 二、交互迭代方向（10 项改进）

### 2.1 Streaming AI Feedback — 流式反馈

**问题**：当前 `AIWorker.run()` 在后台线程积累所有 chunk，完成后一次性 emit。用户在等待期间只看到禁用的输入框，无任何进度反馈。

**改进方案**：
- 在聊天区添加 **打字指示器**（三点动画 + "AI 正在思考..."）
- 显示 **进度条**（SSE chunk 计数 / 预估总量）
- 支持 **取消中途请求**（添加 Cancel 按钮，调用 `worker.quit()`）
- **渐进式应用**：当 AI 返回结构化 JSON 时，提前解析并部分更新预览

**涉及文件**：`ai_chat_widget.py` (AIWorker, _on_send, _on_ai_response)

**优先级**：P0 / Sprint 1

---

### 2.2 Thumbnail Strip — 缩略图导航

**问题**：`outline_panel.py` 的 `SlideListWidget` 是纯文字列表，大规模 PPT 导航困难。

**改进方案**：
- 替换为 **可视化缩略图条**（80×45px mini 渲染的幻灯片预览）
- 支持 **拖拽排序**（已有 `SlideListWidget.slide_moved` 信号基础）
- 缩略图上显示 **质量徽章**（内容过多/版式不匹配等警告）
- 可选 **网格鸟瞰视图**（所有幻灯片一览，方便大规模调整）

**涉及文件**：`outline_panel.py` (SlideListWidget), `preview_panel.py` (SlideRenderer 复用)

**优先级**：P1 / Sprint 2

---

### 2.3 Click-to-Edit on Preview — 预览直接编辑

**问题**：`SlideRenderer` 已实现 `_hit_test` 和 `element_clicked` / `title_double_clicked` 信号，但未连接到编辑流程。

**改进方案**：
- **双击标题** → 在预览区显示 inline 文本编辑器 → 回车确认 → 自动同步到大纲面板和 JSON 数据模型
- **拖拽排序要点** → 在预览中直接拖拽调整 bullet points 顺序
- **右键上下文菜单** → 修改字号、颜色、对齐方式
- 编辑时显示 **虚线边框高亮**（已在 wireframe 中设计）

**涉及文件**：`preview_panel.py` (SlideRenderer 信号), `cocreation_dialog.py` (信号连接)

**优先级**：P1 / Sprint 2-3

---

### 2.4 Contextual Quick Actions — 上下文快捷指令 ✅ 部分已实现

**问题**：`_build_shortcut_command` 硬编码了 5 个标签（换个标题、添加要点、换版式、精简内容、转图表），不随幻灯片内容类型变化。

**已实现**：`_build_shortcut_command` 已注入当前幻灯片上下文（标题、要点摘要、版式），AI 不再盲猜。5 个快捷指令均携带语义化上下文。

**待实现**：根据 `content_type` 动态变化按钮列表（文本页/表格页/图表页/流程图页）。

**涉及文件**：`ai_chat_widget.py` (shortcut_buttons, _build_shortcut_command)

**优先级**：P2 / Sprint 3（基础版已完成，动态版待后续迭代）

---

### 2.5 Detachable AI Chat — 可分离对话面板

**问题**：AI 对话框固定嵌入底部，maxHeight=250px，无法调整位置。

**改进方案**：
- 添加 **拖拽分离手柄**：用户拖拽对话框头部可将其分离为浮动窗口
- 支持 **侧边栏模式**：将对话面板停靠到右侧，释放垂直空间
- 分离/吸附状态 **记忆到 QSettings**
- 分离模式下保持与主窗口的信号连接（slides_updated 等）

**涉及文件**：`cocreation_dialog.py` (布局重构), `ai_chat_widget.py` (添加 DockWidget 支持)

**优先级**：P3 / Sprint 4

---

### 2.6 Diff Preview — 差异预览 ✅ 部分已实现

**问题**：`_on_ai_response` 解析 JSON 后直接调用 `_apply_update` 应用改动，用户无法在应用前审查变更。

**已实现**：所有 `_apply_*` 方法返回 `dict`（含 `summary/field/old_value/new_value`），`_format_diff_message()` 构建 markdown 对比消息：`~~旧值~~ → **新值**`。AI 修改后自动展示 before/after 对比。

**待实现**：Accept/Reject 交互（目前直接应用，用户通过 Undo 撤销）、批量修改逐项审查。

**涉及文件**：`ai_chat_widget.py` (_on_ai_response, _format_diff_message)

**优先级**：P1 / Sprint 2（基础对比已实现，交互式审查待后续迭代）

---

### 2.7 Proactive Quality Badges — 主动质量徽章

**问题**：`ContentAnalysisPanel` 和 `SuggestionBubble` 已实现，但触发时机有限。

**改进方案**：
- **缩略图徽章**：在 Thumbnail Strip 上显示小圆点警告
  - ⚠️ 内容过密（>100 字 / >8 个要点）
  - ⚠️ 版式与内容不匹配（如三栏版式只有 1 个要点）
  - ⚠️ 标题过长（>20 字）
- **大纲面板内联提示**：在编辑表单下方显示非侵入式提醒条
- **规则引擎**：基于 `context_analyzer.py` 的 `StyleCheckResult` 驱动，纯本地判断无需 LLM

**涉及文件**：`suggestion_engine.py`, `outline_panel.py`, `outline_panel.py` (SlideListWidget)

**优先级**：P2 / Sprint 3

---

### 2.8 Theme Picker — 主题选择器

**问题**：主题切换通过 `Ctrl+T` 循环 + `QMessageBox.information` 弹窗，打断用户操作。

**改进方案**：
- 在工具栏添加 **内联色块选择器**（4 个圆角色块，当前主题高亮边框）
- **Hover 实时预览**：鼠标悬停即切换，移开恢复
- **分离 UI 主题与 PPT 主题**：
  - UI 主题 = 编辑器暗色/亮色皮肤（现有 THEMES）
  - PPT 主题 = 幻灯片母版配色（corporate_blue, tech_blue 等）
- 持久化到 `QSettings`

**涉及文件**：`cocreation_dialog.py` (_create_toolbar, _on_toggle_theme, THEMES)

**优先级**：P2 / Sprint 3

---

### 2.9 Coverage Heatmap — 覆盖率热力图

**问题**：原文面板在初始生成后价值快速衰减。

**改进方案**：
- 在原文面板头部添加 **迷你进度条**（`QProgressBar` 扁平样式），显示已提炼文本占比
- `SourceMatcher.get_extracted_ranges()` 已有数据基础
- **智能提示**：覆盖率 < 50% 时显示 "📄 仍有大量未使用内容" 提示
- **高亮动画**：当用户通过 AI 修改某个幻灯片时，对应的原文高亮区域短暂脉冲

**涉及文件**：`source_panel.py` (SourcePanel header), `source_matcher.py`

**优先级**：P3 / Sprint 4

---

### 2.10 Unified Undo Stack — 统一撤销栈 ✅ 部分已实现

**问题**：
- `cocreation_dialog.py` 的 `_on_undo` / `_on_redo` 是空 `pass`
- `ai_chat_widget.py` 有独立的 `_undo_stack` / `_redo_stack`，但手动编辑（通过大纲表单）不进入此栈

**已实现**：
- `ai_chat_widget.py` 中 `_undo_stack` / `_redo_stack`（最大 50 条），Ctrl+Z/Y 快捷键，↩/↪ 按钮
- `_push_undo_state()` 在 `_on_ai_response` 应用修改前自动保存 `deepcopy(slides_data)`
- 按钮 hover 显示栈深度（如 `撤销 (3) — Ctrl+Z`）

**待实现**：
- `cocreation_dialog.py` 层面的统一 UndoManager，合并手动表单编辑和拖拽排序
- 可视化时间线（紫色=AI 编辑，蓝色=手动编辑）
- 点击任意历史点回滚

**涉及文件**：新建 `undo_manager.py`, `cocreation_dialog.py`, `ai_chat_widget.py`, `outline_panel.py`

**优先级**：P3 / Sprint 4（AI 对话层已完成，统一栈待后续迭代）

---

## 三、功能迭代方向

### 3.1 多页批量 AI 操作

**当前限制**：所有 AI 操作通过 `slide_index` 定位单页。

**新增能力**：
- **"统一风格"**：AI 遍历所有幻灯片，统一语言风格和视觉调性
- **"自动平衡"**：AI 检测内容过密的页面，自动拆分
- **"添加过渡页"**：AI 根据前后页内容关系，自动生成过渡叙事页
- **"执行摘要页"**：从全部幻灯片内容自动生成目录/摘要页

**涉及文件**：`ai_chat_widget.py` (_apply_update 新增 batch action), `conversation_manager.py`

---

### 3.2 ConversationManager 集成

**当前状态**：`conversation_manager.py` 已实现多轮对话管理、意图识别、追问澄清，但未接入 `AICopilotChatWidget`。

**集成方案**：
- AI 返回模糊结果时，触发 **澄清对话**："你是指第2页还是第3页？" 附带可点击选项
- 支持 **批量指令解析**："把所有标题改短" → 返回多个 update actions
- **对话回放**：保存对话序列为 "recipe"，可一键重用到其他 PPT

---

### 3.3 视觉资产管线 (Phase 3)

- 解析 `visual_hint` 字段，调用 Unsplash/Pexels API 或本地模型生成配图
- 图标库集成：`icon` 类型 item 显示分类 SVG 图标选择器
- 配色生成器：从上传图片提取主色调应用到幻灯片主题

---

### 3.4 逆向解析 / 一键美化 (Phase 4)

- 拖入现有 `.pptx`，通过 `python-pptx` 解析为 JSON
- 模板市场：预设布局模板一键套用
- 风格迁移："让它看起来像 Apple Keynote" — AI 全局重排

---

### 3.5 导出增强

- **多格式**：PDF、Keynote、Google Slides（API）、HTML 演示（reveal.js）
- **演示模式**：内置演讲者视图 + 演讲笔记 + 计时器
- **版本快照**：在关键编辑节点自动保存版本，支持回滚
- **分享链接**：生成可分享 URL（需后端支持）

---

### 3.6 智能布局引擎

- **Auto-layout 推荐**：AI 分析内容后推荐最优版式
- **自定义布局构建器**：用户定义网格布局
- **响应式预览**：16:9 / 4:3 / 移动端比例切换
- **动画提示**：JSON 中支持 `transition` 字段（fade/slide/zoom）

---

## 四、架构改进要求

### 4.1 中央化状态管理

**现状**：`slides_data` / `json_data` 仍会在 `StudioWindowV5` 相关面板中被直接 mutate，状态收口还可以继续加强。

**改进**：
```
PresentationState (单例)
  ├── slides: List[dict]         # 幻灯片数据
  ├── current_index: int          # 当前选中页
  ├── theme: str                  # UI 主题
  ├── ppt_theme: str              # PPT 母版主题
  └── observers: List[Callable]   # 观察者列表

每个面板 subscribe 到自己关心的状态切片。
所有变更通过 state.apply(action) 收口，自动触发 undo push + observer notify。
```

### 4.2 事件总线 / Mediator 模式

**现状**：`_connect_signals` 中有 10+ 条跨面板信号连接，耦合度高。

**改进**：引入轻量 EventBus，各面板 publish/subscribe 事件，降低直接信号耦合：
```python
class EventBus(QObject):
    slide_selected = pyqtSignal(int)
    slide_changed = pyqtSignal(int, dict)
    ai_update_applied = pyqtSignal(list)
    undo_pushed = pyqtSignal(str, str)  # description, type
```

### 4.3 设计 Token 系统

**现状**：每个 widget 硬编码 QSS 样式，`apply_theme` 逐 widget 刷新。

**改进**：将颜色/间距/圆角等抽取为 JSON/YAML token 文件，单一 `ThemeEngine` 读取后生成全局 QSS。

### 4.4 废弃遗留入口

当前主入口已经统一为 `StudioWindowV5`。`gui/dialogs/ppt_preview.py` (PPTPreviewDialog) 与旧 `CoCreationDialog` 口径都应视为历史遗留，不再作为现行方案描述。

**涉及文件**：`gui/dialogs/ppt_preview.py`, `gui/v5/studio_tab.py`, `gui/v5/studio_window.py`, `smart_copilot.py`

### 4.5 运行时护栏与专项评测（已落地）

以下能力已经不再是“规划项”，而是当前代码中已落地的现状：

#### A. `ppt_editor` 直编护栏

当前 runtime 中间件会对 `ppt_editor` 请求施加额外约束：

- 关闭 web search
- 跳过通用 tools prompt
- 强制 `answer-first`
- 禁止再次请求 `read_slide`
- 默认只修改当前页
- 鼓励直接输出 `render_commands`

这使得当前 PPT 共创链路的真实执行方式，已经从“普通聊天”升级为“受控编辑任务”。

#### B. `F_polish` 忠实改写专项提示

当前 benchmark 构造层已为 `F_polish` 额外注入润色约束，要求：

- 逐条改写
- 保留数字、时间、金额、专有名词
- 保留因果、对比、转折关系
- 保持条目顺序与粒度
- 优先输出可定位的 `render_commands`

#### C. 忠实改写专项 benchmark

围绕“专业化且保事实”，当前已形成固定回归入口：

- 数据集：`tests/test_data/ppt_faithful_rewrite_cases.json`
- 模式：`OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`
- 评测入口：`tests/e2e/test_ppt_cocreation_quality_benchmark.py`
- 单测：`tests/unit/test_ppt_faithful_rewrite_benchmark.py`

当前这套专项基准的意义是：

- 不再只靠单条 case 调 prompt
- 不再只看主观“文风更高级”
- 而是固定样本、固定准入门槛、固定版本对比

#### D. Prompt 已进入版本化管理

当前 `ppt_editor` prompt 的代码真源在：

- `opencopilot/shared/prompt.py`

并且已通过：

- `PPT_EDITOR_PROMPT_VERSION`
- `prompts/ppt_editor/`

进行版本快照管理。当前最新快照已推进到：

- `v7_compound_task`

---

## 五、实施优先级路线图

> **注意**：以下 Sprint 计划基于旧版 4 面板架构制定。新的 3 阶段 E2E 设计已重新组织任务，
> 具体实施顺序参见 [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md) §六架构映射表。

### Sprint 0 — E2E 架构重构（新增）

| 任务 | 工作量 | 影响 | 状态 |
|------|--------|------|------|
| Stage 1 空状态页（QLineEdit → TextArea + 入口路由） | Medium | 统一入口体验 | ⏳ 待实现 |
| Stage 2 修辞分析 + 策略面板 | High | 新增策略发现能力 | ⏳ 待实现 |
| Stage 3 IDE 式双面板布局（60/40） | High | 核心交互升级 | ⏳ 待实现 |
| 原文映射标签 + 双向联动 + 重新提炼 | High | 原文面板价值重塑 | ⏳ 待实现 |
| AI Diff Overlay（浮层式确认） | Medium | AI 修改可控性 | ⏳ 待实现 |

### Sprint 1 — Quick Wins（1-2 周）

| 任务 | 工作量 | 影响 | 状态 |
|------|--------|------|------|
| 接通 Undo/Redo/Zoom 空实现 | Low | 修复快捷键失效问题 | ✅ AI 对话层已接通 Ctrl+Z/Y + 按钮 |
| 流式 AI 反馈（打字指示器 + 进度条 + Cancel） | Medium | 核心体验提升 | ⏳ 待实现 |
| 统一 Undo Stack（合并手动+AI 编辑） | Medium | 撤销行为一致性 | 🔄 AI 对话层已完成，dialog 层待统一 |
| 清理遗留 PPTPreviewDialog / CoCreationDialog 口径 | Low | 减少维护成本 | 🔄 文档口径已统一到 `StudioWindowV5`，代码清理可继续推进 |

### Sprint 2 — Core Interaction（2-3 周）

| 任务 | 工作量 | 影响 | 状态 |
|------|--------|------|------|
| Thumbnail Strip 缩略图导航 | Medium | 大规模 PPT 可用性 | ⏳ 待实现 |
| Click-to-Edit 预览直接编辑 | High | 减少交互路径 | ⏳ 待实现 |
| Diff Preview 差异预览 | Medium | 用户信任感 | ✅ 基础对比已实现 |

### Sprint 3 — Intelligence（2 周）

| 任务 | 工作量 | 影响 | 状态 |
|------|--------|------|------|
| Contextual Quick Actions | Low | 操作效率 | ✅ 基础版已实现（带上下文注入） |
| Quality Badges 质量徽章 | Low | 内容质量保障 | ⏳ 待实现 |
| Theme Picker 内联选择器 | Low | 主题切换体验 | ⏳ 待实现 |
| ConversationManager 集成 | Medium | 多轮对话智能化 | 🔄 多轮上下文已修复，Intent 待集成 |

### Sprint 4 — Polish & Expand（3-4 周）

| 任务 | 工作量 | 影响 |
|------|--------|------|
| Detachable AI Chat | High | 布局灵活性 |
| Coverage Heatmap | Medium | 原文面板利用率 |
| Undo Timeline 可视化 | Medium | 操作可追溯性 |
| 多格式导出 | High | 产品适用场景 |

### Long-term — Vision

| 任务 | 说明 |
|------|------|
| 视觉资产管线 (Phase 3) | AI 配图、图标库、配色生成器 |
| 逆向解析 / 一键美化 (Phase 4) | .pptx → JSON → 重新渲染 |
| 演示模式 | 演讲者视图 + 笔记 + 计时 |
| 协作编辑 | 多人实时协作（需后端） |
| 自定义布局引擎 | 用户定义网格/模板 |

---

## 六、验证清单

每项改进完成后，需通过以下验证：

- [ ] 键盘可完整操作（不依赖鼠标）
- [ ] 信号连接无泄漏（断开旧 worker 信号）
- [ ] `blockSignals(True/False)` 防递归更新
- [ ] 主题切换后所有子面板样式一致
- [ ] Undo/Redo 状态完整恢复
- [ ] AI 返回空/异常时有优雅降级
- [ ] Pipeline 追踪日志覆盖（`PipelineObservability` 打点）
- [ ] 全功能链路测试验证（非仅 mock）

---

> **相关文档**：
> - 端到端设计：[`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)（3 阶段交互流程 + IDE 式布局）
> - 基础设计：[`PPT_CoCreation_Design.md`](./PPT_CoCreation_Design.md)（架构、JSON Schema、路线图）
> - Prompt 演进：[`PPT_COCREATION_PROMPT_EVOLUTION_20260610.md`](./PPT_COCREATION_PROMPT_EVOLUTION_20260610.md)
> - 忠实改写规范：[`PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md`](./PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md)
> - Prompt 迭代手册：[`PPT_FAITHFUL_REWRITE_PROMPT_ITERATION_PLAYBOOK.md`](./PPT_FAITHFUL_REWRITE_PROMPT_ITERATION_PLAYBOOK.md)
> - 交互稿：`canvases/ppt-cocreation-e2e-flow.canvas.tsx`（3 阶段端到端版）
> - 核心代码：`opencopilot/capabilities/ppt/`
