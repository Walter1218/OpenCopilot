"""
LLM Provider 功能测试
覆盖：BaseProvider / MiniMaxProvider / LocalProvider / load_config / save_config
"""
import pytest
import os
import json
import tempfile



class TestBaseProvider:
    """基础 Provider 接口"""

    def test_stream_chat_raises(self):
        from llm_provider import BaseProvider
        with pytest.raises(NotImplementedError):
            list(BaseProvider().stream_chat("test"))

    def test_stream_chat_with_history_raises(self):
        from llm_provider import BaseProvider
        with pytest.raises(NotImplementedError):
            list(BaseProvider().stream_chat_with_history([]))


class TestMiniMaxProvider:
    """MiniMax Provider"""

    def test_init_with_key(self):
        from llm_provider import MiniMaxProvider
        p = MiniMaxProvider(api_key="test_key")
        assert p.api_key == "test_key"
        assert "minimax" in p.base_url
        assert p.default_model == "MiniMax-M3"

    def test_stream_chat_builds_messages(self):
        from llm_provider import MiniMaxProvider
        p = MiniMaxProvider(api_key="test_key")
        captured = []
        orig = p._do_stream

        def mock(messages):
            captured.extend(messages)
            yield "ok"

        p._do_stream = mock
        list(p.stream_chat("hello", system_prompt="You are helpful"))
        assert len(captured) == 2
        assert captured[0]["role"] == "system"
        assert captured[1]["role"] == "user"
        assert captured[1]["content"] == "hello"

    def test_stream_chat_no_system_prompt(self):
        from llm_provider import MiniMaxProvider
        p = MiniMaxProvider(api_key="test_key")
        captured = []
        orig = p._do_stream

        def mock(messages):
            captured.extend(messages)
            yield "ok"

        p._do_stream = mock
        list(p.stream_chat("hello"))
        assert len(captured) == 1
        assert captured[0]["role"] == "user"


class TestLocalProvider:
    """Local Provider"""

    def test_init(self):
        from llm_provider import LocalProvider
        p = LocalProvider(api_base="http://localhost:11434/v1", model="llama3")
        assert p.api_base == "http://localhost:11434/v1/chat/completions"
        assert p.model == "llama3"

    def test_init_trailing_slash(self):
        from llm_provider import LocalProvider
        p = LocalProvider(api_base="http://localhost:11434/v1/", model="llama3")
        assert p.api_base == "http://localhost:11434/v1/chat/completions"


class TestConfigIO:
    """配置读写"""

    def test_load_default(self):
        from llm_provider import load_config
        config = load_config()
        assert "provider_type" in config
        assert config["provider_type"] in ("minimax", "local", "mimo")

    def test_save_and_load(self):
        from llm_provider import save_config, load_config
        # 保存原始 config.json
        import shutil
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        backup = None
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                backup = f.read()

        test_config = {"provider_type": "local", "local_api_base": "http://localhost:8080/v1", "local_model": "gpt-4"}
        try:
            save_config(test_config)
            loaded = load_config()
            assert loaded["provider_type"] == "local"
            assert loaded["local_model"] == "gpt-4"
        finally:
            # 恢复原始配置
            if backup is not None:
                with open(config_path, 'w') as f:
                    f.write(backup)
