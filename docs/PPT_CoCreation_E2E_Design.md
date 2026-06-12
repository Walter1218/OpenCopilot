# PPT 共创工作台 — 端到端交互设计方案

> 版本：v2.4 | 2026-06-12 | 交互稿：`canvases/ppt-cocreation-e2e-flow.canvas.tsx` + `canvases/opencopilot-ui-interaction-20260609.canvas.tsx`
>
> 本文档替代旧版"三阶段"描述，以 3 阶段精简流程为基准。旧版 `PPT_CoCreation_Design.md` 中的架构、数据结构、演进路线图仍有效，本文聚焦**交互流程与布局设计**。

---

## 一、设计目标

从用户输入原文到最终 PPT 定稿，构建**连续、无跳转**的 3 阶段交互体验：

```
输入原文 ──→ 策略发现 ──→ 编辑打磨
 (Stage 1)   (Stage 2)    (Stage 3)
```

**核心原则**：
- **零配置启动**：无需选模板、配参数，粘贴即开始
- **渐进式深入**：策略发现可跳过，AI 对话是可选增强
- **IDE 式沉浸**：Stage 3 参考 IDE 主编辑+侧栏模式，原文大面积可见

### 1.1 入口路由（条件跳转）

Stage 1 是 Tab 3 的**空状态页面**，仅在无文本上下文时显示。已有文本时跳过 Stage 1 直接进入 Stage 2。

| 入口场景 | 有文本？ | 流程 |
|----------|----------|------|
| 打开 Tab 3（无上下文） | 无 | Stage 1 → 2 → 3 |
| Work Tab 选中文本 → 跳转 Studio | 有 | **直接进入 Stage 2** |
| 文件拖入 Tab 3（.txt/.md） | 有（解析后） | **直接进入 Stage 2** |
| 剪贴板自动补全（<50字时） | 有 | **直接进入 Stage 2** |
| 从 Chat 传递文本 | 有 | **直接进入 Stage 2** |

**判断逻辑**：Tab 3 打开时检查 `current_text`（主界面选中文本）→ 剪贴板 → 拖入文件，任一有内容则自动填入并跳转到 Stage 2。

### 1.2 全局交互拓扑

Smart Copilot 系统包含 3 种全局触发姿态，V5Plus PPT 共创作为 Studio Tab 的延伸入口整合其中：

```
┌─────────────────────────────────────────────────────────────────────┐
│  全局触发姿态                                                        │
├──────────────────┬──────────────────────────────────────────────────┤
│ 双击右键          │ → Smart Copilot (680×520)                       │
│                  │    ├─ Tab 1 Work：快捷操作（Explain/Fix/Polish） │
│                  │    ├─ Tab 2 Chat：连续对话                       │
│                  │    └─ Tab 3 Studio：PPT 共创入口                 │
│                  │         ├─ [打开 Studio ▶] → 旧 4-Panel 工作台  │
│                  │         └─ [V5Plus 共创 ▶] → V5Plus E2E 流程   │
│                  │              ├─ 无文本 → Stage 0 (输入原文)      │
│                  │              └─ 有文本 → Stage 1 (策略发现)      │
├──────────────────┼──────────────────────────────────────────────────┤
│ 三击右键          │ → Agent Workspace (1000×700)                    │
│                  │    深度工作台：任务定义 + 文件管理 + 知识图谱     │
├──────────────────┼──────────────────────────────────────────────────┤
│ System Tray 点击  │ → Smart Copilot（同双击右键）                   │
│                  │    菜单可选：快捷卡片 / 工作台 / 隐藏全部        │
└──────────────────┴──────────────────────────────────────────────────┘
```

**NavigationManager 10 条核心链路**（`gui/v5/navigation.py`）：

| 链路 | 方向 | 触发 | 方法 |
|------|------|------|------|
| A | 内部 Tab 切换 | 用户点击 Tab | SmartCopilot 自行处理 |
| B | SC → Studio 窗口 | Studio Tab 按钮 | `open_studio(text, slides)` |
| **B+** | **SC → V5Plus CoCreation** | **Studio Tab 按钮** | **`open_cocreation(text)`** |
| C | SC → Settings | 标题栏 ⚙️ | `open_settings(section)` |
| D | Workspace → Settings | Workspace 内 | `open_settings(section)` |
| E | System Tray → SC | Tray 点击 | `show_smart_copilot(x, y, text)` |
| F | Work → Chat | 上下文跳转 | `jump_work_to_chat(text, source)` |
| G | Studio → Chat | 导出回传 | `jump_studio_to_chat(path)` |
| **H** | **CoCreation Stage 0→1→2** | **条件路由** | **`open_with_text(text)`** |
| **I** | **CoCreation → Chat** | **导出回传（待实现）** | — |

**窗口互斥规则**：V5Plus CoCreation 和旧 Studio 窗口互斥 — 打开 CoCreation 时自动关闭旧 Studio，反之亦然。

