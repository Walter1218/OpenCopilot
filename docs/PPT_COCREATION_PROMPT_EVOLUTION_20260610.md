# PPT 共创提示词设计与迭代详解

> 更新时间：2026-06-10
> 目标：把当前 `PPT 共创模式优化` 的提示词来源、组装方式、版本演进、优化前后完整案例，一次性讲清楚。

---

## 1. 这份文档回答什么问题

这份文档重点回答 6 个问题：

1. 当前 `PPT 共创` 到底有哪些 prompt，不是一个还是多个
2. 这些 prompt 分别来自哪些文件、哪些函数
3. 它们在运行时是如何被拼装在一起的
4. 优化前的 prompt 长什么样
5. 中间几个版本分别改了什么
6. 这一轮迭代，围绕 `situation / character / objective / rules / example` 五种结构，具体增强了哪些部分

注意：

- 当前仓库里，`PPT 共创` 不是“一个大 prompt”，而是“系统规则 + 场景用户消息 + 动态示例”的组合
- 如果走 `self_agent` 本地链路，system/user prompt 都能在仓库中直接追溯
- 如果走 `Hermes / vnext provider`，本地仓库能完全看到的是 `user_message + context_source + context_meta`，远端 provider 侧最终 system prompt 不在当前仓库中
- 因此，本文对“当前完整请求 prompt”的说明，会区分：
  - `本地 self_agent 可验证完整消息`
  - `Hermes 本地可观测请求载荷`

---

## 2. 当前 prompt 总览

当前版本的 `PPT 共创` prompt 由 4 个来源共同构成：

| 层 | 来源文件 | 作用 | 对应 SCORE 结构 |
|---|---|---|---|
| 上下文规则层 | `opencopilot/shared/prompt.py` 里的 `CONTEXT_DESCRIPTIONS["ppt_editor"]` | 定义 PPT 编辑角色、输出协议、硬约束、JSON 示例 | `character / objective / rules / example` |
| 通用 persona 层 | `personas/chat.md` | 注入 OpenCopilot 助手身份和通用回答风格 | `character` |
| 场景消息层 | `opencopilot/capabilities/ppt/ai_chat_widget.py` 的 `_build_user_message()` | 注入当前页、相邻页摘要、用户指令、当前 slide JSON | `situation / objective` |
| 动态 few-shot 层 | `opencopilot/capabilities/ppt/render_prompt_generator.py` | 根据“图表/表格/流程图/文本”动态注入示例和输出 schema | `example / rules` |

一句话概括：

- 当前版本不是“单段 prompt”，而是“`ppt_editor` 规则底座 + `chat persona` + 当前页场景消息 + render 指令 few-shot 示例”。

---

## 3. 当前版本是如何组装在一起的

## 3.1 UI 入口

PPT 共创入口在：

- `opencopilot/capabilities/ppt/ai_chat_widget.py`

实际执行流程是：

1. `AIWorker.run()` 先调用 `_build_user_message()`
2. 构造 `V5AgentWorker(prompt=user_message, action_type="chat", context_source="ppt_editor", ...)`
3. 根据路由，进入 `self_agent` 或 `Hermes / vnext provider`

这里有一个非常关键的事实：

- `V5AgentWorker` 传给下游的 `prompt`，其实是 `user_message`
- PPT 共创专有的系统约束，不是写在 `action_type="chat"` 的 persona 里，而是靠 `context_source="ppt_editor"` 在下游追加

也就是说：

- `action_type="chat"` 决定加载 `chat persona`
- `context_source="ppt_editor"` 决定加载 `ppt_editor` 规则提示

---

## 3.2 self_agent 本地链路的真实组装顺序

如果走本地 `self_agent`，实际组装链路如下：

1. `AIWorker._build_user_message()` 生成用户侧场景消息
2. `call_agent_pipeline_sync()` 创建 `PipelineContext`
3. `SessionSetupMiddleware.process()` 做 4 件事：
   - 加载 persona：`load_persona("chat")`
   - 根据 `context_source="ppt_editor"` 读取 `CONTEXT_DESCRIPTIONS["ppt_editor"]`
   - 组合为 `ctx.enriched_system = context_prefix + "\n\n" + persona_prompt`
   - 再调用 `ContextWindowManager.build_messages()` 组装成消息列表
4. 最终进入模型的消息列表格式为：

```json
[
  {
    "role": "system",
    "content": "<ppt_editor 规则提示>\\n\\n<chat persona>\\n\\n<可选 skill tools prompt>"
  },
  {
    "role": "user",
    "content": "<AIWorker._build_user_message() 的输出>"
  }
]
```

需要特别说明两点：

- `skill tools prompt` 是通用能力注入，不属于 PPT 共创专属 prompt，因此本文后面的“当前完整 prompt 示例”默认不展开这一段
- 仓库里还有 `build_full_prompt()` 这个离线组装函数，它和 runtime 的拼装逻辑等价，但实际在线运行时主要走的是 `SessionSetupMiddleware + build_messages()`

---

## 3.3 Hermes 路径本地可看到什么

如果走 `Hermes / vnext provider`，本地仓库能确定看到的请求信息是：

