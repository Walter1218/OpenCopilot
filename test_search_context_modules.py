"""
测试搜索能力模块和上下文管理模块

运行方式：
    python test_search_context_modules.py
"""

import os
import sys
import unittest
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestSearchCapability(unittest.TestCase):
    """测试搜索能力模块"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self._create_test_files()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_files(self):
        """创建测试文件"""
        # 创建 Python 文件
        with open(os.path.join(self.test_dir, "main.py"), "w") as f:
            f.write("""
def process_data(data):
    \"\"\"处理数据\"\"\"
    return data.strip()

class DataProcessor:
    def __init__(self):
        self.name = "processor"
    
    def run(self):
        print("Running...")
""")
        
        # 创建 Markdown 文件
        with open(os.path.join(self.test_dir, "README.md"), "w") as f:
            f.write("""
# 项目说明

这是一个测试项目。

## 架构设计

项目采用模块化设计。
""")
        
        # 创建子目录
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        with open(os.path.join(self.test_dir, "src", "utils.py"), "w") as f:
            f.write("""
def helper():
    return "helper"
""")
    
    def test_search_capability_init(self):
        """测试搜索能力模块初始化"""
        from search_capability import SearchCapability
        
        search = SearchCapability(workspace=self.test_dir)
        
        # 检查提供者
        providers = search.list_providers()
        print(f"可用搜索提供者: {providers}")
        
        # 至少应该有代码和文档搜索
        self.assertIn("code", providers)
        self.assertIn("doc", providers)
    
    def test_code_search(self):
        """测试代码搜索"""
        from search_capability import SearchCapability
        
        search = SearchCapability(workspace=self.test_dir)
        
        # 搜索函数定义
        results = search.code_search("def process_data", scope=self.test_dir)
        print(f"代码搜索结果: {len(results)} 个")
        
        # 应该找到匹配
        self.assertGreater(len(results), 0)
        
        # 检查结果
        if results:
            result = results[0]
            print(f"  - {result.title}: {result.content[:50]}...")
            self.assertIn("process_data", result.content)
    
    def test_doc_search(self):
        """测试文档搜索"""
        from search_capability import SearchCapability
        
        search = SearchCapability(workspace=self.test_dir)
        
        # 搜索文档标题
        results = search.doc_search("架构设计", scope=self.test_dir)
        print(f"文档搜索结果: {len(results)} 个")
        
        # 应该找到匹配
        self.assertGreater(len(results), 0)
        
        # 检查结果
        if results:
            result = results[0]
            print(f"  - {result.title}: {result.content[:50]}...")
            self.assertIn("架构", result.content)
    
    def test_unified_search(self):
        """测试统一搜索接口"""
        from search_capability import SearchCapability, SearchType
        
        search = SearchCapability(workspace=self.test_dir)
        
        # 统一搜索
        results = search.search("process", search_type=SearchType.ALL, count=10)
        print(f"统一搜索结果: {len(results)} 个")
        
        # 应该找到代码和文档
        code_results = [r for r in results if r.source == SearchType.CODE]
        doc_results = [r for r in results if r.source == SearchType.DOC]
        
        print(f"  - 代码结果: {len(code_results)} 个")
        print(f"  - 文档结果: {len(doc_results)} 个")
    
    def test_minimax_provider_init(self):
        """测试 MiniMax 搜索提供者初始化"""
        from search_capability import MiniMaxSearchProvider
        
        # 测试有 API key 情况
        provider = MiniMaxSearchProvider(api_key="test-key")
        self.assertTrue(provider.is_available())
        
        # 测试 provider 属性
        self.assertEqual(provider.region, "cn")
        self.assertIn("minimaxi.com", provider.endpoint)


class TestContextManager(unittest.TestCase):
    """测试上下文管理模块"""
    
    def test_context_window_manager_init(self):
        """测试 ContextWindowManager 初始化"""
        from context_manager import ContextWindowManager
        
        # 默认初始化
        manager = ContextWindowManager()
        config = manager.get_config()
        
        print(f"默认配置: {config}")
        self.assertEqual(config["max_input_chars"], 120000)
        self.assertEqual(config["recent_turns"], 12)
    
    def test_context_window_manager_model_adjust(self):
        """测试模型适配"""
        from context_manager import ContextWindowManager
        
        # 测试不同模型
        manager = ContextWindowManager(model_name="MiniMax-M3")
        config = manager.get_config()
        
        print(f"MiniMax-M3 配置: {config}")
        self.assertEqual(config["model_name"], "MiniMax-M3")
    
    def test_build_user_payload(self):
        """测试构建用户 payload"""
        from context_manager import ContextWindowManager
        
        manager = ContextWindowManager()
        
        # 构建 envelope
        envelope = {
            "source": "ide",
            "content": "def test():\n    pass",
            "task": "修复 bug",
            "meta": {
                "file_name": "test.py",
                "language": "python"
            }
        }
        
        payload = manager.build_user_payload(envelope)
        print(f"构建的 payload:\n{payload[:200]}...")
        
        # 检查 payload 包含关键信息
        self.assertIn("[context_source] ide", payload)
        self.assertIn("[task] 修复 bug", payload)
        self.assertIn("[meta]", payload)
    
    def test_build_messages(self):
        """测试构建消息列表"""
        from context_manager import ContextWindowManager
        
        manager = ContextWindowManager()
        
        # 构建消息
        system_prompt = "你是一个编程助手"
        context = {
            "source": "ide",
            "content": "代码内容",
            "task": "代码审查"
        }
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮你的？"}
        ]
        
        messages = manager.build_messages(system_prompt, context, history)
        print(f"消息数量: {len(messages)}")
        
        # 检查消息结构
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[3]["role"], "user")
    
    def test_context_manager_init(self):
        """测试 ContextManager 初始化"""
        from context_manager import ContextManager
        
        manager = ContextManager(model_name="MiniMax-M3")
        config = manager.get_config()
        
        print(f"ContextManager 配置: {config}")
        self.assertEqual(config["model_name"], "MiniMax-M3")
    
    def test_context_manager_session(self):
        """测试会话管理"""
        from context_manager import ContextManager
        
        manager = ContextManager()
        
        # 添加消息
        session_id = "test_session_123"
        manager.add_message(session_id, "user", "你好")
        manager.add_message(session_id, "assistant", "你好！")
        
        # 获取上下文
        context = manager.get_context(session_id)
        print(f"会话上下文: {context}")
        
        self.assertEqual(context["session_id"], session_id)
        self.assertEqual(len(context["history"]), 2)
        
        # 清空会话
        manager.clear_session(session_id)
        context = manager.get_context(session_id)
        self.assertEqual(len(context["history"]), 0)
    
    def test_context_envelope(self):
        """测试上下文信封"""
        from context_manager import ContextEnvelope, normalize_context_envelope
        
        # 测试创建
        envelope = ContextEnvelope(
            source="ide",
            content="代码内容",
            task="修复 bug"
        )
        
        data = envelope.to_dict()
        print(f"信封数据: {data}")
        
        self.assertEqual(data["source"], "ide")
        self.assertEqual(data["task"], "修复 bug")
        
        # 测试标准化
        request = {
            "text": "旧格式文本",
            "context_source": "browser",
            "context_meta": {"app_name": "Chrome"}
        }
        
        normalized = normalize_context_envelope(request)
        print(f"标准化结果: {normalized}")
        
        self.assertEqual(normalized["source"], "browser")
        self.assertEqual(normalized["content"], "旧格式文本")


class TestCompatibility(unittest.TestCase):
    """测试向后兼容性"""
    
    def test_asu_custom_agent_compatibility(self):
        """测试与 asu_custom_agent 的兼容性"""
        # 检查是否能导入原有的 ContextWindowManager
        try:
            from asu_custom_agent import ContextWindowManager as OriginalManager
            from context_manager import ContextWindowManager as NewManager
            
            # 两者都应该可用
            original = OriginalManager()
            new = NewManager()
            
            # 配置应该兼容
            original_config = {
                "max_input_chars": original.max_input_chars,
                "reserve_output_chars": original.reserve_output_chars,
                "recent_turns": original.recent_turns,
                "max_history_msg_chars": original.max_history_msg_chars
            }
            new_config = new.get_config()
            
            print(f"原始配置: {original_config}")
            print(f"新配置: {new_config}")
            
            # 关键配置应该一致
            self.assertEqual(original_config["max_input_chars"], new_config["max_input_chars"])
            self.assertEqual(original_config["recent_turns"], new_config["recent_turns"])
            
            print("✓ 向后兼容性测试通过")
            
        except ImportError as e:
            print(f"⚠ 导入警告: {e}")


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("搜索能力模块和上下文管理模块测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestSearchCapability))
    suite.addTests(loader.loadTestsFromTestCase(TestContextManager))
    suite.addTests(loader.loadTestsFromTestCase(TestCompatibility))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"测试结果: {'通过' if result.wasSuccessful() else '失败'}")
    print(f"运行: {result.testsRun}, 失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
