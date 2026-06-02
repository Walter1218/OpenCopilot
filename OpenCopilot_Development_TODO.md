# OpenCopilot 后续开发方向 TODO

> **文档状态**: v1.3  
> **更新日期**: 2026-06-02  
> **当前版本**: v2.6（MCP Server实现，Provider故障转移完成，跨文件符号分析功能实现，全局测试100%通过）  
> **目标**: 从"可用原型"升级为"成熟产品"

---

## 当前状态总结

### 已完成的核心能力 ✅

| 阶段 | 功能 | 状态 |
|------|------|------|
| P0 | 双图层光标特效 + 双击右键唤醒 | ✅ |
| P0 | 双引擎AI后端（MiniMax + Ollama） | ✅ |
| P0 | 上下文感知智能体（IDE/浏览器/拖拽场景） | ✅ |
| P0 | 特权代理Broker（沙盒穿透、系统探针） | ✅ |
| P0 | SQLite会话持久化 + 上下文窗口管理 | ✅ |
| P1 | 多模态视觉感知（Vision OCR） | ✅ |
| P1 | 全局事件订阅与主动状态推送 | ✅ |
| P1 | 底层高亮选区提取（AXAPI落地） | ✅ |
| P2 | Persona角色工坊 | ✅ |
| P2 | Markdown富文本渲染与代码高亮 | ✅ |
| P2 | IDE Extension基础功能 | ✅ |
| P2 | PPT共创模式改进（4阶段） | ✅ |
| P2 | 知识图谱系统（项目知识提取） | ✅ |
| P2 | 统一启动脚本（Broker+知识图谱） | ✅ |
| P2 | Smart Copilot API（能力平台） | ✅ |
| P2 | Skill化架构（模块化AI能力） | ✅ |
| P3 | 智能体核心模块（5个模块开发） | ✅ |
| P3 | 模块验证测试（API覆盖率100%） | ✅ |
| P3 | MCP Server实现（5个工具） | ✅ |
| P3 | Provider故障转移功能 | ✅ |
| P3 | 跨文件符号分析功能 | ✅ |
| P3 | 全局测试修复（100%通过率） | ✅ |

### 待完成的能力 🔶

| 功能 | 状态 | 优先级 |
|------|------|--------|
| IDE Extension v2（诊断/diff） | 🔶 待规划 | P1 |
| Broker产品化（权限诊断） | 🔶 部分完成 | P2 |

---

## 开发方向一：Agent Core v2 - 稳定化与可扩展化

**目标**: 将 `asu_custom_agent.py` 从轻量代理升级为稳定的 Agent Runtime

### 1.1 统一API协议

**当前状态**: 
- 主接口: `POST /v1/agent/chat` ✅
- 管理接口缺失 🔶

**待实现接口**:

```python
# 会话管理
POST /v1/agent/session/clear     # 清除会话
GET  /v1/agent/sessions          # 获取会话列表

# Persona管理
GET  /v1/agent/personas          # 获取Persona列表
POST /v1/agent/personas/reload   # 热重载Persona
```

**预计工作量**: 1-2天

### 1.2 多Provider故障转移 ✅ 已完成

**目标**: 保障极端情况下的可用性，实现云端/本地双擎平滑切换

**当前状态**: 
- MiniMax云端 ✅
- Ollama本地 ✅
- 自动故障转移 ✅

**实现方案**:

```python
class FailoverProvider:
    def __init__(self):
        self.providers = [
            MiniMaxProvider(),  # 优先使用云端
            OllamaProvider(),   # 备选本地
        ]
        self.current_index = 0
    
    def chat(self, message):
        for i, provider in enumerate(self.providers):
            try:
                return provider.chat(message)
            except Exception as e:
                logger.warning(f"Provider {i} failed: {e}")
                continue
        raise AllProvidersFailedError()
```

**已实现功能**:
1. Provider健康检查（定时ping）✅
2. 故障检测与自动切换 ✅
3. 切换状态通知UI ✅
4. 配置优先级设置 ✅

**API端点**:
- `GET /api/provider/status` - 获取 Provider 状态
- `POST /api/provider/failover/test` - 测试故障转移功能

**测试验证**: 13个测试全部通过

**实现文件**: `llm_provider.py`

### 1.3 任务状态管理

**目标**: 工作台任务持久化，支持任务模板

**当前状态**: 
- 工作台任务设定 ✅
- 任务持久化 🔶
- 任务模板 🔶

**待实现功能**:

1. **任务持久化**
   - 任务数据写入SQLite
   - 重启后自动恢复
   - 快捷卡片显示当前任务

2. **任务下挂上下文**
   - 已读取的IDE文件列表
   - 已读取的网页列表
   - 用户拖入的资料
   - 最近问答摘要

