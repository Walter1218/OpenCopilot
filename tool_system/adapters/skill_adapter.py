# tool_system/adapters/skill_adapter.py

"""
Skill 适配器

将现有的 Skill 注册为工具系统中的工具。
"""

from typing import Dict, Any, Optional
import uuid
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models import (
    ToolDefinition, ToolType, ToolCategory,
    ToolParameter, ToolCall, ToolResult
)
from ..registry import ToolRegistry

# 导入现有 Skill 架构
from skill_architecture.models import SkillContext, SkillMetadata
from skill_architecture.base import BaseSkill
from skill_architecture.registry import SkillRegistry


class SkillAdapter:
    """Skill 适配器
    
    将现有的 Skill 注册为工具系统中的工具
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry
    ):
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
    
    def register_all_skills(self) -> int:
        """
        注册所有已注册的 Skill 为工具
        
        Returns:
            int: 注册的工具数量
        """
        count = 0
        
        for skill_name in self._skill_registry.list_skills():
            skill = self._skill_registry.get_skill(skill_name)
            if skill:
                self._register_skill(skill)
                count += 1
        
        return count
    
    def _register_skill(self, skill: BaseSkill) -> None:
        """注册单个 Skill"""
        metadata = skill.metadata
        
        # 创建工具定义
        definition = self._skill_to_tool_definition(metadata)
        
        # 创建处理函数
        handler = self._create_skill_handler(skill)
        
        # 注册到工具系统
        self._tool_registry.register(definition, handler)
    
    def _skill_to_tool_definition(self, metadata: SkillMetadata) -> ToolDefinition:
        """将 Skill 元数据转换为工具定义"""
        # 确定工具类别
        category = self._determine_category(metadata)
        
        # 转换参数
        parameters = self._convert_parameters(metadata.input_schema)
        
        return ToolDefinition(
            tool_id=f"skill_{metadata.name}",
            name=metadata.name,
            description=metadata.description,
            tool_type=ToolType.SKILL,
            category=category,
            version=metadata.version,
            author=metadata.author,
            parameters=parameters,
            output_schema=metadata.output_schema,
            requires_approval=False,  # 内部 Skill 默认不需要审批
            timeout=30.0,
            retry_count=3,
            tags=metadata.tags + ["skill", "internal"],
            metadata={
                "skill_name": metadata.name,
                "intents": metadata.intents,
                "dependencies": metadata.dependencies,
                "capabilities": metadata.tags
            }
        )
    
    def _determine_category(self, metadata: SkillMetadata) -> ToolCategory:
        """确定工具类别"""
        tags_lower = [tag.lower() for tag in metadata.tags]
        
        if any(tag in tags_lower for tag in ["code", "coding", "programming"]):
            return ToolCategory.CODE
        elif any(tag in tags_lower for tag in ["file", "filesystem"]):
            return ToolCategory.FILE
        elif any(tag in tags_lower for tag in ["web", "browser", "search"]):
            return ToolCategory.WEB
        elif any(tag in tags_lower for tag in ["knowledge", "graph"]):
            return ToolCategory.KNOWLEDGE
        elif any(tag in tags_lower for tag in ["system", "admin"]):
            return ToolCategory.SYSTEM
        else:
            return ToolCategory.CUSTOM
    
    def _convert_parameters(self, input_schema: Dict) -> list:
        """将 Skill 输入模式转换为工具参数"""
        parameters = []
        
        if not input_schema:
            return parameters
        
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])
        
        for name, prop in properties.items():
            param = ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required_fields,
                default=prop.get("default"),
                enum=prop.get("enum")
            )
            parameters.append(param)
        
        return parameters
    
    def _create_skill_handler(self, skill: BaseSkill):
        """创建 Skill 处理函数"""
        async def handler(**kwargs) -> Any:
            # 创建 Skill 上下文
            context = SkillContext(
                intent=kwargs.get("intent", "execute"),
                input_data=kwargs,
                config=skill.config
            )
            
            # 执行 Skill
            result = await skill.execute(context)
            
            if result.success:
                return result.data
            else:
                raise Exception(result.error or "Skill execution failed")
        
        return handler
