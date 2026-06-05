"""
MCP Server 实现

Model Context Protocol (MCP) 服务器。
让外部工具（如 Claude Desktop、Cursor）能够查询 OpenCopilot 的能力。

暴露能力：
1. 知识图谱查询（264 实体 + 166 关系）
2. 伴生记忆（L2+L3）
3. Broker 系统探针
4. 对话历史搜索

通信方式：stdio JSON-RPC（安全性优先，不开放网络端口）
"""

import os
import sys
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)


class MCPServer:
    """MCP Server 实现
    
    通过 stdio 接收 JSON-RPC 请求，暴露 OpenCopilot 的能力。
    """
    
    def __init__(self):
        """初始化 MCP Server"""
        self.tools: List[MCPTool] = []
        self._knowledge_graph = None
        self._memory_system = None
        self._system_probe = None
        
        # 注册工具
        self._register_tools()
        
        # 初始化组件
        self._init_components()
    
    def _register_tools(self):
        """注册所有可用工具"""
        self.tools = [
            MCPTool(
                name="query_knowledge_graph",
                description="查询知识图谱中的实体和关系。支持按名称查找实体、查找相关实体、查找路径等。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询内容，如实体名称或关键词"
                        },
                        "query_type": {
                            "type": "string",
                            "enum": ["find_entity", "find_related", "find_path", "search"],
                            "description": "查询类型：find_entity（查找实体）、find_related（查找相关实体）、find_path（查找路径）、search（全文搜索）",
                            "default": "search"
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["module", "api", "component", "file", "class", "function", "concept"],
                            "description": "实体类型过滤（可选）"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "最大搜索深度（用于 find_related）",
                            "default": 2
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="search_memory",
                description="搜索 OpenCopilot 的伴生记忆（L2+L3 层）。支持按内容、标签、类型搜索。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "memory_type": {
                            "type": "string",
                            "enum": ["short_term", "long_term", "episodic", "semantic", "procedural"],
                            "description": "记忆类型过滤（可选）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="get_broker_status",
                description="获取 Broker 系统状态，包括前台应用、剪贴板、系统信息等。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_details": {
                            "type": "boolean",
                            "description": "是否包含详细信息",
                            "default": False
                        }
                    }
                }
            ),
            MCPTool(
                name="search_conversation",
                description="搜索历史对话记录。支持按内容、时间范围搜索。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="get_system_info",
                description="获取 OpenCopilot 系统信息，包括版本、模块状态、API 覆盖率等。",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    def _init_components(self):
        """初始化组件"""
        try:
            # 尝试导入知识图谱
            from knowledge_graph.models import KnowledgeGraph
            from knowledge_graph.query import QueryEngine
            
            # 加载知识图谱
            kg_path = os.path.join(os.path.dirname(__file__), '..', 'knowledge_graph', 'opencopilot_knowledge_graph.json')
            if os.path.exists(kg_path):
                self._knowledge_graph = KnowledgeGraph.load_from_file(kg_path)
                self._query_engine = QueryEngine(self._knowledge_graph)
                logger.info("✅ 知识图谱加载成功")
            else:
                logger.warning(f"⚠️ 知识图谱文件不存在: {kg_path}")
        except ImportError as e:
            logger.warning(f"⚠️ 知识图谱模块导入失败: {e}")
        
        try:
            # 尝试导入记忆系统
            from memory_system.core import MemoryManager
            
            self._memory_system = MemoryManager()
            logger.info("✅ 记忆系统初始化成功")
        except ImportError as e:
            logger.warning(f"⚠️ 记忆系统模块导入失败: {e}")
        
        try:
            # 尝试导入系统探针
            from system_probe_client import SystemProbeClient
            
            self._system_probe = SystemProbeClient()
            logger.info("✅ 系统探针初始化成功")
        except ImportError as e:
            logger.warning(f"⚠️ 系统探针模块导入失败: {e}")
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具的 schema（用于 MCP Client）"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools
        ]
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 JSON-RPC 请求
        
        Args:
            request: JSON-RPC 请求
            
        Returns:
            JSON-RPC 响应
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_tools_list()
            elif method == "tools/call":
                result = await self._handle_tools_call(params)
            elif method == "ping":
                result = {"pong": True}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理初始化请求"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "opencopilot-mcp-server",
                "version": "1.0.0"
            }
        }
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "tools": self.get_tools_schema()
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # 查找工具
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"工具不存在: {tool_name}")
        
        # 调用对应的处理函数
        if tool_name == "query_knowledge_graph":
            result = await self._query_knowledge_graph(**arguments)
        elif tool_name == "search_memory":
            result = await self._search_memory(**arguments)
        elif tool_name == "get_broker_status":
            result = await self._get_broker_status(**arguments)
        elif tool_name == "search_conversation":
            result = await self._search_conversation(**arguments)
        elif tool_name == "get_system_info":
            result = await self._get_system_info(**arguments)
        else:
            raise ValueError(f"工具未实现: {tool_name}")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ]
        }
    
    async def _query_knowledge_graph(
        self,
        query: str,
        query_type: str = "search",
        entity_type: Optional[str] = None,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """查询知识图谱"""
        if not self._query_engine:
            return {
                "success": False,
                "error": "知识图谱未加载",
                "entities": [],
                "relations": []
            }
        
        try:
            from knowledge_graph.models import EntityType
            
            # 转换实体类型
            et = None
            if entity_type:
                type_map = {
                    "module": EntityType.MODULE,
                    "api": EntityType.API,
                    "component": EntityType.COMPONENT,
                    "file": EntityType.FILE,
                    "class": EntityType.CLASS,
                    "function": EntityType.FUNCTION,
                    "concept": EntityType.CONCEPT
                }
                et = type_map.get(entity_type)
            
            if query_type == "find_entity":
                entities = self._query_engine.find_entity(query, et)
                return {
                    "success": True,
                    "query": query,
                    "query_type": query_type,
                    "entities": [
                        {
                            "id": e.entity_id,
                            "name": e.name,
                            "type": e.entity_type.value,
                            "description": e.description,
                            "properties": e.properties
                        }
                        for e in entities
                    ],
                    "count": len(entities)
                }
            
            elif query_type == "find_related":
                # 先查找实体
                entities = self._query_engine.find_entity(query, et)
                if not entities:
                    return {
                        "success": True,
                        "query": query,
                        "query_type": query_type,
                        "entities": [],
                        "relations": [],
                        "message": f"未找到实体: {query}"
                    }
                
                # 查找相关实体
                entity_id = entities[0].entity_id
                result = self._query_engine.find_related_entities(entity_id, max_depth=max_depth)
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": query_type,
                    "root_entity": {
                        "id": entities[0].entity_id,
                        "name": entities[0].name,
                        "type": entities[0].entity_type.value
                    },
                    "related_entities": [
                        {
                            "id": e.entity_id,
                            "name": e.name,
                            "type": e.entity_type.value,
                            "description": e.description
                        }
                        for e in result.get("entities", [])
                    ],
                    "relations": [
                        {
                            "source": r.source_id,
                            "target": r.target_id,
                            "type": r.relation_type.value,
                            "description": r.description
                        }
                        for r in result.get("relations", [])
                    ],
                    "count": len(result.get("entities", []))
                }
            
            else:  # search
                # 全文搜索
                results = []
                for entity in self._knowledge_graph.entities.values():
                    if et and entity.entity_type != et:
                        continue
                    
                    if (query.lower() in entity.name.lower() or
                        query.lower() in entity.description.lower()):
                        results.append({
                            "id": entity.entity_id,
                            "name": entity.name,
                            "type": entity.entity_type.value,
                            "description": entity.description
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "query_type": query_type,
                    "entities": results[:20],  # 限制返回数量
                    "count": len(results)
                }
        
        except Exception as e:
            logger.error(f"查询知识图谱失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "entities": [],
                "relations": []
            }
    
    async def _search_memory(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索记忆"""
        if not self._memory_system:
            return {
                "success": False,
                "error": "记忆系统未初始化",
                "memories": []
            }
        
        try:
            from memory_system.core import MemoryType
            
            # 转换记忆类型
            mt = None
            if memory_type:
                type_map = {
                    "short_term": MemoryType.SHORT_TERM,
                    "long_term": MemoryType.LONG_TERM,
                    "episodic": MemoryType.EPISODIC,
                    "semantic": MemoryType.SEMANTIC,
                    "procedural": MemoryType.PROCEDURAL
                }
                mt = type_map.get(memory_type)
            
            # 搜索记忆
            memories = self._memory_system.retrieve_memories(
                query=query,
                limit=limit,
                memory_types=[mt] if mt else None
            )
            
            return {
                "success": True,
                "query": query,
                "memories": [
                    {
                        "id": m.memory_id,
                        "content": m.content,
                        "type": m.memory_type.value,
                        "importance": m.importance,
                        "tags": m.tags,
                        "created_at": m.created_at,
                        "last_accessed": m.last_accessed
                    }
                    for m in memories
                ],
                "count": len(memories)
            }
        
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "memories": []
            }
    
    async def _get_broker_status(
        self,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """获取 Broker 状态"""
        if not self._system_probe:
            return {
                "success": False,
                "error": "系统探针未初始化",
                "broker_alive": False
            }
        
        try:
            broker_alive = self._system_probe.is_broker_alive()
            
            result = {
                "success": True,
                "broker_alive": broker_alive
            }
            
            if include_details and broker_alive:
                # 获取详细信息
                frontmost_app = self._system_probe.get_frontmost_app()
                result["frontmost_app"] = frontmost_app
                
                # 尝试获取其他信息
                try:
                    clipboard = self._system_probe.get_clipboard()
                    result["clipboard_preview"] = clipboard[:100] if clipboard else ""
                except Exception:
                    pass
            
            return result
        
        except Exception as e:
            logger.error(f"获取 Broker 状态失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "broker_alive": False
            }
    
    async def _search_conversation(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索对话历史"""
        try:
            # 使用 session_manager 搜索对话历史
            from smart_copilot_api import session_manager
            
            results = []
            all_sessions = getattr(session_manager, '_sessions', {})
            
            for sid, session in all_sessions.items():
                messages = getattr(session, 'messages', []) or getattr(session, 'get_messages', lambda: [])()
                for msg in messages:
                    content = getattr(msg, 'content', '') or str(msg)
                    if query.lower() in content.lower():
                        results.append({
                            "session_id": sid,
                            "role": getattr(msg, 'role', 'user'),
                            "content": content[:200],
                            "timestamp": str(getattr(msg, 'timestamp', ''))
                        })
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
            
            return {
                "success": True,
                "query": query,
                "conversations": results,
                "count": len(results)
            }
        
        except ImportError:
            return {
                "success": True,
                "query": query,
                "conversations": [],
                "count": 0,
                "message": "会话管理器不可用，无法搜索对话历史"
            }
        
        except Exception as e:
            logger.error(f"搜索对话失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "conversations": []
            }
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            # 获取版本信息
            version = "1.0.0"
            
            # 获取模块状态
            modules = []
            
            # 检查知识图谱
            if self._knowledge_graph:
                kg_stats = {
                    "name": "knowledge_graph",
                    "status": "loaded",
                    "entities": len(self._knowledge_graph.entities),
                    "relations": len(self._knowledge_graph.relations)
                }
                modules.append(kg_stats)
            
            # 检查记忆系统
            if self._memory_system:
                memory_stats = {
                    "name": "memory_system",
                    "status": "initialized"
                }
                modules.append(memory_stats)
            
            # 检查系统探针
            if self._system_probe:
                probe_stats = {
                    "name": "system_probe",
                    "status": "initialized",
                    "broker_alive": self._system_probe.is_broker_alive()
                }
                modules.append(probe_stats)
            
            return {
                "success": True,
                "version": version,
                "modules": modules,
                "tools_count": len(self.tools),
                "available_tools": [t.name for t in self.tools]
            }
        
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


async def run_stdio_server():
    """运行 stdio MCP Server"""
    server = MCPServer()
    
    logger.info("MCP Server 启动，等待 stdio 请求...")
    
    # 读取 stdin
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        try:
            # 读取一行 JSON-RPC 请求
            line = await reader.readline()
            if not line:
                break
            
            line = line.decode('utf-8').strip()
            if not line:
                continue
            
            # 解析请求
            request = json.loads(line)
            
            # 处理请求
            response = await server.handle_request(request)
            
            # 发送响应
            response_str = json.dumps(response, ensure_ascii=False)
            sys.stdout.write(response_str + '\n')
            sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
        except Exception as e:
            logger.error(f"处理请求错误: {e}", exc_info=True)


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()