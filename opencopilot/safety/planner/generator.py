# planner/generator.py

"""
计划生成器

负责根据任务生成执行计划。
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable

from .models import TaskStep, Plan, PlanRequest, PlanStatus, generate_plan_id
from .strategies import (
    PlanningStrategy,
    SequentialStrategy,
    ParallelStrategy,
    AdaptiveStrategy,
    ReActStrategy
)


# 策略注册表
STRATEGIES = {
    "sequential": SequentialStrategy,
    "parallel": ParallelStrategy,
    "adaptive": AdaptiveStrategy,
    "react": ReActStrategy
}


class PlanGenerator:
    """
    计划生成器
    
    根据任务和策略生成执行计划。
    """
    
    def __init__(self, llm_caller: Optional[Callable[..., Awaitable[str]]] = None):
        """
        初始化计划生成器
        
        Args:
            llm_caller: LLM 调用函数，接受 prompt 返回响应
        """
        self.llm_caller = llm_caller
        self._strategies = {name: cls() for name, cls in STRATEGIES.items()}
    
    def register_strategy(self, name: str, strategy: PlanningStrategy):
        """
        注册规划策略
        
        Args:
            name: 策略名称
            strategy: 策略实例
        """
        self._strategies[name] = strategy
    
    def get_strategy(self, name: str) -> Optional[PlanningStrategy]:
        """
        获取规划策略
        
        Args:
            name: 策略名称
            
        Returns:
            策略实例，如果不存在返回 None
        """
        return self._strategies.get(name)
    
    @property
    def available_strategies(self) -> List[str]:
        """获取可用策略列表"""
        return list(self._strategies.keys())
    
    async def generate(self, request: PlanRequest) -> Plan:
        """
        生成执行计划
        
        Args:
            request: 计划请求
            
        Returns:
            执行计划
        """
        # 获取策略
        strategy = self.get_strategy(request.strategy)
        if strategy is None:
            raise ValueError(f"未知的规划策略: {request.strategy}")
        
        # 生成步骤
        steps = await strategy.generate_steps(request, self.llm_caller)
        
        if not steps:
            raise ValueError("无法生成执行步骤")
        
        # 验证步骤
        errors = strategy.validate_steps(steps)
        if errors:
            raise ValueError(f"步骤验证失败: {errors}")
        
        # 组织依赖关系
        steps = strategy.organize_dependencies(steps)
        
        # 估算执行时间
        estimated_duration = strategy.estimate_duration(steps)
        
        # 创建计划
        plan = Plan(
            plan_id=generate_plan_id(),
            task=request.task,
            steps=steps,
            status=PlanStatus.DRAFT,
            estimated_duration=estimated_duration,
            confidence=0.8,
            metadata={
                "strategy": request.strategy,
                "context": request.context,
                "constraints": request.constraints
            }
        )
        
        return plan
    
    async def generate_with_fallback(self, request: PlanRequest) -> Plan:
        """
        生成执行计划（带回退机制）
        
        如果首选策略失败，尝试其他策略。
        """
        strategies_to_try = [request.strategy] + [
            s for s in self.available_strategies if s != request.strategy
        ]
        
        last_error = None
        for strategy_name in strategies_to_try:
            try:
                request.strategy = strategy_name
                return await self.generate(request)
            except Exception as e:
                last_error = e
                continue
        
        raise ValueError(f"所有策略都失败: {last_error}")
