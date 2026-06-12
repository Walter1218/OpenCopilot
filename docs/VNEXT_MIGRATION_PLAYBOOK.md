# OpenCopilot vNext 迁移作战手册

> 版本 vNext Draft 0.1 | 2026-06-08 | 指导从当前架构平滑迁移到 vnext 新目录架构

---

## 1. 文档定位

本文档回答的是迁移层面的问题：

- 旧系统和新系统如何并存
- 哪些模块先迁，哪些模块后迁
- 哪些旧模块禁止继续扩展
- 什么时候可以切主，什么时候必须停手

本文档不替代蓝图和 API 契约，而是重构落地时的“作战地图”。

---

## 2. 迁移总原则

### 2.1 新旧并存，但边界单向

- 新系统可以参考旧系统
- 旧系统可以暂时与新系统并存
- 新系统不能回依赖旧系统实现

### 2.2 先建新主链路，再删旧旁路

迁移顺序必须是：

1. 新目录建起来
2. 最小闭环跑通
3. 回归验证通过
4. 切主
5. 删旧

### 2.3 迁移期间冻结新增复杂功能

在迁移窗口期：

- 不新增复杂 UI 面板
- 不新增新的旧链路状态存储
- 不扩写旧 bridge / 旧 worker 体系

---

## 3. 当前系统到 vnext 的映射

## 3.1 UI 层映射

| 当前模块 | vnext 去向 | 迁移策略 |
|----------|------------|----------|
| `gui/v5/smart_copilot.py` | `gui_next/smart_copilot/` | 参考交互行为，不复用实现 |
| `gui/v5/work_tab.py` | `gui_next/smart_copilot/components + viewmodels` | 保留行为样本，重建浮层方案 |
| `gui/v5/chat_tab.py` | `gui_next/smart_copilot/components + viewmodels` | follow-up 能力收敛为 task-based UI |
| `gui/v5/navigation.py` | `gui_next/shell/launcher.py` | 只保留入口逻辑，不复制旧窗口体系 |
| `gui/v5/workspace.py` | 暂不迁移 | 第一阶段不纳入 |
| `gui/v5/studio*` | 暂不迁移 | 第一阶段不纳入 |

## 3.2 Agent / API 层映射

| 当前模块 | vnext 去向 | 迁移策略 |
|----------|------------|----------|
| `opencopilot/agent/*` | `agents_next/core/*` | 借鉴职责，不直接复用旧实现 |
| `smart_copilot_api.py` | `platform_next/api/unified/*` | 不在其上继续缝补主链路 |
| `api/routers/*` | `platform_next/api/unified/*` | 新协议独立，不与旧 `/api/*` 混写 |
| `opencopilot.agent.caller` | `agents_next/providers/self_hosted/runtime_bridge.py` | 第二阶段才考虑借桥，第一阶段不进入主链路 |
| 本机 `Hermes API Server` | `agents_next/providers/hermes_local/*` | 第一阶段主 provider，通过 HTTP/SSE 适配，不反向依赖 Hermes 内部实现 |

## 3.3 Broker 层映射

| 当前模块 | vnext 去向 | 迁移策略 |
|----------|------------|----------|
| `opencopilot/broker/*` | `broker_next/*` | 能力抽象延续，接口重整 |
| `gui/v5/bridge.py` | `platform_next/gateway/broker_gateway/*` | 新 UI 不再直接依赖 |
| `system_probe_client.py` | `broker_next/readers/writers` | 只作为能力参考 |

## 3.4 状态层映射

| 当前状态源 | vnext 去向 | 迁移策略 |
|------------|------------|----------|
| `smart_copilot_api.tasks_storage` | `stores_next/task_store.py` | 严禁新链路继续依赖 |
| 路由局部 `_tasks` / `_sessions` | `stores_next/*` | 不复制，直接收敛 |
| UI 层零散 chat history | `stores_next/session_store.py` | 改为 session/task 模型 |

---

## 4. 旧模块分类

## 4.1 立即冻结扩展

这些模块不应继续承担新功能开发：

- `smart_copilot_api.py` 中的重复任务状态
- `gui/v5/bridge.py` 作为新主链路入口
- 旧 `gui/window.py` / `gui/workspace.py`
- 旧 worker 里新增智能体调用逻辑

## 4.2 保留为行为基线

这些模块可以继续作为参考：

- `gui/v5/smart_copilot.py`
- `gui/v5/work_tab.py`
- `gui/v5/chat_tab.py`
- `docs/UI_Redesign_Plan_v5.md`

## 4.3 暂不碰

这些模块第一阶段不进入迁移主线：

- `Studio` / `PPT` 共创链路
- `Workspace` 深层功能
- 大量历史 `/api/*` 长尾端点

---

## 5. 迁移阶段

