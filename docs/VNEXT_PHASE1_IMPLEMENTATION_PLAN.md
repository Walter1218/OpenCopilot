# OpenCopilot vNext 第一阶段实施清单

> 版本 vNext Draft 0.1 | 2026-06-08 | 面向双击右键 Smart Copilot 的第一阶段重构实施方案

---

## 1. 文档定位

本文档将 `docs/VNEXT_REBUILD_BLUEPRINT.md` 落成第一阶段可执行方案，重点回答：

- 第一阶段到底做什么，不做什么
- 先动哪些模块，后动哪些模块
- 每个阶段的产出物、风险和验收标准是什么

本文档是 `方案级` 实施清单，不是逐文件开发任务单。

---

## 2. 第一阶段目标

### 2.1 业务目标

围绕 `双击右键召唤 Smart Copilot` 做出一条稳定、低复杂度、可验证的全新主链路：

`双击右键 -> 上下文快照 -> 创建任务 -> 流式结果 -> 预览回写 -> 确认应用`

### 2.2 架构目标

第一阶段必须同时满足以下约束：

- UI 只调用统一 API
- Agent 通过 Gateway 接入，不与 UI 直连
- Broker 能力只通过 API/ Gateway 参与，不暴露内部协议
- 新链路的 task/session/event/context 只有一份真源
- 新目录不依赖旧业务实现

### 2.3 稳定性目标

- 不破坏现有 `v5` 主入口
- 新链路可以独立演进
- 旧链路作为回归样本存在，但不进入新目录依赖树

---

## 3. 范围定义

### 3.1 第一阶段纳入范围

- 系统级入口继续使用 `SmartCopilotV5`
- 保留 `gui_next` 作为 `vnext` 轻量验证入口
- 新建 `platform_next/api/unified`
- 新建 `platform_next/gateway/agent_gateway`
- 新建 `platform_next/gateway/broker_gateway`
- 新建 `stores_next`
- 接入一个 `Hermes local` agent provider 作为过渡主 provider
- 跑通 `review / explain / polish / translate / ppt` 等已接动作
- 跑通 `apply preview / apply commit`
- `Studio` 共创窗口内 AI 编辑、重生成、建议分析统一复用 `V5AgentWorker -> vnext/Hermes`
- `V5` 埋点保留，并显式补齐 `ui_version / ui_surface / agent_backend / provider`
- 长任务改为“动态 read timeout + 后台事件消费”模式
- `PPT` 共创双智能体基准、第一批稳定性收口和文档同步

### 3.2 第一阶段明确不做

- 新版 Workspace
- 多 provider 前台切换
- 多 Agent 协作
- 完整历史 API 兼容
- 全量动作类型迁移
- 全量场景覆盖测试
- `PPT` story planner 双阶段架构
- 自动图片素材检索/生成与品牌视觉系统化编排
- 共创结果的持久化任务历史与跨进程恢复

### 3.3 Hermes 调试配置约定

第一阶段把 `Hermes local` 当成过渡 provider，因此接入方式必须是“用户可填写配置”，而不是在代码里写死端口或 profile。

推荐配置项如下：

```bash
HERMES_PROVIDER_PROFILE=coder
HERMES_PROFILE_ENV_FILE=
HERMES_BASE_URL=
HERMES_API_KEY=
```

说明：

- 调试阶段默认先写 `coder`
- 如果显式填写了 `HERMES_BASE_URL` / `HERMES_API_KEY`，优先使用显式值
- 如果没有显式填写，则先尝试 `HERMES_PROFILE_ENV_FILE` 或默认的 `~/.hermes/profiles/<profile>/.env`
- 如果首选 profile 不可用，则自动扫描 `~/.hermes/profiles/*/.env` 中可推导端口的 profile，并用 `/health` 验证后动态接入
- 如果没有探测到健康实例，才回退到首个可推导候选或默认值
- OpenCopilot 只读取这些配置，不反向依赖 Hermes 项目目录

---

## 4. 实施原则

### 4.1 先立契约，再写实现

第一阶段必须先冻结：

- Unified API 路由
- DTO 结构
- 任务事件类型
- Apply preview / commit 合同

### 4.2 先打通黄金链路，再扩展动作

优先保证一条链路完整闭环，不追求动作数量。

### 4.3 旧系统只作对照，不作依赖

旧代码可以帮助我们回答“原来如何工作”，但不能成为新链路的实现基础。

### 4.4 新目录先跑单链路，后补外围治理

先把运行时和交互主链路打通，再考虑性能、观测、调试面板等配套。

---

## 5. 阶段拆分

## 5.1 Phase A: 契约冻结

### 目标

把新系统边界钉死，避免后续边写边改协议。

