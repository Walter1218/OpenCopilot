# tool_system/__init__.py

"""
工具调用模块 (Tool System)

提供统一的工具注册、发现、调用和管理能力。
"""

from .models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolType, ToolCategory, ToolParameter,
    ToolStatus, ToolExecutionLog
)
from .registry import ToolRegistry
from .executor import ToolExecutor
from .llm_tool import LLMTool, LLMToolWithProvider, create_llm_tool

__version__ = "1.0.0"
__all__ = [
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ToolType",
    "ToolCategory",
    "ToolParameter",
    "ToolStatus",
    "ToolExecutionLog",
    "ToolRegistry",
    "ToolExecutor",
    "LLMTool",
    "LLMToolWithProvider",
    "create_llm_tool"
]
