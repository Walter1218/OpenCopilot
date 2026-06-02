# OpenCopilot (Advanced System Utilities) 🚀
**全局智能交互增强引擎 & 桌面级 AI Copilot**

> **版本**：v2.5 | **日期**：2026-06-02 | **状态**：智能体核心模块开发完成，知识检索模块封装，Broker权限诊断功能实现，集成测试和消融实验验证通过，文档全面更新

OpenCopilot 是一个致力于探索**下一代人机交互模式**的系统级工具集。它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM (大语言模型) 能力深度结合，旨在打造"不打断用户心流"的极致 AI 体验。

## ✨ 核心亮点 (Core Features)

1. **上下文感知专属智能体 (Context-Aware Agent)**
   后台定制智能体（`asu_custom_agent.py`, 端口 18888）不仅仅是 LLM 的代理层：
   - **场景自动感知**：根据文本来源（IDE 代码文件 / 浏览器网页 / 拖拽文本），自动注入对应的 system prompt 前缀，让 AI 从"通用问答"升级为"场景化分析"。
   - **多角色人格**：内置翻译官、架构师、编辑、通用助手、自定义修改五种 Persona，支持通过 `session_id` 实现多轮对话记忆。
   - **自定义指令修改**：拖拽文本后可输入修改指令，AI 严格按指令输出修改结果，支持一键回写到 IDE。
   - **健康检查**：提供 `GET /health` 端点，UI 启动时异步探活并在标题栏显示绿/红状态点。

2. **双引擎动态热切架构 (Dual-Engine Architecture)**
   在 UI 设置面板中一键切换后端驱动引擎：
   - ☁️ **云端 LLM (MiniMax)**：开箱即用，极速响应。
   - 💻 **本地/第三方 LLM (Ollama/vLLM)**：支持标准 OpenAI 协议的本地推理服务。
   *Agent 与 Broker 均作为独立 OS 级守护进程运行（LaunchAgent 开机自启），UI 启动时仅探活。*

3. **纯鼠标双击唤醒与悬浮拖拽投喂**
   - 任意软件中**双击鼠标右键**，即可在鼠标旁唤出智能悬浮卡片（快捷模式）。
   - **三击鼠标右键**唤出独立任务工作台，用于设定全局任务背景和独立深度对话。
   - 工作台设定的任务会自动注入到快捷卡片的 AI 请求中，实现"定义任务 → 划词执行"的聚焦工作流。

4. **双图层解耦与多屏边缘适配 (Layer Decoupling & Multi-Screen Adaptation)**
   - 采用**双图层架构**：全屏穿透图层负责绘制高刷光标特效（呼吸准星、拖尾轨迹、水波纹）；局部交互图层负责承载 AI 悬浮卡片。
   - 光标特效模块已提取为独立共享库 `cursor_effects.py`，避免代码重复。
   - **多显示器无缝跨越**：特效层自动联合所有外接屏幕进行跨屏渲染。
   - **智能边缘防遮挡与翻转**：实时识别鼠标所在屏幕，自动翻转 + 坐标钳位（Clamp）确保卡片永不越界。

5. **极低资源占用的系统级监听 (Low-Footprint System Hooks)**
   - 基于 `pynput` 与原生系统调用（如 macOS 的 `pbpaste`），极致轻量化。
   - 内置防抖与日志轮转机制（限制单文件 20MB），保障后台常驻稳定。

6. **基于 Privileged Broker 的极客级交互**
   - 彻底解决 macOS 的 TCC 沙盒限制与进程内调用 AppleScript 导致的 `-10004 权限违例` 崩溃。
   - 预埋系统级探针，支持静默获取浏览器 DOM、系统剪贴板读写、高亮选区提取、屏幕 OCR 截图、甚至突破 IDE 文件沙盒直接读取全局文件。

---

## 🆕 最新功能 (Latest Features)

### 1. 知识图谱系统 (2026-05-31)
- **功能**：从项目文档中自动提取核心知识，构建结构化知识库
- **规模**：264个实体，166个关系，覆盖5种实体类型
- **API**：27个RESTful API端点，100%功能覆盖率
- **启动**：`python start_broker_with_kg.py`（与Broker一起启动）
- **文档**：[Knowledge_Graph_Guide.md](Knowledge_Graph_Guide.md)

