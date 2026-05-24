# ASU 定制智能体 (Custom Agent) 开发与使用指南

> **文档状态**: V1.0
> **更新日期**: 2026-05-24

## 1. 什么是 ASU 定制智能体？

在 ASU 项目的早期版本中，我们依赖外部的 `OpenClaw CLI` 作为后端 LLM 服务。为了追求更高的可控性、更低的资源占用以及对 MiniMax 模型 API 的深度定制，我们开发了内置的 **ASU Custom Agent** (`asu_custom_agent.py`)。

它是 ASU 项目的**核心“AI 大脑”**，负责管理所有的 LLM 会话、角色切换 (Persona)、上下文记忆以及与远端 API（目前独家锚定 MiniMax-M2.7）的通信。

---

## 2. 架构与生命周期

*   **运行机制**：在主程序 `smart_copilot.py` 启动时，会自动探活本地的 `18888` 端口。如果发现 Agent 未启动，主程序会作为一个守护子进程静默拉起它。
*   **通信协议**：标准的 HTTP REST API (基于 FastAPI 搭建)。
*   **配置读取**：Agent 启动时会读取项目根目录下的 `.env` 文件，获取用户的 `MINIMAX_API_KEY` 和 `MINIMAX_GROUP_ID`。

---

## 3. 核心 API 接口说明

客户端 (如 UI 层) 主要通过向 `http://127.0.0.1:18888` 发送 HTTP 请求来与 Agent 交互。

### 3.1 探活接口
*   **GET `/health`**
*   **用途**：检查智能体是否已成功启动并就绪。

### 3.2 对话接口 (流式/非流式)
*   **POST `/api/chat`**
*   **用途**：向智能体发送对话请求，支持上下文传递和 Persona 指定。
*   **请求体参数**：
    ```json
    {
      "messages": [
        {"role": "user", "content": "请解释一下这段代码..."}
      ],
      "stream": true,            // 是否开启流式返回
      "session_id": "ide_123",   // 用于维持多轮对话记忆的唯一 ID
      "action_type": "code"      // 指定场景 Persona (翻译/代码分析/通用等)
    }
    ```
*   **场景路由 (`action_type`)**：
    Agent 内部维护了多种场景前缀 (System Prompts)。通过传递不同的 `action_type`，Agent 会在拼接上下文时自动注入不同的指令：
    *   `translate`：强制输出极客风格的中文翻译。
    *   `code`：作为资深架构师，分析代码逻辑。
    *   `polish`：作为技术专栏编辑，润色文本。
    *   *留空*：默认的通用全能助手。

---

## 4. 记忆机制与多轮对话

Agent 内部维护了一个内存级别的会话池 (`sessions_memory`)。

1.  **如何开启记忆**：客户端只要在 POST `/api/chat` 时携带非空的 `session_id`（例如 `ASU_IDE_Session`），Agent 就会自动将本次对话追加到该 ID 对应的历史记录中。
2.  **如何切断记忆**：如果传递的是新的 `session_id`，或者不传该字段，Agent 会将其视为全新的独立对话。
3.  **当前局限与未来规划**：目前的记忆是保存在**内存**中的，这意味着如果 Agent 进程重启（或关闭了 ASU 主程序），对话历史会丢失。未来的路线图计划引入基于 SQLite 或 JSON 的本地持久化存储。

---

## 5. 如何开发与调试智能体？

如果您想优化 AI 的回答质量或增加新的技能：

1.  **修改 Persona (角色设定)**：
    打开 `asu_custom_agent.py`，找到文件开头的 `SYSTEM_PROMPTS` 字典。您可以直接修改或新增 Key-Value，然后在客户端调用时传入对应的 Key 作为 `action_type`。
2.  **对接新的大模型 API**：
    目前 Agent 在 `_call_minimax_api` 函数中硬编码了对 MiniMax `v1/chat/completions` 的调用逻辑。如果未来需要接入其他模型，可以重构该函数，引入策略模式。
3.  **独立测试**：
    您可以不启动 ASU 的 GUI，直接在终端中运行：
    ```bash
    source venv/bin/activate
    python asu_custom_agent.py
    ```
    然后通过 `curl` 或 Postman 直接请求 `http://127.0.0.1:18888/api/chat` 进行 API 级别的联调测试。
