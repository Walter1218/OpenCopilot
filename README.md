# OpenCopilot (Advanced System Utilities) 🚀
**全局智能交互增强引擎 & 桌面级 AI Copilot**

> **版本**：v2.1 | **日期**：2026-05-28 | **状态**：P0-P2 阶段（主动感知、多模态、Persona 工作坊等）已全面完成

OpenCopilot 是一个致力于探索**下一代人机交互模式**的系统级工具集。它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM (大语言模型) 能力深度结合，旨在打造"不打断用户心流"的极致 AI 体验。

## ✨ 核心亮点 (Core Features)

1. **上下文感知专属智能体 (Context-Aware Agent)**
   后台定制智能体（`asu_custom_agent.py`, 端口 18888）不仅仅是 LLM 的代理层：
   - **场景自动感知**：根据文本来源（IDE 代码文件 / 浏览器网页 / 拖拽文本），自动注入对应的 system prompt 前缀，让 AI 从"通用问答"升级为"场景化分析"。
   - **多角色人格**：内置翻译官、架构师、编辑、通用助手、自定义修改五种 Persona，支持通过 `session_id` 实现多轮对话记忆。
   - **自定义指令修改**：拖拽文本后可输入修改指令，AI 严格按指令输出修改结果，支持一键回写到 IDE。
   - **健康检查**：提供 `GET /health` 端点，UI 启动时异步探活并在标题栏显示绿/红状态点。

2. **双引擎动态热切架构 (Dual-Engine Architecture)**
   在 UI 设置面板中一键切换后端驱动引擎：
   - ☁️ **云端 LLM (MiniMax)**：开箱即用，极速响应。
   - 💻 **本地/第三方 LLM (Ollama/vLLM)**：支持标准 OpenAI 协议的本地推理服务。
   *Agent 与 Broker 均作为独立 OS 级守护进程运行（LaunchAgent 开机自启），UI 启动时仅探活。*

3. **纯鼠标双击唤醒与悬浮拖拽投喂**
   - 任意软件中**双击鼠标右键**，即可在鼠标旁唤出智能悬浮卡片（快捷模式）。
   - **三击鼠标右键**唤出独立任务工作台，用于设定全局任务背景和独立深度对话。
   - 工作台设定的任务会自动注入到快捷卡片的 AI 请求中，实现"定义任务 → 划词执行"的聚焦工作流。

4. **双图层解耦与多屏边缘适配 (Layer Decoupling & Multi-Screen Adaptation)**
   - 采用**双图层架构**：全屏穿透图层负责绘制高刷光标特效（呼吸准星、拖尾轨迹、水波纹）；局部交互图层负责承载 AI 悬浮卡片。
   - 光标特效模块已提取为独立共享库 `cursor_effects.py`，避免代码重复。
   - **多显示器无缝跨越**：特效层自动联合所有外接屏幕进行跨屏渲染。
   - **智能边缘防遮挡与翻转**：实时识别鼠标所在屏幕，自动翻转 + 坐标钳位（Clamp）确保卡片永不越界。

5. **极低资源占用的系统级监听 (Low-Footprint System Hooks)**
   - 基于 `pynput` 与原生系统调用（如 macOS 的 `pbpaste`），极致轻量化。
   - 内置防抖与日志轮转机制（限制单文件 20MB），保障后台常驻稳定。

6. **基于 Privileged Broker 的极客级交互**
   - 彻底解决 macOS 的 TCC 沙盒限制与进程内调用 AppleScript 导致的 `-10004 权限违例` 崩溃。
   - 预埋系统级探针，支持静默获取浏览器 DOM、系统剪贴板读写、高亮选区提取、屏幕 OCR 截图、甚至突破 IDE 文件沙盒直接读取全局文件。

---

## 🗺️ 开发路线图 (Roadmap)

