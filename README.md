# ASU (Advanced System Utilities) 🚀
**全局智能交互增强引擎 & 桌面级 AI Copilot**

ASU 是一个致力于探索**下一代人机交互模式**的系统级工具集。它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM (大语言模型) 能力深度结合，旨在打造“不打断用户心流”的极致 AI 体验。

## ✨ 核心亮点 (Core Features)

1. **双引擎动态热切架构 (Dual-Engine Architecture)**
   在 UI 设置面板中一键切换后端驱动引擎：
   - ☁️ **云端 LLM (MiniMax)**：开箱即用，极速响应。
   - 💻 **本地/第三方 LLM (Ollama/vLLM)**：支持标准 OpenAI 协议的本地推理服务。
   *程序启动时会自动探测 18888 端口，并在后台静默拉起专属定制智能体（`asu_custom_agent.py`），实现多轮对话与身份记忆的底层托管。*

2. **纯鼠标双击唤醒与悬浮靶心拖拽 (Pure Mouse Wake-up & Drag-and-Drop Target)**
   - 任意软件（IDE、浏览器、文档）中**双击鼠标右键**，即可在鼠标旁唤出智能悬浮卡片。
   - 将选中的文本**手动拖拽**到悬浮卡片中完成投喂。这一设计巧妙利用了系统原生的拖拽 API，完美避开了自动模拟 `Cmd+C` 触发操作系统底层防护导致 IDE 光标丢失的死结。
   - 告别单轮对话，首创 **“连续对话 (Copilot Tab)”**：后台智能体通过 `session_id` 自动管理对话历史和角色状态（如翻译官、架构师），无缝支持类似微信的流式多轮追问体验。

3. **双图层解耦与多屏边缘适配 (Layer Decoupling & Multi-Screen Adaptation)**
   - 采用创新的**双图层架构**：全屏穿透图层负责绘制高刷光标特效（呼吸准星、水波纹）；局部交互图层负责承载 AI 悬浮卡片。
   - 彻底解决传统悬浮窗“抢夺焦点”或“鼠标事件穿透冲突”的死结。
   - **多显示器无缝跨越**：特效层自动遍历并联合所有外接屏幕（`united geometry`），实现跨屏无缝渲染。
   - **智能边缘防遮挡与翻转**：实时识别鼠标所在屏幕，若卡片靠近边缘会自动向左或向上翻转；配合坐标强制钳位（Clamp），确保卡片在任何分辨率下永不越界或被裁切。

4. **极低资源占用的系统级监听 (Low-Footprint System Hooks)**
   - 极致轻量化设计，剔除了臃肿的 `pyautogui` 与 `pyperclip` 等强依赖，全部基于 `pynput` 与原生系统调用（如 macOS 的 `pbpaste`）完成热键与剪贴板捕获，大大降低了环境配置难度。
   - 内置防抖与日志轮转机制（限制单文件 20MB），保障后台常驻不漏水。

---

## 📚 进阶架构设计文档
针对如何在 macOS 沙盒限制下，安全、无感地获取多场景（浏览器、IDE、文档）全局上下文的问题，我们提出了**智能场景路由+分层降级**架构，详情请参阅技术白皮书：
👉 [ASU 全场景智能上下文获取方案 (Architecture Proposal)](ASU_Architecture_Context_Extraction.md)

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保您的设备已安装 Python 3.10 或 3.11。
> **⚠️ 严重警告**：请勿使用 Python 3.13+！目前核心依赖 `pynput` 在 Python 3.13+ 版本存在底层 `_thread._ThreadHandle` 兼容性 Bug，会导致划词和鼠标监听直接闪退。

```bash
git clone https://github.com/Walter1218/ASU.git
cd ASU
# 请明确指定使用 python3.10 或 3.11 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. ⚠️ 运行说明 (权限要求)
作为系统级增强工具，首次运行脚本时需在 macOS `系统设置 -> 隐私与安全性` 中授予终端或 IDE 以下权限：
1. **辅助功能 (Accessibility)**：用于全局鼠标位置与按键拦截。
2. **屏幕录制/键盘访问**：用于触发系统级文本抓取。

### 3. 启动程序
强烈建议通过绝对路径调用虚拟环境中的 Python，以避免环境丢失导致的 `qt.qpa.plugin` 报错：
```bash
./venv/bin/python smart_copilot.py
```

### 4. 操作指南 (How to Use)
1. 在任何软件（如 IDE 代码编辑器）中，用鼠标左键划选你想要解释的代码或文本。
2. 鼠标原地**双击右键**，唤出智能悬浮卡片。
3. 将鼠标移回刚才划选的高亮区域，**按住左键**将该文本块拖拽并丢入悬浮卡片中。
4. AI 将自动识别文本并开始流式解析输出。