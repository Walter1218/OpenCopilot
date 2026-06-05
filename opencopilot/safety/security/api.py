# security_module/api.py

"""
安全及 HITL 模块 RESTful API 端点
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    SecurityConfig, Permission, ApprovalRequest, AuditEntry,
    ValidationResult, UrgencyLevel
)
from .core import SecurityModule


# Pydantic 模型（用于 API 请求/响应）

class CheckPermissionRequest(BaseModel):
    """检查权限请求"""
    user_id: str = Field(..., description="用户 ID")
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="动作类型")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    ip_address: str = Field("", description="IP 地址")


class ApprovalRequestModel(BaseModel):
    """审批请求模型"""
    requester_id: str = Field(..., description="请求者 ID")
    action: str = Field(..., description="请求的动作")
    resource: str = Field(..., description="资源")
    parameters: Optional[Dict[str, Any]] = Field(None, description="参数")
    reason: str = Field("", description="原因")
    urgency: str = Field(UrgencyLevel.MEDIUM.value, description="紧急程度")
    timeout: Optional[float] = Field(None, description="超时时间")


class ApprovalDecisionRequest(BaseModel):
    """审批决定请求"""
    approver_id: str = Field(..., description="审批者 ID")
    reason: str = Field("", description="原因")


class RateLimitCheckRequest(BaseModel):
    """速率限制检查请求"""
    user_id: str = Field(..., description="用户 ID")
    resource: str = Field(..., description="资源")
    action: str = Field(..., description="动作")


class ValidateInputRequest(BaseModel):
    """验证输入请求"""
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    schema: Dict[str, Any] = Field(..., description="验证模式")


class SecurityViolationRequest(BaseModel):
    """安全违规报告请求"""
    user_id: str = Field(..., description="用户 ID")
    violation_type: str = Field(..., description="违规类型")
    details: Dict[str, Any] = Field(..., description="详细信息")
    ip_address: str = Field("", description="IP 地址")


class PermissionResponse(BaseModel):
    """权限响应"""
    permission_id: str
    resource: str
    action: str
    conditions: Dict[str, Any] = {}
    description: str = ""


class ApprovalRequestResponse(BaseModel):
    """审批请求响应"""
    request_id: str
    requester_id: str
    action: str
    resource: str
    parameters: Dict[str, Any] = {}
    reason: str = ""
    urgency: str
    status: str
    created_at: float
    expires_at: float
    approver_id: Optional[str] = None
    approved_at: Optional[float] = None
    rejection_reason: Optional[str] = None


class AuditEntryResponse(BaseModel):
    """审计条目响应"""
    entry_id: str
    timestamp: float
    user_id: str
    action: str
    resource: str
    parameters: Dict[str, Any] = {}
    result: str = ""
    ip_address: str = ""
    user_agent: str = ""


class ValidationResultResponse(BaseModel):
    """验证结果响应"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class StatsResponse(BaseModel):
    """统计响应"""
    permission_checks: int
    approval_requests: int
    rate_limit_checks: int
    security_violations: int
    permission_manager: Dict[str, Any]
    audit_logger: Dict[str, Any]
    approval_engine: Dict[str, Any]
    rate_limiter: Dict[str, Any]


class StatusResponse(BaseModel):
    """状态响应"""
    status: str
    config: Dict[str, Any]
    stats: Dict[str, Any]


