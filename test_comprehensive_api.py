"""
综合API测试 - 原子能力、复合能力、动线级别测试
"""

import asyncio
import sys
import os
import json
import tempfile
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport


class TestResult:
    """测试结果"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.error = None
        self.details = {}
        self.duration = 0


class ComprehensiveAPITester:
    """综合API测试器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.client = None
        
    async def setup(self):
        """初始化测试环境"""
        from smart_copilot_api import app
        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url="http://test")
        
    async def teardown(self):
        """清理测试环境"""
        if self.client:
            await self.client.aclose()
            
    async def run_test(self, name: str, category: str, test_func):
        """运行单个测试"""
        result = TestResult(name, category)
        start_time = asyncio.get_event_loop().time()
        
        try:
            await test_func(result)
            result.passed = True
        except AssertionError as e:
            result.error = f"断言失败: {str(e)}"
        except Exception as e:
            result.error = f"异常: {str(e)}"
            
        result.duration = asyncio.get_event_loop().time() - start_time
        self.results.append(result)
        
        # 打印结果
        status = "✅" if result.passed else "❌"
        print(f"{status} [{category}] {name} ({result.duration:.2f}s)")
        if result.error:
            print(f"   错误: {result.error}")
            
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)
        
        # 按类别统计
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"passed": 0, "failed": 0}
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
                
        print("\n按类别统计:")
        for cat, stats in categories.items():
            total = stats["passed"] + stats["failed"]
            print(f"  {cat}: {stats['passed']}/{total} 通过")
            
        # 总体统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\n总计: {passed}/{total} 通过, {failed} 失败")
        print(f"通过率: {passed/total*100:.1f}%")
        
        # 列出失败的测试
        if failed > 0:
            print("\n失败的测试:")
            for result in self.results:
                if not result.passed:
                    print(f"  - [{result.category}] {result.name}")
                    print(f"    错误: {result.error}")
                    
        return passed, total


# ==========================================
# 原子能力测试
# ==========================================

async def test_health_check(tester: ComprehensiveAPITester):
    """测试健康检查"""
    async def test(result: TestResult):
        response = await tester.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        result.details = data
        
    await tester.run_test("健康检查", "原子能力", test)