---

## 二、Stage 1：输入原文（空状态）

> Stage 1 仅在 Tab 3 无文本上下文时显示，本质是**空状态引导页**。有文本时直接跳过进入 Stage 2。

### 2.1 页面功能

- 8 行 TextArea，引导用户粘贴或输入原文
- 支持文件拖放（.txt / .md）→ 读取内容后自动跳转 Stage 2
- 实时字数统计 + 段落检测（纯前端，<50ms）
- 唯一 CTA 按钮"分析文档结构"→ 进入 Stage 2

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
│                              [分析文档结构 →] │
└─────────────────────────────────────────────┘
```

### 2.2 设计要点

- 实时字数统计 + 段落检测（纯前端，<50ms）
- 8 行 TextArea，足够预览大部分文档
- 唯一 CTA 按钮"分析文档结构"，明确引导下一步
- 文件拖放区域视觉反馈（拖入时高亮边框）

---

## 三、Stage 2：策略发现

### 3.1 修辞分析

Agent 对输入文本进行**纯正则驱动**的结构分析（不调用 LLM，<500ms）：

| 分析项 | 实现方式 |
|--------|----------|
| 文档类型检测 | 关键词 + 结构特征正则匹配 |
| 段落切分 + 类型标注 | 换行符分割 + 类型分类器 |
| 数据密度统计 | 数字/百分比/比较词计数 |
| 策略匹配推荐 | 基于文档类型的规则映射 |

### 3.2 策略选择

提供 3 种叙事策略，Agent 推荐一种（默认选中），用户可自由切换：

| 策略 | 结构模板 | 适用场景 |
|------|----------|----------|
| ▲ 金字塔式（结论先行） | 核心结论 → 支撑论据 → 数据证据 → 下一步 | 汇报、总结 |
| ◆ 叙事式（问题驱动） | 现状痛点 → 解决思路 → 技术实现 → 预期收益 | 方案介绍 |
| ◇ 对比式（方案论证） | 背景需求 → 方案对比 → 推荐详解 → 实施风险 | 决策论证 |

### 3.3 可选配置

- **目标受众**：自由文本（如"技术总监、产品经理"）
- **演讲时长**：5/10/15/30 分钟下拉

### 3.4 交互

```
┌─────────────────────────────────────────────┐
│  🚦  PPT 共创 - 战略发现                     │
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

### 3.5 数据流

选定策略后，`strategy_config`（结构模板 + 受众 + 时长）注入 Pipeline 的 `_extract_topics()` LLM prompt，指导 Agent 按选定结构组织幻灯片内容。

### 3.6 设计要点

- "跳过，直接生成"保留快速路径，策略发现不是强制步骤
- 策略推荐基于正则分析结果，不调用 LLM，保证 <500ms 响应
- 段落类型热力图直观展示文档结构，帮助用户理解推荐理由

---

## 四、Stage 3：编辑打磨

这是交互的核心，采用 **IDE 式双面板布局**。

### 4.1 布局规格

```
┌─────────────────────────────────────┬──────────────────────────┐
│  PPT 编辑区 (60%)                    │  原文面板 (40%)           │
│  ┌───────────────────────────────┐  │  ┌────────────────────┐  │
│  │ Thumb1 Thumb2 Thumb3 ...      │  │  │ 📄 原文  ████ 72%  │  │
│  ├───────────────────────────────┤  │  ├────────────────────┤  │
│  │                               │  │  │ [重提炼] 更关注...  │  │
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
│                                    [💾 导出 PPT]               │
└───────────────────────────────────────────────────────────────┘
```

| 区域 | 宽度占比 | 内容 |
|------|----------|------|
| 中间 PPT 编辑区 | 60% | 缩略图导航 + 幻灯片预览 + 版式标签栏 |
| 右侧原文面板 | 40% | 原文 + 映射标签 + 重新提炼 + AI 输入 |

### 4.2 中间 PPT 编辑区

#### 缩略图导航（顶部）
- 64×36px 迷你缩略图，水平滚动
- 选中态：蓝色 2px 边框 + 高亮背景
- 质量徽章：橙色圆点角标（⚠️ 内容过密等）
- 点击切换当前编辑页

#### 幻灯片预览（主区域）
- 16:9 白色画布，居中显示
- **Click-to-Edit**：标题/要点区域显示蓝色虚线边框，双击进入 InlineEditor 内联编辑
- **自由拖拽定位**：按住任意文本元素可自由拖拽到幻灯片画布任意位置（custom_x/custom_y 坐标），拖拽过程中实时显示 ghost 半透明反馈，释放后元素停留在新位置
- **表格单元格编辑**：双击表格单元格可独立编辑该单元格内容
- **右键菜单**：编辑内容、删除、重置位置（已自定义坐标的元素可一键回到默认布局）
- **跨面板拖拽**：原文面板的段落可拖拽到 PPT 预览区添加为新内容
- 底部显示当前页码（如 `3 / 6`）

