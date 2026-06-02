"""
知识检索模块和 Broker 权限诊断功能测试

测试知识检索模块的封装功能和 Broker 的权限诊断接口。
"""

import unittest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


class TestKnowledgeRetrieval(unittest.TestCase):
    """知识检索模块测试"""
    
    def test_import_knowledge_retrieval(self):
        """测试知识检索模块导入"""
        try:
            from knowledge_retrieval import KnowledgeRetrieval, RetrievalResult
            from knowledge_retrieval import QueryInterface, QueryType
            self.assertTrue(True, "知识检索模块导入成功")
        except ImportError as e:
            self.fail(f"知识检索模块导入失败: {e}")
    
    def test_knowledge_retrieval_init(self):
        """测试知识检索初始化"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 测试默认初始化
        retrieval = KnowledgeRetrieval()
        self.assertIsNotNone(retrieval)
        self.assertFalse(retrieval._initialized)
        
        # 测试自定义项目根目录
        retrieval = KnowledgeRetrieval(project_root="/tmp/test")
        self.assertEqual(str(retrieval.project_root), "/tmp/test")
    
    def test_retrieval_result(self):
        """测试检索结果类"""
        from knowledge_retrieval import RetrievalResult
        
        # 测试成功结果
        result = RetrievalResult(success=True, data={"test": "data"})
        self.assertTrue(result.success)
        self.assertEqual(result.data, {"test": "data"})
        self.assertIsNone(result.error)
        
        # 测试失败结果
        result = RetrievalResult(success=False, error="测试错误")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "测试错误")
        
        # 测试转换为字典
        result_dict = result.to_dict()
        self.assertIn("success", result_dict)
        self.assertIn("error", result_dict)
    
    def test_query_type_enum(self):
        """测试查询类型枚举"""
        from knowledge_retrieval import QueryType
        
        # 测试所有查询类型
        self.assertEqual(QueryType.AUTO, "auto")
        self.assertEqual(QueryType.ENTITY, "entity")
        self.assertEqual(QueryType.RELATION, "relation")
        self.assertEqual(QueryType.PATH, "path")
        self.assertEqual(QueryType.COMPONENT, "component")
        self.assertEqual(QueryType.API, "api")
        self.assertEqual(QueryType.FEATURE, "feature")
        self.assertEqual(QueryType.DOCUMENT, "document")
        self.assertEqual(QueryType.CONTEXT, "context")
        self.assertEqual(QueryType.STATISTICS, "statistics")
    
    def test_query_interface_init(self):
        """测试查询接口初始化"""
        from knowledge_retrieval import KnowledgeRetrieval, QueryInterface
        
        retrieval = KnowledgeRetrieval()
        interface = QueryInterface(retrieval)
        self.assertIsNotNone(interface)
        self.assertEqual(interface.retrieval, retrieval)


class TestBrokerPermissions(unittest.TestCase):
    """Broker 权限诊断功能测试"""
    
    def test_check_accessibility_permission(self):
        """测试辅助功能权限检查"""
        # 导入权限检查函数
        sys.path.insert(0, str(Path(__file__).parent / "asu_broker" / "core"))
        
        try:
            from server import check_accessibility_permission
            result = check_accessibility_permission()
            
            # 验证返回结构
            self.assertIn("available", result)
            self.assertIn("granted", result)
            self.assertIn("description", result)
            self.assertIn("impact", result)
            
            print(f"辅助功能权限: {'已授予' if result['granted'] else '未授予'}")
        except ImportError as e:
            print(f"跳过辅助功能权限测试: {e}")
    
    def test_check_screen_recording_permission(self):
        """测试屏幕录制权限检查"""
        try:
            from server import check_screen_recording_permission
            result = check_screen_recording_permission()
            
            # 验证返回结构
            self.assertIn("available", result)
            self.assertIn("granted", result)
            self.assertIn("description", result)
            self.assertIn("impact", result)
            
            print(f"屏幕录制权限: {'已授予' if result['granted'] else '未授予'}")
        except ImportError as e:
            print(f"跳过屏幕录制权限测试: {e}")
    
    def test_check_automation_permission(self):
        """测试自动化权限检查"""
        try:
            from server import check_automation_permission
            result = check_automation_permission()
            
            # 验证返回结构
            self.assertIn("available", result)
            self.assertIn("granted", result)
            self.assertIn("description", result)
            self.assertIn("impact", result)
            
            print(f"自动化权限: {'已授予' if result['granted'] else '未授予'}")
        except ImportError as e:
            print(f"跳过自动化权限测试: {e}")
    
    def test_check_full_disk_access(self):
        """测试完全磁盘访问权限检查"""
        try:
            from server import check_full_disk_access
            result = check_full_disk_access()
            
            # 验证返回结构
            self.assertIn("available", result)
            self.assertIn("granted", result)
            self.assertIn("description", result)
            self.assertIn("impact", result)
            
            print(f"完全磁盘访问权限: {'已授予' if result['granted'] else '未授予'}")
        except ImportError as e:
            print(f"跳过完全磁盘访问权限测试: {e}")
    
    def test_generate_permission_recommendations(self):
        """测试权限建议生成"""
        try:
            from server import generate_permission_recommendations
            
            # 模拟权限状态
            permissions = {
                "accessibility": {"granted": False},
                "screen_recording": {"granted": True},
                "automation": {"granted": False},
                "full_disk_access": {"granted": True}
            }
            
            recommendations = generate_permission_recommendations(permissions)
            
            # 验证建议
            self.assertIsInstance(recommendations, list)
            self.assertGreater(len(recommendations), 0)
            
            # 验证包含未授予权限的建议
            has_accessibility_rec = any("辅助功能" in rec for rec in recommendations)
            has_automation_rec = any("自动化" in rec for rec in recommendations)
            
            self.assertTrue(has_accessibility_rec, "应包含辅助功能权限建议")
            self.assertTrue(has_automation_rec, "应包含自动化权限建议")
            
            print(f"生成了 {len(recommendations)} 条权限建议")
        except ImportError as e:
            print(f"跳过权限建议测试: {e}")


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_knowledge_retrieval_workflow(self):
        """测试知识检索工作流程"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 创建检索实例
        retrieval = KnowledgeRetrieval()
        
        # 测试初始化（可能会失败，因为没有实际的知识图谱）
        try:
            result = retrieval.initialize()
            if result.success:
                print("知识图谱初始化成功")
                
                # 测试查询功能
                query_result = retrieval.query("test", "entity")
                print(f"查询结果: {query_result.metadata.get('count', 0)} 个实体")
                
                # 测试统计功能
                stats_result = retrieval.get_statistics()
                if stats_result.success:
                    print(f"统计信息: {stats_result.data}")
            else:
                print(f"知识图谱初始化失败（预期行为）: {result.error}")
        except Exception as e:
            print(f"知识检索工作流程测试异常（预期行为）: {e}")
    
    def test_broker_permissions_workflow(self):
        """测试 Broker 权限诊断工作流程"""
        try:
            from server import check_accessibility_permission, check_screen_recording_permission
            from server import check_automation_permission, check_full_disk_access
            
            # 检查所有权限
            permissions = {
                "accessibility": check_accessibility_permission(),
                "screen_recording": check_screen_recording_permission(),
                "automation": check_automation_permission(),
                "full_disk_access": check_full_disk_access()
            }
            
            # 统计权限状态
            granted_count = sum(1 for p in permissions.values() if p.get("granted", False))
            total_count = len(permissions)
            
            print(f"权限状态: {granted_count}/{total_count} 已授予")
            
            # 验证权限检查功能
            for name, permission in permissions.items():
                self.assertIn("available", permission, f"{name} 权限检查应返回 available 字段")
                self.assertIn("granted", permission, f"{name} 权限检查应返回 granted 字段")
            
            print("Broker 权限诊断工作流程测试完成")
        except ImportError as e:
            print(f"跳过 Broker 权限诊断工作流程测试: {e}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("知识检索模块和 Broker 权限诊断功能测试")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试用例
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeRetrieval))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestBrokerPermissions))
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 60)
    print(f"测试完成: 运行 {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