### 产出物

- `docs/VNEXT_UNIFIED_AGENT_API.md`
- `docs/VNEXT_MODULE_BOUNDARIES.md`
- 本文档
- 统一错误码与事件类型清单

### 工程动作

- 确认 `/vnext/context/snapshots`
- 确认 `/vnext/tasks`
- 确认 `/vnext/tasks/{id}/events`
- 确认 `/vnext/apply/preview`
- 确认 `/vnext/apply/commit`
- 确认 `TaskStatus / EventType / ArtifactType / ErrorCode`

### 风险

- 协议抽象过大，导致第一阶段实现困难
- 协议抽象过小，未来第三方适配无法承接

### 缓解

- 所有 DTO 先以双击右键主链路为中心，不追求全场景泛化
- 在协议中预留扩展字段，但不提前实现复杂语义

---

## 5.2 Phase B: Stores 与 Gateway 骨架

### 目标

建立新链路的单一真源和中间编排层。

### 产出物

- `stores_next/task_store.py`
- `stores_next/session_store.py`
- `stores_next/event_store.py`
- `stores_next/context_store.py`
- `platform_next/gateway/agent_gateway/*`
- `platform_next/gateway/broker_gateway/*`

### 工程动作

- 定义 task 生命周期
- 定义 session 生命周期
- 定义 context snapshot 生命周期
- 定义 event append/read 模型
- 打通 create task -> store -> stream -> result 持久化

### 风险

- 状态模型不完整，后续 UI/Agent 会反复改
- Gateway 过早长成“新巨石”

### 缓解

- Stores 只负责 CRUD 与最小状态机，不承载复杂业务编排
- Gateway 只做适配与标准化，不吞业务语义

---

## 5.3 Phase C: Hermes Local Provider 接入

### 目标

让统一 Gateway 跑通第一个真实 provider，并用它验证新协议与新边界。

### 产出物

- `agents_next/providers/hermes_local/*`
- 统一结果构建器

### 工程动作

- 定义 `AgentProvider` 接口
- 接入 `Hermes local` provider
- 实现 review / explain / polish 最小能力集
- 输出统一 `Result DTO`

### 风险

- Hermes 输出协议与我们的 Result/Event 不完全一致
- 过早引入自研 runtime，导致第一阶段复杂度反弹

### 缓解

- 第一阶段只支持少量动作
- 统一输出结构优先，Hermes 只作为过渡执行内核
- 自研 runtime 收敛到第二阶段

---

## 5.4 Phase D: Broker Gateway 与回写闭环

### 目标

完成从真实上下文到回写确认的完整闭环。

### 产出物

- `broker_next/readers/*`
- `broker_next/writers/*`
- `platform_next/gateway/broker_gateway/*`

### 工程动作

- 接入 selection snapshot
- 接入 active document 基础摘要
- 接入 apply preview
- 接入 apply commit
- 为失败与权限拒绝定义标准错误

### 风险

- 宿主写回行为复杂，容易拖慢整条链路
- preview 与 commit 的一致性处理不清晰

### 缓解

- 第一阶段只支持最基本的 `replace_selection`
- 把复杂宿主差异放进 broker adapter 内部

---

## 5.5 Phase E: V5 UI 接线与 GUI Next 验证入口

### 目标

保持系统级入口继续使用 `V5` 同款 UI，同时把底层智能体执行统一切到 `vnext/Hermes`，并保留 `gui_next` 作为独立验证入口。

### 产出物

- `gui/v5/smart_copilot.py`
- `gui/v5/work_tab.py`
- `gui/v5/chat_tab.py`
- `gui/v5/studio_tab.py`
- `gui/v5/agent_worker.py`
- `gui/v5/navigation.py`
- `gui/main.py`
- `gui_next/smart_copilot/*`
- `unified_api_client`
- `event_stream client`

### 工程动作

- 双击右键继续召唤 `SmartCopilotV5`
- 保持 `Work / Chat / Studio` 页签与交互节奏不变
- 将 `V5AgentWorker` 的 AI 调用统一切到 `/vnext/*`
- 通过 `hermes_local` provider 执行真实 Hermes 任务
- 保留 `gui_next` 测试窗，继续验证 `vnext` API 与回写闭环

### 当前可交互测试基线

当前仓库已经提供一个可直接试用的桌面测试入口，用于验证 `gui_next -> /vnext/* -> Hermes local` 主链路：

- `gui_next/smart_copilot/shell/interactive_window.py`
- `gui_next/smart_copilot/app.py`
- `scripts/start_vnext_smart_copilot.sh`

当前交互测试窗支持：

