from __future__ import annotations

from fastapi.testclient import TestClient

import platform_next.api.unified.dependencies as dependencies
import platform_next.api.unified.tasks as task_routes
from gui_next.smart_copilot.services import UnifiedApiClient
from gui_next.smart_copilot.shell import FloatingPanel
from platform_next.gateway.agent_gateway.protocol import ProviderEvent
from smart_copilot_api import app
from stores_next.models import EventType


class FakeGateway:
    def __init__(self) -> None:
        self.requests = []
        self._has_polled = False

    def create_run(self, request):  # pragma: no cover - exercised via route
        self.requests.append(request)
        return "run_fake_001"

    def poll_events(self, *, provider_id: str, provider_run_id: str):
        _ = (provider_id, provider_run_id)
        if self._has_polled:
            return []
        self._has_polled = True
        return [
            ProviderEvent(
                event_type=EventType.TASK_STAGE_CHANGED,
                payload={"stage": "executing", "message": "Fake provider executing"},
            ),
            ProviderEvent(
                event_type=EventType.TASK_COMPLETED,
                payload={"summary": "Polished selection from fake provider"},
            ),
        ]

    def get_result(self, *, provider_id: str, provider_run_id: str):
        _ = provider_id
        return {
            "summary": "Polished selection from fake provider",
            "artifacts": [{"type": "text", "label": "final"}],
            "evidence": [{"type": "provider", "run_id": provider_run_id}],
            "next_actions": [{"label": "apply"}],
        }


def _reset_vnext_state() -> None:
    dependencies.get_task_store.cache_clear()
    dependencies.get_event_store.cache_clear()
    dependencies.get_context_store.cache_clear()
    dependencies.get_apply_preview_store.cache_clear()
    dependencies.get_context_service.cache_clear()
    dependencies.get_apply_service.cache_clear()


def test_floating_panel_runs_vnext_flow(monkeypatch):
    _reset_vnext_state()
    fake_gateway = FakeGateway()
    monkeypatch.setattr(task_routes, "get_agent_gateway", lambda: fake_gateway)

    with TestClient(app) as test_client:
        api_client = UnifiedApiClient(base_url="http://testserver", client=test_client)
        panel = FloatingPanel(api_client=api_client)

        context = panel.summon(
            source_app="Cursor",
            selection_text="old selection text",
            document_title="demo.py",
        )
        task = panel.run_action(action="polish", user_input="make it clearer", max_polls=2, interval_sec=0)
        preview = panel.preview_latest_apply()
        commit = panel.commit_latest_preview()
        snapshot = panel.snapshot()

    assert context["context_snapshot_id"].startswith("ctx_")
    assert task["task_id"].startswith("task_")
    assert snapshot["visible"] is True
    assert snapshot["ui_state"]["status"] == "applied"
    assert snapshot["ui_state"]["latest_context_id"] == context["context_snapshot_id"]
    assert snapshot["ui_state"]["latest_task_id"] == task["task_id"]
    assert snapshot["ui_state"]["progress_stage"] == "completed"
    assert snapshot["ui_state"]["latest_result_summary"] == "Polished selection from fake provider"
    assert snapshot["result_view"]["artifacts"] == [{"type": "text", "label": "final"}]
    assert snapshot["apply_bar"]["can_preview"] is True
    assert snapshot["apply_bar"]["can_commit"] is True
    assert preview["safe_to_commit"] is True
    assert commit["status"] == "succeeded"
    assert snapshot["ui_state"]["latest_apply_operations"] == [
        {
            "type": "replace_selection",
            "target": {"type": "selection"},
            "before": "old selection text",
            "after": "Polished selection from fake provider",
        }
    ]
    assert fake_gateway.requests[0].action == "polish"
    assert fake_gateway.requests[0].context_payload["selection_text"] == "old selection text"
