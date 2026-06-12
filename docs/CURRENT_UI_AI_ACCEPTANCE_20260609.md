# OpenCopilot 当前 UI/AI 功能与质量验收

> 版本 2026-06-09 | 面向当前仓库真实实现 | 区分已接真实 AI 的主链路与仍未落地的设计项

---

## 1. 文档定位

本文档回答 4 个问题：

1. 当前 UI 里哪些模块已经接入真实 AI
2. 哪些模块仍是 UI 工作流、摘要面板或尚未落地的设计项
3. 当前生产代码的功能验收是否通过
4. 质量验收应该如何做，是否可以用模型输出作为 benchmark

本文档描述的是 **当前仓库真实实现与真实验收结果**，不是 vnext 目标态蓝图。

---

## 2. 总体结论

### 2.1 当前已通过的范围

以下 UI 主链路已经接入真实 AI，并完成完整生产代码验证：

- `Work Tab` 主操作：`Explain / Fix / Polish / Translate / Code Review`
- `Chat Tab` 核心连续对话
- `Workspace Chat` 多意图聊天：`Chat / Research / PPT / Translate / Explain / Fix / Polish / Code Review`
- `Studio Tab` 快速创建 PPT
- `Studio Window` 页内共创聊天
- `PPT` 生成、共创、导出、回退与观测链路
- `Settings -> Engine -> Agent Runtime` 已支持通过配置在 `Self Agent` 与第三方智能体间切换
- 当前第三方智能体接入已支持 `Hermes Local`

### 2.2 当前未接真实 AI 的范围

以下模块要么本来就是 UI 工作流，要么设计里提过但当前还未真正落地：

- `Workspace / Files`
- `Workspace / Memory`
- `Workspace / Settings`
- `Workspace / Task`
- `Work Tab / More`
- `Chat Tab / Skill Panel`
- `Cmd+K` 命令面板
- 右键推荐技能菜单

### 2.3 当前验收结论

- 完整 UI/AI 组合回归：`427 passed`
- 真实生产链路验证：`27/27 PASS`
- 观测体系验证：通过
- 架构收口结论：`V5 UI` 已通过统一 `V5AgentWorker -> /vnext/* -> Agent Gateway` 调用智能体，UI 与智能体实现不再直接强耦合
- 当前可以判定：
  - `主 UI + 主 AI 链路已通过生产级功能验收`
  - `当前已支持一套固定 UI 下配置切换自研智能体与第三方智能体（当前第三方仅 Hermes）`
  - `Skill 体系相关入口尚未进入“已完成”状态`

---

## 3. 验收范围边界

### 3.0 当前架构边界

当前仓库中，`UI` 与智能体运行时的关系已从“界面直接知道具体智能体实现”收敛为：

- `UI` 只感知统一入口：`V5AgentWorker`
- `V5AgentWorker` 只负责按配置选择 `self_agent` 或 `vnext_provider`
- 第三方智能体统一经 `/vnext/context/snapshots`、`/vnext/tasks`、`/vnext/tasks/{id}/events` 协议接入
- Provider 差异沉到 `Agent Gateway / Provider Adapter`
- 因此当前 UI 可以保持固定，智能体能力通过配置与 adapter 演进，而不要求 UI 随 provider 增长而重写

### 3.1 本次功能验收的“通过”定义

某个模块记为“通过”，需要同时满足：

- UI 入口存在且能触发真实业务代码
- 真实请求最终进入 `V5AgentWorker` 或等效生产调用链
- 输出或状态变更符合当前产品预期
- 对应日志与埋点链路存在
- 相关单测/组合回归/生产验证中没有阻塞失败

### 3.2 本次质量验收的“通过”定义

某个 AI 模块记为“质量通过”，需要满足：

- 输出不为空
- 没有 `think` 泄露
- 结构和格式符合该能力的预期
- 关键内容覆盖达到最低阈值
- 达到预设质量评分阈值

---

## 4. 模块验收表

