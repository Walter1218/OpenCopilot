"""
MCP Server 测试

测试 MCP Server 的各项功能：
1. 工具列表获取
2. 知识图谱查询
3. 记忆系统搜索
4. Broker 状态获取
5. 系统信息获取
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

# 导入被测试模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.mcp_server import MCPServer


class TestMCPServer:
    """MCP Server 测试类"""
    
    @pytest.fixture
    def server(self):
        """创建 MCP Server 实例"""
        return MCPServer()
    
    def test_tools_registration(self, server):
        """测试工具注册"""
        assert len(server.tools) == 5
        
        tool_names = [t.name for t in server.tools]
        assert "query_knowledge_graph" in tool_names
        assert "search_memory" in tool_names
        assert "get_broker_status" in tool_names
        assert "search_conversation" in tool_names
        assert "get_system_info" in tool_names
    
    def test_get_tools_schema(self, server):
        """测试获取工具 schema"""
        schema = server.get_tools_schema()
        
        assert len(schema) == 5
        
        # 检查每个工具的 schema
        for tool_schema in schema:
            assert "name" in tool_schema
            assert "description" in tool_schema
            assert "inputSchema" in tool_schema
    
    @pytest.mark.asyncio
    async def test_handle_initialize(self, server):
        """测试初始化请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
    
    @pytest.mark.asyncio
    async def test_handle_tools_list(self, server):
        """测试工具列表请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 5
    
    @pytest.mark.asyncio
    async def test_handle_ping(self, server):
        """测试 ping 请求"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "ping",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert response["result"]["pong"] is True
    
    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, server):
        """测试未知方法"""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown_method",
            "params": {}
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32601
    
    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, server):
        """测试未知工具"""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        assert "工具不存在" in response["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_query_knowledge_graph_no_graph(self, server):
        """测试知识图谱查询（未加载图谱）"""
        server._query_engine = None
        
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "query_knowledge_graph",
                "arguments": {
                    "query": "test"
                }
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 6
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is False
        assert "知识图谱未加载" in content["error"]
    
    @pytest.mark.asyncio
    async def test_search_memory_no_memory(self, server):
        """测试记忆搜索（未初始化记忆系统）"""
        server._memory_system = None
        
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "search_memory",
                "arguments": {
                    "query": "test"
                }
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 7
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is False
        assert "记忆系统未初始化" in content["error"]
    
    @pytest.mark.asyncio
    async def test_get_broker_status_no_probe(self, server):
        """测试 Broker 状态（未初始化探针）"""
        server._system_probe = None
        
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "get_broker_status",
                "arguments": {}
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 8
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is False
        assert "系统探针未初始化" in content["error"]
    
    @pytest.mark.asyncio
    async def test_get_system_info(self, server):
        """测试系统信息获取"""
        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "get_system_info",
                "arguments": {}
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 9
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "version" in content
        assert "modules" in content
        assert "tools_count" in content
        assert content["tools_count"] == 5
    
    @pytest.mark.asyncio
    async def test_search_conversation_no_module(self, server):
        """测试对话搜索（未实现模块）"""
        request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "search_conversation",
                "arguments": {
                    "query": "test"
                }
            }
        }
        
        response = await server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 10
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["count"] == 0
        assert "message" in content


class TestMCPServerWithMock:
    """使用 Mock 测试 MCP Server"""
    
    @pytest.fixture
    def server_with_mock(self):
        """创建带 Mock 的 MCP Server"""
        server = MCPServer()
        
        # Mock 知识图谱
        mock_query_engine = MagicMock()
        mock_entity = MagicMock()
        mock_entity.entity_id = "entity_1"
        mock_entity.name = "Test Entity"
        mock_entity.entity_type.value = "module"
        mock_entity.description = "Test description"
        mock_entity.properties = {}
        
        mock_query_engine.find_entity.return_value = [mock_entity]
        mock_query_engine.find_related_entities.return_value = {
            "entities": [mock_entity],
            "relations": []
        }
        
        server._query_engine = mock_query_engine
        
        # Mock 记忆系统
        mock_memory_system = MagicMock()
        mock_memory = MagicMock()
        mock_memory.memory_id = "memory_1"
        mock_memory.content = "Test memory"
        mock_memory.memory_type.value = "long_term"
        mock_memory.importance = 0.8
        mock_memory.tags = ["test"]
        mock_memory.created_at = "2026-06-02T19:00:00"
        mock_memory.last_accessed = "2026-06-02T19:00:00"
        
        mock_memory_system.retrieve_memories.return_value = [mock_memory]
        server._memory_system = mock_memory_system
        
        # Mock 系统探针
        mock_system_probe = MagicMock()
        mock_system_probe.is_broker_alive.return_value = True
        mock_system_probe.get_frontmost_app.return_value = "VSCode"
        mock_system_probe.get_clipboard.return_value = "Test clipboard"
        
        server._system_probe = mock_system_probe
        
        return server
    
    @pytest.mark.asyncio
    async def test_query_knowledge_graph_with_mock(self, server_with_mock):
        """测试知识图谱查询（使用 Mock）"""
        request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "query_knowledge_graph",
                "arguments": {
                    "query": "Test",
                    "query_type": "find_entity"
                }
            }
        }
        
        response = await server_with_mock.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 11
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["count"] == 1
        assert content["entities"][0]["name"] == "Test Entity"
    
    @pytest.mark.asyncio
    async def test_search_memory_with_mock(self, server_with_mock):
        """测试记忆搜索（使用 Mock）"""
        request = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "search_memory",
                "arguments": {
                    "query": "Test",
                    "limit": 5
                }
            }
        }
        
        response = await server_with_mock.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 12
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["count"] == 1
        assert content["memories"][0]["content"] == "Test memory"
    
    @pytest.mark.asyncio
    async def test_get_broker_status_with_mock(self, server_with_mock):
        """测试 Broker 状态（使用 Mock）"""
        request = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "get_broker_status",
                "arguments": {
                    "include_details": True
                }
            }
        }
        
        response = await server_with_mock.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 13
        assert "result" in response
        
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["success"] is True
        assert content["broker_alive"] is True
        assert content["frontmost_app"] == "VSCode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])