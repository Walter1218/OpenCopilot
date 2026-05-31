# skill_architecture/executor.py

import asyncio
from typing import Dict, List, Optional, Any
from .base import BaseSkill
from .registry import SkillRegistry
from .router import IntentRouter
from .models import (
    SkillContext, SkillResult, SkillStatus,
    ExecutionPlan, ExecutionMode
)


class SkillExecutor:
    """Skill 执行引擎"""
    
    def __init__(self, registry: SkillRegistry, router: IntentRouter):
        self._registry = registry
        self._router = router
        self._execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        context: SkillContext,
        skill_name: Optional[str] = None
    ) -> SkillResult:
        """
        执行单个 Skill
        
        Args:
            context: 执行上下文
            skill_name: 指定的 Skill 名称（可选）
        
        Returns:
            SkillResult: 执行结果
        """
        # 1. 确定要执行的 Skill
        if skill_name:
            skill = self._registry.get_skill(skill_name)
            if not skill:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Skill not found: {skill_name}",
                    status=SkillStatus.FAILED
                )
        else:
            # 自动路由
            routed_name = await self._router.route(context)
            if not routed_name:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"No skill found for intent: {context.intent}",
                    status=SkillStatus.FAILED
                )
            skill = self._registry.get_skill(routed_name)
        
        # 2. 执行 Skill
        try:
            skill.status = SkillStatus.RUNNING
            result = await asyncio.wait_for(
                skill.execute(context),
                timeout=30  # 默认超时 30 秒
            )
            skill.status = SkillStatus.COMPLETED
            
            # 记录执行历史
            self._record_execution(skill.metadata.name, context, result)
            
            return result
        except asyncio.TimeoutError:
            skill.status = SkillStatus.FAILED
            return SkillResult(
                success=False,
                data={},
                error="Execution timeout",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            skill.status = SkillStatus.FAILED
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def execute_chain(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> SkillResult:
        """
        链式执行多个 Skill
        
        Args:
            context: 执行上下文
            skill_names: Skill 名称列表
        
        Returns:
            SkillResult: 最后一个 Skill 的执行结果
        """
        if not skill_names:
            return SkillResult(
                success=False,
                data={},
                error="No skills specified",
                status=SkillStatus.FAILED
            )
        
        current_context = context
        last_result = None
        
        for skill_name in skill_names:
            skill = self._registry.get_skill(skill_name)
            if not skill:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Skill not found: {skill_name}",
                    status=SkillStatus.FAILED
                )
            
            # 执行当前 Skill
            result = await self.execute(current_context, skill_name)
            
            if not result.success:
                return result
            
            # 将结果添加到链式结果中
            current_context.chain_results.append({
                "skill": skill_name,
                "result": result.data
            })
            
            # 更新上下文数据，供下一个 Skill 使用
            current_context.input_data.update(result.data)
            last_result = result
        
        return last_result or SkillResult(
            success=False,
            data={},
            error="No skills executed",
            status=SkillStatus.FAILED
        )
    
    async def execute_parallel(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> Dict[str, SkillResult]:
        """
        并行执行多个 Skill
        
        Args:
            context: 执行上下文
            skill_names: Skill 名称列表
        
        Returns:
            Dict[str, SkillResult]: 每个 Skill 的执行结果
        """
        tasks = {}
        
        for skill_name in skill_names:
            skill = self._registry.get_skill(skill_name)
            if skill:
                tasks[skill_name] = self.execute(context, skill_name)
        
        if not tasks:
            return {}
        
        # 并行执行
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )
        
        # 组织结果
        result_dict = {}
        for skill_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                result_dict[skill_name] = SkillResult(
                    success=False,
                    data={},
                    error=str(result),
                    status=SkillStatus.FAILED
                )
            else:
                result_dict[skill_name] = result
        
        return result_dict
    
    async def execute_plan(
        self,
        context: SkillContext,
        plan: ExecutionPlan
    ) -> Dict[str, SkillResult]:
        """
        根据执行计划执行
        
        Args:
            context: 执行上下文
            plan: 执行计划
        
        Returns:
            Dict[str, SkillResult]: 执行结果
        """
        if plan.mode == ExecutionMode.SINGLE:
            if plan.skills:
                result = await self.execute(context, plan.skills[0])
                return {plan.skills[0]: result}
            return {}
        
        elif plan.mode == ExecutionMode.SEQUENTIAL:
            result = await self.execute_chain(context, plan.skills)
            return {plan.skills[-1]: result} if plan.skills else {}
        
        elif plan.mode == ExecutionMode.PARALLEL:
            return await self.execute_parallel(context, plan.skills)
        
        elif plan.mode == ExecutionMode.PIPELINE:
            # 流水线执行：顺序执行，但每个 Skill 的输出作为下一个的输入
            return await self._execute_pipeline(context, plan.skills)
        
        return {}
    
    async def _execute_pipeline(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> Dict[str, SkillResult]:
        """流水线执行"""
        results = {}
        current_context = context
        
        for skill_name in skill_names:
            result = await self.execute(current_context, skill_name)
            results[skill_name] = result
            
            if not result.success:
                break
            
            # 更新上下文
            current_context.input_data.update(result.data)
        
        return results
    
    def _record_execution(
        self,
        skill_name: str,
        context: SkillContext,
        result: SkillResult
    ) -> None:
        """记录执行历史"""
        self._execution_history.append({
            "skill": skill_name,
            "intent": context.intent,
            "success": result.success,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()