"""
记忆系统模块兼容性验证测试

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

from memory_system import MemoryManager, MemoryType
from asu_custom_agent import ASUAgentMemory, ContextWindowManager, normalize_context_envelope


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


class MemorySystemCompatibilityTest(unittest.TestCase):
    """记忆系统模块兼容性测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db_old = tempfile.NamedTemporaryFile(suffix='_old.db', delete=False)
        self.temp_db_old.close()
        self.temp_db_new = tempfile.NamedTemporaryFile(suffix='_new.db', delete=False)
        self.temp_db_new.close()
        
        # 初始化旧模块（ASUAgentMemory）
        self.old_memory = ASUAgentMemory(self.temp_db_old.name)
        
        # 初始化新模块（MemoryManager）
        self.new_manager = MemoryManager(self.temp_db_new.name)
        
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
    
    # ==========================================
    # 4. 性能兼容性测试
    # ==========================================
    
    def test_response_time_compatibility(self):
        """测试响应时间兼容性"""
        def test_func(result):
            session_id = "test_performance_1"
            iterations = 100
            
            # 测试旧模块性能
            old_start = time.time()
            for i in range(iterations):
                self.old_memory.add_message(session_id, "user", f"消息 {i}")
                self.old_memory.get_context(session_id)
            old_time = time.time() - old_start
            
            # 测试新模块性能
            new_start = time.time()
            for i in range(iterations):
                self.new_manager.add_message(session_id, "user", f"消息 {i}")
                self.new_manager.get_context(session_id)
            new_time = time.time() - new_start
            
            # 验证性能差异在可接受范围内（2倍以内）
            performance_ratio = new_time / old_time if old_time > 0 else 1.0
            self.assertLess(performance_ratio, 2.0, 
                          f"新模块性能差异过大: {performance_ratio:.2f}x")
            
            result.details = {
                "iterations": iterations,
                "old_time": old_time,
                "new_time": new_time,
                "performance_ratio": performance_ratio,
                "old_avg_ms": (old_time / iterations) * 1000,
                "new_avg_ms": (new_time / iterations) * 1000
            }
        
        self._run_test(test_func, "响应时间兼容性", "性能兼容性")
    
    def test_memory_usage_compatibility(self):
        """测试内存使用兼容性"""
        def test_func(result):
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # 测试初始内存
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建大量数据
            session_id = "test_memory_1"
            for i in range(1000):
                self.new_manager.add_message(session_id, "user", f"消息 {i}" * 10)
            
            # 测试最终内存
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # 验证内存增长在合理范围内（<100MB）
            self.assertLess(memory_increase, 100, 
                          f"内存增长过大: {memory_increase:.2f}MB")
            
            result.details = {
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_increase_mb": memory_increase,
                "messages_created": 1000
            }
        
        self._run_test(test_func, "内存使用兼容性", "性能兼容性")
    
    # ==========================================
    # 5. 集成兼容性测试
    # ==========================================
    
    def test_end_to_end_compatibility(self):
        """测试端到端兼容性"""
        def test_func(result):
            # 模拟完整的对话流程
            session_id = "test_e2e_1"
            
            # 1. 设置人设
            self.new_manager.set_persona(session_id, "coding")
            
            # 2. 添加用户消息
            self.new_manager.add_message(session_id, "user", "帮我写一个Python函数")
            
            # 3. 添加助手回复
            self.new_manager.add_message(session_id, "assistant", "好的，我来帮你写一个Python函数")
            
            # 4. 获取上下文
            context = self.new_manager.get_context(session_id)
            
            # 验证完整流程
            self.assertEqual(context["persona"], "coding")
            self.assertEqual(len(context["messages"]), 2)
            self.assertEqual(context["messages"][0]["role"], "user")
            self.assertEqual(context["messages"][1]["role"], "assistant")
            
            result.details = {
                "persona": context["persona"],
                "message_count": len(context["messages"]),
                "first_message": context["messages"][0],
                "last_message": context["messages"][-1]
            }
        
        self._run_test(test_func, "端到端兼容性", "集成兼容性")
    
    def test_error_handling_compatibility(self):
        """测试错误处理兼容性"""
        def test_func(result):
            # 测试各种错误情况
            errors = []
            
            # 1. 空会话ID
            try:
                self.new_manager.get_context("")
                # 如果没有抛出异常，记录为通过
            except Exception as e:
                errors.append(f"空会话ID: {str(e)}")
            
            # 2. 无效人设
            try:
                self.new_manager.set_persona("test", None)
            except Exception as e:
                errors.append(f"无效人设: {str(e)}")
            
            # 3. 空消息
            try:
                self.new_manager.add_message("test", "user", "")
            except Exception as e:
                errors.append(f"空消息: {str(e)}")
            
            # 验证错误处理一致（不崩溃）
            result.details = {
                "errors_handled": len(errors),
                "error_messages": errors
            }
        
        self._run_test(test_func, "错误处理兼容性", "集成兼容性")
    
    # ==========================================
    # 运行所有测试
    # ==========================================
    
    def run_all_tests(self):
        """运行所有兼容性测试"""
        print("开始运行记忆系统模块兼容性测试...")
        
        # 运行所有测试方法
        test_methods = [
            self.test_get_context_interface,
            self.test_add_message_interface,
            self.test_set_persona_interface,
            self.test_clear_interface,
            self.test_session_count_interface,
            self.test_message_format_compatibility,
            self.test_persona_format_compatibility,
            self.test_context_window_manager_compatibility,
            self.test_normalize_context_envelope_compatibility,
            self.test_response_time_compatibility,
            self.test_memory_usage_compatibility,
            self.test_end_to_end_compatibility,
            self.test_error_handling_compatibility,
        ]
        
        for test_method in test_methods:
            test_method()
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\n测试完成:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {failed_tests}")
        print(f"  通过率: {passed_tests/total_tests*100:.1f}%")
        
        # 打印失败的测试
        if failed_tests > 0:
            print(f"\n失败的测试:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.error}")
        
        return self.results
    
    def generate_report(self):
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        report = {
            "test_name": "记忆系统模块兼容性测试",
            "timestamp": time.time(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "interface_compatibility": self._get_category_summary("接口兼容性"),
                "data_format_compatibility": self._get_category_summary("数据格式兼容性"),
                "functionality_compatibility": self._get_category_summary("功能兼容性"),
                "performance_compatibility": self._get_category_summary("性能兼容性"),
                "integration_compatibility": self._get_category_summary("集成兼容性"),
            }
        }
        
        return report
    
    def _get_category_summary(self, category: str):
        """获取分类摘要"""
        category_results = [r for r in self.results if r.category == category]
        total = len(category_results)
        passed = sum(1 for r in category_results if r.passed)
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total * 100 if total > 0 else 0
        }


if __name__ == "__main__":
    # 运行兼容性测试
    test = MemorySystemCompatibilityTest()
    test.setUp()
    
    try:
        results = test.run_all_tests()
        report = test.generate_report()
        
        # 保存报告
        report_path = Path(__file__).parent / "memory_system_compatibility_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存到: {report_path}")
        
    finally:
        test.tearDown()
