# tool_system/adapters/__init__.py

"""
工具适配器模块

提供将不同类型工具（Skill、HTTP API、CLI、MCP）适配到统一工具系统的适配器。
"""

from .skill_adapter import SkillAdapter

__all__ = ["SkillAdapter"]
