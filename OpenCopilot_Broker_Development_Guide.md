# OpenCopilot 特权代理 (Privileged Broker) 开发与设计规范

> **文档状态**: V1.2 (已更新)
> **更新日期**: 2026-05-26
> **目标读者**: OpenCopilot 核心开发者、需要进行 macOS 底层 API 联调的贡献者

---

## 1. 为什么需要 ASU Broker？

在 macOS 现代安全架构下，运行在 IDE（如 Trae, VSCode）内置终端中的 ASU 主进程（`smart_copilot.py`）被系统视为处于受限的沙盒环境。当主进程尝试通过 `osascript` 或 `NSWorkspace` 等跨进程手段去读取外部浏览器网页内容或嗅探系统焦点时，会遭遇 macOS Transparency, Consent, and Control (TCC) 机制拦截，引发 `(-10004) Privilege Violation` 错误。

**解决核心**：引入 **Privileged Broker (特权代理)**。这是一个独立的、高权限的本地守护进程。它在 IDE 沙盒外（原生终端或通过 LaunchAgent）运行并持有系统的辅助功能/自动化权限。ASU 主进程通过本地回环网络（`127.0.0.1:18889`）向 Broker 发起 HTTP/WebSocket 请求，由 Broker 代为执行底层系统操作并返回结果，从而实现**沙盒穿透**。

---

## 2. 整体架构与模块划分

Broker 被设计为一个极度轻量、专注底层的"系统探针"，绝不包含任何大语言模型 (LLM) 的逻辑或推理代码。

建议的工程目录结构：

```text
asu_broker/
├── core/
│   ├── __init__.py
│   ├── server.py              # FastAPI 主服务逻辑 (端口 18889) ✅
│   ├── auth.py                # 动态 Token 鉴权模块 ✅
│   └── ws_manager.py          # WebSocket 连接管理器 🔶 待开发
├── probes/                    # 探针组件库 ✅
│   ├── __init__.py
│   ├── browser_probe.py       # 主流浏览器 URL/DOM
│   ├── window_probe.py        # 活动窗口/BundleID 探测
│   ├── selection_probe.py     # 高亮文本/剪贴板
│   ├── screen_probe.py        # 屏幕截图
│   ├── fs_probe.py            # 文件系统读取
│   ├── app_control_probe.py   # 备忘录等原生应用操作
│   └── events_probe.py        # 系统事件监听 🔶 占位
├── scripts/                   # 复杂 AppleScript 脚本 🔶 待添加
│   └── get_browser_dom.applescript
├── deploy/                    # 部署配置（对应项目顶层 deploy/）
├── setup/                     # 🔶 生命周期与部署（已迁移至顶层 deploy/ + scripts/）
├── config.py                  # 🔶 独立配置文件（待拆分）
└── run.py                     # Broker 启动入口 ✅
```

---

## 3. 核心接口规范 (API Design)

Broker 采用 RESTful API 与 WebSocket 结合的双向通信模型。

### 3.1 REST API (被动拉取模式)
供 OpenCopilot 智能体 在需要时（如用户点击了读取按钮）主动获取系统快照。

#### `GET /api/v1/system/capabilities` ✅ 已实现
*   **用途**：返回 Broker 当前全部探针能力清单，方便 ASU 动态适配。
*   **返回示例**：见 `server.py` 实现。

#### `GET /api/v1/system/shutdown` → `POST /api/v1/system/shutdown` ✅ 已实现
*   **用途**：优雅关闭 Broker 进程（需 Bearer 鉴权）。

#### `GET /health` ✅ 已实现
*   **用途**：健康检查，同时验证探针功能是否可用。

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
*   **前提限制**：目标浏览器必须开启"允许 Apple 事件执行 JavaScript"的开发者权限。
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

#### `GET /api/v1/system/screen/front` (视觉与 OCR 能力)
*   **用途**：静默截取当前最前台应用窗口的屏幕图像（返回 Base64 编码）。用于配合具备 Vision 多模态能力的 LLM（如 GPT-4o 或 MiniMax-Vision）进行 OCR 或视觉交互。完美补充无法通过 DOM 提取上下文的场景（如 PDF 阅读器、设计软件等）。

#### `POST /api/v1/system/fs/read` (全局文件系统监控)
*   **用途**：绕过 IDE 插件可能遭遇的文件系统沙盒限制（例如无权限读取用户的 Desktop 或 Downloads 文件夹）。通过特权代理，直接提取外部指定文件内容作为 AI 上下文。

