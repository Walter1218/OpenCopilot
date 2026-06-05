"""
PersonaSkill - 人设管理技能
封装 PersonaManager 为人设管理相关的技能
"""

import os
from typing import Dict, Any, Optional, List
from .base import BaseSkill
from .models import (
    SkillMetadata, SkillContext, SkillResult,
    SkillStatus, ExecutionMode
)


class PersonaSkill(BaseSkill):
    """人设管理技能
    
    封装人设管理相关的功能，提供统一的技能接口。
    支持人设列表、获取、保存、删除等操作。
    """
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="persona_skill",
            description="人设管理技能，支持人设的列表、获取、保存、删除等操作",
            version="1.0.0",
            author="OpenCopilot",
            category="persona",
            intents=[
                "persona",
                "persona_list",
                "persona_get",
                "persona_save",
                "persona_delete",
                "角色管理",
                "人设管理"
            ],
            tags=["persona", "角色", "人设", "管理"],
            dependencies=[],
            config_schema={
                "base_dir": "personas",
                "built_in_personas": ["default", "code", "translate", "polish", "custom", "revision"]
            }
        )
    
    async def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 检查意图
        if context.intent in self.metadata.intents:
            return 0.9
        
        # 检查输入数据
        if "action" in context.input_data:
            action = context.input_data["action"]
            if action in ["list", "get", "save", "delete"]:
                return 0.8
        
        # 检查内容类型
        content = context.input_data.get("content", "")
        if isinstance(content, str):
            content_lower = content.lower()
            persona_keywords = ["人设", "角色", "persona", "character", "profile"]
            if any(keyword in content_lower for keyword in persona_keywords):
                return 0.7
        
        return 0.0
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行人设管理操作
        
        Args:
            context: 执行上下文，包含:
                - action: 操作类型 (list/get/save/delete)
                - name: 人设名称 (get/save/delete时需要)
                - content: 人设内容 (save时需要)
        
        Returns:
            SkillResult: 执行结果
        """
        try:
            action = context.input_data.get("action", "list")
            
            # 根据操作类型分发
            if action == "list":
                return await self._list_personas(context)
            elif action == "get":
                return await self._get_persona(context)
            elif action == "save":
                return await self._save_persona(context)
            elif action == "delete":
                return await self._delete_persona(context)
            else:
                # 默认列出所有人设
                return await self._list_personas(context)
                
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"人设管理操作失败: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _list_personas(self, context: SkillContext) -> SkillResult:
        """列出所有人设
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 人设列表
        """
        try:
            from persona_manager import PersonaManager
            
            manager = PersonaManager()
            personas = manager.list_personas()
            
            # 分类人设
            built_in = []
            custom = []
            for persona in personas:
                base_name = os.path.basename(persona)
                if base_name in manager.built_in_personas:
                    built_in.append(persona)
                else:
                    custom.append(persona)
            
            return SkillResult(
                success=True,
                data={
                    "personas": personas,
                    "built_in": built_in,
                    "custom": custom,
                    "total": len(personas)
                },
                status=SkillStatus.COMPLETED
            )
                
        except ImportError:
            return SkillResult(
                success=False,
                data={},
                error="需要 persona_manager 模块",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"列出人设失败: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _get_persona(self, context: SkillContext) -> SkillResult:
        """获取指定人设
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 人设内容
        """
        name = context.input_data.get("name", "")
        
        if not name:
            return SkillResult(
                success=False,
                data={},
                error="缺少人设名称",
                status=SkillStatus.FAILED
            )
        
        try:
            from persona_manager import PersonaManager
            
            manager = PersonaManager()
            content = manager.get_persona(name)
            
            if content is None:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"人设 '{name}' 不存在",
                    status=SkillStatus.FAILED
                )
            
            # 判断是否为内置人设
            base_name = os.path.basename(name)
            is_built_in = base_name in manager.built_in_personas
            
            return SkillResult(
                success=True,
                data={
                    "name": name,
                    "content": content,
                    "is_built_in": is_built_in,
                    "length": len(content)
                },
                status=SkillStatus.COMPLETED
            )
                
        except ImportError:
            return SkillResult(
                success=False,
                data={},
                error="需要 persona_manager 模块",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"获取人设失败: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _save_persona(self, context: SkillContext) -> SkillResult:
        """保存人设
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 保存结果
        """
        name = context.input_data.get("name", "")
        content = context.input_data.get("content", "")
        
        if not name:
            return SkillResult(
                success=False,
                data={},
                error="缺少人设名称",
                status=SkillStatus.FAILED
            )
        
        if not content:
            return SkillResult(
                success=False,
                data={},
                error="缺少人设内容",
                status=SkillStatus.FAILED
            )
        
        try:
            from persona_manager import PersonaManager
            
            manager = PersonaManager()
            success = manager.save_persona(name, content)
            
            if success:
                # 判断是否为内置人设
                base_name = os.path.basename(name)
                is_built_in = base_name in manager.built_in_personas
                
                return SkillResult(
                    success=True,
                    data={
                        "name": name,
                        "is_built_in": is_built_in,
                        "action": "updated" if is_built_in else "created",
                        "length": len(content)
                    },
                    status=SkillStatus.COMPLETED
                )
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error="保存人设失败",
                    status=SkillStatus.FAILED
                )
                
        except ImportError:
            return SkillResult(
                success=False,
                data={},
                error="需要 persona_manager 模块",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"保存人设失败: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _delete_persona(self, context: SkillContext) -> SkillResult:
        """删除人设
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 删除结果
        """
        name = context.input_data.get("name", "")
        
        if not name:
            return SkillResult(
                success=False,
                data={},
                error="缺少人设名称",
                status=SkillStatus.FAILED
            )
        
        try:
            from persona_manager import PersonaManager
            
            manager = PersonaManager()
            success, message = manager.delete_persona(name)
            
            if success:
                return SkillResult(
                    success=True,
                    data={
                        "name": name,
                        "action": "deleted",
                        "message": message
                    },
                    status=SkillStatus.COMPLETED
                )
            else:
                return SkillResult(
                    success=False,
                    data={
                        "name": name,
                        "message": message
                    },
                    error=message,
                    status=SkillStatus.FAILED
                )
                
        except ImportError:
            return SkillResult(
                success=False,
                data={},
                error="需要 persona_manager 模块",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"删除人设失败: {str(e)}",
                status=SkillStatus.FAILED
            )