### 2. PPT共创模式 (2026-05-31)
- **功能**：AI辅助PPT创作，支持内容分析、智能建议、多轮对话、领域自适应
- **领域自适应**：AI自动识别内容领域（计算机/AI/商业/产品/教育/数据分析），采用对应专业结构模板
- **模块**：
  - 智能上下文感知：`ppt_cocreation/context_analyzer.py`
  - AI主动建议引擎：`ppt_cocreation/suggestion_engine.py`
  - 多轮对话管理器：`ppt_cocreation/conversation_manager.py`
  - PPT策划师角色：`personas/office/business/presentation.md`
- **API**：8个API端点，支持内容分析、建议生成、对话管理
- **测试**：38项单元测试 + 8项API集成测试，100%通过
- **文档**：[PPT_Assistant_User_Guide.md](PPT_Assistant_User_Guide.md)（使用手册）

### 3. 统一启动脚本 (2026-05-31)
- **功能**：一个命令启动Broker和知识图谱API
- **脚本**：`start_broker_with_kg.py`
- **优势**：简化操作、统一管理、灵活配置
- **使用**：`python start_broker_with_kg.py`

### 4. Smart Copilot API (2026-05-30)
- **功能**：提供统一的AI能力平台接口
- **端口**：8089
- **API**：
  - `POST /api/execute` - 统一动作执行
  - `GET /api/context/current` - 获取当前上下文
  - `WS /ws/events` - WebSocket事件订阅
- **文档**：[Smart_Copilot_API_Guide.md](Smart_Copilot_API_Guide.md)

### 5. Skill化架构 (2026-05-31)
- **功能**：模块化、可扩展的AI能力架构，支持7个Skill实现
- **核心组件**：
  - `skill_architecture/base.py` - BaseSkill抽象基类
  - `skill_architecture/registry.py` - SkillRegistry注册表
  - `skill_architecture/router.py` - IntentRouter意图路由器
  - `skill_architecture/executor.py` - SkillExecutor执行引擎
- **已实现Skill**：
  1. **KnowledgeSkill**：知识图谱查询与管理
  2. **CodingSkill**：代码生成、修复、审查
  3. **PPTSkill**：PPT创作与优化
  4. **EvaluationSkill**：内容质量评估
  5. **FileSkill**：文件操作与管理
  6. **FormatSkill**：格式转换与处理
  7. **PersonaSkill**：人格角色管理
- **API端点**：61个，100%功能覆盖率
- **测试验证**：18个测试全部通过，100%通过率
- **文档**：[Skill_Architecture_Design.md](Skill_Architecture_Design.md)

### 6. 智能体核心模块 (2026-06-01)
- **功能**：5个智能体核心模块，实现任务规划、代码执行、安全控制、可观测性和规则管理
- **模块**：
  1. **Planner（规划器）**：任务分解、执行计划、动态调整、回滚机制（4种规划策略）
  2. **Code Executor（代码执行引擎）**：代码执行、沙盒环境、资源限制、安全检查（支持Python/JS/Shell）
  3. **Security（安全模块）**：权限控制、审计日志、审批流程、速率限制（RBAC权限模型）
  4. **Observability（可观测性模块）**：结构化日志、指标收集、分布式追踪、健康检查
  5. **Agents MD（免疫系统）**：规则检查、违规检测、自动修复、安全防护（5种规则类型）
- **API端点**：51个，100%功能覆盖率
- **测试验证**：61个测试用例，100%通过率（API覆盖率22个 + 真实LLM验证21个 + 消融测试18个）
- **验证结果**：每个模块都有明确的价值，消融测试验证了模块的必要性
- **文档**：[Agent_Core_Modules_Design.md](Agent_Core_Modules_Design.md)、[Agent_Core_Modules_Development_Report.md](Agent_Core_Modules_Development_Report.md)

### 7. 知识检索模块封装 (2026-06-02)
- **功能**：封装底层知识图谱模块，提供统一查询接口
- **核心接口**：
  - `query()` - 统一查询，自动识别查询类型
  - `find_entity()` - 查找实体
  - `find_related()` - 查找相关实体
  - `find_path()` - 查找路径
  - `get_statistics()` - 获取统计信息
