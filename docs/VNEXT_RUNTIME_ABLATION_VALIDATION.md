# vNext Runtime Validation

> 更新时间：2026-06-11
> 范围：`self_hosted` 编排执行器、统一 Task/Event 流、同输入消融验证

## 1. 本次落地内容

本次改造将 `B` 路线收敛到现有功能模块下，核心变化如下：

- `Agent Gateway` 新增 `self_hosted` provider
- `auto` provider 选择策略落地
  - 文本类任务默认走 `self_hosted`
  - `ppt` 默认仍走 `hermes_local`
- 自研 runtime 增加实验开关
  - `disable_planner`
  - `disable_context_prefix`
  - `disable_tools_prompt`
  - `disable_persona_prompt`
  - `disable_history`
  - `disable_session_memory`
- `Task/Event/Result` 统一由 vnext runtime 对外暴露

## 2. 关键验证点

### 2.1 统一任务链路

需要验证的最小闭环：

1. `POST /vnext/context/snapshots`
2. `POST /vnext/tasks`
3. provider 自动选择
4. `task.stage_changed`
5. `task.delta`
6. `task.completed`
7. `GET /vnext/tasks/{id}` 返回统一结果

### 2.2 自研链路可控消融

同一输入下比较：

- 完整编排
- 关闭 planner
- 关闭 context prefix
- 关闭 history

目标不是追求单项绝对分数，而是验证：

- runtime 编排是否可被独立打开/关闭
- 质量评分脚本能否稳定反映增益方向
- 自研智能体在不同 runtime 组件打开/关闭下的质量变化

### 2.3 Complex Text Answer-First 护栏

文件：`opencopilot/agent/middlewares.py`

针对复杂文本类任务新增 `answer-first` 策略，主要覆盖：

- 复杂方案设计
- 复杂代码审查
- 长文档冲突梳理与重写

策略行为：

- 复杂度命中且属于直接交付型任务时，注入内部系统指令
- 强制模型本轮直接输出最终答案，而不是展示工具调用、搜索计划或中间推理
- 默认关闭该类任务的 web search，避免无必要联网干扰
- 明确要求模型基于当前 prompt 与上下文直接完成，不要伪造“先查文件/先查知识库”的动作

验证目标：

- 修复 `self_hosted_full` 在复杂文本任务上偏向工具化输出的问题
- 让 planner 更像“答案结构约束器”，而不是“副作用触发器”

## 3. 已补充的测试

### 3.1 单元测试

文件：`tests/unit/test_vnext_self_hosted_flow.py`

覆盖点：

- `auto` provider 选择
- `self_hosted` 统一任务流
- stage/delta/completed 事件
- runtime flags 透传到自研链路

### 3.2 消融评测脚本

文件：`tests/e2e/test_vnext_runtime_ablation.py`

输出：

- 逐 case 总分、规则分、Embedding 相似度、语义相似分、描述准确性分
- `LLM Judge` 语义裁判分与简要评语
- 各 variant 平均得分
- `self_hosted_full` 相对各消融 variant 的质量差值

任务模式：

- 默认 `complex`
  - 复杂代码审查与修复方案
  - 多约束方案设计
  - 长文档冲突梳理与重写
- 可切回 `simple`
  - 轻量代码解释
  - 轻量代码审查

评分体系：

- `rule_score`
  - 长度、关键词覆盖、步骤结构等启发式指标
- `embedding_similarity`
  - 优先使用 `sentence-transformers` 句向量余弦相似度
  - 若本地未安装该依赖，则回退到项目内置 `hash embedding` 余弦相似度
- `semantic_similarity`
  - `embedding_similarity` 与 token overlap、char n-gram、sequence ratio 的组合分
- `description_accuracy`
  - 参考答案与候选输出的一致性代理分
- `judge_score`
  - 由当前默认 LLM provider 执行的裁判分
- `overall_score`
  - 对以上指标做加权后的综合质量分

报告默认写入：

- `output/vnext_runtime_ablation_report.md`

## 4. 运行方式

### 4.1 单元测试

```bash
pytest tests/unit/test_vnext_self_hosted_flow.py
```

### 4.2 消融实验

```bash
python tests/e2e/test_vnext_runtime_ablation.py
```

可选环境变量：

```bash
OPEN_COPILOT_ABLATION_TASK_MODE=complex
OPEN_COPILOT_ENABLE_LLM_JUDGE=1
OPEN_COPILOT_LLM_JUDGE_MAX_CASES=12
OPEN_COPILOT_EMBEDDING_BACKEND=auto
OPEN_COPILOT_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 4.3 共创质量评测

```bash
python tests/e2e/test_ppt_cocreation_quality_benchmark.py
```

当前共创评测已支持：

- 结构/类型/当前页命中规则分
- Embedding 相似度
- 语义相似分
- 描述准确性代理分
- 抽样 `LLM Judge` 质量裁判
- 默认仅跑 `self_agent`，可通过环境变量扩展到多后端对照
- 默认 `complex` 指令池，覆盖跨页、复合指令、多约束共创
- `faithful_rewrite` 固定数据集模式，专门评测“专业化且保事实”的忠实改写能力
- `ppt_editor` 直编护栏：默认关闭搜索与通用工具提示，要求直接输出可执行编辑结果
- `F_polish` 专项提示：对文案润色类指令明确要求逐条压缩、保数字/专名/因果、保持顺序并直接输出 render_commands

推荐环境变量：

```bash
OPEN_COPILOT_PPT_TASK_MODE=complex
OPEN_COPILOT_PPT_BENCH_BACKENDS=self_agent
OPEN_COPILOT_PPT_BENCH_SEEDS=42
OPEN_COPILOT_PPT_SAMPLES_PER_ROUND=1
# 如需做 A/B 对比，可显式关闭直编护栏
OPEN_COPILOT_DISABLE_PPT_DIRECT_EDIT_GUARD=1
```

忠实改写专项补充资料：

- 规范：`docs/PPT_FAITHFUL_REWRITE_BENCHMARK_SPEC.md`
- 数据集：`tests/test_data/ppt_faithful_rewrite_cases.json`
- 模式：`OPEN_COPILOT_PPT_TASK_MODE=faithful_rewrite`

## 5. 当前边界

本次已经把 runtime 真源从“provider 透传”推进到“统一编排 + 统一事件 + 可控消融 + 语义质量评测”，但仍有两个后续增强点：

- `self_hosted` 当前仍桥接既有自研 pipeline，而非完全独立的 step executor
- 当前 embedding 采用“`sentence-transformers` 优先、`hash embedding` 回退”的渐进式实现；若需要更高可信度，后续可继续接入更强句向量模型 / BERTScore / 人审抽样
- 复杂 chat 任务的状态跟踪兼容问题已修复；后续应继续补步骤级进度推进与失败重规划验证
- `answer-first` 当前仍基于规则判断触发，后续可继续升级为更稳定的任务类型判定与 planner 输出约束
- `ppt_editor` 直编护栏当前更明显提升页命中与类型匹配，对平均质量分的抬升仍需继续验证
- `F_polish` 专项提示在同种子复杂共创回归下未明显抬升文案润色均分，但提升了页命中、延迟与部分 case 的准确性