- `prompt=user_message`
- `action_type="chat"`
- `context_source="ppt_editor"`
- `context_meta` 中带上：
  - `ppt_cocreation: true`
  - `slides_count`
  - `current_index`
  - `current_slide_title`
  - `current_slide_layout`
  - `original_text_len`

也就是说，本地侧可以确定：

- `Situation` 是同一份 `user_message`
- `context_source` 明确告诉 provider 这是 `ppt_editor` 场景

但远端 provider 内部最终 system prompt 的完整原文，不在当前仓库中。因此本文凡是写“当前完整 system prompt”，都以 `self_agent` 可追溯链路为准。

---

## 4. 当前 prompt 的 4 个来源，分别来自哪里

## 4.1 来源一：`ppt_editor` 上下文规则

来源：

- `opencopilot/shared/prompt.py`
- 键名：`CONTEXT_DESCRIPTIONS["ppt_editor"]`

它负责定义：

- 你是谁：专业的 PPT 编辑助手
- 目标是什么：根据用户指令选择最精准的修改模式
- 默认策略是什么：优先局部修改
- 绝对不能犯什么错：不能整体替换 items、不能把标题放 body、不能改错页
- 支持的协议长什么样：`action/update_item/add_item/remove_item/add_slide/remove_slide/render-like` 结构化输出示例

它对应 SCORE 中的：

- `character`
- `objective`
- `rules`
- 一部分 `example`

---

## 4.2 来源二：`chat persona`

来源：

- `personas/chat.md`

它不负责 PPT 专业规则，只负责：

- OpenCopilot 助手身份
- 通用中文输出风格
- 不暴露系统 prompt

它的作用更像“品牌人格层”，而不是“PPT 专业协议层”。

所以当前 PPT 共创的角色其实是两层叠加：

1. `ppt_editor`：专业 PPT 编辑助手
2. `chat persona`：OpenCopilot 智能助手的通用身份

---

## 4.3 来源三：当前页场景消息

来源：

- `opencopilot/capabilities/ppt/ai_chat_widget.py`
- 方法：`AIWorker._build_user_message()`

它负责给模型交代“现在你面对的具体编辑现场”：

- 总页数
- 当前页索引
- 前一页摘要
- 当前页完整 JSON
- 后一页摘要
- 用户指令
- 输出格式要求

这部分是当前版本 `situation` 的核心。

---

## 4.4 来源四：动态 render prompt

来源：

- `opencopilot/capabilities/ppt/render_prompt_generator.py`

它会根据用户指令中的关键词动态识别：

- 图表类：`chart`
- 表格类：`table`
- 流程类：`flowchart`
- 文本类：`text`

然后自动补：

- 这一类任务的 JSON 输出示例
- 这一类任务的字段要求
- 当前页 / 标题位等强约束

这一层的价值不在于“多写了一段提示词”，而在于：

- 从静态 prompt 变成“按任务类型切换的 few-shot”

---

## 5. 历史版本时间线

当前可以清晰追溯出 7 个关键阶段：

| 阶段 | 代表提交 | 主要形态 | 核心特点 |
|---|---|---|---|
| V1 内联单体版 | `e1b5af3` | `ai_chat_widget.py` 里直接拼 `system_prompt + user_message` | 所有规则写死在 UI；用户侧传全量 slides JSON |
| V2 中央收口版 | `483669b` | `ppt_editor` 迁入 `shared/prompt.py` | system prompt 从 UI 抽离；但 user_message 仍是全量 slides |
| V3 增量上下文版 | `1bb0299` | 当前页完整 + 相邻页摘要 | 上下文从“全量 PPT”压缩为“当前页中心” |
| V4 动态 few-shot 强约束版 | `d5b03d7` 及之后当前实现 | `ppt_editor` + render_prompt_generator + 归一化后处理 | 增加当前页命中、标题位命中、render_commands 优先、类型示例 |
| V5 事实锚点版 | 2026-06-11 当前代码 | `ppt_editor` 增加事实锚点/计划结果区分/风险保留硬约束 | 文案改写不再只追求“更像汇报”，开始显式限制事实漂移 |
| V6 结构保持版 | 2026-06-11 当前代码 | `ppt_editor` 增加条目数量/顺序/区间保持约束 | 忠实改写从“保数字”扩展到“保结构、保粒度、保区间” |
| V7 复合任务与正反例版 | 2026-06-11 当前代码 | `PPT_EDITOR_PROMPT_VERSION = v7_compound_task` + `prompts/ppt_editor/` 快照 | 加入忠实改写正反例、复合任务 few-shot，并开始版本化 prompt 管理 |

---

## 6. 统一案例：用于对比的同一条用户需求

为了把“优化前”和“优化后”对齐，下面统一使用同一案例。

用户指令：

```text
把当前页标题改成更聚焦结果，并把财务数据转成柱状图，再补两条行动建议
```

原始文本：

```text
Executive summary: Total revenue in H1 2026 reached 850M RMB, up 32 percent year over year.
Financial data: Q1 revenue was 380M RMB and Q2 revenue was 470M RMB.
Product lines: Copilot Pro renewal 91 percent, Knowledge Hub renewal 84 percent, Meeting Bot trial-to-paid 27 percent.
Management actions: focus on enterprise expansion, improve Meeting Bot conversion, and strengthen cross product selling.
```

示例 slides：

