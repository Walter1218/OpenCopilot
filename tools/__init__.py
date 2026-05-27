# OpenCopilot 工具调用框架

"""
工具调用框架，支持文件处理、文本转换、格式转换等能力。
"""

from .base import BaseTool, ToolRegistry
from .file_tools import FileReadTool, FileWriteTool, FileConvertTool
from .text_tools import TextExtractTool, TextTransformTool
from .format_tools import MarkdownToDocxTool, MarkdownToPptxTool, TextToTableTool

# 全局工具注册表
tool_registry = ToolRegistry()

# 注册默认工具
def register_default_tools():
    """注册默认工具"""
    tool_registry.register("file_read", FileReadTool())
    tool_registry.register("file_write", FileWriteTool())
    tool_registry.register("file_convert", FileConvertTool())
    tool_registry.register("text_extract", TextExtractTool())
    tool_registry.register("text_transform", TextTransformTool())
    tool_registry.register("md_to_docx", MarkdownToDocxTool())
    tool_registry.register("md_to_pptx", MarkdownToPptxTool())
    tool_registry.register("text_to_table", TextToTableTool())

# 初始化时注册工具
register_default_tools()

__all__ = [
    "BaseTool",
    "ToolRegistry", 
    "tool_registry",
    "register_default_tools",
    "FileReadTool",
    "FileWriteTool", 
    "FileConvertTool",
    "TextExtractTool",
    "TextTransformTool",
    "MarkdownToDocxTool",
    "MarkdownToPptxTool",
    "TextToTableTool"
]