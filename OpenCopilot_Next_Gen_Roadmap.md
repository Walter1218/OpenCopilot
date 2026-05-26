# OpenCopilot 下一代架构演进路线图 (Next-Gen Roadmap)

> **文档状态**: V1.1 (已更新)
> **评估时间**: 2026-05-24（2026-05-26 更新状态）
> **愿景**: 从"被动式跨端工具"演进为"具备持久心智与多模态主动感知的 OS 级智能体"

---

## 核心背景

在完成了 **Privileged Broker (特权代理)** 沙盒穿透和 **Custom Agent (定制智能体)** 的架构解耦后，OpenCopilot 已经拥有了强大的底层执行力和独立的大脑。本路线图旨在规划如何利用这些基础设施，赋予智能体真正的"记忆"与"眼睛"。

以下开发规划按照技术依赖性和用户价值，划分为 P0 到 P2 三个优先级阶段。

---

## 🔴 优先级 P0：持久心智与视觉感官 (基石层)

*这是打通 AI 连续性体验和跨模态理解的基石，必须优先解决。*

### P0.1 会话持久化与长上下文管理 ✅ 已完成
*   **痛点**：~~当前 Custom Agent 的 `sessions_memory` 存在于内存中，重启即丢失；且缺乏超长对话的 Token 截断机制。~~
*   **现状**：已引入 SQLite 持久化（`asu_agent.db`，四表结构）+ `ContextWindowManager` 预算驱动裁剪（默认 ~30K token 窗口，69% 平均压缩率，39/39 测试通过）。会话重启后可恢复。历史无限增长问题已通过分层裁剪策略解决。

### P0.2 多模态视觉感知 (Vision OCR)
*   **痛点**：当前依赖 DOM 提取或代码提取，无法处理 PDF、设计软件、视频或远程桌面等无文本节点场景。
*   **目标**：无论什么软件，只要用户能看到，AI 就能看到并分析。
*   **技术路径**：
    *   在 UI 悬浮卡片增加 `[👁️ 视觉分析]` 按钮。
    *   调用 Broker 已实现的 `GET /api/v1/system/screen/front` 接口获取前台窗口 Base64 截图。
    *   对接 MiniMax-Vision 或多模态 API 进行 OCR 和视觉逻辑理解。

---

## 🟠 优先级 P1：系统脉络与被动感知 (交互层)

*从"用户唤醒它"，进化到"它主动感知用户"，这是人机交互的质变。*

### P1.1 全局事件订阅与主动状态推送
*   **痛点**：当前 OpenCopilot 采用"拉 (Pull)"模式，只有用户双击右键呼出卡片时，才去探测前台应用是什么。
*   **目标**：让 ASU 像一个真正的系统守护精灵，实时无感地知道用户焦点的变化。
*   **技术路径**：
    *   在 Broker 端利用 PyObjC 挂载 `NSWorkspaceDidActivateApplicationNotification`（`events_probe.py` 已预留框架）。
    *   通过 WebSocket 长连接将应用切换事件主动推送给 UI。
    *   UI 收到事件后，智能切换界面（如：切到浏览器显示网页分析按钮，切到 IDE 切换为代码分析 Persona）。
*   **当前状态**：Broker REST API 已产品化（LaunchAgent 常驻 + capabilities + 统一错误），WebSocket 待实现。

### P1.2 底层高亮选区提取 (AXAPI 落地)
*   **痛点**：当前划词提取严重依赖用户的物理拖拽，若尝试代码模拟 `Cmd+C` 会导致 IDE 光标丢失。
*   **目标**：实现真正的、不丢光标的"无感划词一键分析"。
*   **技术路径**：
    *   对接 Broker 中预埋的 `/api/v1/system/selection`。
    *   在代理层引入基于 `AXUIElement` 的 Accessibility API，直接从 macOS 渲染层强行读取选中的文本，彻底绕过剪贴板污染和键盘事件流。

---

## 🟡 优先级 P2：精细化工程治理与体验闭环 (体验层)

*提升系统的鲁棒性、可玩性与界面表现力。*

### P2.1 多 Provider 故障转移 (Failover)
*   **目标**：保障极端情况下的可用性，实现云端/本地双擎平滑切换。
*   **技术路径**：重构 `llm_provider.py` 的 `ProviderFactory`（当前硬编码返回 `ASUCustomAgentClient`），实现降级策略：主 Provider 超时 → 自动回退备用 Provider。

### P2.2 自定义 Persona 的 GUI 管理工坊
*   **目标**：满足极客用户的深度定制需求，将 Prompt 设定权交给用户。
*   **技术路径**：
    *   Persona 已实现文件化管理（`personas/*.md` 热加载），目前已有 default / code / translate / polish / custom / revision 六种。
    *   ✅ `custom.md` 已实现自定义指令修改场景，AI 严格按指令输出修改后文本。
    *   后续在 PyQt 界面增加"角色工坊"管理面板，支持增删改查。

### P2.3 Markdown 富文本渲染与代码高亮 ✅ 已完成
*   **现状**：已在 `smart_copilot.py` 中实现基于 PyQt 的 Markdown 渲染器，支持代码块语法高亮。