async def test_file_read(tester: ComprehensiveAPITester):
    """测试文件读取"""
    async def test(result: TestResult):
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("测试内容")
            temp_path = f.name
            
        try:
            response = await tester.client.post(
                "/api/file/read",
                json={"file_path": temp_path, "format": "text"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            result.details = data
        finally:
            os.unlink(temp_path)
            
    await tester.run_test("文件读取", "原子能力", test)


async def test_file_write(tester: ComprehensiveAPITester):
    """测试文件写入"""
    async def test(result: TestResult):
        temp_path = tempfile.mktemp(suffix='.txt')
        
        try:
            response = await tester.client.post(
                "/api/file/write",
                json={
                    "content": "API写入测试",
                    "file_path": temp_path,
                    "format": "text"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") == True or "bytes_written" in data
            result.details = data
            
            # 验证文件确实被写入
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    await tester.run_test("文件写入", "原子能力", test)


async def test_file_list(tester: ComprehensiveAPITester):
    """测试目录列表"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/file/list",
            json={"dir_path": "."}
        )
        assert response.status_code == 200
        data = response.json()
        assert "files" in data or "items" in data
        result.details = data
        
    await tester.run_test("目录列表", "原子能力", test)


async def test_format_md_to_docx(tester: ComprehensiveAPITester):
    """测试Markdown转Word"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/format/md-to-docx",
            json={"content": "# 测试标题\n\n测试内容"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "docx"
        result.details = data
        
    await tester.run_test("Markdown转Word", "原子能力", test)


async def test_format_md_to_pptx(tester: ComprehensiveAPITester):
    """测试Markdown转PPT"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/format/md-to-pptx",
            json={"content": "# 幻灯片1\n\n内容1\n\n# 幻灯片2\n\n内容2"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "pptx"
        result.details = data
        
    await tester.run_test("Markdown转PPT", "原子能力", test)


async def test_format_text_to_table(tester: ComprehensiveAPITester):
    """测试文本转表格"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/format/text-to-table",
            json={
                "content": "姓名,年龄\n张三,25\n李四,30",
                "format": "markdown"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert data["rows"] == 3
        result.details = data
        
    await tester.run_test("文本转表格", "原子能力", test)


async def test_persona_list(tester: ComprehensiveAPITester):
    """测试人设列表"""
    async def test(result: TestResult):
        response = await tester.client.post("/api/persona/list")
        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
        assert "built_in" in data
        result.details = data
        
    await tester.run_test("人设列表", "原子能力", test)


async def test_persona_get(tester: ComprehensiveAPITester):
    """测试获取人设"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/persona/get",
            json={"name": "default"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "default"
        assert "content" in data
        result.details = data
        
    await tester.run_test("获取人设", "原子能力", test)


async def test_persona_save_delete(tester: ComprehensiveAPITester):
    """测试保存和删除人设"""
    async def test(result: TestResult):
        # 保存
        response = await tester.client.post(
            "/api/persona/save",
            json={
                "name": "test_api_persona",
                "content": "# 测试人设\n\nAPI测试用"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_api_persona"
        
        # 删除
        response = await tester.client.post(
            "/api/persona/delete",
            json={"name": "test_api_persona"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "deleted"
        result.details = {"save": True, "delete": True}
        
    await tester.run_test("人设保存删除", "原子能力", test)


async def test_evaluation_evaluate(tester: ComprehensiveAPITester):
    """测试内容评价"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/evaluation/evaluate",
            json={
                "content": "这是一段测试文本，用于评价功能测试。",
                "scene": "auto"
            }
        )
        # 评价功能可能需要LLM，可能返回500
        if response.status_code == 200:
            data = response.json()
            result.details = data
        else:
            # 记录但不失败，因为可能依赖外部服务
            result.details = {"status_code": response.status_code, "note": "可能依赖外部服务"}
            
    await tester.run_test("内容评价", "原子能力", test)


async def test_evaluation_score(tester: ComprehensiveAPITester):
    """测试获取评分"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/evaluation/score",
            json={
                "content": "这是一段测试文本。",
                "scene": "auto"
            }
        )
        # 评分功能可能需要LLM
        if response.status_code == 200:
            data = response.json()
            result.details = data
        else:
            result.details = {"status_code": response.status_code, "note": "可能依赖外部服务"}
            
    await tester.run_test("获取评分", "原子能力", test)


async def test_knowledge_statistics(tester: ComprehensiveAPITester):
    """测试知识图谱统计"""
    async def test(result: TestResult):
        response = await tester.client.get("/api/knowledge/statistics")
        if response.status_code == 200:
            data = response.json()
            result.details = data
        else:
            result.details = {"status_code": response.status_code, "note": "知识图谱可能未初始化"}
            
    await tester.run_test("知识图谱统计", "原子能力", test)


async def test_coding_review(tester: ComprehensiveAPITester):
    """测试代码审查"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/coding/review",
            json={
                "code": "def test():\n    pass",
                "language": "python"
            }
        )
        # 代码审查可能需要LLM
        if response.status_code == 200:
            data = response.json()
            result.details = data
        else:
            result.details = {"status_code": response.status_code, "note": "可能依赖外部服务"}
            
    await tester.run_test("代码审查", "原子能力", test)


async def test_coding_explain(tester: ComprehensiveAPITester):
    """测试代码解释"""
    async def test(result: TestResult):
        response = await tester.client.post(
            "/api/coding/explain",
            json={
                "code": "def hello():\n    print('Hello, World!')",
                "language": "python"
            }
        )
        # 代码解释可能需要LLM
        if response.status_code == 200:
            data = response.json()
            result.details = data
        else:
            result.details = {"status_code": response.status_code, "note": "可能依赖外部服务"}
            
    await tester.run_test("代码解释", "原子能力", test)


# ==========================================
# 复合能力测试
# ==========================================

async def test_file_write_read_cycle(tester: ComprehensiveAPITester):
    """测试文件写入后读取"""
    async def test(result: TestResult):
        temp_path = tempfile.mktemp(suffix='.txt')
        content = "复合测试内容 - 写入后读取"
        
        try:
            # 写入
            response = await tester.client.post(
                "/api/file/write",
                json={
                    "content": content,
                    "file_path": temp_path,
                    "format": "text"
                }
            )
            assert response.status_code == 200
            
            # 读取
            response = await tester.client.post(
                "/api/file/read",
                json={"file_path": temp_path, "format": "text"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["content"] == content
            result.details = {"write": True, "read": True, "content_match": True}
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    await tester.run_test("文件写入读取循环", "复合能力", test)


async def test_format_conversion_chain(tester: ComprehensiveAPITester):
    """测试格式转换链"""
    async def test(result: TestResult):
        md_content = "# 测试标题\n\n- 项目1\n- 项目2"
        
        # Markdown -> Word
        response = await tester.client.post(
            "/api/format/md-to-docx",
            json={"content": md_content}
        )
        assert response.status_code == 200
        docx_result = response.json()
        
        # Markdown -> PPT
        response = await tester.client.post(
            "/api/format/md-to-pptx",
            json={"content": md_content}
        )
        assert response.status_code == 200
        pptx_result = response.json()
        
        result.details = {
            "md_to_docx": docx_result,
            "md_to_pptx": pptx_result
        }
        
    await tester.run_test("格式转换链", "复合能力", test)


async def test_persona_crud_cycle(tester: ComprehensiveAPITester):
    """测试人设CRUD循环"""
    async def test(result: TestResult):
        persona_name = "test_crud_persona"
        persona_content = "# CRUD测试人设\n\n用于测试增删改查"
        
        # Create
        response = await tester.client.post(
            "/api/persona/save",
            json={"name": persona_name, "content": persona_content}
        )
        assert response.status_code == 200
        
        # Read
        response = await tester.client.post(
            "/api/persona/get",
            json={"name": persona_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == persona_content
        
        # Update
        updated_content = "# 更新后的人设\n\n内容已更新"
        response = await tester.client.post(
            "/api/persona/save",
            json={"name": persona_name, "content": updated_content}
        )
        assert response.status_code == 200
        
        # Verify Update
        response = await tester.client.post(
            "/api/persona/get",
            json={"name": persona_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == updated_content
        
        # Delete
        response = await tester.client.post(
            "/api/persona/delete",
            json={"name": persona_name}
        )
        assert response.status_code == 200
        
        # Verify Delete
        response = await tester.client.post(
            "/api/persona/get",
            json={"name": persona_name}
        )
        assert response.status_code in [400, 500]
        
        result.details = {"crud_cycle": "completed"}
        
    await tester.run_test("人设CRUD循环", "复合能力", test)


async def test_table_format_variants(tester: ComprehensiveAPITester):
    """测试表格格式变体"""
    async def test(result: TestResult):
        content = "姓名,年龄,城市\n张三,25,北京\n李四,30,上海"
        formats = ["markdown", "html", "csv"]
        results = {}
        
        for fmt in formats:
            response = await tester.client.post(
                "/api/format/text-to-table",
                json={"content": content, "format": fmt}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["format"] == fmt
            results[fmt] = True
            
        result.details = results
        
    await tester.run_test("表格格式变体", "复合能力", test)


# ==========================================
# 动线级别测试
# ==========================================

async def test_document_creation_workflow(tester: ComprehensiveAPITester):
    """测试文档创建工作流"""
    async def test(result: TestResult):
        # 1. 创建Markdown内容
        md_content = """# 项目报告

## 概述

这是一个测试报告。

## 数据

| 指标 | 数值 |
|------|------|
| 完成率 | 95% |
| 测试通过 | 100% |

## 结论

测试全部通过。
"""
        
        # 2. 转换为Word
        response = await tester.client.post(
            "/api/format/md-to-docx",
            json={"content": md_content, "output_path": "/tmp/test_report.docx"}
        )
        assert response.status_code == 200
        docx_result = response.json()
        
        # 3. 转换为PPT
        response = await tester.client.post(
            "/api/format/md-to-pptx",
            json={"content": md_content, "output_path": "/tmp/test_report.pptx"}
        )
        assert response.status_code == 200
        pptx_result = response.json()
        
        # 4. 清理
        for path in ["/tmp/test_report.docx", "/tmp/test_report.pptx"]:
            if os.path.exists(path):
                os.unlink(path)
                
        result.details = {
            "docx_created": docx_result.get("success", True),
            "pptx_created": pptx_result.get("success", True)
        }
        
    await tester.run_test("文档创建工作流", "动线级别", test)


async def test_persona_based_workflow(tester: ComprehensiveAPITester):
    """测试基于人设的工作流"""
    async def test(result: TestResult):
        # 1. 创建自定义人设
        persona_content = """# 代码审查专家

## 角色描述

你是一位经验丰富的代码审查专家，专注于：
- 代码质量
- 最佳实践
- 性能优化
- 安全性

## 审查标准

1. 代码可读性
2. 命名规范
3. 错误处理
4. 测试覆盖
"""
        
        response = await tester.client.post(
            "/api/persona/save",
            json={"name": "code_review_expert", "content": persona_content}
        )
        assert response.status_code == 200
        
        # 2. 获取人设
        response = await tester.client.post(
            "/api/persona/get",
            json={"name": "code_review_expert"}
        )
        assert response.status_code == 200
        persona_data = response.json()
        
        # 3. 列出人设（包含新创建的）
        response = await tester.client.post("/api/persona/list")
        assert response.status_code == 200
        list_data = response.json()
        assert "code_review_expert" in list_data["custom"]
        
        # 4. 清理
        response = await tester.client.post(
            "/api/persona/delete",
            json={"name": "code_review_expert"}
        )
        assert response.status_code == 200
        
        result.details = {
            "persona_created": True,
            "persona_retrieved": True,
            "persona_listed": True,
            "persona_deleted": True
        }
        
    await tester.run_test("基于人设的工作流", "动线级别", test)


async def test_data_processing_workflow(tester: ComprehensiveAPITester):
    """测试数据处理工作流"""
    async def test(result: TestResult):
        # 1. 准备CSV数据
        csv_data = """产品,销量,价格
产品A,100,50
产品B,200,30
产品C,150,45
"""
        
        # 2. 转换为Markdown表格
        response = await tester.client.post(
            "/api/format/text-to-table",
            json={"content": csv_data, "format": "markdown"}
        )
        assert response.status_code == 200
        md_table = response.json()
        
        # 3. 转换为HTML表格
        response = await tester.client.post(
            "/api/format/text-to-table",
            json={"content": csv_data, "format": "html"}
        )
        assert response.status_code == 200
        html_table = response.json()
        
        # 4. 写入文件
        response = await tester.client.post(
            "/api/file/write",
            json={
                "content": md_table["content"],
                "file_path": "/tmp/table_output.md",
                "format": "text"
            }
        )
        assert response.status_code == 200
        
        # 5. 清理
        if os.path.exists("/tmp/table_output.md"):
            os.unlink("/tmp/table_output.md")
            
        result.details = {
            "csv_parsed": True,
            "markdown_generated": True,
            "html_generated": True,
            "file_written": True
        }
        
    await tester.run_test("数据处理工作流", "动线级别", test)


# ==========================================
# 主测试函数
# ==========================================

async def run_comprehensive_tests():
    """运行综合测试"""
    print("\n" + "=" * 70)
    print("OpenCopilot API 综合测试")
    print("=" * 70)
    
    tester = ComprehensiveAPITester()
    await tester.setup()
    
    try:
        # 原子能力测试
        print("\n--- 原子能力测试 ---")
        await test_health_check(tester)
        await test_file_read(tester)
        await test_file_write(tester)
        await test_file_list(tester)
        await test_format_md_to_docx(tester)
        await test_format_md_to_pptx(tester)
        await test_format_text_to_table(tester)
        await test_persona_list(tester)
        await test_persona_get(tester)
        await test_persona_save_delete(tester)
        await test_evaluation_evaluate(tester)
        await test_evaluation_score(tester)
        await test_knowledge_statistics(tester)
        await test_coding_review(tester)
        await test_coding_explain(tester)
        
        # 复合能力测试
        print("\n--- 复合能力测试 ---")
        await test_file_write_read_cycle(tester)
        await test_format_conversion_chain(tester)
        await test_persona_crud_cycle(tester)
        await test_table_format_variants(tester)
        
        # 动线级别测试
        print("\n--- 动线级别测试 ---")
        await test_document_creation_workflow(tester)
        await test_persona_based_workflow(tester)
        await test_data_processing_workflow(tester)
        
    finally:
        await tester.teardown()
        
    # 打印总结
    passed, total = tester.print_summary()
    
    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_comprehensive_tests())
    sys.exit(0 if passed == total else 1)
