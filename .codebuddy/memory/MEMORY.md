# ASU 项目长期记忆

## 项目概述
- ASU (Advanced System Utilities)：macOS 桌面级 AI Copilot
- 核心技术：Python PyQt6 + pynput + httpx，双图层架构
- AI 后端：MiniMax 云端 + Ollama/vLLM 本地，通过 18888 端口 Agent Server 统一管理
- IDE 插件：VS Code Extension (Node.js)，动态端口 + 临时文件信标通信

## 项目约定
- 运行环境：Python 3.10/3.11 虚拟环境，严禁使用 3.13+
- 启动方式：`./venv/bin/python smart_copilot.py`
- Git 分支：`ai-assistant`
- 敏感文件（.env、config.json、venv/、build/、dist/）已在 .gitignore 中排除
- 备份目录：`/Users/onetwo/Documents/trae_projects/ASU_backup/`

## 架构关键设计
- 双图层解耦：CursorOverlay（全屏穿透特效层）+ AICardWindow（局部可交互卡片层）
- 拖拽方案替代了自动 Cmd+C，彻底解决 macOS 沙盒焦点丢失问题
- Agent Server 通过 session_id 管理多轮对话记忆和人格设定
- IDE 插件通过 `$TMPDIR/asu_ide_port.txt` 动态发布端口

## 待办事项
- 实现 AXAPI 原生文档（Pages/Notes）探针（架构方案阶段三）
- 将 Privileged Broker 从 PoC 集成到主代码
- Broker 守护进程化（launchd LaunchAgent）
