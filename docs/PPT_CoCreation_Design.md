# OpenCopilot 伴生智能体：PPT 人机共创引擎设计方案

> 本文已按当前 `Studio V5` 实现更新，旧的 `PPTPreviewDialog / asu_custom_agent` 口径已废弃。

## 一、 核心定位与设计理念
将现有的“单向格式转换工具”升级为“**伴生式 AI 策划师与排版助理**”。
核心理念：**对话驱动状态更新 (Conversation-driven State Update)**。用户只需用自然语言发号施令，AI 在后台实时更新结构化数据，并在前端实时渲染大纲预览。只有在自然语言遇到瓶颈时，才提供轻量级的手动干预作为兜底。

## 二、 交互心流 (User Workflow)

> **最新设计**：交互流程已精简为 3 阶段端到端设计，详见
> **→ [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)**
>
> 以下保留为历史参考。

整个交互过程分为三个递进阶段：

### 阶段 1：意图捕获与 AI 初版生成 (Drafting)
1. **输入**：用户拖拽文档到 Smart Copilot 窗口，或直接发送指令（如：“把这份产品介绍做成 PPT”）。
2. **AI 处理**：大模型扮演“策划师”，对长文本进行降维提炼，自动规划页数，并为每一页分配合适的版式（图文、三栏、纯文本）。
3. **入口弹出**：当 AI 完成输出后，系统利用底层的正则与解析引擎 (`extract_json_from_text`) 自动扫描内容。一旦识别出合法的 JSON 结构或标准的 Markdown 大纲，界面右下角会自动弹出 **[💾 导出为 PPT]** 按钮，提供人机共创交互的入口。

### 阶段 2：可视化人机共创排版 (Interactive Editing)
这是人机共创的核心。用户点击入口后，不会直接生成死板的 PPT，而是进入独立的 **PPT 人机共创工作台 (`StudioWindowV5`)**。
1. **左侧大纲导航**：直观展示总页数和各页主标题，用户可以快速点击切换幻灯片。
2. **右侧表单编辑**：用户可以对当前选中的幻灯片进行细粒度修改：
   - 修改标题、副标题。
   - 调整页面版式（下拉选择 center, text_only, image_right, three_columns 等）。
   - 修改正文内容要点。
3. **状态同步**：用户在表单中的修改会实时双向绑定到内存中的 JSON 状态文档中。

### 阶段 3：确认与物理渲染 (Fine-tuning & Export)
1. **智能降级兼容**：不仅支持标准的 JSON 协议，即使用户在普通的聊天中让 AI 生成了包含 `# ` 和 `- ` 的 Markdown 纯文本列表，底层解析引擎也能自动将其降级转换为结构化的 PPT JSON，依然能够无缝唤起共创排版器。
2. **一键生成**：用户在共创界面调整满意后，点击底部完整的 **[💾 确认并导出 PPT]** 按钮，系统将最终定型的 JSON 状态结构移交给底层的 `ppt_generator.py`，瞬间完成物理渲染并自动调用系统默认程序（如 Keynote 或 PowerPoint）打开生成的 `.pptx` 文件。

## 三、 系统架构与模块职责

为了支撑上述交互，系统在工程上划分为三个核心引擎：

### 1. 状态管理中心 (State Manager)
- **职责**：在一次会话（Session）的生命周期内，维护一个名为 `shadow_presentation_state` 的 JSON 对象。
- **机制**：无论是 AI 生成初版、AI 根据对话局部修改，还是用户手动表单修改，最终都收束为对这个 JSON 对象的 CRUD 操作。

### 2. AI 策划引擎 (Prompt & LLM Logic)
- **职责**：将模糊的自然语言转化为确定的 JSON 状态修改。
- **机制**：当前统一通过 `V5AgentWorker + agent_runtime` 执行，默认走 `vnext/Hermes`，也可按配置切到 `self_agent`。PPT 场景的提示词和上下文约束由 `ppt_editor` 上下文描述、渲染指令生成器与运行时路由共同控制。输出仍要求遵循内部 JSON / render command 协议。例如：
  ```json
  [
    {"type": "title", "layout": "center", "title": "...", "subtitle": "..."},
    {"type": "content", "layout": "three_columns", "title": "...", "items": [...]}
  ]
  ```

### 3. 物理渲染引擎 (PPT Generator)
- **职责**：将确定的 JSON 状态转化为高质量的视觉文件。
- **机制**：即重构后的 `ppt_generator.py`。内置“极简商务”、“科技蓝”等多套母版引擎。通过解析 JSON 中的 `layout` 字段，动态计算文本框坐标，分配图文混排（Image Right）、三栏对比（Three Columns）或数据表格等物理图层。

## 三点五、最新运行时补充（2026-06-11）

这部分描述当前代码里已经落地、且会直接影响 PPT 共创行为的真实机制。

### 1. `ppt_editor` 已接入运行时护栏

当前 `ppt_editor` 不再只是“普通 chat + prompt”的松耦合模式，而是由 runtime 中间件追加了额外行为约束：

- `SessionSetupMiddleware` 会识别 `context_source="ppt_editor"`
- 命中后默认关闭 web search
- 默认跳过通用 tools prompt 注入
- 默认进入 `answer-first` 直答模式
- 额外注入“不要再次 read_slide、直接返回 render_commands JSON、默认只改当前页”的系统约束

这意味着当前真实行为更接近：

- `PPT 场景专属受控编辑链路`

而不是：

- `普通多轮聊天场景里的一个提示词分支`