| 模块 | 设计预期 | 当前实现 | 是否接真实 AI | 当前状态 | 验收结论 |
|------|----------|----------|----------------|----------|----------|
| `Work Tab` 主操作 | 快速处理选区/文档内容 | 已通过 `V5AgentWorker` 执行 Explain/Fix/Polish/Translate/Code Review | 是 | 已落地 | 通过 |
| `Work Tab / More` | 扩展操作或技能入口 | 当前仅展示操作列表，不执行真实能力 | 否 | 部分落地 | 未完成 |
| `Chat Tab` 核心对话 | 连续对话 + 上下文引用 | 已通过 `V5AgentWorker` 走真实链路 | 是 | 已落地 | 通过 |
| `Chat Tab / Skill Panel` | `/` 触发技能搜索 | 设计存在，当前未在 v5 代码中落地 | 否 | 未落地 | 未完成 |
| `Studio Tab` | 快速创建 PPT | 已通过 `V5AgentWorker` 执行 `ppt` 能力 | 是 | 已落地 | 通过 |
| `Studio Window` 共创 | 页内编辑、重生成、建议分析 | 已通过页内共创链路复用真实执行路径 | 是 | 已落地 | 通过 |
| `Workspace / Chat` | 多意图工作台聊天 | 已通过 `V5AgentWorker` 执行真实链路 | 是 | 已落地 | 通过 |
| `Workspace / Task` | 任务定义与上下文注入 | 当前是任务编排和上下文管理，不直接调用 AI | 否 | 已落地 | 通过 |
| `Workspace / Files` | 文件管理与上下文分发 | 当前是文件筛选/预览/发送到其他 AI 入口，不直接调 AI | 否 | 已落地 | 通过 |
| `Workspace / Memory` | 记忆可视化与注入 | 当前是记忆概览/详情/注入，不直接调 AI | 否 | 已落地 | 通过 |
| `Workspace / Settings` | 设置摘要与运维操作 | 当前是配置摘要/导出/复制/重置，不直接调 AI | 否 | 已落地 | 通过 |
| `Cmd+K` 命令面板 | 全局技能搜索与执行 | 设计存在，当前未落地 | 否 | 未落地 | 未完成 |
| 右键推荐技能菜单 | 原生右键推荐技能 | 设计存在，当前未落地 | 否 | 未落地 | 未完成 |

---

## 5. 当前真实代码证据

### 5.1 已接真实 AI 的主链路

- `Work Tab` 主操作调用真实链路：
  - `gui/v5/work_tab.py`
- `Chat Tab` 核心对话调用真实链路：
  - `gui/v5/chat_tab.py`
- `Workspace Chat` 多意图聊天调用真实链路：
  - `gui/v5/workspace.py`
- `Studio Tab` PPT 快速创建调用真实链路：
  - `gui/v5/studio_tab.py`
- `Studio Window` 页内共创调用真实链路：
  - `opencopilot/capabilities/ppt/ai_chat_widget.py`

这些主链路当前统一复用：

- `gui/v5/agent_worker.py`
- `platform_next/api/unified/tasks.py`
- `platform_next/gateway/agent_gateway/*`

这说明当前真实实现已经不是“每个 UI 模块各自绑定一个智能体实现”，而是通过统一 Runtime 与统一任务协议解耦。

### 5.1.1 当前第三方智能体接入状态

当前已落地的配置化智能体切换边界如下：

- `Agent Mode`
  - `Self Agent`
  - `Third-Party Agent`
- `Agent Provider`
  - 当前第三方仅内置 `Hermes Local`
- `Agent Model`
  - 当前会真实透传到 `/vnext/tasks` 与 `Hermes` run payload
- `Capability Routes`
  - `chat / explain / coding / ppt / translate` 可按能力单独覆盖
- `Fallback Policy`
  - 可配置第三方异常时自动回退到 `Self Agent`

### 5.2 当前仍未完成的设计项

设计文档里已经定义但当前仍未完整落地的项目：

- `Skill Panel`
- `Cmd+K` 命令面板
- 右键推荐技能菜单

这些入口在设计稿中属于目标态能力，不应被误记为“当前已完成”。

---

## 6. 功能验收证据

### 6.1 完整自动化回归

本轮已运行完整 UI/AI 组合回归，结果如下：

- 命令：
  - `python -m pytest tests/unit/test_v5_settings.py tests/unit/test_v5_bridge.py tests/unit/test_v5_bridge_http.py tests/unit/test_v5_agent_worker.py tests/unit/test_v5_agent_worker_hermes.py tests/unit/test_v5_agent_runtime.py tests/unit/test_config.py tests/unit/test_ppt_ai_chat_widget_hermes.py tests/unit/test_v5_studio.py tests/unit/test_v5_navigation.py tests/unit/test_v5_studio_tab_business.py tests/unit/test_v5_workspace.py tests/unit/test_v5_work_tab.py tests/unit/test_v5_chat_tab.py tests/unit/test_v5_chat_incremental_update.py tests/unit/test_v5_drag_drop.py tests/unit/test_v5_file_import.py tests/unit/test_v5_env.py -q`
