# Smart Copilot 能力平台 API 使用指南

## 概述

Smart Copilot 能力平台是基于"能力"而非"功能"设计的 API 平台，核心理念是**上下文管理 + 动作执行 + 事件系统**。

### 核心特性

- **上下文优先**：自动获取 IDE、浏览器、剪贴板等上下文
- **统一动作执行**：通过 `/api/execute` 端点执行所有动作
- **事件驱动**：WebSocket 实时事件系统
- **可扩展**：支持插件式扩展新能力

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn httpx python-pptx
```

### 2. 启动 API 服务

```bash
# 方式 1: 直接运行
python smart_copilot_platform.py

# 方式 2: 使用 uvicorn
uvicorn smart_copilot_platform:app --host 0.0.0.0 --port 8089 --reload
```

### 3. 访问 API 文档

- **Swagger UI**: http://localhost:8089/docs
- **ReDoc**: http://localhost:8089/redoc

## 核心概念

### 上下文（Context）

上下文是能力平台的核心，代表当前处理的内容来源。

| 上下文来源 | 说明 |
|------------|------|
| `ide` | IDE 中选中的代码或文件 |
| `browser` | 浏览器当前页面内容 |
| `clipboard` | 系统剪贴板内容 |
| `selection` | 当前选中的文本 |
| `custom` | 用户自定义内容 |
| `current` | 自动探测当前上下文（优先级：IDE > 剪贴板 > 浏览器） |

### 动作（Action）

动作是对上下文执行的操作。

| 动作类型 | 说明 |
|----------|------|
| `translate` | 翻译 |
| `polish` | 润色 |
| `code` | 代码解析 |
| `revision` | 全文修订 |
| `auto` | 自动处理 |
| `explain` | 解释 |
| `summarize` | 总结 |
| `custom` | 自定义处理 |
| `ppt_extract` | PPT 结构提取 |

## API 端点一览

### 基础接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 根路径，返回 API 信息和能力列表 |
| `/health` | GET | 健康检查 |

### 上下文管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/context/current` | GET | 获取当前上下文 |
| `/api/context/inject` | POST | 注入自定义上下文 |
| `/api/context/history` | GET | 获取上下文历史 |

### 动作执行

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/execute` | POST | 执行动作（统一端点） |
| `/api/execute/stream` | POST | 流式执行动作（SSE） |

### 系统探测

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/probe/status` | GET | 获取系统探测状态 |
| `/api/probe/clipboard` | GET | 获取剪贴板内容 |
| `/api/probe/selection` | GET | 获取选中文本 |
| `/api/probe/ide/context` | GET | 获取 IDE 上下文 |
| `/api/probe/browser` | GET | 获取浏览器上下文 |

### PPT 能力

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ppt/generate` | POST | 生成 PPT 文件 |
| `/api/ppt/from-context` | POST | 从当前上下文生成 PPT |

### 事件系统

| 端点 | 方法 | 描述 |
|------|------|------|
| `/ws/events` | WebSocket | 事件订阅和接收 |

## 使用示例

### 1. 执行翻译动作

```python
import httpx

# 使用自定义上下文
response = httpx.post("http://localhost:8089/api/execute", json={
    "action": "translate",
    "context_source": "custom",
    "context_content": "Hello, how are you?",
    "parameters": {"target_language": "zh"}
})
print(response.json()["result"])  # 输出：你好，你好吗？
```

### 2. 使用自动上下文探测

```python
import httpx

# 自动探测当前上下文（IDE > 剪贴板 > 浏览器）
response = httpx.post("http://localhost:8089/api/execute", json={
    "action": "polish",
    "context_source": "current",
    "parameters": {}
})
print(response.json()["result"])
```

### 3. 注入上下文后执行动作

```python
import httpx

# 先注入上下文
context_resp = httpx.post(
    "http://localhost:8089/api/context/inject",
    params={"content": "这是一段需要处理的文本"}
)
context_id = context_resp.json()["context_id"]

# 然后执行动作
response = httpx.post("http://localhost:8089/api/execute", json={
    "action": "polish",
    "context_source": "custom",
    "context_content": "这是一段需要处理的文本",
    "parameters": {}
})
print(response.json()["result"])
```

### 4. 流式执行动作

```python
import httpx
import json