```json
{
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "2026 H1 Business Review",
      "subtitle": "Leadership Review"
    },
    {
      "type": "content",
      "layout": "text_only",
      "title": "Business Overview",
      "items": [
        {
          "level": 0,
          "text": "Revenue grew 32 percent year over year and enterprise plans led growth.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "Q1 revenue was 380M RMB and Q2 revenue was 470M RMB.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "Copilot Pro, Knowledge Hub, and Meeting Bot showed different retention patterns.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "We should expand enterprise sales and improve Meeting Bot conversion.",
          "content_type": "text"
        }
      ]
    },
    {
      "type": "ending",
      "layout": "center",
      "title": "Thanks",
      "subtitle": "Q and A"
    }
  ]
}
```

当前编辑页：

- 第 2 页

---

## 7. 优化前：V1 内联单体版的完整 prompt

## 7.1 V1 的 prompt 来自哪里

优化前的关键特征是：

- system prompt 在 `ppt_cocreation/ai_chat_widget.py::_build_system_prompt()`
- user prompt 在同文件 `::_build_user_message()`
- 运行时直接：

```text
full_message = system_prompt + "\n\n" + user_message
```

再把这个 `full_message` 作为普通文本一次性发给 Agent。

这意味着：

- `character / objective / rules / example / situation` 全都塞在同一个大字符串里
- UI 层直接拥有 prompt 真相
- 很难按职责分层演进

---

## 7.2 V1 的 system prompt 原文

下面这段来自历史版本 `e1b5af3`：

```text
你是一个 PPT 编辑助手。优先进行局部修改，而不是重新生成整个PPT。

修改模式（按优先级排序）：

1. **局部修改**（推荐）：只修改用户指定的部分
   - 修改标题：{"action": "update", "slide_index": 1, "field": "title", "value": "新标题"}
   - 修改副标题：{"action": "update", "slide_index": 0, "field": "subtitle", "value": "新副标题"}
   - 修改版式：{"action": "update", "slide_index": 0, "field": "layout", "value": "image_right"}

2. **修改要点**：
   - 更新要点：{"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "新内容"}
   - 添加要点：{"action": "add_item", "slide_index": 1, "item": {"text": "新要点", "level": 0, "content_type": "text"}}
   - 删除要点：{"action": "remove_item", "slide_index": 1, "item_index": 0}

3. **幻灯片操作**：
   - 添加幻灯片：{"action": "add_slide", "index": 2, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": []}}
   - 删除幻灯片：{"action": "remove_slide", "index": 2}

4. **内容转换**（当用户要求转换为图表/表格时）：
   - 转为表格：{"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "标题", "columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}
   - 转为柱状图：{"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "标题", "labels": ["标签1", "标签2"], "datasets": [{"label": "系列", "data": [10, 20], "color": "#007bff"}]}}}
   - 转为折线图：同上，chart_type 改为 "line"
   - 转为饼图：同上，chart_type 改为 "pie"

5. **全局修改**（仅当用户明确要求"重新生成"时使用）：
   - 返回 {"slides": [...]}

内容类型：text / image / flowchart / icon / table / chart
版式类型：center / text_only / image_right / image_left / three_columns / two_columns / full_image
```

---

## 7.3 V1 的 user prompt 原文

同一版本里，用户消息原文是：

````text
当前幻灯片数据：
```json
{
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "2026 H1 Business Review",
      "subtitle": "Leadership Review"
    },
    {
      "type": "content",
      "layout": "text_only",
      "title": "Business Overview",
      "items": [
        {
          "level": 0,
          "text": "Revenue grew 32 percent year over year and enterprise plans led growth.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "Q1 revenue was 380M RMB and Q2 revenue was 470M RMB.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "Copilot Pro, Knowledge Hub, and Meeting Bot showed different retention patterns.",
          "content_type": "text"
        },
        {
          "level": 0,
          "text": "We should expand enterprise sales and improve Meeting Bot conversion.",
          "content_type": "text"
        }
      ]
    },
    {
      "type": "ending",
      "layout": "center",
      "title": "Thanks",
      "subtitle": "Q and A"
    }
  ]
}
```

当前正在编辑第 2 页幻灯片。

用户指令：把当前页标题改成更聚焦结果，并把财务数据转成柱状图，再补两条行动建议

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：
````

---

## 7.4 V1 的完整请求长什么样

V1 实际发给下游的内容，可以理解为：

```text
<上面的 system prompt>

<上面的 user prompt>
```

V1 的主要问题有 5 个：

1. `Situation` 太重，直接把全量 slides 都塞进去
2. `Rules` 偏软，没有“只能改当前页”“标题必须进标题位”这种硬约束
3. `Example` 只有旧 JSON action 示例，没有 render command few-shot
4. `Character` 偏泛，只是 PPT 编辑助手，没有“专业编辑执行体”的收束
5. prompt 直接写在 UI 里，维护成本高，难做统一演化

---

## 8. 过渡版：V2 中央收口版

## 8.1 这一版改了什么

到 `483669b`，最核心的变化不是 prompt 内容突然大改，而是：

- `ppt_editor` system prompt 从 UI 内联，迁移到 `opencopilot/shared/prompt.py`

这一步的本质是：

