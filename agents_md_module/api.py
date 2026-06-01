# agents_md_module/api.py

"""
AGENTS.md 免疫机制模块 RESTful API 端点
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    AgentsMdConfig, AgentRule, RuleViolation, RuleContext,
    RuleCheckResult, ImmuneResponse, RuleType, RuleSeverity,
    RuleScope, ViolationAction
)
from .immune_system import ImmuneSystem


# Pydantic 模型（用于 API 请求/响应）

class CheckActionRequest(BaseModel):
    """检查动作请求"""
    user_id: str = Field("", description="用户 ID")
    session_id: str = Field("", description="会话 ID")
    project_path: str = Field("", description="项目路径")
    current_file: str = Field("", description="当前文件")
    action: str = Field(..., description="要执行的动作")
    tool_name: str = Field("", description="工具名称")
    parameters: Optional[Dict[str, Any]] = Field(None, description="动作参数")


class CheckContentRequest(BaseModel):
    """检查内容请求"""
    user_id: str = Field("", description="用户 ID")
    session_id: str = Field("", description="会话 ID")
    project_path: str = Field("", description="项目路径")
    current_file: str = Field("", description="当前文件")
    content: str = Field(..., description="要检查的内容")


class AddRuleRequest(BaseModel):
    """添加规则请求"""
    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    rule_type: str = Field(RuleType.BEHAVIOR.value, description="规则类型")
    severity: str = Field(RuleSeverity.WARNING.value, description="严重程度")
    scope: str = Field(RuleScope.PROJECT.value, description="作用域")
    enabled: bool = Field(True, description="是否启用")
    pattern: Optional[str] = Field(None, description="匹配模式")
    condition: Optional[str] = Field(None, description="条件表达式")
    action: str = Field(ViolationAction.LOG.value, description="违规动作")
    message: str = Field("", description="违规提示消息")
    examples: List[str] = Field([], description="示例")
    tags: List[str] = Field([], description="标签")


class RuleResponse(BaseModel):
    """规则响应"""
    rule_id: str
    name: str
    description: str
    rule_type: str
    severity: str
    scope: str
    enabled: bool
    pattern: Optional[str] = None
    condition: Optional[str] = None
    action: str
    message: str
    examples: List[str] = []
    tags: List[str] = []


class ViolationResponse(BaseModel):
    """违规响应"""
    violation_id: str
    rule_id: str
    rule_name: str
    timestamp: float
    context: Dict[str, Any] = {}
    details: str = ""
    severity: str
    action_taken: str
    resolved: bool


class CheckResultResponse(BaseModel):
    """检查结果响应"""
    allowed: bool
    violations: List[ViolationResponse] = []
    message: str = ""
    suggestions: List[str] = []
    auto_fix_applied: bool = False


class StatsResponse(BaseModel):
    """统计响应"""
    total_checks: int
    violations_detected: int
    actions_blocked: int
    auto_fixes_applied: int
    human_interventions: int
    total_rules: int
    enabled_rules: int
    total_violations: int
    rules_by_type: Dict[str, int] = {}
    rules_by_severity: Dict[str, int] = {}
    violations_by_severity: Dict[str, int] = {}


class StatusResponse(BaseModel):
    """状态响应"""
    enabled: bool
    stats: Dict[str, Any]
    config: Dict[str, Any]


def create_immune_router(immune_system: ImmuneSystem) -> APIRouter:
    """
    创建免疫系统 API 路由器
    
    Args:
        immune_system: 免疫系统实例
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/agents-md", tags=["agents-md"])
    
    @router.post("/check/action", response_model=CheckResultResponse)
    async def check_action(request: CheckActionRequest):
        """检查动作"""
        context = RuleContext(
            user_id=request.user_id,
            session_id=request.session_id,
            project_path=request.project_path,
            current_file=request.current_file,
            tool_name=request.tool_name
        )
        
        response = await immune_system.check_action(
            context=context,
            action=request.action,
            parameters=request.parameters
        )
        
        return CheckResultResponse(
            allowed=response.allowed,
            violations=[
                ViolationResponse(
                    violation_id=v.violation_id,
                    rule_id=v.rule_id,
                    rule_name=v.rule_name,
                    timestamp=v.timestamp,
                    context=v.context,
                    details=v.details,
                    severity=v.severity,
                    action_taken=v.action_taken,
                    resolved=v.resolved
                )
                for v in response.violations
            ],
            message=response.message,
            suggestions=response.suggestions,
            auto_fix_applied=response.auto_fix_applied
        )
    
    @router.post("/check/content", response_model=CheckResultResponse)
    async def check_content(request: CheckContentRequest):
        """检查内容"""
        context = RuleContext(
            user_id=request.user_id,
            session_id=request.session_id,
            project_path=request.project_path,
            current_file=request.current_file
        )
        
        response = await immune_system.check_content(
            context=context,
            content=request.content
        )
        
        return CheckResultResponse(
            allowed=response.allowed,
            violations=[
                ViolationResponse(
                    violation_id=v.violation_id,
                    rule_id=v.rule_id,
                    rule_name=v.rule_name,
                    timestamp=v.timestamp,
                    context=v.context,
                    details=v.details,
                    severity=v.severity,
                    action_taken=v.action_taken,
                    resolved=v.resolved
                )
                for v in response.violations
            ],
            message=response.message,
            suggestions=response.suggestions,
            auto_fix_applied=response.auto_fix_applied
        )
    
    @router.post("/rules", response_model=RuleResponse)
    async def add_rule(request: AddRuleRequest):
        """添加规则"""
        rule = AgentRule(
            rule_id="",
            name=request.name,
            description=request.description,
            rule_type=request.rule_type,
            severity=request.severity,
            scope=request.scope,
            enabled=request.enabled,
            pattern=request.pattern,
            condition=request.condition,
            action=request.action,
            message=request.message,
            examples=request.examples,
            tags=request.tags
        )
        
        success = immune_system.add_rule(rule)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to add rule: {request.name}"
            )
        
        return RuleResponse(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            severity=rule.severity,
            scope=rule.scope,
            enabled=rule.enabled,
            pattern=rule.pattern,
            condition=rule.condition,
            action=rule.action,
            message=rule.message,
            examples=rule.examples,
            tags=rule.tags
        )
    
    @router.get("/rules", response_model=List[RuleResponse])
    async def list_rules(
        rule_type: Optional[str] = Query(None, description="规则类型过滤"),
        scope: Optional[str] = Query(None, description="作用域过滤"),
        enabled_only: bool = Query(True, description="只返回启用的规则")
    ):
        """列出规则"""
        rules = immune_system.list_rules(
            rule_type=rule_type,
            scope=scope,
            enabled_only=enabled_only
        )
        
        return [
            RuleResponse(
                rule_id=r.rule_id,
                name=r.name,
                description=r.description,
                rule_type=r.rule_type,
                severity=r.severity,
                scope=r.scope,
                enabled=r.enabled,
                pattern=r.pattern,
                condition=r.condition,
                action=r.action,
                message=r.message,
                examples=r.examples,
                tags=r.tags
            )
            for r in rules
        ]
    
    @router.get("/rules/{rule_id}", response_model=RuleResponse)
    async def get_rule(rule_id: str):
        """获取规则"""
        rule = immune_system.get_rule(rule_id)
        
        if not rule:
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found: {rule_id}"
            )
        
        return RuleResponse(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            severity=rule.severity,
            scope=rule.scope,
            enabled=rule.enabled,
            pattern=rule.pattern,
            condition=rule.condition,
            action=rule.action,
            message=rule.message,
            examples=rule.examples,
            tags=rule.tags
        )
    
    @router.delete("/rules/{rule_id}")
    async def delete_rule(rule_id: str):
        """删除规则"""
        success = immune_system.remove_rule(rule_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Rule not found: {rule_id}"
            )
        
        return {"status": "deleted", "rule_id": rule_id}
    
    @router.get("/violations", response_model=List[ViolationResponse])
    async def get_violations(
        rule_id: Optional[str] = Query(None, description="规则 ID 过滤"),
        severity: Optional[str] = Query(None, description="严重程度过滤"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取违规记录"""
        violations = immune_system.get_violations(
            rule_id=rule_id,
            severity=severity,
            limit=limit
        )
        
        return [
            ViolationResponse(
                violation_id=v.violation_id,
                rule_id=v.rule_id,
                rule_name=v.rule_name,
                timestamp=v.timestamp,
                context=v.context,
                details=v.details,
                severity=v.severity,
                action_taken=v.action_taken,
                resolved=v.resolved
            )
            for v in violations
        ]
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = immune_system.get_stats()
        return StatsResponse(**stats)
    
    @router.get("/status", response_model=StatusResponse)
    async def get_status():
        """获取状态"""
        status = immune_system.get_status()
        return StatusResponse(**status)
    
    return router
