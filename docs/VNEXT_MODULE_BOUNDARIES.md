# OpenCopilot vNext 目录规划、依赖边界与迁移规则

> 版本 vNext Draft 0.1 | 2026-06-08 | 约束新目录重构，避免再次耦合回旧实现

---

## 1. 文档定位

本文档回答 4 个问题：

1. `vnext` 新目录怎么拆
2. 各模块职责边界是什么
3. 哪些依赖被允许，哪些依赖被禁止
4. 旧代码在迁移期应该扮演什么角色

---

## 2. 总体原则

### 2.1 新目录优先

`vnext` 重构在全新目录内进行，不在旧目录上继续缝补主链路。

### 2.2 不复用旧实现

- 可以参考旧行为
- 可以基于旧链路做回归测试
- 不能把旧业务代码片段直接 copy 到新目录继续演化

### 2.3 边界硬约束

- UI 只能依赖 Unified API DTO 与客户端
- Agent 不能依赖 UI
- Broker 不能依赖 UI
- Broker 不能持有业务语义
- 所有业务状态只能由 Stores 层管理

---

## 3. 目标目录

```text
OpenCopilot/
├── gui_next/
│   └── smart_copilot/
│       ├── shell/
│       ├── components/
│       ├── viewmodels/
│       └── services/
├── platform_next/
│   ├── api/
│   │   └── unified/
│   └── gateway/
│       ├── agent_gateway/
│       └── broker_gateway/
├── agents_next/
│   ├── core/
│   └── providers/
├── broker_next/
│   ├── gateway/
│   ├── readers/
│   ├── writers/
│   └── permissions/
├── stores_next/
│   ├── task_store.py
│   ├── session_store.py
│   ├── event_store.py
│   └── context_store.py
└── tests_next/
    ├── contract/
    ├── golden_flow/
    └── integration/
```

---

## 4. 模块职责

### 4.1 `gui_next/`

职责：

- 右键召唤 Smart Copilot UI
- 输入收集
- 任务状态展示
- 结构化结果渲染
- 回写确认

不负责：

- 业务真相存储
- 任务执行
- provider 选择
- 宿主环境读写

### 4.2 `platform_next/api/unified/`

职责：

- 暴露 `/vnext/*` API
- 做 DTO 校验与错误码统一
- 为 UI 提供 REST + Task Event Feed 合同

不负责：

- provider 实现
- UI 逻辑
- Broker 底层 probe 细节

### 4.3 `platform_next/gateway/agent_gateway/`

职责：

- provider routing
- request normalization
- stream adaptation
- result normalization
- error translation
- policy enforcement

不负责：

- UI 呈现
- 宿主回写执行
- 持久化业务真相

### 4.4 `platform_next/gateway/broker_gateway/`

职责：

- context snapshot 组装
- apply preview / commit 编排
- 权限策略检查

不负责：

- 任务理解
- prompt 设计
- 模型执行

### 4.5 `agents_next/`

职责：

- 标准 coding agent runtime
- task understanding
- planning
- tool execution
- verification
- structured result output

不负责：

- UI 状态
- 宿主环境窗口控制
- 直接写回当前应用

### 4.6 `broker_next/`

职责：

- 选区读取
- 活动文档读取
- 截图和浏览器内容读取
- 结果回写

不负责：

- 业务语义
- provider 特性
- 任务状态流转

### 4.7 `stores_next/`

职责：

- task 真源
- session 真源
- event 真源
- context snapshot 真源

不负责：

- UI 业务编排
- provider 逻辑
- Broker 细节

---

## 5. 允许依赖矩阵

| From | Allowed |
|------|---------|
| `gui_next` | `platform_next/api DTO/client` |
| `platform_next/api` | `platform_next/gateway`, `stores_next` |
| `agent_gateway` | `agents_next`, `stores_next`, 共享 contracts |
| `broker_gateway` | `broker_next`, `stores_next`, 共享 contracts |
| `agents_next` | 内部 contracts / tool abstractions / shared schemas |
| `broker_next` | 内部 adapters / permissions / shared schemas |
| `stores_next` | 基础模型与序列化工具 |

---

## 6. 禁止依赖矩阵