## 5.1 Stage 0: 迁移前冻结

### 做什么

- 冻结 vnext 文档
- 冻结第一阶段范围
- 冻结“第一阶段主 provider = Hermes local，自研 runtime = 第二阶段”口径
- 停止旧链路新增复杂 feature

### 产出

- 文档包完成
- 评审结论
- 切主标准初版

## 5.2 Stage 1: 新目录立骨架

### 做什么

- 创建 `gui_next`
- 创建 `platform_next`
- 创建 `agents_next`
- 创建 `broker_next`
- 创建 `stores_next`

### 成功标准

- 目录存在
- 边界清晰
- CI 或评审规则能防止错误依赖

## 5.3 Stage 2: 契约跑通

### 做什么

- `context snapshot`
- `create task`
- `task events`
- `task result`
- `apply preview`
- `apply commit`

### 成功标准

- 能在不依赖旧 UI 的情况下跑通 API 闭环

## 5.4 Stage 3: 新 UI 接入

### 做什么

- 双击右键接新浮层
- 浮层只调 `/vnext/*`

### 成功标准

- 首条黄金链路可用

## 5.5 Stage 4: 回归验证

### 做什么

- 行为对照
- 性能基线
- 错误路径验证

### 成功标准

- 达到切主门槛

## 5.6 Stage 5: 切主

### 做什么

- 新 Smart Copilot 成为默认路径
- 旧路径保留受控 fallback

### 成功标准

- 主入口不再走旧智能体调用链

## 5.7 Stage 6: 删旧

### 做什么

- 删除重复状态
- 删除失效桥接
- 删除不再使用的旧入口

### 成功标准

- 不再存在第二份真源

---

## 6. 切主策略

### 6.1 推荐切主模式

采用 `灰度切主`：

- 默认指向新链路
- 保留一个开发/诊断开关回退旧链路

### 6.2 不推荐模式

- 一天内大爆炸式替换
- 没有回归数据直接切主
- 在 Studio / Workspace 一起迁移时同时切主

### 6.3 切主开关建议

- 环境变量
- 配置开关
- 开发模式下的隐藏入口

不建议长期暴露给普通用户。

---

## 7. 删除策略

## 7.1 可立即删除的不是代码，而是“扩展权”

先删掉旧模块的扩展许可，而不是一上来删文件。

### 具体表现

- 在开发指南中声明旧模块冻结
- PR 评审中拒绝在旧模块上继续长新主逻辑

## 7.2 先代理后删除

适用于：

- 旧任务路由
- 旧状态映射
- 旧入口 fallback

### 原则

- 代理层必须有删除计划
- 代理层不能成为长期基础设施

## 7.3 最终删除清单

最终应考虑删除或极度收缩：

- 重复任务存储
- 新 UI 不再需要的旧 worker
- 新主入口不再依赖的 bridge 分支
- 冗余任务路由

---

## 8. 风险清单

## 8.1 风险：新目录偷偷回依赖旧实现

症状：

- 为了赶进度，`gui_next` 直接 import `gui/v5/bridge.py`

对策：

- 把禁止依赖写入文档和评审 checklist

## 8.2 风险：双真源长期并存

症状：

- 新老 task/session 各有一套

对策：

- 上线前必须完成真源收敛检查

## 8.3 风险：旧功能仍不断叠加

症状：

- 迁移期间还在旧 smart copilot 上加特性

对策：

- 冻结旧主链路 feature，仅修 bug

## 8.4 风险：切主时 UI 行为回退

症状：

- 新 UI 跑起来了，但关键行为还偷偷走旧链路

对策：

- 做调用链观测和链路断言

---

## 9. 迁移评审清单

每周迁移评审都应该回答：

1. 本周是否新增了旧链路依赖
2. 新链路是否又引入新的状态真源
3. 是否有旧模块被继续扩写
4. 切主条件是否更接近
5. 是否有代理层超出原定职责

---

## 10. 推荐协作方式

### 10.1 角色分工

- 架构 owner：守边界与切主标准
- UI owner：守住 API-only 原则
- Agent owner：守住统一 result / event 协议
- Broker owner：守住 preview / commit 闭环
- QA owner：守住黄金链路与回归样本

### 10.2 决策原则

- 先保证主链路可用
- 再讨论通用性扩展
- 先解决双真源
- 再谈更丰富的 feature

---

## 11. 与其他文档关系

- `docs/VNEXT_REBUILD_BLUEPRINT.md`
- `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`
- `docs/VNEXT_MODULE_BOUNDARIES.md`
- `docs/VNEXT_DATA_MODEL.md`
- `docs/VNEXT_TEST_AND_ACCEPTANCE.md`
- `docs/VNEXT_IMPLEMENTATION_BACKLOG.md`