- 结果：
  - `427 passed`

### 6.2 真实生产链路验证

本轮已运行仓库现有生产验证脚本：

- 命令：
  - `python scripts/production_validation.py`
- 结果：
  - `27/27 PASS`
  - 总耗时：`166.0s`

### 6.3 生产验证覆盖点

生产验证实际覆盖：

- `Chat`
- `Explain`
- `Fix`
- `Polish`
- `Translate`
- `Code Review`
- `PPT` 生成（预算报告）
- `PPT` 生成（会议纪要）
- 共创 persona / 映射 / JSON 解析 / 导出 / fallback
- `Timer log / SQLite log / Timer stats / Immune events`

---

## 7. 当前质量验收结果

### 7.1 当前 live 质量分

基于 `scripts/production_validation.py` 当前这一轮真实结果：

| 模块 | 质量分 | 结果 |
|------|--------|------|
| `Chat` | `4.2/5.0` | 通过 |
| `Explain` | `5.0/5.0` | 通过 |
| `Fix` | `4.8/5.0` | 通过 |
| `Polish` | `4.6/5.0` | 通过 |
| `Translate` | `4.3/5.0` | 通过 |
| `Code Review` | `5.0/5.0` | 通过 |
| `PPT`（预算报告） | `5.0/5.0` | 通过 |
| `PPT`（会议纪要） | `5.0/5.0` | 通过 |
| 共创 `IntentRouter` | `5.0/5.0` | 通过 |
| 共创 `JSON 解析` | `5.0/5.0` | 通过 |
| 共创 `PPT 导出` | `5.0/5.0` | 通过 |
| 共创 `Fallback` | `4.0/5.0` | 通过 |

### 7.2 当前评分口径

当前仓库已有质量验证主要采用以下混合方法：

- 长度与非空检查
- 关键词覆盖率
- `think` 泄露检查
- 结构完整性检查
- JSON / 结构化协议合法性检查

这是一套 **最小可用质量验收**，已经足够支持当前阶段的生产验证。

---

## 8. 质量量化指标

### 8.1 总体量化框架

建议把质量量化分为两层：

1. **硬门槛**
   - 不计入得分
   - 只要违反就直接判失败
2. **质量评分**
   - 用于横向比较版本、做 nightly 趋势跟踪和 benchmark 排名

推荐统一使用：

- `100 分制` 作为正式看板口径
- `5 分制` 作为研发和验收报告摘要口径

换算关系：

```text
score_5 = round(score_100 / 20, 1)
score_100 = score_5 * 20
```

### 8.2 一级指标与权重

建议采用以下总分结构：

| 一级指标 | 权重 | 说明 |
|------|------|------|
| `Reliability` | `30` | 能否稳定成功返回、是否超时、协议是否合法 |
| `Quality` | `40` | 内容是否正确、覆盖是否完整、结构是否清晰 |
| `UX` | `20` | 首字速度、总耗时、流式过程是否平滑 |
| `Safety` | `10` | 是否泄露推理、是否触发违规输出、是否存在明显越界 |

总分公式：

```text
Q_total = 0.30 * Reliability
        + 0.40 * Quality
        + 0.20 * UX
        + 0.10 * Safety
```

### 8.3 二级指标定义

#### Reliability（30 分）

| 指标 | 计算方式 | 建议权重 |
|------|----------|----------|
| 成功返回率 | `successful_calls / total_calls` | 10 |
| 超时率 | `1 - timeout_calls / total_calls` | 8 |
| 协议合法率 | `valid_outputs / total_outputs` | 8 |
| 导出/应用成功率 | `successful_apply_or_export / total_apply_or_export` | 4 |

#### Quality（40 分）

| 指标 | 计算方式 | 建议权重 |
|------|----------|----------|
| 任务完成度 | rubric 评分 `0-100` | 12 |
| 关键信息覆盖率 | `matched_keywords / expected_keywords` | 10 |
| 正确性 | 规则校验或 rubric judge | 10 |
| 结构化程度 | 标题/列表/段落/字段完整性评分 | 8 |

#### UX（20 分）

| 指标 | 计算方式 | 建议权重 |
|------|----------|----------|
| `TTFT` | 首个 chunk 到达耗时 | 8 |
| 总完成耗时 | 请求开始到完整输出结束 | 8 |
| 流式稳定性 | chunk 数、异常中断率、卡顿率 | 4 |

