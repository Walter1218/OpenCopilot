"""
Badcase 集成测试 - 使用 mock 验证完整请求链路

覆盖已知 badcase:
1. Mock LLM 服务 - 测试各种 LLM 响应场景
2. Mock Broker 服务 - 测试 Broker 代理通信
3. 端到端请求链路 - 从输入到输出的完整流程
4. 超时和重试机制
"""

import pytest
import sys
import os
import json
import time
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ==========================================
# Badcase 7: Mock LLM 服务测试
# ==========================================

class TestMockLLMService:
    """使用 mock 测试 LLM 服务的各种响应场景"""

    def test_llm_returns_empty_response(self):
        """[Badcase] LLM 返回空响应时应正确处理"""
        from llm_provider import LocalProvider

        provider = LocalProvider(api_base="http://127.0.0.1:19999", model="test")

        # Mock _do_stream 返回空列表
        with patch.object(provider, '_do_stream', return_value=[]):
            chunks = list(provider.stream_chat("hello"))
            assert chunks == []

    def test_llm_returns_error_message(self):
        """[Badcase] LLM 返回错误消息时应正确传递"""
        from llm_provider import LocalProvider

        provider = LocalProvider(api_base="http://127.0.0.1:19999", model="test")

        error_msg = "\n[连接本地大模型失败]: Connection refused"
        with patch.object(provider, '_do_stream', return_value=[error_msg]):
            chunks = list(provider.stream_chat("hello"))
            assert error_msg in "".join(chunks)

    def test_llm_returns_partial_json(self):
        """[Badcase] LLM 返回不完整 JSON 时不应崩溃"""
        from llm_provider import LocalProvider

        provider = LocalProvider(api_base="http://127.0.0.1:19999", model="test")

        # 模拟 SSE 解析：不完整的 JSON 不应导致崩溃
        partial_chunks = ["partial ", "response ", "without ", "complete json"]
        with patch.object(provider, '_do_stream', return_value=partial_chunks):
            chunks = list(provider.stream_chat("hello"))
            assert len(chunks) == 4

    def test_llm_stream_with_history(self):
        """[Badcase] 使用历史消息调用 LLM 时应正确处理"""
        from llm_provider import LocalProvider

        provider = LocalProvider(api_base="http://127.0.0.1:19999", model="test")

        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you?"},
        ]
        with patch.object(provider, '_do_stream', return_value=["I'm fine"]):
            chunks = list(provider.stream_chat_with_history(history))
            assert "I'm fine" in "".join(chunks)

    def test_llm_stream_with_empty_history(self):
        """[Badcase] 空历史消息调用 LLM 时不应崩溃"""
        from llm_provider import LocalProvider

        provider = LocalProvider(api_base="http://127.0.0.1:19999", model="test")

        with patch.object(provider, '_do_stream', return_value=["response"]):
            chunks = list(provider.stream_chat_with_history([]))
            assert len(chunks) == 1


# ==========================================
# Badcase 8: Mock Broker 服务测试
# ==========================================

class TestMockBrokerService:
    """使用 mock 测试 Broker 代理通信"""

    def test_broker_health_check_timeout(self):
        """[Badcase] Broker 健康检查超时时应返回 False"""
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        with patch('httpx.get', side_effect=Exception("Connection timeout")):
            result = client.is_broker_alive()
            assert result is False

    def test_broker_health_check_401(self):
        """[Badcase] Broker 返回 401 时应返回 False"""
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('httpx.get', return_value=mock_response):
            result = client.is_broker_alive()
            assert result is False

    def test_broker_get_frontmost_returns_empty_on_error(self):
        """[Badcase] Broker 获取前台应用失败时应返回空字符串"""
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        with patch('httpx.get', side_effect=Exception("Connection refused")):
            result = client.get_frontmost_app()
            assert result == ""

    def test_broker_get_browser_dom_timeout(self):
        """[Badcase] 浏览器 DOM 读取超时时应抛出异常"""
        import httpx
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        with patch('httpx.post', side_effect=httpx.ReadTimeout("Read timeout")):
            with pytest.raises(Exception, match="超时"):
                client.get_browser_dom("Chrome")

    def test_broker_get_browser_dom_500_error(self):
        """[Badcase] Broker 返回 500 错误时应抛出异常"""
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal Server Error"}

        with patch('httpx.post', return_value=mock_response):
            with pytest.raises(Exception, match="Broker 返回错误"):
                client.get_browser_dom("Chrome")

    def test_broker_read_office_file_error(self):
        """[Badcase] Broker 读取 Office 文件失败时应抛出异常"""
        from system_probe_client import SystemProbeClient

        client = SystemProbeClient()

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "File not found"}

        with patch('httpx.post', return_value=mock_response):
            with pytest.raises(Exception, match="读取 Office 文件失败"):
                client.read_office_file("/nonexistent/file.docx")


