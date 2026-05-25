# ASU 定制智能体 (Custom Agent) 开发与使用指南

> **文档状态**: V1.0
> **更新日期**: 2026-05-24

## 1. 什么是 ASU 定制智能体？

在 ASU 项目的早期版本中，我们依赖外部的 `OpenClaw CLI` 作为后端 LLM 服务。为了追求更高的可控性、更低的资源占用以及对 MiniMax 模型 API 的深度定制，我们开发了内置的 **ASU Custom Agent** (`asu_custom_agent.py`)。

它是 ASU 项目的**核心“AI 大脑”**，负责管理所有的 LLM 会话、角色切换 (Persona)、上下文记忆以及与远端 API（目前独家锚定 MiniMax-M2.7）的通信。

---

## 2. 架构与生命周期

*   **运行机制**：在主程序 `smart_copilot.py` 启动时，会自动探活本地的 `18888` 端口。如果发现 Agent 未启动，主程序会作为一个守护子进程静默拉起它。
*   **通信协议**：标准 HTTP REST 风格接口。目前实现基于 Python 标准库 `HTTPServer` + `BaseHTTPRequestHandler`，对外提供本地回环 HTTP 服务；后续如需更复杂的路由、鉴权和观测能力，可升级为 FastAPI。
*   **配置读取**：Agent 启动时会读取项目根目录下的 `config.json` 与环境变量，按配置选择 MiniMax 或本地 OpenAI-compatible Provider。

---

## 3. 核心 API 接口说明

客户端 (如 UI 层) 主要通过向 `http://127.0.0.1:18888` 发送 HTTP 请求来与 Agent 交互。

### 3.1 探活接口
*   **GET `/health`**
*   **用途**：检查智能体是否已成功启动并就绪。

### 3.2 对话接口 (SSE 流式)
*   **POST `/v1/agent/chat`**
*   **用途**：向智能体发送对话请求，支持上下文来源、任务背景和 Persona 指定。
*   **请求体参数**：
    ```json
    {
      "text": "请解释一下这段代码...",
      "session_id": "ide_123",
      "action_type": "code",
      "is_new_task": true,
      "context_source": "ide",
      "context_meta": {
        "file_name": "smart_copilot.py",
        "language": "python",
        "task": "审查 Broker 集成稳定性"
      }
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

1.  **如何开启记忆**：客户端只要在 POST `/v1/agent/chat` 时携带非空的 `session_id`（例如 `ASU_IDE_Session`），Agent 就会自动将本次对话追加到该 ID 对应的历史记录中。
2.  **如何切断记忆**：如果传递的是新的 `session_id`，或者将 `is_new_task` 设置为 `true`，Agent 会清空该会话下的旧上下文并开启新任务。
3.  **当前局限与未来规划**：目前的记忆是保存在**内存**中的，这意味着如果 Agent 进程重启（或关闭了 ASU 主程序），对话历史会丢失。未来路线图建议优先引入 SQLite 本地持久化。

---

## 5. 如何开发与调试智能体？

如果您想优化 AI 的回答质量或增加新的技能：

1.  **修改 Persona (角色设定)**：
    打开 `asu_custom_agent.py`，找到文件开头的 `personas` 字典。您可以直接修改或新增 Key-Value，然后在客户端调用时传入对应的 Key 作为 `action_type`。
2.  **对接新的大模型 API**：
    当前 Agent 通过 `llm_provider.py` 中的 `MiniMaxProvider` 与 `LocalProvider` 访问模型。未来需要接入更多模型时，建议继续扩展 Provider 层，而不是在 UI 层直接调用模型。
3.  **独立测试**：
    您可以不启动 ASU 的 GUI，直接在终端中运行：
    ```bash
    source venv/bin/activate
    python asu_custom_agent.py
    ```
    然后通过 `curl` 或 Postman 直接请求 `http://127.0.0.1:18888/v1/agent/chat` 进行 API 级别的联调测试。

---

## 6. 下一阶段开发方向

关于本地专属智能体的完整现状评估、短板和路线图，请参考：

- [ASU 本地专属智能体现状与开发路线建议](ASU_Local_Agent_Roadmap.md)

近期建议优先推进：

1. **Agent Core v2**：SQLite 持久记忆、上下文窗口管理、Persona 文件化、SSE 错误边界优化。
2. **ContextEnvelope**：统一 IDE、Browser、Drag、Workspace 等来源的上下文协议。
3. **IDE Extension v2**：补充选区、diagnostics、git diff、symbol 等开发现场信息。
4. **Broker v2**：补齐 capabilities、统一错误结构、WebSocket 事件推送与 LaunchAgent 常驻。