- 把“prompt 真相”从 UI 组件，收口到统一 prompt 模块

但是这一版仍然保留了两个旧特征：

1. user_message 还是全量 `slides` JSON
2. 还没有 render command 动态 few-shot

---

## 8.2 V2 的 system prompt 关键变化

V2 的 `ppt_editor` 依然还是偏“旧 action JSON 驱动”的思路，但已经开始加强“从非结构化文本提取结构化数据”的说明，例如：

```text
当用户说"把这个内容做成表格"或"用图表展示"时，你需要：
1. 分析内容结构，识别出可提取的数据模式
2. 从自然语言中提取关键信息（人物、属性、数值等）
3. 将提取的数据组织成表格/图表格式
```

也就是说，这一版开始补强：

- `Objective`：不是只会改字，还要会抽数据做结构化转换
- `Rules`：增加了“数据抽取”的隐性执行要求

但它还没有解决：

- 当前页命中
- 标题位命中
- render_commands 优先

---

## 9. 过渡版：V3 增量上下文版

## 9.1 这一版改了什么

到 `1bb0299`，最大变化发生在 user_message：

- 从“全量 slides JSON”
- 变成“当前页完整 JSON + 前后页摘要”

这一版的 `_build_user_message()` 原文结构是：

````text
PPT 总共 N 页，当前正在编辑第 X 页。

前一页（第 X-1 页）摘要：...

当前幻灯片数据：
```json
{当前页完整 JSON}
```

后一页（第 X+1 页）摘要：...

用户指令：...

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：
````

这一步是一次非常关键的 `Situation` 设计优化：

- 模型终于不再盯着整份 PPT，而是围绕当前页进行编辑
- 同时保留前后页，防止内容风格和叙事上下文断裂

---

## 9.2 V3 的局限

V3 仍然有两个明显缺口：

1. 输出格式仍然主要围绕旧 `action/update_item/add_item` JSON
2. 对图表/表格/流程图没有按任务类型动态注入 few-shot 示例

因此 V3 虽然已经解决了 `Situation` 聚焦问题，但 `Example` 和 `Rules` 还没有彻底升级。

---

## 10. 当前版：V4 动态 few-shot + 强规则版

## 10.1 当前版的 system prompt 原文

当前版本 `ppt_editor` 的核心 system prompt 如下：

```text
你是一个专业的 PPT 编辑助手。根据用户指令选择最精准的修改模式：

**模式判断规则**：
- 如果用户明确说"重新生成"、"重做"、"全部重新来" → 使用全局修改模式
- 如果用户说"加一页"、"新增一页" → 使用 add_slide
- 其他情况 → 使用局部修改模式

**核心原则（必须遵守）**：
1. 【精准操作优于整体替换】修改单个元素时，必须用 update_item/add_item/remove_item，严禁用 update 替换整个 items 数组。
2. 【内容要有信息量】生成的文本必须至少 8 个字，表达完整意思，不是关键词堆砌。
3. 【数据必须结构化】涉及数值、对比、排名的内容，必须使用 table_data（表格）或 chart_data（图表）格式，不得用纯文本。
4. 【流程必须可视化】涉及步骤、阶段、审批流的，必须使用 flowchart_data 格式。
5. 【排版本质匹配】比较类内容优先用 three_columns，数据图表页优先用 image_right 布局。
6. 【默认只改当前页】除非用户明确要求新增页面，否则 slide_index 必须指向当前正在编辑的页，不得漂移到其他页。
7. 【标题必须落标题位】当用户要求修改标题、headline、结论型标题时，必须输出标题位更新；若用渲染指令格式，必须使用 slot=title 和 render_params.title。

修改模式（按优先级排序）：

1. **精准局部修改**（推荐用于大多数情况）：
   - 修改标题：{"action": "update", "slide_index": 1, "field": "title", "value": "更有冲击力的标题（至少10字）"}
   - 修改副标题：{"action": "update", "slide_index": 0, "field": "subtitle", "value": "新副标题"}
   - 修改版式：{"action": "update", "slide_index": 0, "field": "layout", "value": "image_right"}
   - 修改单个要点：{"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "完整描述句（至少8字）"}
   - 添加要点：{"action": "add_item", "slide_index": 1, "item": {"text": "完整描述句（至少8字）", "level": 0, "content_type": "text"}}
   - 删除要点：{"action": "remove_item", "slide_index": 1, "item_index": 0}
   - 复杂操作时，返回多个 JSON 对象，每行一个，逐行输出

2. **幻灯片增删**：
   - 添加幻灯片：{"action": "add_slide", "index": 2, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": [{"level": 0, "text": "完整要点", "content_type": "text"}]}}
   - 删除幻灯片：{"action": "remove_slide", "index": 2}

3. **内容转换为结构化格式**（当用户要求转换为图表/表格/流程图时，必须使用结构化数据）：
   a) 转为表格（对比、排名、规格参数）：
   {"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "标题", "columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}
   b) 转为柱状图（适合对比）、折线图（适合趋势）、饼图（适合占比）：
   {"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "标题", "labels": ["A","B"], "datasets": [{"label": "系列", "data": [10,20], "color": "#007bff"}]}}}
   c) 转为流程图（适合步骤、阶段、审批链）：
   {"action": "add_item", "slide_index": 0, "item": {"content_type": "flowchart", "flowchart_data": {"title": "流程标题", "nodes": [{"id": "n1", "text": "第一步", "shape": "start"}, {"id": "n2", "text": "第二步", "shape": "process"}, {"id": "n3", "text": "完成", "shape": "end"}], "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]}}}

4. **全局修改**（当用户明确要求"重新生成"）：
   - 返回完整的 {"slides": [...]} 格式
   - 确保包含封面页和结尾页（type=ending, layout=center, title="谢谢"）
```

