# vNext Runtime Orchestrator 自研消融报告

- 生成时间: 2026-06-11 12:02:46
- Base URL: http://127.0.0.1:8010
- Task Mode: complex
- LLM Judge: enabled / max_cases=12
- Embedding Backend: auto

## 复杂代码审查与修复方案

| Variant | Success | Latency(ms) | Overall | Rule | Embed | Semantic | Accuracy | Judge | Preview |
|---------|---------|-------------|---------|------|-------|----------|----------|-------|---------|
| self_hosted_full | Y | 31243.4 | 50.4 | 92.5 | 36.1 | 32.0 | 12.5 | 96.0 | # 代码深度审查报告  ## 1. 高优先级问题排序  | 优先级 | 问题类型 | 严重程度 | 问题描述 | |--------|----------|-- |
- `self_hosted_full` Embedding: hash_embedding_fallback
- `self_hosted_full` Judge: 报告严格按指令四步完成，识别了所有关键问题，重构方案全面，代码与测试示例详实。
| self_hosted_no_planner | Y | 34783.3 | 50.0 | 92.5 | 39.0 | 32.8 | 12.9 | 90.0 | # 代码深度审查报告  ## 1. 核心功能总结 该代码实现了一个简单的用户配置文件缓存系统，包含两个主要功能： - `get_profile`: 根据用户ID |
- `self_hosted_no_planner` Embedding: hash_embedding_fallback
- `self_hosted_no_planner` Judge: 基本完成指令，结构清晰，但部分细节与参考文本略有偏差。
| self_hosted_no_context | Y | 33995.5 | 49.3 | 92.5 | 32.0 | 30.4 | 11.4 | 94.0 | # 代码深度审查报告  ## 1. 核心功能总结 该代码实现了一个基于线程的用户配置文件缓存预热机制，主要功能包括： - 通过 `get_profile` 函数 |
- `self_hosted_no_context` Embedding: hash_embedding_fallback
- `self_hosted_no_context` Judge: 深度审查报告结构完整，问题分析准确，重构方案落地性强，代码与测试覆盖核心要点。
| self_hosted_no_history | Y | 39080.3 | 50.4 | 92.5 | 39.6 | 32.2 | 12.2 | 96.0 | 我将对提供的代码进行深度审查，按照您要求的四步完成分析。  ## 代码深度审查结果  ### 1. 高优先级问题（按严重程度排序）  | 优先级 | 问题类型  |
- `self_hosted_no_history` Embedding: hash_embedding_fallback
- `self_hosted_no_history` Judge: 全面完成指令，问题识别准确，重构方案详实，代码与测试完整。

## 多约束方案设计

| Variant | Success | Latency(ms) | Overall | Rule | Embed | Semantic | Accuracy | Judge | Preview |
|---------|---------|-------------|---------|------|-------|----------|----------|-------|---------|
| self_hosted_full | Y | 17390.9 | 58.0 | 100.0 | 53.4 | 44.3 | 19.3 | 94.0 | ### 1. 核心约束与冲突拆解  **核心约束：** *   **安全红线**：内网部署，原始代码与客户数据严禁外泄。 *   **性能指标**：单次复杂任务 |
- `self_hosted_full` Embedding: hash_embedding_fallback
- `self_hosted_full` Judge: 方案B选择合理，结构完整，基本符合要求，但部分细节与参考文本略有偏差。
| self_hosted_no_planner | Y | 32689.7 | 53.7 | 93.6 | 51.5 | 37.7 | 15.5 | 98.0 | # 智能体接入企业知识库与代码库：可执行实施方案  ## 1. 核心约束与冲突拆解  ### 核心约束 | 约束类型 | 具体要求 | 优先级 | |----- |
- `self_hosted_no_planner` Embedding: hash_embedding_fallback
- `self_hosted_no_planner` Judge: 方案完全符合指令，结构清晰，内容详实，准确反映了参考文本的核心思想。
| self_hosted_no_context | Y | 17706.5 | 56.8 | 100.0 | 45.2 | 41.9 | 17.9 | 94.0 | ## 1. 核心约束与冲突拆解  **硬约束：** - **数据安全**：原始代码和客户数据严禁出内网，必须本地化部署大模型。 - **时效性**：复杂任务时延 |
- `self_hosted_no_context` Embedding: hash_embedding_fallback
- `self_hosted_no_context` Judge: 方案完整满足指令要求，结构清晰，内容准确，仅在数据脱敏细节上略有扩展。
| self_hosted_no_history | Y | 35078.2 | 55.9 | 100.0 | 48.2 | 39.8 | 14.9 | 98.0 | # 智能体接入企业知识库与代码库 - 可执行实施方案  ## 1. 核心约束与冲突分析  ### 核心约束 | 约束维度 | 具体要求 | |--------- |
- `self_hosted_no_history` Embedding: hash_embedding_fallback
- `self_hosted_no_history` Judge: 方案完整覆盖指令要求，架构选型与参考一致，细节准确清晰。

