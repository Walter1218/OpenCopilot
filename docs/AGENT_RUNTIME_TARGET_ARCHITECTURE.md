# OpenCopilot Target Agent Runtime Architecture

> 更新时间：2026-06-08
> 适用范围：长期目标架构，不等同于当前已落地的 `Phase1 vnext/Hermes` 过渡实现

---

## 1. 文档定位

本文档回答 4 个问题：

1. OpenCopilot 的长期理想架构应该长什么样
2. `UI / Runtime / Capability / Provider` 的职责边界应该如何切分
3. 如何在固定一套 `V5 UI` 的前提下，通过配置选择自研智能体或第三方智能体
4. 如何系统性解决当前“业务协议在 UI、转发协议在后端、Provider 写死”的结构性问题

注意：

- 当前仓库的真实可运行链路，仍以 `docs/STARTUP_GUIDE.md` 与 `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md` 为准
- 本文档定义的是长期目标态；它不是要求一次性重写全部代码，而是要求后续演进都朝这个方向收敛

---

## 2. 当前问题

当前 `Phase1` 架构已经完成了统一 `V5 UI -> vnext/Hermes` 的可运行链路，但它仍是过渡架构，主要问题有：

1. 业务协议真源分散在 UI
   - 例如 `ppt_editor` 的提示词、输出格式约束、当前页命中与标题位语义仍主要在 UI 组件中组装
2. 执行选择权没有沉到 Runtime
   - 当前很多请求默认写死到 `hermes_local`
3. Provider 协议和业务协议没有彻底隔离
   - `vnext` 负责统一任务转发，但并不真正拥有各能力的业务协议真源
4. 流式事件、埋点、错误语义没有完全统一
   - 自研链路与第三方链路在事件形态、收尾方式、调试字段上仍有差异

这些问题在“单 Provider 过渡期”还能接受，但在“固定一套 UI、配置化切换智能体、多 Provider 长期共存”的目标下会变成系统性风险。

---

## 3. 目标原则

长期目标架构必须同时满足以下原则：

1. 固定一套 UI
   - 用户只看到一套 `V5 UI`
   - 不因自研或第三方智能体不同而改变主交互入口
2. Runtime 成为智能体中枢
   - 智能体选择、协议归一化、流式事件、fallback、埋点统一都下沉到 Runtime
3. Capability 协议独立于 UI 与 Provider
   - `chat / code / translate / ppt_editor` 等能力必须有自己的协议真源
4. Provider 只做执行适配
   - Hermes、OpenAI、未来其他第三方只负责运行，不持有系统业务真源
5. 所有输出都先归一化，再交还 UI
   - UI 不直接处理 Provider 私有结果格式

---

## 4. 目标架构

```text
V5 UI
  -> Agent UI Facade
  -> Local Agent Runtime API
  -> Capability Protocol Registry
  -> Policy / Routing Engine
  -> Execution Orchestrator
  -> Runner(SelfAgentRunner | ProviderRunner)
  -> Provider Adapter(Hermes / OpenAI / ...)
  -> Result Normalizer
  -> Capability Materializer
  -> UI Apply / Preview / Export
```

各层职责如下：

- `V5 UI`
  - 负责用户输入、上下文采集、结果展示、交互反馈
  - 不直接持有业务协议真源
- `Agent UI Facade`
  - UI 的唯一 AI 入口
  - 统一接收 `prompt / action / capability / context`
- `Local Agent Runtime API`
  - 本地智能体运行时
  - 负责统一任务生命周期，不暴露 Provider 差异给 UI
- `Capability Protocol Registry`
  - 定义各能力的输入 schema、输出 schema、提示模板、校验规则
  - 是业务协议真源
- `Policy / Routing Engine`
  - 根据配置、任务类型、性能预算、环境策略决定走自研或第三方
- `Execution Orchestrator`
  - 负责任务创建、超时、取消、重试、fallback、shadow run