这段是当前版 `character / objective / rules / example` 的主骨架。

---

## 10.2 当前版的用户场景消息原文

使用同一个案例，当前版本 `_build_user_message()` 组装出的内容是：

````text
PPT 总共 3 页，当前正在编辑第 2 页。

前一页（第 1 页）摘要：标题：2026 H1 Business Review，版式：center，要点：无要点

当前幻灯片数据：
```json
{
  "type": "content",
  "layout": "text_only",
  "title": "Business Overview",
  "items": [
    {
      "level": 0,
      "text": "Revenue grew 32 percent year over year and enterprise plans led growth.",
      "content_type": "text"
    },
    {
      "level": 0,
      "text": "Q1 revenue was 380M RMB and Q2 revenue was 470M RMB.",
      "content_type": "text"
    },
    {
      "level": 0,
      "text": "Copilot Pro, Knowledge Hub, and Meeting Bot showed different retention patterns.",
      "content_type": "text"
    },
    {
      "level": 0,
      "text": "We should expand enterprise sales and improve Meeting Bot conversion.",
      "content_type": "text"
    }
  ]
}
```

后一页（第 3 页）摘要：标题：Thanks，版式：center，要点：无要点

用户指令：把当前页标题改成更聚焦结果，并把财务数据转成柱状图，再补两条行动建议

用户指令：把当前页标题改成更聚焦结果，并把财务数据转成柱状图，再补两条行动建议

## 输出示例（chart类型）
```json
{
  "render_commands": [
    {
      "source_text": "2025年营收12.8亿元，2024年营收10.5亿元",
      "render_type": "chart",
      "render_params": {
        "chart_type": "bar",
        "title": "营收对比",
        "chart_data": {
          "labels": ["2024年", "2025年"],
          "values": [10.5, 12.8]
        }
      }
    }
  ]
}
```

## 输出格式要求

必须返回 JSON 格式的渲染指令：

```json
{
  "render_commands": [
    {
      "source_text": "原文片段（必填，用于定位）",
      "render_type": "chart|table|flowchart|text",
      "render_params": {
        "title": "标题"
      },
      "slide_index": -1,
      "slot": "body"
    }
  ]
}
```

重要：
1. source_text 必须是原文中的完整片段
2. render_type 必须是以下之一：chart, table, flowchart, text
3. chart 类型需要提供 chart_type（bar/line/pie）和 chart_data
4. table 类型需要提供 table_data（含 headers 和 rows）
5. flowchart 类型需要提供 flowchart_data（含 nodes 和 edges）
6. 默认只修改当前正在编辑的页，除非用户明确要求新增页面；此时 slide_index 必须使用当前页索引或 -1
7. 如果用户要求修改标题、headline 或结论型标题，必须输出 slot=title，并将标题文本放在 render_params.title
````

说明：

- `用户指令` 在当前实现里会出现两次
- 第一次来自 `_build_user_message()` 主体
- 第二次来自 `render_prompt_generator.generate_prompt()`
- 这不是概念重复，而是故意把“主任务”和“动态 few-shot 条件”都对齐到同一条 instruction 上

---

## 10.3 当前版的 persona 层原文

当前本地 `self_agent` 链路里，还会追加 `personas/chat.md`：

```text
你是 OpenCopilot 智能助手，由 OpenCopilot 团队打造的 AI 编程与办公伙伴。

## 身份
- 你的名字是 OpenCopilot 助手（或简称 Copilot 助手）
- 你不是 MiMo、不是 ChatGPT、不是其他任何模型的马甲

## 能力
- 代码助手
- 知识检索
- PPT 创作
- 文本处理
- 文件操作

## 风格
- 简洁专业，不说多余的客套话
- 回答问题时优先给出解决方案
- 使用中文回复
```

它不会覆盖 `ppt_editor` 的专业协议，但会给回答增加：

- OpenCopilot 身份一致性
- 中文风格一致性

---

## 10.4 当前版最终发给 self_agent 的消息结构

如果走本地 `self_agent`，当前版本最终是：

```json
[
  {
    "role": "system",
    "content": "<ppt_editor 规则提示>\\n\\n<chat persona>"
  },
  {
    "role": "user",
    "content": "<第 10.2 节的用户场景消息>"
  }
]
```

如果走 `Hermes / vnext provider`，本地能确定的是：

```json
{
  "user_input": "<第 10.2 节的用户场景消息>",
  "action": "chat",
  "context_source": "ppt_editor",
  "context_meta": {
    "ppt_cocreation": true,
    "slides_count": 3,
    "current_index": 1,
    "current_slide_title": "Business Overview",
    "current_slide_layout": "text_only",
    "original_text_len": 382
  }
}
```

---

## 11. 优化前后，到底改了哪些 prompt 结构