def create_security_router(security_module: SecurityModule) -> APIRouter:
    """
    创建安全模块 API 路由器
    
    Args:
        security_module: 安全模块实例
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/security", tags=["security"])
    
    @router.post("/check-permission")
    async def check_permission(request: CheckPermissionRequest):
        """检查权限"""
        granted = await security_module.check_permission(
            user_id=request.user_id,
            resource=request.resource,
            action=request.action,
            context=request.context,
            ip_address=request.ip_address
        )
        
        return {"granted": granted}
    
    @router.post("/approval/request", response_model=ApprovalRequestResponse)
    async def request_approval(request: ApprovalRequestModel):
        """请求审批"""
        approval_request = await security_module.request_approval(
            requester_id=request.requester_id,
            action=request.action,
            resource=request.resource,
            parameters=request.parameters,
            reason=request.reason,
            urgency=request.urgency,
            timeout=request.timeout
        )
        
        return ApprovalRequestResponse(
            request_id=approval_request.request_id,
            requester_id=approval_request.requester_id,
            action=approval_request.action,
            resource=approval_request.resource,
            parameters=approval_request.parameters,
            reason=approval_request.reason,
            urgency=approval_request.urgency,
            status=approval_request.status,
            created_at=approval_request.created_at,
            expires_at=approval_request.expires_at,
            approver_id=approval_request.approver_id,
            approved_at=approval_request.approved_at,
            rejection_reason=approval_request.rejection_reason
        )
    
    @router.post("/approval/{request_id}/approve")
    async def approve_request(request_id: str, request: ApprovalDecisionRequest):
        """批准请求"""
        success = await security_module.approve(
            request_id=request_id,
            approver_id=request.approver_id
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to approve request: {request_id}"
            )
        
        return {"status": "approved", "request_id": request_id}
    
    @router.post("/approval/{request_id}/reject")
    async def reject_request(request_id: str, request: ApprovalDecisionRequest):
        """拒绝请求"""
        success = await security_module.reject(
            request_id=request_id,
            approver_id=request.approver_id,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to reject request: {request_id}"
            )
        
        return {"status": "rejected", "request_id": request_id}
    
    @router.get("/approval/{request_id}", response_model=ApprovalRequestResponse)
    async def get_approval_request(request_id: str):
        """获取审批请求"""
        approval_request = security_module.approval_engine.get_request(request_id)
        
        if not approval_request:
            raise HTTPException(
                status_code=404,
                detail=f"Approval request not found: {request_id}"
            )
        
        return ApprovalRequestResponse(
            request_id=approval_request.request_id,
            requester_id=approval_request.requester_id,
            action=approval_request.action,
            resource=approval_request.resource,
            parameters=approval_request.parameters,
            reason=approval_request.reason,
            urgency=approval_request.urgency,
            status=approval_request.status,
            created_at=approval_request.created_at,
            expires_at=approval_request.expires_at,
            approver_id=approval_request.approver_id,
            approved_at=approval_request.approved_at,
            rejection_reason=approval_request.rejection_reason
        )
    
    @router.get("/approval", response_model=List[ApprovalRequestResponse])
    async def list_approval_requests(
        status: Optional[str] = Query(None, description="状态过滤"),
        requester_id: Optional[str] = Query(None, description="请求者 ID 过滤")
    ):
        """列出审批请求"""
        requests = security_module.get_approval_requests(
            status=status,
            requester_id=requester_id
        )
        
        return [
            ApprovalRequestResponse(
                request_id=r.request_id,
                requester_id=r.requester_id,
                action=r.action,
                resource=r.resource,
                parameters=r.parameters,
                reason=r.reason,
                urgency=r.urgency,
                status=r.status,
                created_at=r.created_at,
                expires_at=r.expires_at,
                approver_id=r.approver_id,
                approved_at=r.approved_at,
                rejection_reason=r.rejection_reason
            )
            for r in requests
        ]
    
    @router.get("/audit-log", response_model=List[AuditEntryResponse])
    async def get_audit_log(
        user_id: Optional[str] = Query(None, description="用户 ID 过滤"),
        action: Optional[str] = Query(None, description="操作类型过滤"),
        resource: Optional[str] = Query(None, description="资源过滤"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取审计日志"""
        entries = security_module.get_audit_log(
            user_id=user_id,
            action=action,
            resource=resource,
            limit=limit
        )
        
        return [
            AuditEntryResponse(
                entry_id=e.entry_id,
                timestamp=e.timestamp,
                user_id=e.user_id,
                action=e.action,
                resource=e.resource,
                parameters=e.parameters,
                result=e.result,
                ip_address=e.ip_address,
                user_agent=e.user_agent
            )
            for e in entries
        ]
    
    @router.post("/validate", response_model=ValidationResultResponse)
    async def validate_input(request: ValidateInputRequest):
        """验证输入"""
        result = await security_module.validate_input(
            input_data=request.input_data,
            schema=request.schema
        )
        
        return ValidationResultResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings
        )
    
    @router.get("/permissions", response_model=List[PermissionResponse])
    async def list_permissions():
        """列出权限"""
        permissions = security_module.get_permissions()
        
        return [
            PermissionResponse(
                permission_id=p.permission_id,
                resource=p.resource,
                action=p.action,
                conditions=p.conditions,
                description=p.description
            )
            for p in permissions
        ]
    
    @router.post("/rate-limit/check")
    async def check_rate_limit(request: RateLimitCheckRequest):
        """检查速率限制"""
        allowed, info = await security_module.check_rate_limit(
            user_id=request.user_id,
            resource=request.resource,
            action=request.action
        )
        
        return {"allowed": allowed, **info}
    
    @router.post("/violation")
    async def report_security_violation(request: SecurityViolationRequest):
        """报告安全违规"""
        await security_module.report_security_violation(
            user_id=request.user_id,
            violation_type=request.violation_type,
            details=request.details,
            ip_address=request.ip_address
        )
        
        return {"status": "reported"}
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = security_module.get_stats()
        return StatsResponse(**stats)
    
    @router.get("/status", response_model=StatusResponse)
    async def get_status():
        """获取模块状态"""
        status = await security_module.get_status()
        return StatusResponse(**status)
    
    return router
