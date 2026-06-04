# planner/core.py

"""
规划器核心模块

提供规划器的核心功能。
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable
from datetime import datetime

from .models import (
    TaskStep, Plan, PlanRequest, PlanStatus, StepStatus,
    ValidationResult, DurationEstimate
)
from .generator import PlanGenerator
from .validator import PlanValidator
from .optimizer import PlanOptimizer


class Planner:
    """
    规划器模块
    
    将复杂任务分解为可执行步骤，生成执行计划。
    
    核心功能：
    - create_plan: 创建执行计划
    - decompose_task: 任务分解
    - validate_plan: 验证计划
    - optimize_plan: 优化计划
    - estimate_duration: 估算执行时间
    - replan: 重新规划
    """
    
    def __init__(self, llm_caller: Optional[Callable[..., Awaitable[str]]] = None):
        """
        初始化规划器
        
        Args:
            llm_caller: LLM 调用函数
        """
        self.llm_caller = llm_caller
        self.generator = PlanGenerator(llm_caller)
        self.validator = PlanValidator()
        self.optimizer = PlanOptimizer()
        
        # 计划存储
        self._plans: Dict[str, Plan] = {}
    
    @property
    def available_strategies(self) -> List[str]:
        """获取可用策略列表"""
        return self.generator.available_strategies
    
    async def create_plan(self, task: str, context: Dict[str, Any] = None,
                         strategy: str = "sequential",
                         max_steps: int = 20) -> Plan:
        """
        创建执行计划
        
        Args:
            task: 任务描述
            context: 上下文信息
            strategy: 规划策略
            max_steps: 最大步骤数
            
        Returns:
            执行计划
        """
        request = PlanRequest(
            task=task,
            context=context or {},
            strategy=strategy,
            max_steps=max_steps
        )
        
        # 生成计划
        plan = await self.generator.generate(request)
        
        # 验证计划
        validation = self.validator.validate(plan)
        if not validation.is_valid:
            raise ValueError(f"计划验证失败: {validation.errors}")
        
        # 优化计划
        plan = self.optimizer.optimize(plan)
        
        # 存储计划
        self._plans[plan.plan_id] = plan
        
        return plan
    
    async def decompose_task(self, task: str, strategy: str = "sequential") -> List[TaskStep]:
        """
        分解任务（不创建完整计划）
        
        Args:
            task: 任务描述
            strategy: 规划策略
            
        Returns:
            步骤列表
        """
        request = PlanRequest(task=task, strategy=strategy)
        
        # 获取策略
        planning_strategy = self.generator.get_strategy(strategy)
        if planning_strategy is None:
            raise ValueError(f"未知的规划策略: {strategy}")
        
        # 生成步骤
        steps = await planning_strategy.generate_steps(request, self.llm_caller)
        
        # 组织依赖关系
        steps = planning_strategy.organize_dependencies(steps)
        
        return steps
    
    def validate_plan(self, plan: Plan) -> ValidationResult:
        """
        验证计划
        
        Args:
            plan: 执行计划
            
        Returns:
            验证结果
        """
        return self.validator.validate(plan)
    
    def optimize_plan(self, plan: Plan) -> Plan:
        """
        优化计划
        
        Args:
            plan: 原始计划
            
        Returns:
            优化后的计划
        """
        return self.optimizer.optimize(plan)
    
    def estimate_duration(self, plan: Plan) -> DurationEstimate:
        """
        估算执行时间
        
        Args:
            plan: 执行计划
            
        Returns:
            时间估算
        """
        return self.optimizer.estimate_duration(plan.steps)
    
    async def replan(self, plan_id: str, feedback: str = None,
                    error: str = None) -> Plan:
        """
        重新规划
        
        Args:
            plan_id: 原计划 ID
            feedback: 反馈信息
            error: 错误信息
            
        Returns:
            新的执行计划
        """
        # 获取原计划
        original_plan = self.get_plan(plan_id)
        if original_plan is None:
            raise ValueError(f"计划不存在: {plan_id}")
        
        # 构建上下文
        context = original_plan.metadata.get("context", {})
        if feedback:
            context["feedback"] = feedback
        if error:
            context["error"] = error
        context["original_plan"] = original_plan.to_dict()
        
        # 创建新计划
        new_plan = await self.create_plan(
            task=original_plan.task,
            context=context,
            strategy=original_plan.metadata.get("strategy", "sequential")
        )
        
        # 标记原计划为失败
        original_plan.status = PlanStatus.FAILED
        original_plan.error = f"重新规划: {feedback or error}"
        
        return new_plan
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """
        获取计划
        
        Args:
            plan_id: 计划 ID
            
        Returns:
            执行计划，如果不存在返回 None
        """
        return self._plans.get(plan_id)
    
    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Plan]:
        """
        列出计划
        
        Args:
            status: 过滤状态
            
        Returns:
            计划列表
        """
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans
    
    def delete_plan(self, plan_id: str) -> bool:
        """
        删除计划
        
        Args:
            plan_id: 计划 ID
            
        Returns:
            是否删除成功
        """
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False
    
    def update_step_status(self, plan_id: str, step_id: str,
                          status: StepStatus, result: Any = None,
                          error: str = None) -> bool:
        """
        更新步骤状态
        
        Args:
            plan_id: 计划 ID
            step_id: 步骤 ID
            status: 新状态
            result: 执行结果
            error: 错误信息
            
        Returns:
            是否更新成功
        """
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        
        step = plan.get_step(step_id)
        if step is None:
            return False
        
        step.status = status
        step.result = result
        step.error = error
        
        if status == StepStatus.RUNNING:
            step.started_at = datetime.now()
        elif status in [StepStatus.COMPLETED, StepStatus.FAILED]:
            step.completed_at = datetime.now()
        
        # 更新计划状态
        self._update_plan_status(plan)
        
        return True
    
    def _update_plan_status(self, plan: Plan):
        """更新计划状态"""
        if not plan.steps:
            return
        
        # 检查是否有失败的步骤
        failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
        if failed_steps:
            # 检查是否有关键步骤失败
            critical_failed = [s for s in failed_steps if s.is_critical]
            if critical_failed:
                plan.status = PlanStatus.FAILED
                plan.error = f"关键步骤失败: {critical_failed[0].step_name}"
            return
        
        # 检查是否所有步骤都完成
        completed_steps = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
        if len(completed_steps) == len(plan.steps):
            plan.status = PlanStatus.COMPLETED
        
        plan.updated_at = datetime.now()
