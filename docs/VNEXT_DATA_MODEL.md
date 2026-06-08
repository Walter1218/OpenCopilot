# OpenCopilot vNext 数据模型与状态机

> 版本 vNext Draft 0.1 | 2026-06-08 | 定义 vnext 中 Task / Session / Context / Event / Apply 的领域模型与状态迁移

---

## 1. 文档定位

本文档解决的问题是：

- 新架构里什么才是“业务真相”
- 哪些对象必须进 Store
- 它们之间的关系是什么
- 每个核心对象有哪些状态与状态迁移

该文档是 `Unified API`、`Stores`、`UI 状态机`、`Gateway` 的共同基础。

---

## 2. 设计原则

### 2.1 单一真源

以下对象必须只有一份系统级真源：

- Task
- Session
- ContextSnapshot
- EventStream
- ApplyPreview

### 2.2 UI 不持有业务真相

UI 可以持有 ViewModel 状态，但不应持有真实任务状态或真实会话状态。

### 2.3 Provider 不持有系统真相

provider 可以持有临时 `run_id`，但该 `run_id` 不能代替系统 `task_id`。

### 2.4 Event 是任务事实流，不是日志替代品

EventStore 保存的是 UI/系统要消费的任务事件，不是低层 debug log 的全部替代。

---

## 3. 核心对象

## 3.1 Task

### 定义

Task 表示一次完整任务执行，是新架构中的一级对象。

### 关键字段

```json
{
  "task_id": "task_xxx",
  "session_id": "sess_xxx",
  "context_snapshot_id": "ctx_xxx",
  "action": "review",
  "status": "running",
  "provider": "hermes_local",
  "created_at": "2026-06-08T12:00:00Z",
  "updated_at": "2026-06-08T12:00:03Z",
  "progress": {
    "stage": "planning",
    "percent": 35,
    "message": "正在规划执行路径"
  },
  "result_ref": null,
  "error_ref": null
}
```

### Task 的职责

- 表示一次用户请求
- 绑定上下文快照
- 绑定执行 provider
- 汇总最终结果或错误

### Task 不负责

- 保存原始 provider 全量流
- 保存 UI 展示布局
- 充当 session 替代品

---

## 3.2 Session

### 定义

Session 表示一组相关任务的对话或上下文连续性。

### 关键字段

```json
{
  "session_id": "sess_xxx",
  "mode": "smart_copilot",
  "created_at": "2026-06-08T12:00:00Z",
  "updated_at": "2026-06-08T12:05:00Z",
  "latest_task_id": "task_xxx",
  "summary": {
    "source_app": "word",
    "document_title": "Q3_Report.docx"
  }
}
```

### Session 的职责

- 维护多轮 follow-up 的连续性
- 连接一组 task
- 提供轻量上下文聚合入口

### Session 不负责

- 保存每一条 delta 事件
- 保存 UI 面板状态

---

## 3.3 ContextSnapshot

### 定义

ContextSnapshot 表示某次触发时的环境快照。

### 关键字段

```json
{
  "context_snapshot_id": "ctx_xxx",
  "trigger": "double_right_click",
  "source_app": "word",
  "selection": {
    "text": "当前选中文本"
  },
  "document": {
    "title": "Q3_Report.docx",
    "page": 4
  },
  "cursor_context": {
    "before": "前文",
    "after": "后文"
  },
  "attachments": [],
  "created_at": "2026-06-08T12:00:00Z"
}
```

### ContextSnapshot 的职责

- 冻结触发当下的上下文
- 作为 task 的输入引用
- 作为结果可追溯性的来源

### ContextSnapshot 不负责

- 实时跟踪宿主变化
- 代表当前宿主实时状态

---

## 3.4 Event

### 定义

Event 表示任务执行过程中的可消费事实。

### 关键字段

```json
{
  "event_id": "evt_xxx",
  "task_id": "task_xxx",
  "type": "task.stage_changed",
  "sequence": 12,
  "payload": {
    "stage": "planning",
    "message": "正在规划执行路径"
  },
  "created_at": "2026-06-08T12:00:01Z"
}
```

### Event 的职责

- 驱动 UI 增量渲染
- 为任务执行过程提供可追溯的事件流
- 统一不同 provider 的流式表现

### Event 不负责

- 保存全部 debug 细节
- 替代最终结果

---

## 3.5 Result

### 定义

Result 表示任务完成后的最终结构化输出。

### 关键字段

```json
{
  "summary": "发现两处逻辑不一致",
  "artifacts": [],
  "evidence": [],
  "warnings": [],
  "next_actions": [],
  "apply_operations": []
}
```

### Result 的职责

- 作为 UI 最终渲染对象
- 作为 apply preview 的输入来源
- 作为切主后行为一致性的对照对象

---

## 3.6 ApplyPreview

### 定义

ApplyPreview 表示用户确认回写之前的预览对象。

### 关键字段

```json
{
  "preview_id": "ap_xxx",
  "task_id": "task_xxx",
  "operation": {
    "op": "replace_selection",
    "target": "current_selection"
  },
  "diff": {
    "before": "原文",
    "after": "修改后文本"
  },
  "safe_to_commit": true,
  "warnings": []
}
```

### ApplyPreview 的职责