- **高级查询接口**：`QueryInterface` 支持关键词搜索、实体详情、依赖链分析
- **封装特点**：统一返回格式、自动查询类型识别、向后兼容
- **应用场景**：翻译术语查询、代码解释增强、PPT内容丰富
- **性能**：查询延迟 < 1ms，几乎无感知
- **文档**：[Agent_Core_Modules_Development_Report.md](Agent_Core_Modules_Development_Report.md)

### 8. Broker权限诊断功能 (2026-06-02)
- **功能**：检查和诊断系统权限，提供权限配置指南
- **检查权限**：
  - 辅助功能权限 - 用于无感划词、UI元素读取
  - 屏幕录制权限 - 用于窗口截图、屏幕录制
  - 自动化权限 - 用于浏览器控制、备忘录操作
  - 完全磁盘访问权限 - 用于访问系统保护目录
- **API接口**：
  - `GET /api/v1/system/permissions` - 权限诊断
  - `GET /api/v1/system/permissions/guide` - 权限配置指南
- **诊断结果**：包含权限状态、功能影响、配置建议
- **使用场景**：首次使用前检查权限配置，功能异常时诊断权限问题
- **文档**：[Agent_Core_Modules_Development_Report.md](Agent_Core_Modules_Development_Report.md)

### 9. 现有功能集成测试 (2026-06-02)
- **功能**：验证翻译、代码阅读、PPT等功能与新模块的集成情况
- **测试覆盖**：
  - 翻译功能 + 知识检索集成（2项）
  - 代码阅读 + 知识检索集成（3项）
  - PPT生成 + 知识检索集成（2项）
  - 功能与Broker权限集成（3项）
- **测试结果**：10项集成测试全部通过，100%通过率
- **结论**：新模块与现有功能具有良好的兼容性和协同工作能力
- **测试文件**：`test_integration_existing_features.py`
- **文档**：[Agent_Core_Modules_Development_Report.md](Agent_Core_Modules_Development_Report.md)

### 10. 消融实验 (2026-06-02)
- **功能**：量化评估新模块对现有功能的影响
- **实验设计**：基线系统（无新模块）vs 完整系统（有新模块）
- **测试覆盖**：8项测试，覆盖翻译、代码阅读、PPT、权限诊断
- **测试结果**：8项测试全部通过，100%通过率
- **核心发现**：
  - 知识检索模块显著增强代码阅读（+6条参考）和PPT生成（+5条知识）
  - Broker权限模块新增4项系统权限检查能力
  - 查询延迟 < 1ms，性能影响极小
- **测试文件**：`test_ablation_study.py`
- **文档**：[Agent_Core_Modules_Development_Report.md](Agent_Core_Modules_Development_Report.md)

---

## 🗺️ 开发路线图 (Roadmap)

| 阶段 | 内容 | 状态 |
|------|------|------|
| 双图层光标特效 + 双击右键唤醒 + 拖拽投喂 | 基础交互 | ✅ |
| 双引擎 AI 后端 (MiniMax + Ollama) + 设置面板 | LLM 接入 | ✅ |
| 专属智能体 (会话记忆 + Persona + 健康检查) | Agent 服务 | ✅ |
| IDE 伴生插件 + 动态端口信标 + 全文静默读取 | IDE 场景 | ✅ |
| 浏览器 DOM 读取 (AppleScript) + 多屏适配 | 浏览器场景 | ✅ |
| Privileged Broker 特权代理集成 (沙盒穿透/高权限探针) | 架构升级 | ✅ |
| 上下文感知 (Agent 识别 IDE/浏览器/拖拽来源) | Agent 增强 | ✅ |
| 三击右键任务工作台 (任务定义 + 独立对话 + 上下文贯通) | 工作台 | ✅ |
| 代码重构：cursor_effects 共享库 + 拖拽卡死修复 | 工程优化 | ✅ |
| SQLite 会话持久化 + Persona 文件化 | Agent 增强 | ✅ |
| Markdown 渲染 + 代码高亮 + 卡片拖拽缩放 | UI 增强 | ✅ |
| UI/Agent 生命周期解耦 + macOS LaunchAgent 常驻 | 架构升级 | ✅ |
| Broker 产品化 (LaunchAgent 常驻 + capabilities + 统一错误) | 架构升级 | ✅ |
| 上下文窗口管理 (超长历史自动截断，防 token 超限) | Agent 增强 | ✅ |
| 自定义指令修改 + IDE 选区回写 + custom Persona | 交互增强 | ✅ |
| AXAPI 原生无感选区提取 (替代手动复制) | 场景扩展 | ✅ |
| IDE Extension v2 (诊断/git diff 端点) | IDE 增强 | 🔶 |
| 多 Provider 故障转移 (云端挂了回退本地) | 稳定性 | 🔶 |
| Broker WebSocket 主动推送 (前台应用切换事件) | 主动感知 | ✅ |
| 视觉感知前台 (Vision OCR) | 多模态 | ✅ |
| 角色工坊 (Persona Workshop) | 用户定制 | ✅ |
| PPT共创模式 (AI辅助PPT创作) | 办公增强 | ✅ |
| 知识图谱系统 (项目知识提取) | 知识管理 | ✅ |
| 统一启动脚本 (Broker+知识图谱) | 工程优化 | ✅ |
| Smart Copilot API (能力平台) | API平台 | ✅ |
| Skill化架构 (模块化AI能力) | 架构升级 | ✅ |
| 智能体核心模块 (5个模块开发) | Agent核心 | ✅ |
| 模块验证测试 (API覆盖率100%) | 质量保证 | ✅ |
| 知识检索模块封装 | 知识管理 | ✅ |
| Broker权限诊断功能 | 权限管理 | ✅ |
| 现有功能集成测试 | 质量保证 | ✅ |
| 消融实验验证 | 质量保证 | ✅ |
| 文档全面更新 | 文档维护 | ✅ |

