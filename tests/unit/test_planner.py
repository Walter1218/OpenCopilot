"""
规划器模块测试
"""
import pytest
import os



class TestPlanRequest:
    """规划请求"""

    def test_create(self):
        from opencopilot.safety.planner.models import PlanRequest
        req = PlanRequest(task="Test task", max_steps=5)
        assert req.task == "Test task"
        assert req.max_steps == 5

    def test_defaults(self):
        from opencopilot.safety.planner.models import PlanRequest
        req = PlanRequest(task="Simple")
        assert req.max_steps > 0


class TestTaskStep:
    """任务步骤"""

    def test_create(self):
        from opencopilot.safety.planner.models import TaskStep, StepType
        step = TaskStep(
            step_id="step-1",
            step_name="Test Step",
            step_type=StepType.LLM_CALL,
            description="Test description",
        )
        assert step.step_name == "Test Step"


class TestPlan:
    """执行计划"""

    def test_create(self):
        from opencopilot.safety.planner.models import Plan, StepType, TaskStep
        step = TaskStep(
            step_id="s1", step_name="Step 1",
            step_type=StepType.LLM_CALL, description="Do something"
        )
        plan = Plan(plan_id="plan-1", task="Test plan", steps=[step])
        assert plan.task == "Test plan"
        assert len(plan.steps) == 1


class TestPlanner:
    """规划器"""

    @pytest.fixture
    def planner(self):
        from opencopilot.safety.planner import Planner
        return Planner()

    def test_init(self, planner):
        assert planner is not None

    def test_available_strategies(self, planner):
        strategies = planner.available_strategies
        assert isinstance(strategies, list)
