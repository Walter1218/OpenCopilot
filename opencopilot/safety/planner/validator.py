# planner/validator.py

"""
计划验证器

验证执行计划的有效性。
"""

from typing import List, Dict, Any, Set

from .models import TaskStep, Plan, ValidationResult, StepType


class PlanValidator:
    """
    计划验证器
    
    验证执行计划的完整性、一致性和可行性。
    """
    
    def validate(self, plan: Plan) -> ValidationResult:
        """
        验证计划
        
        Args:
            plan: 执行计划
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        
        # 基本验证
        errors.extend(self._validate_basic(plan))
        
        # 步骤验证
        errors.extend(self._validate_steps(plan.steps))
        
        # 依赖关系验证
        errors.extend(self._validate_dependencies(plan.steps))
        
        # 工具可用性验证
        warnings.extend(self._validate_tool_availability(plan.steps))
        
        # 复杂度验证
        warnings.extend(self._validate_complexity(plan))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_basic(self, plan: Plan) -> List[str]:
        """基本验证"""
        errors = []
        
        if not plan.plan_id:
            errors.append("计划 ID 不能为空")
        
        if not plan.task:
            errors.append("任务描述不能为空")
        
        if not plan.steps:
            errors.append("步骤列表不能为空")
        
        return errors
    
    def _validate_steps(self, steps: List[TaskStep]) -> List[str]:
        """步骤验证"""
        errors = []
        
        if not steps:
            return errors
        
        # 检查步骤 ID 唯一性
        step_ids: Set[str] = set()
        for step in steps:
            if step.step_id in step_ids:
                errors.append(f"重复的步骤 ID: {step.step_id}")
            step_ids.add(step.step_id)
        
        # 检查步骤名称
        for step in steps:
            if not step.step_name:
                errors.append(f"步骤 {step.step_id} 名称不能为空")
        
        # 检查步骤类型
        valid_types = [t.value for t in StepType]
        for step in steps:
            if step.step_type.value not in valid_types:
                errors.append(f"步骤 {step.step_id} 类型无效: {step.step_type}")
        
        # 检查工具调用步骤
        for step in steps:
            if step.step_type == StepType.TOOL_CALL and not step.tool_id:
                errors.append(f"工具调用步骤 {step.step_id} 缺少 tool_id")
        
        return errors
    
    def _validate_dependencies(self, steps: List[TaskStep]) -> List[str]:
        """依赖关系验证"""
        errors = []
        
        step_ids = {step.step_id for step in steps}
        
        # 检查依赖是否存在
        for step in steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"步骤 {step.step_id} 依赖的步骤 {dep_id} 不存在")
        
        # 检查循环依赖
        if self._has_circular_dependency(steps):
            errors.append("存在循环依赖")
        
        return errors
    
    def _has_circular_dependency(self, steps: List[TaskStep]) -> bool:
        """检查循环依赖"""
        # 构建依赖图
        graph: Dict[str, List[str]] = {}
        for step in steps:
            graph[step.step_id] = step.dependencies
        
        # DFS 检测循环
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step in steps:
            if step.step_id not in visited:
                if dfs(step.step_id):
                    return True
        
        return False
    
    def _validate_tool_availability(self, steps: List[TaskStep]) -> List[str]:
        """工具可用性验证"""
        warnings = []
        
        for step in steps:
            if step.step_type == StepType.TOOL_CALL:
                if not step.tool_id or not step.tool_id.strip():
                    warnings.append(f"步骤 {step.step_id} 的 tool_id 为空")
                elif step.tool_id:
                    # 尝试检查工具是否已注册
                    try:
                        from opencopilot.capabilities.tools import tool_registry
                        if not tool_registry.get(step.tool_id):
                            warnings.append(f"步骤 {step.step_id} 引用的工具 '{step.tool_id}' 未注册")
                    except ImportError:
                        pass  # 工具注册表不可用时跳过
        
        return warnings
    
    def _validate_complexity(self, plan: Plan) -> List[str]:
        """复杂度验证"""
        warnings = []
        
        # 步骤数量过多
        if len(plan.steps) > 20:
            warnings.append(f"步骤数量较多 ({len(plan.steps)})，建议拆分为多个子计划")
        
        # 检查关键步骤
        critical_count = sum(1 for s in plan.steps if s.is_critical)
        if critical_count > len(plan.steps) * 0.5:
            warnings.append("关键步骤比例过高，建议降低关键步骤数量")
        
        # 检查需要审批的步骤
        approval_count = sum(1 for s in plan.steps if s.requires_approval)
        if approval_count > 5:
            warnings.append("需要审批的步骤较多，可能影响执行效率")
        
        return warnings
