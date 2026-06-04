# agents_md_module/__init__.py

"""
AGENTS.md 免疫机制模块

提供项目级行为规则系统，用于定义 Agent 在特定项目中的行为规范。
"""

from .models import (
    AgentsMdConfig, AgentRule, RuleViolation, RuleContext,
    RuleCheckResult, ImmuneResponse, RuleType, RuleSeverity,
    RuleScope, ViolationAction,
    generate_rule_id, generate_violation_id
)
from .immune_system import ImmuneSystem
from .rule_engine import RuleEngine
from .api import create_immune_router

__version__ = "1.0.0"
__author__ = "OpenCopilot Team"

__all__ = [
    # 核心类
    "ImmuneSystem",
    "RuleEngine",
    
    # 数据模型
    "AgentsMdConfig",
    "AgentRule",
    "RuleViolation",
    "RuleContext",
    "RuleCheckResult",
    "ImmuneResponse",
    
    # 枚举类型
    "RuleType",
    "RuleSeverity",
    "RuleScope",
    "ViolationAction",
    
    # 工具函数
    "generate_rule_id",
    "generate_violation_id",
    
    # API
    "create_immune_router",
]