#### AI Diff Overlay（浮层）
- 当 AI 提出修改建议时，以半透明浮层叠加在预览区右上角
- 展示 `-旧值` / `+新值` 的 diff 对比
- `[✓ 接受]` / `[✗ 拒绝]` 两个操作按钮
- 接受后自动更新预览，拒绝后保持原状

#### 版式标签栏（底部）
- 紧凑 Tag 组件：`center` / `text` / `3-col` / `chart` / `timeline`
- 当前版式高亮，点击切换

### 4.3 右侧原文面板

#### 原文头部
- 显示"📄 原文"+ 提炼覆盖率进度条（如 72%）

#### 重新提炼栏
- 指令输入框 + `↻ 重新提炼` 按钮
- 用户可输入引导指令（如"更关注数据部分"），触发 AI 重新分析原文并更新映射关系

#### 映射可视化
每段原文右侧显示映射标签：

| 标签类型 | 样式 | 交互 |
|----------|------|------|
| 已映射 `[S2]` | 彩色圆角标签（颜色对应 slide） | 点击跳转到对应 slide |
| 未映射 `[+]` | 虚线灰色标签 | 点击选择目标 slide 分配 |

**双向联动**：
- 选中某个 slide → 对应映射段落高亮（浅蓝背景 + 蓝色边框）
- 点击映射标签 → 跳转到对应 slide

#### AI 对话输入（底部）
- 一行输入框 + 发送按钮
- 位于原文面板底部，指令自然关联右侧原文上下文
- 支持语义化指令：如"把第2段移到第4页"、"标题改短"
- AI 回复的 diff 结果浮在**中间预览区**上确认

### 4.4 设计决策记录

| 决策 | 原因 |
|------|------|
| 合并原 Stage 3/4 为一个阶段 | 独立 outline 面板、独立 chat 面板与预览编辑功能重叠 |
| 砍掉独立 Outline 面板 | 标题/要点直接在预览上 click-to-edit，版式 tag 移到预览下方 |
| AI 输入放在右下而非底部 | 与原文上下文空间邻近，操作流"右输入→中确认" |
| 砍掉 Contextual Shortcuts 栏 | 用户可直接打字，预设按钮与 AI 输入功能重叠 |
| 砍掉 Theme Picker | 属于设置项，不属于核心编辑流程 |
| 60/40 而非 70/30 分割 | 原文常为长文本，40% 宽度保障可读性 |

---

## 五、数据流向总览

```
原文输入 → 修辞分析 → 策略选择 → strategy_config → Pipeline 生成 → 映射可视化 + 编辑 → AI 内联 Diff → 导出 PPT
```

各阶段产出：

| 阶段 | 产出 | 消费方 |
|------|------|--------|
| Stage 1 | 原始文本 + 段落数 | Stage 2 修辞分析 |
| Stage 2 | strategy_config（结构模板 + 受众 + 时长） | Pipeline prompt 注入 |
| Pipeline | slides JSON（结构化幻灯片数据） | Stage 3 编辑区 |
| Stage 3 | 编辑后的 slides JSON + 映射关系 | PPT Generator 物理渲染 |

---

## 六、架构映射

| 设计方案中的模块 | 对应代码文件 | 操作 |
|-----------------|-------------|------|
| Stage 1 空状态页 | `studio_tab.py` | 改（QLineEdit → TextArea + 入口路由） |
| Stage 2 修辞分析 | `context_analyzer.py` | 改（+修辞分析 +策略推荐） |
| Stage 2 策略面板 | `strategy_panel.py` | 新（StrategyDiscoveryPanel） |
| Stage 3 原文面板 | `source_panel.py` | 改（+映射标签 +重新提炼） |
| Stage 3 缩略图 | `outline_panel.py` | 改（替换为可视化缩略图条） |
| Stage 3 预览编辑 | `slide_renderer.py` | 改（+Click-to-Edit） |
| Stage 3 AI Diff | `instruction_engine.py` | 新（指令解析 + Diff Preview） |
| 端到端流程编排 | `studio_tab.py` | 改（3 阶段流程控制 + 条件跳转） |
| Pipeline 策略注入 | `pipeline.py` | 改（接收 strategy_config） |
| 全链路测试 | `test_e2e.py` | 新 |

---

## 七、关键交互模式

### 7.1 Click-to-Edit

```
用户双击标题区域
  → SlideRenderer 发出 title_double_clicked 信号
  → 预览区在标题位置显示 inline QTextEdit
  → 用户编辑完毕按 Enter
  → 新值写入 slides JSON → 重新渲染预览
```

### 7.2 AI 指令 → Diff → 确认

