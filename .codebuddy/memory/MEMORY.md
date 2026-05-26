# ASU 项目长期记忆

## 项目概述
- ASU (Advanced System Utilities)：macOS 桌面级 AI Copilot
- 核心技术：Python PyQt6 + pynput + httpx，双图层架构
- AI 后端：MiniMax 云端 + Ollama/vLLM 本地，通过 18888 端口 Agent Server 统一管理
- IDE 插件：VS Code Extension (Node.js)，动态端口 + 临时文件信标通信

## 关键文档
- `README.md`：项目概览与开发路线图
- `USER_GUIDE.md`：产品用户说明书（安装/功能/排错）
- `OpenCopilot_Custom_Agent_Guide.md`：Agent 开发指南
- `OpenCopilot_Broker_Development_Guide.md`：Broker 开发指南
- `test_docs/TEST_REPORT.md`：文档修订功能验证报告
- AI 后端：MiniMax 云端 + Ollama/vLLM 本地，通过 18888 端口 Agent Server 统一管理
- IDE 插件：VS Code Extension (Node.js)，动态端口 + 临时文件信标通信

## 当前分支
- `ai-assistant-dev-sp`：Broker 产品化 + IDE Extension v2 开发分支

## 项目约定
- 运行环境：Python 3.10/3.11 虚拟环境，严禁使用 3.13+
- 启动方式：`./venv/bin/python smart_copilot.py`
- 敏感文件（.env、config.json、venv/、build/、dist/）已在 .gitignore 中排除
- 备份目录：`/Users/onetwo/Documents/trae_projects/ASU_backup/`

## 架构关键设计
- 四层架构：交互层(smart_copilot.py) → 智能体层(asu_custom_agent.py) → 上下文层(IDE Extension + Broker) → 模型层(MiniMax/Local)
- 双图层解耦：CursorOverlay（全屏穿透特效层）+ AICardWindow（局部可交互卡片层）
- 拖拽方案替代了自动 Cmd+C，彻底解决 macOS 沙盒焦点丢失问题
- Agent Server 通过 session_id 管理多轮对话记忆和人格设定
- IDE 插件通过 `$TMPDIR/asu_ide_port.txt` 动态发布端口
- Broker（端口 18889）解决 TCC 沙盒穿透，已集成到主程序

## 已完成（Broker 产品化 + 文档修订，2026-05-26）
- Broker LaunchAgent 常驻部署：`deploy/com.asu.broker.plist` + `scripts/install_broker_daemon.sh`
- Broker `/api/v1/system/capabilities` 能力发现端点
- Broker `/api/v1/system/shutdown` 优雅关闭端点
- Broker Office 解析探针：`POST /api/v1/system/fs/office/read`（支持 .docx/.pptx）
- 统一错误格式：所有异常返回 `{"status":"error","code":"...","message":"..."}`
- Token 日志脱敏：启动日志只显示首尾 8 位
- 所有探针路由增加 `asyncio.wait_for` 超时保护
- 请求日志中间件：记录方法/路径/状态/耗时
- **文档全文联动修订功能**：新增 `personas/revision.md` persona，UI 端 `📝 全文修订` 按钮，支持拖拽选中文本 + IDE/Broker 全文上下文，AI 输出三区块（修订文本 + 联动影响标记 + 修订说明），通过 10 个真实案例验证（含 .md/.docx/.pptx）

## 待办事项
- 实现 AXAPI 原生文档（Pages/Notes）探针（架构方案阶段三）
- IDE Extension v2：补充 /selection、/diagnostics、/git-diff 端点
- Broker WebSocket 主动推送（前台应用切换事件）
- 多 Provider 故障转移（ProviderFactory 当前硬编码 ASUCustomAgentClient）