- `Runner`
  - 统一封装两类执行路径：
    - `SelfAgentRunner`
    - `ProviderRunner`
- `Provider Adapter`
  - 只负责第三方接口映射与事件转译
- `Result Normalizer`
  - 把不同 runner 的结果统一成标准事件和标准结果
- `Capability Materializer`
  - 把标准结果落成具体能力的可执行动作，例如 `PPT` 的页面 patch

---

## 5. 推荐边界

### 5.1 UI 应该负责什么

- 采集用户输入与上下文
- 渲染运行中状态与结果
- 接收标准事件：
  - `accepted`
  - `progress`
  - `delta`
  - `artifact`
  - `completed`
  - `failed`

### 5.2 UI 不应该负责什么

- 拼装能力级业务协议真源
- 直接判断该走自研还是第三方
- 按 Provider 分支处理结果结构
- 写死 `provider=hermes_local` 这类执行信息

### 5.3 Runtime 应该负责什么

- 根据配置解析当前执行路由
- 组装能力级提示与约束
- 启动正确的 runner
- 统一流式事件
- 统一结果格式
- 统一错误模型
- 统一埋点

### 5.4 Provider 应该负责什么

- 建立与目标模型服务的连接
- 提交任务 / 拉取流 / 映射错误
- 返回原始输出与原始使用量信息

### 5.5 Provider 不应该负责什么

- 决定 PPT 如何渲染
- 决定标题位、当前页、布局 patch 的业务语义
- 成为系统长期真源

---

## 6. 能力协议中心

长期目标下，能力协议必须集中管理，至少包括：

- `chat`
- `code`
- `translate`
- `ppt_editor`
- `selection_rewrite`

推荐目录：

```text
agent_runtime/protocols/
  chat/
  code/
  translate/
  ppt_editor/
```

每个能力协议至少包含：

1. 输入 schema
2. 输出 schema
3. 默认 system prompt / tool contract
4. 最小完成条件校验
5. 结果归一化规则
6. materializer 规则

以 `ppt_editor` 为例，长期目标不是让 UI 继续直接拼 `render_commands` 提示，而是把它收敛为 Runtime 内部协议，再由 materializer 统一转为 UI 可落地结构。

---

## 7. 统一请求协议

```json
{
  "task_id": "uuid",
  "capability": "ppt_editor",
  "action": "edit",
  "intent": {
    "user_input": "把当前页改成图文布局，标题更有高管感",
    "language": "zh-CN"
  },
  "context": {
    "source": "studio",
    "document": {},
    "selection": {},
    "capability_context": {}
  },
  "constraints": {
    "stream": true,
    "safe_apply_only": true,
    "latency_budget_ms": 12000
  },
  "route_hint": {
    "prefer": "auto",
    "provider": ""
  }
}
```

这个协议由 UI 提交给 Runtime，而不是直接由 UI 面向某个 Provider 组装。

---

## 8. 统一事件协议

```json
{
  "type": "accepted|progress|delta|artifact|completed|failed",
  "task_id": "uuid",
  "backend": "self_agent|provider_runtime",
  "provider": "self_agent|hermes_local|openai",
  "capability": "ppt_editor",
  "payload": {}
}
```

说明：

- UI 只消费这个事件协议
- 自研链路与第三方链路都必须映射成这套标准事件
- 不允许 UI 直接理解 Hermes 原始事件或其他 Provider 私有流式协议

---

## 9. 统一结果协议

```json
{
  "task_id": "uuid",
  "backend": "self_agent|provider_runtime",
  "provider": "self_agent|hermes_local",
  "capability": "ppt_editor",
  "normalized_output": {
    "summary": "",
    "commands": [],
    "warnings": [],
    "evidence": [],
    "raw_text": ""
  },
  "apply_plan": [],
  "debug_meta": {}
}
```

说明：