```
用户在右下输入框输入"标题改短"
  → instruction_engine 解析指令 + 当前 slide 上下文
  → 调用 LLM 生成修改后的 slide JSON
  → diff_engine 对比 old/new JSON
  → 在预览区叠加 Diff Overlay（-旧/+新）
  → 用户点击 [接受] → 应用修改 → Overlay 消失
  → 用户点击 [拒绝] → 保持原状 → Overlay 消失
```

### 7.3 映射标签双向联动

```
用户点击缩略图 S3
  → selSlide = 2
  → 原文面板中 [S3] 段落高亮（背景 + 边框）
  → 其他段落恢复默认样式

用户点击原文 [S3] 标签
  → selSlide = 2
  → 缩略图 S3 变为选中态
  → 预览区切换到第 3 页
```

### 7.4 重新提炼

```
用户输入"更关注数据部分" + 点击 [↻ 重新提炼]
  → instruction_engine 携带原文 + 用户指令调用 LLM
  → 返回新的段落映射关系
  → 更新原文面板的映射标签
  → 可能新增/删除 slide 对应关系
```

---

## 八、埋点与可观测性设计

基于现有 `PipelineObservability`（SQLite 持久化 + stderr 实时输出）和 `V5Telemetry`（UI 事件薄封装）体系，为 3 阶段 E2E 流程设计全链路埋点方案。

### 8.1 技术栈复用

| 层级 | 使用组件 | 获取方式 |
|------|----------|----------|
| UI 事件层 | `V5Telemetry` | `V5Telemetry.get()` → `emit(event, session_id=..., **kwargs)` |
| 管线层 | `PipelineObservability` | `PipelineObservability.get_instance()` → `log()/gui_log()/timer()` |
| 模块日志 | `logging` | `logging.getLogger(__name__)` |

**Correlation ID 传播**：`app_run_id`（进程级） → `session_id`（会话级） → `trace_id`（请求级），与现有体系一致。

### 8.2 Stage 1 埋点（输入原文 / 空状态页）

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE1_OPEN` | Stage 1 页面展示 | UI | `source`（manual/clipboard/drag/chat/work） |
| `V5_STAB_STAGE1_INPUT` | 用户输入/粘贴文本 | UI | `text_len`, `paragraph_count` |
| `V5_STAB_STAGE1_DRAG` | 拖放文件到输入区 | UI | `file_type`, `file_size` |
| `V5_STAB_STAGE1_SUBMIT` | 点击"分析文档结构" | UI | `text_len`, `paragraph_count` |
| `V5_STAB_STAGE1_SKIP` | 有文本时自动跳过 | UI | `source`, `text_len` |

**模块日志**（`studio_tab.py`）：
```python
logger.info("Stage 1: text loaded, len=%d, source=%s", text_len, source)
```

### 8.3 Stage 2 埋点（策略发现）

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `PPT_RHETORIC_ANALYSIS_START` | 修辞分析开始 | 管线 | `text_len` |
| `PPT_RHETORIC_ANALYSIS_DONE` | 修辞分析完成 | 管线 | `elapsed_ms`, `doc_type`, `paragraph_count` |
| `PPT_STRATEGY_RECOMMENDED` | Agent 推荐策略 | 管线 | `recommended_strategy`, `reason` |
| `V5_STAB_STAGE2_STRATEGY_SELECT` | 用户选择策略 | UI | `strategy`（pyramid/narrative/comparison）, `is_recommended` |
| `V5_STAB_STAGE2_SUBMIT` | 点击"开始生成" | UI | `strategy`, `audience`, `duration` |
| `V5_STAB_STAGE2_SKIP` | 点击"跳过，直接生成" | UI | — |

**性能要求**：修辞分析 `PPT_RHETORIC_ANALYSIS_DONE.elapsed_ms < 500`。

```python
# pipeline.py
obs.log("ContextAnalyzer", "Rhetoric analysis complete", level="INFO",
        session_id=session_id, event="PPT_RHETORIC_ANALYSIS_DONE",
        extra_data={"doc_type": doc_type, "elapsed_ms": elapsed, "paragraph_count": len(paragraphs)})

# studio_tab.py
telemetry.emit("V5_STAB_STAGE2_STRATEGY_SELECT",
               session_id=sid, strategy="pyramid", is_recommended=True)
```

### 8.4 Stage 3 埋点（编辑打磨）

**导航与布局交互**：

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE3_SLIDE_SELECT` | 切换幻灯片 | UI | `slide_index`, `slide_title`, `layout` |
| `V5_STAB_STAGE3_LAYOUT_CHANGE` | 版式切换 | UI | `old_layout`, `new_layout`, `slide_index` |
| `V5_STAB_STAGE3_EXPORT` | 点击导出 PPT | UI | `slide_count`, `total_edits` |