- 承接 apply 前的审阅步骤
- 隔离结果生成与真实回写

### ApplyPreview 不负责

- 直接修改宿主环境

---

## 4. 关系模型

```text
Session
  -> Task (1:N)
Task
  -> ContextSnapshot (N:1)
Task
  -> Event (1:N)
Task
  -> Result (1:1)
Task
  -> ApplyPreview (1:N, optional)
```

### 关系解释

- 一个 Session 下可以有多个 Task
- 一个 Task 绑定一个 ContextSnapshot
- 一个 Task 会产生多条 Event
- 一个 Task 最终有一个 Result
- 一个 Task 可产生多个 ApplyPreview 尝试

---

## 5. Task 状态机

### 5.1 状态定义

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

### 5.2 状态流转

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> running -> cancelled
queued -> cancelled
```

### 5.3 状态约束

- `succeeded / failed / cancelled` 为终态
- 终态后不可直接回到 `running`
- `retry` 必须创建新 task，而不是复活旧 task

---

## 6. Task Progress Stage

### 6.1 推荐阶段

- `context_collecting`
- `security_check`
- `planning`
- `executing`
- `verifying`
- `result_building`
- `completed`

### 6.2 约束

- stage 是用户可理解的高层状态
- provider 原始阶段必须归一到这些阶段之一

---

## 7. Session 状态机

Session 不需要复杂运行态，只需要生命周期态：

- `active`
- `archived`

### 原则

- Session 是组织对象，不是执行对象
- Session 的变化频率远低于 Task

---

## 8. Apply 状态机

### 8.1 Preview 状态

- `created`
- `confirmed`
- `expired`
- `failed`

### 8.2 Commit 状态

- `pending`
- `succeeded`
- `failed`

### 8.3 状态流转

```text
preview created
  -> confirmed
  -> commit pending
  -> commit succeeded | commit failed
```

### 原则

- 没有 preview 默认不能直接 commit
- 一个 preview 过期后不能再次复用

---

## 9. Event 模型

### 9.1 事件类型

- `task.created`
- `task.stage_changed`
- `task.delta`
- `task.artifact`
- `task.warning`
- `task.completed`
- `task.failed`
- `task.cancelled`

### 9.2 事件顺序

- 每个 task 的 event 都必须带 `sequence`
- UI 按 `sequence` 重放
- EventStore 负责顺序一致性

### 9.3 事件与结果关系

- Event 是过程
- Result 是终局
- 不能只依赖 Event 拼最终结果

---

## 10. Store 职责划分

## 10.1 TaskStore

负责：

- create / update / get task
- task status transitions

## 10.2 SessionStore

负责：

- create / archive / list session
- session 与 task 关联

## 10.3 ContextStore

负责：

- create / get context snapshot
- 按引用返回冻结上下文

## 10.4 EventStore

负责：

- append event
- list events by task
- 按 sequence 返回事件流

## 10.5 ApplyPreviewStore

如果单独实现，负责：

- create preview
- mark confirmed
- mark expired

---

## 11. UI 与数据模型的关系

### 11.1 UI 消费的对象

UI 直接消费：

- ContextSnapshot summary
- Task status/progress
- Event stream
- Result
- ApplyPreview

### 11.2 UI 不拥有的对象

UI 不应单独拥有：

- 系统 task 真相
- 系统 session 真相
- provider 原始 run 状态

---

## 12. Gateway 与数据模型的关系

### 12.1 Agent Gateway

负责：

- 读取 Task / Session / ContextSnapshot
- 追加 Event
- 写回 Result

### 12.2 Broker Gateway

负责：

- 创建 ContextSnapshot
- 创建 ApplyPreview
- 提交 ApplyCommit 结果

---

## 13. 常见错误建模

### 13.1 Task 错误

- `AGENT_TIMEOUT`
- `AGENT_UNAVAILABLE`
- `PROVIDER_STREAM_ERROR`
- `SECURITY_BLOCKED`

### 13.2 Context 错误

- `CONTEXT_NOT_AVAILABLE`
- `BROKER_DENIED`

### 13.3 Apply 错误

- `BROKER_APPLY_FAILED`
- `APPLY_PREVIEW_EXPIRED`

---

## 14. 实现建议

### 14.1 第一阶段建议使用内存 + 可替换持久化接口

原因：

- 先保证模型正确
- 后续再替换成 SQLite / 文件 / 更完整持久化

### 14.2 ID 策略

推荐：

- `task_*`
- `sess_*`
- `ctx_*`
- `evt_*`
- `ap_*`

### 14.3 时间字段

统一采用 ISO 8601 UTC 时间字符串

---

## 15. 与其他文档关系

- `docs/VNEXT_UNIFIED_AGENT_API.md`：定义外部 DTO 与接口
- `docs/VNEXT_MODULE_BOUNDARIES.md`：定义哪些层可以读写这些模型
- `docs/VNEXT_SMART_COPILOT_UI_SPEC.md`：定义 UI 如何消费这些模型
- `docs/VNEXT_AGENT_GATEWAY_DESIGN.md`：定义 Gateway 如何生产这些模型
- `docs/VNEXT_TEST_AND_ACCEPTANCE.md`：定义如何验证这些模型的正确性
