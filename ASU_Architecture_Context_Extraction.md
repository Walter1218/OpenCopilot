# ASU 全场景智能上下文获取方案 (Architecture Proposal)

## 1. 方案背景与核心痛点
在 macOS 环境下开发全局 AI 悬浮伴生工具（如 ASU），面临着一个严峻的系统级矛盾：
- **用户需求**：希望能够"一键、无感"地获取当前屏幕/软件内的全文内容供 AI 分析。
- **系统限制**：macOS 严格的沙盒与焦点保护机制导致，任何企图通过外部进程（Python）自动模拟发送 `Cmd+A`、`Cmd+C` 的操作，都会被系统判定为输入源异常，进而**强行重置 IDE/浏览器的焦点，导致用户原有的选区和光标永久丢失**。

为了彻底解决这一矛盾，本方案提出了一套**"基于 Bundle ID 的智能场景路由 + 分层降级"**的上下文获取架构。

---

## 2. 核心交互流程设计
1. **唤醒动作**：用户在任何软件界面中，**双击鼠标右键**。
2. **场景嗅探**：ASU 后台异步探测当前活跃窗口（IDE 插件端口 / AppleScript 前台应用名）。
3. **UI 呈现**：鼠标旁弹出 ASU 悬浮卡片。卡片根据当前场景，动态展示定制化的获取按钮（`[📥 极速读取当前 IDE 全文]` / `[🌐 一键读取当前网页全文]`）。
4. **触发动作**：用户点击对应按钮，ASU 调用场景探针静默拉取全文。若探针失败，UI 平滑降级提示用户使用"物理拖拽"方式投喂。

---

## 3. 分场景底层探针设计

### 3.1 浏览器场景 (Browsers) ✅ 已实现
**目标应用**：Chrome, Safari, Edge, Arc, Brave 等
**核心技术**：AppleScript + JavaScript 注入
- **实现原理**：通过执行 AppleScript 脚本，跨进程向当前活跃的浏览器 Tab 注入 JS 代码 `document.body.innerText;`，直接在 DOM 内存树级别提取纯文本。
- **优势**：0 界面重绘，绝对静默，光标安全。
- **前置条件**：需引导用户在浏览器开发者菜单中开启 `Allow JavaScript from Apple Events` 权限。
- **实现位置**：`smart_copilot.py` → `AICardWindow._probe_browser()` + `read_from_browser()`

### 3.2 代码编辑器场景 (IDE) ✅ 已实现
**目标应用**：VSCode, Trae, Cursor 等 (基于 Electron 构建)
**核心技术**：IDE 伴生微插件 + 本地 HTTP 端口
- **实现原理**：由于 Electron 应用的文本缓冲区对外部 Accessibility API 屏蔽，ASU 无法强读。解决方案是开发一个极简的 IDE 伴生插件（`asu-ide-extension/`），该插件在 IDE 内部读取全文。插件申请随机动态端口，并将端口号持续更新至系统临时文件信标（`$TMPDIR/asu_ide_port.txt`）中。当 ASU 探测到 IDE 活跃时，读取该信标获取端口并发起 HTTP 请求拉取文本。
- **优势**：精准、无损地获取数万行代码上下文，无视操作系统沙盒限制。
- **实现位置**：`asu-ide-extension/extension.js` + `smart_copilot.py` → `AICardWindow._get_ide_port()` + `read_from_ide_extension()`

### 3.3 原生文档应用 (DOC) 🔶 待开发
**目标应用**：Pages, 备忘录 (Notes), TextEdit 等
**核心技术**：macOS Accessibility API (AXAPI)
- **实现原理**：利用 `ApplicationServices` 库跨进程遍历系统原生的无障碍语义树，提取 `AXDocument` 或 `AXTextArea` 节点中的 `AXValue`。
- **优势**：系统官方支持的跨进程读取通道，适用于标准的 macOS 原生富文本应用。

### 3.4 终极兜底方案 (Fallback) ✅ 已实现
**目标应用**：未安装插件的 IDE、未授权的浏览器、第三方自绘引擎软件（如微信、WPS 等）
**核心技术**：原生物理拖拽 (Drag & Drop)
- **实现原理**：当所有高阶静默探针均失效或不可用时，系统降级。ASU 卡片提示用户主动选中文本，并将高亮文本**物理拖拽**入悬浮卡片中。卡片对点击外部采用 300ms 延迟隐藏机制，确保拖拽操作不被中断。
- **优势**：利用系统底层的内存级 MIME 传输（`text/plain`），绕过剪贴板同步延迟，100% 保证操作安全与光标不丢失。
- **实现位置**：`smart_copilot.py` → `AICardWindow.dragEnterEvent()` + `dropEvent()` + `_delayed_hide()`

---

## 4. 架构实施路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **阶段一** | Bundle ID 探测器 + 浏览器 AppleScript 探针 + 拖拽兜底 UI | ✅ 已完成 |
| **阶段二** | VSCode/Trae 伴生插件 + 临时文件端口信标 + IDE 全文读取 | ✅ 已完成 |
| **阶段三** | AXAPI 原生文档遍历器 (Pages/备忘录/TextEdit) | 🔶 待开发 |
| **阶段四** | 上下文感知智能体：Agent 自动识别文本来源 (IDE/浏览器/拖拽)，注入场景化 system prompt | ✅ 已完成 |
| **阶段五** | 会话持久化 + 上下文窗口管理 + 自定义 Persona | 🔶 待开发 |
| **阶段六** | Privileged Broker 特权代理 + WebSocket 事件推送 + 多 Provider 故障转移 | 🔶 待开发 |
