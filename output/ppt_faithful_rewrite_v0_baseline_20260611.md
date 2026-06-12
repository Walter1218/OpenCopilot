# PPT Faithful Rewrite v0 Baseline

> 更新时间：2026-06-11
> 目标：冻结 `faithful_rewrite` 专项在当前代码状态下的首版正式基线，作为后续 prompt 迭代的固定对比参照。
> 基线代码：`func-reform-v3` / commit `68f311f`

## 1. 基线范围

- 后端：`self_agent`
- 任务模式：`OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`
- 数据集：`tests/test_data/ppt_faithful_rewrite_cases.json`
- 样本规模：`12` 个固定 case
- LLM Judge：`enabled`，`max_cases=12`
- 原始报告快照：[ppt_faithful_rewrite_v0_raw_20260611.md](file:///Users/onetwo/Documents/trae_projects/OpenCopilot/output/ppt_faithful_rewrite_v0_raw_20260611.md)

## 2. 运行配置

```bash
OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite \
OPEN_COPILOT_ENABLE_LLM_JUDGE=1 \
OPEN_COPILOT_LLM_JUDGE_MAX_CASES=12 \
OPEN_COPILOT_PPT_BENCH_BACKENDS=self_agent \
python tests/e2e/test_ppt_cocreation_quality_benchmark.py
```

## 3. 总体结果

| 指标 | 数值 |
|------|------|
| 成功率 | 100% |
| 平均质量 | 83.8 |
| 规则分 | 94.8 |
| Embedding | 97.7 |
| 语义分 | 59.9 |
| 准确性 | 82.3 |
| Judge 覆盖 | 100% |
| 当前页命中 | 83% |
| 类型匹配 | 100% |
| 平均延迟 | 8503ms |

## 4. PPT 初始生成前置结果

- 初始生成状态：全部成功
- `AI Agent 技术报告`: 成功，8 页，延迟 `58873ms`
- `产品商业计划书`: 成功，8 页，延迟 `68890ms`

## 5. 全量 Case 明细

| Case | 标签 | Focus | 质量 | 规则分 | 语义分 | 准确性 | Judge | 延迟 |
|------|------|-------|------|--------|--------|--------|-------|------|
| fr_001 | 数字与术语保留 | fact_retention, professional_expression | 84.5 | 92.5 | 58.6 | 83.2 | 100.0 | 10430ms |
| fr_002 | 计划与结果区分 | fact_retention, hallucination_control | 74.7 | 80.0 | 59.9 | 86.9 | 91.0 | 9009ms |
| fr_003 | 因果关系保留 | fact_retention, structure_preservation | 85.9 | 100.0 | 57.7 | 81.6 | 83.0 | 7979ms |
| fr_004 | 风险提示不可弱化 | fact_retention, hallucination_control | 87.3 | 100.0 | 59.0 | 84.0 | 94.0 | 7973ms |
| fr_005 | 顺序与粒度保持 | structure_preservation, professional_expression | 83.5 | 92.5 | 57.0 | 81.3 | 96.0 | 7310ms |
| fr_006 | 专有名词与英文缩写 | fact_retention, professional_expression | 85.8 | 100.0 | 55.8 | 77.7 | 99.0 | 7376ms |
| fr_007 | 对比关系保留 | fact_retention, hallucination_control | 88.0 | 100.0 | 59.9 | 85.4 | 97.0 | 7829ms |
| fr_008 | 范围与区间保留 | fact_retention, hallucination_control | 85.3 | 92.5 | 59.8 | 87.0 | 98.0 | 9591ms |
| fr_009 | 结论句但保事实锚点 | fact_retention, professional_expression | 72.2 | 80.0 | 56.7 | 80.8 | 80.0 | 9147ms |
| fr_010 | 多约束忠实压缩 | fact_retention, structure_preservation, professional_expression | 90.1 | 100.0 | 76.9 | 74.5 | 100.0 | 6533ms |
| fr_011 | 负面信息保留 | fact_retention, hallucination_control | 88.2 | 100.0 | 60.2 | 85.6 | 99.0 | 8518ms |
| fr_012 | 组织名与角色保留 | fact_retention, professional_expression, hallucination_control | 80.6 | 100.0 | 57.6 | 79.9 | 0.0 | 10340ms |

## 6. Top 3 Case

- `fr_010` / 多约束忠实压缩: 质量 `90.1`，准确性 `74.5`，Judge `100.0`，摘要：输出完全符合指令，以更简洁的汇报口吻准确保留了所有关键数值事实。
- `fr_011` / 负面信息保留: 质量 `88.2`，准确性 `85.6`，Judge `99.0`，摘要：完美完成指令，保留所有负面信息并提升专业度，仅在呈现清晰度上略有优化空间。
- `fr_007` / 对比关系保留: 质量 `88.0`，准确性 `85.4`，Judge `97.0`，摘要：完美保留所有具体增长数据与对比关系，指令执行到位，表达清晰。

## 7. Bottom 3 Case

- `fr_012` / 组织名与角色保留: 质量 `80.6`，准确性 `79.9`，Judge `0.0`，摘要：输出完全未执行指令，未改写内容，仅重复了参考文本。
- `fr_002` / 计划与结果区分: 质量 `74.7`，准确性 `86.9`，Judge `91.0`，摘要：改写基本符合董事会汇报风格，清晰区分了已完成与计划中事项，但部分表述可更精炼。
- `fr_009` / 结论句但保事实锚点: 质量 `72.2`，准确性 `80.8`，Judge `80.0`，摘要：基本完成指令，但部分文案未完全改为结论句式，事实锚点保留较好。

## 8. 当前基线解读

- 当前 `v0 baseline` 说明：在固定 `12` 个忠实改写 case 下，系统整体均分为 `83.8`，可作为后续 prompt 版本对比的零号参照。
- `当前页命中` 为 `83%`，`类型匹配` 为 `100%`，说明当前 runtime 护栏已能较稳定地把输出收口到 PPT 当前页编辑任务。
- `准确性` 当前为 `82.3`，仍明显低于规则分，说明系统已经具备结构稳定性，但在“忠实执行具体改写约束”上仍有优化空间。
- Bottom 3 case 应被视为后续 prompt 迭代的重点回归样本，任何新 prompt 都不应让这些 case 再进一步下滑。

## 9. 使用规则

- 后续 `prompt v1 / v2 / v3` 对比必须使用同一批 `12` 个 case，不得替换样本。
- 新版本至少同时对比：平均质量、准确性、高风险 case 回归、平均延迟。
- 若 `计划/结果区分`、`风险保留`、`数字保留` 三类 case 出现 `P0` 回归，则新 prompt 不准入。
- 若需更新基线，必须新增 `v1 baseline` 或新日期快照，不覆盖本文件。

## 10. 结论

- 这份报告冻结了当前实现下 `faithful_rewrite` 专项的首版正式基线。
- 从现在开始，所有 PPT 忠实改写 prompt 迭代，都应以本报告作为固定对比参照。
