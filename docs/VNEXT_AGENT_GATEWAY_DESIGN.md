# OpenCopilot vNext Agent Gateway 与 Provider Adapter 设计

> 版本 vNext Draft 0.2 | 2026-06-11 | 面向统一任务协议、self_hosted 编排执行、自研 agent 与第三方 agent 共存

---

## 1. 文档定位

本文档描述 `vnext` 中 `Agent Gateway`、`Provider Adapter`、`Broker Gateway` 的设计方案，目标是：

- 让 UI 只调用统一任务 API
- 让自研智能体与第三方智能体共存
- 把 provider 差异限制在 Gateway 内部
- 为未来 API 转发层打基础

---

## 2. 核心问题

当前如果直接让 UI 面向某个具体智能体，会带来 4 个问题：

1. UI 与智能体内部实现强耦合
2. 第三方智能体接入会把差异上浮到 UI
3. 流式输出、错误码、结果结构无法统一
4. Broker 能力容易被不同智能体各自绕着调用

因此需要一层 `Gateway + Adapter`。

## 2.1 当前落地状态

截至 `2026-06-11`，vnext runtime 已落地下列能力：

- `auto -> provider selector`
  - 文本类任务默认走 `self_hosted`
  - `ppt` 仍默认走 `hermes_local`
- `self_hosted adapter`
  - 通过统一 `Task/Event/Result` 协议桥接本地自研 agent runtime
  - 对 UI 暴露标准 `task.stage_changed / task.delta / task.completed`
- `runtime ablation hooks`
  - 通过 `context_snapshot.metadata.runtime_flags` 控制 planner/context/tool prompt 等能力开关
  - 支持同输入消融评测与增益分析

这意味着 `Agent Gateway` 已不再只是 Hermes 透传层，而是开始承担真正的 runtime orchestration 职责。

---

## 3. 总体设计

```text
UI
  -> Unified API
     -> Agent Gateway
         -> Provider Registry
         -> Provider Selector
         -> Request Normalizer
         -> Stream Adapter
         -> Result Normalizer
         -> Error Mapper
         -> hermes_local adapter
         -> self_hosted adapter
         -> third_party adapter
     -> Broker Gateway
         -> Context Snapshot
         -> Apply Preview
         -> Apply Commit
```

### 3.1 定位

#### Unified API

- 面向 UI 的合同层

#### Agent Gateway

- 面向智能体 provider 的标准化层

#### Broker Gateway

- 面向环境能力的编排层

---

## 4. Agent Gateway 职责

Agent Gateway 负责 6 件事：

1. 选择 provider
2. 标准化请求
3. 标准化事件流
4. 标准化最终结果
5. 标准化错误
6. 执行策略控制

### 4.1 它不负责什么

Agent Gateway 不负责：

- UI 状态
- 宿主上下文读取细节
- 任务真源存储
- 复杂业务语义本体

---

## 5. Provider 模型

### 5.1 Provider 分类

当前 provider 规划如下：

- `self_hosted`
  - 当前文本类任务默认 provider
  - 负责桥接本地自研 orchestrated runtime
- `hermes_local`
  - 当前 `ppt`/结构化产物任务默认 provider
  - 保留为第三方强能力 provider
- `third_party`
  - 扩展类别保留

### 5.2 推荐 provider 目录

```text
agents_next/providers/
  self_hosted/
    adapter.py
  hermes_local/
    adapter.py
    dto_mapper.py
    stream_adapter.py
    error_mapper.py
    healthcheck.py
  openai_compatible/
    adapter.py
    streaming.py
  anthropic_compatible/
    adapter.py
    streaming.py
  custom/
    adapter.py
```

### 5.2.1 Hermes local 配置约定

`hermes_local` 当前按“用户填写配置 + 首选 profile + 自动发现可用端口”执行。

推荐环境变量：

```bash
HERMES_PROVIDER_PROFILE=coder
HERMES_PROFILE_ENV_FILE=
HERMES_BASE_URL=
HERMES_API_KEY=
```