### 2. 当前 prompt 版本已进入快照化管理

`ppt_editor` 当前 system prompt 已在代码中显式版本化：

- 代码真源：`opencopilot/shared/prompt.py`
- 当前版本：`PPT_EDITOR_PROMPT_VERSION = "v7_compound_task"`
- 快照目录：`prompts/ppt_editor/`

当前可追溯的几个关键快照包括：

- `v4_baseline`
- `v5_fact_anchor`
- `v6_structure`
- `v7_compound_task`

这意味着后续 prompt 调整不应该只在聊天里口头讨论，而应基于：

- 版本快照
- 固定 benchmark
- before/after 报告

来做可回滚、可比较的迭代。

### 3. 动态示例层已补到“正反例 + 复合任务”

`render_prompt_generator.py` 当前不再只是最早期的图表/表格/流程图示例。

最新实现中已经补入：

- 忠实改写正例：`faithful_rewrite_good`
- 忠实改写反例：`faithful_rewrite_bad`
- 标题类与复合任务关键词识别增强

因此当前更准确的描述是：

- 仍然是轻量动态 few-shot 体系
- 但已经不再是“只有单个通用示例”的早期形态

### 4. 忠实改写已从“润色子问题”升级为专项评测能力

围绕“专业化且保事实”，当前已新增专项 benchmark 基础设施：

- 固定数据集：`tests/test_data/ppt_faithful_rewrite_cases.json`
- 评测模式：`OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`
- 主入口：`tests/e2e/test_ppt_cocreation_quality_benchmark.py`
- 规范文档：`docs/PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md`
- 迭代手册：`docs/PPT_FAITHFUL_REWRITE_PROMPT_ITERATION_PLAYBOOK.md`

这代表 PPT 共创当前已经进入：

- `有固定 case`
- `有固定评价口径`
- `有版本化 prompt`
- `有准入门槛`

的迭代阶段。

## 四、 核心数据结构协议 (JSON Schema)

这是前端 UI、大模型和排版引擎三者之间沟通的唯一“通用语言”：

```json
{
  "theme": "corporate_blue",  // 预留给未来的主题切换
  "slides": [
    {
      "id": "slide_001",
      "type": "title",
      "layout": "center",
      "title": "2026 智能体发展报告",
      "subtitle": "多模态与人机协同的未来"
    },
    {
      "id": "slide_002",
      "type": "content",
      "layout": "three_columns", // 决定了物理排版的样式
      "title": "核心技术突破",
      "visual_hint": "科技、芯片、未来感", // 用于后续触发 AI 配图或 SVG 检索
      "items": [
        {"level": 0, "text": "多模态感知"},
        {"level": 0, "text": "超长上下文"},
        {"level": 0, "text": "端侧本地化部署"}
      ]
    }
  ]
}
```

## 五、 演进路线图 (Roadmap)

- **Phase 1: 核心链路闭环 (已完成)**
  - 实现 JSON 协议的全面接管。
  - 在前端实现「PPT大纲预览卡片」以及对话式修改 JSON 状态的能力。
- **Phase 2: 内容转换能力增强 (已完成 ✅)**
  - 实现 `content_converter.py`：智能识别文本结构，推荐转换方式
  - 支持转换类型：表格、柱状图、折线图、饼图、流程图
  - 在 `preview_panel.py` 中实现表格和图表渲染
  - 测试验证：107/107 全部通过
- **Phase 2.5: AI 共创交互优化 (已完成 ✅)**
  - 修复多轮对话上下文丢失：稳定 session_id，同一对话框内共享会话历史
  - 快捷指令注入上下文：自动携带当前幻灯片标题/要点/版式信息
  - Undo/Redo 操作栈：50 级历史，Ctrl+Z/Y 快捷键 + ↩/↪ 按钮
  - 改动对比反馈：AI 修改后显示 `~~旧值~~ → **新值**` 的 before/after 对比
  - 增量数据发送：仅发送当前页 + 前后各 1 页摘要，大幅降低 token 消耗
  - 内容转换本地 ETL：chart/table/flowchart 数据自动校验补全默认值
- **Phase 3: 视觉资产增强 (Visual Asset)**
  - 解析 JSON 中的 `visual_hint`，在渲染时自动调用在线无版权图库 API，或通过本地模型生成配图填入版式。
- **Phase 4: 逆向解析 (Reverse Engineering)**
  - 允许用户不仅能生成 PPT，还能把现有的丑陋 PPT 拖进去，系统逆向提取内容为 JSON，然后应用新主题重新渲染，实现"一键美化"。

## 六、交互迭代方案

> 端到端交互设计（3 阶段流程 + IDE 式布局 + 条件入口路由）：
>
> **→ [`PPT_CoCreation_E2E_Design.md`](./PPT_CoCreation_E2E_Design.md)**
>
> 详细的交互迭代方案（10 项交互改进 + 6 项功能迭代 + 架构改进 + Sprint 路线图）：
>
> **→ [`PPT_CoCreation_Iteration_Plan.md`](./PPT_CoCreation_Iteration_Plan.md)**
>
> 忠实改写专项评测规范：
>
> **→ [`PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md`](./PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md)**
>
> Prompt 迭代执行手册：
>
> **→ [`PPT_FAITHFUL_REWRITE_PROMPT_ITERATION_PLAYBOOK.md`](./PPT_FAITHFUL_REWRITE_PROMPT_ITERATION_PLAYBOOK.md)**
>
> 交互稿：`canvases/ppt-cocreation-e2e-flow.canvas.tsx`（3 阶段端到端版）