下面按 `situation / character / objective / rules / example` 五种结构拆开。

## 11.1 Situation

优化前：

- 把整份 `slides` 全量 JSON 喂给模型
- 当前页信息只是一句“当前正在编辑第 X 页”

优化后：

- `当前页完整 JSON` 成为主上下文
- `前一页摘要 + 后一页摘要` 作为局部叙事补充
- 用户 instruction 之后，再补一层动态 render prompt

本质变化：

- 从“让模型看整份 PPT”
- 变成“让模型聚焦当前页，同时保持前后文感知”

收益：

- 降低 token 消耗
- 降低 slide_index 漂移概率
- 提高局部编辑命中率

---

## 11.2 Character

优化前：

- 角色是“一个 PPT 编辑助手”

优化后：

- 角色升级为“一个专业的 PPT 编辑助手”
- 同时叠加 `OpenCopilot 智能助手` 的通用 persona

本质变化：

- 从泛化角色
- 变成执行型、约束型、协议型角色

收益：

- 模型更容易遵守输出协议
- 更不容易跑成泛化对话助手

---

## 11.3 Objective

优化前：

- 目标是“优先局部修改，不要重做整份 PPT”

优化后：

- 目标变成“根据用户指令选择最精准的修改模式”
- 明确区分：
  - 全局修改
  - 新增页面
  - 精准局部修改
  - 结构化内容转换

本质变化：

- 从模糊目标
- 变成明确决策树目标

收益：

- 模型不只是“输出 JSON”
- 而是在先做“模式判断”，再做“协议输出”

---

## 11.4 Rules

这是本轮迭代改动最大的部分。

优化前：

- 只有“优先局部修改”“用 JSON 返回”这类一般性要求

优化后新增的硬规则包括：

1. 不允许整体替换 `items`
2. 生成文本至少要有完整语义，不允许关键词堆砌
3. 数值类内容必须结构化成 `table_data / chart_data`
4. 流程类内容必须结构化成 `flowchart_data`
5. 比较类、图表类内容有推荐布局
6. 默认只改当前页
7. 标题类指令必须命中标题位
8. `render_commands` 场景下必须用 `slot=title + render_params.title`

本质变化：

- 从“希望你这么做”
- 变成“你必须这么做”

收益：

- 当前页命中率提升
- 标题落位正确率提升
- 图表/表格/流程图的解析成功率提升

---

## 11.5 Example

优化前：

- 示例几乎全部是旧式 `action/update_item/add_item` JSON
- 没有按任务类型切换示例

优化后：

- 保留旧 JSON 示例作为兼容兜底
- 新增 `render_commands` 示例
- 按类型动态 few-shot：
  - chart
  - table
  - flowchart
  - text

本质变化：

- 从“静态示例”
- 变成“任务感知型 few-shot”

收益：

- 图表类 instruction 更容易直接产出可执行 render 指令
- 流程类和表格类输出的 schema 更稳定

---

## 12. 这轮迭代最重要的 6 个变化

1. prompt 真相从 UI 内联，迁移到统一 `ppt_editor` context
2. 用户上下文从全量 slides，收缩为当前页中心视角
3. render 指令从“可选补充”升级为“推荐主输出”
4. 当前页命中和标题位命中，变成明确硬约束
5. few-shot 从静态 JSON 示例，升级为按任务类型动态生成
6. prompt 之外再加一层后处理归一化，兜底修正 `slide_index` 和 `slot=title`

第 6 点非常关键：

- 现在不是只依赖 prompt“说服模型”
- 还会在 `AICopilotChatWidget` 中做：
  - 当前页归一化
  - 标题位提升
  - 旧数组 action 兼容

这意味着这轮优化不是“只改提示词”，而是“提示词 + 协议 + 后处理”的一体化升级。

---

## 13. 如果只看一句话，当前版本的核心设计是什么

当前 `PPT 共创` 提示词设计的核心，不再是“写一段更长的 system prompt”，而是：

- 用 `ppt_editor` 统一角色和硬规则
- 用 `_build_user_message()` 锚定当前页编辑现场
- 用 `render_prompt_generator` 动态注入任务型 few-shot
- 再用后处理把当前页命中和标题位命中兜住

也就是：

- 从“文案型 prompt”
- 升级成“协议型 prompt + 场景型 prompt + few-shot prompt”的组合系统

---

## 14. 仍然存在的边界与风险

当前版本已经明显优于旧版，但仍有 4 个边界需要认识清楚：

1. `Hermes` 远端最终 system prompt 在本地仓库不可见，观测性仍不完整
2. 当前 `ppt_editor` 规则仍有一部分在 UI 层和后处理层，尚未完全收口到 Runtime 协议中心
3. `render_prompt_generator` 的类型检测仍是关键词驱动，复杂复合指令下可能不够细
4. `chat persona` 与 `ppt_editor` 的职责虽已分离，但仍依赖 `context_source` 优先级清洗，长期更适合抽成能力协议真源

---

## 15. 结论

如果用一句最准确的话总结这轮 prompt 迭代：

- 优化前，PPT 共创更像“UI 里写死的一段局部修改说明”
- 优化后，PPT 共创已经演化成“当前页中心的编辑协议系统”

