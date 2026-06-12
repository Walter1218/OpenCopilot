# V4 Baseline — 当前生产版本快照

> 快照时间: 2026-06-11
> 来源: opencopilot/shared/prompt.py + opencopilot/capabilities/ppt/render_prompt_generator.py

## 版本说明

V4 是当前生产版本，特征为「动态 few-shot + 强规则」：

- system prompt 从 UI 内联迁移到统一 `ppt_editor` context
- 用户上下文从全量 slides 收缩为当前页中心
- render_commands 从可选补充升级为推荐主输出
- 当前页命中和标题位命中变成明确硬约束（7 条核心原则）
- few-shot 从静态 JSON 升级为按任务类型动态生成（chart/table/flowchart/text）

## SCORE 结构对应

| 结构 | 覆盖情况 |
|------|----------|
| Situation | 当前页完整 JSON + 前后页摘要 |
| Character | 专业 PPT 编辑助手 |
| Objective | 根据指令选择最精准修改模式 |
| Rules | 7 条硬约束（精准操作/信息量/结构化/可视化/排版/当前页/标题位） |
| Example | 按 chart/table/flowchart/text 动态 few-shot |

## 已知局限

1. 无事实锚点保留硬约束
2. 无计划/结果区分约束
3. 无风险/负面信息保留约束
4. 无条目数量和顺序保持约束
5. text 类型 few-shot 仅 1 个简单示例，无忠实改写正反例
6. 无复合任务 few-shot 示例
7. 无 headline_rewrite 专项示例

## Benchmark 结果

待跑（Task 2）。
