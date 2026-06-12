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

打开"系统设置 -> 隐私与安全性"，为你使用的终端程序授予：

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

如果你主要使用桌面端 v5 交互，建议至少启动下面 2 个部分：

```bash
# 终端 1：Broker（必须在原生终端中运行）
bash start_broker.sh

# 终端 2：UI
bash scripts/start_ui.sh
```

如果你还需要稳定抓 API 日志、联调 `/vnext/*` 或查看 API 文档，再额外启动：

```bash
python3 -m uvicorn smart_copilot_api:app --host 127.0.0.1 --port 8010 --reload
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
| `Studio` | PPT 共创入口 | 已可用，核心编辑链路已落地 |

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

`Studio` 是 PPT 共创入口，不再建议理解成旧版的单个"PPT 按钮"。

当前你可以：

- 粘贴文本或输入主题
- 点击"快速创建"
- 让 AI 先生成基础 PPT 结构
- 打开独立 `StudioWindowV5`

需要注意：

- 当前 Studio **已完整实现**：支持从文本生成大纲、缩略图导航、可视化差异预览编辑、底部 AI 聊天交互修改以及完整的撤销链路。
- 它是 OpenCopilot 提供的深度内容创作环境，可以与日常使用的 PowerPoint 无缝配合。
- 快速创建只会在输入极短时才尝试剪贴板兜底，避免把你明确输入的主题替换成历史日志或无关内容。

## 4.2 Workspace：三击右键

三击鼠标右键会打开更大的 `Workspace` 窗口。

当前 v5 Workspace 采用 Sidebar + 5 Panel 结构：

| 面板 | 用途 | 当前状态 |
|------|------|----------|
| `Task` | 任务定义与管理 | 已可用 |
| `Chat` | 多会话对话 | 已可用 |
| `Files` | 最近文件列表 | 已可用 |
| `Memory` | 知识图谱/翻译记忆/术语库统计 | 已可用 |
| `Settings` | 设置入口 | 已可用 |

要点说明：

- Workspace 的窗口壳和切换结构已经落地
- 所有面板均已实现具体业务功能
- Task 面板支持任务定义与管理
- Chat 面板支持多会话切换与持久化
- Files 面板显示最近文件列表
- Memory 面板显示知识图谱、翻译记忆、术语库统计信息

当前 Workspace 已成为 **深度任务的工作台**，所有功能均已成熟。

## 4.3 统一设置

当前推荐使用 v5 的统一设置窗口。

入口包括：

- Smart Copilot 标题栏的设置按钮
- Workspace 内的设置入口

当前设置分区：

| 分区 | 用途 |
|------|------|
| `Engine` | 云端/本地模型配置、连接测试、`Agent Runtime` 路由配置 |
| `Appearance` | 主题、字体等外观配置 |
| `Shortcuts` | 快捷键设置 |
| `Advanced` | 高级配置、导入导出 |

`Engine` 中当前已支持：

- 默认后端：`Third-Party Agent` / `Self Agent`
- 默认 Provider / Model
- `chat / explain / coding / ppt / translate` 的 capability 路由
- `On Timeout / On Protocol Error` 的 fallback policy

如果你要在 UI 中启用第三方智能体，推荐按下面顺序操作：

1. 打开 `Settings -> Engine`
2. 将 `Agent Mode` 切到 `Third-Party Agent`
3. 在 `Agent Provider` 中选择当前内置 preset
4. 需要时设置 `Agent Model`
5. 用 `Capability Routes` 决定哪些能力继续走默认路由，哪些能力单独指定到第三方
6. 用 `Fallback Policy` 决定第三方超时或协议异常时是否自动回退

当前需要注意：

- UI 已支持第三方智能体模式这个统一入口
- 当前内置的第三方 provider preset 以 `Hermes Local` 为主
- 如果你要接入新的第三方 provider，除了模型连接信息，还需要研发侧补 provider adapter 和 UI preset

---

## 五、上下文与数据来源

OpenCopilot 的价值不只是"发一个 prompt"，而是尽量理解你当前正在看的内容。

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

- 更完整的技能整合、命令面板和上下文推荐
- 宿主真回写与整机人工验收

---

## 七、常用命令

| 操作 | 命令 |
|------|------|
| 启动 UI | `bash scripts/start_ui.sh` |
| 启动 Broker | `bash start_broker.sh` |
| 启动 vnext API | `python3 -m uvicorn smart_copilot_api:app --host 127.0.0.1 --port 8010 --reload` |
| 检查 API Gateway | `curl http://127.0.0.1:8000/health` |
| 检查 vnext API | `curl http://127.0.0.1:8010/health` |
| 检查 Broker | `curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health` |

---

## 八、状态提示

当前 UI 标题栏中的状态点主要反映当前运行时链路探活结果。

| 状态 | 含义 |
|------|------|
| 绿色 | 当前 `vnext/Hermes` 或运行时链路可达，服务态较正常 |
| 红色 | 当前运行时探活失败，部分 AI 链路可能不可用或退化 |

需要注意：

- 某些桌面 AI 调用会根据 `agent_runtime` 切到 `self_agent`
- 默认主链路仍建议保证 `vnext/Hermes` 可用

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

这表示当前运行时探活失败。建议先检查：

```bash
curl http://127.0.0.1:8010/health
```

如果 `8010` 不可用，再按 [STARTUP_GUIDE](file:///Users/onetwo/Documents/trae_projects/OpenCopilot/docs/STARTUP_GUIDE.md) 检查 `8000` 回退链路和 Hermes 服务状态。



### Q5：Workspace 面板功能如何？

Workspace 已实现完整业务逻辑。Task 面板支持任务定义与管理，Chat 面板支持多会话对话，Files 面板显示最近文件列表，Memory 面板显示知识图谱/翻译记忆/术语库统计信息。
