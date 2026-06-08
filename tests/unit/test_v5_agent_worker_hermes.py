from __future__ import annotations

from fastapi.testclient import TestClient

import platform_next.api.unified.dependencies as dependencies
import platform_next.api.unified.tasks as task_routes
from gui.v5 import agent_worker as agent_worker_module
from platform_next.gateway.agent_gateway.protocol import ProviderEvent
from smart_copilot_api import app
from stores_next.models import EventType


class FakeGateway:
    def __init__(self) -> None:
        self._has_polled = False

    def create_run(self, request):
        _ = request
        return "run_fake_v5_001"

    def poll_events(self, *, provider_id: str, provider_run_id: str):
        _ = (provider_id, provider_run_id)
        if self._has_polled:
            return []
        self._has_polled = True
        return [
            ProviderEvent(
                event_type=EventType.TASK_STAGE_CHANGED,
                payload={"stage": "executing", "message": "Fake Hermes executing"},
            ),
            ProviderEvent(
                event_type=EventType.TASK_COMPLETED,
                payload={"summary": "Hermes result for V5 worker"},
            ),
        ]

    def get_result(self, *, provider_id: str, provider_run_id: str):
        _ = (provider_id, provider_run_id)
        return {"summary": "Hermes result for V5 worker"}


def _reset_vnext_state() -> None:
    dependencies.get_task_store.cache_clear()
    dependencies.get_event_store.cache_clear()
    dependencies.get_context_store.cache_clear()
    dependencies.get_apply_preview_store.cache_clear()
    dependencies.get_context_service.cache_clear()
    dependencies.get_apply_service.cache_clear()


def test_v5_agent_worker_runs_against_vnext(monkeypatch):
    _reset_vnext_state()
    monkeypatch.setattr(task_routes, "get_agent_gateway", lambda: FakeGateway())
    monkeypatch.setattr(agent_worker_module.SmartCopilotApiRuntime, "ensure_ready", lambda self: "http://testserver")
    monkeypatch.setattr(agent_worker_module.SmartCopilotApiRuntime, "shutdown", lambda self: None)

    finished_payloads: list[str] = []
    streamed_payloads: list[str] = []
    errors: list[str] = []
    client_kwargs: dict = {}

    with TestClient(app) as test_client:
        def fake_client(*_args, **kwargs):
            client_kwargs.update(kwargs)
            return test_client

        monkeypatch.setattr(agent_worker_module.httpx, "Client", fake_client)
        worker = agent_worker_module.V5AgentWorker(
            prompt="请润色以下文本",
            action_type="polish",
            context_source="selection",
            context_meta={"source_text": "old selection"},
        )
        worker.finished_signal.connect(lambda text: finished_payloads.append(text))
        worker.text_updated.connect(lambda text: streamed_payloads.append(text))
        worker.error_signal.connect(lambda text: errors.append(text))
        worker.run()

    assert errors == []
    assert finished_payloads == ["Hermes result for V5 worker"]
    assert streamed_payloads[-1] == "Hermes result for V5 worker"
    assert client_kwargs["base_url"] == "http://testserver"
    timeout = client_kwargs["timeout"]
    assert isinstance(timeout, agent_worker_module.httpx.Timeout)
    assert timeout.read == worker._build_client_timeout().read


def test_v5_agent_worker_timeout_scales_with_input_size():
    short_worker = agent_worker_module.V5AgentWorker(
        prompt="请翻译这句话",
        action_type="translate",
        context_source="selection",
        context_meta={"source_text": "你好", "source_lang": "zh", "target_lang": "en"},
    )
    long_text = "超长文档内容" * 12000
    long_worker = agent_worker_module.V5AgentWorker(
        prompt=long_text,
        action_type="ppt",
        context_source="studio",
        context_meta={"input_text_len": len(long_text)},
        context_envelope={"document_text": long_text},
    )

    short_timeout = short_worker._build_client_timeout()
    long_timeout = long_worker._build_client_timeout()

    assert short_timeout.read >= 60.0
    assert long_timeout.read > short_timeout.read
    assert long_timeout.read <= 480.0
