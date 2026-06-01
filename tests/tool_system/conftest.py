# tests/tool_system/conftest.py

"""
工具系统测试配置
"""

import pytest
import asyncio
import sys
import os
from typing import Generator

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tool_models():
    """导入工具模型"""
    from tool_system.models import (
        ToolDefinition, ToolCall, ToolResult,
        ToolType, ToolCategory, ToolParameter,
        ToolStatus, ToolExecutionLog
    )
    return {
        "ToolDefinition": ToolDefinition,
        "ToolCall": ToolCall,
        "ToolResult": ToolResult,
        "ToolType": ToolType,
        "ToolCategory": ToolCategory,
        "ToolParameter": ToolParameter,
        "ToolStatus": ToolStatus,
        "ToolExecutionLog": ToolExecutionLog
    }


@pytest.fixture
def tool_registry():
    """创建工具注册表"""
    from tool_system.registry import ToolRegistry
    return ToolRegistry()


@pytest.fixture
def tool_executor(tool_registry):
    """创建工具执行器"""
    from tool_system.executor import ToolExecutor
    return ToolExecutor(registry=tool_registry)
