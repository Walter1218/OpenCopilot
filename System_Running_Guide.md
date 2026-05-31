# OpenCopilot 系统运行指南

> **版本**：v2.2 | **日期**：2026-05-31  
> **状态**：包含知识图谱、PPT共创模式、统一启动脚本等最新特性，P0-P2 阶段已全面落地。

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
| python-pptx | >=0.6.23 | PPT 幻灯片生成 |

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

## 四、启动方式 (新架构 P1 阶段)

由于 macOS 沙盒权限的限制（IDE 内置终端无法获取系统级的屏幕录制和辅助功能权限），系统目前采用了**前后端分离（特权 Broker + 用户态 UI）**的运行架构。

根据您的使用场景，请选择以下一种方式：

### 方式一：开发联调期 (Development)
在开发期，为了查看实时的报错和异常栈，需要**手动开启两个终端窗口**：

#### 方案 A：统一启动（推荐）

使用统一启动脚本，同时启动 Broker 和知识图谱 API：

1. **启动后端服务（Broker + 知识图谱）**
   - **必须使用 macOS 原生的 Terminal.app 或 iTerm2**（不能用 IDE 终端）。
   - **命令**：
     ```bash
     source venv/bin/activate
     python start_broker_with_kg.py
     ```
   - *此命令会同时启动：*
     - *Broker 服务（端口 18889）：系统焦点监听、无感划词提取、视觉屏幕抓取等特权操作*
     - *知识图谱 API（端口 8090）：项目知识查询*

2. **启动前端 UI 与智能中枢 (Smart Copilot)**
   - 可以在任何终端中运行（包括 Trae/VSCode 的内置终端）。
   - **命令**：
     ```bash
     source venv/bin/activate
     python smart_copilot.py
     ```

#### 方案 B：分别启动

如需单独控制各服务，可分别启动：

1. **启动底层特权探针 (Privileged Broker)**
   - **必须使用 macOS 原生的 Terminal.app 或 iTerm2**（不能用 IDE 终端）。
   - **命令**：
     ```bash
     source venv/bin/activate
     python asu_broker/run.py
     ```
   - *此进程负责系统焦点监听、无感划词提取、视觉屏幕抓取等特权操作。*

2. **（可选）启动知识图谱 API**
   - 如需查询项目知识，可单独启动：
     ```bash
     python start_knowledge_graph_api.py --port 8090
     ```

3. **启动前端 UI 与智能中枢 (Smart Copilot)**
   - 可以在任何终端中运行（包括 Trae/VSCode 的内置终端）。
   - **命令**：
     ```bash
     source venv/bin/activate
     python smart_copilot.py
     ```

### 方式二：生产使用期 (Production / Daily Use)
作为日常工具使用时，不应每次开机都敲击命令，而是让底层的探测器静默常驻，让 UI 触手可及。

#### 方案 A：统一守护进程（推荐）

同时启动 Broker 和知识图谱 API：

1. **一次性注册为开机自启**
   - 只需执行**一次**：
     ```bash
     bash scripts/install_unified_daemon.sh
     ```
   - 系统会将 Broker + 知识图谱 API 注册到 `LaunchAgent`。以后每次开机都会在后台静默运行。
   - *（如需查看日志：`tail -f ~/Library/Logs/ASU/unified_out.log`）*

2. **日常启动主程序 UI**
   - 当前可配置一个 Shell Alias 或 AppleScript 快速执行 `python smart_copilot.py`。
   - *(注：在未来的 P3 阶段，该 UI 会被打包成标准的 `.app` 应用程序，双击图标即可运行)*。

3. **管理命令**
   ```bash
   # 查看 Broker 状态
   curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health
   
   # 查看知识图谱状态
   curl http://127.0.0.1:8090/health
   
   # 卸载守护进程
   bash scripts/uninstall_unified_daemon.sh
   ```

#### 方案 B：仅 Broker 守护进程

如果不需要知识图谱 API，可以只启动 Broker：

1. **一次性注册 Broker 为开机自启**
   - 只需执行**一次**：
     ```bash
     bash scripts/install_broker_daemon.sh
     ```
   - 系统会将 Broker 注册到 `LaunchAgent`。以后每次开机它都会在后台静默运行。
   - *（如需查看日志：`tail -f ~/Library/Logs/ASU/broker_out.log`）*

2. **日常启动主程序 UI**
   - 当前可配置一个 Shell Alias 或 AppleScript 快速执行 `python smart_copilot.py`。

> **⚠️ 注意：关于 `install_daemon.sh`**
> 早期旧架构曾使用 `install_daemon.sh` 将 Agent 也作为独立 HTTP 服务挂载。在 P1 阶段重构合并后，此脚本已**废弃不再使用**。日常只需挂载 Broker 即可。

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

## 八、进阶场景与智能体能力说明

目前 OpenCopilot 已跨越传统的“对话机器人”形态，进化为 **多模态感知与上下文感知智能体 (Context-Aware & Multi-modal Agent)**，兼具工具增强特性。

### 8.1 全局环境感知 (Context-Aware)
- **行为感知**：无论是否呼出 UI，底层探针都在静默感知你的应用切换轨迹。（详细扩展设计与实现路径请参考 [全局环境感知设计文档](OpenCopilot_Global_Context_Awareness_Design.md)）
- **无感划词**：不需要 `Cmd+C`，选中文本后直接唤起卡片，底层通过 Accessibility API 自动提取选区。

### 8.2 深度工程感知 (IDE Extension v2)
- 在 VSCode/Trae 中写代码时，直接唤起卡片，AI 能通过 `/diagnostics` 和 `/symbol` 接口，自动抓取你的**代码报错（红波浪线）**和**光标所在的函数结构**，彻底告别“复制粘贴代码报错”。

### 8.3 多模态视觉与文档处理 (Multi-modal & Tool-Augmented)
- **视觉穿透**：点击「👁️ 视觉分析前台」，可绕过沙盒直接截取系统最前端窗口进行多模态分析。
- **一键生成 PPT**：
  - **操作方式**：将任意支持的文档（`.docx`, `.md`, `.txt` 等）直接**拖拽**到 Smart Copilot 的卡片中。
  - **指令输入**：在输入框中输入如 `“根据这份文档生成汇报PPT”`。
  - **导出**：AI 生成大纲后，卡片底部会出现 **「� 导出为 PPT」** 按钮，点击即可直接将大纲一键转换为真正的 `.pptx` 文件并保存到本地。

### 8.4 角色工坊 (Role-Playing Agent)
- 三连击右键呼出工作台，或点击设置中的「� 角色工坊」，可为智能体注入特定的系统级 Prompt，使其在不同任务中表现为不同的专家角色。

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
| `bash scripts/install_broker_daemon.sh` | 安装底层特权 Broker (开机自启) |
| `bash scripts/uninstall_broker_daemon.sh`| 卸载底层特权 Broker |
| `python asu_broker/run.py` | 启动 Broker (开发联调模式) |
| `python smart_copilot.py` | 启动 UI 与智能中枢 (开发/日常模式) |
| `bash scripts/tail_logs.sh` | 查看日志 |