3. **任务模板系统**
   ```python
   TASK_TEMPLATES = {
       "code_review": {
           "name": "代码审查",
           "system_prompt": "你是一个专业的代码审查专家...",
           "suggested_actions": ["explain", "polish", "code"]
       },
       "bug_fix": {
           "name": "Bug定位",
           "system_prompt": "你是一个Bug调试专家...",
           "suggested_actions": ["explain", "code"]
       },
       "doc_summary": {
           "name": "文档总结",
           "system_prompt": "你是一个文档分析专家...",
           "suggested_actions": ["summarize", "polish"]
       }
   }
   ```

**预计工作量**: 5-7天

---

## 开发方向二：IDE Extension v2 - 从"全文读取"到"开发现场读取"

**目标**: 让 OpenCopilot 在代码场景下拥有比普通划词工具更强的上下文优势

### 2.1 实现诊断接口 `/diagnostics`

**功能**: 获取当前文件的错误和警告

**接口设计**:
```javascript
// GET /diagnostics
{
    "fileName": "/path/to/file.py",
    "diagnostics": [
        {
            "severity": 0,  // 0=Error, 1=Warning, 2=Info, 3=Hint
            "message": "Undefined variable 'x'",
            "source": "python",
            "code": "reportUndefinedVariable",
            "line": 10,
            "character": 5
        }
    ]
}
```

**实现方式**: 使用 VS Code API `languages.getDiagnostics()`

**预计工作量**: 1-2天

### 2.2 实现Git diff接口 `/git-diff`

**功能**: 获取当前工作区未提交变更

**接口设计**:
```javascript
// GET /git-diff
{
    "fileName": "/path/to/file.py",
    "diff": "diff --git a/file.py b/file.py\n...",
    "error": null
}
```

**实现方式**: 
- 使用 VS Code API `git.repositories`
- 或直接执行 `git diff` 命令

**预计工作量**: 1-2天

### 2.3 实现符号接口 `/symbol`

**功能**: 获取光标附近的函数/类范围

**接口设计**:
```javascript
// GET /symbol
{
    "name": "my_function",
    "kind": 11,  // SymbolKind
    "text": "def my_function():\n    pass",
    "range": {
        "startLine": 10,
        "startCol": 0,
        "endLine": 12,
        "endCol": 8
    }
}
```

**实现方式**: 使用 VS Code API `document.symbolAtPosition()`

**预计工作量**: 1天

### 2.4 实现工作区接口 `/workspace`

**功能**: 获取工作区根路径和文件树摘要

**接口设计**:
```javascript
// GET /workspace
{
    "rootPath": "/path/to/workspace",
    "folders": [
        {"name": "src", "path": "src"},
        {"name": "tests", "path": "tests"}
    ],
    "files": [
        {"name": "main.py", "path": "src/main.py", "language": "python"},
        {"name": "utils.py", "path": "src/utils.py", "language": "python"}
    ],
    "gitBranch": "main"
}
```

**实现方式**: 使用 VS Code API `workspace.workspaceFolders`

**预计工作量**: 1-2天

### 2.5 优先级排序

| 接口 | 优先级 | 价值 | 工作量 |
|------|--------|------|--------|
| `/diagnostics` | P1 | 代码错误自动修复 | 1-2天 |
| `/git-diff` | P1 | 代码审查和变更总结 | 1-2天 |
| `/symbol` | P2 | 精确代码分析 | 1天 |
| `/workspace` | P2 | 项目级上下文理解 | 1-2天 |

**总预计工作量**: 4-7天

---

## 开发方向三：Broker v2 - 系统级探针产品化

**目标**: 让 Broker 成为稳定、可诊断、可常驻的系统探针层

### 3.1 权限诊断面板

**当前状态**: 权限引导偏手动

**待实现功能**:
1. **权限状态检测**
   ```python
   @app.get("/api/v1/system/permissions")
   async def check_permissions():
       return {
           "accessibility": check_accessibility_permission(),
           "screen_recording": check_screen_recording_permission(),
           "automation": check_automation_permission()
       }
   ```

2. **权限引导UI**
   - 在主程序中展示权限状态
   - 提供一键跳转系统设置
   - 权限变更实时检测

**预计工作量**: 2-3天

### 3.2 主动推送扩展

**当前状态**: 
- `app_activated` ✅
- 其他事件 🔶

**待实现事件**:
```python
# 浏览器标签切换
{
    "event": "browser_tab_changed",
    "data": {
        "browser": "Chrome",
        "url": "https://...",
        "title": "Page Title"
    }
}

# 权限需求提示
{
    "event": "permission_required",
    "data": {
        "permission": "accessibility",
        "action": "read_selection"
    }
}

# 探针错误
{
    "event": "probe_error",
    "data": {
        "probe": "screen",
        "error": "Permission denied",
        "suggestion": "请在系统设置中授予屏幕录制权限"
    }
}
```

