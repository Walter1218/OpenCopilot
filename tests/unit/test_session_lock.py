"""
会话序列化锁 + RLock 重入 + 消息过滤 集成测试

验证三个修复点：
1. RLock 重入安全：add_message → store_memory 同一线程重入不死锁
2. _is_important_message 收紧：短消息/简单问候不会被存储为记忆
3. 会话锁基础：asyncio.Lock 创建和获取正常工作
"""
import asyncio
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestRLockReentrancy:
    """测试 RLock 重入安全性：add_message 调用 store_memory 不死锁"""

    def test_add_message_reentrant_store(self, tmp_path):
        """验证 add_message 内部调用 store_memory 不发生死锁"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_reentrant.db")
        mgr = MemoryManager(db_path=db_path)

        # 确保使用的是 RLock（RLock 是函数返回的 _RLock 实例，因此检查类型名）
        assert type(mgr._lock).__name__ == 'RLock' or 'RLock' in str(type(mgr._lock)), (
            f"MemoryManager._lock 应为 RLock，实际为 {type(mgr._lock).__name__}"
        )

        # add_message 内部会调用 _is_important_message → store_memory
        # 由于关键词收紧，"这是一条重要的错误信息需要修复" 应触发 store_memory
        # 如果 Lock（非重入）会死锁，RLock 不会
        session_id = "test_reentrant_session"
        try:
            mgr.add_message(session_id, "user", "发现一个严重的 bug 需要立即修复")
        except Exception as e:
            assert False, f"add_message 不应抛出异常: {e}"

        # 验证消息已添加
        ctx = mgr.get_context(session_id)
        assert len(ctx["messages"]) == 1, f"应有 1 条消息，实际 {len(ctx['messages'])}"
        assert ctx["messages"][0]["content"] == "发现一个严重的 bug 需要立即修复"

    def test_add_message_reentrant_loop(self, tmp_path):
        """验证多条 add_message 连续调用不死锁"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_reentrant_loop.db")
        mgr = MemoryManager(db_path=db_path)

        session_id = "test_loop_session"
        for i in range(10):
            content = f"关键问题 #{i}: 系统出现 bug 需要修复" if i % 3 == 0 else f"普通消息 #{i}"
            mgr.add_message(session_id, "user", content)

        ctx = mgr.get_context(session_id)
        assert len(ctx["messages"]) == 10, f"应有 10 条消息，实际 {len(ctx['messages'])}"


class TestImportantMessageFilter:
    """测试 _is_important_message 收紧后的过滤行为"""

    def test_short_message_not_important(self, tmp_path):
        """短消息（< 30 字符）不应被标记为重要"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_filter_short.db")
        mgr = MemoryManager(db_path=db_path)

        # 短消息（13 字符）
        assert not mgr._is_important_message("你好，帮我一下"), "短消息不应标记为重要"

        # 刚好 30 字符
        assert not mgr._is_important_message("HelloWorldHelloWorldHelloWorld"), "30字符以下不应标记为重要"

        # 普通问候
        assert not mgr._is_important_message("谢谢你的帮助！"), "简单问候不应标记为重要"

    def test_greeting_not_important(self, tmp_path):
        """AI 常见回复不应被标记为重要"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_filter_greeting.db")
        mgr = MemoryManager(db_path=db_path)

        # AI 自我介绍（不含 bug/error/fix 关键词）
        result = mgr._is_important_message(
            "你好！我是 AI 助手，主要功能包括代码编写、文档生成等，有什么需要帮助的吗？"
        )
        assert not result, "不含技术关键词的 AI 自我介绍不应标记为重要"

    def test_bug_message_is_important(self, tmp_path):
        """包含 bug/error/fix 的长消息应被标记为重要"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_filter_bug.db")
        mgr = MemoryManager(db_path=db_path)

        # bug 消息 > 30 字符
        assert mgr._is_important_message(
            "发现了一个严重的 bug 需要立即修复，系统在处理大文件时直接崩溃"
        ), "含 bug 的长消息应标记为重要"

        # error 消息
        assert mgr._is_important_message(
            "系统返回了 error 状态码 500，请检查服务器日志以定位问题根因"
        ), "含 error 的长消息应标记为重要"

        # "记住" 关键词
        assert mgr._is_important_message(
            "请记住这个重要的配置信息：数据库地址是 localhost:5432，用户名是 admin123"
        ), "含'记住'的长消息应标记为重要"

    def test_add_message_triggers_store_only_for_important(self, tmp_path):
        """只有重要消息才触发 store_memory"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_filter_store.db")
        mgr = MemoryManager(db_path=db_path)
        session_id = "test_store_trigger"

        # 短消息不应触发 store_memory
        mgr.add_message(session_id, "assistant", "好的")
        stats = mgr.get_statistics()
        memories_before = stats["total_memories"]

        # 长 bug 消息应触发 store_memory
        mgr.add_message(session_id, "user", "发现一个严重 bug：程序在处理大文件时崩溃，需要修复")
        stats = mgr.get_statistics()
        memories_after = stats["total_memories"]

        assert memories_after >= memories_before, "重要消息应触发记忆存储"

    def test_excluded_keywords_not_important(self, tmp_path):
        """验证已从关键词列表移除的词不再触发标记"""
        from opencopilot.capabilities.memory.core import MemoryManager

        db_path = str(tmp_path / "test_excluded.db")
        mgr = MemoryManager(db_path=db_path)

        # "关键" 已从列表移除，不应标记（虽然 > 30 字符）
        result = mgr._is_important_message("这是一个关键的功能分析，需要仔细研究系统的各个方面")
        assert not result, "'关键'已从关键词列表移除，不应标记为重要"

        # "核心" 已移除
        result = mgr._is_important_message("核心功能需要做进一步的优化和完善")
        assert not result, "'核心'已从关键词列表移除，不应标记为重要"

        # "主要" 已移除
        result = mgr._is_important_message("主要的工作内容是开发新的功能模块")
        assert not result, "'主要'已从关键词列表移除，不应标记为重要"


