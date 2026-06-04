"""
asu_custom_agent 核心功能测试 (v4.0 API)
"""
import pytest
import os



class TestContextWindowManager:
    """上下文窗口管理器"""

    @pytest.fixture
    def mgr(self):
        from asu_custom_agent import ContextWindowManager
        return ContextWindowManager(max_input_chars=24000, recent_turns=6)

    def test_init(self, mgr):
        assert mgr.max_input_chars == 24000
        assert mgr.recent_turns == 6

    def test_adjust_for_model(self, mgr):
        if hasattr(mgr, 'adjust_for_model'):
            mgr.adjust_for_model("gpt-3.5-turbo")
            assert mgr.max_input_chars > 0

    def test_build_messages(self, mgr):
        msgs = mgr.build_messages("You are helpful", {"source": "drag", "content": "hello"}, [])
        assert len(msgs) >= 2
        assert msgs[0]["role"] == "system"

    def test_build_messages_with_history(self, mgr):
        history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
        msgs = mgr.build_messages("System", {"content": "now"}, history)
        assert len(msgs) >= 3

    def test_build_user_payload(self, mgr):
        envelope = {"source": "drag", "content": "test content", "selection": "",
                    "task": "", "custom_instruction": "", "meta": {}}
        result = mgr._build_user_payload(envelope, 5000)
        assert isinstance(result, str) and "test content" in result

    def test_build_user_payload_with_selection(self, mgr):
        envelope = {"source": "ide", "content": "code", "selection": "sel",
                    "task": "", "custom_instruction": "",
                    "meta": {"file_name": "test.py"}}
        result = mgr._build_user_payload(envelope, 5000)
        assert isinstance(result, str)


class TestNormalizeContextEnvelope:
    """上下文信封标准化"""

    def test_new_protocol(self):
        from asu_custom_agent import normalize_context_envelope
        req = {"context_envelope": {"source": "ide", "content": "code",
                "selection": "sel", "task": "refactor",
                "meta": {"file_name": "main.py"}}}
        r = normalize_context_envelope(req, "", "drag", {})
        assert r["source"] == "ide"

    def test_old_protocol_fallback(self):
        from asu_custom_agent import normalize_context_envelope
        r = normalize_context_envelope({}, "fallback", "browser", {})
        assert r["content"] == "fallback"

    def test_type_coercion(self):
        from asu_custom_agent import normalize_context_envelope
        req = {"context_envelope": {"source": 123, "content": None,
                "selection": 456, "task": True, "meta": {}}}
        r = normalize_context_envelope(req, "", "drag", {})
        assert isinstance(r["source"], str)


class TestBuildContextPrefix:
    """上下文前缀"""

    def test_ide_prefix(self):
        from asu_custom_agent import build_context_prefix
        r = build_context_prefix("ide", {"file_name": "main.py"})
        assert "代码编辑器" in r

    def test_drag_prefix(self):
        from asu_custom_agent import build_context_prefix
        assert "拖拽" in build_context_prefix("drag", {})


class TestLoadPersona:
    """Persona 加载"""

    def test_load_default(self):
        from asu_custom_agent import load_persona
        r = load_persona("default")
        assert isinstance(r, str) and len(r) > 0


class TestContextDescriptions:
    """上下文描述"""

    def test_all_sources(self):
        from asu_custom_agent import CONTEXT_DESCRIPTIONS
        for src in ["ide", "browser", "drag", "chat", "revision"]:
            assert src in CONTEXT_DESCRIPTIONS
