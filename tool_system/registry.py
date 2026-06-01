# tool_system/registry.py

"""
工具注册表

负责管理工具定义的注册、更新、删除和查询。
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pathlib import Path

from .models import (
    ToolDefinition, ToolType, ToolCategory,
    ToolParameter, ToolStatus
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表
    
    职责：
    1. 管理工具定义的注册、更新、删除
    2. 支持多种工具类型的注册
    3. 提供工具发现和查询能力
    4. 持久化工具配置
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化工具注册表
        
        Args:
            storage_path: 工具配置存储路径（JSON 文件）
        """
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_handlers: Dict[str, Callable] = {}  # 工具处理函数
        self._storage_path = storage_path
        self._status_map: Dict[str, ToolStatus] = {}
        
        # 加载持久化的工具配置
        if storage_path and os.path.exists(storage_path):
            self._load_from_storage()
    
    def register(self, definition: ToolDefinition, handler: Callable) -> str:
        """
        注册工具
        
        Args:
            definition: 工具定义
            handler: 工具处理函数（同步或异步）
            
        Returns:
            str: 工具 ID
        """
        # 验证工具定义
        self._validate_definition(definition)
        
        # 注册
        self._tools[definition.tool_id] = definition
        self._tool_handlers[definition.tool_id] = handler
        self._status_map[definition.tool_id] = ToolStatus.AVAILABLE
        
        logger.info(f"Registered tool: {definition.tool_id} ({definition.name})")
        
        # 持久化
        if self._storage_path:
            self._save_to_storage()
        
        return definition.tool_id
    
    def unregister(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具 ID
            
        Returns:
            bool: 是否成功
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            del self._tool_handlers[tool_id]
            del self._status_map[tool_id]
            
            logger.info(f"Unregistered tool: {tool_id}")
            
            if self._storage_path:
                self._save_to_storage()
            
            return True
        return False
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(tool_id)
    
    def get_handler(self, tool_id: str) -> Optional[Callable]:
        """获取工具处理函数"""
        return self._tool_handlers.get(tool_id)
    
    def get_status(self, tool_id: str) -> Optional[ToolStatus]:
        """获取工具状态"""
        return self._status_map.get(tool_id)
    
    def set_status(self, tool_id: str, status: ToolStatus) -> None:
        """设置工具状态"""
        if tool_id in self._tools:
            self._status_map[tool_id] = status
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tool_type: Optional[ToolType] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ToolStatus] = None
    ) -> List[ToolDefinition]:
        """
        列出工具（支持过滤）
        
        Args:
            category: 按类别过滤
            tool_type: 按类型过滤
            tags: 按标签过滤（任意匹配）
            status: 按状态过滤
            
        Returns:
            List[ToolDefinition]: 工具定义列表
        """
        result = []
        
        for tool_id, definition in self._tools.items():
            # 应用过滤条件
            if category and definition.category != category:
                continue
            if tool_type and definition.tool_type != tool_type:
                continue
            if tags and not any(tag in definition.tags for tag in tags):
                continue
            if status and self._status_map.get(tool_id) != status:
                continue
            
            result.append(definition)
        
        return result
    
    def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[ToolDefinition]: 匹配的工具定义列表
        """
        query_lower = query.lower()
        result = []
        
        for definition in self._tools.values():
            # 搜索名称、描述、标签
            if (query_lower in definition.name.lower() or
                query_lower in definition.description.lower() or
                any(query_lower in tag.lower() for tag in definition.tags)):
                result.append(definition)
        
        return result
    
    def find_by_capability(self, capability: str) -> List[ToolDefinition]:
        """
        根据能力查找工具
        
        Args:
            capability: 能力描述（如 "code_review", "file_read"）
            
        Returns:
            List[ToolDefinition]: 匹配的工具定义列表
        """
        capability_lower = capability.lower()
        result = []
        
        for definition in self._tools.values():
            # 检查标签和元数据中的能力
            if (any(capability_lower in tag.lower() for tag in definition.tags) or
                capability_lower in definition.metadata.get("capabilities", [])):
                result.append(definition)
        
        return result
    
    def _validate_definition(self, definition: ToolDefinition) -> None:
        """验证工具定义"""
        if not definition.tool_id:
            raise ValueError("Tool ID is required")
        if not definition.name:
            raise ValueError("Tool name is required")
        if not definition.description:
            raise ValueError("Tool description is required")
        
        # 检查 ID 唯一性
        if definition.tool_id in self._tools:
            logger.warning(f"Tool {definition.tool_id} already exists, will be overwritten")
    
    def _load_from_storage(self) -> None:
        """从存储加载工具配置"""
        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for tool_data in data.get("tools", []):
                definition = ToolDefinition(**tool_data)
                self._tools[definition.tool_id] = definition
                self._status_map[definition.tool_id] = ToolStatus.AVAILABLE
            
            logger.info(f"Loaded {len(self._tools)} tools from storage")
        except Exception as e:
            logger.error(f"Failed to load tools from storage: {e}")
    
    def _save_to_storage(self) -> None:
        """保存工具配置到存储"""
        try:
            data = {
                "tools": [
                    {
                        "tool_id": d.tool_id,
                        "name": d.name,
                        "description": d.description,
                        "tool_type": d.tool_type.value,
                        "category": d.category.value,
                        "version": d.version,
                        "author": d.author,
                        "parameters": [
                            {
                                "name": p.name,
                                "type": p.type,
                                "description": p.description,
                                "required": p.required,
                                "default": p.default
                            }
                            for p in d.parameters
                        ],
                        "output_schema": d.output_schema,
                        "requires_approval": d.requires_approval,
                        "timeout": d.timeout,
                        "retry_count": d.retry_count,
                        "tags": d.tags,
                        "metadata": d.metadata
                    }
                    for d in self._tools.values()
                ]
            }
            
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self._tools)} tools to storage")
        except Exception as e:
            logger.error(f"Failed to save tools to storage: {e}")