**预计工作量**: 2-3天

### 3.3 打包为独立.app

**目标**: 拥有稳定 Bundle ID，支持一键重启

**待实现功能**:
1. 创建 `Info.plist`
2. 打包为 `ASU Broker.app`
3. 支持 `open -a "ASU Broker"` 启动
4. 支持 `killall "ASU Broker"` 关闭

**预计工作量**: 3-5天

---

## 开发方向四：全局上下文感知 - 从被动响应到主动感知

**目标**: 利用应用切换事件构建智能工作流

### 4.1 上下文注入原型

**场景**: 用户在浏览器复制报错信息，切换到IDE

**AI行为**: 
- 检测到 `Browser → IDE` 切换
- 隐式附带浏览器上下文
- 主动提示："检测到您刚在浏览器查阅了报错，需要我为您定位问题吗？"

**实现方案**:
```python
class ContextInjector:
    def __init__(self):
        self.app_history = []
    
    def on_app_switch(self, from_app, to_app):
        self.app_history.append({
            "from": from_app,
            "to": to_app,
            "timestamp": time.time()
        })
        
        # 检测高价值切换模式
        if self._is_high_value_switch(from_app, to_app):
            self._inject_context(from_app, to_app)
    
    def _is_high_value_switch(self, from_app, to_app):
        patterns = [
            ("Browser", "IDE"),  # 查资料→写代码
            ("Terminal", "IDE"),  # 调试→修改
            ("Figma", "IDE"),    # 设计→实现
        ]
        return (from_app, to_app) in patterns
```

**预计工作量**: 3-5天

### 4.2 意图预测规则库

**高频切换链路**:
1. `Browser → Terminal → IDE`: 前端开发启动
2. `IDE → Browser → IDE`: 查文档→写代码
3. `Terminal → IDE`: 调试→修复
4. `Figma → IDE`: 设计→实现

**实现方案**:
```python
INTENT_RULES = {
    "frontend_dev_start": {
        "sequence": ["Figma", "Terminal", "IDE"],
        "confidence": 0.8,
        "action": "启动本地开发服务器"
    },
    "debug_fix": {
        "sequence": ["Terminal", "IDE"],
        "confidence": 0.9,
        "action": "定位并修复错误"
    }
}
```

**预计工作量**: 2-3天

### 4.3 沉浸度保护

**场景**: 用户在IDE连续工作30分钟

**AI行为**:
- 自动将系统通知静音
- 拦截非紧急消息
- 生成消息摘要
- 用户切回通讯软件时汇总汇报

**实现方案**:
```python
class FocusManager:
    def __init__(self):
        self.focus_start_time = None
        self.focus_app = None
        self.muted_messages = []
    
    def on_app_switch(self, app_name):
        if app_name in ["IDE", "VSCode", "Cursor"]:
            if not self.focus_start_time:
                self.focus_start_time = time.time()
                self.focus_app = app_name
                self._enable_dnd_mode()
        else:
            if self.focus_start_time:
                self._disable_dnd_mode()
                self._send_summary()
                self.focus_start_time = None
```

**预计工作量**: 3-5天

---

## 开发方向五：API能力平台完善

**目标**: 基于能力导向的API设计，提供更灵活的扩展能力

### 5.1 统一上下文协议（ContextEnvelope）

**当前状态**: 上下文参数分散在各层

**设计方案**:
```json
{
    "source": "ide|browser|drag|chat|screen|file",
    "app": "Trae|Chrome|Safari",
    "title": "文件名或网页标题",
    "language": "python",
    "content": "主要内容",
    "selection": "用户选区",
    "task": "工作台任务",
    "metadata": {},
    "timestamp": 1716480000.123
}
```

**实现方式**:
```python
class ContextEnvelope:
    def __init__(self, source, content, **kwargs):
        self.source = source
        self.content = content
        self.app = kwargs.get("app")
        self.title = kwargs.get("title")
        self.language = kwargs.get("language")
        self.selection = kwargs.get("selection")
        self.task = kwargs.get("task")
        self.metadata = kwargs.get("metadata", {})
        self.timestamp = kwargs.get("timestamp", time.time())
    
    def to_dict(self):
        return {
            "source": self.source,
            "app": self.app,
            "title": self.title,
            "language": self.language,
            "content": self.content,
            "selection": self.selection,
            "task": self.task,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
```

**预计工作量**: 2-3天

### 5.2 事件系统增强

**当前事件类型**:
- `app_activated` ✅
- `mouse.click` 🔶
- `ide.selection` 🔶

**待实现事件**:
```python
EVENT_TYPES = {
    "mouse.click": "鼠标点击",
    "mouse.double_click": "鼠标双击",
    "ide.selection": "IDE选区变更",
    "ide.file_open": "IDE打开文件",
    "ide.file_save": "IDE保存文件",
    "browser.tab_changed": "浏览器标签切换",
    "browser.url_changed": "浏览器URL变更",
    "clipboard.changed": "剪贴板内容变更",
    "system.app_switch": "系统应用切换"
}
```

