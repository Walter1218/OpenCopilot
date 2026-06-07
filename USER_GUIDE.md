# OpenCopilot 用户说明书

> 版本：v5.0 | 适用平台：macOS 12+ | 最后更新：2026-06-02  
> 状态：按当前 v5 主交互路径修订，已移除大部分旧版卡片文案

---

## 一、产品简介

OpenCopilot 是一款 macOS 系统级 AI 右键工具。它的目标不是把你带到另一个聊天窗口，而是在你当前正在使用的软件里，直接把 AI 带到你手边。

一句话理解：

- 选中内容
- 双击右键
- AI 就在当前工作流里介入

当前主交互基于 v5 界面，核心分为两种姿态：

- **双击右键**：打开 `Smart Copilot`
- **三击右键**：打开 `Workspace`

---

## 二、系统要求与权限

### 2.1 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 12 及以上 |
| Python | 3.11 ~ 3.13 |
| 运行环境 | 建议使用原生 Terminal.app 或 iTerm2 |

### 2.2 必需权限

打开“系统设置 -> 隐私与安全性”，为你使用的终端程序授予：

| 权限 | 用途 |
|------|------|
| 辅助功能 | 监听全局鼠标事件、读取系统级上下文 |
| 屏幕录制 | 部分视觉相关能力和桌面级采集 |

如果没有辅助功能权限，双击/三击右键通常不会生效。

---

## 三、启动方式

### 3.1 安装

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -e .
```

### 3.2 推荐启动组合

如果你主要使用桌面端 v5 交互，建议至少启动下面 3 个部分：

```bash
# 终端 1：Broker（必须在原生终端中运行）
bash start_broker.sh

# 终端 2：Agent 服务（推荐启动，便于健康检查和 HTTP 兼容链路）
python3 asu_custom_agent.py