| 阶段 | 内容 | 状态 |
|------|------|------|
| 双图层光标特效 + 双击右键唤醒 + 拖拽投喂 | 基础交互 | ✅ |
| 双引擎 AI 后端 (MiniMax + Ollama) + 设置面板 | LLM 接入 | ✅ |
| 专属智能体 (会话记忆 + Persona + 健康检查) | Agent 服务 | ✅ |
| IDE 伴生插件 + 动态端口信标 + 全文静默读取 | IDE 场景 | ✅ |
| 浏览器 DOM 读取 (AppleScript) + 多屏适配 | 浏览器场景 | ✅ |
| Privileged Broker 特权代理集成 (沙盒穿透/高权限探针) | 架构升级 | ✅ |
| 上下文感知 (Agent 识别 IDE/浏览器/拖拽来源) | Agent 增强 | ✅ |
| 三击右键任务工作台 (任务定义 + 独立对话 + 上下文贯通) | 工作台 | ✅ |
| 代码重构：cursor_effects 共享库 + 拖拽卡死修复 | 工程优化 | ✅ |
| SQLite 会话持久化 + Persona 文件化 | Agent 增强 | ✅ |
| Markdown 渲染 + 代码高亮 + 卡片拖拽缩放 | UI 增强 | ✅ |
| UI/Agent 生命周期解耦 + macOS LaunchAgent 常驻 | 架构升级 | ✅ |
| Broker 产品化 (LaunchAgent 常驻 + capabilities + 统一错误) | 架构升级 | ✅ |
| 上下文窗口管理 (超长历史自动截断，防 token 超限) | Agent 增强 | ✅ |
| 自定义指令修改 + IDE 选区回写 + custom Persona | 交互增强 | ✅ |
| AXAPI 原生无感选区提取 (替代手动复制) | 场景扩展 | ✅ |
| IDE Extension v2 (诊断/git diff 端点) | IDE 增强 | 🔶 |
| 多 Provider 故障转移 (云端挂了回退本地) | 稳定性 | 🔶 |
| Broker WebSocket 主动推送 (前台应用切换事件) | 主动感知 | ✅ |
| 视觉感知前台 (Vision OCR) | 多模态 | ✅ |
| 角色工坊 (Persona Workshop) | 用户定制 | ✅ |

---

## 📚 进阶架构设计文档
- 👉 [OpenCopilot 定制智能体 (Custom Agent) 开发与使用指南](OpenCopilot_Custom_Agent_Guide.md)
- 👉 [OpenCopilot 特权代理模式集成与开发指南](OpenCopilot_Broker_Development_Guide.md)
- 👉 [OpenCopilot 下一代架构演进路线图 (Next-Gen Roadmap)](OpenCopilot_Next_Gen_Roadmap.md)
- 👉 [OpenCopilot 全场景智能上下文获取方案](OpenCopilot_Architecture_Context_Extraction.md)
- 👉 [OpenCopilot Code Review 报告 (2026-05-23)](OpenCopilot_Code_Review_Report.md)

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -r requirements.txt
```

> **Python 版本说明**：推荐 Python 3.11~3.13。如遇 `pynput` 鼠标监听闪退，请降至 3.11。

### 2. ⚠️ 权限要求
首次运行需在 macOS `系统设置 -> 隐私与安全性` 中授予终端以下权限：
1. **辅助功能 (Accessibility)**：用于全局鼠标位置与按键拦截。
2. **屏幕录制/键盘访问**：用于触发系统级文本抓取。

### 3. 启动程序

**方式一：守护进程模式（推荐，一次性安装，开机自启）**

```bash
# 注册 macOS LaunchAgent，安装后 Agent 立即后台启动，并开机自动重启
bash scripts/install_daemon.sh

# 启动 UI（自动处理 Qt 插件路径）
bash scripts/start_ui.sh
```

**方式二：开发调试模式（两个终端）**

```bash
# 终端 1：启动 Agent 后台服务
python asu_custom_agent.py

