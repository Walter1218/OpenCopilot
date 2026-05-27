# OpenCopilot 系统运行指南

> **版本**：v2.0 | **日期**：2026-05-28  
> **状态**：阶段1-4已实现，文件拖拽功能已验证通过

---

## 一、系统架构概述

```
OpenCopilot 系统架构
├── UI 层 (smart_copilot.py)
│   ├── AICardWindow - 悬浮卡片主界面
│   ├── SettingsDialog - 设置对话框
│   ├── CursorOverlay - 光标特效层
│   └── 各种 UI 组件 (widgets/)
├── Agent 层 (asu_custom_agent.py)
│   ├── FastAPI 服务 (端口 18888)
│   ├── LLM Provider 抽象层
│   ├── 会话管理 (SQLite)
│   └── Persona 系统
└── Broker 层 (asu_broker/)
    ├── 特权代理服务
    ├── 系统探针
    └── 沙盒穿透
```

---

## 二、环境准备

### 2.1 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 12+ (Monterey 或更高) |
| Python | 3.11 ~ 3.13 (推荐 3.11) |
| 权限 | 辅助功能、屏幕录制 |

### 2.2 安装依赖

```bash
# 克隆项目
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot

# 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2.3 依赖包说明

| 包名 | 版本 | 用途 |
|------|------|------|
| pynput | >=1.8.2 | 鼠标/键盘监听 |
| PyQt6 | 6.7.0 | GUI 框架 |
| httpx | >=0.24.0 | HTTP 客户端 |
| python-dotenv | 1.0.1 | 环境变量管理 |
| markdown | >=3.5 | Markdown 渲染 |
| Pygments | >=2.17.0 | 代码高亮 |
| fastapi | >=0.100.0 | Agent 服务框架 |
| uvicorn | >=0.23.0 | ASGI 服务器 |

---

## 三、权限配置 (macOS)

### 3.1 辅助功能权限

1. 打开 **系统设置** → **隐私与安全性** → **辅助功能**
2. 点击 `+` 添加终端应用 (Terminal / iTerm2 / Trae)
3. 勾选启用

### 3.2 屏幕录制权限 (可选)

1. 打开 **系统设置** → **隐私与安全性** → **屏幕录制**
2. 添加终端应用

### 3.3 权限检测

系统启动时会自动检测权限，如果未授权会弹窗提示。

---

## 四、启动方式

### 方式一：守护进程模式 (推荐)

适用于日常使用，一次性安装，开机自启。

```bash
# 1. 注册 macOS LaunchAgent
bash scripts/install_daemon.sh

# 2. 启动 UI
bash scripts/start_ui.sh
```

**说明**：
- Agent 和 Broker 将作为后台服务运行
- 开机自动启动
- UI 启动时会自动探活 Agent

### 方式二：开发调试模式

适用于开发调试，需要两个终端。

```bash
# 终端 1：启动 Agent 后台服务
python asu_custom_agent.py

# 终端 2：启动 UI
bash scripts/start_ui.sh
```

**说明**：
- Agent 和 UI 生命周期独立
- UI 启动时异步检测 Agent 状态
- 标题栏显示绿/红状态点

### 方式三：直接运行 Python

```bash
# 启动 Agent
python asu_custom_agent.py &

# 启动 UI
python smart_copilot.py
```

---

## 五、系统状态检测

### 5.1 检查 Agent 是否在线

```bash
curl http://127.0.0.1:18888/health
```

**响应示例**：
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": 3600
}
```

### 5.2 查看 Agent 日志

```bash
bash scripts/tail_logs.sh
```

### 5.3 UI 状态指示

| 状态点颜色 | 含义 |
|------------|------|
| 🟢 绿色 | Agent 在线，正常交互 |
| 🔴 红色 | Agent 离线，UI 仍可打开 |
| 🟠 橙色横幅 | Agent 离线提示 |

---

## 六、常用管理命令

### 6.1 守护进程管理

```bash
# 安装守护进程
bash scripts/install_daemon.sh

# 卸载守护进程
bash scripts/uninstall_daemon.sh

# 查看日志
bash scripts/tail_logs.sh
```

### 6.2 进程管理

```bash
# 查看 Agent 进程
ps aux | grep asu_custom_agent

# 查看 UI 进程
ps aux | grep smart_copilot

# 终止进程
kill <PID>
```

### 6.3 端口检查

```bash
# 检查 Agent 端口 (18888)
lsof -i :18888

# 检查 Broker 端口 (如果启用)
lsof -i :18889
```

---

## 七、配置文件

### 7.1 LLM 配置

配置文件位置：`~/.asu_copilot/config.json`

```json
{
  "provider": "minimax",
  "api_key": "your-api-key",
  "model": "MiniMax-Text-01",
  "temperature": 0.7
}
```

### 7.2 环境变量

创建 `.env` 文件：

