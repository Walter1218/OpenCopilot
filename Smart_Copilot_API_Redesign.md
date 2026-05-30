# Smart Copilot API 重新设计

## 设计原则

1. **能力导向**：按"能做什么"而非"调用什么"设计
2. **上下文优先**：所有操作都支持上下文注入
3. **事件驱动**：实时能力通过 WebSocket + 事件系统
4. **可扩展**：支持插件式扩展新能力

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
├─────────────────────────────────────────────────────────┤
│  Context Manager    │  Action Engine   │  Event Bus      │
│  - IDE Context      │  - translate     │  - mouse events │
│  - Browser Context  │  - polish        │  - file events  │
│  - Clipboard        │  - code          │  - IDE events   │
│  - Selection        │  - revision      │  - system events│
│  - File Context     │  - auto          │                 │
└─────────────────────────────────────────────────────────┘
```

## API 端点设计

### 1. 上下文管理（Context API）

```python
# 获取当前上下文
GET /api/context/current
Response: {
    "source": "ide|browser|clipboard|selection|file",
    "content": "选中的文本内容",
    "metadata": {
        "file_path": "/path/to/file.py",
        "language": "python",
        "line_range": [10, 25],
        "browser_url": "https://..."
    }
}

# 注入上下文
POST /api/context/inject
Body: {
    "source": "custom",
    "content": "用户提供的文本",
    "metadata": {}
}

# 上下文历史
GET /api/context/history?limit=10
```

### 2. 动作执行（Action API）

```python
# 统一动作执行端点
POST /api/execute
Body: {
    "action": "translate|polish|code|revision|auto|explain|summarize",
    "context_source": "current|clipboard|selection|file|custom",
    "context_id": "可选，指定上下文ID",
    "parameters": {
        "target_language": "zh",
        "custom_instruction": "可选的自定义指令"
    },
    "stream": true
}

# 响应（非流式）
Response: {
    "action": "translate",
    "result": "翻译结果...",
    "context_used": {...},
    "session_id": "xxx"
}

# 响应（流式 SSE）
data: {"chunk": "翻译", "progress": 0.1}
data: {"chunk": "结果", "progress": 0.5}
data: {"done": true, "full_result": "翻译结果..."}
```

### 3. 会话管理（Session API）

```python
# 创建会话
POST /api/sessions
Body: {
    "type": "quick|chat|cocreation",
    "context_source": "ide"
}

# 获取会话
GET /api/sessions/{session_id}

# 会话内对话
POST /api/sessions/{session_id}/messages
Body: {
    "message": "用户消息",
    "context_source": "current"
}

# 获取会话历史
GET /api/sessions/{session_id}/messages
```

### 4. 系统探测（Probe API）

```python
# 获取系统状态
GET /api/probe/status

# 获取剪贴板
GET /api/probe/clipboard

# 获取选中文本
GET /api/probe/selection

# 获取前台应用
GET /api/probe/frontmost-app

# 获取浏览器内容
GET /api/probe/browser/{browser_name}

# 获取 IDE 上下文
GET /api/probe/ide/context

# 获取窗口截图
GET /api/probe/screenshot
```

### 5. PPT 能力（PPT API）

```python
# 从文本生成 PPT 结构
POST /api/ppt/extract
Body: {
    "text": "原始文本",
    "style": "corporate|creative|minimal"
}

# 生成 PPT 文件
POST /api/ppt/generate
Body: {
    "slides": [...],
    "filename": "output.pptx",
    "theme": "corporate"
}

# PPT 共创
POST /api/ppt/cocreation
Body: {
    "session_id": "xxx",
    "slides": [...],
    "instruction": "添加一页关于..."
}

# 从当前上下文生成 PPT
POST /api/ppt/from-context
Body: {
    "context_source": "selection",
    "style": "corporate"
}
```

### 6. 批量处理（Batch API）

```python
# 批量执行
POST /api/batch
Body: {
    "items": [
        {"text": "文本1", "action": "translate"},
        {"text": "文本2", "action": "polish"}
    ],
    "parallel": true,
    "max_concurrent": 3
}

# 批量任务状态
GET /api/batch/{batch_id}/status
```

### 7. 事件系统（WebSocket）

```python
# WebSocket 连接
WS /ws/events

# 订阅事件
{"action": "subscribe", "events": ["mouse.click", "ide.selection", "file.change"]}

# 接收事件
{"event": "mouse.click", "data": {"x": 100, "y": 200, "button": "right", "count": 2}}
{"event": "ide.selection", "data": {"text": "选中的代码", "file": "main.py"}}
```

## 对比：当前 vs 重新设计

| 方面 | 当前设计 | 重新设计 |
|------|----------|----------|
| **设计理念** | 按功能模块划分 | 按能力划分 |
| **上下文** | 手动传入文本 | 自动获取+手动注入 |
| **动作类型** | 6 种固定 | 可扩展的动作系统 |
| **实时能力** | 无 | WebSocket 事件系统 |
| **批量处理** | 简单循环 | 异步任务队列 |
| **会话管理** | 内存存储 | 支持持久化 |
| **扩展性** | 需改代码 | 插件式扩展 |

## 实现建议

### 1. 分层架构
```python
# 第一层：API Gateway（路由+认证）
# 第二层：Context Manager（上下文管理）
# 第三层：Action Engine（动作执行）
# 第四层：Provider（LLM 调用）
```

### 2. 使用依赖注入
```python
from fastapi import Depends

async def get_context_manager():
    return ContextManager()

async def get_action_engine(
    context: ContextManager = Depends(get_context_manager)
):
    return ActionEngine(context)
```

### 3. 事件总线
```python
class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
    
    def subscribe(self, event: str, callback):
        self._subscribers[event].append(callback)
    
    async def publish(self, event: str, data: dict):
        for callback in self._subscribers[event]:
            await callback(data)
```

## 结论

如果我重新设计，会采用：
1. **能力导向**而非功能导向
2. **上下文优先**的设计理念
3. **事件驱动**的实时能力
4. **可扩展**的插件架构

当前的 API 设计更像一个"功能列表"，而不是一个"能力平台"。
