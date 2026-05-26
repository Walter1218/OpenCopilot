# OpenCopilot 项目 Code Review 报告

**时间**: 2026-05-23
**分支**: `ai-assistant-dev`
**审查目标**: 全面审查代码现状，梳理与 TCC 权限、架构稳定性、UI 性能以及历史包袱相关的技术债务与潜在问题。

---

## 一、架构缺陷与安全/权限问题

### 1. 致命缺陷：进程内调用 AppleScript 导致 TCC 沙盒拦截
*   **定位**：`smart_copilot.py`
    *   `_probe_browser()` 方法内部的 `subprocess.check_output(['osascript', ...])`
    *   `read_from_browser()` 方法内部的 `subprocess.check_output(['osascript', ...])`
*   **问题描述**：这是导致应用在 IDE 终端沙盒或普通环境运行时触发 `(-10004) 权限违例` 崩溃的根本原因。直接在主进程中注入 AppleScript 请求系统焦点应用或浏览器 DOM，会被 macOS 的 Transparency, Consent, and Control (TCC) 机制直接拦截。
*   **重构建议**：必须将这两处逻辑彻底剥离主进程。改用 HTTP 客户端模式，向拥有高权限的本地特权代理（Privileged Broker，运行在 `127.0.0.1:18889`）发起请求。

## 二、UI 响应与并发模型问题

### 1. 严重问题：主 UI 线程被跨进程调用阻塞
*   **定位**：`smart_copilot.py` -> `read_from_browser()` 方法。
*   **问题描述**：当用户点击“一键读取当前网页”按钮时，`subprocess.check_output()` 是在主线程同步执行的。如果目标浏览器（如 Chrome/Safari）卡死，或者 AppleScript 执行超时（例如等待用户在浏览器中授权 JavaScript 权限），整个 PyQt 悬浮卡片 UI 会瞬间冻结（无响应）。
*   **重构建议**：任何涉及跨进程通信或网络请求的操作（包括未来与 Broker 的 HTTP 通信），必须放到独立的 `QThread` (或使用异步 `aiohttp` 配合 `QTimer`) 中执行，并通过 Qt 信号 (`pyqtSignal`) 更新 UI。

## 三、代码质量与历史包袱清理

### 1. 过时的 OpenClaw 强耦合逻辑
*   **定位**：`smart_copilot.py` -> `ModelScannerWorker` 类
*   **问题描述**：根据项目上下文与核心记忆，OpenCopilot 项目已明确转向使用内置的 `asu_custom_agent.py`，不再强依赖 OpenClaw。但在探测逻辑中（L29-L74），仍然存在大量关于 `openclaw agents list`、端口 `18789`/`18791` 探测的硬编码“脏逻辑”。
*   **重构建议**：遵循“删除旧的过失信息”的开发规范，重构 `ModelScannerWorker`，清理 OpenClaw 的特定逻辑，专注于探测通用的 OpenAI 兼容接口或仅仅检查 OpenCopilot 内置代理的心跳。

### 2. 异常处理过宽 (Error Swallowing)
*   **定位**：`smart_copilot.py` 多个地方，例如 `_probe_browser` 中的 `except Exception:`。
*   **问题描述**：宽泛的异常捕获直接将错误静默（吞噬），这使得诸如 `-10004` 这样的核心权限问题在开发阶段难以被及时发现。
*   **重构建议**：在捕获宽泛异常时，至少需要通过 `logging` 模块或控制台 `print` 打印出 `e` 的详细堆栈，以支持后续的 Debug。

### 3. Agent 服务的硬编码与错误响应结构
*   **定位**：`asu_custom_agent.py` -> `AgentHTTPRequestHandler.do_POST`
*   **问题描述**：在捕获 LLM 异常时，向流中写入的错误数据格式虽然是 SSE 格式，但前端（`ASUCustomAgentClient.stream_agent_task`）的解析逻辑比较脆弱，如果后端的异常栈非常长，可能会破坏 JSON 结构。
*   **重构建议**：优化 Server-Sent Events (SSE) 的错误边界处理，确保流的关闭是安全和合规的。

## 四、下一步重构路线图 (Roadmap)

结合上述问题与之前验证的 [特权代理模式集成指南](./ASU_Privileged_Broker_Integration_Doc.md)，建议分阶段执行以下重构：

1.  **阶段 1：剥离高权限代码 (Fix TCC)**
    *   移除 `smart_copilot.py` 中的 `osascript`。
    *   建立并集成 `asu_broker` 模块。
2.  **阶段 2：UI 线程解耦**
    *   将 `read_from_browser` 重构为基于 `QThread` 的异步请求模式。
3.  **阶段 3：代码净化**
    *   清理 `ModelScannerWorker` 和其它与旧版 OpenClaw 相关的历史废弃代码。