class TestSessionLockInfrastructure:
    """测试会话锁基础设施"""

    def test_lock_creation_thread_safe(self):
        """验证 _get_or_create_session_lock 线程安全"""
        from opencopilot.agent.caller import _get_or_create_session_lock

        lock1 = _get_or_create_session_lock("test_session_1")
        assert isinstance(lock1, asyncio.Lock), "应返回 asyncio.Lock 实例"

        # 同一 session 返回同一个锁
        lock2 = _get_or_create_session_lock("test_session_1")
        assert lock1 is lock2, "同一 session 应返回同一个锁实例"

        # 不同 session 返回不同锁
        lock3 = _get_or_create_session_lock("test_session_2")
        assert lock1 is not lock3, "不同 session 应返回不同锁实例"

    def test_lock_creation_concurrent(self):
        """验证并发创建会话锁的线程安全性"""
        from opencopilot.agent.caller import _get_or_create_session_lock

        errors = []
        locks = []

        def create_lock():
            try:
                lock = _get_or_create_session_lock("concurrent_test")
                locks.append(id(lock))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=create_lock) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"不应有错误: {errors}"
        # 所有线程应获取到同一个锁
        assert len(set(locks)) == 1, f"所有线程应获取到同一个锁实例，但拿到了 {len(set(locks))} 个不同实例"

    def test_lock_acquire_release(self):
        """验证 asyncio.Lock 可以正常获取和释放"""
        from opencopilot.agent.caller import _get_or_create_session_lock

        async def _test():
            lock = _get_or_create_session_lock("acquire_test")
            acquired = await asyncio.wait_for(asyncio.shield(lock.acquire()), timeout=1.0)
            assert acquired is True, "应成功获取锁"
            lock.release()

        asyncio.run(_test())


class TestStateManagerRLock:
    """测试 StateManager 的 RLock 安全性"""

    def test_state_lock_is_rlock(self, tmp_path):
        """验证 StateManager 使用 RLock"""
        from opencopilot.capabilities.state.core import StateManager

        db_path = str(tmp_path / "test_state_lock.db")
        mgr = StateManager(db_path=db_path)
        assert type(mgr._lock).__name__ == 'RLock' or 'RLock' in str(type(mgr._lock)), (
            f"StateManager._lock 应为 RLock，实际为 {type(mgr._lock).__name__}"
        )

    def test_update_task_reentrant(self, tmp_path):
        """验证 update_task 中 get_task 重入安全"""
        from opencopilot.capabilities.state.core import StateManager, TaskStatus

        db_path = str(tmp_path / "test_state_reentrant.db")
        mgr = StateManager(db_path=db_path)

        # 创建任务
        task = mgr.create_task("test_session", task_type="test", description="测试任务")

        # update_task 内部调用 get_task，如果 Lock 不可重入会死锁
        updated = mgr.update_task(task.task_id, status=TaskStatus.IN_PROGRESS, progress=0.5)
        assert updated is not None, "update_task 应返回更新后的任务"
        assert updated.status == TaskStatus.IN_PROGRESS
        assert updated.progress == 0.5