**Click-to-Edit**：

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE3_EDIT_TITLE` | 双击标题进入编辑 | UI | `slide_index`, `old_title_len` |
| `V5_STAB_STAGE3_EDIT_COMMIT` | Enter 确认编辑 | UI | `slide_index`, `field`（title/body）, `old_len`, `new_len` |

**映射联动**：

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE3_MAPPING_CLICK` | 点击映射标签 | UI | `tag`（S2~S6）, `direction`（tag→slide / slide→paragraph） |
| `V5_STAB_STAGE3_MAPPING_ADD` | [+] 补入未映射段落 | UI | `paragraph_index`, `target_slide` |
| `PPT_REEXTRACT_START` | 重新提炼开始 | 管线 | `instruction`, `text_len` |
| `PPT_REEXTRACT_DONE` | 重新提炼完成 | 管线 | `elapsed_ms`, `new_mapping_count` |

**AI 对话与 Diff**：

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE3_AI_SEND` | 发送 AI 指令 | UI | `instruction_len`, `slide_index`, `slide_layout` |
| `PPT_STAGE3_AI_START` | AI 处理开始 | 管线 | `instruction`, `slide_index` |
| `PPT_STAGE3_AI_DONE` | AI 返回结果 | 管线 | `elapsed_ms`, `response_len`, `has_diff` |
| `V5_STAB_STAGE3_DIFF_SHOW` | Diff Overlay 显示 | UI | `slide_index`, `diff_fields` |
| `V5_STAB_STAGE3_DIFF_ACCEPT` | 接受 AI 修改 | UI | `slide_index`, `diff_fields` |
| `V5_STAB_STAGE3_DIFF_REJECT` | 拒绝 AI 修改 | UI | `slide_index`, `diff_fields` |
| `PPT_STAGE3_AI_ERROR` | AI 处理失败 | 管线 | `error_msg`, `slide_index` |

**Undo/Redo**：

| 事件名 | 触发时机 | 层级 | 关键字段 |
|--------|----------|------|----------|
| `V5_STAB_STAGE3_UNDO` | 撤销操作 | UI | `source`（manual/ai）, `stack_depth` |
| `V5_STAB_STAGE3_REDO` | 重做操作 | UI | `source`, `stack_depth` |

### 8.5 全链路 session_id 传播

```
用户打开 Stage 1
  └─ session_id = telemetry.new_session_id()   # 如 "a1b2c3d4e5f67890"
     │
     ├─ Stage 1 输入完成
     │   └─ V5_STAB_STAGE1_SUBMIT(session_id=...)
     │
     ├─ Stage 2 修辞分析
     │   └─ PPT_RHETORIC_ANALYSIS_START/DONE(session_id=...)
     │
     ├─ Stage 2 策略选择 + Pipeline 生成
     │   ├─ PPT_STRATEGY_RECOMMENDED(session_id=...)
     │   └─ 管线内部: ppt_topic_{uuid} / ppt_map_{uuid} 等子 session
     │       └─ parent_session_id = 顶层 session_id（kwargs 传播）
     │
     └─ Stage 3 编辑打磨
         ├─ V5_STAB_STAGE3_*(session_id=...)
         ├─ PPT_STAGE3_AI_*(session_id=...)
         └─ PPT_REEXTRACT_*(session_id=...)