with httpx.stream("POST", "http://localhost:8089/api/execute/stream", json={
    "action": "translate",
    "context_source": "custom",
    "context_content": "Hello World",
    "parameters": {"target_language": "zh"}
}) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            data = json.loads(line[6:])
            if "chunk" in data:
                print(data["chunk"], end="", flush=True)
            elif data.get("done"):
                print("\n完成")
                break
```

### 5. 从上下文生成 PPT

```python
import httpx

# 从当前上下文生成 PPT
response = httpx.post(
    "http://localhost:8089/api/ppt/from-context",
    params={"context_source": "clipboard", "style": "corporate"}
)

# 保存文件
with open("output.pptx", "wb") as f:
    f.write(response.content)
```

### 6. WebSocket 事件订阅

```python
import asyncio
import websockets
import json

async def subscribe_events():
    async with websockets.connect("ws://localhost:8089/ws/events") as ws:
        # 订阅事件
        await ws.send(json.dumps({
            "action": "subscribe",
            "events": ["mouse.click", "ide.selection"]
        }))
        
        # 接收事件
        while True:
            event = json.loads(await ws.recv())
            print(f"事件: {event['event']}, 数据: {event['data']}")

asyncio.run(subscribe_events())
```

### 7. 系统探测

```python
import httpx

# 获取系统状态
status = httpx.get("http://localhost:8089/api/probe/status").json()
print(f"Broker 在线: {status['broker_online']}")
print(f"IDE 连接: {status['ide_connected']}")
print(f"浏览器连接: {status['browser_connected']}")

# 获取剪贴板
clipboard = httpx.get("http://localhost:8089/api/probe/clipboard").json()
print(f"剪贴板内容: {clipboard['content']}")

# 获取 IDE 上下文
ide_ctx = httpx.get("http://localhost:8089/api/probe/ide/context").json()
print(f"IDE 上下文: {ide_ctx['content'][:100]}...")
```

## cURL 示例

```bash
# 健康检查
curl http://localhost:8089/health

# 执行翻译动作
curl -X POST http://localhost:8089/api/execute \
  -H "Content-Type: application/json" \
  -d '{"action":"translate","context_source":"custom","context_content":"Hello","parameters":{"target_language":"zh"}}'

# 注入上下文
curl -X POST "http://localhost:8089/api/context/inject?content=测试文本"

# 获取当前上下文
curl http://localhost:8089/api/context/current

# 获取系统状态
curl http://localhost:8089/api/probe/status

# 获取剪贴板
curl http://localhost:8089/api/probe/clipboard
```

## 错误处理

所有 API 错误都返回标准格式：

```json
{
  "detail": "错误描述信息"
}
```

常见状态码：
- `200`: 成功
- `400`: 请求参数错误（如无法获取上下文）
- `404`: 资源不存在
- `500`: 服务器内部错误
- `503`: 服务不可用（如 Broker 未运行）

## 注意事项

1. **LLM Provider 配置**: 首次使用前需要配置 LLM Provider（MiniMax 或本地模型）
2. **Broker 服务**: 系统探测功能需要 Broker 服务运行
3. **IDE 扩展**: IDE 上下文获取需要 IDE 扩展连接
4. **浏览器探测**: 浏览器上下文获取需要前台应用是支持的浏览器
5. **上下文过滤**: LLM 返回的 `<think>` 标签会被自动过滤

## 架构说明

### 核心模块

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
├─────────────────────────────────────────────────────────┤
│  ContextManager    │  ActionEngine   │  EventBus         │
│  - IDE Context     │  - translate    │  - mouse events   │
│  - Browser Context │  - polish       │  - file events    │
│  - Clipboard       │  - code         │  - IDE events     │
│  - Selection       │  - revision     │  - system events  │
│  - File Context    │  - auto         │                   │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
用户请求 → 获取上下文 → 执行动作 → 返回结果
    ↓
上下文来源：IDE / 浏览器 / 剪贴板 / 自定义
    ↓
动作类型：translate / polish / code / ...
    ↓
LLM 处理 → 过滤 <think> 标签 → 返回结果
```

## 相关文件

- `smart_copilot_platform.py` - 能力平台 API 服务主文件
- `Smart_Copilot_API_Redesign.md` - 详细设计方案文档
- `test_platform.py` - 测试脚本

## 相关链接

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Swagger UI](http://localhost:8089/docs)
- [ReDoc](http://localhost:8089/redoc)
