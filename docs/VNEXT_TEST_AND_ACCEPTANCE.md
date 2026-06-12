# OpenCopilot vNext 测试与验收方案

> 版本 vNext Draft 0.1 | 2026-06-08 | 用于约束 vnext 第一阶段的测试体系、黄金链路和切主验收标准

---

## 1. 文档定位

本文档定义 `vnext` 第一阶段的测试与验收规则，回答：

- 要测什么
- 先测什么
- 哪些指标达到才允许切主

本文件不替代 `DEVELOPMENT.md` 中的当前仓库测试说明，而是补充 `vnext` 新链路的专用质量标准。

---

## 2. 测试目标

### 2.1 目标

确保系统级 `V5 Smart Copilot` 链路：

- 功能可用
- 状态一致
- API 稳定
- 回写可控
- 与旧系统行为差异可解释
- 日志与埋点可区分当前 UI 版本和执行后端
- 固定 UI 下可通过配置切换自研智能体与第三方智能体，而不引入 UI 分叉

### 2.2 非目标

- 不追求第一阶段覆盖所有历史功能
- 不做大规模低价值 UI 截图测试
- 不做全平台全 provider 全动作穷举

---

## 3. 测试分层

### 3.1 Contract Tests

验证统一协议是否稳定：

- `/vnext/context/snapshots`
- `/vnext/tasks`
- `/vnext/tasks/{id}`
- `/vnext/tasks/{id}/events`
- `/vnext/apply/preview`
- `/vnext/apply/commit`

### 3.2 Data Model Tests

验证：

- task 状态机
- session 生命周期
- event sequence 顺序
- apply preview 过期与确认逻辑

### 3.3 Gateway Integration Tests

验证：

- request normalization
- provider selection
- stream adaptation
- result normalization
- error mapping

### 3.4 Broker Integration Tests

验证：

- selection snapshot
- context snapshot 组装
- apply preview
- apply commit

### 3.5 UI Flow Tests

验证：

- 双击右键召唤 `SmartCopilotV5`
- 上下文摘要可见
- 发起任务
- 渲染结果
- 预览修改
- 确认应用

### 3.6 Golden Flow Tests

验证代表性主链路，作为切主前硬门槛。

---

## 4. 第一阶段必测范围

### 4.1 API 层

必须覆盖：

- 正常创建 context snapshot
- context 缺失或 Broker 拒绝
- 正常创建 task
- task 查询与终态
- 任务事件基本顺序与 sequence 递增
- preview / commit 闭环

### 4.2 Runtime / Gateway 层

必须覆盖：

- `Hermes local` provider 正常返回
- `Self Agent / Third-Party Agent` 配置切换正确落到统一运行时路由
- `Agent Model` 能从设置项透传到 `/vnext/tasks` 与第三方 provider payload
- provider 超时
- provider 流中断
- result normalize 成功
- error map 正确

### 4.3 UI 层

必须覆盖：

- `SmartCopilotV5` 首次召唤
- UI 只通过统一 `V5AgentWorker` 发起任务，不直接依赖具体 provider 实现
- task running
- result ready
- preview ready
- apply success
- apply failure recovery
- 埋点字段完整性

---

## 5. 黄金链路

## 5.1 黄金链路 A：审查

```text
双击右键
  -> 获取选区
  -> 创建 review task
  -> 流式返回结果
  -> 展示 evidence / suggestions
```

### 通过条件

- 状态机完整
- 首条结果达标
- 最终结果结构完整

## 5.2 黄金链路 B：追问

```text
已有结果
  -> follow-up 输入
  -> 创建新 task
  -> 渲染追加结果
```

### 通过条件

- follow-up 仍走统一 task 模型
- UI 不依赖临时拼接逻辑

## 5.3 黄金链路 C：增量回写

```text
结果完成
  -> apply preview
  -> 用户确认
  -> apply commit
  -> 成功反馈
```

### 通过条件

- 没有 preview 不允许直接 commit
- commit 成功后状态一致

## 5.4 黄金链路 D：Studio PPT 共创

```text
导入文档或进入 Studio
  -> 创建 ppt / ppt_editor 任务
  -> 进入共创界面
  -> AI 编辑 / 重生成 / 建议分析
  -> 渲染指令或旧动作兼容执行
  -> 幻灯片更新
```

### 通过条件

- 初稿生成与共创内 follow-up 统一走 `V5AgentWorker -> vnext/Hermes`
- 当前页命中、标题位命中、图文版式更新可稳定落盘
- 旧 `action/update` JSON 在共创链路里仍可兼容

---

## 6. 核心测试用例

### 6.1 Context Snapshot

- 正常创建 snapshot
- 缺 selection 但有 document 上下文
- Broker 权限拒绝
- source_app 缺失时的降级行为

### 6.2 Task Lifecycle

- queued -> running -> succeeded
- queued -> running -> failed
- queued -> running -> cancelled
- retry 创建新 task

### 6.3 Event Stream

- event sequence 连续
- `completed` 后可查完整 result
- `failed` 时 error 可用

### 6.4 Result Model

- summary 存在
- artifacts 结构合法
- apply_operations 存在时 preview 可调用

### 6.5 Apply Flow

