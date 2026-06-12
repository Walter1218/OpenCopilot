# OpenCopilot vNext Unified Agent API 契约草案

> 版本 vNext Draft 0.1 | 2026-06-08 | 面向新目录重构，服务 UI / 自研 agent / 第三方 agent 统一接入

---

## 1. 文档定位

本文档定义 `vnext` 的统一任务 API 契约，目标是：

- 让 UI 只依赖一套稳定协议
- 让自研 coding agent 与第三方 agent 可以共同挂到统一 Gateway 后面
- 让 Broker 能力通过标准化接口参与任务闭环

该文档描述的是第一阶段实际协议与后续扩展方向。

当前仓库 Phase 1 已落地的子集：

- `POST /vnext/context/snapshots`
- `POST /vnext/tasks`
- `GET /vnext/tasks/{id}`
- `GET /vnext/tasks/{id}/events`
- `POST /vnext/apply/preview`
- `POST /vnext/apply/commit`

当前 `GET /vnext/tasks/{id}/events` 返回的是 JSON 事件列表，GUI 通过轮询消费；provider 内部可继续使用流式协议。

---

## 2. 设计目标

### 2.1 目标

- 统一 `task / event / result / apply` 模型
- UI 不感知 provider 差异
- 支持流式结果和结构化产物
- 支持回写预览与确认
- 为未来 API 转发层和 provider routing 预留空间

### 2.2 非目标

- 不试图覆盖所有历史 `/api/*` 端点
- 不为每类 UI 设计不同协议
- 不把 Broker 的系统细节直接暴露给 UI

---

## 3. 协议原则

1. `UI -> Unified API` 是唯一调用路径
2. 所有长任务统一抽象成 `Task`
3. 所有任务过程输出统一经 Task Event Feed
4. 所有最终结果统一为结构化 `Result`
5. 所有回写统一经 `Preview -> Commit`
6. provider 差异在 Gateway 内部被吸收

---

## 4. 资源模型

### 4.1 Context Snapshot

描述 UI 触发当下的环境快照。

### 4.2 Task

描述一次完整任务执行。

### 4.3 Artifact

描述任务生成的结构化产物，例如：

- patch
- structured suggestions
- rendered markdown
- diff preview
- follow-up hints

### 4.4 Event

描述任务执行过程中的阶段变化、增量输出、警告和完成事件。

### 4.5 Apply Operation

描述对宿主环境的潜在写回动作。

---