- `normalized_output` 是 UI 唯一稳定依赖的结果结构
- `raw_text` 仅作为调试与兜底存在
- 各能力的 materializer 负责把 `commands` 转成具体动作

---

## 10. 配置模型

理想状态下，必须把“LLM 连接配置”和“智能体运行时配置”拆开。

推荐新增：

```json
{
  "agent_runtime": {
    "routing_mode": "policy",
    "default_backend": "self_agent",
    "default_provider": "self_agent",
    "capability_routes": {
      "chat": {
        "backend": "self_agent",
        "provider": "self_agent"
      },
      "translate": {
        "backend": "provider_runtime",
        "provider": "hermes_local"
      },
      "ppt_editor": {
        "backend": "provider_runtime",
        "provider": "hermes_local"
      }
    },
    "fallback_policy": {
      "enabled": true,
      "on_timeout": "self_agent",
      "on_protocol_error": "self_agent"
    }
  }
}
```

说明：

- `provider_type / api_key / api_base / model` 继续服务于 LLM 连接层
- `agent_runtime` 专门决定请求路由、能力级分流和 fallback

---

## 11. 为什么这是最理想架构

### 11.1 技术层

- 业务协议、任务编排、Provider 适配彻底分层
- 多智能体共存不会继续污染 UI
- Provider 可替换，可灰度，可 shadow，可回退

### 11.2 产品层

- 用户始终只使用一套 `V5 UI`
- 可以针对不同能力做最佳路由，而不是全局一刀切
- 可以在不改变 UI 的前提下持续优化体验

### 11.3 用户层

- 交互一致
- 结果结构稳定
- 错误语义一致
- 慢、失败、回退都能被解释清楚

---

## 12. 当前架构与目标架构的关系

当前 `Phase1` 架构的定位应明确为：

- 已完成 `V5 UI -> vnext/Hermes` 主链路打通
- 已完成第一批 PPT 共创稳定性修复
- 已完成长任务 timeout 与后台事件消费改造

但它不是长期终局，长期目标必须是：

- 固定一套 `V5 UI`
- 引入本地统一 `Agent Runtime`
- 能力协议从 UI 内联逻辑迁出
- 自研与第三方智能体都通过同一 Runtime 接入

---

## 13. 推荐演进顺序

### Phase A: 统一执行门面

- 新增 `AgentExecutionRouter`
- `V5AgentWorker` 不再写死 Hermes
- 支持 `self_agent` 与 `provider_runtime` 两类 backend

### Phase B: 能力协议中心化

- 把 `ppt_editor` 等能力协议从 UI 抽到 Runtime
- 新增统一 normalizer 与 materializer

### Phase C: 统一事件与结果协议

- 各 runner 输出同一事件流
- UI 只认标准事件和标准结果

### Phase D: 策略化路由与 fallback

- 按 capability 配置 backend
- 支持超时回退、协议错误回退、灰度和 shadow run

---

## 14. 验收标准

长期目标架构的关键验收指标：

1. UI 直接依赖 Provider 的次数 `= 0`
2. 能力协议定义落在 UI 的 case 数 `= 0`
3. 自研与第三方链路的标准事件协议覆盖率 `= 100%`
4. Provider 差异上浮到 UI 的 case 数 `= 0`
5. 能力级路由、fallback、埋点全部可配置

---

## 15. 最终结论

最理想的 OpenCopilot 架构不是“继续把 UI 统一到 Hermes”，也不是“保留两套 UI 分别接自研和第三方”，而是：

- 固定一套 `V5 UI`
- 用本地统一 `Agent Runtime` 承接所有智能体执行
- 用 `Capability Protocol Registry` 承接所有能力协议真源
- 用 `Policy / Routing Engine` 实现配置化智能体选择
- 用 `Provider Adapter` 隔离第三方差异

只有这样，系统才能同时具备：

- 长期可演进性
- 用户体验一致性
- 多智能体可切换性
- 协议与实现解耦性