## 长文档冲突梳理与重写

| Variant | Success | Latency(ms) | Overall | Rule | Embed | Semantic | Accuracy | Judge | Preview |
|---------|---------|-------------|---------|------|-------|----------|----------|-------|---------|
| self_hosted_full | Y | 13798.0 | 57.2 | 100.0 | 49.4 | 43.2 | 18.2 | 93.0 | ### 1. 需求冲突与不完整点 - **鉴权范围冲突**：产品要求首版仅内部试用，无需鉴权；安全团队要求所有环境必须集成SSO。 - **上线时间冲突**：老 |
- `self_hosted_full` Embedding: hash_embedding_fallback
- `self_hosted_full` Judge: 回答结构完整，准确识别并整合了所有核心冲突，提出了合理的分阶段方案与行动清单。
| self_hosted_no_planner | Y | 16118.9 | 58.5 | 100.0 | 55.0 | 44.1 | 18.7 | 99.0 | **1. 互相冲突或不完整的需求点**  *   **访问控制冲突**：产品要求首版内部试用不鉴权，安全要求所有环境必须集成SSO。 *   **上线时间冲突* |
- `self_hosted_no_planner` Embedding: hash_embedding_fallback
- `self_hosted_no_planner` Judge: 回答完全遵循指令，精准识别所有冲突点，并给出了结构清晰、内容准确的统一方案、风险清单与行动清单。
| self_hosted_no_context | Y | 14290.2 | 58.2 | 100.0 | 49.8 | 43.1 | 18.3 | 100.0 | 1. **冲突或不完整的需求点**     *   **鉴权要求冲突**：产品要求首版仅内部试用、无需鉴权；安全要求所有环境必须集成SSO。     *   * |
- `self_hosted_no_context` Embedding: hash_embedding_fallback
- `self_hosted_no_context` Judge: 输出完美符合指令要求，准确识别并整合了所有冲突点，结构清晰，内容完整。
| self_hosted_no_history | Y | 16074.7 | 57.3 | 100.0 | 50.1 | 42.0 | 16.8 | 99.0 | ## 1. 冲突或不完整的需求点  1.  **访问控制要求冲突**：产品需求（首版内部试用，无需鉴权）与安全策略（所有环境必须做SSO）存在根本性矛盾。 2. |
- `self_hosted_no_history` Embedding: hash_embedding_fallback
- `self_hosted_no_history` Judge: 回答精准识别所有冲突，提供统一方案与行动清单，完全符合指令要求。

## 汇总

| Variant | Avg Overall | Avg Rule | Avg Embed | Avg Semantic | Avg Accuracy | Judge Coverage | Avg Latency(ms) |
|---------|-------------|----------|-----------|--------------|--------------|---------------|-----------------|
| self_hosted_full | 55.24 | 97.50 | 46.29 | 39.81 | 16.69 | 100% | 20810.74 |
| self_hosted_no_planner | 54.06 | 95.36 | 48.47 | 38.20 | 15.69 | 100% | 27863.95 |
| self_hosted_no_context | 54.77 | 97.50 | 42.33 | 38.46 | 15.85 | 100% | 21997.38 |
| self_hosted_no_history | 54.51 | 97.50 | 45.97 | 38.02 | 14.61 | 100% | 30077.73 |

## 增益

- `self_hosted_full` 相对 `self_hosted_no_planner` 的质量差值: +1.18
- `self_hosted_full` 相对 `self_hosted_no_context` 的质量差值: +0.47
- `self_hosted_full` 相对 `self_hosted_no_history` 的质量差值: +0.73