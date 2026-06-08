import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeSignal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args, **kwargs):
        for slot in list(self._slots):
            slot(*args, **kwargs)


class _FakeObservability:
    def gui_log(self, *args, **kwargs):
        _ = (args, kwargs)


def test_ai_worker_delegates_to_v5_agent_worker(monkeypatch, qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AIWorker
    import gui.v5.agent_worker as agent_worker_module
    import opencopilot.capabilities.ppt.render_prompt_generator as prompt_module
    import opencopilot.agent.observability as observability_module

    captured = {}

    def fake_generate_render_prompt(*, instruction, current_slide, original_text, selected_text):
        captured["instruction"] = instruction
        captured["current_slide"] = current_slide
        captured["original_text"] = original_text
        captured["selected_text"] = selected_text
        return "## 渲染指令"

    class FakeV5AgentWorker:
        def __init__(self, **kwargs):
            captured["delegate_kwargs"] = kwargs
            self.finished_signal = _FakeSignal()
            self.error_signal = _FakeSignal()

        def run(self):
            self.finished_signal.emit('{"action":"update","slide_index":0,"field":"title","value":"新标题"}')

        def stop(self):
            captured["delegate_stopped"] = True

    monkeypatch.setattr(prompt_module, "generate_render_prompt", fake_generate_render_prompt)
    monkeypatch.setattr(agent_worker_module, "V5AgentWorker", FakeV5AgentWorker)
    monkeypatch.setattr(
        observability_module.PipelineObservability,
        "get_instance",
        staticmethod(lambda: _FakeObservability()),
    )

    worker = AIWorker()
    worker.set_task(
        "把当前页标题改成更聚焦结果",
        [{"title": "旧标题", "layout": "text_only", "items": [{"text": "要点A"}]}],
        0,
        "这里是完整原文",
        "ppt-session-001",
    )

    responses = []
    errors = []
    worker.response_ready.connect(lambda text: responses.append(text))
    worker.error_occurred.connect(lambda text: errors.append(text))

    worker.run()

    assert errors == []
    assert responses == ['{"action":"update","slide_index":0,"field":"title","value":"新标题"}']
    assert captured["original_text"] == "这里是完整原文"
    assert captured["delegate_kwargs"]["action_type"] == "chat"
    assert captured["delegate_kwargs"]["context_source"] == "ppt_editor"
    assert captured["delegate_kwargs"]["session_id"] == "ppt-session-001"
    assert captured["delegate_kwargs"]["context_meta"]["ppt_cocreation"] is True
    assert captured["delegate_kwargs"]["context_meta"]["slides_count"] == 1


def test_ai_worker_stop_propagates_to_delegate(qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AIWorker

    called = []

    class FakeDelegate:
        def stop(self):
            called.append(True)

    worker = AIWorker()
    worker._delegate_worker = FakeDelegate()

    worker.stop()

    assert called == [True]


def test_ai_worker_surfaces_delegate_errors(monkeypatch, qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AIWorker
    import gui.v5.agent_worker as agent_worker_module
    import opencopilot.agent.observability as observability_module

    class FakeV5AgentWorker:
        def __init__(self, **kwargs):
            _ = kwargs
            self.finished_signal = _FakeSignal()
            self.error_signal = _FakeSignal()

        def run(self):
            self.error_signal.emit("[错误]: delegate boom")

        def stop(self):
            return None

    monkeypatch.setattr(agent_worker_module, "V5AgentWorker", FakeV5AgentWorker)
    monkeypatch.setattr(
        observability_module.PipelineObservability,
        "get_instance",
        staticmethod(lambda: _FakeObservability()),
    )

    worker = AIWorker()
    worker.set_task("请调整当前页", [{"title": "旧标题"}], 0, "原文", "ppt-session-err")

    errors = []
    worker.error_occurred.connect(lambda text: errors.append(text))

    worker.run()

    assert len(errors) == 1
    assert "调用 Hermes 共创链路失败" in errors[0]
    assert "delegate boom" in errors[0]


def test_analysis_uses_hermes_runner(monkeypatch, qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AICopilotChatWidget
    import opencopilot.agent.observability as observability_module

    class FakeAnalysisManager:
        def __init__(self):
            self.payloads = []

        def update_analysis_debounced(self, payload):
            self.payloads.append(payload)

    monkeypatch.setattr(
        observability_module.PipelineObservability,
        "get_instance",
        staticmethod(lambda: _FakeObservability()),
    )

    widget = AICopilotChatWidget()
    widget.analysis_manager = FakeAnalysisManager()
    widget.slides_data = [{"title": "标题A", "content": "内容A"}]
    widget.current_index = 0
    widget.original_text = "原文A"
    widget._run_hermes_ppt_request = lambda **kwargs: "这是分析结果"

    widget._analyze_current_slide()

    assert widget.analysis_manager.payloads == [{"analysis": "这是分析结果"}]


def test_suggestions_use_hermes_runner(monkeypatch, qapp):
    _ = qapp
    import opencopilot.capabilities.ppt.ai_chat_widget as ai_chat_widget_module
    import opencopilot.agent.observability as observability_module

    shown = []

    class FakeSuggestionManager:
        def __init__(self, parent):
            _ = parent

        def show_suggestion(self, suggestion, pos, on_accept=None, on_dismiss=None):
            shown.append((suggestion, pos, on_accept, on_dismiss))

    monkeypatch.setattr(
        observability_module.PipelineObservability,
        "get_instance",
        staticmethod(lambda: _FakeObservability()),
    )
    monkeypatch.setattr(ai_chat_widget_module, "SuggestionBubbleManager", FakeSuggestionManager)

    widget = ai_chat_widget_module.AICopilotChatWidget()
    widget.slides_data = [{"title": "标题B", "content": "内容B"}]
    widget.current_index = 0
    widget.original_text = "原文B"
    widget._run_hermes_ppt_request = lambda **kwargs: "建议一：强化价值表达。"

    widget._trigger_suggestions_for_current_slide()

    assert len(shown) == 1
    assert shown[0][0]["title"] == "AI优化建议"
    assert "强化价值表达" in shown[0][0]["content"]


def test_widget_normalizes_render_commands_to_current_slide_and_title(qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AICopilotChatWidget
    from opencopilot.capabilities.ppt.render_command import RenderCommand

    widget = AICopilotChatWidget()
    widget.current_index = 1
    widget.instruction = "请把当前页标题改成更有结论感的 headline"
    widget._last_instruction = widget.instruction

    commands = [
        RenderCommand(
            slide_index=2,
            slot="body",
            render_type="text",
            render_params={"text": "增长提速，企业版成为核心引擎"},
        )
    ]

    normalized = widget._normalize_render_commands(commands)

    assert normalized[0].slide_index == 1
    assert normalized[0].slot == "title"
    assert normalized[0].render_params["title"] == "增长提速，企业版成为核心引擎"


def test_widget_collects_legacy_action_arrays_and_normalizes_slide_index(qapp):
    _ = qapp
    from opencopilot.capabilities.ppt.ai_chat_widget import AICopilotChatWidget

    widget = AICopilotChatWidget()
    widget.current_index = 1
    widget.instruction = "把当前页改成 image_right 版式，并改标题"
    widget._last_instruction = widget.instruction

    actions = widget._collect_legacy_actions([
        """
        [
          {"action": "update", "slide_index": 3, "field": "layout", "value": "image_right"},
          {"action": "update", "slide_index": 3, "field": "title", "value": "企业版增长进入加速区间"}
        ]
        """
    ])

    assert len(actions) == 2
    assert all(action["slide_index"] == 1 for action in actions)
    assert actions[0]["field"] == "layout"
    assert actions[1]["field"] == "title"
