# OpenCopilot vNext 重构蓝图

> 版本 vNext Draft 0.1 | 2026-06-08 | 面向下一阶段减法重构，不代表当前仓库已完成实现

---

## 1. 文档定位

本文档描述的是 OpenCopilot 下一阶段的重构目标，用来指导：

- 围绕 `双击右键召唤 Smart Copilot` 的最小闭环重建
- 将 `UI 交互层` 与 `智能体/Broker 层` 彻底解耦
- 通过新目录重构丢掉历史包袱，同时保障当前 `v5` 可持续稳定运行

本文档不是当前实现说明。当前真实架构请看 `ARCHITECTURE.md`，本文件只描述 `vnext` 目标态和迁移策略。

---

## 2. 重构目标

### 2.1 总目标

本轮重构的目标不是继续堆功能，而是做一次体系化减法：

- 聚焦 `双击右键 -> Smart Copilot -> 审查/修正 -> 确认回写`
- UI 只负责输入、状态展示、结果渲染，不再持有业务真相
- 智能体侧先通过可插拔第三方 provider 降低复杂度，再逐步收敛到自研 `coding agent runtime`
- Broker 保持系统级环境能力提供者角色，不混入业务语义
- UI 与智能体之间继续通过 API 解耦，为未来第三方智能体接入预留转发层

### 2.2 成功标准

重构完成的标志不是“新目录建好了”，而是下面 6 条成立：

1. `Smart Copilot` 前期主入口只围绕双击右键闭环运作
2. UI 不再直接 import 旧 Agent、旧 Bridge 全局状态、旧任务存储
3. 新链路中任务、会话、上下文、事件只有一份真源
4. 新 UI 只通过统一 API 调用智能体与 Broker 能力
5. 现有 `v5` 可作为兼容入口存在，但不会反向侵入新目录
6. 至少一条第三方智能体适配链路在架构上可插拔

---

## 3. 范围控制

### 3.1 本轮保留范围

前期只保留与 `Smart Copilot` 最小闭环直接相关的能力：

- 双击右键召唤轻量浮层
- 自动采集当前选区与基础上下文
- 发起一次智能体任务
- 流式返回结构化结果
- 预览修改并确认回写

### 3.2 本轮暂不扩展

以下能力不作为 `vnext` 第一阶段目标：

- 新版 Workspace 全量迁移
- 多面板工作台扩容
- 多智能体协作
- 大规模自治规划
- 所有历史 API 的一次性兼容
- 第三方智能体前台可见切换 UI

---

## 4. 目标架构

```text
User Interaction
  -> gui_next/smart_copilot
  -> platform_next/api/unified
  -> platform_next/gateway
       -> agent_gateway
       -> broker_gateway
  -> agents_next
       -> hermes_local provider (phase 1 primary)
       -> self_hosted coding agent runtime (phase 2 target)
       -> third-party adapters
  -> broker_next
       -> context readers
       -> apply-back writers
  -> stores_next
       -> task/session/event/context single source of truth
```

### 4.1 分层说明

#### UI 交互层

- 只负责召唤、输入、任务状态展示、结果渲染、回写确认
- 不直接访问智能体内部模块
- 不直接访问 Broker、本地存储、全局状态

#### Unified API 层

- 是 UI 唯一后端入口
- 负责 DTO 校验、错误语义统一、任务事件输出
- 负责把 UI 请求路由到 Agent Gateway 或 Broker Gateway

#### Agent Gateway 层

- 负责 provider 选择、任务协议标准化、结果标准化、流式事件统一
- 第一阶段优先接入 `Hermes local provider`
- 自研 runtime 作为第二阶段目标保留目录与协议位置

#### Agent Runtime 层

- 按标准 coding agent runtime 设计
- 负责任务理解、规划、工具执行、验证、结构化产出
- 不面向某个特定 UI 写死逻辑

#### Broker Gateway 层

- 只暴露环境能力：选区、活动文档、截图、回写
- 不承担业务语义判断
- 不直接被 UI 调用，统一经 API 层暴露

#### Stores 层

- 统一维护 task/session/event/context
- 任何其他层都不能私自维护业务真相

---

## 5. 设计原则

### 5.1 API 解耦优先

- UI 永远只面向统一 API
- 智能体和 Broker 的内部实现细节不进入 UI
- 任何第三方智能体接入都不应要求 UI 特判 provider

### 5.2 新目录独立重建

- `vnext` 新目录不复用旧业务实现代码片段
- 旧代码只作为行为参考和回归基线
- 新目录禁止 import 旧目录中的业务模块

### 5.3 单一真源

- task 只有一个 store
- session 只有一个 store
- context snapshot 只有一个 store
- event 只有一个 store

### 5.4 人在回路中

- 任何高影响输出默认先预览再回写
- 智能体输出需要携带 evidence / warnings / next actions
- UI 默认围绕“建议 + 确认 + 应用”设计

### 5.5 先减法后增强

- 先跑通一条稳定黄金链路
- 再逐步接入更多动作、更多 provider、更多上下文源

---

## 6. UI 方案

### 6.1 产品形态

UI 前期采用 `轻量浮层 + 单任务面板`：

- 靠近鼠标弹出
- 自动显示当前上下文摘要
- 提供少量高频动作
- 轮询并渲染任务事件结果
- 支持复制、继续追问、预览回写、确认应用

### 6.2 UI 职责边界

UI 只做以下 5 件事：

1. 采集用户输入与 UI 行为
2. 请求上下文快照
3. 发起任务与订阅事件
4. 渲染统一结构化结果
5. 发起回写预览与确认

