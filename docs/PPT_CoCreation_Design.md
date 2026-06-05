# OpenCopilot 伴生智能体：PPT 人机共创引擎设计方案

## 一、 核心定位与设计理念
将现有的“单向格式转换工具”升级为“**伴生式 AI 策划师与排版助理**”。
核心理念：**对话驱动状态更新 (Conversation-driven State Update)**。用户只需用自然语言发号施令，AI 在后台实时更新结构化数据，并在前端实时渲染大纲预览。只有在自然语言遇到瓶颈时，才提供轻量级的手动干预作为兜底。

## 二、 交互心流 (User Workflow)

整个交互过程分为三个递进阶段：

### 阶段 1：意图捕获与 AI 初版生成 (Drafting)
1. **输入**：用户拖拽文档到 Smart Copilot 窗口，或直接发送指令（如：“把这份产品介绍做成 PPT”）。
2. **AI 处理**：大模型扮演“策划师”，对长文本进行降维提炼，自动规划页数，并为每一页分配合适的版式（图文、三栏、纯文本）。
3. **入口弹出**：当 AI 完成输出后，系统利用底层的正则与解析引擎 (`extract_json_from_text`) 自动扫描内容。一旦识别出合法的 JSON 结构或标准的 Markdown 大纲，界面右下角会自动弹出 **[💾 导出为 PPT]** 按钮，提供人机共创交互的入口。

### 阶段 2：可视化人机共创排版 (Interactive Editing)
这是人机共创的核心。用户点击导出按钮后，不会直接生成死板的 PPT，而是进入一个独立的 **PPT 人机共创编辑器 (`PPTPreviewDialog`)**。
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
- **机制**：在 `asu_custom_agent.py` 中预置 `ppt_planner` 角色。要求其输出必须严格遵循内部 JSON 协议。例如：
  ```json
  [
    {"type": "title", "layout": "center", "title": "...", "subtitle": "..."},
    {"type": "content", "layout": "three_columns", "title": "...", "items": [...]}
  ]
  ```

### 3. 物理渲染引擎 (PPT Generator)
- **职责**：将确定的 JSON 状态转化为高质量的视觉文件。
- **机制**：即重构后的 `ppt_generator.py`。内置“极简商务”、“科技蓝”等多套母版引擎。通过解析 JSON 中的 `layout` 字段，动态计算文本框坐标，分配图文混排（Image Right）、三栏对比（Three Columns）或数据表格等物理图层。

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

> 详细的下一代交互迭代方案（10 项交互改进 + 6 项功能迭代 + 架构改进 + Sprint 路线图）已独立成文：
>
> **→ [`PPT_CoCreation_Iteration_Plan.md`](./PPT_CoCreation_Iteration_Plan.md)**
>
> 交互稿 (Canvas Wireframe) 也已配套输出，包含 Main Layout / AI Detail / Features 三个视图。
