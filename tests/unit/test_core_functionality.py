"""
核心功能测试 - 针对 ContextWindowManager、normalize_context_envelope、
build_context_prefix、load_persona、ASUAgentMemory 等核心逻辑的真实功能测试
"""

import pytest
import sys
import os
import time
import json
import tempfile
import sqlite3

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ==========================================
# ContextWindowManager 测试
# ==========================================

class TestContextWindowManager:
    """上下文窗口管理器功能测试"""

    @pytest.fixture
    def manager(self):
        from asu_custom_agent import ContextWindowManager
        return ContextWindowManager(
            max_input_chars=24000,
            reserve_output_chars=6000,
            recent_turns=6,
            max_history_msg_chars=2200
        )

    # --- _truncate_text ---
    def test_truncate_short_text(self, manager):
        """短文本不截断"""
        text = "Hello World"
        result = manager._truncate_text(text, 1000)
        assert result == text

    def test_truncate_exact_limit(self, manager):
        """刚好等于限制的文本不截断"""
        text = "A" * 100
        result = manager._truncate_text(text, 100)
        assert result == text

    def test_truncate_long_text(self, manager):
        """长文本被截断并包含标记"""
        text = "A" * 5000
        result = manager._truncate_text(text, 500)
        assert len(result) <= 500
        assert "已截断" in result
        # 头尾都保留
        assert result.startswith("A")
        assert result.endswith("A")

    def test_truncate_empty_text(self, manager):
        """空文本返回空字符串"""
        assert manager._truncate_text("", 100) == ""
        assert manager._truncate_text(None, 100) == ""

    def test_truncate_zero_limit(self, manager):
        """零限制返回空字符串"""
        assert manager._truncate_text("hello", 0) == ""
        assert manager._truncate_text("hello", -1) == ""

    def test_truncate_very_small_limit(self, manager):
        """极小限制：marker空间不足时直接截取"""
        text = "A" * 100
        result = manager._truncate_text(text, 10)
        assert len(result) == 10

    # --- _clip_by_source ---
    def test_clip_ide_source_preserves_head_tail(self, manager):
        """IDE来源：保留头尾"""
        text = "HEAD" + "MIDDLE" * 500 + "TAIL"
        result = manager._clip_by_source("ide", text, 200)
        assert len(result) <= 200
        assert "HEAD" in result
        assert "TAIL" in result
        assert "IDE内容已裁剪" in result

    def test_clip_browser_source_prefers_head(self, manager):
        """Browser来源：偏头部"""
        text = "START" + "MIDDLE" * 500 + "END"
        result = manager._clip_by_source("browser", text, 200)
        assert len(result) <= 200
        assert "START" in result
        assert "网页正文已裁剪" in result

    def test_clip_drag_source_uses_truncate(self, manager):
        """Drag来源：使用默认截断"""
        text = "A" * 5000
        result = manager._clip_by_source("drag", text, 500)
        assert len(result) <= 500
        assert "已截断" in result

    def test_clip_short_text_not_clipped(self, manager):
        """短文本不裁剪"""
        text = "short text"
        for source in ("ide", "browser", "drag"):
            result = manager._clip_by_source(source, text, 1000)
            assert result == text

    # --- _build_user_payload ---
    def test_build_payload_basic(self, manager):
        """基础payload构建"""
        envelope = {
            "source": "drag",
            "content": "test content",
            "selection": "",
            "task": "",
            "custom_instruction": "",
            "meta": {}
        }
        result = manager._build_user_payload(envelope, 5000)
        assert "[context_source] drag" in result
        assert "test content" in result

    def test_build_payload_with_selection(self, manager):
        """带选区的payload"""
        envelope = {
            "source": "ide",
            "content": "full file content",
            "selection": "selected text",
            "task": "",
            "custom_instruction": "",
            "meta": {"file_name": "test.py", "language": "python"}
        }
        result = manager._build_user_payload(envelope, 5000)
        assert "[selection]" in result
        assert "selected text" in result
        assert "[meta]" in result
        assert "file_name=test.py" in result
        assert "language=python" in result

    def test_build_payload_with_custom_instruction(self, manager):
        """带自定义指令的payload"""
        envelope = {
            "source": "drag",
            "content": "text",
            "selection": "selected",
            "task": "",
            "custom_instruction": "改为被动语态",
            "meta": {}
        }
        result = manager._build_user_payload(envelope, 5000)
        assert "[custom_instruction]" in result
        assert "改为被动语态" in result
        assert "严格按照上述指令" in result

    def test_build_payload_with_task(self, manager):
        """带任务的payload"""
        envelope = {
            "source": "drag",
            "content": "text",
            "selection": "",
            "task": "翻译为英文",
            "custom_instruction": "",
            "meta": {}
        }
        result = manager._build_user_payload(envelope, 5000)
        assert "[task] 翻译为英文" in result

    # --- _pick_recent_history ---
    def test_pick_recent_within_budget(self, manager):
        """历史消息在预算内全部保留"""
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you"},
            {"role": "assistant", "content": "I'm fine"},
        ]
        result = manager._pick_recent_history(history, 10000)
        assert len(result) == 4

    def test_pick_recent_limited_by_turns(self, manager):
        """历史消息受 recent_turns 限制"""
        history = []
        for i in range(20):
            history.append({"role": "user", "content": f"msg {i}"})
            history.append({"role": "assistant", "content": f"reply {i}"})
        
        result = manager._pick_recent_history(history, 100000)
        # recent_turns=6, so max 12 messages
        assert len(result) <= 12

    def test_pick_recent_limited_by_budget(self, manager):
        """历史消息受预算限制"""
        history = [
            {"role": "user", "content": "A" * 1000},
            {"role": "assistant", "content": "B" * 1000},
            {"role": "user", "content": "C" * 1000},
            {"role": "assistant", "content": "D" * 1000},
        ]
        result = manager._pick_recent_history(history, 1500)
        assert len(result) < 4

    def test_pick_recent_empty_history(self, manager):
        """空历史返回空列表"""
        result = manager._pick_recent_history([], 10000)
        assert result == []

    def test_pick_recent_zero_budget(self, manager):
        """零预算返回空列表"""
        history = [{"role": "user", "content": "hello"}]
        result = manager._pick_recent_history(history, 0)
        assert result == []

    def test_pick_recent_preserves_order(self, manager):
        """历史消息保持时序"""
        history = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "third"},
            {"role": "assistant", "content": "fourth"},
        ]
        result = manager._pick_recent_history(history, 10000)
        assert result[0]["content"] == "first"
        assert result[-1]["content"] == "fourth"

    # --- build_messages ---
    def test_build_messages_structure(self, manager):
        """构建消息列表的结构正确"""
        envelope = {
            "source": "drag",
            "content": "hello world",
            "selection": "",
            "task": "",
            "custom_instruction": "",
            "meta": {}
        }
        messages = manager.build_messages("You are a helpful assistant", envelope, [])
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[-1]["role"] == "user"
        assert "hello world" in messages[-1]["content"]

    def test_build_messages_with_history(self, manager):
        """带历史消息的构建"""
        envelope = {
            "source": "drag",
            "content": "current message",
            "selection": "",
            "task": "",
            "custom_instruction": "",
            "meta": {}
        }
        history = [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
        messages = manager.build_messages("System prompt", envelope, history)
        assert len(messages) >= 3  # system + history + user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        # 历史消息在中间
        roles = [m["role"] for m in messages]
        assert "user" in roles[1:-1]  # 历史中的user消息


# ==========================================
# normalize_context_envelope 测试
# ==========================================

class TestNormalizeContextEnvelope:
    """上下文信封标准化测试"""

    def test_new_protocol_full(self):
        """新协议完整输入"""
        from asu_custom_agent import normalize_context_envelope
        req = {
            "context_envelope": {
                "source": "ide",
                "content": "file content",
                "selection": "selected code",
                "task": "refactor",
                "meta": {"file_name": "main.py", "language": "python"}
            }
        }
        result = normalize_context_envelope(req, "", "drag", {})
        assert result["source"] == "ide"
        assert result["content"] == "file content"
        assert result["selection"] == "selected code"
        assert result["task"] == "refactor"
        assert result["meta"]["file_name"] == "main.py"

    def test_old_protocol_fallback(self):
        """旧协议回退"""
        from asu_custom_agent import normalize_context_envelope
        req = {}
        result = normalize_context_envelope(req, "fallback text", "browser", {"task": "analyze"})
        assert result["source"] == "browser"
        assert result["content"] == "fallback text"
        assert result["task"] == "analyze"

    def test_custom_instruction_from_meta(self):
        """custom_instruction 从 fallback_meta 合并"""
        from asu_custom_agent import normalize_context_envelope
        req = {
            "context_envelope": {
                "source": "drag",
                "content": "text",
                "meta": {}
            }
        }
        result = normalize_context_envelope(req, "", "drag", {"custom_instruction": "改为被动语态"})
        assert result["custom_instruction"] == "改为被动语态"

    def test_custom_instruction_from_envelope_meta(self):
        """custom_instruction 从 envelope meta 中获取（保留在meta中）"""
        from asu_custom_agent import normalize_context_envelope
        req = {
            "context_envelope": {
                "source": "drag",
                "content": "text",
                "meta": {"custom_instruction": "翻译为英文"}
            }
        }
        result = normalize_context_envelope(req, "", "drag", {})
        # custom_instruction 在 envelope meta 中，通过 _build_user_payload 从 meta 取
        assert result["meta"]["custom_instruction"] == "翻译为英文"

    def test_weak_type_coercion(self):
        """弱类型输入转字符串"""
        from asu_custom_agent import normalize_context_envelope
        req = {
            "context_envelope": {
                "source": 123,
                "content": None,
                "selection": 456,
                "task": True,
                "meta": {}
            }
        }
        result = normalize_context_envelope(req, "", "drag", {})
        assert isinstance(result["source"], str)
        assert isinstance(result["content"], str)
        assert isinstance(result["selection"], str)
        assert isinstance(result["task"], str)

    def test_none_envelope_fallback(self):
        """None envelope 使用回退值"""
        from asu_custom_agent import normalize_context_envelope
        req = {"context_envelope": None}
        result = normalize_context_envelope(req, "fallback", "drag", {})
        assert result["content"] == "fallback"
        assert result["source"] == "drag"


# ==========================================
# build_context_prefix 测试
# ==========================================

class TestBuildContextPrefix:
    """上下文前缀构建测试"""

    def test_ide_source_prefix(self):
        """IDE来源前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("ide", {"file_name": "main.py", "language": "python"})
        assert "代码编辑器" in result
        assert "main.py" in result
        assert "python" in result

    def test_browser_source_prefix(self):
        """Browser来源前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("browser", {"app_name": "Chrome"})
        assert "浏览器" in result
        assert "Chrome" in result

    def test_drag_source_prefix(self):
        """Drag来源前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("drag", {})
        assert "拖拽" in result

    def test_chat_source_prefix(self):
        """Chat来源前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("chat", {})
        assert "连续对话" in result

    def test_revision_source_prefix(self):
        """Revision来源前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("revision", {})
        assert "修订" in result

    def test_with_task(self):
        """带任务的前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("drag", {"task": "翻译为英文"})
        assert "翻译为英文" in result

    def test_with_custom_instruction(self):
        """带自定义指令的前缀"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("drag", {"custom_instruction": "改为被动语态"})
        assert "改为被动语态" in result
        assert "严格按此指令" in result

    def test_unknown_source(self):
        """未知来源返回空"""
        from asu_custom_agent import build_context_prefix
        result = build_context_prefix("unknown_source", {})
        # 未知来源没有基础描述，但如果有meta信息也会生成
        assert isinstance(result, str)


# ==========================================
# load_persona 测试
# ==========================================

class TestLoadPersona:
    """Persona加载测试"""

    def test_load_existing_persona(self):
        """加载存在的persona"""
        from asu_custom_agent import load_persona
        # 检查personas目录是否有文件
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personas")
        if os.path.exists(personas_dir):
            files = [f for f in os.listdir(personas_dir) if f.endswith('.md')]
            if files:
                persona_name = files[0].replace('.md', '')
                result = load_persona(persona_name)
                assert len(result) > 0

    def test_load_nonexistent_persona_fallback(self):
        """加载不存在的persona回退到default"""
        from asu_custom_agent import load_persona
        result = load_persona("nonexistent_persona_xyz")
        assert len(result) > 0

    def test_load_persona_returns_string(self):
        """load_persona 返回字符串"""
        from asu_custom_agent import load_persona
        result = load_persona("default")
        assert isinstance(result, str)


# ==========================================
# ASUAgentMemory 测试（SQLite）
# ==========================================

class TestASUAgentMemory:
    """Agent记忆管理测试"""

    @pytest.fixture
    def memory(self, tmp_path):
        from asu_custom_agent import ASUAgentMemory
        db_path = str(tmp_path / "test_agent.db")
        return ASUAgentMemory(db_path=db_path)

    def test_init_creates_tables(self, memory):
        """初始化创建表"""
        conn = sqlite3.connect(memory.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "sessions" in tables
        assert "messages" in tables

    def test_get_context_creates_session(self, memory):
        """获取上下文自动创建session"""
        result = memory.get_context("test_session_1")
        assert "messages" in result
        assert "persona" in result
        assert result["persona"] == "default"
        assert result["messages"] == []

    def test_add_message(self, memory):
        """添加消息"""
        memory.add_message("session_1", "user", "Hello")
        memory.add_message("session_1", "assistant", "Hi there")
        
        result = memory.get_context("session_1")
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["role"] == "assistant"
        assert result["messages"][1]["content"] == "Hi there"

    def test_set_persona(self, memory):
        """设置persona"""
        memory.set_persona("session_2", "translator")
        result = memory.get_context("session_2")
        assert result["persona"] == "translator"

    def test_set_persona_update(self, memory):
        """更新已有session的persona"""
        memory.get_context("session_3")  # 创建session
        memory.set_persona("session_3", "polisher")
        result = memory.get_context("session_3")
        assert result["persona"] == "polisher"

    def test_clear_session(self, memory):
        """清除session"""
        memory.add_message("session_4", "user", "msg1")
        memory.add_message("session_4", "assistant", "msg2")
        memory.set_persona("session_4", "custom")
        
        memory.clear("session_4")
        result = memory.get_context("session_4")
        assert result["messages"] == []
        assert result["persona"] == "default"

    def test_session_count(self, memory):
        """session计数"""
        assert memory.session_count() == 0
        memory.get_context("s1")
        memory.get_context("s2")
        memory.get_context("s3")
        assert memory.session_count() == 3

    def test_multiple_sessions_isolation(self, memory):
        """多session隔离"""
        memory.add_message("s1", "user", "message for s1")
        memory.add_message("s2", "user", "message for s2")
        
        r1 = memory.get_context("s1")
        r2 = memory.get_context("s2")
        
        assert len(r1["messages"]) == 1
        assert r1["messages"][0]["content"] == "message for s1"
        assert len(r2["messages"]) == 1
        assert r2["messages"][0]["content"] == "message for s2"

    def test_message_ordering(self, memory):
        """消息按时间排序"""
        memory.add_message("s1", "user", "first")
        time.sleep(0.01)
        memory.add_message("s1", "assistant", "second")
        time.sleep(0.01)
        memory.add_message("s1", "user", "third")
        
        result = memory.get_context("s1")
        assert len(result["messages"]) == 3
        assert result["messages"][0]["content"] == "first"
        assert result["messages"][1]["content"] == "second"
        assert result["messages"][2]["content"] == "third"


# ==========================================
# LLM Provider 测试
# ==========================================

class TestLLMProvider:
    """LLM Provider 功能测试"""

    def test_load_config_default(self):
        """加载默认配置"""
        from llm_provider import load_config
        # 保存当前目录
        original_dir = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                config = load_config()
                assert "provider_type" in config
                assert config["provider_type"] in ("minimax", "local")
            finally:
                os.chdir(original_dir)

    def test_save_and_load_config(self):
        """保存和加载配置"""
        from llm_provider import save_config, load_config
        original_dir = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                test_config = {
                    "provider_type": "local",
                    "local_api_base": "http://localhost:8080/v1",
                    "local_model": "gpt-4"
                }
                save_config(test_config)
                loaded = load_config()
                assert loaded["provider_type"] == "local"
                assert loaded["local_api_base"] == "http://localhost:8080/v1"
                assert loaded["local_model"] == "gpt-4"
            finally:
                os.chdir(original_dir)

    def test_base_provider_interface(self):
        """BaseProvider 接口定义"""
        from llm_provider import BaseProvider
        provider = BaseProvider()
        
        with pytest.raises(NotImplementedError):
            list(provider.stream_chat("test"))
        
        with pytest.raises(NotImplementedError):
            list(provider.stream_chat_with_history([]))

    def test_minimax_provider_init(self):
        """MiniMaxProvider 初始化"""
        from llm_provider import MiniMaxProvider
        provider = MiniMaxProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert "minimax" in provider.base_url
        assert provider.default_model == "MiniMax-M3"

    def test_local_provider_init(self):
        """LocalProvider 初始化"""
        from llm_provider import LocalProvider
        provider = LocalProvider(api_base="http://localhost:11434/v1", model="llama3")
        # api_base 会自动追加 /chat/completions
        assert provider.api_base == "http://localhost:11434/v1/chat/completions"
        assert provider.model == "llama3"

    def test_local_provider_url_trailing_slash(self):
        """LocalProvider 处理尾部斜杠"""
        from llm_provider import LocalProvider
        provider = LocalProvider(api_base="http://localhost:11434/v1/", model="llama3")
        assert provider.api_base == "http://localhost:11434/v1/chat/completions"

    def test_provider_factory(self):
        """ProviderFactory 创建 Provider"""
        from llm_provider import ProviderFactory
        provider = ProviderFactory.create_provider()
        assert provider is not None

    def test_minimax_stream_chat_builds_correct_messages(self):
        """MiniMax stream_chat 构建正确的消息格式"""
        from llm_provider import MiniMaxProvider
        provider = MiniMaxProvider(api_key="test_key")
        
        # 收集传给 _do_stream 的 messages
        captured_messages = []
        original_do_stream = provider._do_stream
        
        def mock_do_stream(messages):
            captured_messages.extend(messages)
            yield "test"
        
        provider._do_stream = mock_do_stream
        
        # 带 system_prompt
        list(provider.stream_chat("hello", system_prompt="You are helpful"))
        assert len(captured_messages) == 2
        assert captured_messages[0]["role"] == "system"
        assert captured_messages[0]["content"] == "You are helpful"
        assert captured_messages[1]["role"] == "user"
        assert captured_messages[1]["content"] == "hello"
        
        # 不带 system_prompt
        captured_messages.clear()
        list(provider.stream_chat("hello"))
        assert len(captured_messages) == 1
        assert captured_messages[0]["role"] == "user"


# ==========================================
# CONTEXT_DESCRIPTIONS 测试
# ==========================================

class TestContextDescriptions:
    """上下文描述配置测试"""

    def test_all_source_types_have_descriptions(self):
        """所有来源类型都有描述"""
        from asu_custom_agent import CONTEXT_DESCRIPTIONS
        expected_sources = ["ide", "browser", "drag", "chat", "revision"]
        for source in expected_sources:
            assert source in CONTEXT_DESCRIPTIONS
            assert len(CONTEXT_DESCRIPTIONS[source]) > 0

    def test_ide_description_mentions_selection(self):
        """IDE描述提到选区概念"""
        from asu_custom_agent import CONTEXT_DESCRIPTIONS
        assert "selection" in CONTEXT_DESCRIPTIONS["ide"].lower() or "选" in CONTEXT_DESCRIPTIONS["ide"]

    def test_revision_description_mentions_revision(self):
        """修订描述提到修订概念"""
        from asu_custom_agent import CONTEXT_DESCRIPTIONS
        assert "修订" in CONTEXT_DESCRIPTIONS["revision"] or "修改" in CONTEXT_DESCRIPTIONS["revision"]