# ASU (Advanced System Utilities) 🚀
**全局智能交互增强引擎 & 桌面级 AI Copilot**

ASU 是一个致力于探索**下一代人机交互模式**的系统级工具集。它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM (大语言模型) 能力深度结合，旨在打造"不打断用户心流"的极致 AI 体验。

## ✨ 核心亮点 (Core Features)

1. **上下文感知专属智能体 (Context-Aware Agent)**
   后台定制智能体（`asu_custom_agent.py`, 端口 18888）不仅仅是 LLM 的代理层：
   - **场景自动感知**：根据文本来源（IDE 代码文件 / 浏览器网页 / 拖拽文本），自动注入对应的 system prompt 前缀，让 AI 从"通用问答"升级为"场景化分析"。
   - **多角色人格**：内置翻译官、架构师、编辑、通用助手四种 Persona，支持通过 `session_id` 实现多轮对话记忆。
   - **健康检查**：提供 `GET /health` 端点，主程序启动时自动探活。

2. **双引擎动态热切架构 (Dual-Engine Architecture)**
   在 UI 设置面板中一键切换后端驱动引擎：
   - ☁️ **云端 LLM (MiniMax)**：开箱即用，极速响应。
   - 💻 **本地/第三方 LLM (Ollama/vLLM)**：支持标准 OpenAI 协议的本地推理服务。
   *程序启动时自动探测 18888 端口，若未运行则在后台静默拉起专属智能体。*

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
| AXAPI 原生文档遍历器 (Pages/备忘录/TextEdit) | 场景扩展 | 🔶 |
| 会话持久化 (shelve/JSON，重启不丢对话) | Agent 增强 | 🔶 |
| 上下文窗口管理 (超长历史自动截断，防 token 超限) | Agent 增强 | 🔶 |
| 自定义 Persona (config 化 + GUI 管理) | Agent 增强 | 🔶 |
| 多 Provider 故障转移 (云端挂了回退本地) | 稳定性 | 🔶 |
| Markdown 渲染 + 代码高亮 + 卡片拖拽缩放 | UI 增强 | 🔶 |

---

## 📚 进阶架构设计文档
- 👉 [ASU 定制智能体 (Custom Agent) 开发与使用指南](ASU_Custom_Agent_Guide.md)
- 👉 [ASU 特权代理模式集成与开发指南](ASU_Broker_Development_Guide.md)
- 👉 [ASU 下一代架构演进路线图 (Next-Gen Roadmap)](ASU_Next_Gen_Roadmap.md)
- 👉 [ASU 全场景智能上下文获取方案](ASU_Architecture_Context_Extraction.md)
- 👉 [ASU Code Review 报告 (2026-05-23)](ASU_Code_Review_Report.md)

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保您的设备已安装 Python 3.10 或 3.11。
> **⚠️ 严重警告**：请勿使用 Python 3.13+！`pynput` 在 Python 3.13+ 存在底层 `_thread._ThreadHandle` 兼容性 Bug，会导致鼠标监听直接闪退。

```bash
git clone https://github.com/Walter1218/ASU.git
cd ASU
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. ⚠️ 权限要求
首次运行需在 macOS `系统设置 -> 隐私与安全性` 中授予终端以下权限：
1. **辅助功能 (Accessibility)**：用于全局鼠标位置与按键拦截。
2. **屏幕录制/键盘访问**：用于触发系统级文本抓取。

### 3. 启动程序
```bash
./venv/bin/python smart_copilot.py
```

### 4. 操作指南

**方式一：物理拖拽（通用，100% 兼容）**
1. 在任何软件中划选文本。
2. 双击右键唤出悬浮卡片。
3. 将高亮文本**拖拽**丢入卡片，AI 自动流式解析。

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
ASU/
├── smart_copilot.py              # 主程序入口（总调度管理器）
├── cursor_effects.py             # 光标特效共享库（Ripple + CursorOverlay）
├── asu_custom_agent.py           # 专属智能体 Server（端口 18888）
├── llm_provider.py               # LLM Provider 抽象层
├── dynamic_cursor.py             # 光标特效独立演示程序
├── mouse_tracker.py              # 鼠标轨迹日志工具
├── text_selector.py              # [已废弃] Cmd+C 剪贴板方案
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Cursor/Trae)
├── requirements.txt              # Python 依赖
└── *.md                          # 架构文档
```