---

## 📚 进阶架构设计文档
- 👉 [OpenCopilot 定制智能体 (Custom Agent) 开发与使用指南](OpenCopilot_Custom_Agent_Guide.md)
- 👉 [OpenCopilot 特权代理模式集成与开发指南](OpenCopilot_Broker_Development_Guide.md)
- 👉 [OpenCopilot 下一代架构演进路线图 (Next-Gen Roadmap)](OpenCopilot_Next_Gen_Roadmap.md)
- 👉 [OpenCopilot 全场景智能上下文获取方案](OpenCopilot_Architecture_Context_Extraction.md)
- 👉 [OpenCopilot Code Review 报告 (2026-05-23)](OpenCopilot_Code_Review_Report.md)
- 👉 [Skill化架构设计文档](Skill_Architecture_Design.md)
- 👉 [智能体核心模块设计文档](Agent_Core_Modules_Design.md)
- 👉 [智能体核心模块开发报告](Agent_Core_Modules_Development_Report.md) - 包含集成测试和消融实验
- 👉 [模块验证报告](Module_Verification_Report.md)

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -r requirements.txt
```

> **Python 版本说明**：推荐 Python 3.11~3.13。如遇 `pynput` 鼠标监听闪退，请降至 3.11。

### 2. ⚠️ 权限要求
首次运行需在 macOS `系统设置 -> 隐私与安全性` 中授予终端以下权限：
1. **辅助功能 (Accessibility)**：用于全局鼠标位置与按键拦截。
2. **屏幕录制/键盘访问**：用于触发系统级文本抓取。

### 3. 启动程序

**方式一：守护进程模式（推荐，一次性安装，开机自启）**

```bash
# 方案 A：统一守护进程（Broker + 知识图谱 API）
bash scripts/install_unified_daemon.sh

# 方案 B：仅 Broker 守护进程
bash scripts/install_broker_daemon.sh

# 启动 UI（自动处理 Qt 插件路径）
bash scripts/start_ui.sh
```

**方式二：开发调试模式（推荐，统一启动）**

```bash
# 终端 1：启动 Broker + 知识图谱 API（需原生终端）
python start_broker_with_kg.py
# 会自动清理占用端口的旧进程，然后启动服务

# 终端 2：启动 UI
bash scripts/start_ui.sh
```

> *可选参数：`--kg-port 8091`、`--broker-port 18890`、`--no-kg`、`--no-cleanup`、`--no-restart`*
> 
> *稳定性特性：自动端口清理、知识图谱 API 崩溃自动重启、健康检查、PID 文件管理*

**方式三：分别启动（灵活控制）**

```bash
# 终端 1：启动 Agent 后台服务
python asu_custom_agent.py

# 终端 2：（可选）启动知识图谱 API
python start_knowledge_graph_api.py --port 8090

