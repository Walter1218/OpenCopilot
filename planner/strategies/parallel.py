# planner/strategies/parallel.py

"""
并行执行策略

独立步骤同时执行，提升效率。
"""

from typing import List, Dict, Any, Set

from .base import PlanningStrategy
from ..models import TaskStep, StepType, StepStatus, PlanRequest, generate_step_id


class ParallelStrategy(PlanningStrategy):
    """
    并行执行策略
    
    将任务分解为可并行执行的步骤组。
    适用于无依赖关系的任务、性能优化场景。
    """
    
    @property
    def name(self) -> str:
        return "parallel"
    
    @property
    def description(self) -> str:
        return "并行执行策略：独立步骤同时执行，提升效率"
    
    async def generate_steps(self, request: PlanRequest, 
                           llm_caller=None) -> List[TaskStep]:
        """
        生成可并行执行的步骤
        
        使用 LLM 将任务分解为可并行的步骤组。
        """
        if llm_caller is None:
            return self._generate_basic_steps(request)
        
        prompt = self._build_prompt(request)
        
        try:
            response = await llm_caller(prompt)
            steps = self._parse_llm_response(response, request.max_steps)
            return steps
        except Exception as e:
            return self._generate_basic_steps(request)
    
    def organize_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """
        组织并行依赖关系
        
        将步骤分为多个并行组，组内步骤可并行执行。
        """
        if not steps:
            return steps
        
        # 识别可并行的步骤（无依赖或依赖已完成的步骤）
        independent_steps = []
        dependent_steps = []
        
        for step in steps:
            if not step.dependencies:
                independent_steps.append(step)
            else:
                dependent_steps.append(step)
        
        # 独立步骤可以并行执行
        # 为独立步骤添加并行标记
        for step in independent_steps:
            step.parameters['_parallel_group'] = 0
        
        # 依赖步骤按依赖层级分组
        current_group = 1
        processed = set(s.step_id for s in independent_steps)
        
        while dependent_steps:
            next_batch = []
            remaining = []
            
            for step in dependent_steps:
                # 检查依赖是否都已处理
                deps_met = all(dep_id in processed for dep_id in step.dependencies)
                if deps_met:
                    step.parameters['_parallel_group'] = current_group
                    next_batch.append(step)
                    processed.add(step.step_id)
                else:
                    remaining.append(step)
            
            if not next_batch:
                # 没有可处理的步骤，可能存在循环依赖
                # 将剩余步骤设为顺序执行
                for step in remaining:
                    step.parameters['_parallel_group'] = current_group + 1
                    processed.add(step.step_id)
                break
            
            dependent_steps = remaining
            current_group += 1
        
        return steps
    
    def get_parallel_groups(self, steps: List[TaskStep]) -> Dict[int, List[TaskStep]]:
        """
        获取并行执行组
        
        Returns:
            分组字典，key 为组号，value 为该组的步骤列表
        """
        groups = {}
        for step in steps:
            group = step.parameters.get('_parallel_group', 0)
            if group not in groups:
                groups[group] = []
            groups[group].append(step)
        return groups
    
    def estimate_duration(self, steps: List[TaskStep]) -> float:
        """
        估算并行执行时间
        
        并行执行时间 = 各组中最长步骤时间之和
        """
        if not steps:
            return 0.0
        
        groups = self.get_parallel_groups(steps)
        total_duration = 0.0
        
        for group_steps in groups.values():
            # 每组取最长步骤时间
            max_duration = max(30.0 for _ in group_steps)  # 默认每个步骤 30 秒
            total_duration += max_duration
        
        return total_duration
    
    def _build_prompt(self, request: PlanRequest) -> str:
        """构建 LLM 提示"""
        context_str = ""
        if request.context:
            context_str = f"\n上下文信息：\n{request.context}"
        
        return f"""请将以下任务分解为可并行执行的步骤。

任务：{request.task}
{context_str}

要求：
1. 最多 {request.max_steps} 个步骤
2. 尽量识别可并行执行的独立步骤
3. 明确标注步骤之间的依赖关系
4. 每个步骤都有清晰的描述

请以 JSON 格式返回步骤列表：
[
    {{
        "step_name": "步骤名称",
        "step_type": "llm_call|tool_call|code_execution|human_approval",
        "description": "步骤描述",
        "tool_id": "工具ID（如果是tool_call类型）",
        "parameters": {{}},
        "dependencies": [],
        "is_critical": false,
        "requires_approval": false
    }}
]

注意：
- 无依赖的步骤可以并行执行
- 依赖项填写其他步骤的 step_name
"""
    
    def _parse_llm_response(self, response: str, max_steps: int) -> List[TaskStep]:
        """解析 LLM 响应"""
        import json
        
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                steps_data = json.loads(json_str)
            else:
                steps_data = json.loads(response)
            
            steps_data = steps_data[:max_steps]
            
            # 第一遍：创建步骤并建立 name -> id 映射
            name_to_id = {}
            steps = []
            for i, step_data in enumerate(steps_data):
                step_id = generate_step_id()
                step_name = step_data.get('step_name', f"步骤 {i+1}")
                name_to_id[step_name] = step_id
                
                step = TaskStep(
                    step_id=step_id,
                    step_name=step_name,
                    step_type=StepType(step_data.get('step_type', 'llm_call')),
                    description=step_data.get('description', ''),
                    tool_id=step_data.get('tool_id'),
                    parameters=step_data.get('parameters', {}),
                    is_critical=step_data.get('is_critical', False),
                    requires_approval=step_data.get('requires_approval', False)
                )
                steps.append(step)
            
            # 第二遍：转换依赖关系
            for i, step_data in enumerate(steps_data):
                deps = step_data.get('dependencies', [])
                step = steps[i]
                step.dependencies = [name_to_id[dep_name] for dep_name in deps if dep_name in name_to_id]
            
            return steps
            
        except Exception as e:
            return []
    
    def _generate_basic_steps(self, request: PlanRequest) -> List[TaskStep]:
        """生成基础并行步骤（无 LLM 时）"""
        # 创建多个可并行的步骤
        steps = [
            TaskStep(
                step_id=generate_step_id(),
                step_name="分析任务需求",
                step_type=StepType.LLM_CALL,
                description=f"分析任务需求：{request.task}"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="搜索相关知识",
                step_type=StepType.TOOL_CALL,
                description="搜索与任务相关的知识和代码",
                tool_id="knowledge_search"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="收集上下文信息",
                step_type=StepType.TOOL_CALL,
                description="收集当前上下文信息",
                tool_id="context_collector"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="执行主要任务",
                step_type=StepType.TOOL_CALL,
                description="执行主要任务",
                dependencies=[]  # 依赖前面三个步骤
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="验证结果",
                step_type=StepType.LLM_CALL,
                description="验证执行结果"
            )
        ]
        
        # 设置依赖关系
        steps[3].dependencies = [steps[0].step_id, steps[1].step_id, steps[2].step_id]
        steps[4].dependencies = [steps[3].step_id]
        
        return self.organize_dependencies(steps)