# ==========================================
# Badcase 9: 端到端请求链路测试
# ==========================================

class TestEndToEndRequestChain:
    """测试从输入到输出的完整请求链路"""

    def test_full_request_chain_drag_source(self):
        """[Badcase] 拖拽来源的完整请求链路"""
        from asu_custom_agent import normalize_context_envelope, build_context_prefix, ContextWindowManager

        # 模拟前端发来的请求
        req = {
            "text": "selected text",
            "action_type": "translate",
            "session_id": "test-session",
            "is_new_task": True,
            "context_source": "drag",
            "context_meta": {"task": "翻译为中文"},
        }

        # 1. 规范化上下文
        envelope = normalize_context_envelope(req, req["text"], req["context_source"], req["context_meta"])
        assert envelope["source"] == "drag"
        assert envelope["content"] == "selected text"

        # 2. 构建上下文前缀
        prefix = build_context_prefix(envelope["source"], envelope.get("meta", {}))
        assert isinstance(prefix, str)

        # 3. 构建消息
        manager = ContextWindowManager()
        messages = manager.build_messages(
            system_prompt=f"{prefix}\n\nYou are a translator.",
            envelope=envelope,
            history_messages=[]
        )
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"

    def test_full_request_chain_ide_source(self):
        """[Badcase] IDE 来源的完整请求链路"""
        from asu_custom_agent import normalize_context_envelope, build_context_prefix, ContextWindowManager

        req = {
            "text": "def hello():\n    pass",
            "action_type": "code_review",
            "session_id": "test-session",
            "context_source": "ide",
            "context_meta": {
                "file_name": "main.py",
                "language": "python",
                "task": "代码审查",
            },
            "context_envelope": {
                "source": "ide",
                "content": "def hello():\n    pass\ndef world():\n    pass",
                "selection": "def hello():\n    pass",
                "task": "代码审查",
                "meta": {"file_name": "main.py", "language": "python"},
            },
        }

        envelope = normalize_context_envelope(req, req["text"], req["context_source"], req["context_meta"])
        assert envelope["source"] == "ide"
        assert "selection" in envelope

        prefix = build_context_prefix(envelope["source"], envelope.get("meta", {}))
        assert "IDE" in prefix or "代码编辑器" in prefix

        manager = ContextWindowManager()
        messages = manager.build_messages(
            system_prompt=f"{prefix}\n\nYou are a code reviewer.",
            envelope=envelope,
            history_messages=[]
        )
        assert len(messages) >= 2

    def test_full_request_chain_with_history(self):
        """[Badcase] 带历史对话的完整请求链路"""
        from asu_custom_agent import normalize_context_envelope, ContextWindowManager

        history = [
            {"role": "user", "content": "翻译这段文字"},
            {"role": "assistant", "content": "好的，请提供文字"},
            {"role": "user", "content": "Hello World"},
            {"role": "assistant", "content": "你好世界"},
        ]

        req = {"context_envelope": {"source": "drag", "content": "Good morning"}}
        envelope = normalize_context_envelope(req, "", "drag", {})

        manager = ContextWindowManager(recent_turns=3)
        messages = manager.build_messages(
            system_prompt="You are a translator.",
            envelope=envelope,
            history_messages=history
        )

        # 应包含 system + history + user
        assert len(messages) >= 3
        roles = [m["role"] for m in messages]
        assert roles[0] == "system"
        assert roles[-1] == "user"

    def test_full_request_chain_with_persona(self):
        """[Badcase] 使用 persona 的完整请求链路"""
        from asu_custom_agent import load_persona, build_context_prefix, ContextWindowManager, normalize_context_envelope

        # 加载翻译 persona
        persona = load_persona("translation")
        assert isinstance(persona, str)
        assert len(persona) > 0

        req = {"context_envelope": {"source": "drag", "content": "Hello World"}}
        envelope = normalize_context_envelope(req, "", "drag", {})
        prefix = build_context_prefix("drag", {})

        manager = ContextWindowManager()
        messages = manager.build_messages(
            system_prompt=f"{prefix}\n\n{persona}",
            envelope=envelope,
            history_messages=[]
        )

        # 验证 persona 被注入到 system prompt 中
        system_msg = messages[0]["content"]
        assert len(system_msg) > len(prefix) + 10  # persona 内容应该比 prefix 长

    def test_full_request_chain_custom_instruction(self):
        """[Badcase] 自定义指令的完整请求链路"""
        from asu_custom_agent import normalize_context_envelope, build_context_prefix, ContextWindowManager

        req = {
            "context_envelope": {
                "source": "drag",
                "content": "Hello World",
                "meta": {"custom_instruction": "翻译为日语"},
            }
        }
        envelope = normalize_context_envelope(req, "", "drag", {})
        # custom_instruction 从 envelope meta 中获取
        ci = envelope.get("custom_instruction") or envelope.get("meta", {}).get("custom_instruction", "")
        assert ci == "翻译为日语"

        prefix = build_context_prefix("drag", envelope.get("meta", {}))
        manager = ContextWindowManager()
        messages = manager.build_messages(
            system_prompt=f"{prefix}\n\nYou are a translator.",
            envelope=envelope,
            history_messages=[]
        )

        user_payload = messages[-1]["content"]
        assert "翻译为日语" in user_payload