# 终端 2：启动 UI
bash scripts/start_ui.sh
```

> **说明**：Agent（端口 18888）和 UI 生命周期完全独立。UI 启动时异步探活 Agent——
> - 🟢 Agent 在线：标题栏绿色状态点，正常交互。
> - 🔴 Agent 离线：标题栏红色状态点 + 橙色横幅提示，UI 仍可正常打开。

**常用管理命令**

```bash
bash scripts/tail_logs.sh          # 实时查看 Agent 日志
bash scripts/uninstall_daemon.sh   # 卸载守护进程
curl http://127.0.0.1:18888/health # 检查 Agent 是否在线
```

### 4. P0 上下文窗口治理验证结果（2026-05）

- **测试范围**：真实多轮场景 + 边界压力场景
- **通过情况**：`39/39`（`100%`）
- **平均压缩率**：`69.3%`
- **平均历史保留率**：`51.2%`（稳定性优先的预期策略）
- **分场景压缩率**：
  - `ide_large_file`：`74.1%`
  - `browser_long_article`：`70.2%`
  - `chat_long_session`：`58.9%`
  - `drag_bulk_text`：`73.9%`

> 注：历史保留率不是越高越好；当前策略优先保证不超上下文预算与响应稳定性。

### 5. 操作指南

**方式一：物理拖拽（通用，100% 兼容）**
1. 在任何软件中划选文本。
2. 双击右键唤出悬浮卡片（卡片将保持常驻）。
3. 将高亮文本**拖拽**丢入卡片，AI 自动流式解析。
3. **关闭**：分析完成后，点击卡片右上角的 `✕` 按钮即可隐藏。

**方式二：IDE 全文静默读取 (VSCode/Trae/Cursor)**
1. 安装 `asu-ide-extension/` 目录下的 `.vsix` 插件。
2. 双击右键唤出卡片 → 点击绿色 **[📥 极速读取当前 IDE 全文]** 按钮。
3. 当前编辑器内全部代码瞬间投喂给 AI。（Broker 也可以通过文件探针提供更深度的支持）

**方式三：基于 Broker 的浏览器无感读取**
1. 确保已在原生终端启动 `python3 asu_broker/run.py`。
2. 在 Chrome/Safari/Brave/Edge/Arc 中浏览网页。
3. 双击右键唤出卡片 → 点击橙色 **[🌐 一键读取当前网页全文]** 按钮。
4. Broker 将在后台提取 DOM 节点并穿透沙盒返回给 AI。（初次使用仍需在浏览器启用 `Allow JavaScript from Apple Events`）

---

## 🏗️ 项目结构

```text
OpenCopilot/
├── smart_copilot.py              # UI 主程序（悬浮卡片 + 工作台）
├── asu_custom_agent.py           # Agent 后台服务（端口 18888）
├── cursor_effects.py             # 光标特效共享库（Ripple + CursorOverlay）
├── llm_provider.py               # LLM Provider 抽象层
├── dynamic_cursor.py             # 光标特效独立演示程序
├── mouse_tracker.py              # 鼠标轨迹日志工具
├── text_selector.py              # [已废弃] 模拟 Cmd+C 自动捕获方案（当前使用拖拽+粘贴按钮共存）
├── personas/                     # Persona 人格文件
│   └── custom.md                 #   自定义修改指令专用人格
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Cursor/Trae)
├── scripts/                      # 管理脚本
│   ├── start_ui.sh               #   启动 UI（自动设置 Qt 插件路径）
│   ├── install_daemon.sh         #   安装 Agent 为 macOS LaunchAgent
│   ├── uninstall_daemon.sh       #   卸载 Agent 守护进程
│   ├── install_broker_daemon.sh  #   安装 Broker 为 macOS LaunchAgent
│   ├── uninstall_broker_daemon.sh#   卸载 Broker 守护进程
│   └── tail_logs.sh              #   实时查看 Agent 日志
├── deploy/                       # 部署配置
│   ├── com.asu.agent.plist       #   Agent macOS LaunchAgent 配置模板
│   └── com.asu.broker.plist      #   Broker macOS LaunchAgent 配置模板
├── requirements.txt              # Python 依赖
└── *.md                          # 架构文档
```
