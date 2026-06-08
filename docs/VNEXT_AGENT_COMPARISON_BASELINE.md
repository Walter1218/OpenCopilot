# vNext Agent Comparison Baseline

> 版本 0.1 | 2026-06-08 | 该文档记录“接线前”的历史基线对比，不代表当前系统级正式路由决策

## 1. 目的

在正式把新 Smart Copilot 接到系统级召唤入口之前，先验证两条智能体路径在不同功能模块下的表现：

- `v5 自研智能体`
- `vnext -> hermes_local -> Hermes API Server`

本轮目标不是做严格 benchmark，而是回答三个问题：

1. 哪些模块 Hermes 已经可用
2. 哪些模块 Hermes 可以跑通但体验弱于 `v5`
3. 接入双击右键新入口时，第一阶段应优先暴露哪些能力

注意：

- 当前系统级正式入口已经统一为 `V5 UI -> vnext/Hermes`
- 本文档只保留为“当时为什么先这样接”的历史参考，不应用它覆盖更新的实施文档与验收文档

## 2. 测试方法

使用同一批输入，分别走两条真实路径：

- `v5 自研智能体`：
  `opencopilot.agent.caller.call_agent_pipeline_sync(...)`
- `Hermes`：
  `smart_copilot_api.app -> /vnext/context/snapshots -> /vnext/tasks -> /vnext/tasks/{id}/events`

测试脚本：

- `scripts/compare_agent_modes.py`

输出报告：

- `output/agent_compare_report.json`
- `output/agent_compare_report_ppt.json`

本轮覆盖模块：

- `Chat`
- `Explain`
- `Polish`
- `Code Review`
- `PPT`

评分说明：

- 不是离线模型评分器
- 只做最小可比指标：
  - 是否成功返回
  - 端到端延迟
  - 输出长度
  - 关键词命中
  - 粗粒度质量分（0-5）

## 3. 结果摘要

| 模块 | 路径 | 成功 | 延迟 | 输出长度 | 质量分 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| Chat | `v5_self_agent` | 是 | `4.42s` | `325` | `4.60` | 响应快，适合交互型入口 |
| Chat | `hermes_vnext` | 是 | `15.57s` | `344` | `5.00` | 能用，但首轮响应明显更慢 |
| Explain | `v5_self_agent` | 是 | `9.10s` | `1806` | `5.00` | 解释结构更稳定，适合代码说明 |
| Explain | `hermes_vnext` | 是 | `74.39s` | `5491` | `4.60` | 能完成，但耗时过长，超出浮层期望 |
| Polish | `v5_self_agent` | 是 | `2.61s` | `54` | `2.60` | 短改写足够快 |
| Polish | `hermes_vnext` | 是 | `11.10s` | `74` | `2.60` | 质量相近，但速度劣势明显 |
| Code Review | `v5_self_agent` | 是 | `11.76s` | `2503` | `5.00` | 审查结构和风险表达较完整 |
| Code Review | `hermes_vnext` | 是 | `48.23s` | `2580` | `4.60` | 能跑通，但整体偏慢 |
| PPT | `v5_self_agent` | 是 | `11.16s` | `2084` | `5.00` | 可输出结构化内容，适合 Studio 能力 |
| PPT | `hermes_vnext` | 是 | `36.59s` | `1745` | `5.00` | 能生成大纲，但当前更偏自然语言说明 |

## 4. 关键发现

### 4.1 Hermes 当前更适合作为过渡型通用能力提供者

Hermes 在本轮所有已测模块上都能跑通，说明它适合作为 `vnext` 第一阶段的过渡 provider。

但从交互体验看，Hermes 更适合：

- 通用对话
- 轻量解释
- 轻量润色

不适合直接承担高频、低等待容忍度的浮层入口默认体验，尤其是：

- `Explain`
- `Code Review`
- `PPT`

### 4.2 v5 自研智能体在分析型和结构化模块上更稳定

`v5 自研智能体` 在以下模块更有优势：

- `Explain`
- `Code Review`
- `PPT`

优势不只在速度，也在输出形态：

- 更容易形成标题、列表、分层结构
- 更贴近当前产品对代码解释和审查的预期
- `PPT` 路径已经更接近结构化产物，而不是纯自然语言建议

### 4.3 Hermes 的主要问题不是“不能用”，而是“交互等待过长”

本轮最明显问题不是失败率，而是延迟：

- `Chat`：`15.57s`
- `Explain`：`74.39s`
- `Code Review`：`48.23s`
- `PPT`：`36.59s`

对于双击右键召唤类入口，这个等待时间过长，会直接影响用户主观可用性。

## 5. 接入建议

基于本轮结果，需要区分“基线认知”和“当前接入决策”。

### 5.1 双击右键新入口第一阶段

基线结论仍然成立：

- `Polish`
- `轻量 Explain`
- `基础 Chat / Follow-up`

这些能力在 Hermes 上的主观等待成本更低，更适合作为体验基线样本。

### 5.2 暂缓把以下能力完全切到 Hermes

- `Code Review`
- `PPT / Studio`
- 复杂 `Explain`

这些模块在本轮对比中仍然表现出明显的延迟劣势，属于后续需要重点优化的风险点。

### 5.3 更合理的阶段性策略

当前项目决策已经更新为：

- 系统级入口继续使用 `V5 UI`
- 底层智能体执行统一切到 `Hermes`
- 不再按模块做 provider 分流

因此，本节的作用不再是“决定是否分流”，而是给出统一走 Hermes 后的风险排序：

- `Chat / Polish`：可作为日常回归样本
- `Explain`：需要重点盯首条结果时延
- `Code Review / PPT / Studio`：需要重点盯长耗时和结构化输出质量

## 6. 当前结论

当前可执行结论是：

- 可以继续推进并验证 `V5 UI -> vnext/Hermes` 系统级入口
- Hermes 仍然是第一阶段的过渡型 provider
- 不再采用“部分能力走 Hermes、部分能力走自研”的入口分流策略
- 后续优化重点转为时延治理、结构化结果质量和整机交互体验
