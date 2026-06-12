# OpenCopilot vNext 实施 Backlog

> 版本 vNext Draft 0.1 | 2026-06-08 | 将第一阶段重构拆成 Epic / Story / 任务清单

---

## 1. 文档定位

本文档把 `vnext` 第一阶段从“方案”拆到“可执行 backlog”，用于：

- 开迭代
- 拆任务
- 分配 owner
- 跟踪依赖关系

本文档不是精确工时表，但已足够作为首轮执行 backlog。

---

## 2. Epic 总览

| Epic | 目标 |
|------|------|
| E1 | 冻结协议与边界 |
| E2 | 建立 stores 与数据模型 |
| E3 | 建立 Unified API 与 Gateway 骨架 |
| E4 | 接入 Hermes local provider |
| E5 | 接入 Broker Gateway 与 apply 闭环 |
| E6 | 实现 Smart Copilot 新浮层 UI |
| E7 | 建立测试与切主评估体系 |

---

## 3. Backlog 细项

## E1: 冻结协议与边界

### Story E1-S1: 冻结 Unified API 协议

- 确认 `context snapshot` DTO
- 确认 `task` DTO
- 确认 `result` DTO
- 确认 `apply preview / commit` DTO
- 确认任务事件列表

### Story E1-S2: 冻结数据模型

- 确认 Task 状态机
- 确认 Session 模型
- 确认 ContextSnapshot 模型
- 确认 Event sequence 约束

### Story E1-S3: 冻结依赖边界

- 明确允许依赖矩阵
- 明确禁止依赖矩阵
- 明确旧代码冻结范围

---

## E2: 建立 Stores 与数据模型

### Story E2-S1: 实现 TaskStore

- create task
- update task status
- persist result ref / error ref
- query by task id

### Story E2-S2: 实现 SessionStore

- create session
- append task to session
- archive session
- get latest task

### Story E2-S3: 实现 ContextStore

- create snapshot
- query snapshot
- snapshot summary builder

### Story E2-S4: 实现 EventStore

- append event
- list events by task
- sequence ordering

### Story E2-S5: 实现 ApplyPreviewStore

- create preview
- mark confirmed
- expire preview

---

## E3: 建立 Unified API 与 Gateway 骨架

### Story E3-S1: 建 API 基础路由

- `POST /vnext/context/snapshots`
- `POST /vnext/tasks`
- `GET /vnext/tasks/{id}`
- `GET /vnext/tasks/{id}/events`
- `POST /vnext/apply/preview`
- `POST /vnext/apply/commit`

### Story E3-S2: 建 Agent Gateway 骨架

- provider registry
- provider selector
- request normalizer
- stream adapter
- response normalizer
- error mapper

### Story E3-S3: 建 Broker Gateway 骨架

- context service
- apply service
- permission guard
- broker error mapper

---

## E4: 接入 Hermes local provider

### Story E4-S1: 定义 Provider 接口

- create_run
- stream_events
- cancel_run
- get_result

### Story E4-S2: 实现 Hermes local adapter

- request mapping
- result mapping
- error mapping
- healthcheck
- run / event stream mapping

### Story E4-S3: 接 review / explain / polish

- review 最小任务链
- explain 最小任务链
- polish 最小任务链

### Story E4-S4: 统一结果构建

- summary
- artifacts
- warnings
- evidence
- apply operations

### Story E4-S5: 预留 self-hosted provider 接口

- 保留 `self_hosted` 目录位置
- 保留 runtime bridge 接口
- 不进入第一阶段交付

---

## E5: 接入 Broker Gateway 与 apply 闭环

### Story E5-S1: 实现 Context Snapshot

- selection reader
- source app reader
- document summary builder

### Story E5-S2: 实现 Apply Preview

- replace selection preview builder
- diff generator
- preview persistence

### Story E5-S3: 实现 Apply Commit

- replace selection writer
- commit result mapper
- failure recovery result

---

## E6: 实现 Smart Copilot 新浮层 UI

### Story E6-S1: 浮层骨架

- launcher
- floating panel
- close / esc / outside click

### Story E6-S2: Context 与 Action 区

- context card
- action bar
- 与 `summon_vm` 的 context snapshot 接线

### Story E6-S3: Task 渲染

- stage render
- delta render
- artifact render
- warning render

### Story E6-S4: Apply 交互

- `task_vm` 内聚 preview / commit
- commit button
- apply result feedback

### Story E6-S5: Follow-up

- new task creation
- result append display
- follow-up 输入框作为后续增强，不列入当前最小闭环

---

## E7: 建立测试与切主评估体系

### Story E7-S1: Contract Tests

- context API
- task API
- apply API

### Story E7-S2: Golden Flow Tests

- review flow
- follow-up flow
- apply flow

### Story E7-S3: 架构约束检查

- import boundary check
- no old-state dependency check

### Story E7-S4: 切主评估

- latency report
- success rate report
- go/no-go checklist

---

## 4. 优先级建议

### P0

- E1-S1
- E1-S2
- E1-S3
- E2-S1
- E2-S3
- E2-S4
- E3-S1
- E3-S2

### P1

- E2-S2
- E2-S5
- E3-S3
- E4-S1
- E4-S2
- E4-S3
- E5-S1

### P2

- E4-S4
- E4-S5
- E5-S2
- E5-S3
- E6-S1
- E6-S2
- E6-S3

### P3

- E6-S4
- E6-S5
- E7-S1
- E7-S2
- E7-S3
- E7-S4

---

## 5. 依赖关系

```text
E1 -> E2 -> E3 -> E4 -> E5 -> E6 -> E7
```

### 关键依赖

- UI 开发依赖 Unified API 冻结
- Gateway 开发依赖数据模型冻结
- Hermes local adapter 依赖本机 Hermes API Server 探活通过
- Apply 流依赖 Broker Gateway 骨架
- 切主评估依赖 Golden Flow 稳定

---

## 6. 建议 owner 分工

### UI Owner

- E6

### Agent/Gateway Owner

- E3
- E4

### Broker Owner

- E5

### Data/Infra Owner

- E2

### QA/Release Owner

- E7

### Architecture Owner

- E1
- 跨 Epic 评审

---

## 7. Definition of Done

### Story 完成条件

- 代码可运行
- 对应文档同步
- 基本测试通过
- 不引入新的旧依赖

### Epic 完成条件

- 关键场景贯通
- 与上游/下游契约一致
- 通过一次阶段评审

---

## 8. 建议看板列

- `Todo`
- `Ready`
- `In Progress`
- `Blocked`
- `Review`
- `Verified`
- `Done`

### Blocked 常见原因

- DTO 未冻结
- Gateway 接口未定
- Broker 能力未准备
- 旧系统行为样本不清楚

---

## 9. 每周同步建议

每周同步最好回答：

1. 当前主阻塞在哪个 Epic
2. 是否出现边界回退
3. 是否出现第二份真源
4. 是否满足下一周的切入条件

---

## 10. 与其他文档关系

- `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`
- `docs/VNEXT_DATA_MODEL.md`
- `docs/VNEXT_TEST_AND_ACCEPTANCE.md`
- `docs/VNEXT_MIGRATION_PLAYBOOK.md`
