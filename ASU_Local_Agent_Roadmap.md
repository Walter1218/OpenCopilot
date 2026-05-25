# ASU 本地专属智能体现状与开发路线建议

> **文档状态**: V1.0  
> **更新日期**: 2026-05-24  
> **目标**: 将 ASU 当前“本地专属智能体”能力、短板与后续开发方向沉淀为可执行路线图。

---

## 1. 总体判断

ASU 当前已经从“悬浮 AI 卡片原型”演进到“桌面级本地上下文感知 Agent 原型”。核心链路已经打通：

```text
用户交互层 smart_copilot.py
  -> 本地 Agent Client llm_provider.py
  -> ASU Custom Agent asu_custom_agent.py
  -> MiniMax / Local OpenAI-compatible Provider

系统上下文层：
  IDE Extension asu-ide-extension/
  Privileged Broker asu_broker/
  Drag & Drop fallback
```

当前状态可以概括为：

- **可用性**：已经具备实际使用价值。
- **架构方向**：Agent / Broker / IDE Extension / Context 四层拆分是正确的。
- **产品成熟度**：仍处于可用原型阶段，尚未完成稳定化、持久化和产品化。
- **下一阶段重点**：不宜继续优先堆 UI，而应优先打磨 Agent Core、上下文协议、Broker 常驻能力和 IDE 深度上下文。

---

## 2. 当前已具备能力

### 2.1 本地专属智能体 `asu_custom_agent.py`

当前 Agent 已经承担本地 AI 中枢职责：

- 监听 `127.0.0.1:18888`。
- 提供 `GET /health` 健康检查。
- 提供 `POST /v1/agent/chat` 对话接口。
- 支持 SSE 流式输出。
- 支持基于 `session_id` 的内存会话。
- 支持多 Persona：
  - `translate`
  - `code`
  - `polish`
  - `default`
- 支持上下文来源注入：
  - `ide`
  - `browser`
  - `drag`
  - `chat`
- 支持工作台任务 `task` 注入到 system prompt。
- 可根据 `config.json` 切换 MiniMax 或本地 OpenAI-compatible 服务。

### 2.2 主程序 `smart_copilot.py`

主程序已形成完整桌面交互闭环：

- 双击右键唤出快捷悬浮卡片。
- 三击右键唤出 Agent Workspace。
- 支持拖拽文本投喂。
- 支持 IDE 全文读取。
- 支持通过 Broker 读取浏览器 DOM。
- 支持 Markdown 渲染与代码高亮。
- 支持卡片拖拽缩放。
- 支持多屏边界适配。
- 启动时自动探活并拉起本地 Agent。

### 2.3 IDE Extension `asu-ide-extension/`

当前插件已经解决 Electron IDE 文本缓冲区难以被外部读取的问题：

- 插件在 IDE 内部读取当前文件全文。
- 动态监听 `127.0.0.1:<random-port>`。
- 将端口写入 `$TMPDIR/asu_ide_port.txt`。
- ASU 主程序读取端口后调用 `/context` 获取：
  - `fileName`
  - `languageId`
  - `content`

这是 ASU 获取代码上下文的关键基础设施。

### 2.4 Privileged Broker `asu_broker/`

Broker 已从架构草案进入可运行实现阶段：

- 监听 `127.0.0.1:18889`。
- 基于 Bearer Token 鉴权。
- Token 文件：`~/.asu_broker_token`。
- 已暴露能力包括：
  - `GET /health`
  - `GET /api/v1/system/frontmost`
  - `GET /api/v1/system/clipboard`
  - `POST /api/v1/system/clipboard`
  - `GET /api/v1/system/selection`
  - `POST /api/v1/apps/notes`
  - `GET /api/v1/system/screen/front`
  - `POST /api/v1/system/fs/read`
  - `GET /api/v1/browser/tabs`
  - `POST /api/v1/browser/dom`

Broker 是 ASU 解决 macOS TCC 沙盒限制、实现系统级探针能力的关键模块。

---

## 3. 当前主要短板

### 3.1 Agent 仍偏“LLM Gateway”，还不是完整 Agent Runtime

当前 `asu_custom_agent.py` 的核心能力是：

```text
上下文拼接 + Persona 选择 + 内存会话 + LLM 转发
```

这已经足够支撑“专属划词助手”，但还缺少更完整的 Agent Runtime 能力：

- 持久记忆。
- 上下文窗口治理。
- 工具调用编排。
- 多 Provider 故障转移。
- 任务状态管理。
- Persona 热加载与 GUI 管理。
- 本地知识库或项目索引。

### 3.2 会话记忆仅存在内存中