# 终端 3：UI
bash scripts/start_ui.sh
```

如果你还需要 API 文档、HTTP 路由或 Studio 相关 `/api/*` 接口，再额外启动：

```bash
python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload
```

更完整的启动矩阵请参考 [docs/STARTUP_GUIDE.md](file:///Users/onetwo/Documents/trae_projects/OpenCopilot/docs/STARTUP_GUIDE.md)。

---

## 四、核心使用方式

## 4.1 Smart Copilot：双击右键

这是最常用的入口。

使用步骤：

1. 在任意软件中选中文本，或先准备好需要处理的内容
2. 双击鼠标右键
3. 打开 `Smart Copilot` v5 主窗口

当前 v5 的 `Smart Copilot` 有 3 个 Tab：

| Tab | 用途 | 当前状态 |
|------|------|----------|
| `Work` | 快速处理当前内容 | 已可用 |
| `Chat` | 连续对话与追问 | 已可用 |
| `Studio` | PPT 共创入口 | 基础可用，高级编辑仍在迭代 |

### 4.1.1 Work Tab

`Work` 适合快速处理当前选区或上下文内容。

当前主要按钮：

| 按钮 | 作用 |
|------|------|
| `Explain` | 解释当前内容 |
| `Fix` | 修复问题 |
| `Polish` | 润色表达 |
| `Translate` | 翻译内容 |
| `Code Review` | 代码审查 |
| `More` | 查看更多已配置操作 |

当前还支持 `Context Strip` 数据源切换：

| 数据源 | 说明 |
|------|------|
| `Selection` | 当前选区 |
| `Active Doc` | 当前活动文档 |
| `Browser` | 当前浏览器内容 |
| `Clipboard` | 剪贴板 |
| `File` | 文件内容 |

执行 AI 请求后，底部常见操作包括：

| 操作 | 说明 |
|------|------|
| `Copy` | 复制结果 |
| `Export PPT` | 将当前结果作为 PPT 相关内容继续导出/流转 |
| `Apply` | 尝试回写到 IDE 或回退到剪贴板 |

### 4.1.2 Chat Tab

`Chat` 用于连续对话和追问。

当前已具备：

- 基础多会话 UI
- 流式输出
- 停止生成
- 从 `Work` 或拖放内容中注入上下文

适用场景：

- 针对同一段材料连续追问
- 对同一个问题逐层拆解
- 在已有上下文基础上继续补充要求

### 4.1.3 Studio Tab

`Studio` 是 PPT 共创入口，不再建议理解成旧版的单个“PPT 按钮”。

当前你可以：

- 粘贴文本或输入主题
- 点击“快速创建”
- 让 AI 先生成基础 PPT 结构
- 打开独立 `StudioWindowV5`

需要注意：

- 当前 Studio 的**基础骨架已经可用**
- 但缩略图导航、真正的 WYSIWYG 预览编辑、统一撤销等高级体验仍在迭代中

所以它更适合作为“PPT 内容生成与初步组织入口”，而不是完全成熟的演示文稿编辑器。

## 4.2 Workspace：三击右键

三击鼠标右键会打开更大的 `Workspace` 窗口。

当前 v5 Workspace 采用 Sidebar + 5 Panel 结构：

| 面板 | 用途 | 当前状态 |
|------|------|----------|
| `Task` | 任务定义 | 基础骨架 |
| `Chat` | 对话区 | 基础骨架 |
| `Files` | 文件上下文 | 基础骨架 |
| `Memory` | 记忆/知识入口 | 基础骨架 |
| `Settings` | 设置入口 | 可用 |

要点说明：

- Workspace 的窗口壳和切换结构已经落地
- 但除设置入口外，很多面板仍属于“可见的骨架能力”，不是全部业务都已补完

因此当前更适合把它当成 **深度任务的工作台框架**，而不是所有功能都成熟的最终形态。

## 4.3 统一设置

当前推荐使用 v5 的统一设置窗口。

入口包括：

- Smart Copilot 标题栏的设置按钮
- Workspace 内的设置入口

当前设置分区：

| 分区 | 用途 |
|------|------|
| `Engine` | 云端/本地模型配置、连接测试 |
| `Appearance` | 主题、字体等外观配置 |
| `Shortcuts` | 快捷键设置 |
| `Advanced` | 高级配置、导入导出 |

---

## 五、上下文与数据来源

OpenCopilot 的价值不只是“发一个 prompt”，而是尽量理解你当前正在看的内容。

当前主要依赖 Broker 提供这些来源：

| 来源 | 当前支持情况 |
|------|--------------|
| 系统选区 | 已支持 |
| 活动文档 | 已支持基础读取 |
| 浏览器内容 | 已支持基础读取 |
| 剪贴板 | 已支持 |
| 文件内容 | 已支持基础读取 |

如果 Broker 未运行，这些上下文能力会明显退化。

---

## 六、当前完成度说明

为了避免误解，下面是当前 v5 功能的真实成熟度：

### 6.1 已经相对稳定的部分

- Smart Copilot 3-Tab 主窗口
- Work Tab 的基础操作链路
- Chat Tab 的基础连续对话链路
- Unified Settings
- NavigationManager 统一窗口调度

### 6.2 仍在完善中的部分

- Studio 的高级交互体验
- Workspace 的大部分业务面板
- 更完整的技能整合、命令面板和上下文推荐

如果你看到某些窗口里还有“功能待接入”或偏占位的内容，这属于当前版本的正常现状。

---

## 七、常用命令

| 操作 | 命令 |
|------|------|
| 启动 UI | `bash scripts/start_ui.sh` |
| 启动 Broker | `bash start_broker.sh` |
| 启动 Agent 服务 | `python3 asu_custom_agent.py` |
| 启动 API Gateway | `python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload` |
| 检查 Agent | `curl http://127.0.0.1:18888/health` |
| 检查 API Gateway | `curl http://127.0.0.1:8000/health` |
| 检查 Broker | `curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health` |

---

## 八、状态提示

当前 UI 标题栏中的状态点主要反映 Agent 服务探活结果。

| 状态 | 含义 |
|------|------|
| 绿色 | Agent 服务可达，完整服务态较正常 |
| 红色 | Agent 服务未探活成功，部分服务链路可能不可用或退化 |

需要注意：

- 某些桌面 AI 调用会复用本地 Pipeline 实现
- 但从用户体验上，仍建议把 Agent 服务视为推荐常驻组件

---

## 九、常见问题

### Q1：双击右键没反应？

先检查：

- 当前终端是否已授予辅助功能权限
- 是否真的在原生终端里启动
- Broker 是否已经正常运行

### Q2：为什么能打开 UI，但上下文获取不稳定？

通常是 Broker 没有正常运行，或者权限不足。  
建议先执行：

```bash
bash start_broker.sh
```

### Q3：为什么 Smart Copilot 标题栏状态点是红色？

这表示 Agent 服务探活失败。建议执行：

```bash
python3 asu_custom_agent.py
```

### Q4：Studio 为什么看起来还有一些占位内容？

因为当前 v5 Studio 只完成了主窗口骨架、快速创建和部分后端能力，高级交互仍在继续完善。

### Q5：Workspace 为什么有些面板功能不完整？

这是当前版本的真实状态。Workspace 已完成结构和入口整合，但 Task / Chat / Files / Memory 的完整业务逻辑还在持续接入。