配置优先级：

1. 显式 `HERMES_BASE_URL` / `HERMES_API_KEY`
2. `HERMES_PROFILE_ENV_FILE` 指向的 profile `.env`
3. 默认 `~/.hermes/profiles/<profile>/.env`
4. 自动扫描 `~/.hermes/profiles/*/.env`，对可推导端口做 `/health` 验证后选择健康实例

这样做的目的不是耦合 Hermes 目录，而是在调试阶段先稳定接通首选 profile；如果当前机器上的 Hermes 端口或 profile 不一致，OpenCopilot 会在运行时动态选择健康实例，同时保留未来切换到其他 profile 或 provider 的能力。

### 5.2.2 Self-hosted 配置约定

`self_hosted` 当前不依赖独立 HTTP provider 进程，而是直接桥接仓库内自研 runtime：

- 入口：`opencopilot.agent.caller.call_agent_pipeline_sync`
- 编排层：`platform_next/gateway/agent_gateway/coordinator.py`
- 运行时 flags：`context_snapshot.metadata.runtime_flags`

当前已支持的实验 flags：

- `disable_planner`
- `disable_context_prefix`
- `disable_tools_prompt`
- `disable_persona_prompt`
- `disable_history`
- `disable_session_memory`

### 5.3 Provider 能力差异

不同 provider 可能在这些方面不同：

- 是否支持流式
- 是否支持工具调用
- 是否支持结构化输出
- 是否支持取消
- 是否支持长上下文
- 是否支持 patch 风格产物

这些差异都不应该暴露给 UI。

---

## 6. 标准接口设计

### 6.1 Provider 协议

```python
class AgentProvider(Protocol):
    async def create_run(self, request: UnifiedTaskRequest) -> str: ...
    async def stream_events(self, run_id: str) -> AsyncIterator[UnifiedAgentEvent]: ...
    async def cancel_run(self, run_id: str) -> None: ...
    async def get_result(self, run_id: str) -> UnifiedTaskResult: ...
```

### 6.2 设计原则

- Gateway 对 provider 只要求最少 4 个能力
- provider 内部可自由映射到自己的 SDK / API / runtime
- provider 原始事件不直接传给 UI

---

## 7. Gateway 内部模块

```text
platform_next/gateway/agent_gateway/
  registry.py
  selector.py
  request_normalizer.py
  response_normalizer.py
  stream_adapter.py
  policy_guard.py
  timeout_controller.py
  error_mapper.py
  coordinator.py
```

### 7.1 `registry.py`

职责：

- 注册 provider
- 查询 provider 能力
- 维护 provider 元信息

### 7.2 `selector.py`

职责：

- 根据 action / constraints / policy 选择 provider

输入：

- action
- provider preference
- require_evidence
- latency budget
- fallback policy

### 7.3 `request_normalizer.py`

职责：

- 将 `UnifiedTaskRequest` 变成 provider 可接受的请求对象

规范化内容：

- action
- context snapshot
- user_input
- constraints
- provider options

### 7.4 `stream_adapter.py`

职责：

- 将 provider 原始流式事件转换成统一 Task Event

要解决的问题：

- 不同 provider 的事件粒度不同
- 有的 provider 只有 delta，没有 stage
- 有的 provider 只有最终结果，没有 artifact 事件

### 7.5 `response_normalizer.py`

职责：

- 将 provider 最终输出归一成统一 `Result DTO`

重点：

- summary
- artifacts
- evidence
- warnings
- next_actions
- apply_operations

### 7.6 `policy_guard.py`

职责：

- 限制 provider 选择
- 限制动作范围
- 控制是否允许自动回写
- 控制是否必须要求 evidence

### 7.7 `timeout_controller.py`

职责：

- 处理请求超时
- 处理事件流超时
- 处理 fallback 决策

### 7.8 `error_mapper.py`

职责：

- 将 provider 异常映射成统一错误码

---

## 8. Broker Gateway 设计

### 8.1 为什么单独拆 Broker Gateway

