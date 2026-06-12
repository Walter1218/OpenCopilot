# PPT Prompt 迭代对比报告

**生成时间**: 2026-06-11
**迭代范围**: V4 Baseline → V5 事实锚点 → V6 结构保持 → V7 复合任务
**评测方式**: 12 个固定 case 忠实改写 benchmark（LLM Judge + 规则分 + Embedding + 语义分）

---

## 1. 版本概览

| 版本 | 策略变更 | 改动文件 |
|------|---------|---------|
| V4 Baseline | 动态 few-shot + 7 条核心规则 | prompt.py (rules 1-7) |
| V5 事实锚点 | 新增规则 8/9/10（事实锚点/计划结果区分/风险不可弱化）| prompt.py + render_prompt_generator.py |
| V6 结构保持 | 新增规则 11/12（条目数量顺序不变/区间不可单点化）+ 忠实改写正反例 | prompt.py + render_prompt_generator.py |
| V7 复合任务 | 不改 system prompt，新增 compound 类型关键词 + 复合任务 few-shot 示例 | render_prompt_generator.py |

---

## 2. 核心指标对比

| 指标 | V4 Baseline | V5 事实锚点 | V6 结构保持 | V7 复合任务 |
|------|------------|------------|------------|------------|
| **质量均分** | **85.1** ✅ | 84.1 | 83.7 | 81.9 |
| **当前页命中** | **92%** | 83% | 83% | 75% |
| **平均延迟** | **10169ms** | 11582ms (+14%) | 20290ms (+99%) | 11299ms (+11%) |
| **规则分** | **96.5** | 95.4 | 94.4 | 93.1 |
| **Embedding** | 96.7 | 97.0 | **97.6** | 97.8 |
| **语义分** | 59.3 | 60.2 | 59.6 | **60.1** |
| **准确性** | 81.2 | **84.5** | 81.7 | 82.0 |

> ⚠️ 所有版本 current_page_hit 均未达到 95% 准入门槛。V4 最接近（92%）。

---

## 3. 逐条 case 得分对比

| Case ID | 标签 | V4 | V5 | V6 | V7 | 趋势 |
|---------|------|-----|-----|-----|-----|------|
| fr_001 | 数字与术语保留 | 83.4 | **87.6** | 71.3 | 82.9 | V5最优, V6回归 |
| fr_002 | 计划与结果区分 | 86.6 | 87.5 | **88.0** | 87.4 | 稳定 |
| fr_003 | 因果关系保留 | **88.1** | 88.5 | 84.1 | 85.7 | V5最优 |
| fr_004 | 风险提示不可弱化 | 71.7 | **85.3** | 85.6 | **87.6** | 持续改善 ✅ |
| fr_005 | 顺序与粒度保持 | 82.6 | **83.1** | 83.2 | 69.0 | V7严重回归 ❌ |
| fr_006 | 专有名词与英文缩写 | 87.6 | 86.6 | 86.1 | **88.0** | 稳定 |
| fr_007 | 对比关系保留 | **88.0** | 86.4 | 86.7 | **88.0** | 稳定 |
| fr_008 | 范围与区间保留 | **83.9** | 68.4 | 85.0 | 77.7 | V5回归, V6恢复 |
| fr_009 | 结论句但保事实锚点 | 87.3 | **88.0** | 71.6 | 87.6 | V6回归, V7恢复 |
| fr_010 | 多约束忠实压缩 | 89.1 | **92.3** | 91.5 | 71.7 | V7严重回归 ❌ |
| fr_011 | 负面信息保留 | 87.2 | 76.1 | **88.1** | 88.4 | V5回归, V6恢复 |
| fr_012 | 组织名与角色保留 | 86.3 | 79.1 | 83.3 | 68.7 | 持续下降 ❌ |

---

## 4. 高风险 case 分析

### fr_005 顺序与粒度保持 — V7 严重回归 (82.6→69.0, -13.6)
- V7 新增的 compound 类型关键词可能干扰了 text 类型的条目数量保持约束
- 模型在处理 "保持原有条目数量" 时，可能因 few-shot 示例中的复合任务展示了不同的条目处理方式而混淆

### fr_010 多约束忠实压缩 — V7 严重回归 (89.1→71.7, -17.4)
- 该 case 要求同时保留数字、计划/结果区分、风险等多项约束
- V7 的 compound 示例增加了 prompt 复杂度，可能稀释了模型对多重约束的注意力

