# ASU: Advanced System Utilities

本项目包含三个用于鼠标监控与交互增强的独立工具脚本。

## 1. 环境准备

建议使用 Python 3.8+ 虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 依赖库说明 (`requirements.txt`)
- `pynput`: 用于全局监听鼠标的移动和点击事件。
- `PyQt6`: 用于绘制无边框、鼠标穿透的透明悬浮窗特效。
- `pyautogui` & `pyperclip`: 用于触发系统级按键和剪贴板读写。
- `openai`: 用于对接 MiniMax 兼容 OpenAI 格式的 LLM API 接口。

---

## 2. 工具列表

### 2.1 MiniMax LLM 接口模块 (`minimax_provider.py`)
- **功能**：作为本项目核心的 LLM API Provider 模块，集成了 MiniMax 的大语言模型能力。
- **特性**：
  - 采用 OpenAI 兼容格式调用 `https://api.minimax.chat/v1` 接口。
  - 支持最新的 `MiniMax-M2.7` 模型。
  - 完美适配并返回 MiniMax **Token Plan**（计费与配额）的 Tokens 消耗统计（包含 prompt_tokens, completion_tokens 等）。
  - 支持同步对话与流式输出（Stream）两种模式。
- **用法示例**：
  ```python
  from minimax_provider import MiniMaxProvider
  
  provider = MiniMaxProvider(api_key="你的API_KEY")
  content, usage = provider.chat("你好", model="MiniMax-M2.7")
  print("回答:", content, "消耗:", usage)
  ```

### 2.2 鼠标轨迹后台记录器 (`mouse_tracker.py`)
- **功能**：静默监听全局鼠标的移动、点击、滚动，并以 `0.1秒` 节流的频率写入日志。
- **产出**：在当前目录下生成 `mouse_tracking.log` 文件。
- **启动方式**：
  ```bash
  python mouse_tracker.py
  ```

### 2.3 屏幕动态光标特效 (`dynamic_cursor.py`)
- **功能**：在屏幕上绘制一个跟随鼠标移动的科幻蓝色十字准星，具备呼吸灯动画、彗星拖尾特效以及点击时的橙色水波纹特效。
- **技术亮点**：
  - 支持 macOS Retina 高 DPI 屏幕下的坐标精准映射。
  - 支持多显示器全屏无缝覆盖。
  - 使用了 `BypassWindowManagerHint` 防止窗口在 macOS 失去焦点时被隐藏。
- **启动方式**：
  ```bash
  python dynamic_cursor.py
  ```

### 2.4 全局划词捕获器 (`text_selector.py`)
- **功能**：监听鼠标拖拽事件，当检测到用户在任意窗口中划选了文本后，自动触发复制快捷键（基于 `pyautogui`），并通过剪贴板获取该文本打印到终端。
- **启动方式**：
  ```bash
  python text_selector.py
  ```

---

## 3. 权限提示 (针对 macOS)

首次运行以上任何脚本时，系统可能弹出权限请求：
1. **辅助功能 (Accessibility)**：需要授权给终端 (Terminal/IDE) 以便 `pynput` 获取鼠标事件。
2. **屏幕录制/键盘访问**：为了使 `pyautogui` 能发送复制快捷键。

*注意：本指南基于当前最新的代码实现，删除了此前关于 AppleScript 和基础准星等过时信息，保障时效性。*