# ASU 特权代理模式 (Privileged Broker Pattern) 技术方案与集成指南

## 1. 背景与痛点：沙盒隔离与权限链断裂

在 macOS 现代安全架构（SIP、TCC、Sandbox）下，ASU Agent 在 IDE（如 Trae、VSCode）内置终端中运行时，面临着严峻的跨进程探测壁垒。

**核心问题：**
当 ASU 尝试通过 `osascript`、`pynput` 等工具探测系统环境（如获取浏览器标签页、读取焦点应用）时，即使系统 UI 层面授予了 IDE 或终端相应的权限，操作依然会被内核拦截，返回 `(-10004) 权限违例`。

**底层原因：**
*   **权限链断裂**：IDE 内置终端通常处于受限的沙盒环境（如 `trae-sandbox`），其子进程无法可靠地继承父进程的 TCC（透明、同意和控制）自动化权限。
*   **身份缺失**：直接在终端执行的 Python 脚本被系统视为“二等公民”，缺乏独立的 Bundle ID，导致权限回溯失败。

## 2. 解决方案：本地特权代理模式 (Privileged Broker)

为了在不破坏开发环境体验的前提下绕过沙盒限制，我们提出并验证了 **“本地特权代理模式”**。

### 2.1 架构设计原理
1.  **架构解耦与权限分离**：将需要高权限的“系统探测”逻辑从 ASU 主进程中剥离，形成一个独立的代理服务（Broker）。
2.  **获取真实权限**：Broker 必须在 IDE 沙盒之外（如 macOS 原生 Terminal.app 或打包为独立 `.app`）启动。这样它就能合法获得并保持系统级别的 `Accessibility` 和 `Automation` 权限。
3.  **本地网络穿透**：受困于 IDE 沙盒的 ASU 主进程，通过本地回环网络（如 `localhost:18889` 上的 HTTP/WebSocket 协议）向 Broker 发起请求。沙盒会拦截 Mach IPC（Apple Events），但不会拦截本地网络请求。
4.  **代理执行与返回**：Broker 接收到网络请求后，以高权限执行系统级脚本，将结果通过 HTTP Response 返回给 ASU。

### 2.2 PoC 验证记录
*   **时间**：2026-05-20
*   **动作**：
    1.  创建高权限代理服务器 (`privilege_broker.py`)，监听 `18889` 端口，提供 `/chrome-tabs` 接口执行 AppleScript。
    2.  创建沙盒内客户端 (`trae_client_test.py`)，通过 HTTP GET 发起请求。
*   **结果**：在系统原生终端启动 Broker 后，沙盒内的 Python 客户端成功穿透拦截，读取到了 Chrome 浏览器的所有活跃标签页（包括飞书开发者后台、MiniMax 控制台等环境信息）。

---

## 3. ASU 项目集成方案

将此模式集成到 ASU 项目的初步规划如下：

### 3.1 模块划分
建议在 ASU 项目中新增 `asu_broker/` 目录：
```text
ASU/
├── asu_broker/                  # 高权限代理模块
│   ├── broker_server.py         # 代理主服务 (Flask/FastAPI)
│   ├── scripts/                 # AppleScript/JXA 脚本库
│   │   ├── get_chrome_tabs.applescript
│   │   └── get_frontmost_app.applescript
│   └── setup_daemon.sh          # 用于注册开机自启守护进程的脚本
├── client/                      # 现有的沙盒内 ASU Agent
│   └── system_probe_client.py   # 与 Broker 通信的 HTTP/WebSocket 客户端
└── ...
```

### 3.2 代理服务 (Broker) 的演进建议
*   **通信协议升级**：考虑到 ASU 可能需要实时感知系统焦点变化（例如用户从浏览器切回了 IDE），建议在 HTTP 基础上增加 **WebSocket 或 SSE (Server-Sent Events)**。由 Broker 主动监听系统事件并推送到 ASU Agent。
*   **守护进程化 (Daemonize)**：为了用户体验，不应要求用户每次手动在原生终端启动 Broker。可通过 `launchd` 编写 `.plist` 文件，将 Broker 注册为 macOS 的 `LaunchAgent`，实现开机静默启动并在后台常驻监听。
*   **轻量级安全校验**：为了防止本机的其他恶意进程探测 18889 端口，可以在 Broker 和 ASU 客户端之间约定一个静态 Token，放在 HTTP Header 中进行简单的身份鉴权。

### 3.3 与定制化 Agent 的结合
ASU 当前的后台定制智能体（`asu_custom_agent.py`）可以引入 `system_probe_client.py` 模块。当 AI 在规划阶段需要感知外部上下文时（例如用户提问：“帮我总结刚才看的那个网页”），AI 主动调用 Broker 接口，无感抓取外部应用的上下文注入到 Prompt 中。

## 4. ASU Broker 核心架构规划 (v1.0)

