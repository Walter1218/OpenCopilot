# ASU (Advanced System Utilities) 🚀
**全局智能交互增强引擎 & 桌面级 AI Copilot**

ASU 是一个致力于探索**下一代人机交互模式**的系统级工具集。它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM (大语言模型) 能力深度结合，旨在打造“不打断用户心流”的极致 AI 体验。

## ✨ 核心亮点 (Core Features)

1. **三引擎动态热切架构 (Tri-Engine Architecture)**
   首创三模式无缝切换，在 UI 设置面板中一键切换：
   - ☁️ **云端 LLM (MiniMax)**：开箱即用，极速响应。
   - 💻 **本地/第三方 LLM (Ollama/vLLM)**：支持标准 OpenAI 协议的本地推理服务。
   - 🤖 **本地智能体 (OpenClaw Server)**：原生对接 OpenClaw HTTP Server 模式，程序启动时自动探测 18791 端口并在后台静默拉起服务端，实现真正的流式输出与零冷启动延迟。

2. **全局智能划词与无缝追问 (Global Smart Selection & Context Chat)**
   - 任意软件（IDE、浏览器、文档）中选中文字松开鼠标，即可触发智能悬浮卡片。
   - 告别单轮对话，首创 **“连续对话 (Copilot Tab)”**：将初步解析无缝带入多轮聊天上下文，支持类似微信的流式追问体验。

3. **双图层解耦与多屏边缘适配 (Layer Decoupling & Multi-Screen Adaptation)**
   - 采用创新的**双图层架构**：全屏穿透图层负责绘制高刷光标特效（呼吸准星、水波纹）；局部交互图层负责承载 AI 悬浮卡片。
   - 彻底解决传统悬浮窗“抢夺焦点”或“鼠标事件穿透冲突”的死结。
   - **多显示器无缝跨越**：特效层自动遍历并联合所有外接屏幕（`united geometry`），实现跨屏无缝渲染。
   - **智能边缘防遮挡与翻转**：实时识别鼠标所在屏幕，若卡片靠近边缘会自动向左或向上翻转；配合坐标强制钳位（Clamp），确保卡片在任何分辨率下永不越界或被裁切。

4. **极低资源占用的系统级监听 (Low-Footprint System Hooks)**
   - 极致轻量化设计，剔除了臃肿的 `pyautogui` 与 `pyperclip` 等强依赖，全部基于 `pynput` 与原生系统调用（如 macOS 的 `pbpaste`）完成热键与剪贴板捕获，大大降低了环境配置难度。
   - 内置防抖与日志轮转机制（限制单文件 20MB），保障后台常驻不漏水。

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保您的设备已安装 Python 3.10+。

```bash
git clone https://github.com/Walter1218/ASU.git
cd ASU
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. ⚠️ 重要运行说明 (沙盒与权限)
**如果您要使用本地智能体 (OpenClaw) 模式，请务必在原生系统终端 (Terminal/iTerm) 中启动本程序，请勿在带有权限沙盒的 IDE 内置终端中启动！**
因为沙盒环境会拦截 OpenClaw 引擎对本机 `~/.openclaw` 配置与锁文件的读写权限，导致 `EPERM: operation not permitted` 错误。

### 3. 启动程序
```bash
python smart_copilot.py
```

### ⚠️ macOS 权限提示
作为系统级增强工具，首次运行脚本时需在 macOS `系统设置 -> 隐私与安全性` 中授予终端或 IDE 以下权限：
1. **辅助功能 (Accessibility)**：用于全局鼠标位置与按键拦截。
2. **屏幕录制/键盘访问**：用于触发系统级文本抓取。