```env
# MiniMax API
MINIMAX_API_KEY=your-api-key
MINIMAX_GROUP_ID=your-group-id

# Ollama (本地)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### 7.3 快捷键配置

在 UI 设置中可自定义快捷键：

| 默认快捷键 | 功能 |
|------------|------|
| `Cmd+Shift+Space` | 唤醒/隐藏卡片 |
| `Cmd+Shift+T` | 翻译模式 |
| `Cmd+Shift+P` | 润色模式 |
| `Cmd+Shift+R` | 文档修订模式 |
| `Cmd+Shift+S` | 打开设置 |

---

## 八、使用指南

### 8.1 基本操作

#### 唤醒卡片
- **双击右键**：唤出快捷悬浮卡片
- **三击右键**：唤出任务工作台

#### 文本投喂
1. 在任意软件中划选文本
2. 双击右键唤出卡片
3. 将高亮文本拖拽到卡片
4. AI 自动流式解析

#### 关闭卡片
- 点击卡片右上角的 `✕` 按钮

### 8.2 功能模式

| 模式 | 说明 | 触发方式 |
|------|------|----------|
| 自动模式 | AI 自动判断任务类型 | 默认模式 |
| 翻译模式 | 中英互译 | `Cmd+Shift+T` |
| 润色模式 | 文本润色优化 | `Cmd+Shift+P` |
| 代码解析 | 代码解释分析 | 点击按钮 |
| 全文修订 | 文档整体修订 | `Cmd+Shift+R` |

### 8.3 IDE 集成

1. 安装 `asu-ide-extension/` 目录下的 `.vsix` 插件
2. 双击右键唤出卡片
3. 点击绿色 **[📥 极速读取当前 IDE 全文]** 按钮

### 8.4 浏览器集成

1. 确保 Broker 运行：`python3 asu_broker/run.py`
2. 在浏览器中浏览网页
3. 双击右键唤出卡片
4. 点击橙色 **[🌐 一键读取当前网页全文]** 按钮

---

## 九、故障排查

### 9.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 鼠标监听不工作 | 辅助功能权限未授予 | 检查系统设置权限 |
| UI 无法启动 | PyQt6 插件路径问题 | 使用 `scripts/start_ui.sh` |
| Agent 连接失败 | 端口被占用或服务未启动 | 检查端口 18888 |
| 卡片不显示 | 多屏幕适配问题 | 检查显示器配置 |
| 文本拖拽无效 | 权限问题 | 检查辅助功能权限 |

### 9.2 日志位置

```
~/.asu_copilot/
├── logs/
│   ├── agent.log          # Agent 日志
│   ├── ui.log             # UI 日志
│   └── broker.log         # Broker 日志
└── config.json            # 配置文件
```

### 9.3 重置配置

```bash
# 备份配置
cp ~/.asu_copilot/config.json ~/.asu_copilot/config.json.bak

# 删除配置
rm ~/.asu_copilot/config.json

# 重启系统
```

---

## 十、项目结构

```
OpenCopilot/
├── smart_copilot.py              # UI 主程序
├── asu_custom_agent.py           # Agent 后台服务
├── cursor_effects.py             # 光标特效库
├── llm_provider.py               # LLM Provider 抽象层
├── system_probe_client.py        # 系统探针客户端
├── markdown_renderer.py          # Markdown 渲染器
├── requirements.txt              # Python 依赖
├── README.md                     # 项目说明
├── scripts/                      # 启动脚本
│   ├── install_daemon.sh         # 安装守护进程
│   ├── uninstall_daemon.sh       # 卸载守护进程
│   ├── start_ui.sh               # 启动 UI
│   └── tail_logs.sh              # 查看日志
├── core/                         # 核心模块
│   ├── theme_manager.py          # 主题管理
│   └── shortcut_manager.py       # 快捷键管理
├── widgets/                      # UI 组件
│   ├── settings_dialog.py        # 设置对话框
│   ├── progress_widget.py        # 进度组件
│   ├── context_menu.py           # 上下文菜单
│   ├── file_drop_zone.py         # 文件拖拽区
│   ├── batch_dialog.py           # 批量处理
│   ├── terminology_dialog.py     # 术语库管理
│   └── translation_memory.py     # 翻译记忆
├── asu-ide-extension/            # IDE 插件
├── asu_broker/                   # Broker 服务
└── tests/                        # 测试文件
    └── unit/                     # 单元测试
```

---

## 十一、开发模式

### 11.1 启动开发环境

```bash
# 终端 1：启动 Agent (热重载)
uvicorn asu_custom_agent:app --reload --port 18888

# 终端 2：启动 UI
python smart_copilot.py

# 终端 3：运行测试
python -m pytest tests/unit/ -v
```

### 11.2 调试技巧

1. **查看 Agent 日志**：`tail -f ~/.asu_copilot/logs/agent.log`
2. **检查 UI 状态**：标题栏状态点颜色
3. **测试 API**：`curl http://127.0.0.1:18888/health`
4. **查看进程**：`ps aux | grep -E "(asu_custom_agent|smart_copilot)"`

---

## 十二、卸载

```bash
# 1. 卸载守护进程
bash scripts/uninstall_daemon.sh

# 2. 删除配置
rm -rf ~/.asu_copilot

# 3. 删除项目
rm -rf /path/to/OpenCopilot
```

---

## 附录：快速命令速查

| 命令 | 说明 |
|------|------|
| `bash scripts/install_daemon.sh` | 安装守护进程 |
| `bash scripts/start_ui.sh` | 启动 UI |
| `bash scripts/uninstall_daemon.sh` | 卸载守护进程 |
| `bash scripts/tail_logs.sh` | 查看日志 |
| `curl http://127.0.0.1:18888/health` | 检查 Agent 状态 |
| `python asu_custom_agent.py` | 启动 Agent (开发模式) |
| `python smart_copilot.py` | 启动 UI (开发模式) |
