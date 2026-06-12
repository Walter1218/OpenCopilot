# V7 — 复合任务 few-shot 增强

> 迭代时间: 2026-06-11
> 基于: V6 结构保持与条目粒度约束

## 本轮改动

**只改一类策略**：不改 system prompt 规则，只增强 render_prompt_generator 的 few-shot 示例。

### system prompt

与 V6 完全一致，无改动（12 条核心原则保持不变）。

### render_prompt_generator 增强

1. **新增复合任务示例** (`compound_task`)：
   - 同时包含标题改写 + 图表转换 + 文案润色的 render_commands 输出
   - 展示多 command 联合输出的正确格式

2. **新增忠实改写正反例** (`faithful_rewrite_good/bad`)：
   - 正例：保留所有事实锚点的专业改写
   - 反例：事实漂移的错误改写（标注 WHY 错）

3. **新增 headline_rewrite 专项示例**：
   - 正例：结论型标题改写但保留事实锚点（如"2026 H1 营收达 850M，同比增长 32%"）
   - 反例：空泛标题（如"业绩表现亮眼，增长势头强劲"）标注为错误

4. **新增指令类型关键词**：
   - "润色"/"专业化"/"正式"/"汇报" → text 类型
   - "标题"/"换标题" → compound 类型

### 未改动部分

- system prompt 12 条规则保持不变
- 修改模式说明保持不变

## 预期提升

- 复合指令下输出格式更稳定
- 标题改写类 case 的事实锚点保留率上升
- text 类型改写的事实漂移率下降

## 潜在风险

- few-shot 示例增多会增加 prompt 长度和 token 消耗
- 复合任务示例可能对简单指令产生过度引导

## Benchmark 结果

待跑。