- preview 正常生成
- preview 过期
- commit 成功
- commit 失败
- commit 前 preview 缺失

### 6.6 UI Recovery

- context 获取失败重试
- task 超时重试
- preview 失败后返回结果页
- apply 失败后允许取消

### 6.7 Observability

- `V5_AGENT_START` 带 `ui_version=v5`
- `V5_AGENT_START` 带 `ui_surface=desktop`
- `V5_AGENT_START` 带 `agent_backend=hermes_vnext`
- `V5_AGENT_START` 带 `provider=hermes_local`
- `V5_AGENT_DONE / V5_AGENT_ERROR` 保持同样字段口径
- `PPT` 共创相关日志能区分：
  - 初稿生成
  - 共创 follow-up
  - 建议分析
  - 图文/标题更新失败

---

## 7. 指标与门槛

### 7.0 当前基线说明

除了本文件定义的 `vnext` 目标态测试标准，当前仓库已经形成一份面向真实实现的验收基线：

- 当前实现验收真源：`docs/CURRENT_UI_AI_ACCEPTANCE_20260609.md`
- 主 UI/AI 链路组合回归：`427 passed`
- 真实生产链路验证：`27/27 PASS`

后续 `vnext` 门槛建议直接继承这份当前基线的功能通过标准与质量量化口径。

### 7.1 体验指标

- 双击右键到浮层可见 `< 300ms`
- 上下文摘要显示 `< 800ms`
- 首条结果 `< 2.5s`
- 应用修改关键点击数 `<= 2`

当前已接真实 AI 的主能力，建议补充 `P95` 时延上限：

- `Chat <= 12s`
- `Explain <= 15s`
- `Fix <= 15s`
- `Polish <= 8s`
- `Translate <= 10s`
- `Code Review <= 30s`
- `PPT <= 25s`

### 7.2 稳定性指标

- 黄金链路通过率 `= 100%`
- 统一结果可渲染率 `> 95%`
- apply preview 成功率 `> 95%`
- apply commit 成功率 `> 95%`
- `PPT` 共创当前页命中率 `> 95%`
- `PPT` 共创标题位命中率 `> 95%`
- 主链路成功率 `= 100%`
- 协议错误率 `= 0`
- `JSON` 解析失败率 `= 0`
- `think` 泄露率 `= 0`

### 7.3 架构指标

- 系统级 `V5 UI` 不直接依赖 provider 实现次数 `= 0`
- 新链路双真源数量 `= 0`
- provider 差异上浮到 UI 的 case 数 `= 0`

### 7.4 质量量化口径

建议统一沿用当前已落地的 scorecard 结构：

- `Reliability 30 + Quality 40 + UX 20 + Safety 10`
- 整体平均质量分 `>= 4.3/5.0`
- 高价值模块 `Explain / Code Review / PPT >= 4.5/5.0`
- `Chat / Translate / Polish >= 4.2/5.0`

nightly 建议统一输出：

- 成功率
- 协议合法率
- 平均质量分
- `P50 / P95` 耗时
- `think` 泄露率
- 失败 case 列表

## 7.5 当前测试 TODO

- 补 `PPT` 共创“最小完成条件校验 + 轻量 reprompt”回归测试
- 补图片/版式 patch 标准化后的执行器测试
- 在第一批修复后重跑 `PPT` 共创 6-case 基准并刷新验收结论

---

## 8. 推荐测试目录

```text
tests_next/
  contract/
    test_context_api.py
    test_task_api.py
    test_apply_api.py
  golden_flow/
    test_review_flow.py
    test_follow_up_flow.py
    test_apply_flow.py
  integration/
    test_agent_gateway.py
    test_broker_gateway.py
    test_stores.py
  ui/
    test_smart_copilot_state_machine.py
    test_smart_copilot_actions.py
```

---

## 9. 测试环境建议

### 9.1 单元/契约

- 使用 fake store
- 使用 fake provider
- 使用 fake broker adapter

### 9.2 集成

- 最少跑一个真实 `Hermes local` provider
- 最少跑一条真实 preview/commit 链路

### 9.3 回归对照

- 用旧 `v5` 路径作为行为参考
- 对比同类输入的结果结构是否一致或可解释

---

## 10. 切主验收

## 10.1 Go 条件

- 三条黄金链路全部稳定通过
- 契约测试通过
- 数据模型状态迁移正确
- `replace_selection` 回写闭环稳定
- 无新旧双真源
- `Hermes local` 的断联、超时、事件流中断可被统一错误模型稳定承接

## 10.2 No-Go 条件

- event 流与最终 result 不一致
- preview/commit 经常失败
- UI 仍然需要 provider 特判
- 新 UI 仍依赖旧业务实现

---

## 11. 回归策略

### 11.1 每次迭代必须回归

- review flow
- follow-up flow
- apply flow

### 11.2 协议变更必须回归

- 所有 contract tests
- 结果结构渲染
- 错误码映射

### 11.3 Broker 变更必须回归

- context snapshot
- preview / commit
- 权限拒绝路径

---

## 12. 与其他文档关系

- `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`
- `docs/VNEXT_DATA_MODEL.md`
- `docs/VNEXT_UNIFIED_AGENT_API.md`
- `docs/VNEXT_MIGRATION_PLAYBOOK.md`