```

一次完整 E2E 流程使用**同一个 session_id**，管线内部子调用通过 `parent_session_id` 关联，支持在 SQLite 中按 session_id 查询完整事件序列。

### 8.6 错误埋点规范

| 场景 | 事件名 | level | 额外字段 |
|------|--------|-------|----------|
| 修辞分析异常 | `PPT_RHETORIC_ANALYSIS_ERROR` | ERROR | `error_msg`, `stack_trace` |
| 策略推荐失败（降级为默认） | `PPT_STRATEGY_FALLBACK` | WARNING | `reason` |
| Pipeline 生成失败 | `PPT_PIPELINE_ERROR` | ERROR | `stage`, `error_msg` |
| 重新提炼 LLM 超时 | `PPT_REEXTRACT_TIMEOUT` | ERROR | `elapsed_ms`, `instruction` |
| AI 指令返回空结果 | `PPT_STAGE3_AI_EMPTY` | WARNING | `instruction`, `slide_index` |
| 映射数据不一致 | `PPT_MAPPING_INCONSISTENCY` | WARNING | `paragraph_count`, `mapping_count` |
| 导出失败 | `V5_STAB_STAGE3_EXPORT_ERROR` | ERROR | `error_msg` |

所有错误事件同时通过 `obs.error()` 写入 SQLite 和 `logger.error()` 写入标准日志，确保两套系统都能查到。

### 8.7 性能指标

| 指标名 | 类型 | 采集点 |
|--------|------|--------|
| `ppt.e2e.total_duration` | histogram | Stage 1 开始 → 导出完成 |
| `ppt.stage2.rhetoric_ms` | histogram | 修辞分析耗时 |
| `ppt.stage2.pipeline_ms` | histogram | Pipeline 生成耗时 |
| `ppt.stage3.edit_count` | counter | 单次会话手动编辑次数 |
| `ppt.stage3.ai_request_count` | counter | 单次会话 AI 指令次数 |
| `ppt.stage3.diff_accept_rate` | gauge | accept / (accept + reject) |
| `ppt.stage3.mapping_coverage` | gauge | 已映射段落 / 总段落 |

```python
# 采集示例
obs.metric("ppt.stage2.rhetoric_ms", elapsed, tags={"doc_type": doc_type})
obs.metric("ppt.stage3.diff_accept_rate", accept_count / total_count, tags={})
```

---

## 九、验证要求

- [ ] 3 阶段流程无中断跳转
- [ ] 条件路由：有文本时跳过 Stage 1，直接进入 Stage 2
- [ ] Stage 2 策略推荐 <500ms 响应（纯正则，无 LLM）
- [ ] Stage 3 Click-to-Edit 双击到出现编辑器 <100ms
- [ ] AI Diff Overlay 接受/拒绝后预览正确更新
- [ ] 映射标签双向联动无延迟
- [ ] 重新提炼后映射关系正确刷新
- [ ] 6+ 段映射标签在 40% 宽度面板内可读性良好
- [ ] Undo/Redo 覆盖手动编辑 + AI 编辑
- [ ] Pipeline 追踪日志覆盖全链路
- [ ] 所有 E2E 事件使用同一 session_id，可在 SQLite 中按 session_id 串联
- [ ] 错误事件同时写入 PipelineObservability + standard logging
- [ ] 修辞分析 elapsed_ms < 500ms 指标可查
- [ ] diff_accept_rate 指标正确计算

---

## 附录 A：Smart Copilot 交互设计参考

> Smart Copilot 是 V5Plus 共创的入口载体。本节记录 Smart Copilot 现有交互设计，作为 V5Plus 共创的交互基准参考。

### A.1 主窗口架构

**窗口规格**：680×520 frameless 浮窗，`WindowStaysOnTopHint`，带阴影 + 圆角（12px），支持拖拽移动 + 边缘缩放。

```
┌──────────────────────────────────────────┐
│  ✨ Smart Copilot  ● ⚙️  ✕              │  ← 标题栏（可拖拽）
├──────────────────────────────────────────┤
│  ⚡ Work │ 💬 Chat │ 🎨 Studio           │  ← 3-Tab QTabWidget
│                                          │
│  ┌────────────────────────────────────┐  │
│  │                                    │  │
│  │        (当前 Tab 内容区)            │  │
│  │                                    │  │
│  │                                    │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

**Tab 自动路由**：
- 有选中文本 → 默认切到 Work Tab
- 无选中文本 → 默认切到 Chat Tab
- Tab 切换埋点：`V5_SC_TAB_SWITCH(to_index, tab_name)`

**拖放同步**：文件/文本拖入 Smart Copilot 时，**同步注入三个 Tab**（Work/Chat/Studio），埋点 `V5_SC_TEXT_SHARED` / `V5_SC_FILE_SHARED`。

### A.2 Tab 1 Work：上下文感知快捷操作

**布局从上到下**：

```
┌─ Context Header Bar ─────────────────────────────────────────┐
│  ● Selection │ 236 chars │ [VS] VS Code          [↻] [✕]    │
├─ Selection Preview ──────────────────────────────────────────┤
│  │ selected text                                             │
│  │ async def process_selection(text: str, source: str):      │
│  │     # Analyze selected code and return structured result   │
│  │     context = analyze_context(text)                       │
│  │  ... 236 chars total | lines 42-58                        │
├─ Context Strip (5 sources) ──────────────────────────────────┤
│  [S Selection ●] [D Doc] [B Browser] [C Clipboard] [F File]  │
├─ Primary Actions (卡片式) ───────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ 📖 Explain   │ │ 🔧 Fix       │ │ ✨ Polish     │          │
│  │ What does... │ │ Find & fix   │ │ Improve...   │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
├─ Secondary Actions ──────────────────────────────────────────┤
│  [🌐 Translate] [🔍 Code Review] [📝 Summarize] [⋯ More]    │
├─ Result Area (streaming) ────────────────────────────────────┤
│  📖 Explain Result                     ● Streaming...        │
│  Function: process_selection                                 │
│  ┌─ Key Operations ──────────────────────────────────┐       │
│  │ • Parse selection boundaries...                    │       │
│  │ • Call analyze_context()...                        │       │
│  └────────────────────────────────────────────────────┘       │
│  Confidence: ████████████████░░░ 87%                          │
├─ Action Bar ─────────────────────────────────────────────────┤
│  [Ctrl+Shift+E to explain]       [📋Copy] [📤Export] [✓Apply] │
└──────────────────────────────────────────────────────────────┘
```

**Context Header Bar**：顶部状态栏，发光圆点指示在线状态，竖线分隔来源类型（Selection）、字数（236 chars）、宿主应用 icon（`[VS] VS Code`），右侧刷新/关闭按钮。

