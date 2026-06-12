from __future__ import annotations

from types import SimpleNamespace

import pytest

from opencopilot.agent.middlewares import PlannerMiddleware, SessionSetupMiddleware
from opencopilot.agent.pipeline import PipelineContext


class _DummyMemory:
    def __init__(self):
        self.messages = []
        self.persona = "default"

    def clear(self, session_id: str):
        self.messages.clear()

    def set_persona(self, session_id: str, persona: str):
        self.persona = persona

    def get_context(self, session_id: str):
        return {"messages": list(self.messages), "persona": self.persona}

    def add_message(self, session_id: str, role: str, content: str):
        self.messages.append({"role": role, "content": content})


class _DummyWindowManager:
    @staticmethod
    def build_messages(system_prompt: str, envelope: dict, history_messages: list):
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_messages)
        messages.append({"role": "user", "content": envelope.get("content", "")})
        return messages


def _normalize_context_envelope(req: dict, text: str, context_source: str, context_meta: dict):
    del req, context_meta
    return {"source": context_source, "content": text, "meta": {}}


@pytest.mark.asyncio
async def test_session_setup_uses_direct_edit_mode_for_ppt_editor():
    middleware = SessionSetupMiddleware(
        memory=_DummyMemory(),
        window_manager=_DummyWindowManager(),
        normalize_context_envelope=_normalize_context_envelope,
        load_persona=lambda persona: f"persona:{persona}",
        build_context_prefix=lambda source, meta: "",
        sanitize_persona_for_context=lambda prompt, source: prompt,
    )
    middleware._tools_prompt_cache = "TOOLS_PROMPT"

    ctx = PipelineContext(
        request={"context_source": "ppt_editor", "context_meta": {}},
        session_id="ppt-editor-session",
        text="PPT 总共 9 页，当前正在编辑第 3 页。\n当前幻灯片数据：{}",
        action_type="chat",
        is_new_task=True,
        enable_web_search=True,
    )

    called = False

    async def next_fn():
        nonlocal called
        called = True

    await middleware.process(ctx, next_fn)

    assert called is True
    assert ctx.enable_web_search is False
    assert ctx.metadata["answer_first"] is True
    system_message = ctx.messages[0]["content"]
    assert "Return the final editable result directly" in system_message
    assert "Do not ask to read the slide again" in system_message
    assert "TOOLS_PROMPT" not in system_message


class _DummyPlanner:
    async def create_plan(self, task: str, context: dict):
        del task, context
        return SimpleNamespace(
            plan_id="ppt-plan-1",
            task="ppt edit task",
            steps=[
                SimpleNamespace(description="收集完成任务所需的信息", step_type=SimpleNamespace(value="tool_call")),
                SimpleNamespace(description="执行主要任务", step_type=SimpleNamespace(value="llm_call")),
            ],
        )


@pytest.mark.asyncio
async def test_planner_forces_answer_first_for_ppt_editor_requests():
    middleware = PlannerMiddleware(_DummyPlanner())
    ctx = PipelineContext(
        request={"context_source": "ppt_editor", "context_meta": {"runtime_flags": {}}},
        session_id="ppt-editor-plan",
        text="PPT 总共 9 页，当前正在编辑第 9 页。\n当前幻灯片数据：{}",
        action_type="chat",
        messages=[
            {"role": "system", "content": "base system"},
            {"role": "user", "content": "edit prompt"},
        ],
        enable_web_search=True,
    )

    called = False

    async def next_fn():
        nonlocal called
        called = True

    await middleware.process(ctx, next_fn)

    assert called is True
    assert ctx.metadata["answer_first"] is True
    assert ctx.enable_web_search is False
    assert ctx.messages[1]["role"] == "system"
    assert "provide the final answer directly" in ctx.messages[1]["content"]


def test_ppt_editor_guard_can_be_disabled(monkeypatch):
    monkeypatch.setenv("OPEN_COPILOT_DISABLE_PPT_DIRECT_EDIT_GUARD", "1")
    ctx = PipelineContext(
        request={"context_source": "ppt_editor"},
        session_id="ppt-editor-disabled",
        text="PPT 总共 9 页，当前正在编辑第 3 页。\n当前幻灯片数据：{}",
    )

    assert SessionSetupMiddleware._is_ppt_editor_request(ctx) is False
    assert PlannerMiddleware._is_ppt_editor_request(ctx) is False
