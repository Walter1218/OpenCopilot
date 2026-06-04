# planner/strategies/react.py

"""
ReAct 规划策略

Reasoning + Acting 交替进行。
"""

from typing import List, Dict, Any, Optional

from .base import PlanningStrategy
from ..models import TaskStep, StepType, StepStatus, PlanRequest, generate_step_id


class ReActStrategy(PlanningStrategy):
    """
    ReAct 规划策略
    
    推理（Reasoning）和行动（Acting）交替进行。
    适用于需要迭代思考的复杂任务。
    """
    
    @property
    def name(self) -> str:
        return "react"
    
    @property
    def description(self) -> str:
        return "ReAct 策略：推理和行动交替进行，适合复杂任务"
    
    async def generate_steps(self, request: PlanRequest, 
                           llm_caller=None) -> List[TaskStep]:
        """
        生成 ReAct 步骤
        
        ReAct 模式：Thought → Action → Observation 循环
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
        """组织 ReAct 依赖关系"""
        # ReAct 步骤按顺序依赖
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
        
        return f"""请使用 ReAct 模式为以下任务生成执行计划。

任务：{request.task}
{context_str}

ReAct 模式说明：
- Thought（思考）：分析当前情况，决定下一步行动
- Action（行动）：执行具体操作
- Observation（观察）：观察行动结果

要求：
1. 生成 {request.max_steps} 个以内的步骤
2. 步骤应该交替包含思考和行动
3. 每个步骤都有清晰的描述
4. 思考步骤使用 llm_call 类型
5. 行动步骤使用 tool_call 类型

请以 JSON 格式返回步骤列表：
[
    {{
        "step_name": "Thought: 分析...",
        "step_type": "llm_call",
        "description": "思考内容"
    }},
    {{
        "step_name": "Action: 执行...",
        "step_type": "tool_call",
        "description": "行动描述",
        "tool_id": "工具ID"
    }},
    {{
        "step_name": "Observation: 观察...",
        "step_type": "llm_call",
        "description": "观察和分析结果"
    }}
]
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
            
            steps = []
            for i, step_data in enumerate(steps_data):
                step_name = step_data.get('step_name', f"步骤 {i+1}")
                
                # 根据步骤名称推断类型
                step_type_str = step_data.get('step_type', 'llm_call')
                if step_name.startswith('Thought') or step_name.startswith('Observation'):
                    step_type_str = 'llm_call'
                elif step_name.startswith('Action'):
                    step_type_str = 'tool_call'
                
                step = TaskStep(
                    step_id=generate_step_id(),
                    step_name=step_name,
                    step_type=StepType(step_type_str),
                    description=step_data.get('description', ''),
                    tool_id=step_data.get('tool_id'),
                    parameters=step_data.get('parameters', {})
                )
                steps.append(step)
            
            return self.organize_dependencies(steps)
            
        except Exception:
            return []
    
    def _generate_basic_steps(self, request: PlanRequest) -> List[TaskStep]:
        """生成基础 ReAct 步骤"""
        steps = [
            TaskStep(
                step_id=generate_step_id(),
                step_name="Thought: 分析任务",
                step_type=StepType.LLM_CALL,
                description=f"思考如何完成任务：{request.task}"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="Action: 收集信息",
                step_type=StepType.TOOL_CALL,
                description="收集完成任务所需的信息",
                tool_id="knowledge_search"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="Observation: 分析信息",
                step_type=StepType.LLM_CALL,
                description="分析收集到的信息"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="Action: 执行任务",
                step_type=StepType.TOOL_CALL,
                description="执行主要任务"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="Thought: 评估结果",
                step_type=StepType.LLM_CALL,
                description="评估执行结果，决定是否需要进一步行动"
            )
        ]
        return self.organize_dependencies(steps)
