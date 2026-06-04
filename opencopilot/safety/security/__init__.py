# security_module/__init__.py

"""
安全及 HITL 模块

提供安全管理和人工介入功能，包括权限管理、审计日志、审批流程、速率限制等。
"""

from .models import (
    SecurityConfig, Permission, ApprovalRequest, AuditEntry,
    ValidationResult, HumanResponse, RateLimitRule, RateLimitState,
    PermissionAction, ResourceType, ApprovalStatus, UrgencyLevel,
    AuditAction,
    generate_permission_id, generate_request_id, generate_entry_id
)
from .core import SecurityModule
from .permission_manager import PermissionManager
from .audit_logger import AuditLogger
from .approval_engine import ApprovalEngine
from .rate_limiter import RateLimiter
from .api import create_security_router

__version__ = "1.0.0"
__author__ = "OpenCopilot Team"

__all__ = [
    # 核心类
    "SecurityModule",
    "PermissionManager",
    "AuditLogger",
    "ApprovalEngine",
    "RateLimiter",
    
    # 数据模型
    "SecurityConfig",
    "Permission",
    "ApprovalRequest",
    "AuditEntry",
    "ValidationResult",
    "HumanResponse",
    "RateLimitRule",
    "RateLimitState",
    
    # 枚举类型
    "PermissionAction",
    "ResourceType",
    "ApprovalStatus",
    "UrgencyLevel",
    "AuditAction",
    
    # 工具函数
    "generate_permission_id",
    "generate_request_id",
    "generate_entry_id",
    
    # API
    "create_security_router",
]
