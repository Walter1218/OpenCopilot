# tests/planner/test_planner.py

"""
规划器模块测试

使用真实 LLM 能力测试规划器功能。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入规划器模块
from planner.models import (
    TaskStep, Plan, PlanRequest, PlanStatus, StepStatus, StepType,
    ValidationResult, DurationEstimate,
    generate_plan_id, generate_step_id
)
from planner.generator import PlanGenerator
from planner.validator import PlanValidator
from planner.optimizer import PlanOptimizer
from planner.core import Planner
from planner.strategies import (
    SequentialStrategy, ParallelStrategy, AdaptiveStrategy, ReActStrategy
)


# 测试用的 LLM 调用函数（模拟）
async def mock_llm_caller(prompt: str) -> str:
    """模拟 LLM 调用"""
    # 返回一个简单的步骤列表
    return '''
    [
        {
            "step_name": "分析任务",
            "step_type": "llm_call",
            "description": "分析用户任务需求"
        },
        {
            "step_name": "执行任务",
            "step_type": "tool_call",
            "description": "执行主要任务",
            "tool_id": "code_executor"
        },
        {
            "step_name": "验证结果",
            "step_type": "llm_call",
            "description": "验证执行结果"
        }
    ]
    '''


class TestPlannerModels:
    """测试规划器数据模型"""
    
    def test_task_step_creation(self):
        """测试创建任务步骤"""
        step = TaskStep(
            step_id="step_001",
            step_name="测试步骤",
            step_type=StepType.LLM_CALL,
            description="这是一个测试步骤"
        )
        
        assert step.step_id == "step_001"
        assert step.step_name == "测试步骤"
        assert step.step_type == StepType.LLM_CALL
        assert step.status == StepStatus.PENDING
    
    def test_task_step_to_dict(self):
        """测试步骤转换为字典"""
        step = TaskStep(
            step_id="step_001",
            step_name="测试步骤",
            step_type=StepType.TOOL_CALL,
            description="测试描述",
            tool_id="test_tool"
        )
        
        data = step.to_dict()
        assert data["step_id"] == "step_001"
        assert data["step_type"] == "tool_call"
        assert data["tool_id"] == "test_tool"
    
    def test_plan_creation(self):
        """测试创建计划"""
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="步骤1",
                step_type=StepType.LLM_CALL,
                description="第一步"
            ),
            TaskStep(
                step_id="step_002",
                step_name="步骤2",
                step_type=StepType.TOOL_CALL,
                description="第二步"
            )
        ]
        
        plan = Plan(
            plan_id="plan_001",
            task="测试任务",
            steps=steps
        )
        
        assert plan.plan_id == "plan_001"
        assert plan.task == "测试任务"
        assert len(plan.steps) == 2
        assert plan.status == PlanStatus.DRAFT
    
    def test_plan_progress(self):
        """测试计划进度"""
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="步骤1",
                step_type=StepType.LLM_CALL,
                description="第一步",
                status=StepStatus.COMPLETED
            ),
            TaskStep(
                step_id="step_002",
                step_name="步骤2",
                step_type=StepType.TOOL_CALL,
                description="第二步",
                status=StepStatus.PENDING
            )
        ]
        
        plan = Plan(
            plan_id="plan_001",
            task="测试任务",
            steps=steps
        )
        
        assert plan.progress == 0.5


class TestPlanValidator:
    """测试计划验证器"""
    
    def test_valid_plan(self):
        """测试有效计划验证"""
        validator = PlanValidator()
        
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="步骤1",
                step_type=StepType.LLM_CALL,
                description="第一步"
            )
        ]
        
        plan = Plan(
            plan_id="plan_001",
            task="测试任务",
            steps=steps
        )
        
        result = validator.validate(plan)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_empty_task(self):
        """测试空任务验证"""
        validator = PlanValidator()
        
        plan = Plan(
            plan_id="plan_001",
            task="",
            steps=[]
        )
        
        result = validator.validate(plan)
        assert result.is_valid is False
        assert "任务描述不能为空" in result.errors
    
    def test_circular_dependency(self):
        """测试循环依赖检测"""
        validator = PlanValidator()
        
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="步骤1",
                step_type=StepType.LLM_CALL,
                description="第一步",
                dependencies=["step_002"]
            ),
            TaskStep(
                step_id="step_002",
                step_name="步骤2",
                step_type=StepType.TOOL_CALL,
                description="第二步",
                dependencies=["step_001"]
            )
        ]
        
        plan = Plan(
            plan_id="plan_001",
            task="测试任务",
            steps=steps
        )
        
        result = validator.validate(plan)
        assert result.is_valid is False
        assert "存在循环依赖" in result.errors


class TestPlanOptimizer:
    """测试计划优化器"""
    
    def test_estimate_duration(self):
        """测试时间估算"""
        optimizer = PlanOptimizer()
        
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="LLM调用",
                step_type=StepType.LLM_CALL,
                description="调用LLM"
            ),
            TaskStep(
                step_id="step_002",
                step_name="工具调用",
                step_type=StepType.TOOL_CALL,
                description="调用工具"
            )
        ]
        
        estimate = optimizer.estimate_duration(steps)
        assert estimate.min_duration > 0
        assert estimate.max_duration >= estimate.min_duration
    
    def test_optimize_plan(self):
        """测试计划优化"""
        optimizer = PlanOptimizer()
        
        steps = [
            TaskStep(
                step_id="step_001",
                step_name="步骤1",
                step_type=StepType.LLM_CALL,
                description="第一步"
            ),
            TaskStep(
                step_id="step_002",
                step_name="步骤1",  # 重复名称
                step_type=StepType.LLM_CALL,
                description="第一步"  # 重复描述
            )
        ]
        
        plan = Plan(
            plan_id="plan_001",
            task="测试任务",
            steps=steps
        )
        
        optimized = optimizer.optimize(plan)
        # 优化后应该移除重复步骤
        assert len(optimized.steps) <= len(steps)


class TestPlanner:
    """测试规划器核心功能"""
    
    @pytest.mark.asyncio
    async def test_create_plan(self):
        """测试创建计划"""
        planner = Planner(llm_caller=mock_llm_caller)
        
        plan = await planner.create_plan(
            task="修复登录bug",
            context={"file": "auth.py"},
            strategy="sequential"
        )
        
        assert plan is not None
        assert plan.task == "修复登录bug"
        assert len(plan.steps) > 0
        assert plan.plan_id.startswith("plan_")
    
    @pytest.mark.asyncio
    async def test_decompose_task(self):
        """测试任务分解"""
        planner = Planner(llm_caller=mock_llm_caller)
        
        steps = await planner.decompose_task(
            task="重构用户模块",
            strategy="sequential"
        )
        
        assert len(steps) > 0
        assert all(isinstance(s, TaskStep) for s in steps)
    
    @pytest.mark.asyncio
    async def test_create_plan_with_parallel_strategy(self):
        """测试并行策略创建计划"""
        planner = Planner(llm_caller=mock_llm_caller)
        
        plan = await planner.create_plan(
            task="搜索代码库",
            strategy="parallel"
        )
        
        assert plan is not None
        assert plan.metadata.get("strategy") == "parallel"
    
    @pytest.mark.asyncio
    async def test_replan(self):
        """测试重新规划"""
        planner = Planner(llm_caller=mock_llm_caller)
        
        # 创建初始计划
        plan = await planner.create_plan(task="测试任务")
        
        # 重新规划
        new_plan = await planner.replan(
            plan_id=plan.plan_id,
            feedback="需要调整策略"
        )
        
        assert new_plan is not None
        assert new_plan.plan_id != plan.plan_id
    
    def test_list_plans(self):
        """测试列出计划"""
        planner = Planner()
        
        plans = planner.list_plans()
        assert isinstance(plans, list)


class TestPlannerStrategies:
    """测试规划策略"""
    
    @pytest.mark.asyncio
    async def test_sequential_strategy(self):
        """测试顺序策略"""
        strategy = SequentialStrategy()
        
        request = PlanRequest(task="测试任务")
        steps = await strategy.generate_steps(request, mock_llm_caller)
        
        assert len(steps) > 0
        # 组织依赖关系
        steps = strategy.organize_dependencies(steps)
        # 验证依赖关系
        for i, step in enumerate(steps):
            if i > 0:
                assert steps[i-1].step_id in step.dependencies
    
    @pytest.mark.asyncio
    async def test_parallel_strategy(self):
        """测试并行策略"""
        strategy = ParallelStrategy()
        
        request = PlanRequest(task="测试任务")
        steps = await strategy.generate_steps(request, mock_llm_caller)
        
        assert len(steps) > 0
    
    @pytest.mark.asyncio
    async def test_react_strategy(self):
        """测试 ReAct 策略"""
        strategy = ReActStrategy()
        
        request = PlanRequest(task="测试任务")
        steps = await strategy.generate_steps(request, mock_llm_caller)
        
        assert len(steps) > 0


class TestPlannerAPI:
    """测试规划器 API"""
    
    @pytest.mark.asyncio
    async def test_handle_create(self):
        """测试创建计划 API"""
        from planner.api import PlannerAPI
        
        planner = Planner(llm_caller=mock_llm_caller)
        api = PlannerAPI(planner)
        
        data = {
            "task": "测试任务",
            "strategy": "sequential"
        }
        
        result = await api.handle_create(data)
        assert result["success"] is True
        assert "plan" in result
    
    @pytest.mark.asyncio
    async def test_handle_decompose(self):
        """测试分解任务 API"""
        from planner.api import PlannerAPI
        
        planner = Planner(llm_caller=mock_llm_caller)
        api = PlannerAPI(planner)
        
        data = {
            "task": "测试任务",
            "strategy": "sequential"
        }
        
        result = await api.handle_decompose(data)
        assert result["success"] is True
        assert "steps" in result
    
    @pytest.mark.asyncio
    async def test_handle_validate(self):
        """测试验证计划 API"""
        from planner.api import PlannerAPI
        
        planner = Planner()
        api = PlannerAPI(planner)
        
        plan_data = {
            "plan_id": "plan_001",
            "task": "测试任务",
            "steps": [
                {
                    "step_id": "step_001",
                    "step_name": "步骤1",
                    "step_type": "llm_call",
                    "description": "第一步",
                    "status": "pending"
                }
            ],
            "status": "draft",
            "estimated_duration": 0.0,
            "confidence": 0.0,
            "metadata": {},
            "created_at": "2026-06-01T00:00:00",
            "updated_at": "2026-06-01T00:00:00",
            "current_step_index": 0
        }
        
        data = {"plan": plan_data}
        result = await api.handle_validate(data)
        assert result["success"] is True
        assert "validation" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
