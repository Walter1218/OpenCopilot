"""
MemoryManager 功能测试
"""
import pytest
import os



class TestMemoryManagerCompat:
    """兼容 ASUAgentMemory 接口"""

    @pytest.fixture
    def mem(self, temp_dir):
        from opencopilot.capabilities.memory import MemoryManager
        db_path = os.path.join(temp_dir, "test.db")
        m = MemoryManager(db_path=db_path)
        yield m
        try:
            os.remove(db_path)
        except:
            pass

    def test_compat_alias(self):
        from opencopilot.capabilities.memory import ASUAgentMemory, MemoryManager
        assert ASUAgentMemory is MemoryManager

    def test_get_context_creates_session(self, mem):
        ctx = mem.get_context("sess1")
        assert ctx["messages"] == []
        assert ctx["persona"] == "default"

    def test_add_message(self, mem):
        mem.add_message("s1", "user", "Hello")
        mem.add_message("s1", "assistant", "Hi")
        ctx = mem.get_context("s1")
        assert len(ctx["messages"]) == 2

    def test_set_persona(self, mem):
        mem.set_persona("s2", "translator")
        assert mem.get_context("s2")["persona"] == "translator"

    def test_clear_session(self, mem):
        mem.add_message("s3", "user", "msg")
        mem.set_persona("s3", "custom")
        mem.clear("s3")
        ctx = mem.get_context("s3")
        assert ctx["messages"] == []
        assert ctx["persona"] == "default"

    def test_session_count(self, mem):
        assert mem.session_count() == 0
        mem.get_context("a")
        mem.get_context("b")
        assert mem.session_count() == 2

    def test_multi_session_isolation(self, mem):
        mem.add_message("x", "user", "x msg")
        mem.add_message("y", "user", "y msg")
        assert mem.get_context("x")["messages"][0]["content"] == "x msg"
        assert mem.get_context("y")["messages"][0]["content"] == "y msg"


class TestMemoryManagerAdvanced:
    """高级记忆功能"""

    @pytest.fixture
    def mem(self, temp_dir):
        from opencopilot.capabilities.memory import MemoryManager
        db_path = os.path.join(temp_dir, "test.db")
        return MemoryManager(db_path=db_path)

    def test_store_memory(self, mem):
        from opencopilot.capabilities.memory import MemoryType
        mem.store_memory(
            content="test memory content",
            memory_type=MemoryType.SHORT_TERM,
            session_id="sess_store",
            importance=0.8,
            tags=["test"]
        )
        assert True

    def test_retrieve_memories(self, mem):
        from opencopilot.capabilities.memory import MemoryType
        mem.store_memory(
            content="unique phrase for testing retrieval",
            memory_type=MemoryType.SHORT_TERM,
            session_id="sess_retrieve",
        )
        results = mem.retrieve_memories(query="unique phrase", limit=10)
        assert len(results) > 0

    def test_get_statistics(self, mem):
        stats = mem.get_statistics()
        assert "total_memories" in stats or "total_sessions" in stats

    def test_default_manager(self):
        from opencopilot.capabilities.memory import get_default_manager
        mgr = get_default_manager()
        assert mgr is not None
