#!/usr/bin/env python3
"""
知识图谱API覆盖率测试脚本

使用真实数据测试所有API端点，验证功能正确性和质量。
"""

import requests
import json
import time
import sys
from pathlib import Path


class KnowledgeGraphAPITester:
    """知识图谱API测试器"""
    
    def __init__(self, base_url="http://localhost:8090"):
        self.base_url = base_url
        self.test_results = []
        self.created_entity_id = None
        self.created_relation_id = None
    
    def test_endpoint(self, method, endpoint, description, params=None, data=None, expected_status=200):
        """测试单个API端点"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            success = response.status_code == expected_status
            result = {
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
            
            if success:
                print(f"  ✓ [{method}] {endpoint} - {description}")
            else:
                print(f"  ✗ [{method}] {endpoint} - {description} (期望状态码: {expected_status}, 实际: {response.status_code})")
            
            self.test_results.append(result)
            return result
            
        except requests.exceptions.ConnectionError:
            print(f"  ✗ [{method}] {endpoint} - 连接失败")
            self.test_results.append({
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "success": False,
                "error": "连接失败"
            })
            return None
        except Exception as e:
            print(f"  ✗ [{method}] {endpoint} - 错误: {str(e)}")
            self.test_results.append({
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "success": False,
                "error": str(e)
            })
            return None
    
    def test_health_check(self):
        """测试健康检查"""
        print("\n1. 测试健康检查")
        print("-" * 40)
        
        self.test_endpoint("GET", "/health", "健康检查")
        self.test_endpoint("GET", "/", "根路径信息")
    
    def test_statistics(self):
        """测试统计信息"""
        print("\n2. 测试统计信息")
        print("-" * 40)
        
        self.test_endpoint("GET", "/graph/statistics", "获取统计信息")
        self.test_endpoint("GET", "/graph/statistics-by-type", "按类型获取统计信息")
    
    def test_entity_operations(self):
        """测试实体操作"""
        print("\n3. 测试实体操作")
        print("-" * 40)
        
        # 搜索实体
        self.test_endpoint("GET", "/entity/search", "搜索实体", params={"query": "Agent"})
        
        # 按类型搜索
        self.test_endpoint("GET", "/entity/search", "按类型搜索实体", params={"query": "Agent", "entity_type": "component"})
        
        # 获取实体详情（先搜索一个实体）
        result = self.test_endpoint("GET", "/entity/search", "搜索实体获取ID", params={"query": "Agent"})
        if result and result.get("success") and result["response"].get("entities"):
            entity_id = result["response"]["entities"][0]["id"]
            self.test_endpoint("GET", f"/entity/{entity_id}", "获取实体详情")
            self.test_endpoint("GET", f"/entity/{entity_id}/context", "获取实体上下文")
            self.test_endpoint("GET", f"/entity/{entity_id}/report", "获取实体报告")
            self.test_endpoint("GET", f"/entity/{entity_id}/related", "获取相关实体")
        
        # 按名称获取实体（先搜索一个存在的实体名称）
        result = self.test_endpoint("GET", "/entity/search", "搜索实体获取名称", params={"query": "Agent"})
        if result and result.get("success") and result["response"].get("entities"):
            entity_name = result["response"]["entities"][0]["name"]
            self.test_endpoint("GET", f"/entity/by-name/{entity_name}", "按名称获取实体")
        
        # 按属性获取实体
        self.test_endpoint("GET", "/entity/by-property", "按属性获取实体", params={"property_name": "entity_type", "property_value": "component"})
        
        # 添加实体
        new_entity = {
            "name": "TestComponent",
            "entity_type": "component",
            "description": "测试组件",
            "properties": {"test": True},
            "source_documents": ["test.md"]
        }
        result = self.test_endpoint("POST", "/entity", "添加实体", data=new_entity)
        if result and result.get("success"):
            self.created_entity_id = result["response"].get("entity_id")
            
            # 更新实体
            if self.created_entity_id:
                self.test_endpoint("PUT", f"/entity/{self.created_entity_id}", "更新实体", 
                                 data={"description": "更新后的测试组件"})
    
    def test_relation_operations(self):
        """测试关系操作"""
        print("\n4. 测试关系操作")
        print("-" * 40)
        
        # 搜索关系
        self.test_endpoint("GET", "/relation/search", "搜索所有关系")
        
        # 按类型搜索关系
        self.test_endpoint("GET", "/relation/search", "按类型搜索关系", params={"relation_type": "depends_on"})
        
        # 添加关系（如果有创建的实体）
        if self.created_entity_id:
            # 先获取另一个实体
            result = self.test_endpoint("GET", "/entity/search", "搜索实体获取目标ID", params={"query": "Agent"})
            if result and result.get("success") and result["response"].get("entities"):
                target_id = result["response"]["entities"][0]["id"]
                new_relation = {
                    "source_id": self.created_entity_id,
                    "target_id": target_id,
                    "relation_type": "depends_on",
                    "description": "测试关系",
                    "weight": 1.0
                }
                result = self.test_endpoint("POST", "/relation", "添加关系", data=new_relation)
                if result and result.get("success"):
                    self.created_relation_id = result["response"].get("relation_id")
    
    def test_query_operations(self):
        """测试查询操作"""
        print("\n5. 测试查询操作")
        print("-" * 40)
        
        # 查询路径
        self.test_endpoint("GET", "/query/path", "查询实体路径", 
                          params={"source_id": "entity_1", "target_id": "entity_2"})
        
        # 查询组件
        self.test_endpoint("GET", "/query/components", "查询所有组件")
        self.test_endpoint("GET", "/query/components", "按功能查询组件", params={"feature": "Agent"})
        
        # 查询API
        self.test_endpoint("GET", "/query/apis", "查询所有API")
        self.test_endpoint("GET", "/query/apis", "按组件查询API", params={"component": "Agent"})
        
        # 查询功能
        self.test_endpoint("GET", "/query/features", "查询所有功能")
        
        # 查询文档
        self.test_endpoint("GET", "/query/documents", "查询所有文档")
        
        # 查询关键组件
        self.test_endpoint("GET", "/query/critical", "查询关键组件")
        
        # 查询孤立实体
        self.test_endpoint("GET", "/query/isolated", "查询孤立实体")
        
        # 按文档查询实体
        self.test_endpoint("GET", "/query/entities-by-document", "按文档查询实体", 
                          params={"doc_path": "README.md"})
    
    def test_export_operations(self):
        """测试导出操作"""
        print("\n6. 测试导出操作")
        print("-" * 40)
        
        self.test_endpoint("GET", "/export/json", "导出JSON")
        self.test_endpoint("GET", "/export/report", "生成报告")
        self.test_endpoint("GET", "/export/csv", "导出CSV")
    
    def test_error_handling(self):
        """测试错误处理"""
        print("\n7. 测试错误处理")
        print("-" * 40)
        
        # 测试不存在的实体
        self.test_endpoint("GET", "/entity/nonexistent_entity", "获取不存在的实体", expected_status=404)
        
        # 测试无效的实体类型
        self.test_endpoint("GET", "/entity/search", "无效的实体类型", 
                          params={"query": "test", "entity_type": "invalid_type"}, expected_status=400)
        
        # 测试缺少必填字段
        self.test_endpoint("POST", "/entity", "缺少必填字段", data={"name": "test"}, expected_status=400)
    
    def cleanup(self):
        """清理测试数据"""
        print("\n8. 清理测试数据")
        print("-" * 40)
        
        if self.created_entity_id:
            self.test_endpoint("DELETE", f"/entity/{self.created_entity_id}", "删除测试实体")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("知识图谱API覆盖率测试")
        print("=" * 80)
        
        start_time = time.time()
        
        # 运行所有测试
        self.test_health_check()
        self.test_statistics()
        self.test_entity_operations()
        self.test_relation_operations()
        self.test_query_operations()
        self.test_export_operations()
        self.test_error_handling()
        self.cleanup()
        
        end_time = time.time()
        
        # 统计结果
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success"))
        failed_tests = total_tests - successful_tests
        
        print("\n" + "=" * 80)
        print("测试结果统计")
        print("=" * 80)
        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {(successful_tests/total_tests)*100:.1f}%")
        print(f"测试时间: {end_time - start_time:.2f}秒")
        
        # 显示失败测试详情
        if failed_tests > 0:
            print("\n失败测试详情:")
            print("-" * 40)
            for result in self.test_results:
                if not result.get("success"):
                    print(f"  [{result['method']}] {result['endpoint']} - {result.get('description', '无描述')}")
                    if "error" in result:
                        print(f"    错误: {result['error']}")
                    elif "status_code" in result:
                        print(f"    期望状态码: {result['expected_status']}, 实际: {result['status_code']}")
        
        # 保存测试结果
        self.save_results()
        
        return failed_tests == 0
    
    def save_results(self):
        """保存测试结果"""
        results_file = Path("/Users/onetwo/Documents/trae_projects/OpenCopilot/knowledge_graph/test_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_tests": len(self.test_results),
                "successful_tests": sum(1 for r in self.test_results if r.get("success")),
                "failed_tests": sum(1 for r in self.test_results if not r.get("success")),
                "results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n测试结果已保存到: {results_file}")


def main():
    """主函数"""
    # 检查API服务器是否运行
    try:
        response = requests.get("http://localhost:8090/health", timeout=5)
        if response.status_code != 200:
            print("错误: API服务器未运行或状态异常")
            print("请先启动API服务器: python start_knowledge_graph_api.py --port 8090")
            return False
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到API服务器")
        print("请先启动API服务器: python start_knowledge_graph_api.py --port 8090")
        return False
    
    # 运行测试
    tester = KnowledgeGraphAPITester()
    return tester.run_all_tests()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)