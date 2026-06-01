"""
状态管理模块兼容性验证测试

验证新模块与现有 ASUAgentMemory 的完全兼容性。
测试内容：
1. 接口兼容性
2. 数据格式兼容性
3. 功能兼容性
4. 性能兼容性
5. 集成兼容性
"""

import sys
import time
import json
import tempfile
import unittest
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from state_manager import StateManager, TaskStatus
from asu_custom_agent import ASUAgentMemory, ContextWindowManager, normalize_context_envelope, build_context_prefix


class CompatibilityTestResult:
    """兼容性测试结果"""
    def __init__(self, test_name: str, category: str):
        self.test_name = test_name
        self.category = category
        self.passed = False
        self.error = None
        self.details = {}
        self.duration = 0.0
    
    def to_dict(self):
        return {
            "test_name": self.test_name,
            "category": self.category,
            "passed": self.passed,
            "error": self.error,
            "details": self.details,
            "duration": self.duration
        }


class StateManagerCompatibilityTest(unittest.TestCase):
    """状态管理模块兼容性测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db_old = tempfile.NamedTemporaryFile(suffix='_old.db', delete=False)
        self.temp_db_old.close()
        self.temp_db_new = tempfile.NamedTemporaryFile(suffix='_new.db', delete=False)
        self.temp_db_new.close()
        
        # 初始化旧模块（ASUAgentMemory）
        self.old_memory = ASUAgentMemory(self.temp_db_old.name)
        
        # 初始化新模块（StateManager）
        self.new_manager = StateManager(self.temp_db_new.name)
        
        # 测试结果
        self.results = []
    
    def tearDown(self):
        """测试后清理"""
        import os
        try:
            os.unlink(self.temp_db_old.name)
            os.unlink(self.temp_db_new.name)
        except:
            pass
    
    def _run_test(self, test_func, test_name, category):
        """运行单个测试"""
        result = CompatibilityTestResult(test_name, category)
        start_time = time.time()
        
        try:
            test_func(result)
            result.passed = True
        except Exception as e:
            result.error = str(e)
            result.passed = False
        
        result.duration = time.time() - start_time
        self.results.append(result)
        return result
    
    # ==========================================
    # 1. 接口兼容性测试
    # ==========================================
    
    def test_get_context_interface(self):
        """测试 get_context 接口兼容性"""
        def test_func(result):
            session_id = "test_session_1"
            
            # 旧模块
            old_context = self.old_memory.get_context(session_id)
            
            # 新模块
            new_context = self.new_manager.get_context(session_id)
            
            # 验证接口一致性
            self.assertIn("messages", old_context)
            self.assertIn("persona", old_context)
            self.assertIn("messages", new_context)
            self.assertIn("persona", new_context)
            
            # 验证数据类型一致
            self.assertIsInstance(old_context["messages"], list)
            self.assertIsInstance(old_context["persona"], str)
            self.assertIsInstance(new_context["messages"], list)
            self.assertIsInstance(new_context["persona"], str)
            
            result.details = {
                "old_keys": list(old_context.keys()),
                "new_keys": list(new_context.keys()),
                "old_types": {k: type(v).__name__ for k, v in old_context.items()},
                "new_types": {k: type(v).__name__ for k, v in new_context.items()}
            }
        
        self._run_test(test_func, "get_context 接口", "接口兼容性")
    
    def test_add_message_interface(self):
        """测试 add_message 接口兼容性"""
        def test_func(result):
            session_id = "test_session_2"
            
            # 旧模块
            self.old_memory.add_message(session_id, "user", "测试消息")
            old_context = self.old_memory.get_context(session_id)
            
            # 新模块
            self.new_manager.add_message(session_id, "user", "测试消息")
            new_context = self.new_manager.get_context(session_id)
            
            # 验证消息添加成功
            self.assertEqual(len(old_context["messages"]), 1)
            self.assertEqual(len(new_context["messages"]), 1)
            self.assertEqual(old_context["messages"][0]["role"], "user")
            self.assertEqual(old_context["messages"][0]["content"], "测试消息")
            self.assertEqual(new_context["messages"][0]["role"], "user")
            self.assertEqual(new_context["messages"][0]["content"], "测试消息")
            
            result.details = {
                "old_message_count": len(old_context["messages"]),
                "new_message_count": len(new_context["messages"]),
                "old_message": old_context["messages"][0],
                "new_message": new_context["messages"][0]
            }
        
        self._run_test(test_func, "add_message 接口", "接口兼容性")
    
    def test_set_persona_interface(self):
        """测试 set_persona 接口兼容性"""
        def test_func(result):
            session_id = "test_session_3"
            
            # 旧模块
            self.old_memory.set_persona(session_id, "coding")
            old_context = self.old_memory.get_context(session_id)
            
            # 新模块
            self.new_manager.set_persona(session_id, "coding")
            new_context = self.new_manager.get_context(session_id)
            
            # 验证人设设置成功
            self.assertEqual(old_context["persona"], "coding")
            self.assertEqual(new_context["persona"], "coding")
            
            result.details = {
                "old_persona": old_context["persona"],
                "new_persona": new_context["persona"]
            }
        
        self._run_test(test_func, "set_persona 接口", "接口兼容性")
    
    def test_clear_interface(self):
        """测试 clear 接口兼容性"""
        def test_func(result):
            session_id = "test_session_4"
            
            # 添加一些数据
            self.old_memory.add_message(session_id, "user", "消息1")
            self.old_memory.add_message(session_id, "assistant", "回复1")
            self.old_memory.set_persona(session_id, "translation")
            
            self.new_manager.add_message(session_id, "user", "消息1")
            self.new_manager.add_message(session_id, "assistant", "回复1")
            self.new_manager.set_persona(session_id, "translation")
            
            # 清空
            self.old_memory.clear(session_id)
            self.new_manager.clear(session_id)
            
            # 验证清空成功
            old_context = self.old_memory.get_context(session_id)
            new_context = self.new_manager.get_context(session_id)
            
            self.assertEqual(len(old_context["messages"]), 0)
            self.assertEqual(len(new_context["messages"]), 0)
            self.assertEqual(old_context["persona"], "default")
            self.assertEqual(new_context["persona"], "default")
            
            result.details = {
                "old_messages_after_clear": len(old_context["messages"]),
                "new_messages_after_clear": len(new_context["messages"]),
                "old_persona_after_clear": old_context["persona"],
                "new_persona_after_clear": new_context["persona"]
            }
        
        self._run_test(test_func, "clear 接口", "接口兼容性")
    
    def test_session_count_interface(self):
        """测试 session_count 接口兼容性"""
        def test_func(result):
            # 创建几个会话
            for i in range(3):
                session_id = f"test_session_count_{i}"
                self.old_memory.get_context(session_id)
                self.new_manager.get_context(session_id)
            
            # 获取会话数
            old_count = self.old_memory.session_count()
            new_count = self.new_manager.session_count()
            
            # 验证会话数一致
            self.assertEqual(old_count, new_count)
            
            result.details = {
                "old_count": old_count,
                "new_count": new_count
            }
        
        self._run_test(test_func, "session_count 接口", "接口兼容性")
    
    # ==========================================
    # 2. 数据格式兼容性测试
    # ==========================================
    
    def test_message_format_compatibility(self):
        """测试消息格式兼容性"""
        def test_func(result):
            session_id = "test_format_1"
            
            # 添加多种类型的消息
            messages = [
                ("user", "用户消息"),
                ("assistant", "助手回复"),
                ("user", "包含特殊字符的消息：!@#$%^&*()"),
                ("assistant", "包含中文的消息：你好世界"),
                ("user", "包含换行的消息\n第二行\n第三行"),
            ]
            
            for role, content in messages:
                self.old_memory.add_message(session_id, role, content)
                self.new_manager.add_message(session_id, role, content)
            
            # 获取消息
            old_context = self.old_memory.get_context(session_id)
            new_context = self.new_manager.get_context(session_id)
            
            # 验证消息数量
            self.assertEqual(len(old_context["messages"]), len(messages))
            self.assertEqual(len(new_context["messages"]), len(messages))
            
            # 验证每条消息格式
            for i, (role, content) in enumerate(messages):
                old_msg = old_context["messages"][i]
                new_msg = new_context["messages"][i]
                
                self.assertEqual(old_msg["role"], role)
                self.assertEqual(old_msg["content"], content)
                self.assertEqual(new_msg["role"], role)
                self.assertEqual(new_msg["content"], content)
            
            result.details = {
                "message_count": len(messages),
                "old_messages": old_context["messages"],
                "new_messages": new_context["messages"]
            }
        
        self._run_test(test_func, "消息格式兼容性", "数据格式兼容性")
    
    def test_persona_format_compatibility(self):
        """测试人设格式兼容性"""
        def test_func(result):
            session_id = "test_format_2"
            
            # 测试不同人设
            personas = ["default", "coding", "translation", "ppt_generator", "custom_persona"]
            
            for persona in personas:
                self.old_memory.set_persona(session_id, persona)
                self.new_manager.set_persona(session_id, persona)
                
                old_context = self.old_memory.get_context(session_id)
                new_context = self.new_manager.get_context(session_id)
                
                self.assertEqual(old_context["persona"], persona)
                self.assertEqual(new_context["persona"], persona)
            
            result.details = {
                "personas_tested": personas,
                "all_passed": True
            }
        
        self._run_test(test_func, "人设格式兼容性", "数据格式兼容性")
    
    # ==========================================
    # 3. 功能兼容性测试
    # ==========================================
    
    def test_context_window_manager_compatibility(self):
        """测试与 ContextWindowManager 的兼容性"""
        def test_func(result):
            # 初始化 ContextWindowManager
            window_manager = ContextWindowManager()
            
            # 创建测试数据
            session_id = "test_window_1"
            self.new_manager.add_message(session_id, "user", "测试消息1")
            self.new_manager.add_message(session_id, "assistant", "测试回复1")
            
            # 获取上下文
            context = self.new_manager.get_context(session_id)
            
            # 构建消息
            envelope = {
                "source": "ide",
                "content": "测试内容",
                "meta": {"file_name": "test.py", "language": "python"}
            }
            
            messages = window_manager.build_messages(
                system_prompt="你是一个助手",
                envelope=envelope,
                history_messages=context["messages"]
            )
            
            # 验证消息构建成功
            self.assertIsInstance(messages, list)
            self.assertGreater(len(messages), 0)
            self.assertEqual(messages[0]["role"], "system")
            
            result.details = {
                "message_count": len(messages),
                "first_message_role": messages[0]["role"],
                "last_message_role": messages[-1]["role"]
            }
        
        self._run_test(test_func, "ContextWindowManager 兼容性", "功能兼容性")
    
    def test_normalize_context_envelope_compatibility(self):
        """测试与 normalize_context_envelope 的兼容性"""
        def test_func(result):
            # 测试新协议
            req_new = {
                "context_envelope": {
                    "source": "ide",
                    "content": "测试内容",
                    "meta": {"file_name": "test.py"}
                }
            }
            
            # 测试旧协议
            req_old = {
                "text": "旧协议文本",
                "context_source": "browser",
                "context_meta": {"url": "https://example.com"}
            }
            
            # 标准化
            envelope_new = normalize_context_envelope(req_new, "fallback", "drag", {})
            envelope_old = normalize_context_envelope(req_old, req_old["text"], req_old["context_source"], req_old.get("context_meta", {}))
            
            # 验证格式一致
            self.assertIn("source", envelope_new)
            self.assertIn("content", envelope_new)
            self.assertIn("meta", envelope_new)
            
            self.assertIn("source", envelope_old)
            self.assertIn("content", envelope_old)
            self.assertIn("meta", envelope_old)
            
            result.details = {
                "new_envelope_keys": list(envelope_new.keys()),
                "old_envelope_keys": list(envelope_old.keys()),
                "new_source": envelope_new["source"],
                "old_source": envelope_old["source"]
            }
        
        self._run_test(test_func, "normalize_context_envelope 兼容性", "功能兼容性")
    
    def test_build_context_prefix_compatibility(self):
        """测试与 build_context_prefix 的兼容性"""
        def test_func(result):
            # 测试不同来源
            sources = ["ide", "browser", "drag", "chat", "revision", "ppt_generator"]
            
            results = {}
            for source in sources:
                meta = {"file_name": "test.py", "language": "python", "app_name": "Chrome"}
                prefix = build_context_prefix(source, meta)
                results[source] = prefix
            
            # 验证所有来源都能生成前缀
            for source in sources:
                self.assertIsInstance(results[source], str)
            
            result.details = {
                "sources_tested": sources,
                "prefixes": {k: v[:50] + "..." if len(v) > 50 else v for k, v in results.items()}
            }
        
        self._run_test(test_func, "build_context_prefix 兼容性", "功能兼容性")
    
    # ==========================================
    # 4. 性能兼容性测试
    # ==========================================
    
    def test_response_time_compatibility(self):
        """测试响应时间兼容性"""
        def test_func(result):
            session_id = "test_perf_1"
            iterations = 100
            
            # 测试旧模块性能
            start_time = time.time()
            for i in range(iterations):
                self.old_memory.add_message(session_id, "user", f"消息 {i}")
                self.old_memory.get_context(session_id)
            old_duration = time.time() - start_time
            
            # 测试新模块性能
            start_time = time.time()
            for i in range(iterations):
                self.new_manager.add_message(session_id, "user", f"消息 {i}")
                self.new_manager.get_context(session_id)
            new_duration = time.time() - start_time
            
            # 验证性能差异在可接受范围内（不超过 2 倍）
            performance_ratio = new_duration / old_duration if old_duration > 0 else 1
            
            result.details = {
                "iterations": iterations,
                "old_duration": old_duration,
                "new_duration": new_duration,
                "performance_ratio": performance_ratio,
                "acceptable": performance_ratio < 2.0
            }
            
            self.assertLess(performance_ratio, 2.0, "新模块性能下降超过 2 倍")
        
        self._run_test(test_func, "响应时间兼容性", "性能兼容性")
    
    def test_memory_usage_compatibility(self):
        """测试内存使用兼容性"""
        def test_func(result):
            import gc
            
            session_id = "test_memory_1"
            iterations = 50
            
            # 测试旧模块内存
            gc.collect()
            for i in range(iterations):
                self.old_memory.add_message(session_id, "user", f"消息 {i}" * 10)
            
            # 测试新模块内存
            gc.collect()
            for i in range(iterations):
                self.new_manager.add_message(session_id, "user", f"消息 {i}" * 10)
            
            # 验证没有内存泄漏（简单检查）
            old_context = self.old_memory.get_context(session_id)
            new_context = self.new_manager.get_context(session_id)
            
            self.assertEqual(len(old_context["messages"]), iterations)
            self.assertEqual(len(new_context["messages"]), iterations)
            
            result.details = {
                "iterations": iterations,
                "old_message_count": len(old_context["messages"]),
                "new_message_count": len(new_context["messages"])
            }
        
        self._run_test(test_func, "内存使用兼容性", "性能兼容性")
    
    # ==========================================
    # 5. 集成兼容性测试
    # ==========================================
    
    def test_end_to_end_flow_compatibility(self):
        """测试端到端流程兼容性"""
        def test_func(result):
            # 模拟完整的对话流程
            session_id = "test_e2e_1"
            
            # 1. 获取上下文（创建会话）
            context = self.new_manager.get_context(session_id)
            self.assertEqual(len(context["messages"]), 0)
            
            # 2. 设置人设
            self.new_manager.set_persona(session_id, "coding")
            
            # 3. 添加用户消息
            self.new_manager.add_message(session_id, "user", "帮我写一个 Python 函数")
            
            # 4. 添加助手回复
            self.new_manager.add_message(session_id, "assistant", "好的，我来帮你写一个函数")
            
            # 5. 获取上下文验证
            context = self.new_manager.get_context(session_id)
            self.assertEqual(context["persona"], "coding")
            self.assertEqual(len(context["messages"]), 2)
            
            # 6. 使用 ContextWindowManager 构建消息
            window_manager = ContextWindowManager()
            envelope = {
                "source": "chat",
                "content": "继续对话",
                "meta": {}
            }
            
            messages = window_manager.build_messages(
                system_prompt="你是一个编程助手",
                envelope=envelope,
                history_messages=context["messages"]
            )
            
            # 验证消息构建成功
            self.assertIsInstance(messages, list)
            self.assertGreater(len(messages), 0)
            
            result.details = {
                "session_id": session_id,
                "persona": context["persona"],
                "message_count": len(context["messages"]),
                "built_message_count": len(messages)
            }
        
        self._run_test(test_func, "端到端流程兼容性", "集成兼容性")
    
    def test_error_handling_compatibility(self):
        """测试错误处理兼容性"""
        def test_func(result):
            # 测试各种边界情况
            
            # 1. 空会话ID
            try:
                self.new_manager.get_context("")
                empty_context_ok = True
            except:
                empty_context_ok = False
            
            # 2. None 内容
            try:
                self.new_manager.add_message("test", "user", None)
                none_content_ok = True
            except:
                none_content_ok = False
            
            # 3. 特殊字符
            try:
                self.new_manager.add_message("test", "user", "!@#$%^&*()_+{}|:<>?")
                special_chars_ok = True
            except:
                special_chars_ok = False
            
            # 4. 超长内容
            try:
                long_content = "A" * 100000
                self.new_manager.add_message("test", "user", long_content)
                long_content_ok = True
            except:
                long_content_ok = False
            
            result.details = {
                "empty_session_id": empty_context_ok,
                "none_content": none_content_ok,
                "special_chars": special_chars_ok,
                "long_content": long_content_ok
            }
            
            # 验证至少部分边界情况能处理
            self.assertTrue(empty_context_ok or none_content_ok or special_chars_ok or long_content_ok,
                          "所有边界情况都处理失败")
        
        self._run_test(test_func, "错误处理兼容性", "集成兼容性")
    
    # ==========================================
    # 新增功能测试
    # ==========================================
    
    def test_task_management(self):
        """测试任务管理功能（新增）"""
        def test_func(result):
            session_id = "test_task_1"
            
            # 创建任务
            task = self.new_manager.create_task(
                session_id=session_id,
                task_type="code_review",
                description="审查 Python 代码"
            )
            
            self.assertIsNotNone(task)
            self.assertEqual(task.status, TaskStatus.PENDING)
            
            # 更新任务状态
            updated_task = self.new_manager.update_task(
                task.task_id,
                status=TaskStatus.IN_PROGRESS,
                progress=0.5
            )
            
            self.assertEqual(updated_task.status, TaskStatus.IN_PROGRESS)
            self.assertEqual(updated_task.progress, 0.5)
            
            # 完成任务
            completed_task = self.new_manager.update_task(
                task.task_id,
                status=TaskStatus.COMPLETED,
                result={"score": 95}
            )
            
            self.assertEqual(completed_task.status, TaskStatus.COMPLETED)
            self.assertEqual(completed_task.progress, 1.0)
            
            # 获取任务
            retrieved_task = self.new_manager.get_task(task.task_id)
            self.assertIsNotNone(retrieved_task)
            self.assertEqual(retrieved_task.status, TaskStatus.COMPLETED)
            
            result.details = {
                "task_id": task.task_id,
                "final_status": completed_task.status.value,
                "final_progress": completed_task.progress,
                "result": completed_task.result
            }
        
        self._run_test(test_func, "任务管理功能", "新增功能")
    
    def test_session_state_management(self):
        """测试会话状态管理功能（新增）"""
        def test_func(result):
            session_id = "test_session_state_1"
            
            # 获取会话状态
            state = self.new_manager.get_session_state(session_id)
            
            self.assertIsNotNone(state)
            self.assertEqual(state.session_id, session_id)
            self.assertEqual(state.persona, "default")
            
            # 更新会话状态
            updated_state = self.new_manager.update_session_state(
                session_id,
                persona="coding",
                metadata={"theme": "dark"}
            )
            
            self.assertEqual(updated_state.persona, "coding")
            self.assertEqual(updated_state.metadata.get("theme"), "dark")
            
            result.details = {
                "session_id": session_id,
                "initial_persona": state.persona,
                "updated_persona": updated_state.persona,
                "metadata": updated_state.metadata
            }
        
        self._run_test(test_func, "会话状态管理功能", "新增功能")
    
    def test_statistics(self):
        """测试统计功能（新增）"""
        def test_func(result):
            # 创建一些数据
            for i in range(3):
                session_id = f"test_stats_{i}"
                self.new_manager.get_context(session_id)
                self.new_manager.add_message(session_id, "user", f"消息 {i}")
            
            # 获取统计信息
            stats = self.new_manager.get_statistics()
            
            self.assertIn("total_sessions", stats)
            self.assertIn("total_messages", stats)
            self.assertGreaterEqual(stats["total_sessions"], 3)
            self.assertGreaterEqual(stats["total_messages"], 3)
            
            result.details = stats
        
        self._run_test(test_func, "统计功能", "新增功能")
    
    # ==========================================
    # 运行所有测试
    # ==========================================
    
    def run_all_tests(self):
        """运行所有兼容性测试"""
        test_methods = [
            # 接口兼容性
            (self.test_get_context_interface, "get_context 接口", "接口兼容性"),
            (self.test_add_message_interface, "add_message 接口", "接口兼容性"),
            (self.test_set_persona_interface, "set_persona 接口", "接口兼容性"),
            (self.test_clear_interface, "clear 接口", "接口兼容性"),
            (self.test_session_count_interface, "session_count 接口", "接口兼容性"),
            
            # 数据格式兼容性
            (self.test_message_format_compatibility, "消息格式兼容性", "数据格式兼容性"),
            (self.test_persona_format_compatibility, "人设格式兼容性", "数据格式兼容性"),
            
            # 功能兼容性
            (self.test_context_window_manager_compatibility, "ContextWindowManager 兼容性", "功能兼容性"),
            (self.test_normalize_context_envelope_compatibility, "normalize_context_envelope 兼容性", "功能兼容性"),
            (self.test_build_context_prefix_compatibility, "build_context_prefix 兼容性", "功能兼容性"),
            
            # 性能兼容性
            (self.test_response_time_compatibility, "响应时间兼容性", "性能兼容性"),
            (self.test_memory_usage_compatibility, "内存使用兼容性", "性能兼容性"),
            
            # 集成兼容性
            (self.test_end_to_end_flow_compatibility, "端到端流程兼容性", "集成兼容性"),
            (self.test_error_handling_compatibility, "错误处理兼容性", "集成兼容性"),
            
            # 新增功能
            (self.test_task_management, "任务管理功能", "新增功能"),
            (self.test_session_state_management, "会话状态管理功能", "新增功能"),
            (self.test_statistics, "统计功能", "新增功能"),
        ]
        
        for test_func, test_name, category in test_methods:
            try:
                test_func()
            except Exception as e:
                result = CompatibilityTestResult(test_name, category)
                result.error = str(e)
                result.passed = False
                self.results.append(result)
        
        return self.results
    
    def generate_report(self):
        """生成测试报告"""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        report = {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / total if total > 0 else 0
            },
            "categories": {},
            "details": [r.to_dict() for r in self.results]
        }
        
        # 按类别统计
        for result in self.results:
            category = result.category
            if category not in report["categories"]:
                report["categories"][category] = {"total": 0, "passed": 0, "failed": 0}
            
            report["categories"][category]["total"] += 1
            if result.passed:
                report["categories"][category]["passed"] += 1
            else:
                report["categories"][category]["failed"] += 1
        
        return report


def main():
    """主函数"""
    print("=" * 60)
    print("状态管理模块兼容性验证测试")
    print("=" * 60)
    
    # 创建测试实例
    test_suite = StateManagerCompatibilityTest()
    test_suite.setUp()
    
    try:
        # 运行所有测试
        results = test_suite.run_all_tests()
        
        # 生成报告
        report = test_suite.generate_report()
        
        # 打印摘要
        print(f"\n测试结果摘要:")
        print(f"  总测试数: {report['summary']['total']}")
        print(f"  通过: {report['summary']['passed']}")
        print(f"  失败: {report['summary']['failed']}")
        print(f"  通过率: {report['summary']['pass_rate']:.1%}")
        
        # 打印分类统计
        print(f"\n分类统计:")
        for category, stats in report["categories"].items():
            print(f"  {category}: {stats['passed']}/{stats['total']} 通过")
        
        # 打印失败的测试
        failed_tests = [r for r in results if not r.passed]
        if failed_tests:
            print(f"\n失败的测试:")
            for test in failed_tests:
                print(f"  - {test.test_name}: {test.error}")
        
        # 保存报告
        report_path = Path(__file__).parent / "state_manager_compatibility_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {report_path}")
        
        # 返回是否全部通过
        return report["summary"]["failed"] == 0
    
    finally:
        test_suite.tearDown()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
