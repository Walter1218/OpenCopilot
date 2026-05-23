# ASU 特权代理 (Privileged Broker) 开发与设计规范

> **文档状态**: 草案 (Draft) / V1.0
> **更新日期**: 2026-05-24
> **目标读者**: ASU 核心开发者、需要进行 macOS 底层 API 联调的贡献者

---

## 1. 为什么需要 ASU Broker？

在 macOS 现代安全架构下，运行在 IDE（如 Trae, VSCode）内置终端中的 ASU 主进程（`smart_copilot.py`）被系统视为处于受限的沙盒环境。当主进程尝试通过 `osascript` 或 `NSWorkspace` 等跨进程手段去读取外部浏览器网页内容或嗅探系统焦点时，会遭遇 macOS Transparency, Consent, and Control (TCC) 机制拦截，引发 `(-10004) Privilege Violation` 错误。

**解决核心**：引入 **Privileged Broker (特权代理)**。这是一个独立的、高权限的本地守护进程。它在 IDE 沙盒外（原生终端或通过 LaunchAgent）运行并持有系统的辅助功能/自动化权限。ASU 主进程通过本地回环网络（`127.0.0.1:18889`）向 Broker 发起 HTTP/WebSocket 请求，由 Broker 代为执行底层系统操作并返回结果，从而实现**沙盒穿透**。

---

## 2. 整体架构与模块划分

Broker 被设计为一个极度轻量、专注底层的“系统探针”，绝不包含任何大语言模型 (LLM) 的逻辑或推理代码。

建议的工程目录结构：

```text
asu_broker/
├── core/
│   ├── __init__.py
│   ├── server.py              # FastAPI/aiohttp 主服务逻辑 (端口 18889)
│   ├── auth.py                # 动态 Token 鉴权模块
│   └── ws_manager.py          # WebSocket 连接管理器 (用于系统事件的主动推送)
├── probes/                    # 探针组件库 (执行高权限的 OS 操作)
│   ├── __init__.py
│   ├── browser_probe.py       # 获取主流浏览器 (Chrome/Safari/Edge等) URL、DOM
│   ├── window_probe.py        # 探测当前活动窗口、前台应用 BundleID
│   └── selection_probe.py     # 探测高亮文本、剪贴板内容 (慎用)
├── scripts/                   # 存放复杂的 AppleScript/JXA 脚本文件
│   └── get_browser_dom.applescript
├── setup/                     # 生命周期与部署脚本
│   ├── install_daemon.sh      # 用于将 Broker 注册为 macOS LaunchAgent
│   └── com.asu.broker.plist   # launchd 守护进程配置文件
├── config.py                  # 代理的独立配置文件
└── run.py                     # Broker 的启动入口点
```

---

## 3. 核心接口规范 (API Design)

Broker 采用 RESTful API 与 WebSocket 结合的双向通信模型。

### 3.1 REST API (被动拉取模式)
供 ASU Agent 在需要时（如用户点击了读取按钮）主动获取系统快照。

#### `GET /api/v1/system/frontmost`
*   **用途**：获取当前系统处于最前台的应用信息。
*   **返回示例**：
    ```json
    {
      "status": "success",
      "data": {
        "app_name": "Google Chrome",
        "bundle_id": "com.google.Chrome"
      }
    }
    ```

#### `GET /api/v1/browser/tabs`
*   **用途**：获取浏览器当前所有打开的标签页列表（常用于帮助 AI 推断用户的宏观上下文）。
*   **返回示例**：
    ```json
    {
      "status": "success",
      "data": [
        {"title": "ASU GitHub Repo", "url": "https://github.com/..."},
        {"title": "OpenAI API Docs", "url": "https://platform.openai.com/..."}
      ]
    }
    ```

#### `POST /api/v1/browser/dom`
*   **用途**：跨进程提取特定浏览器当前激活标签页的全文内容。
*   **请求体**：`{"browser_name": "Google Chrome"}`
*   **前提限制**：目标浏览器必须开启“允许 Apple 事件执行 JavaScript”的开发者权限。
*   **返回示例**：
    ```json
    {
      "status": "success",
      "data": {"content": "网页的纯文本内容 (document.body.innerText)..."}
    }
    ```