- 手动输入 `source_app / document_title / selection_text / user_input`
- 选择 `review / explain / polish`
- 创建 context snapshot
- 创建 task 并轮询任务事件
- 预览 apply
- 提交 commit
- 当前测试脚本默认优先连接 `:8010`，若 `:8010` 已存在但未挂载 `vnext`，再回退探测 `:8000`

这一步是进入“可交互测试阶段”的基线；当前仓库已经把系统级双击右键召唤入口恢复为 `V5` 同款 UI，并把底层 AI 执行切到 `Hermes local`。

接入后的设计约束仍参考：

- `docs/VNEXT_AGENT_COMPARISON_BASELINE.md`

当前仍应记住的基线结论是：

- 第一阶段统一使用 `Hermes` 作为 `V5` 同款 UI 背后的第三方智能体
- 双击右键仍进入 `SmartCopilotV5`，不再显示新造的测试弹层
- `V5AgentWorker` 负责把 Work / Chat / Studio / Workspace Chat 的 AI 调用切到 `vnext/Hermes`
- `Studio` 共创窗口内部的 AI 编辑、重生成与建议分析链路也已统一复用 `V5AgentWorker(chat + ppt_editor)`，与外层 `V5 UI` 保持同一 Hermes 执行后端
- `V5AgentWorker` 对长任务的 UI 侧 read timeout 已改为按输入体量动态估算，降低超长文本被前端提前打断的概率
- `vnext` 任务事件现由后台线程持续消费 provider 事件并落库，前台 `/events` 只读取已落库结果，降低长任务阻塞风险
- `V5` 埋点继续保留，并显式写入 `ui_version=v5`、`ui_surface=desktop`、`agent_backend=hermes_vnext`、`provider=hermes_local`
- 已补一轮 `PPT` 共创 6-case 双智能体基准，结论不是“单边绝对胜出”，而是：自研更强在结论页/动作页叙事，`Hermes` 更强在图文与版式表达；当前共性优化点集中在“当前页命中、标题位协议、图片/版式共创、旧动作 JSON 兼容”
- 已完成第一批 `PPT` 共创收口：补强 `ppt_editor` 的“当前页命中/标题位”提示词约束，在 `AICopilotChatWidget` 中增加 render command 与旧 `action/update` JSON 的当前页归一化、标题位提升与数组兼容，并让 `RenderExecutor` 在图文页指令下同步落 `slide.layout`

### 风险

- UI 容易为了方便回到旧逻辑
- 状态机设计不清晰，交互复杂度失控

### 缓解

- UI 不直接 import runtime / broker / stores
- 所有 UI 状态围绕 `idle -> collecting -> running -> result -> applying` 五态设计

---

## 5.6 Phase F: 回归与切主准备

### 目标

把新链路从“能跑”提升到“可切主评估”。

### 产出物

- `tests_next/contract/*`
- `tests_next/golden_flow/*`
- 切主 checklist

### 工程动作

- 建立 API 契约测试
- 建立 3 条黄金链路测试
- 与旧 `v5` 做行为对照
- 统计时延、错误率、回写成功率

### 风险

- 只验证 happy path，切主时暴露边界问题

### 缓解

- 必测取消、超时、Broker 权限拒绝、上下文缺失、apply 失败

---

## 6. 当前状态与剩余动作

### 6.1 已完成

- `platform_next/api/unified`、`stores_next`、`agent_gateway`、`broker_gateway` 已落地
- `Hermes local provider` 已完成 profile 自动发现、gateway 自动拉起和统一错误映射
- 系统级桌面入口已恢复为 `SmartCopilotV5`，不再使用新造测试弹层替代正式 UI
- `V5AgentWorker` 已统一切到 `/vnext/* -> hermes_local -> Hermes API Server`
- `Studio` 共创内 AI 编辑、重生成、建议分析已统一走 `V5AgentWorker(chat + ppt_editor)`
- 长任务已改为“动态 read timeout + 后台事件消费”模式，降低 `ppt / translate` 被前端提前打断的概率
- `PPT` 共创 6-case 双智能体基准已完成，第一批稳定性修复已落地

### 6.2 当前 TODO

- 重新跑一轮 `PPT` 共创 6-case 基准，验证第一批“当前页命中 / 标题位 / 旧动作兼容”修复后的真实收益
- 在共创链路里补“最小完成条件校验 + 轻量 reprompt”，至少覆盖：
  - 当前页命中
  - 标题位命中
  - 目标 render type 命中
  - 建议条数下限
- 标准化图片/版式 patch 语义，避免 `layout=image_right` 混入普通 `text` 指令导致执行不完整
- 继续补 `PPT` 共创的人机实测，重点验证：
  - 标题改写页
  - 图文版式页
  - 长文档导入后的共创稳定性
