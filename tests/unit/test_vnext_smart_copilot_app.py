from __future__ import annotations

from fastapi.testclient import TestClient

import platform_next.api.unified.dependencies as dependencies
import platform_next.api.unified.tasks as task_routes
from gui_next.smart_copilot.app import run_headless_flow
from platform_next.gateway.agent_gateway.protocol import ProviderEvent
from smart_copilot_api import app
from stores_next.models import EventType


class FakeGateway:
    def __init__(self) -> None:
        self._has_polled = False

    def create_run(self, request):
        _ = request
        return "run_fake_headless"

    def poll_events(self, *, provider_id: str, provider_run_id: str):
        _ = (provider_id, provider_run_id)
        if self._has_polled:
            return []
        self._has_polled = True
        return [
            ProviderEvent(
                event_type=EventType.TASK_STAGE_CHANGED,
                payload={"stage": "executing", "message": "Headless provider executing"},
            ),
            ProviderEvent(
                event_type=EventType.TASK_COMPLETED,
                payload={"summary": "Headless interactive result"},
            ),
        ]

    def get_result(self, *, provider_id: str, provider_run_id: str):
        _ = (provider_id, provider_run_id)
        return {
            "summary": "Headless interactive result",
            "artifacts": [{"type": "text", "label": "final"}],
        }


def _reset_vnext_state() -> None:
    dependencies.get_task_store.cache_clear()
    dependencies.get_event_store.cache_clear()
    dependencies.get_context_store.cache_clear()
    dependencies.get_apply_preview_store.cache_clear()
    dependencies.get_context_service.cache_clear()
    dependencies.get_apply_service.cache_clear()


def test_run_headless_flow(monkeypatch):
    _reset_vnext_state()
    monkeypatch.setattr(task_routes, "get_agent_gateway", lambda: FakeGateway())

    with TestClient(app) as test_client:
        snapshot = run_headless_flow("http://testserver", client=test_client)

    assert snapshot["visible"] is True
    assert snapshot["ui_state"]["status"] == "applied"
    assert snapshot["ui_state"]["progress_stage"] == "completed"
    assert snapshot["result_view"]["summary"] == "Headless interactive result"
    assert snapshot["apply_bar"]["can_preview"] is True
    assert snapshot["apply_bar"]["can_commit"] is True