## 5. API 一览

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/vnext/context/snapshots` | 创建上下文快照 |
| `GET` | `/vnext/context/snapshots/{id}` | 查询上下文快照 |
| `POST` | `/vnext/tasks` | 创建任务 |
| `GET` | `/vnext/tasks/{id}` | 查询任务状态与结果 |
| `GET` | `/vnext/tasks/{id}/events` | 任务事件列表，供 UI 轮询 |
| `POST` | `/vnext/tasks/{id}/cancel` | 取消任务 |
| `POST` | `/vnext/tasks/{id}/retry` | 重试任务 |
| `POST` | `/vnext/apply/preview` | 生成回写预览 |
| `POST` | `/vnext/apply/commit` | 执行回写 |
| `GET` | `/vnext/agents` | 查询可用 provider |
| `POST` | `/vnext/agents/select` | 选择 provider 或 provider policy |

---

## 6. DTO 设计

### 6.1 Create Context Snapshot

```json
{
  "trigger": "double_right_click",
  "source_app": "word",
  "selection_text": "当前选中的文字",
  "document_title": "Q3_Report.docx",
  "metadata": {
    "locale": "zh-CN",
    "platform": "macOS"
  }
}
```

### 6.2 Context Snapshot Response

```json
{
  "context_snapshot_id": "ctx_123",
  "created_at": "2026-06-08T12:00:00Z",
  "summary": {
    "source_app": "word",
    "document_title": "Q3_Report.docx",
    "selection_chars": 128
  }
}
```

### 6.3 Create Task Request

```json
{
  "action": "review",
  "user_input": "帮我检查这段内容是否有逻辑问题，并给出增量修改建议",
  "context_snapshot_id": "ctx_123",
  "agent_preferences": {
    "provider": "hermes_local",
    "model": "default",
    "temperature": 0.2
  },
  "constraints": {
    "safe_apply_only": true,
    "max_latency_ms": 12000,
    "require_evidence": true
  }
}
```

### 6.4 Create Task Response

```json
{
  "task_id": "task_123",
  "status": "running",
  "provider": "hermes_local"
}
```

### 6.5 Task DTO

```json
{
  "task_id": "task_123",
  "status": "running",
  "action": "review",
  "provider": "hermes_local",
  "progress_stage": "planning",
  "progress_message": "正在分析上下文并选择执行路径",
  "provider_run_id": "run_123",
  "result": null,
  "error": null
}
```

### 6.6 Unified Result DTO

```json
{
  "summary": "发现两处逻辑不一致，并生成了更顺的改写版本",
  "artifacts": [
    {
      "id": "art_1",
      "type": "structured_suggestions",
      "title": "修改建议",
      "content": [
        {
          "kind": "issue",
          "severity": "major",
          "source_range": {
            "start": 10,
            "end": 28
          },
          "reason": "前后指标口径不一致",
          "suggestion": "统一为同比增速口径"
        }
      ]
    },
    {
      "id": "art_2",
      "type": "patch",
      "title": "建议改写",
      "content": {
        "format": "text_patch",
        "patch": "..."
      }
    }
  ],
  "evidence": [
    {
      "type": "selection",
      "snippet": "原文片段",
      "reason": "这里和后文结论冲突"
    }
  ],
  "apply_operations": [
    {
      "op": "replace_selection",
      "target": "current_selection",
      "preview_ref": "preview_123"
    }
  ],
  "warnings": [],
  "next_actions": [
    {
      "action": "apply",
      "label": "应用修改"
    },
    {
      "action": "follow_up",
      "label": "继续追问"
    }
  ]
}
```

### 6.7 Apply Preview Request

```json
{
  "task_id": "task_123",
  "apply_operation": {
    "op": "replace_selection",
    "target": "current_selection",
    "preview_ref": "preview_123"
  }
}
```

### 6.8 Apply Preview Response

```json
{
  "preview_id": "apply_preview_1",
  "target": {
    "type": "selection",
    "app": "word"
  },
  "diff": {
    "before": "原文",
    "after": "修改后文本"
  },
  "safe_to_commit": true,
  "warnings": []
}
```

### 6.9 Apply Commit Request

```json
{
  "preview_id": "apply_preview_1",
  "confirmed_by_user": true
}
```

### 6.10 Apply Commit Response

```json
{
  "status": "succeeded",
  "applied_at": "2026-06-08T12:00:08Z"
}
```

---

## 7. Task Event Feed

UI 只消费统一事件类型，不直接消费 provider 原始流。
当前 Phase 1 通过轮询拉取 JSON 事件列表，后续如需升级为推送式流，不改变事件类型语义。

### 7.1 事件列表

- `task.created`
- `task.stage_changed`
- `task.delta`
- `task.artifact`
- `task.warning`
- `task.completed`
- `task.failed`
- `task.cancelled`

### 7.2 事件示例

```json
{
  "task_id": "task_123",
  "events": [
    {
      "event_id": "evt_001",
      "type": "task.created",
      "sequence": 1,
      "payload": {"task_id": "task_123"}
    },
    {
      "event_id": "evt_002",
      "type": "task.stage_changed",
      "sequence": 2,
      "payload": {"stage": "planning", "message": "正在规划执行路径"}
    },
    {
      "event_id": "evt_003",
      "type": "task.completed",
      "sequence": 3,
      "payload": {"task_id": "task_123", "status": "succeeded"}
    }
  ]
}
```

### 7.3 事件约束

- `stage_changed` 只表达阶段，不承载最终结果
- `delta` 只用于增量文本，不用于结构化 artifact
- `artifact` 允许增量上屏结构化结果
- `completed` 后必须能通过 `GET /vnext/tasks/{id}` 拿到完整结果

---

## 8. 错误模型

```json
{
  "error": {
    "code": "AGENT_TIMEOUT",
    "message": "智能体执行超时",
    "retryable": true,
    "provider": "hermes_local",
    "details": {}
  }
}
```

### 8.1 推荐错误码

- `INVALID_REQUEST`
- `CONTEXT_NOT_AVAILABLE`
- `AGENT_UNAVAILABLE`
- `AGENT_TIMEOUT`
- `BROKER_DENIED`
- `BROKER_APPLY_FAILED`
- `UNSUPPORTED_ACTION`
- `PROVIDER_STREAM_ERROR`
- `SECURITY_BLOCKED`

### 8.2 错误约束

- 所有错误必须可 machine-readable
- UI 只能依赖 `code / message / retryable`
- provider 特有异常必须在 Gateway 中转换

---

## 9. Provider 模型

### 9.1 Provider Registry

统一维护可用智能体 provider：

- `hermes_local`
- `self_hosted`
- `openai_compatible`
- `anthropic_compatible`
- `custom`

### 9.2 Provider 选择策略

推荐默认由 Gateway 自动选择 provider：

- UI 可以传递 `agent_preferences`
- 但是否采纳、如何降级由 Gateway 决定

### 9.3 Provider 能力探测

`GET /vnext/agents` 返回：

```json
{
  "providers": [
    {
      "id": "hermes_local",
      "display_name": "Hermes Local Provider",
      "capabilities": ["streaming", "structured_result", "apply_preview"]
    }
  ]
}
```

---

## 10. 与 Broker 的关系

Unified API 不直接暴露 Broker 内部协议，只暴露面向任务的接口：

- 创建 context snapshot
- 回写预览
- 回写提交

UI 无需知道：

- 选区从哪种 probe 读取
- 当前文档如何识别
- 回写是通过哪种宿主适配器执行

---

## 11. 兼容与迁移建议

### 11.1 当前仓库迁移方向

- 新 UI 只接 `/vnext/*`
- 旧 `/api/*` 暂时保留，不与新协议强行混合
- 可以在 Gateway 内部短期代理旧实现，但不暴露给 UI

### 11.2 契约冻结建议

第一阶段先冻结以下内容：

- Context snapshot DTO
- Create task DTO
- Task result DTO
- Task Event Feed 事件类型
- Apply preview / commit 协议

未冻结前不建议并行开发多个 UI 客户端。

---

## 12. 相关文档

- `docs/VNEXT_REBUILD_BLUEPRINT.md`
- `docs/VNEXT_MODULE_BOUNDARIES.md`
- `ARCHITECTURE.md`
- `DEVELOPMENT.md`