**Selection Preview**：选中内容以等宽字体 + 语法高亮预览（关键字紫色、注释绿色、函数名黄色），左侧蓝色竖线标识，右上角 `selected text` 标签，底部显示字符总数和行号范围。

**Context Strip**（数据源切换，`gui/v5/bridge.py` 桥接层）：5 个胶囊按钮，active 态带 icon 字母 + 发光圆点。

| 数据源 | ID | 说明 |
|--------|----|------|
| 🎯 Selection | `selection` | 系统选区（`SystemProbeClient.get_selection()`） |
| 📄 Doc | `active_doc` | 当前活动文档 |
| 🌐 Browser | `browser` | 浏览器内容 |
| 📋 Clipboard | `clipboard` | 剪贴板文本 |
| 📁 File | `file` | 文件内容 |

**Primary Action Cards**（三列卡片式按钮，走 `V5AgentWorker` → Agent Pipeline）：

| 卡片 | Icon | 色系 | 描述 |
|------|------|------|------|
| Explain | 📖 | 蓝 `#4da6ff` | What does this do? |
| Fix | 🔧 | 绿 `#28a745` | Find & fix issues |
| Polish | ✨ | 黄 `#ffc107` | Improve quality |

**Secondary Actions**（紧凑行，灰色描边，低频操作）：Translate / Code Review / Summarize / More

**Streaming Result Area**：结构化结果面板——header 显示 action 类型 + streaming 状态灯（绿色脉冲），body 包含函数名、说明文本、Key Operations 列表（灰底卡片），底部 confidence bar 可视化 AI 置信度（如 87%）。

**Action Bar**（非 AI 操作，通过 Bridge 执行）：
- 左侧：快捷键提示（如 `Ctrl+Shift+E to explain`）
- 📋 Copy → `bridge.do_clipboard(text)` → 复制到系统剪贴板
- 📤 Export → `nav.open_studio(text=text)` → 发送到 Studio 生成 PPT
- ✓ Apply → `bridge.do_apply_to_ide(text)` → 应用到 IDE（绿色填充突出）

### A.3 Tab 2 Chat：连续对话

**布局从上到下**：

```
┌──────────────────────────────────────────┐
│  Context ▸  0 sources    [清空]           │  ← Context Panel (可折叠)
│  ┌─ 折叠内容 ──────────────────────────┐  │
│  │ 暂无上下文来源                        │  │
│  └──────────────────────────────────────┘  │
├──────────────────────────────────────────┤
│                                          │
│  你: 请帮我解释下这段代码                  │  ← Conversation (只读)
│  AI: 这段代码实现了...                     │
│  系统: 已将上下文带入...                   │
│                                          │
├──────────────────────────────────────────┤
│ [默认会话 ▼] [输入消息...] [发送] [+]     │  ← 输入区
└──────────────────────────────────────────┘
```

**关键交互**：
- **Context Panel**：可折叠，显示已注入的上下文来源；从 Work Tab 跳转时自动注入
- **会话管理**：QComboBox 切换历史会话，`[+]` 按钮新建会话
- **AI 流式回复**：`V5AgentWorker` 的 `text_updated` 信号实时更新最后一条 AI 消息
- **停止功能**：发送按钮在 AI 处理时变为"停止"，点击取消 Worker

**跨 Tab 跳转**：
- 链路 F（Work → Chat）：`nav.jump_work_to_chat(text, source)` → `chat_tab.inject_context(text, source)` → 自动切到 Chat Tab + focus 输入框
- 链路 G（Studio → Chat）：`nav.jump_studio_to_chat(path)` → 注入导出文件路径

### A.4 Tab 3 Studio：PPT 共创入口

**布局**：Launcher 卡片 + 快速输入区 + 快速创建按钮 + 状态文案

```
┌──────────────────────────────────────────┐
│  ┌─ Launcher Card ─────────────────────┐ │
│  │ 🎨 Studio                           │ │
│  │ AI 驱动的 PPT 共创工作台              │ │
│  │ • 智能大纲生成 • 3 阶段 E2E 流程     │ │
│  │ • Click-to-Edit • AI 差异预览       │ │
│  │                                     │ │
│  │ [打开 Studio ▶]                     │ │  ← 旧 4-Panel 工作台
│  │ [V5Plus 共创 ▶] (紫色)              │ │  ← 3 阶段 E2E 流程
│  └─────────────────────────────────────┘ │
│                                          │
│  [粘贴文本、输入主题...]                  │  ← 快速输入区 (QTextEdit, max 80px)
│                              [快速创建]   │
│  💡 请先导入文本，或点击按钮直接粘贴内容    │  ← 状态文案
└──────────────────────────────────────────┘
```

**入口路由**（两个按钮 + 快速创建）：

