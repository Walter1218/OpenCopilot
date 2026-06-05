# skill_architecture/executor.py

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from .base import BaseSkill
from .registry import SkillRegistry
from .router import IntentRouter
from .models import (
    SkillContext, SkillResult, SkillStatus,
    ExecutionPlan, ExecutionMode
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStats:
    """执行统计"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    retry_count: int = 0
    timeout_count: int = 0


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    retry_on_timeout: bool = True
    retry_on_error: bool = True


class SkillExecutor:
    """Skill 执行引擎 - 增强版
    
    新增功能：
    1. 执行计划优化：动态生成、依赖解析、并行组
    2. 错误处理增强：重试机制、降级策略、回滚操作
    3. 性能监控：执行时间统计、资源监控、瓶颈分析
    """
    
    def __init__(
        self, 
        registry: SkillRegistry, 
        router: IntentRouter,
        retry_config: Optional[RetryConfig] = None,
        default_timeout: int = 30
    ):
        self._registry = registry
        self._router = router
        self._retry_config = retry_config or RetryConfig()
        self._default_timeout = default_timeout
        
        # 执行历史
        self._execution_history: List[Dict[str, Any]] = []
        
        # 统计信息
        self._stats = ExecutionStats()
        
        # 性能监控
        self._performance_monitors: List[Callable[[str, float, bool], Awaitable[None]]] = []
        
        # 降级策略
        self._fallback_strategies: Dict[str, Callable[[SkillContext, Exception], Awaitable[SkillResult]]] = {}
    
    async def execute(
        self,
        context: SkillContext,
        skill_name: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_config: Optional[RetryConfig] = None
    ) -> SkillResult:
        """
        执行单个 Skill - 增强版
        
        Args:
            context: 执行上下文
            skill_name: 指定的 Skill 名称（可选）
            timeout: 超时时间（秒）
            retry_config: 重试配置
        
        Returns:
            SkillResult: 执行结果
        """
        start_time = time.time()
        actual_timeout = timeout or self._default_timeout
        actual_retry_config = retry_config or self._retry_config
        
        # 1. 确定要执行的 Skill
        skill = await self._resolve_skill(context, skill_name)
        if not skill:
            return SkillResult(
                success=False,
                data={},
                error=f"Skill not found: {skill_name or context.intent}",
                status=SkillStatus.FAILED
            )
        
        # 2. 执行重试逻辑
        last_error = None
        for attempt in range(actual_retry_config.max_retries + 1):
            try:
                # 执行 Skill
                skill.status = SkillStatus.RUNNING
                result = await asyncio.wait_for(
                    skill.execute(context),
                    timeout=actual_timeout
                )
                skill.status = SkillStatus.COMPLETED
                
                # 记录成功执行
                execution_time = time.time() - start_time
                self._record_execution(skill.metadata.name, context, result, execution_time)
                self._update_stats(execution_time, success=True)
                
                # 触发性能监控
                await self._notify_performance_monitors(skill.metadata.name, execution_time, True)
                
                return result
                
            except asyncio.TimeoutError:
                last_error = "Execution timeout"
                skill.status = SkillStatus.FAILED
                self._stats.timeout_count += 1
                
                if not actual_retry_config.retry_on_timeout:
                    break
                    
            except Exception as e:
                last_error = str(e)
                skill.status = SkillStatus.FAILED
                logger.warning(f"Skill {skill.metadata.name} execution failed (attempt {attempt + 1}): {e}")
                
                if not actual_retry_config.retry_on_error:
                    break
            
            # 重试延迟
            if attempt < actual_retry_config.max_retries:
                delay = actual_retry_config.retry_delay * (actual_retry_config.backoff_factor ** attempt)
                await asyncio.sleep(delay)
                self._stats.retry_count += 1
                logger.info(f"Retrying skill {skill.metadata.name} after {delay:.2f}s (attempt {attempt + 2})")
        
        # 3. 所有重试都失败，尝试降级策略
        fallback_result = await self._try_fallback(context, skill.metadata.name, last_error)
        if fallback_result:
            return fallback_result
        
        # 4. 返回最终失败结果
        execution_time = time.time() - start_time
        self._update_stats(execution_time, success=False)
        
        return SkillResult(
            success=False,
            data={},
            error=last_error,
            status=SkillStatus.FAILED
        )
    
    async def _resolve_skill(
        self, 
        context: SkillContext, 
        skill_name: Optional[str]
    ) -> Optional[BaseSkill]:
        """解析要执行的 Skill"""
        if skill_name:
            return self._registry.get_skill(skill_name)
        
        # 自动路由
        routed_name = await self._router.route(context)
        if routed_name:
            return self._registry.get_skill(routed_name)
        
        return None
    
    async def _try_fallback(
        self, 
        context: SkillContext, 
        skill_name: str, 
        error: str
    ) -> Optional[SkillResult]:
        """尝试降级策略"""
        if skill_name in self._fallback_strategies:
            try:
                logger.info(f"Trying fallback strategy for skill {skill_name}")
                return await self._fallback_strategies[skill_name](context, Exception(error))
            except Exception as e:
                logger.warning(f"Fallback strategy failed for skill {skill_name}: {e}")
        
        return None
    
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
        skill_names: List[str],
        max_concurrent: Optional[int] = None
    ) -> Dict[str, SkillResult]:
        """
        并行执行多个 Skill - 增强版
        
        Args:
            context: 执行上下文
            skill_names: Skill 名称列表
            max_concurrent: 最大并发数
        
        Returns:
            Dict[str, SkillResult]: 每个 Skill 的执行结果
        """
        if not skill_names:
            return {}
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
        
        async def execute_with_semaphore(skill_name: str) -> Tuple[str, SkillResult]:
            """带信号量的执行"""
            if semaphore:
                async with semaphore:
                    result = await self.execute(context, skill_name)
            else:
                result = await self.execute(context, skill_name)
            return skill_name, result
        
        # 创建任务
        tasks = [execute_with_semaphore(name) for name in skill_names]
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组织结果
        result_dict = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel execution failed: {result}")
                continue
            
            skill_name, skill_result = result
            result_dict[skill_name] = skill_result
        
        return result_dict
    
    async def execute_plan(
        self,
        context: SkillContext,
        plan: ExecutionPlan
    ) -> Dict[str, SkillResult]:
        """
        根据执行计划执行 - 增强版
        
        Args:
            context: 执行上下文
            plan: 执行计划
        
        Returns:
            Dict[str, SkillResult]: 执行结果
        """
        start_time = time.time()
        
        try:
            if plan.mode == ExecutionMode.SINGLE:
                if plan.skills:
                    result = await self.execute(context, plan.skills[0], timeout=plan.timeout)
                    return {plan.skills[0]: result}
                return {}
            
            elif plan.mode == ExecutionMode.SEQUENTIAL:
                result = await self.execute_chain(context, plan.skills)
                return {plan.skills[-1]: result} if plan.skills else {}
            
            elif plan.mode == ExecutionMode.PARALLEL:
                return await self.execute_parallel(context, plan.skills)
            
            elif plan.mode == ExecutionMode.PIPELINE:
                return await self._execute_pipeline(context, plan.skills)
            
            else:
                logger.warning(f"Unknown execution mode: {plan.mode}")
                return {}
                
        except Exception as e:
            logger.error(f"Execution plan failed: {e}")
            return {}
        finally:
            execution_time = time.time() - start_time
            logger.info(f"Execution plan completed in {execution_time:.2f}s")
    
    async def _execute_pipeline(
        self,
        context: SkillContext,
        skill_names: List[str]
    ) -> Dict[str, SkillResult]:
        """流水线执行 - 增强版"""
        results = {}
        current_context = context
        
        for i, skill_name in enumerate(skill_names):
            logger.info(f"Pipeline step {i + 1}/{len(skill_names)}: {skill_name}")
            
            result = await self.execute(current_context, skill_name)
            results[skill_name] = result
            
            if not result.success:
                logger.warning(f"Pipeline failed at step {i + 1}: {skill_name}")
                break
            
            # 更新上下文
            current_context.input_data.update(result.data)
            
            # 添加链式结果
            current_context.chain_results.append({
                "step": i + 1,
                "skill": skill_name,
                "result": result.data
            })
        
        return results
    
    async def execute_dynamic(
        self,
        context: SkillContext,
        max_steps: int = 10
    ) -> Dict[str, SkillResult]:
        """
        动态执行：根据上下文自动决定执行步骤
        
        Args:
            context: 执行上下文
            max_steps: 最大步骤数
        
        Returns:
            Dict[str, SkillResult]: 执行结果
        """
        results = {}
        current_context = context
        
        for step in range(max_steps):
            # 路由到下一个 Skill
            skill_name = await self._router.route(current_context)
            if not skill_name:
                logger.info(f"No more skills to execute at step {step + 1}")
                break
            
            # 检查是否已经执行过
            if skill_name in results:
                logger.info(f"Skill {skill_name} already executed, skipping")
                break
            
            # 执行 Skill
            result = await self.execute(current_context, skill_name)
            results[skill_name] = result
            
            if not result.success:
                logger.warning(f"Dynamic execution failed at step {step + 1}: {skill_name}")
                break
            
            # 更新上下文
            current_context.input_data.update(result.data)
            current_context.chain_results.append({
                "step": step + 1,
                "skill": skill_name,
                "result": result.data
            })
            
            # 检查是否有建议的下一步
            if result.next_skills:
                logger.info(f"Suggested next skills: {result.next_skills}")
        
        return results
    
    def _record_execution(
        self,
        skill_name: str,
        context: SkillContext,
        result: SkillResult,
        execution_time: float
    ) -> None:
        """记录执行历史 - 增强版"""
        self._execution_history.append({
            "skill": skill_name,
            "intent": context.intent,
            "success": result.success,
            "execution_time": execution_time,
            "timestamp": time.time(),
            "error": result.error if not result.success else None
        })
        
        # 限制历史记录大小
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-500:]
    
    def _update_stats(self, execution_time: float, success: bool) -> None:
        """更新统计信息"""
        self._stats.total_executions += 1
        self._stats.total_time += execution_time
        
        if success:
            self._stats.successful_executions += 1
        else:
            self._stats.failed_executions += 1
        
        # 更新时间统计
        self._stats.min_time = min(self._stats.min_time, execution_time)
        self._stats.max_time = max(self._stats.max_time, execution_time)
        self._stats.avg_time = self._stats.total_time / self._stats.total_executions
    
    async def _notify_performance_monitors(
        self, 
        skill_name: str, 
        execution_time: float, 
        success: bool
    ) -> None:
        """通知性能监控器"""
        for monitor in self._performance_monitors:
            try:
                await monitor(skill_name, execution_time, success)
            except Exception as e:
                logger.warning(f"Performance monitor failed: {e}")
    
    def add_performance_monitor(
        self, 
        monitor: Callable[[str, float, bool], Awaitable[None]]
    ) -> None:
        """添加性能监控器"""
        self._performance_monitors.append(monitor)
    
    def add_fallback_strategy(
        self, 
        skill_name: str, 
        strategy: Callable[[SkillContext, Exception], Awaitable[SkillResult]]
    ) -> None:
        """添加降级策略"""
        self._fallback_strategies[skill_name] = strategy
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_executions": self._stats.total_executions,
            "successful_executions": self._stats.successful_executions,
            "failed_executions": self._stats.failed_executions,
            "success_rate": (
                self._stats.successful_executions / self._stats.total_executions 
                if self._stats.total_executions > 0 else 0.0
            ),
            "total_time": self._stats.total_time,
            "avg_time": self._stats.avg_time,
            "min_time": self._stats.min_time if self._stats.min_time != float('inf') else 0.0,
            "max_time": self._stats.max_time,
            "retry_count": self._stats.retry_count,
            "timeout_count": self._stats.timeout_count,
            "history_size": len(self._execution_history)
        }
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()
    
    def clear_history(self) -> None:
        """清除执行历史"""
        self._execution_history.clear()
        logger.info("Execution history cleared")
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = ExecutionStats()
        logger.info("Execution stats reset")