# OpenCopilot MCP 使用指南

## 概述

OpenCopilot 已实现 MCP (Model Context Protocol) Server，允许外部工具（如 Claude Desktop、Cursor）通过 MCP 协议查询 OpenCopilot 的能力。

## 可用工具

MCP Server 暴露以下 5 个工具：

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `query_knowledge_graph` | 查询知识图谱（482 实体，329 关系） | query, query_type, entity_type, max_depth |
| `search_memory` | 搜索伴生记忆（L2+L3） | query, memory_type, limit |
| `get_broker_status` | 获取 Broker 系统状态 | include_details |
| `search_conversation` | 搜索历史对话 | query, limit |
| `get_system_info` | 获取系统信息 | 无 |

## 使用方式

### 方式 1：Claude Desktop

配置文件已自动创建：`~/.config/claude/claude_desktop_config.json`

**重启 Claude Desktop** 后，在对话中即可使用 OpenCopilot 的工具。

示例对话：
```
User: 查询知识图谱中关于 "knowledge_graph" 的信息
Claude: [调用 query_knowledge_graph 工具]
```

### 方式 2：Cursor

在 Cursor 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "opencopilot": {
      "command": "python",
      "args": ["/Users/onetwo/Documents/trae_projects/OpenCopilot/tools/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/onetwo/Documents/trae_projects/OpenCopilot"
      }
    }
  }
}
```

### 方式 3：命令行测试

```bash
# 启动 MCP Server
./start_mcp_server.sh

# 或直接运行
python tools/mcp_server.py
```

然后通过 stdin 发送 JSON-RPC 请求：

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_system_info","arguments":{}}}
```

## 工具使用示例

### 1. 查询知识图谱

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query_knowledge_graph",
    "arguments": {
      "query": "knowledge_graph",
      "query_type": "search",
      "max_depth": 2
    }
  }
}
```

### 2. 搜索记忆

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_memory",
    "arguments": {
      "query": "项目架构",
      "limit": 5
    }
  }
}
```

### 3. 获取 Broker 状态

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_broker_status",
    "arguments": {
      "include_details": true
    }
  }
}
```

## 技术细节

- **协议**：MCP (Model Context Protocol) - JSON-RPC over stdio
- **传输方式**：stdio（标准输入/输出）
- **安全特性**：不开放网络端口，进程间通信

## 故障排除

### Claude Desktop 无法连接

1. 确认配置文件存在：`~/.config/claude/claude_desktop_config.json`
2. 重启 Claude Desktop
3. 检查 Python 路径是否正确

### 工具调用失败

1. 检查知识图谱文件是否存在：`knowledge_graph/opencopilot_knowledge_graph.json`
2. 检查记忆系统是否初始化
3. 查看日志输出

## 文件清单

- `tools/mcp_server.py` - MCP Server 实现
- `tools/mcp_client.py` - MCP Client 实现（用于连接外部 MCP Server）
- `start_mcp_server.sh` - 启动脚本
- `~/.config/claude/claude_desktop_config.json` - Claude Desktop 配置
- `~/.asu_copilot/mcp_servers.json` - MCP Client 配置
