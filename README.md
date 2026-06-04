# OpenCopilot 🚀

> **macOS 系统级 AI Copilot** | 版本 v4.0 | 2026-06-04
>
> OpenClaw 单进程架构 · Agent Loop 混合范式 · Pipeline 管线 · 声明式 Skill 系统

OpenCopilot 是一个 macOS 桌面级 AI 助手，通过**鼠标右键**在任何软件中唤出悬浮卡片，实现不打断心流的 AI 交互。

---

## 架构一览

```
┌─────────────────────────────────────────────────────┐
│                  PyQt6 UI (smart_copilot.py)         │
│              悬浮卡片 · 任务工作台 · 光标特效           │
└──────────────────────┬──────────────────────────────┘
                       │ opencopilot/agent/caller.py
                       ▼
┌─────────────────────────────────────────────────────┐
│         API Gateway (smart_copilot_api.py :8000)     │
│  ┌───────────────────────────────────────────────┐  │
│  │           7 层异步 Pipeline                     │  │
│  │  SessionSetup → SecurityGuard → ImmuneSystem   │  │
│  │  → Planner → StateTracking → CapabilityRouter  │  │
│  │  → LLMProviderMiddleware                       │  │
│  │                                                │  │
│  │  ┌──────────────────────────────────────┐     │  │
│  │  │  Agent Loop: 复杂度判断 → 动态范式     │     │  │
│  │  │  · SIMPLE  → One-Shot (~2s)          │     │  │
│  │  │  · MEDIUM  → Plan-and-Solve (~10s)   │     │  │
│  │  │  · COMPLEX → Plan+ReAct (~20s)       │     │  │
│  │  └──────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  Broker  │ │ 知识图谱  │ │  Skills  │
   │ :18889   │ │  :8090   │ │  SKILL.md│
   └──────────┘ └──────────┘ └──────────┘
```

**核心端口**:

| 服务 | 端口 | 说明 |
|------|------|------|
| API Gateway | 8000 | FastAPI + 内嵌 Agent Pipeline + 能力平台（统一入口） |
| Broker | 18889 | 特权代理（系统探针、无感划词、沙盒穿透） |
| 知识图谱 | 8090 | 项目知识查询（可选） |

---

## 快速开始

### 1. 环境准备

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -r requirements.txt
```

> Python 3.11~3.13，macOS 需授予**辅助功能**和**屏幕录制**权限。

### 2. 启动后台服务（开发模式）

```bash
# 1. 启动 API Gateway（自动带起知识图谱 + 能力平台）
uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 2. 启动 Broker（需 macOS 原生终端，辅助功能权限）
python opencopilot/broker/run.py

# 3. 启动 UI
python smart_copilot.py
```

### 3. 守护进程模式（开机自启）

```bash
bash scripts/install_unified_daemon.sh   # Broker + 知识图谱
bash scripts/start_ui.sh                 # 启动 UI
```

---

## 核心功能

| 功能 | 操作 | 说明 |
|------|------|------|
| 快捷悬浮卡片 | 双击右键 | AI 分析选中文本 |
| 任务工作台 | 三击右键 | 设定任务背景 + 深度对话 |
| IDE 全文读取 | 安装插件 | 读取 IDE 全文 / 选区回写 |
| 浏览器读取 | Broker 探针 | 获取当前网页全文 |
| 视觉分析 | 👁️ 按钮 | 截图前台窗口多模态分析 |
| PPT 共创 | 拖拽文档 | AI 生成大纲 → 导出 PPTX |
| 角色工坊 | 🎭 按钮 | 自定义 Persona 专家角色 |
| 知识图谱 | :8090 | 项目知识结构化查询 |

---

## 项目结构 (v4.0 分层架构)

```
OpenCopilot/
├── opencopilot/                  # 主包 (pip install -e .)
│   ├── agent/                    #   Agent 核心 (Pipeline + Loop + Caller)
│   ├── capabilities/             #   能力层 (coding/knowledge/search/memory/skill/ppt/tools)
│   ├── safety/                   #   安全层 (security/immune/planner)
│   ├── providers/                #   LLM 提供者
│   ├── broker/                   #   系统代理
│   ├── observability/            #   可观测性
│   ├── config/                   #   配置管理
│   └── shared/                   #   共享工具
├── api/                          # API 网关 (端口 8000)
│   ├── app.py                    #   路由工厂
│   ├── models.py                 #   Pydantic 模型
│   └── routers/                  #   12 个独立路由模块
├── gui/                          # PyQt6 桌面应用
│   ├── main.py                   #   入口 + CopilotManager
│   ├── window.py                 #   AICardWindow 核心窗口
│   ├── workspace.py              #   AgentWorkspace 工作台
│   ├── shared.py                 #   共享工具
│   ├── workers/                  #   7 个 QThread Worker
│   └── dialogs/                  #   对话框组件
├── personas/                     # Persona 角色文件
├── skills/                       # Skill 声明文件
├── asu-ide-extension/            # IDE 伴生插件
├── tests/                        # 测试 (166 用例, 3 层: unit/e2e/ablation)
├── quality_check.py               # 质量评估体系(代码正确性)
├── output_quality.py              # 输出质量评估(内容评分)
├── smart_copilot.py              # GUI 兼容入口 → gui/main.py
├── smart_copilot_api.py          # API 兼容入口 → api/app.py
├── pyproject.toml                # 项目配置
└── requirements.txt              # 依赖清单

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构设计（Pipeline、Agent Loop、Skill 系统） |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南（环境搭建、模块开发、测试、路线图） |
| [USER_GUIDE.md](USER_GUIDE.md) | 用户使用手册 |

---

## 开发路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0 | 基础交互、多引擎 AI、上下文感知 Agent | ✅ |
| P1 | 特权 Broker、多模态视觉、无感划词 | ✅ |
| P2 | Persona 工坊、PPT 共创、知识图谱、Skill 架构 | ✅ |
| P3 | Agent Loop 重构、OpenClaw 单进程迁移、Pipeline 统一 | ✅ |
| P4 | v4.0 分层架构重构、代码治理、质量提升 | ✅ |
| P5 | IDE Extension v2、Broker 产品化 | 🔶 |
| P6 | 上下文主动感知、多 Agent 协作 | 📋 |
