# planner/strategies/base.py

"""
规划策略基类

定义规划策略的通用接口。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..models import TaskStep, Plan, PlanRequest


class PlanningStrategy(ABC):
    """
    规划策略基类
    
    所有规划策略都应继承此类并实现抽象方法。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述"""
        pass
    
    @abstractmethod
    async def generate_steps(self, request: PlanRequest, 
                           llm_caller=None) -> List[TaskStep]:
        """
        生成执行步骤
        
        Args:
            request: 计划请求
            llm_caller: LLM 调用函数
            
        Returns:
            步骤列表
        """
        pass
    
    @abstractmethod
    def organize_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """
        组织步骤依赖关系
        
        Args:
            steps: 原始步骤列表
            
        Returns:
            添加依赖关系后的步骤列表
        """
        pass
    
    def estimate_duration(self, steps: List[TaskStep]) -> float:
        """
        估算执行时间
        
        Args:
            steps: 步骤列表
            
        Returns:
            预估时间（秒）
        """
        # 默认估算：每个步骤 30 秒
        return len(steps) * 30.0
    
    def validate_steps(self, steps: List[TaskStep]) -> List[str]:
        """
        验证步骤
        
        Args:
            steps: 步骤列表
            
        Returns:
            错误列表
        """
        errors = []
        
        if not steps:
            errors.append("步骤列表为空")
            return errors
        
        # 检查步骤 ID 唯一性
        step_ids = [step.step_id for step in steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("存在重复的步骤 ID")
        
        # 检查依赖关系有效性
        for step in steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"步骤 {step.step_id} 依赖的步骤 {dep_id} 不存在")
        
        return errors
