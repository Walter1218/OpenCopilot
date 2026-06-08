# OpenCopilot vNext 文档总索引

> 版本 vNext Draft 0.1 | 2026-06-08 | 用于汇总下一阶段重构的全部设计与实施文档

---

## 1. 文档定位

这份索引文档解决 3 个问题：

1. `vnext` 现在到底有哪些文档
2. 每份文档分别回答什么问题
3. 不同角色应该按什么顺序阅读

注意：

- `vnext` 文档描述的是下一阶段目标态和迁移策略
- 当前仓库的真实实现与运行方式，仍以 `ARCHITECTURE.md`、`DEVELOPMENT.md` 为准

---

## 2. 文档地图

### 2.1 总体蓝图

| 文档 | 作用 |
|------|------|
| `docs/VNEXT_REBUILD_BLUEPRINT.md` | 总蓝图，定义目标、边界、总体架构、迁移原则 |
| `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md` | 第一阶段实施清单，定义阶段顺序、里程碑、Go/No-Go 条件 |

### 2.2 协议与边界

| 文档 | 作用 |
|------|------|
| `docs/VNEXT_UNIFIED_AGENT_API.md` | 统一 Agent API 契约，覆盖 Task / Event / Result / Apply |
| `docs/VNEXT_MODULE_BOUNDARIES.md` | 目录规划、允许依赖、禁止依赖、旧代码角色定义 |
| `docs/VNEXT_DATA_MODEL.md` | Task / Session / Context / Event / Apply 的领域模型与状态机 |

### 2.3 UI 与智能体

| 文档 | 作用 |
|------|------|
| `docs/VNEXT_SMART_COPILOT_UI_SPEC.md` | 双击右键 Smart Copilot UI 方案、状态机、组件拆分 |
| `docs/VNEXT_AGENT_GATEWAY_DESIGN.md` | Agent Gateway / Provider Adapter / Broker Gateway 设计 |

### 2.4 迁移与质量

| 文档 | 作用 |
|------|------|
| `docs/VNEXT_MIGRATION_PLAYBOOK.md` | 从旧架构到新架构的迁移手册、模块映射、切主策略 |
| `docs/VNEXT_TEST_AND_ACCEPTANCE.md` | 契约测试、黄金链路、回归测试、验收指标 |
| `docs/VNEXT_IMPLEMENTATION_BACKLOG.md` | 实施 backlog，按 Epic/Story/任务拆解首轮落地工作 |
| `docs/VNEXT_AGENT_COMPARISON_BASELINE.md` | 第三方 Hermes 与 v5 自研智能体的接入前基线对比 |

---

## 3. 推荐阅读顺序

### 3.1 如果你是项目 owner / 架构负责人

建议顺序：

1. `docs/VNEXT_REBUILD_BLUEPRINT.md`
2. `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`
3. `docs/VNEXT_MODULE_BOUNDARIES.md`
4. `docs/VNEXT_AGENT_GATEWAY_DESIGN.md`
5. `docs/VNEXT_SMART_COPILOT_UI_SPEC.md`
6. `docs/VNEXT_TEST_AND_ACCEPTANCE.md`

### 3.2 如果你是 UI 开发

建议顺序：

1. `docs/VNEXT_SMART_COPILOT_UI_SPEC.md`
2. `docs/VNEXT_UNIFIED_AGENT_API.md`
3. `docs/VNEXT_DATA_MODEL.md`
4. `docs/VNEXT_MODULE_BOUNDARIES.md`
5. `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`

### 3.3 如果你是 Agent / Gateway 开发

建议顺序：

1. `docs/VNEXT_AGENT_GATEWAY_DESIGN.md`
2. `docs/VNEXT_UNIFIED_AGENT_API.md`
3. `docs/VNEXT_DATA_MODEL.md`
4. `docs/VNEXT_MODULE_BOUNDARIES.md`
5. `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`

### 3.4 如果你是测试 / 交付负责人

建议顺序：

1. `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`
2. `docs/VNEXT_TEST_AND_ACCEPTANCE.md`
3. `docs/VNEXT_DATA_MODEL.md`
4. `docs/VNEXT_MIGRATION_PLAYBOOK.md`
5. `docs/VNEXT_AGENT_COMPARISON_BASELINE.md`

---

## 4. 文档之间的关系

```text
VNEXT_REBUILD_BLUEPRINT
  -> VNEXT_PHASE1_IMPLEMENTATION_PLAN
  -> VNEXT_UNIFIED_AGENT_API
  -> VNEXT_MODULE_BOUNDARIES
  -> VNEXT_SMART_COPILOT_UI_SPEC
  -> VNEXT_AGENT_GATEWAY_DESIGN
  -> VNEXT_DATA_MODEL
  -> VNEXT_MIGRATION_PLAYBOOK
  -> VNEXT_TEST_AND_ACCEPTANCE
  -> VNEXT_IMPLEMENTATION_BACKLOG
```

理解方式：

- `蓝图` 定方向
- `契约` 定接口
- `边界` 定纪律
- `数据模型` 定状态真相
- `UI / Gateway` 定模块方案
- `实施计划 / backlog` 定节奏
- `迁移 / 测试` 定风险控制

---

## 5. 文档使用规则

### 5.1 哪些文档描述“当前实现”

- `ARCHITECTURE.md`
- `DEVELOPMENT.md`
- `README.md`
- `README_CN.md`

### 5.2 哪些文档描述“vnext 目标态”

- 全部 `docs/VNEXT_*`

### 5.3 变更时如何同步

- 协议改动：同步 `VNEXT_UNIFIED_AGENT_API`
- 状态模型改动：同步 `VNEXT_DATA_MODEL`
- 依赖边界改动：同步 `VNEXT_MODULE_BOUNDARIES`
- 阶段节奏改动：同步 `VNEXT_PHASE1_IMPLEMENTATION_PLAN` 与 `VNEXT_IMPLEMENTATION_BACKLOG`
- UI 交互改动：同步 `VNEXT_SMART_COPILOT_UI_SPEC`
- Gateway/provider 设计改动：同步 `VNEXT_AGENT_GATEWAY_DESIGN`

---

## 6. 审阅重点

你在审文档时，建议重点看这 6 件事：

1. 是否真的围绕 `双击右键 Smart Copilot` 收敛范围
2. UI 是否真的只通过 API 工作
3. provider 差异是否真的被压在 Gateway 内
4. task/session/context/event 是否真的只有一份真源
5. 新目录是否真的与旧业务实现脱钩
6. 切主前的测试与验收标准是否足够硬

---

## 7. 相关文档

- `ARCHITECTURE.md`
- `DEVELOPMENT.md`
- `docs/UI_Redesign_Plan_v5.md`