### 3.2 WebSocket (主动推送模式) 🔶 待开发
供 OpenCopilot 智能体 建立长连接，实现系统状态变化的"无感感知"。（`events_probe.py` 已预留框架，待挂载 NSWorkspace 通知）

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
*   **应用场景**：OpenCopilot 接收到该事件后，可以动态改变自身 UI（例如，如果发现切到了 IDE，就显示"读取代码"按钮；切到 Chrome，就显示"读取网页"按钮）。

---

## 4. 安全与权限机制 (Security Model)

Broker 拥有系统极高的控制权（能够窥探任意网页和窗口），因此必须采取严格的安全隔离：

1.  **网络隔离**：Broker 必须强制绑定在 `127.0.0.1`，绝不允许绑定到 `0.0.0.0`，防范局域网内的恶意扫描和调用。
2.  **动态 Token 鉴权 (Local-only)**：
    *   在 OpenCopilot 主程序或 Broker 启动时，生成一个高强度的随机 Token，并写入到临时目录中仅当前用户可读的隐藏文件（如 `~/.asu_broker_token`）。
    *   所有的 HTTP 和 WS 请求，必须在 Header 中携带 `Authorization: Bearer <Token>`，否则 Broker 立即返回 403 Forbidden。
3.  **用户态运行 (User Space)**：
    *   Broker 的部署必须是针对当前用户的 `LaunchAgent`（位于 `~/Library/LaunchAgents/`），绝不能作为 `LaunchDaemon` 以 `root` 权限运行。这限制了即使 Broker 出现漏洞，其破坏力也仅限于当前用户级别。

---

## 5. 生命周期与部署策略 (Deployment)

为了保证"无感体验"，Broker 的启动和停止需要极其谨慎，尤其是**启动环境的选择**决定了其是否能成功拥有特权。

### 5.1 绝对正确的启动方式 (手动调试阶段)
**⚠️ 严重警告：绝不能在 IDE (如 Trae, VSCode, Cursor) 的内置终端中启动 Broker！**

现代 IDE 的终端运行在被系统严格限制的沙盒（Sandbox）内。如果在 IDE 终端中启动，Broker 会继承沙盒的枷锁，即使你在系统设置中给了权限，依然会触发 `(-10004) Privilege Violation`。

**正确的启动步骤**：
1. 使用 `Cmd + Space` 打开 macOS **原生的 Terminal.app**（或 iTerm2）。
2. 在原生终端中进入项目根目录：
   ```bash
   cd /Users/onetwo/Documents/trae_projects/ASU
   ```
3. 运行项目提供的一键启动脚本：
   ```bash
   ./start_broker.sh
   ```
4. **权限弹窗处理**：当 Broker 第一次尝试截取屏幕或读取浏览器时，macOS 可能会弹出如下提示：
   > *"终端"想要控制"Google Chrome"...* 或 *"终端"想要录制屏幕...*
   
   **必须点击"好"或在系统设置中予以"允许"**。一旦授权，原生终端就会永久持有这块"免死金牌"。此后，无论 OpenCopilot 主程序在什么沙盒里运行，只要通过 HTTP 请求这个原生终端里跑着的 Broker，就能无视沙盒边界！

### 5.2 生产环境的常驻 (Launchd) ✅ 已实现

1.  **一键安装**：
    ```bash
    bash scripts/install_broker_daemon.sh
    ```
    注册 `com.asu.broker` LaunchAgent（`deploy/com.asu.broker.plist`），开机自启 + 崩溃 5 秒后自动重启。日志输出至 `~/Library/Logs/ASU/broker_*.log`。

2.  **一键卸载**：
    ```bash
    bash scripts/uninstall_broker_daemon.sh
    ```

3.  **优雅退出**：
    `POST /api/v1/system/shutdown`（需 Bearer 鉴权）支持平滑关闭 Broker 进程。

4.  **长期规划**：
    - 打包为独立 `.app`（拥有稳定 Bundle ID），以便在 macOS 辅助功能白名单中持久授权。

---

## 6. 开发规范与注意事项

*   **异步为王**：Broker 内部调用 AppleScript (osascript) 极易因为目标应用卡死而阻塞。在 FastAPI 中，这类操作必须放入线程池 (`asyncio.to_thread` 或 `run_in_executor`) 中执行。
*   **Python 3.13 兼容性警告**：正如 ASU 主项目要求，Broker 同样不得使用 Python 3.13+，以避免 `pynput` 等底层库的线程崩溃问题。
*   **错误返回规范**：所有的异常必须被包裹在统一的 JSON 结构中返回（如 `{"status": "error", "message": "..."}`），绝不能让服务端直接抛出 500 HTML 页面，以免导致 ASU 客户端解析崩溃。