| 操作 | 目标 | 代码路径 |
|------|------|----------|
| [打开 Studio ▶] | 旧 4-Panel 工作台 | `nav.open_studio()` |
| [V5Plus 共创 ▶] | V5Plus CoCreation 窗口 | `nav.open_cocreation(text)` |
| [快速创建] | AI 生成 PPT → 旧 Studio | `V5AgentWorker` → `nav.open_studio(text, slides)` |

**状态文案**（动态更新，Tab 切换时调用 `update_status`）：

| 场景 | 文案 |
|------|------|
| Studio 已打开 | ✅ 共创工作台已打开，切换回去即可继续编辑 |
| 有历史编辑 | 上次编辑：N 页幻灯片 — 点击按钮继续编辑 |
| 有文本未打开 | 📄 已导入文本，点击按钮即可打开共创工作台 |
| 空状态 | 💡 请先导入文本，或点击按钮直接粘贴内容 |

### A.5 跨 Tab 数据流与联动

```
                      拖放文本/文件
                          │
                          ▼
              ┌─────── Smart Copilot ───────┐
              │   同步注入到三个 Tab          │
              │                             │
    ┌─────────┼─────────┬───────────────┐   │
    ▼         ▼         ▼               │   │
  Work      Chat     Studio             │   │
  Tab        Tab      Tab               │   │
    │         │         │               │   │
    │  链路F  │         │  链路B/B+     │   │
    │────────→│         │──────────────→ │   │
    │  跳转   │         │ 打开工作台/    │   │
    │  带上下文│         │ V5Plus共创    │   │
    │         │         │               │   │
    │ Action  │         │ Export PPT    │   │
    │ Bar 导出│─────────→│ (nav.open_    │   │
    │         │         │  studio)      │   │
    └─────────┴─────────┴───────────────┘   │
              └─────────────────────────────┘
```

**核心联动事件**（埋点）：

| 事件 | 触发场景 | 关键数据 |
|------|----------|----------|
| `V5_SC_SET_TEXT` | 选中文本注入 Smart Copilot | `text_len`, `has_text` |
| `V5_SC_TAB_SWITCH` | Tab 切换 | `to_index`, `tab_name` |
| `V5_SC_DROP_TEXT` | 文本拖放 | `text_len`, `source_tab` |
| `V5_SC_TEXT_SHARED` | 拖放文本同步三 Tab | `text_len`, `target_tabs` |
| `V5_SC_DROP_FILES` | 文件拖放 | `file_count` |
| `V5_SC_FILE_SHARED` | 拖放文件同步三 Tab | `file`, `text_len`, `target_tabs` |
| `V5_SC_FILE_ERROR` | 文件读取失败 | `file`, `status` |
| `V5_SC_RESIZE` | 窗口缩放 | `w`, `h` |
| `V5_SC_CREATE` | 窗口创建 | — |
| `V5_SC_CLOSE` | 窗口关闭 | — |

### A.6 与 V5Plus 共创的衔接点

Smart Copilot 与 V5Plus CoCreation 的衔接通过以下路径实现：

| 衔接方式 | 入口 | 数据传递 | 说明 |
|----------|------|----------|------|
| Studio Tab 按钮 | `[V5Plus 共创 ▶]` | `quick_input.toPlainText()` → `open_with_text(text)` | 主入口，条件路由 |
| 快速输入区文本 | Studio Tab `_quick_input` | 用户粘贴/输入的文本 | 传入 V5Plus Stage 0/1 |
| Work Tab Export | Action Bar `[💾 Export PPT]` | `result_text` → `nav.open_studio(text)` | 目前到旧 Studio，可扩展到 V5Plus |
| 拖放共享 | 文件/文本拖入 Smart Copilot | 同步注入三个 Tab → Studio Tab 获取 | 间接路径 |
| 窗口互斥 | `open_cocreation()` | 自动关闭旧 Studio | 同时只开一个工作台 |

**待实现衔接**（链路 I）：
- V5Plus CoCreation → Chat：Stage 3 导出 PPT 后可跳转到 Chat 继续讨论
- Work Tab → V5Plus：Action Bar 的 Export 可直接路由到 V5Plus CoCreation

---

> **相关文档**：
> - 基础架构设计：[`PPT_CoCreation_Design.md`](./PPT_CoCreation_Design.md)（JSON Schema、系统架构、演进路线图）
> - 交互迭代方案：[`PPT_CoCreation_Iteration_Plan.md`](./PPT_CoCreation_Iteration_Plan.md)（10 项交互改进 + Sprint 路线图）
> - UI 总体方案：[`UI_Redesign_Plan_v5.md`](./UI_Redesign_Plan_v5.md)（3-Tab 架构、Studio Tab §3.4）
> - 交互稿：`canvases/ppt-cocreation-e2e-flow.canvas.tsx`（3 阶段端到端版）+ `canvases/opencopilot-ui-interaction-20260609.canvas.tsx`（四窗口全局交互）