#### Safety（10 分）

| 指标 | 计算方式 | 建议权重 |
|------|----------|----------|
| `think` 泄露率 | `1 - leaked_outputs / total_outputs` | 4 |
| 违规输出率 | `1 - unsafe_outputs / total_outputs` | 4 |
| 安全拦截误杀率 | `1 - false_blocked / total_safe_inputs` | 2 |

### 8.4 硬门槛指标

以下指标建议作为 **Pass/Fail** 直接门槛，而不是仅参与加权得分：

- `协议错误率 = 0`
- `JSON 解析失败率 = 0`，适用于 `PPT / 结构化输出`
- `think` 泄露率 = `0`
- `P0 主链路成功率 = 100%`
- `导出/应用` 关键路径失败率 = `0`

### 8.5 按模块的量化门槛

| 模块 | 关键量化指标 | 建议最低门槛 |
|------|--------------|--------------|
| `Chat` | 任务完成度、相关性、追问一致性、`TTFT`、总耗时 | 质量分 `>= 4.2/5.0`，追问一致性 `>= 0.80` |
| `Explain` | 正确性、关键点覆盖率、结构化率 | 质量分 `>= 4.5/5.0`，覆盖率 `>= 85%` |
| `Fix` | 根因识别率、修复可执行率、修复正确率 | 质量分 `>= 4.5/5.0`，修复正确率 `>= 80%` |
| `Code Review` | 风险召回率、误报率、建议可执行性 | 质量分 `>= 4.5/5.0`，高风险召回 `>= 85%` |
| `Polish` | 语义保持、流畅度、风格达成度 | 质量分 `>= 4.3/5.0`，语义保持 `>= 90%` |
| `Translate` | 语义等价、术语一致性、格式保留 | 质量分 `>= 4.3/5.0`，术语一致性 `>= 95%` |
| `PPT` | JSON 合法率、结构完整率、主题覆盖率、导出成功率 | 质量分 `>= 4.5/5.0`，导出成功率 `= 100%` |
| `Workspace Research` | 证据覆盖、结构完整性、可追溯性 | 质量分 `>= 4.2/5.0`，证据覆盖 `>= 80%` |

### 8.6 时延门槛建议

建议同时建立 `P50 / P95` 时延门槛：

| 模块 | 建议 `P95` 上限 |
|------|-----------------|
| `Chat` | `<= 12s` |
| `Explain` | `<= 15s` |
| `Fix` | `<= 15s` |
| `Polish` | `<= 8s` |
| `Translate` | `<= 10s` |
| `Code Review` | `<= 30s` |
| `PPT` | `<= 25s` |

### 8.7 Benchmark Scorecard 模板

建议在 nightly 验收中统一输出以下 scorecard：

| 模块 | 成功率 | 协议合法率 | 平均质量分 | P50 耗时 | P95 耗时 | think 泄露率 | 结论 |
|------|--------|------------|------------|----------|----------|--------------|------|
| `Chat` | `100%` | `100%` | `4.2/5.0` | `6.1s` | `11.4s` | `0%` | Pass |
| `Explain` | `100%` | `100%` | `5.0/5.0` | `8.8s` | `14.6s` | `0%` | Pass |
| `PPT` | `100%` | `100%` | `5.0/5.0` | `13.0s` | `22.0s` | `0%` | Pass |

建议再配一个汇总公式：

```text
release_gate = (
    functional_pass_rate == 100%
    and hard_constraints_violations == 0
    and overall_quality_score >= 4.3
    and high_value_modules_score >= 4.5
)
```

---

## 9. 能否用模型输出作为 benchmark

### 9.1 可以，但不能直接把单一模型输出当唯一标准答案

推荐结论：

- `可以` 用模型输出作为 benchmark 的起点
- `不建议` 把某一个模型的一次输出直接当成唯一金标准

原因：

- 开放式任务往往存在多种正确答案
- 单一模型输出容易把风格误当成正确性
- 当底层模型升级后，答案可能更好但表述不同，直接做字符串对比会误伤

### 9.2 最合理的 benchmark 结构

建议采用四层结构：

1. **硬约束**
   - 非空
   - 无 `think` 泄露
   - JSON 可解析
   - 必填字段完整
   - 页数/字段/格式满足协议
2. **参考答案**
   - 用模型先生成 1-2 份参考输出
   - 再由人工合并为 `golden set`
