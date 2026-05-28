# OpenCopilot 定制智能体 (Custom Agent) 开发与使用指南

> **文档状态**: V2.1
> **更新日期**: 2026-05-28
> **状态**: P0-P2 阶段（主动感知、多模态、无感划词、Persona 工作坊）已全面完成

## 1. 什么是 OpenCopilot 定制智能体？

在 OpenCopilot 项目的早期版本中，我们依赖外部的 `OpenClaw CLI` 作为后端 LLM 服务。为了追求更高的可控性、更低的资源占用以及对 MiniMax 模型 API 的深度定制，我们开发了内置的 **ASU Custom Agent** (`asu_custom_agent.py`)。

它是 OpenCopilot 项目的**核心"AI 大脑"**，负责管理所有的 LLM 会话、角色切换 (Persona)、上下文记忆以及与远端 API（目前支持 MiniMax 和本地 OpenAI-compatible Provider）的通信。

---

## 2. 架构与生命周期

*   **运行机制**：Agent 作为**独立的 OS 级守护进程**运行（通过 macOS LaunchAgent 开机自启），与 UI 生命周期完全解耦。UI 启动时仅通过 `AgentHealthWorker` 异步探活 `127.0.0.1:18888/health`，不启动也不终止 Agent 进程。
    *   一键安装：`bash scripts/install_daemon.sh`
    *   手动运行：`python asu_custom_agent.py`
*   **通信协议**：标准 HTTP REST 风格接口，基于 Python 标准库 `HTTPServer`，对外提供本地回环 HTTP 服务与 SSE 流式响应。
*   **配置读取**：Agent 启动时读取项目根目录下的 `config.json` 与环境变量，按 `provider_type` 选择 MiniMax 或本地 OpenAI-compatible Provider。

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
    *   `custom`：自定义指令修改，严格按用户指令输出修改后文本（不输出解释）。
    *   `revision`：文档全文联动修订，输出修订后文本 + 联动影响分析 + 修订说明。
    *   *留空*：默认的通用全能助手。

---

## 4. 记忆机制与多轮对话

Agent 基于 **SQLite 本地持久化**（`asu_agent.db`）管理会话记忆，包含 `sessions`、`messages`、`tasks`、`personas` 四张表。

1.  **如何开启记忆**：客户端在 POST `/v1/agent/chat` 时携带非空的 `session_id`（例如 `ASU_IDE_Session`），Agent 自动将对话追加到该会话历史。
2.  **如何切断记忆**：传递新的 `session_id` 或将 `is_new_task` 设为 `true`，Agent 清空该会话旧上下文并开启新任务。
3.  **上下文窗口管理**：内置 `ContextWindowManager`，基于字符预算驱动（默认 ~30K token 输入窗口），按来源（IDE/Browser/其他）差异化裁剪，旧消息自动截断，防止 Token 超限和成本浪费。（39/39 测试通过）

---

## 5. 如何开发与调试智能体？

如果您想优化 AI 的回答质量或增加新的技能：

1.  **修改 Persona (角色设定)**：
    Persona 已实现**文件化管理**，存放在 `personas/` 目录下（如 `personas/code.md`、`personas/translate.md`、`personas/custom.md`、`personas/revision.md`）。直接编辑对应的 Markdown 文件即可，Agent 下次请求时自动热加载，无需修改源码。
2.  **对接新的大模型 API**：
    当前 Agent 通过 `llm_provider.py` 中的 `MiniMaxProvider` 与 `LocalProvider` 访问模型。在 `asu_custom_agent.py` 的 `get_base_llm()` 中配置 `provider_type`。未来需要接入更多模型时，建议继续扩展 Provider 层。
3.  **独立测试**：
    可以不启动 OpenCopilot 的 GUI，直接在终端中运行：
    ```bash
    python asu_custom_agent.py
    ```
    然后通过 `curl` 或 Postman 直接请求 `http://127.0.0.1:18888/v1/agent/chat` 进行 API 级别的联调测试。

---

## 6. 当前开发状态与方向

已完成（✅）：
- SQLite 持久记忆 + 会话恢复
- 上下文窗口管理（预算驱动裁剪，69% 平均压缩率）
- Persona 文件化 + 角色工坊 (Persona Workshop) 动态热加载
- ContextEnvelope 协议兼容层
- UI/Agent 生命周期解耦 + LaunchAgent 常驻
- 自定义指令修改（custom Persona + custom_instruction 传递）
- IDE 选区读取 + 回写（/selection + /apply 端点）
- 多模态视觉感知支持 (image_base64 透传)
- 基于 WebSocket 的主动状态推送与托盘联动

待推进（🔶）：
- IDE Extension v2：补充 `/diagnostics`、`/git-diff` 端点
- 多 Provider 故障转移
- SSE 错误边界优化

详细路线图见 [OpenCopilot 本地专属智能体现状与开发路线建议](OpenCopilot_Local_Agent_Roadmap.md)。
