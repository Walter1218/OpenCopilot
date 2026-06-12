# OpenCopilot vNext Smart Copilot UI 交互方案

> 版本 vNext Draft 0.1 | 2026-06-08 | 该文档描述 `gui_next` 轻量验证 UI 的设计稿，不代表当前系统级正式入口

---

## 1. 文档定位

本文档描述 `vnext` 第一阶段的 `gui_next` Smart Copilot UI 方案，目标是：

- 围绕双击右键做最小闭环
- 让 UI 完全 API 驱动
- 把交互复杂度控制在可打磨范围内

当前事实口径：

- 系统级双击右键入口当前仍是 `SmartCopilotV5`
- `V5AgentWorker` 已接到 `vnext/Hermes`
- 本文档仅保留为 `gui_next` 轻量实验 UI 的交互设计参考

---

## 2. 设计目标

### 2.1 核心目标

让用户在任意宿主中完成以下操作，而不切换到重型工作台：

1. 双击右键召唤
2. 看到当前上下文摘要
3. 选择一个动作或补一句要求
4. 得到流式结果
5. 预览并确认应用

### 2.2 设计关键词

- 轻量
- 就地
- 不抢焦点
- 结果可信
- 回写可控

---

## 3. 交互原则

### 3.1 就地完成

浮层必须贴近触发位置，让用户视线不跳走。

### 3.2 少即是多

前期不做多标签工作台，不做复杂导航，不做过多动作按钮。

### 3.3 明确“AI 正在看什么”

每次任务都必须展示当前上下文摘要，降低黑盒感。

### 3.4 结构化优先于长文本

结果优先展示：

- 结论摘要
- 关键建议
- 证据来源
- 可应用操作

### 3.5 默认人在回路中

高影响结果不直接应用，先给 preview，再由用户 commit。

---

## 4. 产品形态

采用 `轻量浮层 + 单任务面板` 方案。

### 4.1 不采用的形态

- 不采用多 Tab 工作台
- 不采用常驻 Chat 窗口
- 不采用完整 Workspace 迁入
- 不采用 provider 切换面板

### 4.2 浮层结构

```text
┌──────────────────────────────────────┐
│ Header                              │
│ App / 文档 / 状态点 / 关闭          │
├──────────────────────────────────────┤
│ Context Card                        │
│ 当前选区 + 来源摘要                 │
├──────────────────────────────────────┤
│ Action Bar                          │
│ Review / Explain / Polish / More    │
├──────────────────────────────────────┤
│ Composer                            │
│ 补充一句要求                        │
├──────────────────────────────────────┤
│ Result View                         │
│ Stage / Delta / Artifacts / Evidence│
├──────────────────────────────────────┤
│ Apply Bar                           │
│ Copy / Follow-up / Preview / Apply  │
└──────────────────────────────────────┘
```

---

## 5. 页面模块

### 5.1 Header

职责：

- 显示来源应用
- 显示文档标题或上下文来源
- 显示在线/处理中状态
- 提供关闭入口

显示建议：

- 左侧：`[Word] Q3_Report.docx`
- 右侧：状态点 + 关闭按钮

### 5.2 Context Card

职责：

- 告诉用户 AI 当前正在看什么
- 在上下文缺失时给出明确提示

展示内容：

- 当前选区摘要
- 来源应用
- 可选文档标题
- 可选上下文完整度提示

不做：

- 不在这里切换复杂上下文源
- 不暴露 Broker 细节

### 5.3 Action Bar

前期只保留 4 个动作入口：

- `审查`
- `解释`
- `润色`
- `更多`

`更多` 前期可以只展开二级菜单，不进入重型工作台。

### 5.4 Composer

职责：

- 允许用户补一句约束
- 允许 follow-up

输入示例：

- “重点检查逻辑矛盾”
- “改成更正式的 B2B 风格”
- “只给增量修改，不要重写整段”

### 5.5 Result View

结果区需要分层渲染：

1. 当前阶段
2. 流式增量文本
3. 结构化 artifacts
4. 证据和 warning

不建议默认只渲染一整段 markdown。

### 5.6 Apply Bar

根据任务结果动态出现：

- `复制`
- `继续追问`
- `预览修改`
- `应用修改`

默认策略：

- 没有 apply operation 时，不显示 `预览修改/应用修改`
- 有 apply operation 时，先要求 preview，再允许 apply

---

## 6. UI 状态机

### 6.1 顶层状态

```text
idle
  -> collecting_context
  -> ready
  -> task_running
  -> result_ready
  -> preview_ready
  -> applying
  -> done
  -> error
```

### 6.2 状态说明

#### `idle`

- 尚未唤起

#### `collecting_context`

- UI 已弹出
- 正在请求 context snapshot

#### `ready`

- 上下文已拿到
- 用户可点击动作或补充输入

#### `task_running`

- 已创建 task
- 正在轮询 `/vnext/tasks/{id}/events` 事件列表

#### `result_ready`

- 已收到完整结果
- 允许复制、追问、预览修改

#### `preview_ready`

- 已拿到 apply preview
- 允许用户确认 apply

#### `applying`

- 已提交 commit
- 等待宿主回写结果

#### `done`

- 已成功完成

#### `error`

