# security_module/core.py

"""
安全及 HITL 模块核心模块
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .models import (
    SecurityConfig, Permission, ApprovalRequest, AuditEntry,
    ValidationResult, HumanResponse, UrgencyLevel,
    AuditAction, PermissionAction, ResourceType
)
from .permission_manager import PermissionManager
from .audit_logger import AuditLogger
from .approval_engine import ApprovalEngine
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SecurityModule:
    """安全及 HITL 模块
    
    提供安全管理和人工介入功能，包括：
    - 权限管理
    - 审计日志
    - 审批流程
    - 速率限制
    - 人工介入
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        初始化安全模块
        
        Args:
            config: 安全配置
        """
        self.config = config or SecurityConfig()
        
        # 初始化子模块
        self.permission_manager = PermissionManager()
        self.audit_logger = AuditLogger()
        self.approval_engine = ApprovalEngine(self.config)
        self.rate_limiter = RateLimiter()
        
        # HITL 回调函数
        self._hitl_callbacks: Dict[str, Callable] = {}
        
        # 统计信息
        self._stats = {
            "permission_checks": 0,
            "approval_requests": 0,
            "rate_limit_checks": 0,
            "security_violations": 0
        }
    
    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        ip_address: str = ""
    ) -> bool:
        """检查权限
        
        Args:
            user_id: 用户 ID
            resource: 资源类型
            action: 动作类型
            context: 上下文信息
            ip_address: IP 地址
            
        Returns:
            bool: 是否有权限
        """
        # 检查权限
        granted = self.permission_manager.check_permission(
            user_id, resource, action, context
        )
        
        # 记录审计日志
        self.audit_logger.log_permission_check(
            user_id, resource, action, granted, ip_address
        )
        
        # 更新统计
        self._stats["permission_checks"] += 1
        
        if not granted:
            logger.warning(
                f"Permission denied: user={user_id}, "
                f"resource={resource}, action={action}"
            )
        
        return granted
    
    async def request_approval(
        self,
        requester_id: str,
        action: str,
        resource: str,
        parameters: Optional[Dict[str, Any]] = None,
        reason: str = "",
        urgency: str = UrgencyLevel.MEDIUM.value,
        timeout: Optional[float] = None
    ) -> ApprovalRequest:
        """请求审批
        
        Args:
            requester_id: 请求者 ID
            action: 请求的动作
            resource: 资源
            parameters: 参数
            reason: 原因
            urgency: 紧急程度
            timeout: 超时时间
            
        Returns:
            ApprovalRequest: 审批请求
        """
        # 创建审批请求
        request = await self.approval_engine.create_request(
            requester_id=requester_id,
            action=action,
            resource=resource,
            parameters=parameters,
            reason=reason,
            urgency=urgency,
            timeout=timeout
        )
        
        # 记录审计日志
        self.audit_logger.log_approval_request(
            requester_id, action, resource, request.request_id, urgency
        )
        
        # 更新统计
        self._stats["approval_requests"] += 1
        
        return request
    
    async def approve(
        self,
        request_id: str,
        approver_id: str
    ) -> bool:
        """批准请求
        
        Args:
            request_id: 请求 ID
            approver_id: 审批者 ID
            
        Returns:
            bool: 是否批准成功
        """
        # 批准请求
        success = await self.approval_engine.approve(request_id, approver_id)
        
        if success:
            # 记录审计日志
            self.audit_logger.log_approval_decision(
                approver_id, request_id, True
            )
        
        return success
    
    async def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str = ""
    ) -> bool:
        """拒绝请求
        
        Args:
            request_id: 请求 ID
            approver_id: 审批者 ID
            reason: 拒绝原因
            
        Returns:
            bool: 是否拒绝成功
        """
        # 拒绝请求
        success = await self.approval_engine.reject(request_id, approver_id, reason)
        
        if success:
            # 记录审计日志
            self.audit_logger.log_approval_decision(
                approver_id, request_id, False, reason
            )
        
        return success
    
    async def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[float] = None
    ) -> Optional[ApprovalRequest]:
        """等待审批决定
        
        Args:
            request_id: 请求 ID
            timeout: 超时时间
            
        Returns:
            Optional[ApprovalRequest]: 审批请求
        """
        return await self.approval_engine.wait_for_decision(request_id, timeout)
    
    async def check_rate_limit(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> tuple[bool, Dict[str, Any]]:
        """检查速率限制
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            
        Returns:
            tuple: (是否允许, 详细信息)
        """
        # 检查速率限制
        allowed, info = self.rate_limiter.check_rate_limit(
            user_id, resource, action
        )
        
        # 记录审计日志
        self.audit_logger.log_rate_limit_check(
            user_id, resource, action, allowed,
            info.get("current_count", 0),
            info.get("max_requests", 0)
        )
        
        # 更新统计
        self._stats["rate_limit_checks"] += 1
        
        # 如果允许，记录请求
        if allowed:
            self.rate_limiter.record_request(user_id, resource, action)
        
        return allowed, info
    
    async def validate_input(
        self,
        input_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> ValidationResult:
        """验证输入
        
        Args:
            input_data: 输入数据
            schema: 验证模式
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Missing required field: {field}")
        
        # 检查字段类型
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in input_data:
                expected_type = field_schema.get("type")
                actual_value = input_data[field]
                
                # 类型检查
                if expected_type == "string" and not isinstance(actual_value, str):
                    errors.append(f"Field {field} should be string")
                elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                    errors.append(f"Field {field} should be number")
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    errors.append(f"Field {field} should be boolean")
                elif expected_type == "array" and not isinstance(actual_value, list):
                    errors.append(f"Field {field} should be array")
                elif expected_type == "object" and not isinstance(actual_value, dict):
                    errors.append(f"Field {field} should be object")
                
                # 范围检查
                if "minimum" in field_schema and isinstance(actual_value, (int, float)):
                    if actual_value < field_schema["minimum"]:
                        errors.append(f"Field {field} is below minimum")
                
                if "maximum" in field_schema and isinstance(actual_value, (int, float)):
                    if actual_value > field_schema["maximum"]:
                        errors.append(f"Field {field} is above maximum")
                
                # 长度检查
                if "minLength" in field_schema and isinstance(actual_value, str):
                    if len(actual_value) < field_schema["minLength"]:
                        errors.append(f"Field {field} is too short")
                
                if "maxLength" in field_schema and isinstance(actual_value, str):
                    if len(actual_value) > field_schema["maxLength"]:
                        errors.append(f"Field {field} is too long")
        
        # 记录审计日志
        self.audit_logger.log(
            user_id="system",
            action=AuditAction.INPUT_VALIDATION.value,
            resource="input",
            parameters={"schema": schema},
            result="valid" if len(errors) == 0 else "invalid"
        )
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def report_security_violation(
        self,
        user_id: str,
        violation_type: str,
        details: Dict[str, Any],
        ip_address: str = ""
    ):
        """报告安全违规
        
        Args:
            user_id: 用户 ID
            violation_type: 违规类型
            details: 详细信息
            ip_address: IP 地址
        """
        # 记录审计日志
        self.audit_logger.log_security_violation(
            user_id, violation_type, details, ip_address
        )
        
        # 更新统计
        self._stats["security_violations"] += 1
        
        logger.warning(
            f"Security violation: user={user_id}, "
            f"type={violation_type}, details={details}"
        )
    
    async def should_ask_human(self, context: Dict[str, Any]) -> bool:
        """判断是否需要人工介入
        
        Args:
            context: 上下文信息
            
        Returns:
            bool: 是否需要人工介入
        """
        # 高风险操作
        action = context.get("action", "")
        if action in self.config.high_risk_actions:
            return True
        
        # 需要审批的操作
        if action in self.config.approval_required_actions:
            return True
        
        # 不确定的决策
        confidence = context.get("confidence", 1.0)
        if confidence < 0.8:
            return True
        
        # 用户明确要求
        if context.get("require_approval", False):
            return True
        
        return False
    
    async def ask_human(
        self,
        question: str,
        options: Optional[List[str]] = None,
        timeout: Optional[float] = None
    ) -> Optional[HumanResponse]:
        """向人工提问
        
        Args:
            question: 问题
            options: 选项
            timeout: 超时时间
            
        Returns:
            Optional[HumanResponse]: 人工响应
        """
        # 这里应该实现与用户的交互
        # 暂时返回一个模拟响应
        logger.info(f"Human question: {question}")
        
        # 创建模拟响应
        response = HumanResponse(
            response_id="",
            request_id="",
            responder_id="human",
            response="Approved",
            approved=True
        )
        
        return response
    
    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """获取审计日志
        
        Args:
            user_id: 用户 ID 过滤
            action: 操作类型过滤
            resource: 资源过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[AuditEntry]: 审计条目列表
        """
        return self.audit_logger.get_entries(
            user_id=user_id,
            action=action,
            resource=resource,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def get_permissions(self) -> List[Permission]:
        """获取所有权限
        
        Returns:
            List[Permission]: 权限列表
        """
        return self.permission_manager.list_permissions()
    
    def get_approval_requests(
        self,
        status: Optional[str] = None,
        requester_id: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """获取审批请求
        
        Args:
            status: 状态过滤
            requester_id: 请求者 ID 过滤
            
        Returns:
            List[ApprovalRequest]: 审批请求列表
        """
        if requester_id:
            requests = self.approval_engine.get_requests_by_requester(requester_id)
        else:
            requests = list(self.approval_engine._requests.values())
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        return requests
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "permission_checks": self._stats["permission_checks"],
            "approval_requests": self._stats["approval_requests"],
            "rate_limit_checks": self._stats["rate_limit_checks"],
            "security_violations": self._stats["security_violations"],
            "permission_manager": {
                "total_permissions": len(self.permission_manager.list_permissions()),
                "total_roles": len(self.permission_manager._role_permissions),
                "total_users": len(self.permission_manager._user_roles)
            },
            "audit_logger": self.audit_logger.get_stats(),
            "approval_engine": self.approval_engine.get_stats(),
            "rate_limiter": self.rate_limiter.get_stats()
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """获取模块状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "status": "ready",
            "config": {
                "default_approval_timeout": self.config.default_approval_timeout,
                "enable_rate_limiting": self.config.enable_rate_limiting,
                "enable_audit_logging": self.config.enable_audit_logging,
                "enable_permission_check": self.config.enable_permission_check
            },
            "stats": self.get_stats()
        }