即使 UI 最终只调用统一 API，`上下文采集` 和 `回写` 仍然和智能体执行是两类不同问题：

- 智能体关心的是理解、规划、生成
- Broker 关心的是读宿主、写宿主、权限校验

因此不应把 Broker 细节塞进 Agent Gateway。

### 8.2 Broker Gateway 职责

- 创建 context snapshot
- 生成 apply preview
- 提交 apply commit
- 统一权限和错误语义

### 8.3 Broker Gateway 目录建议

```text
platform_next/gateway/broker_gateway/
  context_service.py
  apply_service.py
  permission_guard.py
  error_mapper.py
```

---

## 9. Hermes 过渡 provider 设计

### 9.1 Hermes local provider 定位

`Hermes local provider` 在第一阶段是主 provider，但它的角色是：

- 过渡执行内核
- 降低重构初期复杂度
- 帮助验证 Unified API / Gateway / Broker / UI 边界

它不是：

- 系统真源
- 长期主脑
- UI 需要感知的特例

### 9.2 Hermes local provider 接入面

基于本机 Hermes 的现状，第一阶段建议优先使用：

- `GET /health`
- `GET /v1/models`
- `POST /v1/runs`
- `GET /v1/runs/{run_id}/events`

兜底兼容：

- `POST /v1/chat/completions`

### 9.3 Hermes local provider 约束

- Hermes 负责执行和生成
- OpenCopilot 负责 task/session/event/context 真源
- OpenCopilot Broker 负责 context snapshot 与 apply preview / commit
- Hermes 原始事件和结果必须经过 normalize 后才能进入 UI

---

## 10. 自研 provider 设计

### 10.1 自研 runtime 定位

自研 provider 是第二阶段的目标主 provider，用于承接：

- 高质量结构化结果
- 与 Broker 的深度配合
- 稳定的 patch / apply 产物输出

### 10.2 自研 provider 内部结构

```text
agents_next/core/
  runtime/
    orchestrator.py
    task_context.py
    session_manager.py
    execution_state.py
  planning/
    planner.py
  execution/
    executor.py
    tool_runner.py
    verifier.py
  output/
    artifact_builder.py
    result_builder.py
    stream_emitter.py
  safety/
    input_guard.py
    output_guard.py
    tool_policy.py
```

### 10.3 自研 provider 执行流

```text
UnifiedTaskRequest
  -> input guard
  -> context binding
  -> planning
  -> tool/capability execution
  -> verification
  -> result building
  -> stream emit
```

---

## 11. 第三方 adapter 设计

### 11.1 第三方 adapter 目标

第三方 adapter 的目标不是“照搬对方协议”，而是把对方协议转成平台统一协议。

### 11.2 第三方 adapter 职责

- 构造 provider 请求
- 适配 provider 事件流
- 将 provider 结果转换成 Unified Result
- 将 provider 错误转换成统一错误码

### 11.3 第三方 adapter 不负责

- UI 特判
- 存储 task 真相
- 宿主回写
- 自己定义新的结果结构

---

## 12. Provider 选择策略

### 12.1 路径 A：UI 指定 provider

优点：

- 简单直观

缺点：

- provider 差异容易上浮到 UI

### 12.2 路径 B：Gateway 自动选择

优点：

- UI 更稳定
- 更利于 fallback 和成本控制

缺点：

- Gateway 逻辑更重

### 12.3 推荐策略

默认采用路径 B：

- UI 可以传递偏好
- Gateway 负责最终选择
- 第一阶段默认优先选择 `hermes_local`

---

## 13. 结果标准化策略

### 13.1 统一结果必须包含

- `summary`
- `artifacts`
- `warnings`
- `next_actions`

### 13.2 尽可能包含

- `evidence`
- `apply_operations`

### 13.3 对第三方 provider 的降级策略

如果第三方 provider 无法原生提供结构化结果：

- Gateway 先收原始结果
- 再做二次 normalize
- 必要时做结构化补全

注意：