- 任何步骤失败，进入统一错误态

---

## 7. 核心交互流

## 7.1 首次召唤

1. 用户双击右键
2. UI 弹出浮层
3. 立即进入 `collecting_context`
4. 成功后展示 Context Card 与 Action Bar
5. 用户点击动作或输入补充要求

### 成功指标

- 浮层可见 `< 300ms`
- 上下文摘要可见 `< 800ms`

## 7.2 发起任务

1. UI 调用 `POST /vnext/tasks`
2. UI 进入 `task_running`
3. 通过事件轮询消费阶段、delta、artifact 事件
4. 渲染结果
5. 收到 completed 后进入 `result_ready`

### 体验要求

- 首条结果 `< 2.5s`
- 阶段状态可见
- 不因 provider 不同改变 UI 逻辑

## 7.3 继续追问

1. 用户在已有结果下补一句 follow-up
2. UI 复用最近一次上下文快照和 task 结果视图
3. 发起新 task
4. 结果继续在当前面板滚动呈现

### 原则

- follow-up 是新 task，不是 UI 层偷偷拼接临时状态

## 7.4 预览与应用

1. 用户点击 `预览修改`
2. UI 调用 `POST /vnext/apply/preview`
3. 渲染 before/after diff
4. 用户点击 `应用修改`
5. UI 调用 `POST /vnext/apply/commit`
6. 成功后进入 `done`

### 原则

- `应用修改` 默认不能跳过 preview
- preview 失败时要可退回 `result_ready`

---

## 8. 组件拆分建议

```text
gui_next/smart_copilot/
  shell/
    launcher.py
    floating_panel.py
    interactive_window.py
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

### 8.1 组件职责

#### `floating_panel.py`

- 窗口定位
- 焦点策略
- 生命周期管理
- 编排 `collect_context -> run_task -> preview/commit`

#### `interactive_window.py`

- 第一阶段桌面交互测试窗
- 连接 `FloatingPanel` 与 `/vnext/*`
- 用于手工验证新链路，不承载最终浮层形态承诺

#### `runtime/api_runtime.py`

- 在桌面入口内探测 `/vnext/*` API
- 当前主要由 `gui/v5/agent_worker.py` 复用，用于保持 `V5` 同款 UI 不变
- 当本机默认端口不可用或未挂载 `vnext` 时自动启动/回退

#### `context_card.py`

- 显示上下文摘要
- 显示来源状态

#### `action_bar.py`

- 固定动作入口
- 动作点击事件分发

#### `result_view.py`

- 渲染 stage / delta / artifacts / warnings

## 9. ViewModel 设计

### 9.1 `summon_vm`

负责：

- 浮层初始化
- context snapshot 请求
- 顶层状态切换

### 9.2 `task_vm`

负责：

- 创建 task
- 轮询 events
- 聚合 delta / artifact / completed
- 维护结果态
- 请求 preview / commit

### 9.3 ViewModel 约束

- ViewModel 可以组合状态
- ViewModel 不能直接调用 broker/runtime/stores
- ViewModel 只通过 `unified_api_client` 访问后端

---

## 10. 错误设计

### 10.1 错误分类

- `上下文错误`
- `任务错误`
- `事件流错误`
- `预览错误`
- `回写错误`

### 10.2 错误呈现原则

- 只显示用户可理解的信息
- 同时允许在调试模式查看错误码
- 提供明确下一步动作

### 10.3 错误恢复

- context 获取失败：允许重试
- task 失败：允许重试/复制输入
- preview 失败：允许返回结果页
- apply 失败：允许重新 preview 或取消

---

## 11. 焦点与窗口策略

### 11.1 焦点原则

- 默认不抢宿主焦点
- 用户点击输入框后才进入交互焦点

### 11.2 窗口行为

- 贴近触发点出现
- 可 ESC 关闭
- 点击外部可收起
- 长任务不中断事件处理

### 11.3 尺寸建议

- 默认宽度：`640 ~ 720`
- 默认高度：`420 ~ 520`
- 允许内容区伸缩，但不做复杂可停靠布局

---

## 12. 用户场景指标

- 双击右键到浮层可见 `< 300ms`
- 上下文摘要显示 `< 800ms`
- 首条可用结果 `< 2.5s`
- 从结果到提交应用关键点击数 `<= 2`
- 误触关闭成功率 `> 99%`

---

## 13. 风险与取舍

### 13.1 为什么不先做 Mini Workspace

因为右键召唤是短任务心智，过早引入复杂面板会让重构重新长回“大工作台”。

### 13.2 为什么结果区不只显示长文本

因为后续要接第三方 agent，纯文本 UI 容易让结构化能力白白丢失。

### 13.3 为什么 preview 要单独一步

因为 OpenCopilot 的定位是“增量修正，不抢控制权”，这要求回写必须可预览、可取消。

---

## 14. 本文档与其他文档关系

- `docs/VNEXT_REBUILD_BLUEPRINT.md`：总蓝图
- `docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md`：阶段实施清单
- `docs/VNEXT_UNIFIED_AGENT_API.md`：统一 API 契约
- `docs/VNEXT_AGENT_GATEWAY_DESIGN.md`：Gateway 与 provider 设计