围绕 `situation / character / objective / rules / example` 五种结构，本轮真正完成的是：

- `Situation`：从全量 PPT 改成当前页中心
- `Character`：从普通助手改成专业编辑执行体
- `Objective`：从模糊编辑改成模式判断 + 协议输出
- `Rules`：从软约束改成强约束
- `Example`：从静态 JSON 改成按任务类型动态 few-shot

这也是为什么这一轮提升不是“prompt 文案优化”，而是“prompt 架构升级”。

---

## 16. 后续迭代升级建议

基于当前实现和前面的分析，后续升级不建议继续走“只堆 prompt 文案”的路线，而应明确拆成三层：

1. `prompt`：负责单次模型调用内部的角色、规则、输出协议、few-shot 示例
2. `skill`：负责跨调用的路由、上下文装配、补问、能力切换、失败回退
3. `code`：负责确定性的 schema 校验、归一化、兼容修复和执行兜底

换句话说：

- `prompt` 解决“这次怎么答”
- `skill` 解决“这件事怎么跑”
- `code` 解决“怎么保证别翻车”

当前版本已经把 `prompt + code` 这两层做出了明显进展，但 `skill` 层基本还没有独立出来，因此下一个阶段的升级重点，应该是把“编排脑子”从 `ppt_editor` prompt 中抽离。

---

## 17. prompt 与 skill 的边界

## 17.1 哪些问题应该继续增强 prompt

以下问题，本质上仍然属于“单次模型调用内部行为控制”，建议继续通过 `prompt` 演进：

1. `ppt_editor` 的角色定义
2. 当前页编辑的规则与输出协议
3. `render_commands` 的 schema/example 说明
4. 图表/表格/流程图/标题改写类的 few-shot
5. 复合编辑任务的输出示例
6. 当前页编辑场景的 `situation` 组织方式

这些能力的共同特点是：

- 不需要跨能力切换
- 不需要多步编排
- 目标是让模型本轮输出更稳定、更可执行

例如：

- “把当前页标题改成更有结论感”
- “把这段内容转成表格”
- “把当前页改成图表页”
- “补两条行动建议并保持当前页结构”

这些都应该继续由 `ppt_editor` prompt 驱动，而不是抽成 skill。

---

## 17.2 哪些问题最适合抽成 skill

以下问题，本质上属于“系统编排和流程控制”，最适合抽成 skill：

1. `ppt_editor` vs `ppt_generator` 的路由判断
2. `current_slide` vs `full_deck` 的 scope 判断
3. 是否需要补问
4. 该装哪些上下文
5. 该挂哪类 few-shot profile
6. 失败后的回退或降级策略

这些能力的共同特点是：

- 会影响后续调用路径
- 会影响上下文装配粒度
- 不是在回答用户，而是在决定系统下一步怎么执行

例如：

- 用户说“全部重新来”，到底是当前页重做还是整稿重做
- 当前只有当前页上下文时，是否足以执行
- 当前请求更适合 `ppt_editor` 还是 `ppt_generator`
- 当前任务需要挂 `chart_conversion` 还是 `headline_rewrite` 的 few-shot profile

这类能力继续塞在 `ppt_editor` prompt 里，会让 prompt 同时承担“执行”和“编排”两种职责，边界会越来越混乱。

---

## 17.3 哪些部分不该主要依赖 prompt 或 skill，而应继续放在代码层

以下问题属于高频、确定性、可程序化修复的问题，最适合继续由代码兜底：

1. `slide_index` 漂移修正
2. `slot=title` 提升
3. 旧 `action/update` JSON 兼容
4. 字段缺省补齐
5. 枚举值和字段别名修复
6. schema 校验

这些能力的共同特点是：

- 是机械性错误，不是理解性错误
- 用 prompt 反复强调收益有限
- 用代码兜底更便宜、更稳、更可测试

当前版本在这一层已经做得相对正确，后续不建议把这些能力 skill 化。

---

## 18. 当前系统最需要收口的矛盾

当前实现里最值得优先修正的矛盾有两个。

### 18.1 `ppt_editor` 的“全局修改”表述与上下文能力边界不一致

当前 `ppt_editor` 规则里仍然保留了：

- 用户说“重新生成”“重做”“全部重新来”时使用全局修改

但真正发送给模型的上下文仍然是：

- 当前页完整 JSON
- 前一页摘要
- 后一页摘要

这意味着：

- 当前链路更适合“当前页重做 / 当前页重构”
- 并不真正适合“整份 PPT 全量重生成”

因此，后续建议是：

1. 在 `ppt_editor` prompt 中弱化或移除“整稿全局修改”的表述
2. 将“整份 PPT 重做”明确交给上层 route decision
3. 由 `skill` 或 orchestrator 判断是否切到 `ppt_generator`

### 18.2 few-shot 仍然偏轻，尚未形成完整任务型示例体系

当前 `render_prompt_generator` 已经不再是最早期的“单示例轻量提示”。

当前已具备：

1. 类型判断仍以关键词为主，但已覆盖标题类和复合任务关键词
2. 文本改写场景已加入忠实改写正例
3. 文本改写场景已加入忠实改写反例
4. few-shot 已和 `prompts/ppt_editor/` 的版本快照体系形成配合

但它仍然有 3 个明显短板：

