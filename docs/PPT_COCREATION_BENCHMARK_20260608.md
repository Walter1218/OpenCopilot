# PPT 共创双智能体评测

更新日期：`2026-06-08`

## 评测目的

- 用同一套 `ppt_editor` 共创消息构造逻辑，对比 `V5 自研智能体` 与 `Hermes` 在 PPT 共创指令上的真实质量差异。
- 不只比较“有没有回复”，而是比较：
  - 是否命中当前页
  - 是否产出正确的结构化渲染类型
  - 是否把标题、图表、表格、流程图、建议等要求真正落到可执行指令
  - 指令交给本地渲染执行器后能否稳定应用

## 评测入口

- 脚本：`scripts/benchmark_ppt_cocreation_agents.py`
- 原始输出：
  - `output/ppt_cocreation_benchmark.json`
  - `output/ppt_cocreation_benchmark.md`
- 说明：
  - `output` 下的 markdown 仍保留这轮启发式原始分值，适合看相对胜负与指标命中，不建议把分数字面值当成最终产品 KPI

## Case 设计

本轮使用 6 个覆盖面不同的共创场景：

1. `Executive Summary With Chart And Table`
2. `Onboarding Flow Update`
3. `Product Hero Image Layout`
4. `Competitor Comparison Table`
5. `KPI Trend Chart`
6. `Action Page With Recommendations`

## 本轮结论

基于 `output/ppt_cocreation_benchmark.json` 当前这轮真实结果，结论如下：

- `V5 自研智能体` 更强的场景：
  - `Executive Summary With Chart And Table`
  - `KPI Trend Chart`
  - `Action Page With Recommendations`
- `Hermes` 更强的场景：
  - `Product Hero Image Layout`
- 双方基本打平的场景：
  - `Onboarding Flow Update`
  - `Competitor Comparison Table`

从这轮结果看，二者并不是简单的“谁全面更好”，而是各有明显强项：

- `V5 自研智能体` 更擅长：
  - 高管汇报口吻
  - 行动建议展开
  - 标题重写与结论式叙述
- `Hermes` 更擅长：
  - 版式感知
  - 简洁输出
  - 图文页和更偏视觉导向的页面改写

## 关键观察

### 1. 当前页命中仍不稳定

- 在本轮 `Executive Summary` 和 `KPI Trend Chart` 中，`Hermes` 出现了 `slide_index=2` 的偏移，未稳定命中当前页。
- 在前一轮单 case 评测中，也出现过相反方向的漂移，说明“目标页漂移”并非单一 provider 问题，而是当前提示词与协议层对“当前页”约束还不够硬。

结论：

- `当前页命中` 是当前共创链路最应该优先收敛的稳定性问题。

### 2. 图片 / 版式类共创是当前最大短板之一

- `Product Hero Image Layout` 里，自研智能体返回了旧式 `action/update` JSON，而不是 `render_commands`。
- 这导致它虽然语义上做对了事，但在新链路里无法直接被 `RenderCommandParser` 吃掉。
- `Hermes` 在这个 case 中明显更贴近“图文页/视觉页”的表达方式，能够输出带 `layout=image_right`、`hero_image_placeholder`、`caption` 的结构。

结论：

- 版式/图片类任务当前并不是纯模型问题，更是“协议兼容性 + 执行器支持度”问题。

### 3. 标题位协议仍然不够硬

- 多个 case 里，模型虽然“理解了要改标题”，但有时会把标题写成 `body text`，有时写进 `render_params.title`，有时又只是改正文。
- 这使得“标题是否真正替换到标题区”变得不稳定。

结论：

- `slot=title` 与 `render_params.title` 需要更明确的 schema 约束和后处理归一化。

### 4. 建议型页面更偏自研智能体优势区

- 在 `Action Page With Recommendations` 中，自研智能体给出的 COO 风格动作页更像“可直接拿去汇报”的管理动作表。
- `Hermes` 也能完成任务，但更像结构化纪要，而不是强管理口吻的动作页。

结论：

- 对“高管动作页 / 结论页 / 战略叙事页”，自研智能体当前仍有语言风格优势。

### 5. Hermes 时延明显更高

按当前这轮 6 个 case 的 `latency_sec` 粗算：

- `V5 自研智能体` 平均约 `5.97s`
- `Hermes` 平均约 `25.64s`

结论：

- 即使质量可接受，`Hermes` 在共创环节的交互体感仍偏慢。
- 如果后面继续扩大共创内 Hermes 的覆盖比例，需要同步做：
  - 中间态反馈
  - 分步结果回显
  - 超时/取消体验优化

## 优化点

说明：

- 下列条目已经按当前仓库状态重新标注为 `已完成 / 待完成`
- 其中“第一批低风险修复”已落地，文档不再把这些动作继续写成未开始

