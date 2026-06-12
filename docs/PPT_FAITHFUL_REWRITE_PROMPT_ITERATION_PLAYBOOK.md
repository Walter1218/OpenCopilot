# PPT 忠实改写 Prompt 迭代手册

> 更新时间：2026-06-11
> 范围：`self_agent` / `ppt_editor` / `F_polish` / `OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`

## 1. 这份文档回答什么问题

这份文档只回答 4 个问题：

1. 现在是否已经具备进入 `prompt` 迭代的条件
2. 当前固定 benchmark、测试集和准入门槛是什么
3. 每轮 `prompt` 迭代应该怎么跑、怎么比、怎么决定是否保留
4. 当前还有哪些已知边界，不能误判为“已经完全验证”

结论先说：

- 当前已经具备进入 `prompt` 迭代的基础条件
- 但必须以 `faithful_rewrite` 固定 benchmark 作为回归门槛
- 不允许脱离固定 case 只凭单条样本或主观感觉决定 prompt 好坏

---

## 2. 当前已落地的基础设施

### 2.1 评测规范

- 文档：`docs/PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md`
- 作用：定义忠实改写的能力边界、评分维度、测试集设计原则、准入门槛

当前固定的 4 个一级维度：

- `Fact Retention`
- `Structure Preservation`
- `Professional Expression`
- `Hallucination Control`

建议权重：

- `Fact Retention`: `35%`
- `Structure Preservation`: `20%`
- `Professional Expression`: `20%`
- `Hallucination Control`: `25%`

### 2.2 固定测试集

- 文件：`tests/test_data/ppt_faithful_rewrite_cases.json`
- 当前规模：`12` 个固定 case
- 当前类别：`F_polish`

当前已覆盖的高风险点：

1. 数字保留
2. 专有名词保留
3. 计划/结果区分
4. 风险与限制保留
5. 因果关系保留
6. 顺序与粒度保持
7. 区间与范围保留
8. 结论句式但保事实锚点
9. 负面信息保留
10. 组织名与角色保留

### 2.3 Benchmark 入口

- 主入口：`tests/e2e/test_ppt_cocreation_quality_benchmark.py`
- 模式开关：`OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`

当前模式行为：

- 不再随机抽样复杂共创指令
- 固定读取忠实改写数据集
- 固定构造同一批 case
- 适合作为 `prompt v1 / v2 / v3` 的可比回归基线

### 2.4 基础验证

已完成的最小验证：

- `tests/unit/test_ppt_faithful_rewrite_benchmark.py` 已通过
- `faithful_rewrite` 模式可正确加载固定数据集
- 当前可稳定构造 `12` 个固定样本，首尾 case 为 `fr_001 ~ fr_012`
- 新增专项相关文件当前无诊断报错

这说明：

- 这套专项能力已经不是“只有文档和想法”
- 而是已经具备了最小可执行、可回归、可比较的工程入口

---

## 3. 当前结论

当前可以进入 `prompt` 迭代，但要按以下口径执行：

### 3.1 可以做的事

- 继续迭代 `F_polish` 相关 prompt
- 比较不同 prompt 版本在忠实改写专项上的增益
- 以固定 benchmark 做版本准入

### 3.2 不可以做的事

- 不要只看单条 case 就替换默认 prompt
- 不要把“表达更专业”当成牺牲事实精度的理由
- 不要把随机复杂共创报告当作忠实改写专项准入结果
- 不要在没有回归数据的情况下直接覆盖线上默认策略

---

## 4. 每轮 Prompt 迭代的标准流程

建议每一轮都严格遵守以下闭环：

### Step 1. 明确本轮只优化一个目标

示例：

- 保留每条文案中的事实锚点
- 强化计划态与完成态区分
- 防止风险提示被弱化成积极表述
- 保持条目顺序和粒度不变

### Step 2. 只改一类 prompt 策略

示例：

- 增加“每条至少保留一个事实锚点”的硬约束
- 增加“不得将计划、预测、目标改写为已完成结果”的硬约束
- 增加“风险、限制、不确定性必须显式保留”的硬约束

不要在同一轮混改多类策略，否则很难判断增益来源。

### Step 3. 固定跑忠实改写专项 benchmark

推荐命令：

```bash
OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite \
OPEN_COPILOT_ENABLE_LLM_JUDGE=1 \
OPEN_COPILOT_LLM_JUDGE_MAX_CASES=12 \
OPEN_COPILOT_PPT_BENCH_BACKENDS=self_agent \
python tests/e2e/test_ppt_cocreation_quality_benchmark.py
```

### Step 4. 观察 4 类结果

每轮至少看这 4 类结果：

1. 专项平均分是否上升
2. 高风险 case 是否出现回归
3. 平均延迟是否异常上升
4. 是否伤害其他 PPT 共创类别

### Step 5. 决定是否保留为候选版本

只有满足以下条件，才进入下一步：

- 专项均分不低于上一版
- 高风险 case 没有明显回归
- 当前页命中率保持稳定
- 输出类型匹配保持稳定

---

## 5. 准入门槛

建议把以下条件作为 `prompt` 升级准入标准：

- `faithful_rewrite` 平均分不低于上一版
- `计划/结果区分`、`风险保留`、`数字保留` 三类 case 不允许出现 `P0` 回归
- `current_page_hit >= 95%`
- 平均延迟增幅不超过 `15%`
- 抽样 `LLM Judge` 结论中不能出现集中性的事实漂移或结构破坏

如果不满足以上条件，即使文风更“高级”，也不能作为升级版本。

---

## 6. 当前建议的版本管理方式

建议从现在开始固定以下版本节奏：

### 6.1 版本命名

- `faithful_rewrite_prompt_v1`
- `faithful_rewrite_prompt_v2`
- `faithful_rewrite_prompt_v3`

### 6.2 每轮必须记录的信息

- 本轮改了什么
- 预期提升什么
- 哪些 case 明显变好
- 哪些 case 出现回归
- 是否影响其他共创类别

### 6.3 建议产出物

- 一份专项 benchmark 报告
- 一份 before/after 对比摘要
- 一份是否准入的结论

---

## 7. 当前已知边界

当前虽然已经具备进入迭代的条件，但还需要明确以下边界：

- 当前已完成的是“最小可执行验证”，不是所有 case 的正式基线归档
- 后续应补一份 `faithful_rewrite` 专项首版基线报告，作为后续所有 prompt 对比的 `v0 baseline`
- 当前自动指标已能做代理判断，但后续仍建议补充更专项的自动指标：
  - `fact_anchor_coverage`
  - `structure_keep_rate`
  - `risk_retention_rate`
  - `hallucination_rate`

这意味着：

- 可以开始做 prompt 迭代
- 但后续每轮都要继续把基线、回归和专项报告补齐

---

## 8. 推荐的下一步

最推荐的下一步不是继续泛泛讨论，而是直接进入第一轮专项 prompt 迭代：

1. 先定义 `v1 -> v2` 只改一类约束
2. 产出首份 `faithful_rewrite` 基线报告
3. 做同一批 `12` 个 case 的前后对比
4. 按准入门槛判断是否保留

---

## 9. 一句话结论

当前围绕“专业化且保事实”的：

- 评测标准
- 固定测试集
- benchmark 入口
- 最小验证

都已经具备。

因此，当前已经进入 `可验证、可回归、可比较` 的 prompt 迭代阶段。