### fr_012 组织名与角色保留 — 持续下降 (86.3→68.7, -17.6)
- 从 V4 到 V7 持续恶化，说明每轮迭代对该 case 都有负面影响
- 可能原因：规则越来越多，模型对 "保留组织名和角色" 这一相对简单约束的注意力被稀释

### fr_004 风险提示不可弱化 — 持续改善 ✅ (71.7→87.6, +15.9)
- 唯一持续改善的 case，说明事实锚点规则对风险保留有正向作用

---

## 5. 延迟变化趋势

```
V4: 10169ms ██████████
V5: 11582ms ███████████▌  (+14%)
V6: 20290ms ████████████████████  (+99%)
V7: 11299ms ███████████▎  (+11%)
```

- V6 延迟翻倍是因为 render_prompt_generator 新增了大量忠实改写正反例和约束文本
- V7 延迟回落但仍高于 V4 baseline

---

## 6. 准入门槛评估

| 门槛指标 | 要求 | V5 vs V4 | V6 vs V5 | V7 vs V6 |
|---------|------|----------|----------|----------|
| 质量均分 >= 上一版 | ✅/❌ | ❌ (84.1 < 85.1) | ❌ (83.7 < 84.1) | ❌ (81.9 < 83.7) |
| 数字保留 case 无 P0 回归 | ✅/❌ | ✅ | ❌ (fr_001 -16.3) | ✅ |
| 计划/结果区分 无 P0 回归 | ✅/❌ | ✅ | ✅ | ✅ |
| 风险保留 无 P0 回归 | ✅/❌ | ❌ (fr_011 -11.1) | ✅ | ✅ |
| current_page_hit >= 95% | ✅/❌ | ❌ (83%) | ❌ (83%) | ❌ (75%) |
| 延迟增幅 <= 15% | ✅/❌ | ✅ (+14%) | ❌ (+99%) | ✅ (+11%) |

**结论：V5/V6/V7 均未通过准入门槛。**

---

## 7. 最终结论

### 推荐版本：**V4 Baseline** (保持现状)

**理由**：
1. **质量最高**：85.1 分，四个版本中最优
2. **当前页命中最高**：92%，最接近 95% 门槛
3. **延迟最低**：10169ms
4. **规则分最高**：96.5，说明模型对核心规则的遵循最好
5. 所有迭代版本均未能通过准入门槛，每轮改动都导致了某些 case 的回归

### 改进方向建议：
1. **当前页约束需专项强化**：所有版本的 page_hit 都未达 95%，这是共性问题
2. **规则数量控制在 7 条以内**：V5/V6 新增的规则稀释了模型注意力
3. **few-shot 示例精简**：V6/V7 的示例增多反而导致延迟增加和质量下降
4. **fr_012 组织名保留需专项修复**：该 case 在所有版本中持续恶化

---

## 8. 回滚指南

### 回滚到 V4 Baseline（推荐）：

```bash
# 1. 恢复 system prompt
cp prompts/ppt_editor/v4_baseline/system_prompt.py opencopilot/shared/prompt.py

# 2. 恢复 render_prompt_generator
cp prompts/ppt_editor/v4_baseline/render_prompt.py opencopilot/capabilities/ppt/render_prompt_generator.py
```

### 回滚到任意版本：

```bash
# 查看可用版本
ls prompts/ppt_editor/

# 复制到生产路径（替换 <version> 为目录名）
cp prompts/ppt_editor/<version>/system_prompt.py opencopilot/shared/prompt.py
cp prompts/ppt_editor/<version>/render_prompt.py opencopilot/capabilities/ppt/render_prompt_generator.py
```

### 版本目录结构：

```
prompts/ppt_editor/
  __init__.py                -- 版本管理入口
  v4_baseline/               -- 推荐生产版本
    system_prompt.py
    render_prompt.py
    CHANGELOG.md
    benchmark_result.md
  v5_fact_anchor/            -- 第一轮迭代（事实锚点）
    system_prompt.py
    render_prompt.py
    CHANGELOG.md
    benchmark_result.md
  v6_structure/              -- 第二轮迭代（结构保持）
    system_prompt.py
    render_prompt.py
    CHANGELOG.md
    benchmark_result.md
  v7_compound_task/          -- 第三轮迭代（复合任务）
    system_prompt.py
    render_prompt.py
    CHANGELOG.md
    benchmark_result.md
  ITERATION_REPORT.md        -- 本报告
```
