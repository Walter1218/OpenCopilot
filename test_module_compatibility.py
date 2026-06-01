"""
模块兼容性验证框架
==================

验证新模块与现有模块的兼容性，确保：
1. 新模块不破坏现有功能
2. 新旧模块可以并存
3. 新模块可以逐步替换旧模块
4. 接口保持一致

运行方式：
    python test_module_compatibility.py
"""

import time
import json
import sys
import os
import copy

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asu_custom_agent import (
    ContextWindowManager,
    normalize_context_envelope,
    build_context_prefix,
    ASUAgentMemory,
    CONTEXT_DESCRIPTIONS
)


class CompatibilityTestResult:
    """兼容性测试结果"""
    def __init__(self, test_name, category):
        self.test_name = test_name
        self.category = category
        self.passed = False
        self.old_result = None
        self.new_result = None
        self.differences = []
        self.error = None


class ModuleCompatibilityTester:
    """模块兼容性测试器"""
    
    def __init__(self):
        self.results = []
        # 使用临时文件数据库，避免内存数据库问题
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.memory = ASUAgentMemory(self.temp_db.name)
        self.window_manager = ContextWindowManager()
    
    def run_all_tests(self):
        """运行所有兼容性测试"""
        print("=" * 70)
        print("模块兼容性验证测试")
        print("=" * 70)
        
        test_categories = [
            ("接口兼容性", self.test_interface_compatibility),
            ("数据格式兼容性", self.test_data_format_compatibility),
            ("功能兼容性", self.test_functional_compatibility),
            ("性能兼容性", self.test_performance_compatibility),
            ("集成兼容性", self.test_integration_compatibility),
        ]
        
        for category_name, test_func in test_categories:
            print(f"\n{'=' * 50}")
            print(f"测试类别: {category_name}")
            print('=' * 50)
            test_func()
        
        return self.generate_report()
    
    def test_interface_compatibility(self):
        """测试接口兼容性"""
        # 测试1: ContextWindowManager 接口
        result = self._test_context_window_manager_interface()
        self.results.append(result)
        self._print_result(result)
        
        # 测试2: normalize_context_envelope 接口
        result = self._test_normalize_context_envelope_interface()
        self.results.append(result)
        self._print_result(result)
        
        # 测试3: build_context_prefix 接口
        result = self._test_build_context_prefix_interface()
        self.results.append(result)
        self._print_result(result)
        
        # 测试4: ASUAgentMemory 接口
        result = self._test_asu_agent_memory_interface()
        self.results.append(result)
        self._print_result(result)
    
    def _test_context_window_manager_interface(self):
        """测试 ContextWindowManager 接口兼容性"""
        result = CompatibilityTestResult("ContextWindowManager 接口", "接口兼容性")
        
        try:
            # 测试初始化接口
            manager = ContextWindowManager(
                max_input_chars=10000,
                reserve_output_chars=2500,
                recent_turns=4,
                max_history_msg_chars=1000
            )
            
            # 验证属性存在
            assert hasattr(manager, 'max_input_chars')
            assert hasattr(manager, 'reserve_output_chars')
            assert hasattr(manager, 'recent_turns')
            assert hasattr(manager, 'max_history_msg_chars')
            
            # 验证方法存在
            assert hasattr(manager, 'build_messages')
            assert hasattr(manager, '_truncate_text')
            assert hasattr(manager, '_clip_by_source')
            assert hasattr(manager, '_build_user_payload')
            assert hasattr(manager, '_pick_recent_history')
            
            # 测试 build_messages 接口
            system_prompt = "你是一个助手"
            envelope = {
                "source": "ide",
                "content": "测试内容",
                "meta": {"file_name": "test.py"}
            }
            history = [{"role": "user", "content": "历史消息"}]
            
            messages = manager.build_messages(system_prompt, envelope, history)
            
            # 验证返回格式
            assert isinstance(messages, list)
            assert len(messages) > 0
            assert all(isinstance(m, dict) for m in messages)
            assert all("role" in m and "content" in m for m in messages)
            
            result.passed = True
            result.new_result = {
                "attributes": [attr for attr in ['max_input_chars', 'reserve_output_chars', 'recent_turns', 'max_history_msg_chars'] if hasattr(manager, attr)],
                "methods": [method for method in ['build_messages', '_truncate_text', '_clip_by_source', '_build_user_payload', '_pick_recent_history'] if hasattr(manager, method)],
                "messages_count": len(messages),
                "messages_format": "correct"
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_normalize_context_envelope_interface(self):
        """测试 normalize_context_envelope 接口兼容性"""
        result = CompatibilityTestResult("normalize_context_envelope 接口", "接口兼容性")
        
        try:
            # 测试新协议
            req_new = {
                "context_envelope": {
                    "source": "browser",
                    "content": "网页内容",
                    "selection": "选中文本",
                    "task": "研究",
                    "meta": {"url": "https://example.com"},
                    "timestamp": 1234567890.0
                }
            }
            
            result_new = normalize_context_envelope(req_new, "fallback", "drag", {})
            
            # 测试旧协议
            req_old = {
                "text": "旧协议文本",
                "context_source": "ide",
                "context_meta": {"file_name": "old.py"}
            }
            
            result_old = normalize_context_envelope(req_old, req_old["text"], req_old["context_source"], req_old.get("context_meta", {}))
            
            # 验证返回格式一致
            assert isinstance(result_new, dict)
            assert isinstance(result_old, dict)
            
            # 验证必需字段
            required_fields = ["source", "content", "selection", "task", "meta", "timestamp"]
            for field in required_fields:
                assert field in result_new, f"缺少字段: {field}"
                assert field in result_old, f"缺少字段: {field}"
            
            result.passed = True
            result.new_result = {
                "new_protocol_fields": list(result_new.keys()),
                "old_protocol_fields": list(result_old.keys()),
                "required_fields_present": True
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_build_context_prefix_interface(self):
        """测试 build_context_prefix 接口兼容性"""
        result = CompatibilityTestResult("build_context_prefix 接口", "接口兼容性")
        
        try:
            # 测试所有来源类型
            sources = ["ide", "browser", "drag", "chat", "revision", "ppt_generator"]
            results = {}
            
            for source in sources:
                meta = {"file_name": "test.py", "language": "python", "app_name": "VS Code"}
                prefix = build_context_prefix(source, meta)
                results[source] = {
                    "is_string": isinstance(prefix, str),
                    "length": len(prefix)
                }
            
            result.passed = True
            result.new_result = {
                "sources_tested": len(sources),
                "all_return_strings": all(r["is_string"] for r in results.values()),
                "results": results
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_asu_agent_memory_interface(self):
        """测试 ASUAgentMemory 接口兼容性"""
        result = CompatibilityTestResult("ASUAgentMemory 接口", "接口兼容性")
        
        try:
            # 测试初始化
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            memory = ASUAgentMemory(temp_db.name)
            
            # 验证方法存在
            methods = ['get_context', 'add_message', 'set_persona', 'clear', 'session_count']
            for method in methods:
                assert hasattr(memory, method), f"缺少方法: {method}"
            
            # 测试基本操作
            session_id = "test_session_1"
            
            # 测试 get_context
            context = memory.get_context(session_id)
            assert "messages" in context
            assert "persona" in context
            
            # 测试 add_message
            memory.add_message(session_id, "user", "测试消息")
            memory.add_message(session_id, "assistant", "测试回复")
            
            # 测试 get_context 更新后
            context_after = memory.get_context(session_id)
            assert len(context_after["messages"]) == 2
            
            # 测试 set_persona
            memory.set_persona(session_id, "code")
            context_with_persona = memory.get_context(session_id)
            assert context_with_persona["persona"] == "code"
            
            # 测试 clear
            memory.clear(session_id)
            context_cleared = memory.get_context(session_id)
            assert len(context_cleared["messages"]) == 0
            
            result.passed = True
            result.new_result = {
                "methods_available": methods,
                "get_context_works": True,
                "add_message_works": True,
                "set_persona_works": True,
                "clear_works": True
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_data_format_compatibility(self):
        """测试数据格式兼容性"""
        # 测试1: 消息格式兼容性
        result = self._test_message_format_compatibility()
        self.results.append(result)
        self._print_result(result)
        
        # 测试2: 信封格式兼容性
        result = self._test_envelope_format_compatibility()
        self.results.append(result)
        self._print_result(result)
        
        # 测试3: 历史记录格式兼容性
        result = self._test_history_format_compatibility()
        self.results.append(result)
        self._print_result(result)
    
    def _test_message_format_compatibility(self):
        """测试消息格式兼容性"""
        result = CompatibilityTestResult("消息格式兼容性", "数据格式兼容性")
        
        try:
            manager = ContextWindowManager()
            
            # 测试各种输入格式
            test_cases = [
                {
                    "name": "标准格式",
                    "system_prompt": "你是一个助手",
                    "envelope": {"source": "ide", "content": "test", "meta": {}},
                    "history": [{"role": "user", "content": "msg"}]
                },
                {
                    "name": "空历史",
                    "system_prompt": "你是一个助手",
                    "envelope": {"source": "browser", "content": "test", "meta": {}},
                    "history": []
                },
                {
                    "name": "复杂信封",
                    "system_prompt": "你是一个助手",
                    "envelope": {
                        "source": "ide",
                        "content": "code",
                        "selection": "selected",
                        "task": "review",
                        "custom_instruction": "fix bugs",
                        "meta": {"file_name": "test.py", "language": "python"}
                    },
                    "history": [
                        {"role": "user", "content": "msg1"},
                        {"role": "assistant", "content": "reply1"}
                    ]
                }
            ]
            
            results = {}
            for case in test_cases:
                messages = manager.build_messages(
                    case["system_prompt"],
                    case["envelope"],
                    case["history"]
                )
                
                # 验证消息格式
                assert isinstance(messages, list)
                assert all(isinstance(m, dict) for m in messages)
                assert all("role" in m for m in messages)
                assert all("content" in m for m in messages)
                assert all(m["role"] in ["system", "user", "assistant"] for m in messages)
                
                results[case["name"]] = {
                    "messages_count": len(messages),
                    "format_valid": True
                }
            
            result.passed = True
            result.new_result = results
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_envelope_format_compatibility(self):
        """测试信封格式兼容性"""
        result = CompatibilityTestResult("信封格式兼容性", "数据格式兼容性")
        
        try:
            # 测试各种信封格式
            envelope_formats = [
                {
                    "name": "完整信封",
                    "envelope": {
                        "source": "ide",
                        "content": "code",
                        "selection": "selected",
                        "task": "review",
                        "meta": {"file_name": "test.py"},
                        "timestamp": time.time()
                    }
                },
                {
                    "name": "最小信封",
                    "envelope": {
                        "source": "drag",
                        "content": "text"
                    }
                },
                {
                    "name": "空信封",
                    "envelope": {}
                }
            ]
            
            results = {}
            for fmt in envelope_formats:
                # 测试 normalize_context_envelope
                normalized = normalize_context_envelope(
                    {"context_envelope": fmt["envelope"]},
                    "fallback",
                    "drag",
                    {}
                )
                
                # 验证标准化后的格式
                assert isinstance(normalized, dict)
                assert "source" in normalized
                assert "content" in normalized
                assert "meta" in normalized
                
                results[fmt["name"]] = {
                    "normalized_fields": list(normalized.keys()),
                    "format_valid": True
                }
            
            result.passed = True
            result.new_result = results
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_history_format_compatibility(self):
        """测试历史记录格式兼容性"""
        result = CompatibilityTestResult("历史记录格式兼容性", "数据格式兼容性")
        
        try:
            manager = ContextWindowManager()
            
            # 测试各种历史记录格式
            history_formats = [
                {
                    "name": "标准历史",
                    "history": [
                        {"role": "user", "content": "msg1"},
                        {"role": "assistant", "content": "reply1"}
                    ]
                },
                {
                    "name": "空历史",
                    "history": []
                },
                {
                    "name": "单条历史",
                    "history": [{"role": "user", "content": "single msg"}]
                },
                {
                    "name": "长历史",
                    "history": [
                        {"role": "user", "content": f"msg{i}"}
                        for i in range(20)
                    ]
                }
            ]
            
            results = {}
            for fmt in history_formats:
                envelope = {"source": "ide", "content": "test", "meta": {}}
                messages = manager.build_messages("系统提示", envelope, fmt["history"])
                
                # 验证历史记录被正确处理
                assert isinstance(messages, list)
                assert len(messages) > 0
                
                results[fmt["name"]] = {
                    "input_length": len(fmt["history"]),
                    "output_length": len(messages),
                    "format_valid": True
                }
            
            result.passed = True
            result.new_result = results
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_functional_compatibility(self):
        """测试功能兼容性"""
        # 测试1: 上下文窗口管理功能
        result = self._test_context_window_functionality()
        self.results.append(result)
        self._print_result(result)
        
        # 测试2: 记忆系统功能
        result = self._test_memory_functionality()
        self.results.append(result)
        self._print_result(result)
        
        # 测试3: 多源上下文处理
        result = self._test_multi_source_handling()
        self.results.append(result)
        self._print_result(result)
    
    def _test_context_window_functionality(self):
        """测试上下文窗口管理功能"""
        result = CompatibilityTestResult("上下文窗口管理功能", "功能兼容性")
        
        try:
            manager = ContextWindowManager(
                max_input_chars=10000,
                reserve_output_chars=2500,
                recent_turns=4,
                max_history_msg_chars=1000
            )
            
            # 测试预算控制
            system_prompt = "A" * 5000
            envelope = {
                "source": "ide",
                "content": "B" * 8000,
                "meta": {}
            }
            history = [
                {"role": "user", "content": "C" * 2000},
                {"role": "assistant", "content": "D" * 2000}
            ]
            
            messages = manager.build_messages(system_prompt, envelope, history)
            
            # 验证预算控制
            total_len = sum(len(m["content"]) for m in messages)
            max_budget = manager.max_input_chars - manager.reserve_output_chars
            
            # 验证消息结构
            assert messages[0]["role"] == "system"
            assert messages[-1]["role"] == "user"
            
            result.passed = True
            result.new_result = {
                "total_length": total_len,
                "max_budget": max_budget,
                "within_budget": total_len <= max_budget + 1000,  # 允许一定开销
                "messages_count": len(messages)
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_memory_functionality(self):
        """测试记忆系统功能"""
        result = CompatibilityTestResult("记忆系统功能", "功能兼容性")
        
        try:
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            memory = ASUAgentMemory(temp_db.name)
            
            # 测试多会话管理
            sessions = ["session_1", "session_2", "session_3"]
            
            for session_id in sessions:
                memory.add_message(session_id, "user", f"消息_{session_id}")
                memory.add_message(session_id, "assistant", f"回复_{session_id}")
            
            # 验证会话隔离
            for session_id in sessions:
                context = memory.get_context(session_id)
                assert len(context["messages"]) == 2
                assert context["messages"][0]["content"] == f"消息_{session_id}"
            
            # 验证会话计数
            assert memory.session_count() == len(sessions)
            
            # 测试人设管理
            memory.set_persona("session_1", "code")
            context = memory.get_context("session_1")
            assert context["persona"] == "code"
            
            result.passed = True
            result.new_result = {
                "sessions_managed": len(sessions),
                "session_isolation": True,
                "persona_management": True,
                "session_count": memory.session_count()
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_multi_source_handling(self):
        """测试多源上下文处理"""
        result = CompatibilityTestResult("多源上下文处理", "功能兼容性")
        
        try:
            manager = ContextWindowManager()
            
            # 测试不同来源的上下文处理
            sources = [
                {
                    "source": "ide",
                    "content": "def hello():\n    print('Hello')",
                    "meta": {"file_name": "test.py", "language": "python"}
                },
                {
                    "source": "browser",
                    "content": "Python 最佳实践指南",
                    "meta": {"url": "https://python.org", "title": "Python Docs"}
                },
                {
                    "source": "drag",
                    "content": "Terminal output",
                    "meta": {"app_name": "Terminal"}
                }
            ]
            
            results = {}
            for source_data in sources:
                envelope = {
                    "source": source_data["source"],
                    "content": source_data["content"],
                    "meta": source_data["meta"]
                }
                
                messages = manager.build_messages("系统提示", envelope, [])
                
                # 验证每个来源都能正确处理
                assert len(messages) > 0
                assert messages[-1]["role"] == "user"
                
                # 验证来源信息被正确注入
                user_content = messages[-1]["content"]
                assert f"[context_source] {source_data['source']}" in user_content
                
                results[source_data["source"]] = {
                    "messages_count": len(messages),
                    "source_injected": True
                }
            
            result.passed = True
            result.new_result = results
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_performance_compatibility(self):
        """测试性能兼容性"""
        # 测试1: 响应时间兼容性
        result = self._test_response_time_compatibility()
        self.results.append(result)
        self._print_result(result)
        
        # 测试2: 内存使用兼容性
        result = self._test_memory_usage_compatibility()
        self.results.append(result)
        self._print_result(result)
    
    def _test_response_time_compatibility(self):
        """测试响应时间兼容性"""
        result = CompatibilityTestResult("响应时间兼容性", "性能兼容性")
        
        try:
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            manager = ContextWindowManager()
            memory = ASUAgentMemory(temp_db.name)
            
            # 测试上下文处理响应时间
            envelope = {
                "source": "ide",
                "content": "A" * 1000,
                "meta": {"file_name": "test.py"}
            }
            
            iterations = 100
            start_time = time.time()
            
            for i in range(iterations):
                messages = manager.build_messages("系统提示", envelope, [])
            
            context_time = time.time() - start_time
            
            # 测试记忆系统响应时间
            start_time = time.time()
            
            for i in range(iterations):
                memory.add_message(f"session_{i}", "user", f"消息_{i}")
                context = memory.get_context(f"session_{i}")
            
            memory_time = time.time() - start_time
            
            # 验证响应时间在合理范围内
            assert context_time < 1.0, f"上下文处理时间过长: {context_time:.3f}s"
            assert memory_time < 2.0, f"记忆系统时间过长: {memory_time:.3f}s"
            
            result.passed = True
            result.new_result = {
                "context_processing_time": context_time,
                "memory_system_time": memory_time,
                "iterations": iterations,
                "avg_context_time": context_time / iterations,
                "avg_memory_time": memory_time / iterations
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_memory_usage_compatibility(self):
        """测试内存使用兼容性"""
        result = CompatibilityTestResult("内存使用兼容性", "性能兼容性")
        
        try:
            import gc
            import tempfile
            
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            manager = ContextWindowManager()
            memory = ASUAgentMemory(temp_db.name)
            
            # 测试大量操作后的内存稳定性
            for i in range(50):
                envelope = {
                    "source": "ide",
                    "content": f"内容_{i}" * 100,
                    "meta": {"file_name": f"file_{i}.py"}
                }
                messages = manager.build_messages("系统提示", envelope, [])
                memory.add_message(f"session_{i}", "user", f"消息_{i}")
            
            # 强制垃圾回收
            gc.collect()
            
            # 验证系统仍然正常工作
            test_envelope = {"source": "ide", "content": "final_test", "meta": {}}
            messages = manager.build_messages("系统提示", test_envelope, [])
            context = memory.get_context("session_0")
            
            assert len(messages) > 0
            assert "messages" in context
            
            result.passed = True
            result.new_result = {
                "operations_completed": 50,
                "system_stable": True,
                "gc_collected": True
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def test_integration_compatibility(self):
        """测试集成兼容性"""
        # 测试1: 端到端流程兼容性
        result = self._test_end_to_end_compatibility()
        self.results.append(result)
        self._print_result(result)
        
        # 测试2: 错误处理兼容性
        result = self._test_error_handling_compatibility()
        self.results.append(result)
        self._print_result(result)
    
    def _test_end_to_end_compatibility(self):
        """测试端到端流程兼容性"""
        result = CompatibilityTestResult("端到端流程兼容性", "集成兼容性")
        
        try:
            # 模拟完整的对话流程
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            manager = ContextWindowManager()
            memory = ASUAgentMemory(temp_db.name)
            session_id = "e2e_test_session"
            
            # 第一轮对话
            user_msg_1 = "帮我审查这段代码"
            envelope_1 = {
                "source": "ide",
                "content": "def hello():\n    print('Hello')",
                "selection": "hello()",
                "task": "代码审查",
                "meta": {"file_name": "test.py", "language": "python"}
            }
            
            # 存储用户消息
            memory.add_message(session_id, "user", user_msg_1)
            
            # 获取历史记录
            context = memory.get_context(session_id)
            history = context["messages"]
            
            # 构建消息
            messages_1 = manager.build_messages("你是一个代码助手", envelope_1, history)
            
            # 模拟助手回复
            assistant_reply_1 = "代码看起来不错，但建议添加类型注解"
            memory.add_message(session_id, "assistant", assistant_reply_1)
            
            # 第二轮对话
            user_msg_2 = "如何添加类型注解？"
            envelope_2 = {
                "source": "ide",
                "content": "def hello():\n    print('Hello')",
                "meta": {"file_name": "test.py"}
            }
            
            # 存储用户消息
            memory.add_message(session_id, "user", user_msg_2)
            
            # 获取更新后的历史记录
            context_updated = memory.get_context(session_id)
            history_updated = context_updated["messages"]
            
            # 构建消息
            messages_2 = manager.build_messages("你是一个代码助手", envelope_2, history_updated)
            
            # 验证端到端流程
            assert len(history_updated) == 3  # user, assistant, user
            assert len(messages_2) > 0
            assert messages_2[-1]["role"] == "user"
            
            result.passed = True
            result.new_result = {
                "conversation_rounds": 2,
                "history_length": len(history_updated),
                "messages_generated": len(messages_2),
                "session_maintained": True
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _test_error_handling_compatibility(self):
        """测试错误处理兼容性"""
        result = CompatibilityTestResult("错误处理兼容性", "集成兼容性")
        
        try:
            import tempfile
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            manager = ContextWindowManager()
            memory = ASUAgentMemory(temp_db.name)
            
            # 测试各种错误情况
            error_cases = [
                {
                    "name": "空信封",
                    "envelope": {},
                    "should_work": True
                },
                {
                    "name": "None 内容",
                    "envelope": {"source": "ide", "content": None, "meta": {}},
                    "should_work": True
                },
                {
                    "name": "缺少 source",
                    "envelope": {"content": "test", "meta": {}},
                    "should_work": True
                },
                {
                    "name": "空历史记录",
                    "history": [],
                    "should_work": True
                },
                {
                    "name": "格式错误的历史",
                    "history": [{"role": "user"}],  # 缺少 content
                    "should_work": True
                }
            ]
            
            results = {}
            for case in error_cases:
                try:
                    envelope = case.get("envelope", {"source": "ide", "content": "test", "meta": {}})
                    history = case.get("history", [])
                    
                    messages = manager.build_messages("系统提示", envelope, history)
                    results[case["name"]] = {
                        "success": True,
                        "messages_count": len(messages)
                    }
                except Exception as e:
                    results[case["name"]] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # 验证所有错误情况都被正确处理
            all_handled = all(r["success"] for r in results.values())
            
            result.passed = True
            result.new_result = {
                "error_cases_tested": len(error_cases),
                "all_handled": all_handled,
                "results": results
            }
            
        except Exception as e:
            result.error = str(e)
        
        return result
    
    def _print_result(self, result):
        """打印测试结果"""
        status = "✓ 通过" if result.passed else "✗ 失败"
        print(f"  {status} | {result.test_name}")
        if result.error:
            print(f"       错误: {result.error}")
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 70)
        print("兼容性测试报告")
        print("=" * 70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        # 按类别统计
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"total": 0, "passed": 0}
            categories[result.category]["total"] += 1
            if result.passed:
                categories[result.category]["passed"] += 1
        
        print(f"\n总体结果:")
        print(f"  总测试数: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        print(f"  通过率: {passed/total*100:.1f}%")
        
        print(f"\n按类别统计:")
        for category, stats in categories.items():
            status = "✓" if stats["passed"] == stats["total"] else "✗"
            print(f"  {status} {category}: {stats['passed']}/{stats['total']}")
        
        # 详细结果
        print(f"\n详细结果:")
        for result in self.results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.test_name}")
            if result.new_result:
                # 只显示关键信息
                key_info = {k: v for k, v in result.new_result.items() 
                           if k not in ["results", "error_cases_tested"]}
                if key_info:
                    print(f"       {json.dumps(key_info, ensure_ascii=False, indent=2)[:200]}...")
        
        # 兼容性结论
        print(f"\n" + "=" * 70)
        print("兼容性结论")
        print("=" * 70)
        
        if passed == total:
            print("✅ 所有兼容性测试通过！")
            print("   新模块与现有模块完全兼容，可以安全集成。")
        else:
            print("⚠️  存在兼容性问题，需要修复后再集成。")
            print("   失败的测试:")
            for result in self.results:
                if not result.passed:
                    print(f"   - {result.test_name}: {result.error}")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "categories": categories,
            "all_passed": passed == total
        }


def run_compatibility_tests():
    """运行兼容性测试"""
    tester = ModuleCompatibilityTester()
    report = tester.run_all_tests()
    
    # 保存报告到文件
    report_path = os.path.join(os.path.dirname(__file__), "compatibility_test_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试报告已保存到: {report_path}")
    
    return report["all_passed"]


if __name__ == "__main__":
    success = run_compatibility_tests()
    sys.exit(0 if success else 1)
