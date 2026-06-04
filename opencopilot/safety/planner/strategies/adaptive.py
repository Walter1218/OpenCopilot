# planner/strategies/adaptive.py

"""
自适应规划策略

根据执行反馈动态调整计划。
"""

from typing import List, Dict, Any, Optional

from .base import PlanningStrategy
from ..models import TaskStep, StepType, StepStatus, Plan, PlanRequest, generate_step_id


class AdaptiveStrategy(PlanningStrategy):
    """
    自适应规划策略
    
    边执行边调整，根据执行结果动态修改计划。
    适用于不确定性高的任务。
    """
    
    @property
    def name(self) -> str:
        return "adaptive"
    
    @property
    def description(self) -> str:
        return "自适应策略：根据执行反馈动态调整计划"
    
    async def generate_steps(self, request: PlanRequest, 
                           llm_caller=None) -> List[TaskStep]:
        """
        生成初始步骤
        
        自适应策略生成较少的初始步骤，后续动态补充。
        """
        if llm_caller is None:
            return self._generate_basic_steps(request)
        
        prompt = self._build_prompt(request)
        
        try:
            response = await llm_caller(prompt)
            steps = self._parse_llm_response(response, min(request.max_steps, 5))
            return steps
        except Exception as e:
            return self._generate_basic_steps(request)
    
    def organize_dependencies(self, steps: List[TaskStep]) -> List[TaskStep]:
        """组织依赖关系（顺序为主）"""
        for i, step in enumerate(steps):
            if i > 0:
                step.dependencies = [steps[i-1].step_id]
            else:
                step.dependencies = []
        return steps
    
    async def adapt_plan(self, plan: Plan, execution_result: Dict[str, Any],
                        llm_caller=None) -> Plan:
        """
        根据执行结果调整计划
        
        Args:
            plan: 当前计划
            execution_result: 执行结果
            llm_caller: LLM 调用函数
            
        Returns:
            调整后的计划
        """
        if llm_caller is None:
            return plan
        
        # 分析执行结果
        analysis_prompt = self._build_analysis_prompt(plan, execution_result)
        
        try:
            analysis = await llm_caller(analysis_prompt)
            adjustments = self._parse_adjustments(analysis)
            
            # 应用调整
            plan = self._apply_adjustments(plan, adjustments)
            
        except Exception as e:
            # 分析失败，保持原计划
            pass
        
        return plan
    
    def _build_analysis_prompt(self, plan: Plan, execution_result: Dict[str, Any]) -> str:
        """构建分析提示"""
        current_step = plan.current_step
        completed_steps = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
        
        return f"""分析以下执行结果，决定是否需要调整计划。

当前计划：{plan.task}
已完成步骤：{len(completed_steps)}/{len(plan.steps)}
当前步骤：{current_step.step_name if current_step else '无'}

执行结果：
{execution_result}

请分析：
1. 执行是否成功？
2. 是否需要添加新步骤？
3. 是否需要修改后续步骤？
4. 是否需要跳过某些步骤？

请以 JSON 格式返回调整建议：
{{
    "success": true/false,
    "add_steps": [
        {{
            "step_name": "步骤名称",
            "step_type": "llm_call|tool_call",
            "description": "描述",
            "insert_after": "step_id"
        }}
    ],
    "modify_steps": [
        {{
            "step_id": "step_id",
            "new_description": "新描述"
        }}
    ],
    "skip_steps": ["step_id"],
    "reason": "调整原因"
}}
"""
    
    def _parse_adjustments(self, analysis: str) -> Dict[str, Any]:
        """解析调整建议"""
        import json
        
        try:
            json_start = analysis.find('{')
            json_end = analysis.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis[json_start:json_end]
                return json.loads(json_str)
        except Exception:
            pass
        
        return {"success": True, "add_steps": [], "modify_steps": [], "skip_steps": []}
    
    def _apply_adjustments(self, plan: Plan, adjustments: Dict[str, Any]) -> Plan:
        """应用调整"""
        # 添加新步骤
        for step_data in adjustments.get("add_steps", []):
            new_step = TaskStep(
                step_id=generate_step_id(),
                step_name=step_data.get("step_name", "新步骤"),
                step_type=StepType(step_data.get("step_type", "llm_call")),
                description=step_data.get("description", "")
            )
            
            insert_after = step_data.get("insert_after")
            if insert_after:
                # 在指定步骤后插入
                for i, step in enumerate(plan.steps):
                    if step.step_id == insert_after:
                        plan.steps.insert(i + 1, new_step)
                        break
            else:
                # 在当前步骤后插入
                plan.steps.insert(plan.current_step_index + 1, new_step)
        
        # 修改步骤
        for mod_data in adjustments.get("modify_steps", []):
            step_id = mod_data.get("step_id")
            step = plan.get_step(step_id)
            if step:
                if "new_description" in mod_data:
                    step.description = mod_data["new_description"]
        
        # 跳过步骤
        for step_id in adjustments.get("skip_steps", []):
            step = plan.get_step(step_id)
            if step:
                step.status = StepStatus.SKIPPED
        
        return plan
    
    def _build_prompt(self, request: PlanRequest) -> str:
        """构建 LLM 提示"""
        context_str = ""
        if request.context:
            context_str = f"\n上下文信息：\n{request.context}"
        
        return f"""请为以下任务生成初始执行计划（3-5个步骤）。

任务：{request.task}
{context_str}

要求：
1. 生成 3-5 个初始步骤
2. 步骤应该是顺序执行的
3. 每个步骤都有清晰的描述
4. 计划应该允许后续调整

请以 JSON 格式返回步骤列表：
[
    {{
        "step_name": "步骤名称",
        "step_type": "llm_call|tool_call|code_execution",
        "description": "步骤描述",
        "tool_id": "工具ID（可选）",
        "parameters": {{}}
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
                step = TaskStep(
                    step_id=generate_step_id(),
                    step_name=step_data.get('step_name', f"步骤 {i+1}"),
                    step_type=StepType(step_data.get('step_type', 'llm_call')),
                    description=step_data.get('description', ''),
                    tool_id=step_data.get('tool_id'),
                    parameters=step_data.get('parameters', {})
                )
                steps.append(step)
            
            return self.organize_dependencies(steps)
            
        except Exception:
            return []
    
    def _generate_basic_steps(self, request: PlanRequest) -> List[TaskStep]:
        """生成基础步骤"""
        steps = [
            TaskStep(
                step_id=generate_step_id(),
                step_name="分析任务",
                step_type=StepType.LLM_CALL,
                description=f"分析任务需求：{request.task}"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="执行第一步",
                step_type=StepType.TOOL_CALL,
                description="执行任务的第一步"
            ),
            TaskStep(
                step_id=generate_step_id(),
                step_name="评估结果",
                step_type=StepType.LLM_CALL,
                description="评估执行结果，决定下一步"
            )
        ]
        return self.organize_dependencies(steps)