### A. 提示词层

1. 强化当前页约束 `已完成`

- 在 `ppt_editor` Prompt 中显式加入：
  - `You must update the current slide unless the user explicitly asks for a new page.`
  - `When current slide is requested, slide_index must be -1 or current_index.`

2. 强化标题位约束 `已完成`

- 对“标题改写 / 结论型标题 / sharpen headline”类指令，要求必须输出：
  - `slot=title`
  - `render_params.title`
- 禁止把标题改写写成普通 body 文本。

3. 强化图片/版式示例 `待完成`

- 当前 `image_right / image_left / hero image / caption` 的 few-shot 还不够强。
- 需要补一组“产品发布页 / 图文页 / 单图 + 一句定位语”示例，降低模型退回旧 `action` JSON 的概率。

4. 强化最小完成条件 `待完成`

- 当用户明确要求：
  - `chart`
  - `table`
  - `flowchart`
  - `two recommendations`
- Prompt 中要写成“至少包含这些元素”的硬约束，而不是建议性语气。

### B. 协议层

1. 增加共创结果校验器 `待完成`

- 在模型返回后增加校验：
  - 是否命中当前页
  - 是否包含要求的 render type
  - 标题是否落在 `slot=title`
  - 建议条数是否满足最低要求
- 不满足时自动轻量 reprompt，而不是直接进入渲染。

2. 兼容旧式 `action/update` JSON `已完成`

- 当前图片/版式类 case 暴露出，自研智能体仍可能返回旧格式。
- 需要在 `AIWorker` 共创链路里补：
  - 新格式优先走 `RenderCommandParser`
  - 若只返回旧格式，则走旧动作解析和执行兜底

3. 明确版式 patch 语义 `待完成`

- 现在很多模型把 `layout=image_right` 塞在 `text` 指令里，执行层不一定完整理解。
- 建议新增更明确的协议形式：
  - `render_type=layout_patch`
  - 或在 `render_params` 中增加标准化 `layout_patch` 字段

### C. 渲染执行层

1. 补标题位强制落盘 `已完成`

- 若 `slot=title` 存在，则执行器应优先更新 slide title，而不是把它当普通 body 内容。

2. 补图片布局执行能力 `部分完成`

- 当前 `hero_image_placeholder`、`caption`、`layout=image_right` 这类字段的执行效果不够强。
- 需要让执行器真正把它们映射成：
  - slide layout 变化
  - image item 注入
  - caption 注入

3. 补 post-normalization `已完成`

- 若模型返回 `slide_index=2`，但用户明确在编辑当前页且没有要求新增页面，则可做一次安全归一化，回写为当前页。

## 当前 TODO

- `P0`：补“最小完成条件校验 + 自动轻量 reprompt”，至少覆盖当前页、标题位、目标 render type、建议条数
- `P0`：标准化图片/版式 patch 语义，避免 `layout=image_right` 继续混在普通 `text` 指令里
- `P1`：在第一批修复后重跑 `PPT` 共创 6-case 基准，刷新本报告中的质量与时延结论
- `P1`：补产品发布页 / 单图页 / 图文页 few-shot，强化 Hermes 与自研在视觉型页上的协议一致性
- `P1`：评估是否把导入 `.md` 文件来源标识透传到共创日志，方便溯源与排障

## 已落地的第一批修复

截至 `2026-06-08` 当前分支，已先落地第一批低风险修复：

- `ppt_editor` 提示词与渲染 prompt 已补充：
  - 默认只改当前正在编辑的页
  - 标题改写必须落到标题位
- `AICopilotChatWidget` 在接收模型响应时新增轻量归一化：
  - 若未显式要求新增页面，`slide_index` 会优先归一到当前页
  - 标题类指令会优先提升到 `slot=title`
  - 旧式 `action/update` JSON 数组现在可以直接展开并继续兼容处理
- `RenderExecutor` 已补一层兜底：
  - `slot=title` 时优先使用 `render_params.title`
  - `image_right / image_left / image_top` 指令会同步落版式到 slide layout

这批修复的目标不是“彻底解决全部共创问题”，而是先降低最常见的：

- 当前页漂移
- 标题写进正文
- 旧格式 JSON 无法直接应用
- 图文布局只生成 item、不落版式

## 总结

这轮基准说明：

- `Hermes` 已经能承担大量共创执行任务，但还不够稳定，不应把“能跑通”误判成“已完全成熟”。
- `V5 自研智能体` 在叙事、动作页、管理层语气上仍保有明显优势。
- 眼下最该做的不是盲目二选一，而是先把：
  - 当前页命中
  - 标题位协议
  - 图片/版式共创
  - 旧格式兼容

这四个共性短板补齐。
