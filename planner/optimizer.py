# planner/optimizer.py

"""
计划优化器

优化执行计划，提升执行效率。
"""

from typing import List, Dict, Any, Set

from .models import TaskStep, Plan, StepType, StepStatus, DurationEstimate


class PlanOptimizer:
    """
    计划优化器
    
    优化执行计划，包括：
    - 合并可并行步骤
    - 优化执行顺序
    - 估算执行时间
    - 移除冗余步骤
    """
    
    def optimize(self, plan: Plan) -> Plan:
        """
        优化计划
        
        Args:
            plan: 原始计划
            
        Returns:
            优化后的计划
        """
        # 1. 移除冗余步骤
        plan = self._remove_redundant_steps(plan)
        
        # 2. 合并可并行步骤
        plan = self._merge_parallel_steps(plan)
        
        # 3. 优化依赖关系
        plan = self._optimize_dependencies(plan)
        
        # 4. 更新预估时间
        plan.estimated_duration = self.estimate_duration(plan.steps).expected_duration
        
        return plan
    
    def estimate_duration(self, steps: List[TaskStep]) -> DurationEstimate:
        """
        估算执行时间
        
        Args:
            steps: 步骤列表
            
        Returns:
            时间估算
        """
        if not steps:
            return DurationEstimate(0, 0, 0, 1.0)
        
        # 基础时间估算（秒）
        base_times = {
            StepType.LLM_CALL: 10.0,
            StepType.TOOL_CALL: 5.0,
            StepType.CODE_EXECUTION: 30.0,
            StepType.HUMAN_APPROVAL: 60.0,
            StepType.CONDITIONAL: 2.0,
            StepType.PARALLEL: 0.0
        }
        
        # 计算每个步骤的时间
        step_times = []
        for step in steps:
            base_time = base_times.get(step.step_type, 10.0)
            # 考虑重试
            max_time = base_time * (step.retry_count + 1)
            step_times.append((base_time, max_time))
        
        # 计算总时间
        min_duration = sum(t[0] for t in step_times)
        max_duration = sum(t[1] for t in step_times)
        expected_duration = min_duration * 1.2  # 预期时间 = 最小时间 * 1.2
        
        return DurationEstimate(
            min_duration=min_duration,
            max_duration=max_duration,
            expected_duration=expected_duration,
            confidence=0.8
        )
    
    def _remove_redundant_steps(self, plan: Plan) -> Plan:
        """移除冗余步骤"""
        if len(plan.steps) <= 1:
            return plan
        
        # 检查是否有重复的步骤
        seen_descriptions: Set[str] = set()
        unique_steps = []
        
        for step in plan.steps:
            # 使用步骤描述作为去重依据
            desc_key = f"{step.step_type.value}:{step.description}"
            if desc_key not in seen_descriptions:
                seen_descriptions.add(desc_key)
                unique_steps.append(step)
        
        plan.steps = unique_steps
        return plan
    
    def _merge_parallel_steps(self, plan: Plan) -> Plan:
        """合并可并行步骤"""
        if len(plan.steps) <= 1:
            return plan
        
        # 找出可并行的独立步骤
        independent_steps = []
        dependent_steps = []
        
        for step in plan.steps:
            if not step.dependencies:
                independent_steps.append(step)
            else:
                dependent_steps.append(step)
        
        # 如果有多个独立步骤，创建一个并行组
        if len(independent_steps) > 1:
            # 保持原步骤，但标记为可并行
            for step in independent_steps:
                step.parameters['_parallelizable'] = True
        
        return plan
    
    def _optimize_dependencies(self, plan: Plan) -> Plan:
        """优化依赖关系"""
        # 移除间接依赖
        # 例如：A -> B -> C，如果 A -> C 也存在，则移除 A -> C
        for step in plan.steps:
            direct_deps = set(step.dependencies)
            transitive_deps = set()
            
            # 获取传递依赖
            for dep_id in direct_deps:
                dep_step = plan.get_step(dep_id)
                if dep_step:
                    transitive_deps.update(dep_step.dependencies)
            
            # 移除间接依赖
            step.dependencies = [d for d in step.dependencies if d not in transitive_deps or d in direct_deps]
        
        return plan
    
    def get_execution_order(self, plan: Plan) -> List[List[TaskStep]]:
        """
        获取执行顺序
        
        Returns:
            执行顺序列表，每个元素是一组可并行执行的步骤
        """
        if not plan.steps:
            return []
        
        # 拓扑排序
        in_degree: Dict[str, int] = {step.step_id: 0 for step in plan.steps}
        graph: Dict[str, List[str]] = {step.step_id: [] for step in plan.steps}
        
        # 构建图
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(step.step_id)
                    in_degree[step.step_id] += 1
        
        # BFS 拓扑排序
        execution_order = []
        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        
        while queue:
            # 当前层级可并行执行
            current_level = []
            next_queue = []
            
            for step_id in queue:
                step = plan.get_step(step_id)
                if step:
                    current_level.append(step)
                
                # 更新入度
                for neighbor in graph[step_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            
            execution_order.append(current_level)
            queue = next_queue
        
        return execution_order
