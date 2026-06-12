from __future__ import annotations

import pytest

from opencopilot.agent.middlewares import StateTrackingMiddleware
from opencopilot.agent.pipeline import PipelineContext
from opencopilot.capabilities.state.core import StateManager


def test_state_manager_create_task_accepts_custom_task_id(tmp_path):
    db_path = str(tmp_path / "state_tracking_custom_id.db")
    manager = StateManager(db_path=db_path)

    task = manager.create_task(
        session_id="session-1",
        task_id="plan-123",
        task_type="agent_request",
        description="复杂规划任务",
        metadata={"source": "test"},
    )

    assert task.task_id == "plan-123"
    assert task.metadata["source"] == "test"
    persisted = manager.get_task("plan-123")
    assert persisted is not None
    assert persisted.task_id == "plan-123"


@pytest.mark.asyncio
async def test_state_tracking_middleware_supports_sync_state_manager(tmp_path):
    db_path = str(tmp_path / "state_tracking_sync_middleware.db")
    manager = StateManager(db_path=db_path)
    middleware = StateTrackingMiddleware(manager)
    ctx = PipelineContext(
        request={},
        session_id="session-2",
        text="请做复杂规划",
        action_type="chat",
        metadata={"plan": {"plan_id": "plan-sync-1", "task": "复杂任务拆解"}},
    )

    called = False

    async def next_fn():
        nonlocal called
        called = True

    await middleware.process(ctx, next_fn)

    assert called is True
    task = manager.get_task("plan-sync-1")
    assert task is not None
    assert task.description == "复杂任务拆解"
    assert task.metadata["plan"]["plan_id"] == "plan-sync-1"
