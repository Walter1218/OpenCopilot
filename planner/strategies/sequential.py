# planner/strategies/sequential.py

"""
顺序执行策略

按顺序执行步骤，前一步完成才执行下一步。
"""

from typing import List, Dict, Any

from .base import PlanningStrategy
from ..models import TaskStep, StepType, StepStatus, PlanRequest, generate_step_id


class SequentialStrategy(PlanningStrategy):
    """
    顺序执行策略
    
    最基础的规划策略，步骤按顺序执行。
    适用于线性任务、依赖性强的任务。
    """
    
    @property
    def name(self) -> str:
        return "sequential"
    
    @property
    def description(self) -> str:
        return "顺序执行策略：步骤按顺序执行，前一步完成才执行下一步"
    
    async def generate_steps(self, request: PlanRequest, 
                           llm_caller=None) -> List[TaskStep]:
        """
        生成顺序执行步骤
        
        使用 LLM 将任务分解为顺序步骤。
        """
        if llm_caller is None:
            # 如果没有 LLM，返回基础步骤
            return self._generate_basic_steps(request)
        
        # 使用 LLM 生成步骤
        prompt = self._build_prompt(request)
        
        try:
            response = await llm_caller(prompt)
            steps = self._parse_llm_response(response, request.max_steps)
            return steps
        except Exception as e:
            # LLM 调用失败，返回基础步骤
            return self._generate_basic_steps(request)
    
    def organize_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """
        组织顺序依赖关系
        
        每个步骤依赖前一个步骤。
        """
        for i, step in enumerate(steps):
            if i > 0:
                step.dependencies = [steps[i-1].step_id]
            else:
                step.dependencies = []
        return steps
    
    def _build_prompt(self, request: PlanRequest) -> str:
        """构建 LLM 提示"""
        context_str = ""
        if request.context:
            context_str = f"\n上下文信息：\n{request.context}"
        
        return f"""请将以下任务分解为顺序执行的步骤。

任务：{request.task}
{context_str}

要求：
1. 最多 {request.max_steps} 个步骤
2. 每个步骤应该是可独立执行的
3. 步骤之间有明确的先后顺序
4. 每个步骤都有清晰的描述

请以 JSON 格式返回步骤列表：
[
    {{
        "step_name": "步骤名称",
        "step_type": "llm_call|tool_call|code_execution|human_approval",
        "description": "步骤描述",
        "tool_id": "工具ID（如果是tool_call类型）",
        "parameters": {{}},
        "is_critical": false,
        "requires_approval": false
    }}
]
"""
    
    def _parse_llm_response(self, response: str, max_steps: int) -> List[TaskStep]:
        """解析 LLM 响应"""
        import json
        
        try:
            # 尝试提取 JSON
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                steps_data = json.loads(json_str)
            else:
                steps_data = json.loads(response)
            
            # 限制步骤数量
            steps_data = steps_data[:max_steps]
            
            # 转换为 TaskStep
            steps = []
            for i, step_data in enumerate(steps_data):
                step = TaskStep(
                    step_id=generate_step_id(),
                    step_name=step_data.get('step_name', f"步骤 {i+1}"),
                    step_type=StepType(step_data.get('step_type', 'llm_call')),
                    description=step_data.get('description', ''),
                    tool_id=step_data.get('tool_id'),
                    parameters=step_data.get('parameters', {}),
                    is_critical=step_data.get('is_critical', False),
                    requires_approval=step_data.get('requires_approval', False)
                )
                steps.append(step)
            
            return steps
            
        except Exception as e:
            # 解析失败，返回基础步骤
            return []
    
    def _generate_basic_steps(self, request: PlanRequest) -> List[TaskStep]:
        """生成基础步骤（无 LLM 时）"""
        steps = [
            TaskStep(
                step_id=generate_step_id(),
                step_name="分析任务",
                step_type=StepType.LLM_CALL,
                description=f"分析任务需求：{request.task}"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="执行任务",
                step_type=StepType.TOOL_CALL,
                description="执行主要任务"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="验证结果",
                step_type=StepType.LLM_CALL,
                description="验证执行结果是否符合预期"
            )
        ]
        return self.organize_dependencies(steps)