| From | Forbidden |
|------|-----------|
| `gui_next` | `agents_next`, `broker_next`, `stores_next`, 旧 `gui/` 业务模块 |
| `agents_next` | `gui_next`, 旧 `gui/v5`, 旧 `bridge` |
| `broker_next` | `gui_next`, `agents_next` 业务逻辑 |
| `stores_next` | `gui_next`, provider 实现 |
| `platform_next/api` | 旧 `smart_copilot_api.py` 业务全局状态 |

### 6.1 特别禁止

- 新目录禁止 import `smart_copilot_api.tasks_storage`
- 新目录禁止 import `gui/v5/bridge.py`
- 新目录禁止 import 旧 `worker` 直接驱动智能体
- 不允许在 `gui_next` 里写 provider 分支判断

---

## 7. 旧代码在迁移期的角色

### 7.1 允许的角色

- 行为参考
- 黄金链路回归对照
- 临时兼容入口
- 数据样本和测试来源

### 7.2 不允许的角色

- 新系统的业务依赖源
- 新系统的模块库
- 新系统的状态真源
- 新系统的架构模板实现

---

## 8. 推荐模块骨架

### 8.1 `platform_next/gateway/agent_gateway/`

```text
agent_gateway/
  registry.py
  selector.py
  request_normalizer.py
  response_normalizer.py
  stream_adapter.py
  policy_guard.py
  timeout_controller.py
  error_mapper.py
```

### 8.2 `agents_next/providers/`

```text
providers/
  hermes_local/
    adapter.py
    dto_mapper.py
    stream_adapter.py
    error_mapper.py
    healthcheck.py
  self_hosted/
    adapter.py
    runtime_bridge.py
  openai_compatible/
    adapter.py
  anthropic_compatible/
    adapter.py
  custom/
    adapter.py
```

### 8.3 `gui_next/smart_copilot/`

```text
smart_copilot/
  shell/
    launcher.py
    floating_panel.py
  components/
    context_card.py
    action_bar.py
    result_view.py
    apply_bar.py
  viewmodels/
    summon_vm.py
    task_vm.py
  services/
    unified_api_client.py
    event_stream.py
    ui_state.py
```

---

## 9. 迁移期的工程约束

### 9.1 代码规则

- 每个新模块必须在文件头注释里标明所属层
- 每个新服务模块必须说明上游允许依赖和下游允许暴露
- 禁止新目录直接读写旧全局变量

### 9.2 测试规则

- 新 API 先写 contract test
- 新 UI 至少覆盖 3 条黄金链路
- 新 provider adapter 必须通过统一结果格式测试

### 9.3 文档规则

- 新目录设计变更优先同步 `docs/VNEXT_*`
- 当前实现变更同步 `ARCHITECTURE.md` / `DEVELOPMENT.md`
- 不再把“目标态文档”写成“已落地事实”

---

## 10. 黄金链路

迁移期优先稳定以下 3 条链路：

### 10.1 右键审查

`双击右键 -> 采集选区 -> 创建任务 -> 返回结构化建议`

### 10.2 继续追问

`展示结果 -> 输入 follow-up -> 复用上下文 -> 返回追加结果`

### 10.3 增量回写

`生成预览 -> 用户确认 -> 回写当前选区 -> 成功反馈`

---

## 11. 删除策略

### 11.1 立即禁止继续扩展

- 旧版 UI 新功能
- 旧任务存储复制扩展
- 新增绕过 Pipeline 的临时调用链

### 11.2 先代理后删除

- 旧任务路由
- 旧 workspace 状态桥接
- 部分服务侧兼容 API

### 11.3 最后删除

- 旧 Smart Copilot 兼容入口
- 不再被调用的 Bridge 路径
- 与新链路功能重复的任务/session 状态逻辑

---

## 12. 评审清单

任何 `vnext` PR 在合并前都应回答这些问题：

1. 是否新增了跨层耦合
2. UI 是否仍只面向统一 API
3. 是否引入了第二份业务真相
4. provider 差异是否被留在 Gateway 内部
5. 新代码是否依赖了旧业务实现
6. 文档是否同步到 `docs/VNEXT_*`

---

## 13. 相关文档

- `docs/VNEXT_REBUILD_BLUEPRINT.md`
- `docs/VNEXT_UNIFIED_AGENT_API.md`
- `ARCHITECTURE.md`
- `DEVELOPMENT.md`