# 终端 3：启动 UI
bash scripts/start_ui.sh

# 可选：使用知识检索模块（封装知识图谱）
from knowledge_retrieval import KnowledgeRetrieval
retrieval = KnowledgeRetrieval()
retrieval.initialize()
result = retrieval.query("Agent", "entity")
```

> **说明**：Agent（端口 18888）和 UI 生命周期完全独立。UI 启动时异步探活 Agent——
> - 🟢 Agent 在线：标题栏绿色状态点，正常交互。
> - 🔴 Agent 离线：标题栏红色状态点 + 橙色横幅提示，UI 仍可正常打开。
> - 📊 知识图谱 API（端口 8090）：可选服务，用于查询项目知识。
> - 🔍 知识检索模块：封装知识图谱，提供统一查询接口，支持翻译、代码阅读、PPT等功能的知识增强。

**常用管理命令**

```bash
bash scripts/tail_logs.sh          # 实时查看 Agent 日志
bash scripts/uninstall_daemon.sh   # 卸载守护进程
curl http://127.0.0.1:18888/health # 检查 Agent 是否在线
```

### 4. P0 上下文窗口治理验证结果（2026-05）

- **测试范围**：真实多轮场景 + 边界压力场景
- **通过情况**：`39/39`（`100%`）
- **平均压缩率**：`69.3%`
- **平均历史保留率**：`51.2%`（稳定性优先的预期策略）
- **分场景压缩率**：
  - `ide_large_file`：`74.1%`
  - `browser_long_article`：`70.2%`
  - `chat_long_session`：`58.9%`
  - `drag_bulk_text`：`73.9%`

> 注：历史保留率不是越高越好；当前策略优先保证不超上下文预算与响应稳定性。

### 5. 操作指南

**方式一：物理拖拽（通用，100% 兼容）**
1. 在任何软件中划选文本。
2. 双击右键唤出悬浮卡片（卡片将保持常驻）。
3. 将高亮文本**拖拽**丢入卡片，AI 自动流式解析。
3. **关闭**：分析完成后，点击卡片右上角的 `✕` 按钮即可隐藏。

**方式二：IDE 全文静默读取 (VSCode/Trae/Cursor)**
1. 安装 `asu-ide-extension/` 目录下的 `.vsix` 插件。
2. 双击右键唤出卡片 → 点击绿色 **[📥 极速读取当前 IDE 全文]** 按钮。
3. 当前编辑器内全部代码瞬间投喂给 AI。（Broker 也可以通过文件探针提供更深度的支持）

**方式三：基于 Broker 的浏览器无感读取**
1. 确保已在原生终端启动 `python3 asu_broker/run.py`。
2. 在 Chrome/Safari/Brave/Edge/Arc 中浏览网页。
3. 双击右键唤出卡片 → 点击橙色 **[🌐 一键读取当前网页全文]** 按钮。
4. Broker 将在后台提取 DOM 节点并穿透沙盒返回给 AI。（初次使用仍需在浏览器启用 `Allow JavaScript from Apple Events`）

---

## 🏗️ 项目结构

```text
OpenCopilot/
├── smart_copilot.py              # UI 主程序（悬浮卡片 + 工作台）
├── asu_custom_agent.py           # Agent 后台服务（端口 18888）
├── start_broker_with_kg.py       # 统一启动脚本（Broker + 知识图谱）
├── smart_copilot_api.py          # Smart Copilot API 服务（端口 8089）
├── cursor_effects.py             # 光标特效共享库（Ripple + CursorOverlay）
├── llm_provider.py               # LLM Provider 抽象层
├── dynamic_cursor.py             # 光标特效独立演示程序
├── mouse_tracker.py              # 鼠标轨迹日志工具
├── text_selector.py              # [已废弃] 模拟 Cmd+C 自动捕获方案（当前使用拖拽+粘贴按钮共存）
├── personas/                     # Persona 人格文件
│   └── custom.md                 #   自定义修改指令专用人格
├── knowledge_graph/              # 知识图谱系统
│   ├── models.py                 #   数据模型定义
│   ├── extractor.py              #   文档知识提取器
│   ├── graph.py                  #   知识图谱管理器
│   ├── query.py                  #   查询引擎
│   └── api.py                    #   RESTful API 接口
├── knowledge_retrieval/          # 知识检索模块（封装知识图谱）
│   ├── __init__.py               #   模块入口
│   ├── core.py                   #   核心接口 KnowledgeRetrieval
│   └── query_interface.py        #   高级查询接口 QueryInterface
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Cursor/Trae)
│   ├── context_analyzer.py       #   智能上下文感知
│   ├── suggestion_engine.py      #   AI 主动建议引擎
│   ├── conversation_manager.py   #   多轮对话管理器
│   ├── suggestion_bubble.py      #   建议气泡组件
│   └── content_analysis_panel.py #   内容分析面板
│   ├── context_analyzer.py       #   智能上下文感知
│   ├── suggestion_engine.py      #   AI 主动建议引擎
│   ├── conversation_manager.py   #   多轮对话管理器
│   ├── suggestion_bubble.py      #   建议气泡组件
│   └── content_analysis_panel.py #   内容分析面板
├── skill_architecture/           # Skill化架构核心模块
│   ├── base.py                   #   BaseSkill抽象基类
│   ├── registry.py               #   SkillRegistry注册表
│   ├── router.py                 #   IntentRouter意图路由器
│   ├── executor.py               #   SkillExecutor执行引擎
│   ├── discovery.py              #   SkillDiscovery自动发现
│   ├── config_manager.py         #   ConfigManager配置管理
│   ├── performance.py            #   性能优化模块
│   ├── knowledge_skill.py        #   KnowledgeSkill实现
│   ├── coding_skill.py           #   CodingSkill实现
│   ├── ppt_skill.py              #   PPTSkill实现
│   ├── evaluation_skill.py       #   EvaluationSkill实现
│   ├── file_skill.py             #   FileSkill实现
│   ├── format_skill.py           #   FormatSkill实现
│   └── persona_skill.py          #   PersonaSkill实现
├── planner/                      # 规划器模块（Plan-and-Execute模式）
│   ├── core.py                   #   核心规划逻辑（4种策略）
│   ├── api.py                    #   RESTful API接口
│   └── models.py                 #   数据模型定义
├── code_executor/                # 代码执行引擎模块（沙盒隔离）
│   ├── core.py                   #   核心执行逻辑（Python/JS/Shell）
│   ├── api.py                    #   RESTful API接口
│   └── models.py                 #   数据模型定义
├── security_module/              # 安全模块（RBAC权限模型）
│   ├── core.py                   #   核心安全逻辑
│   ├── api.py                    #   RESTful API接口
│   └── models.py                 #   数据模型定义
├── observability_module/         # 可观测性模块（日志/指标/追踪）
│   ├── core.py                   #   核心可观测性逻辑
│   ├── api.py                    #   RESTful API接口
│   └── models.py                 #   数据模型定义
├── agents_md_module/             # 免疫系统模块（规则检查）
│   ├── core.py                   #   核心规则检查逻辑
│   ├── api.py                    #   RESTful API接口
│   └── models.py                 #   数据模型定义
├── knowledge_retrieval/          # 知识检索模块（封装知识图谱）
│   ├── __init__.py               #   模块入口
│   ├── core.py                   #   核心接口 KnowledgeRetrieval
│   └── query_interface.py        #   高级查询接口 QueryInterface
├── asu-ide-extension/            # IDE 伴生插件 (VSCode/Cursor/Trae)
├── scripts/                      # 管理脚本
│   ├── start_ui.sh               #   启动 UI（自动设置 Qt 插件路径）
│   ├── install_unified_daemon.sh #   安装统一守护进程（Broker + 知识图谱）
│   ├── uninstall_unified_daemon.sh#  卸载统一守护进程
│   ├── install_broker_daemon.sh  #   安装 Broker 为 macOS LaunchAgent
│   ├── uninstall_broker_daemon.sh#   卸载 Broker 守护进程
│   └── tail_logs.sh              #   实时查看 Agent 日志
├── deploy/                       # 部署配置
│   ├── com.asu.unified.plist     #   统一守护进程配置模板（Broker + 知识图谱）
│   ├── com.asu.agent.plist       #   Agent macOS LaunchAgent 配置模板
│   └── com.asu.broker.plist      #   Broker macOS LaunchAgent 配置模板
├── requirements.txt              # Python 依赖
└── *.md                          # 架构文档
```
