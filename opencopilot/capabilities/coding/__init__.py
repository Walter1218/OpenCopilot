# code_executor/__init__.py

"""
代码执行引擎模块

提供安全的代码执行环境，支持多种编程语言和沙盒隔离。
"""

from .models import (
    ExecutorConfig, SandboxConfig, CodeExecutionRequest,
    ExecutionResult, ValidationResult, LanguageInfo,
    ExecutionLog, ExecutionStatus, LanguageType,
    generate_execution_id, generate_request_id
)
from .core import CodeExecutor
from .sandbox import SandboxManager, ResourceMonitor
from .handlers.base import LanguageHandler
from .handlers.python_handler import PythonHandler
from .handlers.javascript_handler import JavaScriptHandler
from .handlers.shell_handler import ShellHandler
from .api import create_executor_router

__version__ = "1.0.0"
__author__ = "OpenCopilot Team"

__all__ = [
    # 核心类
    "CodeExecutor",
    "SandboxManager",
    "ResourceMonitor",
    
    # 语言处理器
    "LanguageHandler",
    "PythonHandler",
    "JavaScriptHandler",
    "ShellHandler",
    
    # 数据模型
    "ExecutorConfig",
    "SandboxConfig",
    "CodeExecutionRequest",
    "ExecutionResult",
    "ValidationResult",
    "LanguageInfo",
    "ExecutionLog",
    "ExecutionStatus",
    "LanguageType",
    
    # 工具函数
    "generate_execution_id",
    "generate_request_id",
    
    # API
    "create_executor_router",
]