- 这一步可以存在，但第一阶段优先适配 Hermes 原生 `runs/events`

---

## 14. 流式事件标准化策略

### 14.1 统一事件类型

- `task.created`
- `task.stage_changed`
- `task.delta`
- `task.artifact`
- `task.warning`
- `task.completed`
- `task.failed`

### 14.2 事件对齐策略

对于只有文本流的 provider：

- 由 `stream_adapter` 合成 `stage_changed`
- 将文本块转换为 `delta`
- 在最终结果时补发 `artifact`

对于原生支持结构化中间结果的 provider：

- 直接映射 artifact 事件

---

## 15. 错误标准化策略

### 15.1 错误来源

- provider 不可用
- provider 超时
- provider 流中断
- 输出结构化失败
- policy 拒绝
- Broker 权限拒绝

### 15.2 统一错误码

- `AGENT_UNAVAILABLE`
- `AGENT_TIMEOUT`
- `PROVIDER_STREAM_ERROR`
- `UNSUPPORTED_ACTION`
- `SECURITY_BLOCKED`
- `BROKER_DENIED`

### 15.3 原则

- 所有 provider 特有异常都在 Gateway 内部收敛
- UI 只依赖统一错误码和是否可重试

---

## 16. 状态与存储关系

### 16.1 Gateway 与 Store 的关系

Gateway 不自己保存业务真相，而是使用 Stores：

- task store
- session store
- event store
- context store

### 16.2 存储边界

provider 可以维护临时 run_id，但不能成为系统任务真相。

---

## 17. 典型时序

### 17.1 创建任务

```text
UI
  -> Unified API POST /vnext/tasks
  -> Agent Gateway
  -> Selector choose provider
  -> Request Normalizer
  -> Provider.create_run()
  -> TaskStore create
  -> return task_id
```

### 17.2 订阅事件

```text
UI
  -> GET /vnext/tasks/{id}/events
  -> Gateway reads provider stream
  -> Stream Adapter normalize
  -> EventStore append
  -> UI polling consume events
```

### 17.3 获取最终结果

```text
Provider result
  -> Response Normalizer
  -> TaskStore update result
  -> UI GET /vnext/tasks/{id}
```

---

## 18. 风险与缓解

### 18.1 Gateway 巨石化

风险：

- 把所有逻辑都塞进 Gateway

缓解：

- 严格拆成 selector / normalizer / adapter / error mapper / policy

### 18.2 第三方 provider 破坏统一协议

风险：

- 第三方能力太弱，逼 UI 做兼容特判

缓解：

- 统一协议高于 provider 能力
- 无法满足最低协议的 provider 不能进入主链路

### 18.3 Broker 反向侵入 agent 协议

### 18.4 过渡 provider 固化为长期依赖

风险：

- 第一阶段因为 Hermes 可用，就不再推动自研 runtime 建设

缓解：

- 在文档与目录上明确 `self_hosted` 是第二阶段目标
- 第一阶段不让 Hermes 持有系统真源与宿主控制权

风险：

- provider 直接去调 broker 细节，破坏分层

缓解：

- 上下文和回写统一由 Broker Gateway 编排
- provider 消费的是标准化 context，不是 broker 原始对象

---

## 19. 第一阶段建议范围

第一阶段建议只做：

- `hermes_local` provider
- review / explain / polish
- replace selection apply
- 自研 `self_hosted` 目录与接口预留，但不进入第一阶段交付

不建议第一阶段做：

- 复杂多 provider 路由策略
- 用户前台切换 provider
- 自治规划型长链任务

---

## 20. 与其他文档关系

- `docs/VNEXT_REBUILD_BLUEPRINT.md`：总体架构与目标
- `docs/VNEXT_UNIFIED_AGENT_API.md`：外部 API 契约
- `docs/VNEXT_MODULE_BOUNDARIES.md`：目录与依赖边界
- `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`：实施步骤与阶段目标
- `docs/VNEXT_SMART_COPILOT_UI_SPEC.md`：UI 交互与状态机设计
