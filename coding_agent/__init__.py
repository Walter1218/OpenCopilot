"""
Coding Agent 模块

实现 Coding Agent 的核心功能，包括 Bug 修复、API 结果增强、代码分析等。
"""

from .intent_detector import IntentDetector, CodingIntent
from .prompt_generator import PromptGenerator, PromptLibrary, PromptTemplate
from .tool_executor import ToolExecutor, IDEToolExecutor, AnalysisToolExecutor
from .core import CodingAgent

__version__ = "1.0.0"
__all__ = [
    "IntentDetector",
    "CodingIntent",
    "PromptGenerator",
    "PromptLibrary",
    "PromptTemplate",
    "ToolExecutor",
    "IDEToolExecutor",
    "AnalysisToolExecutor",
    "CodingAgent"
]