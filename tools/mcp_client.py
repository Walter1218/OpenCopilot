"""
MCP Client 实现

Model Context Protocol (MCP) 客户端桥接层。
让 OpenCopilot Agent 能够调用外部 MCP 工具。

MCP 协议核心: JSON-RPC over stdio/sse
- stdio: 启动本地进程，通过标准输入/输出通信
- sse: HTTP SSE 长连接（远程 MCP Server）

配置格式: 与 Claude Desktop / Cursor 兼容的 mcp_servers.json
"""

import os
import json
import asyncio
import subprocess
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MCPTransport(str, Enum):
    """MCP 传输方式"""
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: MCPTransport = MCPTransport.STDIO
    url: Optional[str] = None  # SSE 模式使用


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass
class MCPToolResult:
    """MCP 工具调用结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    server_name: str = ""


class MCPClient:
    """MCP 客户端
    
    管理多个 MCP Server 连接，提供统一的工具调用接口。
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化 MCP 客户端
        
        Args:
            config_path: 配置文件路径，默认 ~/.asu_copilot/mcp_servers.json
        """
        self.config_path = config_path or os.path.expanduser("~/.asu_copilot/mcp_servers.json")
        self.servers: Dict[str, subprocess.Popen] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.server_tools: Dict[str, List[MCPTool]] = {}
        self._initialized = False
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载 MCP Server 配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                mcp_servers = config.get("mcpServers", {})
                
                for name, server_config in mcp_servers.items():
                    self.server_configs[name] = MCPServerConfig(
                        name=name,
                        command=server_config.get("command", ""),
                        args=server_config.get("args", []),
                        env=server_config.get("env", {}),
                        transport=MCPTransport(server_config.get("transport", "stdio")),
                        url=server_config.get("url")
                    )
                
                logger.info(f"已加载 {len(self.server_configs)} 个 MCP Server 配置")
            else:
                logger.info(f"MCP 配置文件不存在: {self.config_path}")
                
        except Exception as e:
            logger.error(f"加载 MCP 配置失败: {e}")
    
    def reload_config(self):
        """重新加载配置"""
        self.server_configs.clear()
        self._load_config()
    
    def list_servers(self) -> List[str]:
        """列出所有配置的 MCP Server
        
        Returns:
            List[str]: Server 名称列表
        """
        return list(self.server_configs.keys())
    
    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """获取 Server 配置
        
        Args:
            server_name: Server 名称
            
        Returns:
            Optional[MCPServerConfig]: Server 配置
        """
        return self.server_configs.get(server_name)
    
    async def start_server(self, server_name: str) -> bool:
        """启动 MCP Server
        
        Args:
            server_name: Server 名称
            
        Returns:
            bool: 是否启动成功
        """
        if server_name in self.servers:
            # 检查进程是否还在运行
            proc = self.servers[server_name]
            if proc.poll() is None:
                return True
            else:
                del self.servers[server_name]
        
        config = self.server_configs.get(server_name)
        if not config:
            logger.error(f"MCP Server '{server_name}' 未配置")
            return False
        
        try:
            if config.transport == MCPTransport.STDIO:
                # 启动 stdio 模式的 MCP Server
                cmd = [config.command] + config.args
                
                env = os.environ.copy()
                env.update(config.env)
                
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1
                )
                
                self.servers[server_name] = proc
                
                # 发送 initialize 请求
                init_result = await self._send_request(server_name, "initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "OpenCopilot",
                        "version": "2.0.0"
                    }
                })
                
                if init_result:
                    # 发送 initialized 通知
                    await self._send_notification(server_name, "notifications/initialized", {})
                    logger.info(f"✅ MCP Server '{server_name}' 已启动")
                    return True
                else:
                    logger.error(f"❌ MCP Server '{server_name}' 初始化失败")
                    await self.stop_server(server_name)
                    return False
                    
            elif config.transport == MCPTransport.SSE:
                # SSE 模式暂不实现
                logger.warning(f"SSE 模式暂不支持: {server_name}")
                return False
                
        except Exception as e:
            logger.error(f"启动 MCP Server '{server_name}' 失败: {e}")
            return False
    
    async def stop_server(self, server_name: str):
        """停止 MCP Server
        
        Args:
            server_name: Server 名称
        """
        if server_name in self.servers:
            proc = self.servers[server_name]
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                logger.warning(f"停止 MCP Server '{server_name}' 时出错: {e}")
                proc.kill()
            
            del self.servers[server_name]
            logger.info(f"已停止 MCP Server: {server_name}")
    
    async def stop_all_servers(self):
        """停止所有 MCP Server"""
        for server_name in list(self.servers.keys()):
            await self.stop_server(server_name)
    
    async def _send_request(self, server_name: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送 JSON-RPC 请求
        
        Args:
            server_name: Server 名称
            method: 方法名
            params: 参数
            
        Returns:
            Optional[Dict[str, Any]]: 响应结果
        """
        if server_name not in self.servers:
            logger.error(f"MCP Server '{server_name}' 未启动")
            return None
        
        proc = self.servers[server_name]
        
        # 构建 JSON-RPC 请求
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            # 发送请求
            request_str = json.dumps(request) + "\n"
            proc.stdin.write(request_str)
            proc.stdin.flush()
            
            # 读取响应
            response_str = proc.stdout.readline()
            if response_str:
                response = json.loads(response_str)
                
                if "error" in response:
                    logger.error(f"MCP 错误: {response['error']}")
                    return None
                
                return response.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"发送 MCP 请求失败: {e}")
            return None
    
    async def _send_notification(self, server_name: str, method: str, params: Dict[str, Any]):
        """发送 JSON-RPC 通知（无需响应）
        
        Args:
            server_name: Server 名称
            method: 方法名
            params: 参数
        """
        if server_name not in self.servers:
            return
        
        proc = self.servers[server_name]
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        try:
            notification_str = json.dumps(notification) + "\n"
            proc.stdin.write(notification_str)
            proc.stdin.flush()
        except Exception as e:
            logger.error(f"发送 MCP 通知失败: {e}")
    
    async def get_server_tools(self, server_name: str) -> List[MCPTool]:
        """获取 Server 的工具列表
        
        Args:
            server_name: Server 名称
            
        Returns:
            List[MCPTool]: 工具列表
        """
        # 确保 Server 已启动
        if server_name not in self.servers:
            success = await self.start_server(server_name)
            if not success:
                return []
        
        # 如果已缓存，直接返回
        if server_name in self.server_tools:
            return self.server_tools[server_name]
        
        # 获取工具列表
        result = await self._send_request(server_name, "tools/list", {})
        
        if result and "tools" in result:
            tools = []
            for tool_data in result["tools"]:
                tool = MCPTool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=server_name
                )
                tools.append(tool)
            
            self.server_tools[server_name] = tools
            logger.info(f"从 '{server_name}' 获取 {len(tools)} 个工具")
            return tools
        
        return []
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """调用 MCP 工具
        
        Args:
            server_name: Server 名称
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            MCPToolResult: 调用结果
        """
        # 确保 Server 已启动
        if server_name not in self.servers:
            success = await self.start_server(server_name)
            if not success:
                return MCPToolResult(
                    success=False,
                    error=f"无法启动 MCP Server: {server_name}",
                    tool_name=tool_name,
                    server_name=server_name
                )
        
        # 调用工具
        result = await self._send_request(server_name, "tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if result:
            return MCPToolResult(
                success=True,
                result=result,
                tool_name=tool_name,
                server_name=server_name
            )
        else:
            return MCPToolResult(
                success=False,
                error=f"工具调用失败: {server_name}/{tool_name}",
                tool_name=tool_name,
                server_name=server_name
            )
    
    async def get_all_tools(self) -> List[MCPTool]:
        """获取所有 Server 的工具列表
        
        Returns:
            List[MCPTool]: 所有工具列表
        """
        all_tools = []
        
        for server_name in self.server_configs.keys():
            tools = await self.get_server_tools(server_name)
            all_tools.extend(tools)
        
        return all_tools
    
    def get_status(self) -> Dict[str, Any]:
        """获取 MCP 客户端状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "config_path": self.config_path,
            "configured_servers": list(self.server_configs.keys()),
            "running_servers": list(self.servers.keys()),
            "tools_cache": {
                name: len(tools) for name, tools in self.server_tools.items()
            }
        }


# 全局 MCP 客户端实例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例
    
    Returns:
        MCPClient: MCP 客户端实例
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def cleanup_mcp_client():
    """清理 MCP 客户端"""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.stop_all_servers()
        _mcp_client = None


# 测试代码
if __name__ == "__main__":
    async def test_mcp_client():
        """测试 MCP 客户端"""
        client = MCPClient()
        
        print("MCP 客户端状态:")
        print(json.dumps(client.get_status(), indent=2))
        
        print("\n配置的 Server:")
        for server_name in client.list_servers():
            config = client.get_server_config(server_name)
            print(f"  - {server_name}: {config.command} {' '.join(config.args)}")
    
    asyncio.run(test_mcp_client())
