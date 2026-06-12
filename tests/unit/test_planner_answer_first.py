from __future__ import annotations

from types import SimpleNamespace

import pytest

from opencopilot.agent.middlewares import PlannerMiddleware
from opencopilot.agent.pipeline import PipelineContext


class _DummyPlanner:
    async def create_plan(self, task: str, context: dict):
        assert task
        assert context["session_id"] == "answer-first-session"
        return SimpleNamespace(
            plan_id="plan-answer-first",
            task=task,
            steps=[
                SimpleNamespace(description="收集完成任务所需的信息", step_type=SimpleNamespace(value="tool_call")),
                SimpleNamespace(description="执行主要任务", step_type=SimpleNamespace(value="llm_call")),
            ],
        )


@pytest.mark.asyncio
async def test_planner_enables_answer_first_for_complex_text_task():
    middleware = PlannerMiddleware(_DummyPlanner())
    ctx = PipelineContext(
        request={"context_meta": {"runtime_flags": {}}},
        session_id="answer-first-session",
        text="请按 5 个部分输出一份实施方案，先拆解约束，然后给上线计划、风险和行动清单，最后总结核心建议。",
        action_type="chat",
        messages=[
            {"role": "system", "content": "base system"},
            {"role": "user", "content": "user prompt"},
        ],
    )

    called = False

    async def next_fn():
        nonlocal called
        called = True

    await middleware.process(ctx, next_fn)

    assert called is True
    assert ctx.metadata["answer_first"] is True
    assert ctx.enable_web_search is False
    assert len(ctx.messages) == 3
    injected = ctx.messages[1]
    assert injected["role"] == "system"
    assert "provide the final answer directly" in injected["content"]
    assert "tool calls" in injected["content"]
    assert "Do not claim that you need to inspect files" in injected["content"]
    assert "提炼完成任务所需的必要信息" in injected["content"]