# ==========================================
# Badcase 10: ProviderFactory 测试
# ==========================================

class TestProviderFactoryIntegration:
    """测试 Provider 工厂的集成场景"""

    def test_factory_creates_asu_client(self):
        """[Badcase] ProviderFactory 应创建 ASUCustomAgentClient"""
        from llm_provider import ProviderFactory, ASUCustomAgentClient

        provider = ProviderFactory.create_provider()
        assert isinstance(provider, ASUCustomAgentClient)

    def test_asu_client_stream_agent_task_structure(self):
        """[Badcase] ASUCustomAgentClient 的请求结构应正确"""
        from llm_provider import ASUCustomAgentClient

        client = ASUCustomAgentClient(port=19999)

        # Mock httpx.Client 的 stream 方法
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"chunk": "Hello"}',
            'data: {"chunk": " World"}',
            'data: [DONE]',
        ]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('httpx.Client', return_value=mock_client):
            chunks = list(client.stream_agent_task(
                text="test",
                action_type="translate",
                session_id="test-session",
                context_source="drag",
                context_meta={"task": "翻译"}
            ))
            assert "Hello" in "".join(chunks)
            assert "World" in "".join(chunks)

    def test_asu_client_stream_agent_task_with_envelope(self):
        """[Badcase] 使用 context_envelope 的请求应正确传递"""
        from llm_provider import ASUCustomAgentClient

        client = ASUCustomAgentClient(port=19999)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            'data: {"chunk": "response"}',
            'data: [DONE]',
        ]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('httpx.Client', return_value=mock_client):
            envelope = {
                "source": "ide",
                "content": "code",
                "selection": "selected",
            }
            chunks = list(client.stream_agent_task(
                text="test",
                context_envelope=envelope
            ))
            assert len(chunks) > 0

    def test_asu_client_handles_500_error(self):
        """[Badcase] Agent Server 返回 500 时应返回错误消息"""
        from llm_provider import ASUCustomAgentClient

        client = ASUCustomAgentClient(port=19999)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('httpx.Client', return_value=mock_client):
            chunks = list(client.stream_agent_task("test"))
            full_text = "".join(chunks)
            assert "500" in full_text or "Error" in full_text