3. **Rubric 评分**
   - 正确性
   - 关键信息覆盖
   - 结构化程度
   - 指令遵循
   - 风险与幻觉控制
4. **人工抽检**
   - 对边缘 case 和高价值业务做抽检

### 9.3 推荐的最终方案

#### 方案 A：单参考输出

- 做法：每个 case 先生成一份参考答案，再比对实际输出
- 优点：建设速度快
- 风险：容易把“措辞像不像”误当成“质量好不好”

#### 方案 B：混合 benchmark

- 做法：`硬约束 + 多参考答案 + rubric + 人工抽检`
- 优点：更稳、更适合长期 nightly 验收
- 风险：建设成本更高

**推荐使用方案 B。**

---

## 10. 建议的 benchmark 数据集结构

建议新增一套稳定的 `golden set`，每个 case 至少包含：

```json
{
  "case_id": "chat_explain_python_cache_001",
  "module": "Explain",
  "action_type": "explain",
  "input": "请解释下面这段 Python 代码的作用和潜在问题",
  "context_source": "selection",
  "context_meta": {
    "source_text": "..."
  },
  "hard_constraints": {
    "must_not_contain": ["<think>", "</think>"],
    "min_length": 120
  },
  "expected_keywords": ["缓存", "淘汰", "边界", "性能"],
  "golden_outputs": [
    "参考答案 A",
    "参考答案 B"
  ],
  "rubric": {
    "correctness": 0.35,
    "coverage": 0.25,
    "structure": 0.15,
    "instruction_following": 0.15,
    "risk_control": 0.10
  }
}
```

---

## 11. 推荐的质量验收流程

### 11.1 P0：建立首批 golden set

优先覆盖以下模块，每个模块先做 `5-8` 个 case：

- `Chat`
- `Explain`
- `Fix`
- `Polish`
- `Translate`
- `Code Review`
- `PPT`

目标规模：

- 首批 `30-50` 条 case

### 11.2 P1：接入 nightly benchmark

建议直接复用现有脚本体系：

- `scripts/production_validation.py`
- `scripts/workspace_chat_validation.py`
- `scripts/compare_agent_modes.py`

让 nightly 输出：

- 通过率
- 质量分均值
- 各模块耗时
- 失败 case 列表
- 关键日志链接或 trace id

### 11.3 P2：上线前门槛

建议设置最低门槛：

- 功能通过率 `= 100%`
- AI 质量平均分 `>= 4.2/5.0`
- `PPT / Code Review / Explain` 三个高价值模块平均分 `>= 4.5/5.0`
- JSON / 协议类错误 `= 0`
- `think` 泄露 `= 0`

---

## 12. 当前风险项

### 12.1 已知未完成项

- `Skill Panel`
- `Cmd+K` 命令面板
- 右键推荐技能菜单
- `Work Tab / More` 真执行链路

这些模块不应在对外口径里被描述为“已完成”。

### 12.2 质量体系的当前不足

- 目前质量评分仍以规则评分为主
- 还没有正式的 `golden set`
- 还没有 nightly 稳定基线
- 开放式任务尚未形成多参考答案评估

### 12.3 运行时层风险

- 当前生产验证已经通过，但不同环境下延迟仍可能波动
- `Code Review / PPT / Explain` 仍应继续重点盯响应时延与结构化稳定性

---

## 13. 当前可对外口径

建议对外统一描述为：

- `V5 UI 主链路已经完成并通过生产级功能验收`
- `Work / Chat / Workspace Chat / Studio / PPT 共创已接入真实 AI`
- `当前已支持在固定一套 V5 UI 下，通过配置切换自研智能体与第三方智能体`
- `当前第三方智能体接入已支持 Hermes Local，Agent Model 也已真实透传到第三方执行链路`
- `UI 与智能体执行层已通过统一 Runtime / API / Gateway 解耦，后续新增 provider 不再要求 UI 重写主交互入口`
- `Skill 体系相关入口仍处于设计已定义、实现未完成状态`
- `当前已具备可运行的质量验证能力，但正式 golden benchmark 仍建议继续建设`

---

## 14. 下一步建议

1. 新建 `golden set` 数据目录，先覆盖 30-50 条高价值 case
2. 把 `production_validation.py` 扩成 nightly 质量回归
3. 给 `Skill Panel / Cmd+K / 右键技能菜单 / Work More` 单独立项验收
4. 将本文件作为“当前实现验收真源”，避免再用目标态文档替代当前事实