当前 `ASUAgentMemory` 使用进程内字典保存历史。Agent 或 ASU 重启后，对话历史、工作台任务背景都会丢失。

这会影响三击右键工作台的长期任务价值：工作台天然应该承载“持续任务上下文”，而不是一次性聊天窗口。

### 3.3 缺少上下文窗口管理

IDE 全文、网页正文、拖拽文本和多轮历史可能直接进入模型。随着上下文变长，会出现：

- token 超限。
- 响应变慢。
- 调用成本升高。
- 模型注意力稀释。
- 历史消息无限增长。

下一阶段必须引入上下文裁剪、摘要和分层上下文策略。

### 3.4 Broker 产品化程度不足

Broker 方向正确，但还处于“接口已具备、常驻和体验未完成”的阶段：

- WebSocket 主动事件推送尚未落地。
- LaunchAgent 常驻部署尚未完成。
- 权限引导仍偏手动。
- 调试时会打印 Token，产品化阶段应隐藏。
- 多个 probe 虽已暴露，但主程序和 Agent 利用程度还较浅。

### 3.5 IDE Extension 上下文粒度还不够

当前插件主要提供当前文件全文。对代码智能体而言，还需要更多开发现场信息：

- 当前选区。
- 当前函数/类。
- 当前文件 diagnostics。
- 当前 Git diff。
- 工作区文件树。
- 最近打开文件。
- 当前光标附近上下文。

---

## 4. 关键开发方向

## 4.1 Agent Core v2：稳定化与可扩展化

目标：让 `asu_custom_agent.py` 从轻量代理升级为稳定 Agent Core。

### 建议任务

1. **统一 API 协议**
   - 明确保留 `POST /v1/agent/chat` 作为主接口。
   - 可兼容旧文档中的 `/api/chat`，但不建议再新增旧路径能力。
   - 新增：
     - `POST /v1/agent/session/clear`
     - `GET /v1/agent/sessions`
     - `GET /v1/agent/personas`
     - `POST /v1/agent/personas/reload`

2. **[已完成] 引入 SQLite 会话持久化**
   - 建议表：
     - `sessions`
     - `messages`
     - `tasks`
     - `personas`
   - 目标：ASU 重启后仍可恢复工作台任务和历史摘要。

3. **实现上下文窗口管理**
   - 最近若干轮完整保留。
   - 旧消息自动摘要。
   - 大文本输入先结构化裁剪。
   - IDE 文件优先提取语言、文件名、函数/类、选区、diff，而不是永远发送全文。

4. **[已完成] Persona 文件化**
   - 推荐目录：

```text
personas/
├── default.md
├── code.md
├── translate.md
├── polish.md
├── browser_research.md
└── code_review.md
```

   - 后续由 GUI 管理 Persona，而不是修改 Python 源码。

5. **SSE 错误边界优化**
   - 保证异常也返回合法 SSE。
   - 流结束必须安全发送 `[DONE]` 或明确错误事件。
   - 避免长异常栈破坏前端 JSON 解析。

---

## 4.2 ContextEnvelope：统一上下文协议

当前上下文参数分散在 UI、Agent、Broker、Extension 之间。建议定义统一上下文信封：

```json
{
  "source": "ide",
  "app": "Trae",
  "title": "smart_copilot.py",
  "language": "python",
  "content": "...",
  "selection": "...",
  "task": "正在审查 Broker 稳定性",
  "metadata": {},
  "timestamp": 1716480000.123
}
```

### 目标

- IDE、Browser、Drag、Broker、Workspace 都转换为统一结构。
- Agent 只处理标准上下文包，不直接理解各类零散参数。
- 后续可基于 `source` 自动选择 Persona、裁剪策略和回答格式。

### 建议上下文字段

| 字段 | 说明 |
|------|------|
| `source` | `ide` / `browser` / `drag` / `chat` / `screen` / `file` |
| `app` | 来源应用，如 Trae、Chrome、Safari |
| `title` | 文件名、网页标题、窗口标题 |
| `language` | 编程语言，可选 |
| `content` | 主要文本内容 |
| `selection` | 用户选区，可选 |
| `task` | 工作台任务，可选 |
| `metadata` | 扩展元信息 |
| `timestamp` | 上下文采集时间 |

---

## 4.3 IDE Extension v2：从“全文读取”升级为“开发现场读取”

目标：让 ASU 在代码场景下拥有比普通划词工具更强的上下文优势。

### 建议新增接口

