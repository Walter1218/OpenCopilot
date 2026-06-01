# planner/models.py

"""
规划器模块数据模型定义

定义规划器模块使用的所有数据结构。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


class StepType(Enum):
    """步骤类型"""
    LLM_CALL = "llm_call"              # LLM 调用
    TOOL_CALL = "tool_call"            # 工具调用
    CODE_EXECUTION = "code_execution"  # 代码执行
    HUMAN_APPROVAL = "human_approval"  # 人工审批
    CONDITIONAL = "conditional"        # 条件判断
    PARALLEL = "parallel"              # 并行执行


class PlanStatus(Enum):
    """计划状态"""
    DRAFT = "draft"           # 草稿
    VALIDATED = "validated"   # 已验证
    EXECUTING = "executing"   # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消
    PAUSED = "paused"         # 已暂停


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 已跳过
    WAITING = "waiting"       # 等待依赖


@dataclass
class TaskStep:
    """
    任务步骤
    
    Attributes:
        step_id: 步骤唯一标识
        step_name: 步骤名称
        step_type: 步骤类型
        description: 步骤描述
        tool_id: 工具 ID（仅 tool_call 类型）
        parameters: 步骤参数
        dependencies: 依赖的步骤 ID 列表
        timeout: 超时时间（秒）
        retry_count: 重试次数
        is_critical: 是否关键步骤
        requires_approval: 是否需要人工审批
        output_schema: 输出格式定义
        status: 步骤状态
        result: 执行结果
        error: 错误信息
        started_at: 开始时间
        completed_at: 完成时间
    """
    step_id: str
    step_name: str
    step_type: StepType
    description: str
    tool_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 300.0
    retry_count: int = 3
    is_critical: bool = False
    requires_approval: bool = False
    output_schema: Optional[Dict[str, Any]] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "step_type": self.step_type.value,
            "description": self.description,
            "tool_id": self.tool_id,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "is_critical": self.is_critical,
            "requires_approval": self.requires_approval,
            "output_schema": self.output_schema,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskStep':
        """从字典创建"""
        data = data.copy()
        data['step_type'] = StepType(data['step_type'])
        data['status'] = StepStatus(data.get('status', 'pending'))
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class Plan:
    """
    执行计划
    
    Attributes:
        plan_id: 计划唯一标识
        task: 任务描述
        steps: 步骤列表
        status: 计划状态
        estimated_duration: 预估执行时间（秒）
        confidence: 置信度（0-1）
        metadata: 元信息
        created_at: 创建时间
        updated_at: 更新时间
        current_step_index: 当前执行步骤索引
        error: 错误信息
    """
    plan_id: str
    task: str
    steps: List[TaskStep]
    status: PlanStatus = PlanStatus.DRAFT
    estimated_duration: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    current_step_index: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "task": self.task,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "estimated_duration": self.estimated_duration,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_step_index": self.current_step_index,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """从字典创建"""
        data = data.copy()
        data['steps'] = [TaskStep.from_dict(s) for s in data['steps']]
        data['status'] = PlanStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    @property
    def current_step(self) -> Optional[TaskStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    @property
    def progress(self) -> float:
        """获取执行进度（0-1）"""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return completed / len(self.steps)
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in [PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED]
    
    def get_step(self, step_id: str) -> Optional[TaskStep]:
        """根据 ID 获取步骤"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_dependencies(self, step_id: str) -> List[TaskStep]:
        """获取步骤的依赖步骤"""
        step = self.get_step(step_id)
        if not step:
            return []
        return [self.get_step(dep_id) for dep_id in step.dependencies if self.get_step(dep_id)]


@dataclass
class ValidationResult:
    """
    验证结果
    
    Attributes:
        is_valid: 是否有效
        errors: 错误列表
        warnings: 警告列表
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class DurationEstimate:
    """
    时间估算
    
    Attributes:
        min_duration: 最小时间（秒）
        max_duration: 最大时间（秒）
        expected_duration: 预期时间（秒）
        confidence: 置信度（0-1）
    """
    min_duration: float
    max_duration: float
    expected_duration: float
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "expected_duration": self.expected_duration,
            "confidence": self.confidence
        }


@dataclass
class PlanRequest:
    """
    计划请求
    
    Attributes:
        task: 任务描述
        context: 上下文信息
        strategy: 规划策略
        max_steps: 最大步骤数
        constraints: 约束条件
    """
    task: str
    context: Dict[str, Any] = field(default_factory=dict)
    strategy: str = "sequential"
    max_steps: int = 20
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task": self.task,
            "context": self.context,
            "strategy": self.strategy,
            "max_steps": self.max_steps,
            "constraints": self.constraints
        }


def generate_plan_id() -> str:
    """生成计划 ID"""
    return f"plan_{uuid.uuid4().hex[:12]}"


def generate_step_id() -> str:
    """生成步骤 ID"""
    return f"step_{uuid.uuid4().hex[:12]}"
