# security_module/models.py

"""
安全及 HITL 模块数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid
import time


class PermissionAction(Enum):
    """权限动作"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class ResourceType(Enum):
    """资源类型"""
    TOOL = "tool"
    FILE = "file"
    API = "api"
    SYSTEM = "system"
    CODE = "code"
    DATA = "data"


class ApprovalStatus(Enum):
    """审批状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class UrgencyLevel(Enum):
    """紧急程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(Enum):
    """审计动作"""
    PERMISSION_CHECK = "permission_check"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_APPROVE = "approval_approve"
    APPROVAL_REJECT = "approval_reject"
    RATE_LIMIT_CHECK = "rate_limit_check"
    INPUT_VALIDATION = "input_validation"
    SECURITY_VIOLATION = "security_violation"
    USER_ACTION = "user_action"


@dataclass
class Permission:
    """权限定义"""
    permission_id: str
    resource: str                          # 资源类型
    action: str                            # 动作类型
    conditions: Dict[str, Any] = field(default_factory=dict)  # 条件限制
    description: str = ""                  # 描述
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None     # 过期时间
    
    def __post_init__(self):
        """初始化权限 ID"""
        if not self.permission_id:
            self.permission_id = str(uuid.uuid4())
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    requester_id: str                      # 请求者 ID
    action: str                            # 请求的动作
    resource: str                          # 资源
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
    reason: str = ""                       # 原因
    urgency: str = UrgencyLevel.MEDIUM.value  # 紧急程度
    status: str = ApprovalStatus.PENDING.value  # 状态
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300)  # 5 分钟后过期
    approver_id: Optional[str] = None      # 审批者 ID
    approved_at: Optional[float] = None    # 审批时间
    rejection_reason: Optional[str] = None  # 拒绝原因
    
    def __post_init__(self):
        """初始化请求 ID"""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at
    
    def approve(self, approver_id: str):
        """批准请求"""
        self.status = ApprovalStatus.APPROVED.value
        self.approver_id = approver_id
        self.approved_at = time.time()
    
    def reject(self, approver_id: str, reason: str):
        """拒绝请求"""
        self.status = ApprovalStatus.REJECTED.value
        self.approver_id = approver_id
        self.rejection_reason = reason


@dataclass
class AuditEntry:
    """审计条目"""
    entry_id: str
    timestamp: float
    user_id: str
    action: str
    resource: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: str = ""                       # 操作结果
    ip_address: str = ""
    user_agent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化条目 ID"""
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())


@dataclass
class RateLimitRule:
    """速率限制规则"""
    rule_id: str
    resource: str                          # 资源
    action: str                            # 动作
    max_requests: int                      # 最大请求数
    time_window: float                     # 时间窗口（秒）
    description: str = ""
    
    def __post_init__(self):
        """初始化规则 ID"""
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())


@dataclass
class RateLimitState:
    """速率限制状态"""
    resource: str
    action: str
    requests: List[float] = field(default_factory=list)  # 请求时间戳列表
    
    def add_request(self):
        """添加请求"""
        self.requests.append(time.time())
    
    def cleanup(self, time_window: float):
        """清理过期请求"""
        now = time.time()
        self.requests = [t for t in self.requests if now - t <= time_window]
    
    def get_request_count(self) -> int:
        """获取请求数量"""
        return len(self.requests)


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HumanResponse:
    """人工响应"""
    response_id: str
    request_id: str
    responder_id: str
    response: str                          # 响应内容
    approved: bool = False                 # 是否批准
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """初始化响应 ID"""
        if not self.response_id:
            self.response_id = str(uuid.uuid4())


@dataclass
class SecurityConfig:
    """安全配置"""
    # 默认审批超时时间（秒）
    default_approval_timeout: float = 300.0
    # 是否启用速率限制
    enable_rate_limiting: bool = True
    # 是否启用审计日志
    enable_audit_logging: bool = True
    # 是否启用权限检查
    enable_permission_check: bool = True
    # 高风险操作列表
    high_risk_actions: List[str] = field(default_factory=lambda: [
        "delete_file", "execute_command", "modify_system",
        "access_sensitive_data", "change_permissions"
    ])
    # 需要审批的操作列表
    approval_required_actions: List[str] = field(default_factory=lambda: [
        "delete_file", "execute_command", "modify_system",
        "change_permissions", "access_network"
    ])


def generate_permission_id() -> str:
    """生成权限 ID"""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """生成请求 ID"""
    return str(uuid.uuid4())


def generate_entry_id() -> str:
    """生成审计条目 ID"""
    return str(uuid.uuid4())