**预计工作量**: 2-3天

### 5.3 批量处理优化

**当前状态**: 简单循环

**待实现功能**:
1. **异步任务队列**
   ```python
   class BatchProcessor:
       def __init__(self, max_concurrent=3):
           self.queue = asyncio.Queue()
           self.max_concurrent = max_concurrent
           self.results = {}
       
       async def process(self, items):
           tasks = []
           for item in items:
               task = asyncio.create_task(self._process_item(item))
               tasks.append(task)
           return await asyncio.gather(*tasks)
   ```

2. **任务状态监控**
   ```python
   GET /api/batch/{batch_id}/status
   {
       "batch_id": "xxx",
       "total": 10,
       "completed": 7,
       "failed": 1,
       "pending": 2,
       "results": [...]
   }
   ```

**预计工作量**: 2-3天

---

## 开发方向六：工程化治理

**目标**: 提升代码质量、测试覆盖和系统稳定性

### 6.1 代码清理

**待清理内容**:

1. **ModelScannerWorker OpenClaw遗留代码**
   - 位置: `smart_copilot.py` 第29-74行
   - 问题: 包含 `openclaw agents list`、端口 `18789`/`18791` 探测
   - 修复: 清理OpenClaw特定逻辑，专注于通用OpenAI兼容接口

2. **异常处理过宽**
   - 位置: 多处 `except Exception:`
   - 问题: 错误被静默吞噬
   - 修复: 至少打印 `e` 的详细堆栈

3. **SSE错误边界优化**
   - 问题: 长异常栈可能破坏JSON结构
   - 修复: 确保流关闭安全合规

**预计工作量**: 2-3天

### 6.2 测试覆盖提升

**当前测试结构**:
- 根目录散落约20个测试文件
- `tests/unit/` 下33个单元测试
- 结构不够统一

**改进方案**:
1. 整合根目录测试文件到 `tests/` 目录
2. 按功能模块组织测试
3. 补充集成测试和端到端测试
4. 建立CI/CD流水线

**预计工作量**: 3-5天

### 6.3 配置安全

**当前问题**:
- `config.json` 和 `.env` 包含API Key
- 配置文件权限未限制

**改进方案**:
1. 敏感信息加密存储
2. 配置文件权限管理（600）
3. 环境变量验证
4. 配置文件模板（`.env.example`）

**预计工作量**: 1-2天

---

## 推荐实施路线图

| 阶段 | 目标 | 核心产出 | 预计周期 |
|------|------|----------|----------|
| **阶段1** | Agent Core稳定化 | 统一API、多Provider故障转移、任务状态管理 | ✅ 故障转移已完成 |
| **阶段2** | IDE深度集成 | Extension v2（诊断/diff/符号/工作区） | 2周 |
| **阶段3** | Broker产品化 | 权限诊断、主动推送扩展、独立.app打包 | 1-2周 |
| **阶段4** | 上下文感知增强 | 上下文注入、意图预测、沉浸度保护 | 2-3周 |
| **阶段5** | API平台完善 | ContextEnvelope、事件系统、批量处理 | 1-2周 |
| **阶段6** | 工程化收敛 | 代码清理、测试覆盖、配置安全 | 1-2周 |

**总预计周期**: 10-14周

---

## 近期最建议优先做的3件事

### 1. IDE Extension v2（诊断接口）⭐⭐⭐

**理由**:
- 开发场景的核心价值
- 让AI能理解代码错误
- 提供自动修复建议

**预计工作量**: 2-3天

### 2. 统一API协议 ⭐⭐

**理由**:
- 规范Agent接口
- 为后续功能扩展打下基础
- 提升API一致性

**预计工作量**: 1-2天

### 3. MCP Server 增强 ⭐⭐

**理由**:
- 已实现基础MCP Server，支持5个工具
- 可扩展更多工具，如代码执行、文件操作等
- 提升与外部工具的集成能力

**预计工作量**: 2-3天

---

## 相关文档

- `OpenCopilot_Next_Gen_Roadmap.md` - 下一代架构演进路线图
- `OpenCopilot_Local_Agent_Roadmap.md` - 本地智能体开发路线
- `OpenCopilot_Global_Context_Awareness_Design.md` - 全局上下文感知设计
- `Smart_Copilot_API_Redesign.md` - 能力平台API设计方案
- `MCP_Usage_Guide.md` - MCP Server 使用指南
- `IDE_Extension_Development_Guide.md` - IDE扩展开发指南
- `OpenCopilot_Code_Review_Report.md` - 代码审查报告

---

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-05-30 | v1.0 | 初始版本，整理6大开发方向 |
