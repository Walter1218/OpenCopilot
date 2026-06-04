"""
File Skill

封装文件处理工具为 Skill，支持文件读取、写入、格式转换等功能。
"""

import os
import json
from typing import Any, Dict, List, Optional
from .base import BaseSkill
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class FileSkill(BaseSkill):
    """File Skill
    
    封装文件处理工具，提供以下功能：
    - 文件读取：支持文本、docx、pptx、pdf等格式
    - 文件写入：支持文本、docx、pptx等格式
    - 格式转换：支持多种格式之间的转换
    - 目录操作：列出目录内容、创建目录等
    """
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        return SkillMetadata(
            name="file_skill",
            version="1.0.0",
            description="文件处理技能，支持文件读取、写入、格式转换等功能",
            author="OpenCopilot",
            category="file",            tags=["file", "read", "write", "convert", "format"],
            intents=[
                "file_read",
                "file_write",
                "file_convert",
                "file_list",
                "file_delete",
                "read_file",
                "write_file",
                "convert_file"
            ],
            dependencies=[],
            config_schema={},
            input_schema={
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["read", "write", "convert", "list", "delete"],
                    "required": True
                },
                "file_path": {
                    "type": "string",
                    "description": "文件路径",
                    "required": False
                },
                "content": {
                    "type": "string",
                    "description": "文件内容（写入时必填）",
                    "required": False
                },
                "format": {
                    "type": "string",
                    "description": "文件格式",
                    "enum": ["text", "docx", "pptx", "pdf", "md", "txt"],
                    "required": False
                },
                "input_path": {
                    "type": "string",
                    "description": "输入文件路径（转换时必填）",
                    "required": False
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径",
                    "required": False
                },
                "output_format": {
                    "type": "string",
                    "description": "输出格式（转换时必填）",
                    "enum": ["pdf", "docx", "pptx", "txt", "md"],
                    "required": False
                }
            },
            output_schema={
                "success": {
                    "type": "boolean",
                    "description": "操作是否成功"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容（读取时）"
                },
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "error": {
                    "type": "string",
                    "description": "错误信息"
                }
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
            if action in ["read", "write", "convert", "list", "delete"]:
                return 0.8
        
        # 检查内容类型
        content = context.input_data.get("content", "")
        if isinstance(content, str):
            content_lower = content.lower()
            file_keywords = ["文件", "读取", "写入", "转换", "格式", "file", "read", "write", "convert"]
            if any(keyword in content_lower for keyword in file_keywords):
                return 0.7
        
        return 0.0
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行文件操作
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        # 获取操作类型
        action = context.input_data.get("action")
        
        if not action:
            return SkillResult(
                success=False,
                data={},
                error="action is required",
                status=SkillStatus.FAILED
            )
        
        # 根据操作类型分发
        try:
            if action == "read":
                return await self._read_file(context)
            elif action == "write":
                return await self._write_file(context)
            elif action == "convert":
                return await self._convert_file(context)
            elif action == "list":
                return await self._list_directory(context)
            elif action == "delete":
                return await self._delete_file(context)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Unknown action: {action}",
                    status=SkillStatus.FAILED
                )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def _read_file(self, context: SkillContext) -> SkillResult:
        """读取文件
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        file_path = context.input_data.get("file_path")
        file_format = context.input_data.get("format", "text")
        
        if not file_path:
            return SkillResult(
                success=False,
                data={},
                error="file_path is required for read action",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.tools.file_tools import FileReadTool
            
            # 创建工具实例
            tool = FileReadTool()
            
            # 执行读取
            result = await tool.execute(file_path=file_path, format=file_format)
            
            # 检查错误
            if "error" in result:
                return SkillResult(
                    success=False,
                    data={},
                    error=result["error"],
                    status=SkillStatus.FAILED
                )
            
            return SkillResult(
                success=True,
                data=result,
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import file tools: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to read file: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _write_file(self, context: SkillContext) -> SkillResult:
        """写入文件
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        content = context.input_data.get("content")
        file_path = context.input_data.get("file_path")
        file_format = context.input_data.get("format", "text")
        
        if not content:
            return SkillResult(
                success=False,
                data={},
                error="content is required for write action",
                status=SkillStatus.FAILED
            )
        
        if not file_path:
            return SkillResult(
                success=False,
                data={},
                error="file_path is required for write action",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.tools.file_tools import FileWriteTool
            
            # 创建工具实例
            tool = FileWriteTool()
            
            # 执行写入
            result = await tool.execute(content=content, file_path=file_path, format=file_format)
            
            # 检查错误
            if "error" in result:
                return SkillResult(
                    success=False,
                    data={},
                    error=result["error"],
                    status=SkillStatus.FAILED
                )
            
            return SkillResult(
                success=True,
                data=result,
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import file tools: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to write file: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _convert_file(self, context: SkillContext) -> SkillResult:
        """转换文件格式
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        input_path = context.input_data.get("input_path")
        output_format = context.input_data.get("output_format")
        output_path = context.input_data.get("output_path")
        
        if not input_path:
            return SkillResult(
                success=False,
                data={},
                error="input_path is required for convert action",
                status=SkillStatus.FAILED
            )
        
        if not output_format:
            return SkillResult(
                success=False,
                data={},
                error="output_format is required for convert action",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.tools.file_tools import FileConvertTool
            
            # 创建工具实例
            tool = FileConvertTool()
            
            # 执行转换
            result = await tool.execute(
                input_path=input_path,
                output_format=output_format,
                output_path=output_path
            )
            
            # 检查错误
            if "error" in result:
                return SkillResult(
                    success=False,
                    data={},
                    error=result["error"],
                    status=SkillStatus.FAILED
                )
            
            return SkillResult(
                success=True,
                data=result,
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import file tools: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to convert file: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _list_directory(self, context: SkillContext) -> SkillResult:
        """列出目录内容
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        dir_path = context.input_data.get("file_path", ".")
        
        try:
            # 扩展路径
            expanded_path = os.path.expanduser(dir_path)
            
            # 检查路径是否存在
            if not os.path.exists(expanded_path):
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Directory does not exist: {dir_path}",
                    status=SkillStatus.FAILED
                )
            
            # 检查是否为目录
            if not os.path.isdir(expanded_path):
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Path is not a directory: {dir_path}",
                    status=SkillStatus.FAILED
                )
            
            # 列出目录内容
            items = []
            for item in os.listdir(expanded_path):
                item_path = os.path.join(expanded_path, item)
                item_info = {
                    "name": item,
                    "path": item_path,
                    "is_dir": os.path.isdir(item_path),
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                }
                items.append(item_info)
            
            return SkillResult(
                success=True,
                data={
                    "directory": expanded_path,
                    "items": items,
                    "count": len(items)
                },
                status=SkillStatus.COMPLETED
            )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to list directory: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _delete_file(self, context: SkillContext) -> SkillResult:
        """删除文件
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        file_path = context.input_data.get("file_path")
        
        if not file_path:
            return SkillResult(
                success=False,
                data={},
                error="file_path is required for delete action",
                status=SkillStatus.FAILED
            )
        
        try:
            # 扩展路径
            expanded_path = os.path.expanduser(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(expanded_path):
                return SkillResult(
                    success=False,
                    data={},
                    error=f"File does not exist: {file_path}",
                    status=SkillStatus.FAILED
                )
            
            # 删除文件
            os.remove(expanded_path)
            
            return SkillResult(
                success=True,
                data={
                    "deleted": True,
                    "file_path": expanded_path
                },
                status=SkillStatus.COMPLETED
            )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to delete file: {str(e)}",
                status=SkillStatus.FAILED
            )