- 评估是否补“导入 `.md` 文件来源标识”到共创日志，减少任务溯源歧义

---

## 7. 第一阶段验收标准

### 7.0 当前阶段说明

当前已经进入 `可交互测试` 阶段：

- 可通过 `scripts/start_vnext_smart_copilot.sh` 启动新测试窗
- 可通过 `python -m gui_next.smart_copilot.app --smoke-test` 运行无界面冒烟链路
- 可人工验证 `context -> task -> task events -> apply preview -> commit`
- 系统级双击右键入口当前保持 `SmartCopilotV5`
- `V5AgentWorker` 已连接到 `vnext/Hermes`
- 仍待持续回归的是宿主 Broker 真回写与整机人工交互验收

### 7.1 功能验收

- 可通过双击右键唤起 `SmartCopilotV5`
- 可自动获取当前选区摘要
- 可创建 review / explain / polish / translate / ppt 任务
- 可展示任务事件结果
- 可执行 apply preview / commit
- `Studio` 共创内 AI 编辑、重生成、建议分析与外层 `V5` 一样统一走 Hermes
- `PPT` 共创在标题改写、图文版式、旧动作兼容场景下不再出现明显的当前页漂移

### 7.2 架构验收

- 系统级 `gui/v5` 只通过 `/vnext/*` API 访问后端
- `gui_next` 仅作为验证入口，不再承担系统级正式 UI
- provider 差异未上浮到 UI
- task/session/event/context 都只有一份真源
- `Hermes local` 仅作为 provider 存在，不持有系统真源

### 7.4 当前文档 TODO

- `P0`：补共创结果校验器和自动轻量 reprompt
- `P0`：标准化 `layout/image_*` patch 语义并补执行器支持
- `P1`：重跑 `PPT` 共创 6-case 基准并刷新评测文档
- `P1`：补导入 `.md` 文件来源标识的透传与日志记录方案

### 7.3 体验验收

- 双击右键到浮层可见 `< 300ms`
- 创建任务到首条结果 `< 2.5s`
- 应用修改关键点击数 `<= 2`

---

## 8. 第一阶段的关键风险

### 8.1 抽象过度

问题：

- 过早为未来所有 agent/provider 设计协议，导致第一阶段无法收敛

策略：

- 协议对未来开放，但实现只围绕双击右键主链路

### 8.2 切回旧依赖

问题：

- 为了快，开发过程容易再次引用旧 bridge、旧 tasks_storage、旧 worker

策略：

- 文档和代码评审中把“是否回依赖旧实现”作为硬门槛

### 8.3 Gateway 巨石化

问题：

- 把业务语义、provider 适配、上下文编排、存储都塞进 Gateway

策略：

- Gateway 只做标准化与编排
- stores 与 runtime 必须各自独立

### 8.4 过渡 provider 固化为长期依赖

问题：

- 第一阶段接入 Hermes 后，后续不再推动自研 runtime 收敛

策略：

- 文档明确 `Hermes local` 是减法重构期的过渡主 provider
- `self_hosted` 目录和接口提前预留，但不纳入第一阶段交付

---

## 9. 切主前的 Go / No-Go 条件

### Go 条件

- 三条黄金链路稳定
- API 契约冻结
- 结构化结果可稳定渲染
- replace selection 可稳定工作
- 新 UI 无旧依赖
- Hermes 断联、超时、流中断都能被统一错误码正确承接

### No-Go 条件

- 回写失败率高
- 事件流与最终结果不一致
- 状态真源仍分裂
- UI 仍存在 provider 特判

---

## 10. 相关文档

- `docs/VNEXT_REBUILD_BLUEPRINT.md`
- `docs/VNEXT_UNIFIED_AGENT_API.md`
- `docs/VNEXT_MODULE_BOUNDARIES.md`
- `docs/VNEXT_SMART_COPILOT_UI_SPEC.md`
- `docs/VNEXT_AGENT_GATEWAY_DESIGN.md`

---

## 11. 第一阶段执行优先级

### P0: 必须先完成

- 冻结 Unified API / DTO / Task Events / ErrorCode
- 建立 task/event/context/apply 单一真源
- 打通 `Hermes local provider` 的 healthcheck / create run / stream events
- 打通 Broker 的 context snapshot 与 `replace_selection` preview/commit

### P1: 构成最小可用闭环

- `V5` Smart Copilot UI 接线保持原交互
- review / explain / polish 三类动作
- 统一结果渲染
- 取消、超时、权限拒绝错误恢复

### P2: 为第二阶段预埋

- 预留 `self_hosted` provider 接口与目录
- 预留 provider selector / fallback 能力位
- 补完整测试与切主 checklist
