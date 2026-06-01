# tests/security_module/test_security_module.py

"""
安全及 HITL 模块测试

测试安全模块的各项功能。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入安全模块
from security_module.models import (
    SecurityConfig, Permission, ApprovalRequest, AuditEntry,
    ValidationResult, HumanResponse, RateLimitRule,
    PermissionAction, ResourceType, ApprovalStatus, UrgencyLevel,
    AuditAction, generate_permission_id, generate_request_id
)
from security_module.core import SecurityModule
from security_module.permission_manager import PermissionManager
from security_module.audit_logger import AuditLogger
from security_module.approval_engine import ApprovalEngine
from security_module.rate_limiter import RateLimiter


@pytest.fixture
def security_module():
    """创建安全模块实例"""
    config = SecurityConfig(
        default_approval_timeout=10.0,
        enable_rate_limiting=True,
        enable_audit_logging=True,
        enable_permission_check=True
    )
    return SecurityModule(config=config)


@pytest.fixture
def permission_manager():
    """创建权限管理器实例"""
    return PermissionManager()


@pytest.fixture
def audit_logger():
    """创建审计日志器实例"""
    return AuditLogger()


@pytest.fixture
def approval_engine():
    """创建审批引擎实例"""
    return ApprovalEngine()


@pytest.fixture
def rate_limiter():
    """创建速率限制器实例"""
    return RateLimiter()


class TestModels:
    """数据模型测试"""
    
    def test_generate_permission_id(self):
        """测试生成权限 ID"""
        id1 = generate_permission_id()
        id2 = generate_permission_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_generate_request_id(self):
        """测试生成请求 ID"""
        id1 = generate_request_id()
        id2 = generate_request_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_permission_creation(self):
        """测试权限创建"""
        permission = Permission(
            permission_id="test_perm",
            resource=ResourceType.TOOL.value,
            action=PermissionAction.READ.value,
            description="Test permission"
        )
        
        assert permission.permission_id == "test_perm"
        assert permission.resource == ResourceType.TOOL.value
        assert permission.action == PermissionAction.READ.value
        assert not permission.is_expired()
    
    def test_approval_request_creation(self):
        """测试审批请求创建"""
        request = ApprovalRequest(
            request_id="test_req",
            requester_id="user1",
            action="execute",
            resource="tool",
            urgency=UrgencyLevel.HIGH.value
        )
        
        assert request.request_id == "test_req"
        assert request.requester_id == "user1"
        assert request.status == ApprovalStatus.PENDING.value
        assert not request.is_expired()
    
    def test_approval_request_approve(self):
        """测试审批请求批准"""
        request = ApprovalRequest(
            request_id="test_req",
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        request.approve("approver1")
        
        assert request.status == ApprovalStatus.APPROVED.value
        assert request.approver_id == "approver1"
        assert request.approved_at is not None
    
    def test_approval_request_reject(self):
        """测试审批请求拒绝"""
        request = ApprovalRequest(
            request_id="test_req",
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        request.reject("approver1", "Not allowed")
        
        assert request.status == ApprovalStatus.REJECTED.value
        assert request.approver_id == "approver1"
        assert request.rejection_reason == "Not allowed"


class TestPermissionManager:
    """权限管理器测试"""
    
    def test_default_permissions(self, permission_manager):
        """测试默认权限"""
        permissions = permission_manager.list_permissions()
        
        assert len(permissions) > 0
        
        # 检查是否有基本权限
        perm_ids = [p.permission_id for p in permissions]
        assert "perm_read_tools" in perm_ids
        assert "perm_execute_tools" in perm_ids
    
    def test_default_roles(self, permission_manager):
        """测试默认角色"""
        roles = permission_manager._role_permissions
        
        assert "viewer" in roles
        assert "user" in roles
        assert "admin" in roles
    
    def test_assign_role_to_user(self, permission_manager):
        """测试分配角色给用户"""
        success = permission_manager.assign_role_to_user("user1", "user")
        
        assert success is True
        
        roles = permission_manager.get_user_roles("user1")
        assert "user" in roles
    
    def test_check_permission(self, permission_manager):
        """测试检查权限"""
        # 分配角色
        permission_manager.assign_role_to_user("user1", "user")
        
        # 检查权限
        has_perm = permission_manager.check_permission(
            "user1",
            ResourceType.TOOL.value,
            PermissionAction.READ.value
        )
        
        assert has_perm is True
    
    def test_check_permission_denied(self, permission_manager):
        """测试权限拒绝"""
        # 分配查看者角色
        permission_manager.assign_role_to_user("user1", "viewer")
        
        # 检查执行权限（应该被拒绝）
        has_perm = permission_manager.check_permission(
            "user1",
            ResourceType.TOOL.value,
            PermissionAction.EXECUTE.value
        )
        
        assert has_perm is False
    
    def test_assign_permission_to_user(self, permission_manager):
        """测试直接分配权限给用户"""
        success = permission_manager.assign_permission_to_user(
            "perm_execute_tools", "user1"
        )
        
        assert success is True
        
        has_perm = permission_manager.check_permission(
            "user1",
            ResourceType.TOOL.value,
            PermissionAction.EXECUTE.value
        )
        
        assert has_perm is True


class TestAuditLogger:
    """审计日志器测试"""
    
    def test_log_entry(self, audit_logger):
        """测试记录日志"""
        entry = audit_logger.log(
            user_id="user1",
            action="test_action",
            resource="test_resource",
            result="success"
        )
        
        assert entry is not None
        assert entry.user_id == "user1"
        assert entry.action == "test_action"
        assert entry.result == "success"
    
    def test_get_entries(self, audit_logger):
        """测试获取日志"""
        # 记录一些日志
        audit_logger.log("user1", "action1", "resource1")
        audit_logger.log("user2", "action2", "resource2")
        audit_logger.log("user1", "action3", "resource3")
        
        # 获取所有日志
        entries = audit_logger.get_entries()
        assert len(entries) == 3
        
        # 按用户过滤
        entries = audit_logger.get_entries(user_id="user1")
        assert len(entries) == 2
        
        # 按操作过滤
        entries = audit_logger.get_entries(action="action2")
        assert len(entries) == 1
    
    def test_log_permission_check(self, audit_logger):
        """测试记录权限检查日志"""
        entry = audit_logger.log_permission_check(
            user_id="user1",
            resource="tool",
            action="read",
            granted=True
        )
        
        assert entry.action == AuditAction.PERMISSION_CHECK.value
        assert entry.result == "granted"
    
    def test_log_approval_request(self, audit_logger):
        """测试记录审批请求日志"""
        entry = audit_logger.log_approval_request(
            requester_id="user1",
            action="execute",
            resource="tool",
            request_id="req123",
            urgency="high"
        )
        
        assert entry.action == AuditAction.APPROVAL_REQUEST.value
        assert entry.parameters["request_id"] == "req123"
    
    def test_get_stats(self, audit_logger):
        """测试获取统计信息"""
        # 记录一些日志
        audit_logger.log("user1", "action1", "resource1")
        audit_logger.log("user2", "action2", "resource2")
        
        stats = audit_logger.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["current_entries"] == 2


class TestApprovalEngine:
    """审批引擎测试"""
    
    @pytest.mark.asyncio
    async def test_create_request(self, approval_engine):
        """测试创建审批请求"""
        request = await approval_engine.create_request(
            requester_id="user1",
            action="execute",
            resource="tool",
            reason="Need to run analysis"
        )
        
        assert request is not None
        assert request.requester_id == "user1"
        assert request.status == ApprovalStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_approve_request(self, approval_engine):
        """测试批准请求"""
        # 创建请求
        request = await approval_engine.create_request(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 批准请求
        success = await approval_engine.approve(
            request.request_id, "approver1"
        )
        
        assert success is True
        
        # 检查状态
        updated_request = approval_engine.get_request(request.request_id)
        assert updated_request.status == ApprovalStatus.APPROVED.value
    
    @pytest.mark.asyncio
    async def test_reject_request(self, approval_engine):
        """测试拒绝请求"""
        # 创建请求
        request = await approval_engine.create_request(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 拒绝请求
        success = await approval_engine.reject(
            request.request_id, "approver1", "Not allowed"
        )
        
        assert success is True
        
        # 检查状态
        updated_request = approval_engine.get_request(request.request_id)
        assert updated_request.status == ApprovalStatus.REJECTED.value
    
    @pytest.mark.asyncio
    async def test_get_pending_requests(self, approval_engine):
        """测试获取待处理请求"""
        # 创建一些请求
        await approval_engine.create_request(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        await approval_engine.create_request(
            requester_id="user2",
            action="write",
            resource="file"
        )
        
        # 获取待处理请求
        pending = approval_engine.get_pending_requests()
        
        assert len(pending) == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, approval_engine):
        """测试获取统计信息"""
        # 创建一些请求
        await approval_engine.create_request(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        stats = approval_engine.get_stats()
        
        assert stats["total_requests"] == 1
        assert stats["pending"] == 1


class TestRateLimiter:
    """速率限制器测试"""
    
    def test_default_rules(self, rate_limiter):
        """测试默认规则"""
        rules = rate_limiter.list_rules()
        
        assert len(rules) > 0
        
        rule_ids = [r.rule_id for r in rules]
        assert "rule_api_calls" in rule_ids
        assert "rule_code_execute" in rule_ids
    
    def test_check_rate_limit_allowed(self, rate_limiter):
        """测试速率限制允许"""
        allowed, info = rate_limiter.check_rate_limit(
            "user1", "api", "call"
        )
        
        assert allowed is True
        assert info["allowed"] is True
        assert info["remaining"] > 0
    
    def test_check_rate_limit_exceeded(self, rate_limiter):
        """测试速率限制超出"""
        # 发送多个请求
        for _ in range(101):
            rate_limiter.record_request("user1", "api", "call")
        
        # 检查速率限制
        allowed, info = rate_limiter.check_rate_limit(
            "user1", "api", "call"
        )
        
        assert allowed is False
        assert info["allowed"] is False
    
    def test_get_user_state(self, rate_limiter):
        """测试获取用户状态"""
        # 记录一些请求
        rate_limiter.record_request("user1", "api", "call")
        rate_limiter.record_request("user1", "api", "call")
        
        state = rate_limiter.get_user_state("user1", "api", "call")
        
        assert state["request_count"] == 2
    
    def test_reset_user_state(self, rate_limiter):
        """测试重置用户状态"""
        # 记录一些请求
        rate_limiter.record_request("user1", "api", "call")
        rate_limiter.record_request("user1", "api", "call")
        
        # 重置状态
        reset_count = rate_limiter.reset_user_state("user1")
        
        assert reset_count == 1
        
        # 检查状态
        state = rate_limiter.get_user_state("user1", "api", "call")
        assert state["request_count"] == 0


class TestSecurityModule:
    """安全模块测试"""
    
    @pytest.mark.asyncio
    async def test_check_permission(self, security_module):
        """测试检查权限"""
        # 分配角色
        security_module.permission_manager.assign_role_to_user("user1", "user")
        
        # 检查权限
        granted = await security_module.check_permission(
            user_id="user1",
            resource=ResourceType.TOOL.value,
            action=PermissionAction.READ.value
        )
        
        assert granted is True
    
    @pytest.mark.asyncio
    async def test_request_approval(self, security_module):
        """测试请求审批"""
        request = await security_module.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool",
            reason="Need to run analysis"
        )
        
        assert request is not None
        assert request.status == ApprovalStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_approve_request(self, security_module):
        """测试批准请求"""
        # 创建请求
        request = await security_module.request_approval(
            requester_id="user1",
            action="execute",
            resource="tool"
        )
        
        # 批准请求
        success = await security_module.approve(
            request.request_id, "approver1"
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit(self, security_module):
        """测试检查速率限制"""
        allowed, info = await security_module.check_rate_limit(
            user_id="user1",
            resource="api",
            action="call"
        )
        
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_validate_input(self, security_module):
        """测试验证输入"""
        # 有效输入
        result = await security_module.validate_input(
            input_data={"name": "test", "age": 25},
            schema={
                "required": ["name", "age"],
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number", "minimum": 0}
                }
            }
        )
        
        assert result.valid is True
        
        # 无效输入
        result = await security_module.validate_input(
            input_data={"name": "test"},
            schema={
                "required": ["name", "age"],
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"}
                }
            }
        )
        
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_should_ask_human(self, security_module):
        """测试判断是否需要人工介入"""
        # 高风险操作
        context = {"action": "delete_file"}
        should_ask = await security_module.should_ask_human(context)
        assert should_ask is True
        
        # 低风险操作
        context = {"action": "read_file", "confidence": 1.0}
        should_ask = await security_module.should_ask_human(context)
        assert should_ask is False
    
    @pytest.mark.asyncio
    async def test_get_status(self, security_module):
        """测试获取状态"""
        status = await security_module.get_status()
        
        assert status["status"] == "ready"
        assert "config" in status
        assert "stats" in status
    
    @pytest.mark.asyncio
    async def test_get_stats(self, security_module):
        """测试获取统计信息"""
        # 执行一些操作
        await security_module.check_permission(
            "user1", "tool", "read"
        )
        await security_module.check_rate_limit(
            "user1", "api", "call"
        )
        
        stats = security_module.get_stats()
        
        assert stats["permission_checks"] > 0
        assert stats["rate_limit_checks"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
