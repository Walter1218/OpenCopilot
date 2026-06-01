# tool_system/integration.py

"""
工具系统集成器

负责将工具系统集成到现有的 OpenCopilot 架构中。
"""

import logging
from typing import Optional

from .registry import ToolRegistry
from .executor import ToolExecutor
from .adapters.skill_adapter import SkillAdapter
from .api import create_tool_router

# 导入现有系统
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from skill_architecture.registry import SkillRegistry as ExistingSkillRegistry
from skill_architecture.executor import SkillExecutor as ExistingSkillExecutor
from skill_architecture.discovery import SkillDiscovery

logger = logging.getLogger(__name__)


class ToolSystemIntegration:
    """工具系统集成器
    
    负责将工具系统集成到现有的 OpenCopilot 架构中
    """
    
    def __init__(
        self,
        tool_storage_path: Optional[str] = None
    ):
        # 创建工具系统组件
        self.tool_registry = ToolRegistry(storage_path=tool_storage_path)
        self.tool_executor = ToolExecutor(registry=self.tool_registry)
        
        # 获取现有的 Skill 系统
        self.skill_registry = ExistingSkillRegistry()
        self.skill_discovery = SkillDiscovery()
        
        # 创建 Skill 适配器
        self.skill_adapter = SkillAdapter(
            tool_registry=self.tool_registry,
            skill_registry=self.skill_registry
        )
        
        # API 路由器
        self.router = None
    
    async def initialize(self) -> None:
        """初始化工具系统"""
        logger.info("Initializing Tool System...")
        
        # 1. 自动发现并注册 Skill
        self.skill_discovery.auto_discover("skill_architecture")
        
        # 2. 将 Skill 注册为工具
        skill_count = self.skill_adapter.register_all_skills()
        logger.info(f"Registered {skill_count} skills as tools")
        
        # 3. 注册内置工具（如文件操作、代码执行等）
        await self._register_builtin_tools()
        
        # 4. 创建 API 路由器
        self.router = create_tool_router(
            self.tool_registry,
            self.tool_executor
        )
        
        logger.info(f"Tool System initialized with {len(self.tool_registry.list_tools())} tools")
    
    async def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        from .models import (
            ToolDefinition, ToolType, ToolCategory,
            ToolParameter
        )
        
        # 示例：注册文件读取工具
        file_read_tool = ToolDefinition(
            tool_id="builtin_file_read",
            name="file_read",
            description="读取文件内容",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="文件路径",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="文件编码",
                    required=False,
                    default="utf-8"
                )
            ],
            tags=["file", "read", "builtin"],
            metadata={"builtin": True}
        )
        
        async def file_read_handler(file_path: str, encoding: str = "utf-8") -> str:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        
        self.tool_registry.register(file_read_tool, file_read_handler)
        
        # 更多内置工具...
    
    def get_api_router(self):
        """获取 API 路由器"""
        return self.router
    
    async def shutdown(self) -> None:
        """关闭工具系统"""
        logger.info("Shutting down Tool System...")
        # 清理资源
