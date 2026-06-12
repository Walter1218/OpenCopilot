from __future__ import annotations

import time

from fastapi.testclient import TestClient

import platform_next.api.unified.dependencies as dependencies
from platform_next.gateway.agent_gateway.protocol import UnifiedTaskRequest
from platform_next.gateway.agent_gateway.selector import ProviderSelector
from smart_copilot_api import app


def _reset_vnext_state() -> None:
    dependencies.get_task_store.cache_clear()
    dependencies.get_event_store.cache_clear()
    dependencies.get_context_store.cache_clear()
    dependencies.get_apply_preview_store.cache_clear()
    dependencies.get_context_service.cache_clear()
    dependencies.get_apply_service.cache_clear()
    dependencies.get_agent_gateway.cache_clear()


def test_provider_selector_prefers_self_hosted_for_text_actions():
    selector = ProviderSelector()

    text_request = UnifiedTaskRequest(
        task_id="task_text",
        action="polish",
        user_input="make it better",
        context_snapshot_id="ctx_1",
        provider="auto",
    )
    ppt_request = UnifiedTaskRequest(
        task_id="task_ppt",
        action="ppt",
        user_input="生成汇报",
        context_snapshot_id="ctx_2",
        provider="auto",
    )

    assert selector.choose_provider(text_request) == "self_hosted"
    assert selector.choose_provider(ppt_request) == "hermes_local"


def test_vnext_task_flow_runs_through_self_hosted_adapter(monkeypatch):
    _reset_vnext_state()
    captured_kwargs = {}

    def fake_call_agent_pipeline_sync(**kwargs):
        captured_kwargs.update(kwargs)
        yield "第一段输出。"
        yield "第二段输出。"

    monkeypatch.setattr(
        "agents_next.providers.self_hosted.adapter.call_agent_pipeline_sync",
        fake_call_agent_pipeline_sync,
    )

    with TestClient(app) as client:
        context_resp = client.post(
            "/vnext/context/snapshots",
            json={
                "trigger": "test",
                "source_app": "Cursor",
                "selection_text": "原始文本",
                "document_title": "demo.py",
                "metadata": {
                    "context_source": "selection",
                    "context_meta": {
                        "source_text": "原始文本",
                        "runtime_flags": {"disable_planner": True},
                    },
                    "runtime_flags": {"disable_planner": True},
                },
            },
        )
        assert context_resp.status_code == 200
        snapshot_id = context_resp.json()["context_snapshot_id"]

        task_resp = client.post(
            "/vnext/tasks",
            json={
                "action": "polish",
                "user_input": "请优化这段文字",
                "context_snapshot_id": snapshot_id,
            },
        )
        assert task_resp.status_code == 200
        task_id = task_resp.json()["task_id"]

        deadline = time.time() + 3.0
        task_payload = {}
        while time.time() < deadline:
            task_payload = client.get(f"/vnext/tasks/{task_id}").json()
            if task_payload["status"] == "succeeded":
                break
            time.sleep(0.05)

        events_payload = client.get(f"/vnext/tasks/{task_id}/events").json()

    assert task_payload["provider"] == "self_hosted"
    assert task_payload["status"] == "succeeded"
    assert task_payload["result"]["summary"] == "第一段输出。第二段输出。"
    event_types = [event["type"] for event in events_payload["events"]]
    assert "task.stage_changed" in event_types
    assert "task.delta" in event_types
    assert "task.completed" in event_types
    assert captured_kwargs["action_type"] == "polish"
    assert captured_kwargs["context_source"] == "selection"
    assert captured_kwargs["context_meta"]["runtime_flags"]["disable_planner"] is True
