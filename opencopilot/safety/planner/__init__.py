# planner/__init__.py

"""
规划器模块 (Planner Module)

将复杂任务分解为可执行步骤，生成执行计划。

核心功能：
- PlanGenerator: 计划生成器
- PlanValidator: 计划验证器
- PlanOptimizer: 计划优化器
- Planner: 规划器核心类

规划策略：
- SequentialStrategy: 顺序执行策略
- ParallelStrategy: 并行执行策略
- AdaptiveStrategy: 自适应策略
- ReActStrategy: ReAct 策略
"""

from .models import (
    TaskStep, Plan, PlanRequest, PlanStatus, StepStatus, StepType,
    ValidationResult, DurationEstimate,
    generate_plan_id, generate_step_id
)
from .generator import PlanGenerator
from .validator import PlanValidator
from .optimizer import PlanOptimizer
from .core import Planner
from .strategies import (
    PlanningStrategy,
    SequentialStrategy,
    ParallelStrategy,
    AdaptiveStrategy,
    ReActStrategy
)

__version__ = "1.0.0"

__all__ = [
    # 核心类
    "Planner",
    "PlanGenerator",
    "PlanValidator",
    "PlanOptimizer",
    
    # 数据模型
    "TaskStep",
    "Plan",
    "PlanRequest",
    "PlanStatus",
    "StepStatus",
    "StepType",
    "ValidationResult",
    "DurationEstimate",
    
    # 策略
    "PlanningStrategy",
    "SequentialStrategy",
    "ParallelStrategy",
    "AdaptiveStrategy",
    "ReActStrategy",
    
    # 工具函数
    "generate_plan_id",
    "generate_step_id"
]