#### `GET /api/v1/system/clipboard` (高级能力)
*   **用途**：静默读取操作系统的当前剪贴板内容，用于 AI 辅助。

#### `GET /api/v1/system/selection` (高级能力)
*   **用途**：提取当前系统任何应用程序中高亮选中的文本（通过底层命令或 AXAPI 实现）。解决沙盒内应用强行注入按键导致的选区丢失问题。

#### `POST /api/v1/apps/notes` (高级能力)
*   **用途**：静默调用 Apple 备忘录 (Notes) 创建新文档，支持 AI 结果直接回写。

### 3.2 WebSocket (主动推送模式)
供 ASU Agent 建立长连接，实现系统状态变化的“无感感知”。

#### `ws://127.0.0.1:18889/ws/events`
*   **行为**：Broker 底层使用 `NSWorkspace` 的通知机制监听应用切换。当用户改变了焦点应用，Broker 会主动推送信封。
*   **推送数据示例**：
    ```json
    {
      "event_type": "app_activated",
      "timestamp": 1716480000.123,
      "payload": {
        "app_name": "Visual Studio Code",
        "bundle_id": "com.microsoft.VSCode"
      }
    }
    ```
*   **应用场景**：ASU Copilot 接收到该事件后，可以动态改变自身 UI（例如，如果发现切到了 IDE，就显示“读取代码”按钮；切到 Chrome，就显示“读取网页”按钮）。

---

## 4. 安全与权限机制 (Security Model)

Broker 拥有系统极高的控制权（能够窥探任意网页和窗口），因此必须采取严格的安全隔离：

1.  **网络隔离**：Broker 必须强制绑定在 `127.0.0.1`，绝不允许绑定到 `0.0.0.0`，防范局域网内的恶意扫描和调用。
2.  **动态 Token 鉴权 (Local-only)**：
    *   在 ASU 主程序或 Broker 启动时，生成一个高强度的随机 Token，并写入到临时目录中仅当前用户可读的隐藏文件（如 `~/.asu_broker_token`）。
    *   所有的 HTTP 和 WS 请求，必须在 Header 中携带 `Authorization: Bearer <Token>`，否则 Broker 立即返回 403 Forbidden。
3.  **用户态运行 (User Space)**：
    *   Broker 的部署必须是针对当前用户的 `LaunchAgent`（位于 `~/Library/LaunchAgents/`），绝不能作为 `LaunchDaemon` 以 `root` 权限运行。这限制了即使 Broker 出现漏洞，其破坏力也仅限于当前用户级别。

---

## 5. 生命周期与部署策略 (Deployment)

为了保证“无感体验”，Broker 的启动和停止不应依赖用户在终端手动敲命令。

1.  **首次安装与授权**：
    *   提供自动化脚本，使用 `py2app` 或 `PyInstaller` 将 Broker 打包为一个无界面的原生 `.app` (具有独立的 Bundle ID)。
    *   引导用户在 macOS 的 `隐私与安全性 -> 辅助功能` 中，将这个 `.app` 添加到白名单。这保证了即使更新代码，系统授权依然有效。
2.  **开机自启与常驻 (Launchd)**：
    *   配置 `com.asu.broker.plist`，使用 `KeepAlive` 属性确保服务崩溃后自动重启。
    *   在 ASU 安装阶段，通过 `launchctl load` 注册服务。
3.  **平滑退出**：
    *   提供 `/api/v1/system/shutdown` 接口（需严格鉴权），允许 ASU 主程序在彻底退出或卸载时，优雅地关闭 Broker 进程。

---

## 6. 开发规范与注意事项

*   **异步为王**：Broker 内部调用 AppleScript (osascript) 极易因为目标应用卡死而阻塞。在 FastAPI 中，这类操作必须放入线程池 (`asyncio.to_thread` 或 `run_in_executor`) 中执行。
*   **Python 3.13 兼容性警告**：正如 ASU 主项目要求，Broker 同样不得使用 Python 3.13+，以避免 `pynput` 等底层库的线程崩溃问题。
*   **错误返回规范**：所有的异常必须被包裹在统一的 JSON 结构中返回（如 `{"status": "error", "message": "..."}`），绝不能让服务端直接抛出 500 HTML 页面，以免导致 ASU 客户端解析崩溃。