UI 不做以下事情：

- 不缓存任务真相
- 不直接调用 Broker
- 不持有会话业务状态
- 不理解 provider 差异
- 不拼装智能体 prompt

### 6.3 UI 推荐目录

```text
gui_next/
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

## 7. 智能体方案

### 7.1 定位

第一阶段不把“自研 runtime 落地”作为主目标，而是采用两阶段策略：

- 第一阶段：以 `Hermes local provider` 作为过渡执行内核
- 第二阶段：补齐自研 `coding agent runtime`

这样做的目的不是长期依赖第三方，而是先验证：

- Unified API 是否合理
- Gateway / Broker 边界是否稳定
- UI 是否真的能只依赖统一协议

长期看，智能体仍然要收敛成标准的 `coding agent runtime`：

- 可以服务 Smart Copilot
- 可以服务未来 IDE/CLI/API 入口
- 可以与第三方智能体共同挂在统一 Gateway 后面

### 7.2 智能体职责

智能体负责：

- Task understanding
- Planning
- Tool use
- Verification
- Structured output
- Event emission

智能体不负责：

- UI 展示
- 宿主窗口控制
- 直接回写当前应用
- 与用户界面强绑定的状态管理

### 7.3 Agent Runtime 推荐目录

```text
agents_next/
  core/
    runtime/
      orchestrator.py
      task_context.py
      session_manager.py
      execution_state.py
    planning/
      planner.py
      plan_types.py
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
    contracts/
      provider.py
      events.py
      results.py
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

---

## 8. Broker 方案

### 8.1 Broker 定位

Broker 继续作为系统级环境能力层存在，负责：

- 当前选区读取
- 活动窗口/活动文档读取
- 浏览器/截图等上下文采集
- 结果回写

### 8.2 Broker 边界

Broker 不负责：

- 意图识别
- prompt 构建
- 任务路由
- 业务结果解释

### 8.3 Broker 推荐目录

```text
broker_next/
  gateway/
    context_gateway.py
    apply_gateway.py
  readers/
    selection_reader.py
    active_document_reader.py
    screenshot_reader.py
  writers/
    selection_writer.py
    ide_writer.py
  permissions/
    policy.py
```

---

## 9. Unified API 与 Gateway

### 9.1 Unified API 目标

Unified API 是 `UI -> 智能体/Broker` 的唯一合同层：

- 对 UI 隐藏 provider 细节
- 对 UI 隐藏 Broker 细节
- 标准化 task / event / result / apply 协议
- 为未来 API 转发层与第三方接入打地基

### 9.2 Gateway 目标

Gateway 不是薄转发，而是厚适配层：

- Request normalization
- Provider routing
- Stream adaptation
- Result normalization
- Error translation
- Policy enforcement

---

## 10. 迁移策略

### 10.1 总体策略

采用 `新目录重建 + 旧系统并存 + API 切换` 的绞杀式迁移，而不是原地大改。

### 10.2 迁移顺序

1. 定义统一 API 契约
2. 新建 `platform_next / agents_next / broker_next / stores_next / gui_next`
3. 跑通 `context snapshot -> create task -> task events -> apply preview -> apply commit`
4. 让新 Smart Copilot UI 只连接新 API
5. 用旧系统做行为回归对照
6. 新链路稳定后再删旧桥接和重复状态

### 10.3 禁止事项

- 新目录禁止 import 旧业务模块
- UI 禁止直接 import runtime / broker / stores
- 不允许在新链路里继续复制旧版任务存储和 session 状态
- 不允许为了兼容而把 provider 差异上浮到 UI

---

## 11. 里程碑建议

### M1: 契约冻结

- 完成 Unified Agent API
- 完成核心 DTO 与任务事件协议
- 完成目录边界和禁止依赖规则

### M2: 最小闭环跑通

- 双击右键召唤新浮层
- 获取 context snapshot
- 创建任务并轮询事件返回
- 输出统一 result
- 回写预览与确认

### M3: Hermes 过渡接入

- Gateway 接 `Hermes local provider`
- 跑通 review / explain / polish 基本链路
- 验证统一 result / event / error 协议

### M4: Broker 闭环与切主准备

- 完成上下文采集与 apply preview / commit 闭环
- 验证 Hermes 过渡方案下 UI/Broker/Store 边界稳定

### M5: 自研 runtime 预埋与切主

- 保留 `self_hosted` 目录与 provider 接口位置
- 完成阶段性切主与旧链路收缩

---

## 12. 验收指标

### 12.1 用户指标

- 双击右键到浮层可见 `< 300ms`
- 浮层到上下文摘要可见 `< 800ms`
- 首条流式结果 `< 2.5s`
- 应用确认路径 `<= 2` 次关键点击

### 12.2 工程指标

- UI 直连旧业务模块次数 `= 0`
- 新链路业务真源数量 `= 1`
- 统一结果可渲染率 `> 95%`
- 回写预览成功率 `> 95%`

### 12.3 架构指标

- 第一阶段至少稳定支持 1 个 `Hermes local provider`
- 保留 1 个自研 provider 的协议与目录落点
- provider 差异不上浮到 UI

---

## 13. 相关文档

- `ARCHITECTURE.md`：当前仓库真实架构
- `DEVELOPMENT.md`：当前仓库开发指南
- `docs/VNEXT_UNIFIED_AGENT_API.md`：统一 Agent API 契约草案
- `docs/VNEXT_MODULE_BOUNDARIES.md`：目录规划、依赖边界与迁移规则
