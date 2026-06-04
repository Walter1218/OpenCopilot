# agents_md_module/models.py

"""
AGENTS.md 免疫机制模块数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import uuid
import time


class RuleType(Enum):
    """规则类型"""
    BEHAVIOR = "behavior"          # 行为规则
    CONSTRAINT = "constraint"      # 约束规则
    PREFERENCE = "preference"      # 偏好规则
    WORKFLOW = "workflow"          # 工作流规则
    SECURITY = "security"          # 安全规则


class RuleSeverity(Enum):
    """规则严重程度"""
    INFO = "info"                  # 信息
    WARNING = "warning"            # 警告
    ERROR = "error"                # 错误
    CRITICAL = "critical"          # 严重


class RuleScope(Enum):
    """规则作用域"""
    GLOBAL = "global"              # 全局规则
    PROJECT = "project"            # 项目规则
    SESSION = "session"            # 会话规则
    USER = "user"                  # 用户规则


class ViolationAction(Enum):
    """违规处理动作"""
    LOG = "log"                    # 仅记录
    WARN = "warn"                  # 警告
    BLOCK = "block"                # 阻止
    ASK_HUMAN = "ask_human"        # 询问人工
    AUTO_FIX = "auto_fix"          # 自动修复


@dataclass
class AgentRule:
    """Agent 规则"""
    rule_id: str
    name: str
    description: str
    rule_type: str
    severity: str = RuleSeverity.WARNING.value
    scope: str = RuleScope.PROJECT.value
    enabled: bool = True
    pattern: Optional[str] = None  # 匹配模式（正则表达式）
    condition: Optional[str] = None  # 条件表达式
    action: str = ViolationAction.LOG.value
    message: str = ""  # 违规提示消息
    examples: List[str] = field(default_factory=list)  # 示例
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """初始化规则 ID"""
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())


@dataclass
class RuleViolation:
    """规则违规记录"""
    violation_id: str
    rule_id: str
    rule_name: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    details: str = ""
    severity: str = RuleSeverity.WARNING.value
    action_taken: str = ViolationAction.LOG.value
    resolved: bool = False
    
    def __post_init__(self):
        """初始化违规 ID"""
        if not self.violation_id:
            self.violation_id = str(uuid.uuid4())


@dataclass
class AgentsMdConfig:
    """AGENTS.md 配置"""
    # 是否启用免疫机制
    enabled: bool = True
    # 规则文件路径
    rules_file: Optional[str] = None
    # 默认违规处理动作
    default_action: str = ViolationAction.LOG.value
    # 是否启用自动修复
    enable_auto_fix: bool = False
    # 是否启用规则继承
    enable_inheritance: bool = True
    # 规则作用域优先级
    scope_priority: List[str] = field(default_factory=lambda: [
        RuleScope.SESSION.value,
        RuleScope.USER.value,
        RuleScope.PROJECT.value,
        RuleScope.GLOBAL.value
    ])
    # 最大违规记录数
    max_violations: int = 1000
    # 规则缓存时间（秒）
    rules_cache_ttl: float = 300.0


@dataclass
class RuleContext:
    """规则检查上下文"""
    user_id: str = ""
    session_id: str = ""
    project_path: str = ""
    current_file: str = ""
    current_action: str = ""
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleCheckResult:
    """规则检查结果"""
    valid: bool
    violations: List[RuleViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def has_violations(self) -> bool:
        """是否有违规"""
        return len(self.violations) > 0
    
    @property
    def has_critical_violations(self) -> bool:
        """是否有严重违规"""
        return any(
            v.severity == RuleSeverity.CRITICAL.value
            for v in self.violations
        )


@dataclass
class ImmuneResponse:
    """免疫响应"""
    allowed: bool
    violations: List[RuleViolation] = field(default_factory=list)
    message: str = ""
    suggestions: List[str] = field(default_factory=list)
    auto_fix_applied: bool = False


def generate_rule_id() -> str:
    """生成规则 ID"""
    return str(uuid.uuid4())


def generate_violation_id() -> str:
    """生成违规 ID"""
    return str(uuid.uuid4())