1. 复杂复合任务下的类型判断仍偏弱
2. 范围判断（当前页 / 跨页 / 整稿）仍未完全从 prompt 中抽离
3. 示例库仍未达到完整任务矩阵覆盖

因此，当前更准确的描述是：

- 已经形成“轻量动态示例 + 正反例 + 版本快照”的 prompt 体系
- 但距离成熟的 orchestrated few-shot profile 仍有距离

---

## 19. 建议的能力分工

从后续迭代角度，建议按下面方式分工。

### 19.1 继续增强 prompt 的部分

建议继续增强以下 4 类 prompt 能力：

1. 当前页编辑 prompt
2. render schema/example 层
3. few-shot 示例层
4. `ppt_editor` 的能力协议定义

建议重点补强的 prompt 能力包括：

- 当前页重做与整稿重做的语义边界
- 标题类任务的更强 few-shot
- 图表类型选择的 few-shot
- 文本转表格的 few-shot
- 步骤转流程图的 few-shot
- 复合任务的多 command 输出示例
- 更硬的 schema/example 约束

### 19.2 优先 skill 化的部分

建议优先抽出一个统一编排 skill，而不是拆成多个零散 skill。

推荐名称：

- `ppt-orchestrator`

它只负责 5 件事：

1. 判断 route：`ppt_editor / ppt_generator / ask_clarification`
2. 判断 scope：`current_slide / full_deck`
3. 判断上下文是否足够
4. 选择上下文装配策略
5. 选择 few-shot profile

它不负责：

- 直接输出 `render_commands`
- 直接生成 PPT 内容
- 直接做 schema 修复
- 直接做 render 执行

### 19.3 继续留在代码层的部分

建议继续由代码承担：

1. schema 校验
2. `slide_index` 归一化
3. 标题位提升
4. 旧 JSON 兼容
5. 字段轻修复
6. render executor 落地约束

---

## 20. 推荐升级路线图

为了降低风险，建议分 3 个阶段推进。

### 20.1 第一阶段：收口 prompt 边界

目标：

- 先把当前 prompt 的能力边界讲清楚
- 消除 `ppt_editor` 的“整稿重做”误导性表述

建议动作：

1. 收口 `ppt_editor` prompt 中的“全局修改”表述
2. 明确“当前页重做”与“整稿重做”的区别
3. 增强 few-shot 示例库
4. 收紧 schema/example
5. 保持现有后处理逻辑并补强测试

这一阶段的特点是：

- 改动小
- 风险低
- 收益直接

### 20.2 第二阶段：引入编排 skill

目标：

- 把 route/scope/context/few-shot 选择从 prompt 中抽离

建议动作：

1. 新增 `ppt-orchestrator` skill
2. skill 输出结构化 plan
3. runtime 根据 plan 组装执行 prompt
4. 低置信场景支持补问
5. 模糊 case 支持回退和降级

推荐的最小输出结构：

```json
{
  "route": "ppt_editor",
  "scope": "current_slide",
  "need_clarification": false,
  "required_context": [
    "current_slide",
    "adjacent_slides",
    "source_document"
  ],
  "fewshot_profile": [
    "chart_conversion",
    "headline_rewrite"
  ]
}
```

这一阶段的价值是：

- 让 `prompt` 专注于“执行”
- 让 `skill` 专注于“编排”

### 20.3 第三阶段：能力协议中心化

目标：

- 把 `ppt_editor / ppt_generator / chart_convert / content_map` 等能力协议从 UI 和零散模块里进一步收口到统一 runtime

建议动作：

1. 建立能力注册表
2. 建立 few-shot profile 注册表
3. 建立 route policy 配置化机制
4. 逐步减少 UI 侧 prompt 拼装职责
5. 为不同 provider 建立统一能力协议适配层

这一阶段的价值是：

- 长期可维护性更高
- 后续接入更多 agent/provider 更容易

---

## 21. 优先级建议

如果按“必做 / 应该做 / 可以晚点做”来分，我建议如下。

### 21.1 必做

1. 收口 `ppt_editor` 的能力边界
2. 修正文案中“整稿全局修改”的误导性表达
3. 补强 few-shot 中的高频 case
4. 保持并补强后处理兜底

### 21.2 应该做

1. 引入 `ppt-orchestrator` skill
2. 建立结构化 route/scope/context/few-shot plan
3. 增加补问策略
4. 增加可观测性指标

### 21.3 可以晚点做

1. 能力协议中心化
2. provider 无关化的能力注册
3. few-shot profile 的配置化管理
4. 更强的语义路由与多阶段编排

---

## 22. 最终建议

如果只给一句最实用的建议：

- 下一步不要继续把“路由判断、补问、上下文装配、few-shot 选择”继续堆进 `ppt_editor` prompt
- 而应该把这部分逐步抽成 `skill`
- 同时让 `ppt_editor` 继续专注于“当前页编辑执行 prompt”的专业化增强

因此，后续最合理的升级路线是：

1. `ppt_editor` 继续做强
2. `ppt-orchestrator` 开始抽出
3. `后处理` 继续保持在代码层
4. `ppt_generator` 继续承担整稿生成职责

这条路线能最大程度保持当前版本的收益，同时解决后续扩展时最容易失控的边界问题。