为了将“特权代理模式”从简单的 PoC 升级为生产可用的 ASU 核心组件，我对 `asu_broker` 模块进行了以下详细规划：

### 4.1 核心职责定义
`asu_broker` 不参与任何 LLM 逻辑或 Agent 推理，它仅仅是一个**极度轻量、安全、专注底层的“系统探针”**。
*   **向下 (OS 层)**：通过 macOS 原生 API (AppKit, ApplicationServices, SystemEvents, osascript) 获取系统状态、焦点应用、窗口内容。
*   **向上 (IDE 层)**：提供稳定的 HTTP/WebSocket 接口，供被困在沙盒里的 ASU 智能体（或 IDE 插件）调用。

### 4.2 模块架构设计

建议采用基于 `FastAPI` (或轻量级 `aiohttp`) 的异步服务架构，确保高并发探测时不阻塞：

```text
asu_broker/
├── core/
│   ├── server.py              # FastAPI 主服务 (端口 18889)
│   ├── auth.py                # 本地安全鉴权机制 (Local-only Token)
│   └── ws_manager.py          # WebSocket 连接管理器 (用于主动推送事件)
├── probes/                    # 探针组件库 (执行高权限操作)
│   ├── browser_probe.py       # 获取浏览器(Chrome/Safari) URL、DOM、标签页
│   ├── window_probe.py        # 获取当前活动窗口、前台应用 BundleID
│   ├── selection_probe.py     # (慎用) 尝试获取高亮文本/剪贴板内容
│   └── ide_probe.py           # 探测主流 IDE 的活动文件路径
├── scripts/                   # 存放 AppleScript/JXA 脚本
├── setup/
│   ├── install_daemon.sh      # 注册 macOS LaunchAgent 脚本
│   └── com.asu.broker.plist   # launchd 守护进程配置文件
└── run_broker.py              # 代理服务入口点
```

### 4.3 核心接口规划 (API Design)

#### **REST API (被动拉取)**
用于 ASU Agent 在需要时主动获取系统快照。
*   `GET /api/v1/system/frontmost`
    *   **用途**：获取当前系统处于最前台的应用名称和 Bundle ID。
    *   **返回**：`{"app": "Google Chrome", "bundle_id": "com.google.Chrome"}`
*   `GET /api/v1/browser/tabs`
    *   **用途**：获取浏览器当前所有打开的标签页（用于 AI 上下文推断）。
*   `POST /api/v1/browser/dom`
    *   **用途**：根据指定的 Tab ID，跨进程提取该网页的 `document.body.innerText`。
    *   **前提**：需浏览器开启“允许 Apple 事件执行 JS”。

#### **WebSocket (主动推送)**
监听 `ws://localhost:18889/ws/events`。
*   **用途**：实现真正的“无感交互”。当 Broker 通过底层的 `NSWorkspace` 监听到用户切换了前台应用（例如从 Trae 切到了 Chrome），Broker 会主动向 ASU Agent 发送事件：
    `{"event": "app_activated", "data": {"app": "Google Chrome"}}`
*   **价值**：Agent 可以根据这个事件，自动切换 Persona（比如从“代码辅助模式”切换到“网页分析模式”）。

### 4.4 权限与安全机制 (Security)

因为 Broker 拥有极高的系统权限，必须防止被其他恶意本地软件滥用：
1.  **仅限本地回环**：Server 强制绑定到 `127.0.0.1`，拒绝任何来自局域网的外部请求。
2.  **动态 Token 鉴权**：在 ASU 主程序启动时，随机生成一个 `BROKER_TOKEN` 写入到项目目录下的 `.asu_env` 或系统临时目录中。Broker 和 Client 通信必须在 Header 中携带 `Authorization: Bearer <Token>`。
3.  **用户态隔离**：Broker 作为当前用户的 `LaunchAgent` 运行，而不是 `root` 权限的 `LaunchDaemon`，防止造成灾难性的系统破坏。

### 4.5 部署与生命周期管理

为了对用户透明，Broker 的生命周期不应由用户在终端手动管理：
1.  提供一个 `setup_daemon.sh` 脚本。
2.  在安装 ASU 时，将 `com.asu.broker.plist` 复制到 `~/Library/LaunchAgents/`。
3.  使用 `launchctl load` 启动服务。这样即使用户重启电脑，Broker 也会默默在后台拉起，随时准备为 IDE 里的 ASU Agent 提供特权服务。

## 5. 后续工作计划
1.  **完善 Broker 接口**：除了浏览器标签，补充前台应用识别、选中高亮文本获取等接口。
2.  **编写打包与部署脚本**：探索将 Broker 打包为拥有独立 Bundle ID 的原生免安装组件，降低用户的权限配置成本。
3.  **集成测试**：在 ASU 主体逻辑中引入 Broker 客户端并进行联调。