| 接口 | 作用 |
|------|------|
| `GET /context` | 当前文件全文，保留现有能力 |
| `GET /selection` | 当前选区内容 |
| `GET /workspace` | 工作区根路径和文件树摘要 |
| `GET /diagnostics` | 当前文件错误和警告 |
| `GET /git-diff` | 当前工作区未提交变更 |
| `GET /symbol` | 当前光标附近函数/类范围 |

### 建议优先级

1. `/selection`
2. `/diagnostics`
3. `/git-diff`
4. `/symbol`
5. `/workspace`

这些能力会让 `code` Persona 不只是“解释文件”，而能参与真实开发任务：代码审查、Bug 定位、重构建议、变更总结。

---

## 4.4 Broker v2：系统级探针产品化

目标：让 Broker 成为稳定、可诊断、可常驻的系统探针层。

### 短期任务

- 隐藏启动日志中的明文 Token。
- 增加 `GET /api/v1/system/capabilities`。
- 所有接口统一错误结构：

```json
{
  "status": "error",
  "message": "...",
  "code": "BROKER_TIMEOUT"
}
```

- 所有 AppleScript / 截图 / 文件读取类操作增加 timeout。
- 主程序中展示 Broker 未启动、Token 无效、权限不足的区别提示。

### 中期任务

- 实现 `ws://127.0.0.1:18889/ws/events`。
- 通过 `NSWorkspace` 监听前台 App 切换。
- 主动推送：
  - `app_activated`
  - `browser_tab_changed`
  - `permission_required`
  - `probe_error`

### 长期任务

- 提供 LaunchAgent 安装脚本。
- 打包为独立 `.app`，拥有稳定 Bundle ID。
- 提供权限诊断面板。
- 支持一键重启 Broker。
- 支持平滑关闭接口 `/api/v1/system/shutdown`。

---

## 4.5 Agent Workspace：从聊天窗口升级为任务中枢

当前三击右键工作台已经具备任务设定和独立对话能力。下一阶段建议将其升级为“长期任务控制台”。

### 建议能力

1. **任务持久化**
   - 当前任务重启后仍恢复。
   - 快捷卡片明确显示当前注入任务。

2. **任务下挂上下文**
   - 已读取的 IDE 文件。
   - 已读取的网页。
   - 用户拖入的资料。
   - 最近问答摘要。

3. **任务模板**
   - 代码审查。
   - Bug 定位。
   - 文档总结。
   - 翻译润色。
   - 架构分析。
   - 浏览器资料研究。

4. **上下文列表 UI**
   - 用户能看到当前任务到底注入了哪些上下文。
   - 支持移除、归档、清空。

---

## 5. 推荐实施路线图

| 阶段 | 目标 | 核心产出 |
|------|------|----------|
| 阶段 1 | Agent 稳定化 | API 统一、SQLite 记忆、上下文窗口、Persona 文件化 |
| 阶段 2 | 上下文系统升级 | `ContextEnvelope`、IDE 选区/诊断/diff、Browser URL/title/正文抽取 |
| 阶段 3 | Broker 产品化 | WebSocket 事件、LaunchAgent、权限诊断、统一错误结构 |
| 阶段 4 | 工作台产品化 | 任务持久化、任务模板、上下文列表、长期任务记忆 |
| 阶段 5 | 工程化收敛 | 日志、测试、配置安全、旧 OpenClaw 逻辑清理 |

---

## 6. 近期最建议优先做的 3 件事

### 1. Agent Core v2

优先实现：

- [x] SQLite 持久记忆。
- [ ] 上下文窗口裁剪。
- [x] Persona 文件化。
- [ ] `/v1/agent/session/*` 管理接口。

这是“本地专属智能体”能否长期可用的基础。

### 2. IDE Extension v2

优先实现：

- `/selection`
- `/diagnostics`
- `/git-diff`

这是让 ASU 在代码场景下真正有差异化的关键。

### 3. Broker v2

优先实现：

- `capabilities` 接口。
- 统一错误结构。
- WebSocket 前台应用切换事件。
- LaunchAgent 常驻方案。

这是 ASU 成为桌面级 Copilot 的系统能力底座。

---

## 7. 总结

ASU 当前最核心的价值不只是“右键唤出 AI 卡片”，而是已经形成了一个非常有潜力的四层架构：

```text
交互层：smart_copilot.py
智能体层：asu_custom_agent.py
上下文层：asu-ide-extension/ + asu_broker/
模型层：MiniMax / Local OpenAI-compatible Provider
```

下一阶段的关键目标是：

> 把“能跑的本地智能体”升级为“可持续、可扩展、可恢复、深度上下文感知的桌面 Agent Runtime”。

建议近期所有开发都围绕这个目标收敛，少做一次性 UI 功能，多做长期稳定的 Agent 基础设施。
