# OpenCopilot 技术规格说明书

## 1. 产品定义

OpenCopilot（简称 OpenCopilot）是一款面向 macOS 平台的桌面级 AI 智能协驾工具。通过全局鼠标监听和悬浮卡片交互，实现跨应用的上下文感知和智能分析。

## 2. 核心模块

### 2.1 交互层 (smart_copilot.py)
采用 PyQt6 双图层架构，全屏穿透特效层负责光标视觉效果，局部可交互卡片层承载 AI 对话。支持双击右键唤出快捷卡片，三击右键唤出任务工作台。

### 2.2 智能体层 (asu_custom_agent.py)
运行于端口 18888 的独立 HTTP 服务，负责 LLM 会话管理、角色切换、上下文记忆和模型调度。目前支持 MiniMax 和本地 OpenAI-compatible 两种后端。

### 2.3 上下文层
- **IDE 插件 (asu-ide-extension/)**：基于 VS Code Extension API，通过 HTTP 暴露当前文件全文和选区
- **特权代理 (asu_broker/)**：运行于端口 18889，持有 macOS 系统高级权限，提供浏览器 DOM 提取、屏幕截图、剪贴板读写等探针能力

### 2.4 模型层 (llm_provider.py)
抽象 Provider 接口，支持 MiniMax M2.7（云端）和多款本地模型（Ollama/vLLM）的动态切换。

## 3. 通信架构

```
UI (PyQt6) ←→ Agent Server (127.0.0.1:18888) ←→ LLM Provider
    ↓                      ↓
 SystemProbeClient ←→ Broker (127.0.0.1:18889) → macOS System APIs
    ↓
 IDE Extension ←→ VS Code API
```

## 4. 性能要求

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| 卡片唤出延迟 | < 200ms | ✅ 150ms |
| AI 首字响应 | < 3s | ✅ 2.1s (MiniMax) |
| 内存占用 | < 500MB | ✅ 320MB |
| CPU 空闲占用 | < 2% | ✅ 1.2% |
| 上下文窗口 | 30K tokens | ✅ 已实现 |

## 5. 部署方案

推荐通过 macOS LaunchAgent 实现开机自启。Agent 和 Broker 分别注册为独立守护进程，UI 作为无状态客户端按需唤出。日志统一输出至 ~/Library/Logs/ASU/。
