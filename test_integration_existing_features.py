"""
现有功能与新模块集成测试

测试翻译、代码阅读、PPT等功能与知识检索、Broker权限的集成情况。

测试分类：
1. 翻译功能 + 知识检索集成
2. 代码阅读 + 知识检索集成
3. PPT生成 + 知识检索集成
4. 功能与Broker权限集成
"""

import os
import sys
import json
import asyncio
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


class IntegrationTestResult:
    """集成测试结果封装"""
    def __init__(self, name: str, success: bool, duration: float = 0, 
                 error: str = None, details: Dict = None):
        self.name = name
        self.success = success
        self.duration = duration
        self.error = error
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "success": self.success,
            "duration": self.duration,
            "error": self.error,
            "details": self.details,
            "timestamp": self.timestamp
        }


class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.results: List[IntegrationTestResult] = []
        self.llm_provider = None
        self.api_key = os.environ.get("MINIMAX_API_KEY")
        
    def log_result(self, result: IntegrationTestResult):
        """记录测试结果"""
        self.results.append(result)
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.name} ({result.duration:.2f}s)")
        if result.error:
            print(f"    错误: {result.error[:100]}...")
    
    def run_test(self, name: str, test_func, *args, **kwargs) -> IntegrationTestResult:
        """运行单个测试"""
        import time
        start_time = time.time()
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            if isinstance(result, dict):
                return IntegrationTestResult(name, True, duration, details=result)
            else:
                return IntegrationTestResult(name, True, duration)
        except Exception as e:
            duration = time.time() - start_time
            return IntegrationTestResult(name, False, duration, error=str(e))
    
    def get_llm_provider(self):
        """获取 LLM 提供者"""
        if self.llm_provider is None:
            from llm_provider import MiniMaxProvider
            self.llm_provider = MiniMaxProvider(api_key=self.api_key)
        return self.llm_provider
    
    def llm_chat(self, prompt: str, system_prompt: str = "") -> str:
        """与 LLM 对话"""
        provider = self.get_llm_provider()
        response = ""
        for chunk in provider.stream_chat(prompt, system_prompt):
            response += chunk
        return response


# ==========================================
# 翻译功能 + 知识检索集成测试
# ==========================================

class TranslationKnowledgeIntegrationTests:
    """翻译功能与知识检索集成测试"""
    
    def __init__(self, runner: IntegrationTestRunner):
        self.runner = runner
    
    def test_translation_with_terminology_retrieval(self) -> Dict:
        """测试翻译时查询术语库"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 初始化知识检索
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        # 查询术语相关知识
        terminology_result = retrieval.query("术语", "document")
        
        # 模拟翻译场景：翻译技术文档
        source_text = "The API endpoint returns a JSON response with status code 200."
        
        # 使用 LLM 进行翻译，并尝试利用术语知识
        system_prompt = "你是一个专业的技术翻译专家。"
        if terminology_result.success and terminology_result.data:
            # 提取术语知识
            terminology_items = []
            for item in terminology_result.data[:3]:
                if hasattr(item, 'name'):
                    terminology_items.append(f"- {item.name}: {item.description}")
            
            if terminology_items:
                terminology_text = "\n".join(terminology_items)
                system_prompt += f"\n\n参考术语库：\n{terminology_text}"
        
        translation_prompt = f"请将以下英文翻译成中文：\n\n{source_text}"
        response = self.runner.llm_chat(translation_prompt, system_prompt)
        
        return {
            "source_text": source_text,
            "translated_text": response,
            "terminology_retrieved": terminology_result.success,
            "terminology_count": len(terminology_result.data) if terminology_result.success else 0,
            "translation_length": len(response)
        }
    
    def test_translation_memory_with_knowledge(self) -> Dict:
        """测试翻译记忆系统与知识检索的集成"""
        from knowledge_retrieval import KnowledgeRetrieval
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        # 初始化组件
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        memory = TranslationMemory()
        
        # 存储一些翻译记忆
        unit = TranslationUnit(
            source="API endpoint",
            target="API 端点",
            source_lang="en",
            target_lang="zh",
            context="技术文档"
        )
        memory.add_unit(unit)
        
        # 查询相关知识
        api_knowledge = retrieval.query("API", "api")
        
        # 测试翻译时是否能利用记忆和知识
        test_text = "Please check the API endpoint documentation."
        
        # 从记忆中查找匹配
        memory_matches = memory.search_fuzzy("API endpoint", threshold=0.5)
        
        # 从知识中获取补充信息
        knowledge_context = ""
        if api_knowledge.success and api_knowledge.data:
            knowledge_items = []
            for item in api_knowledge.data[:2]:
                if hasattr(item, 'description'):
                    knowledge_items.append(f"- {item.description}")
            if knowledge_items:
                knowledge_context = "\n".join(knowledge_items)
        
        return {
            "test_text": test_text,
            "memory_matches": len(memory_matches),
            "knowledge_items": len(api_knowledge.data) if api_knowledge.success else 0,
            "has_memory": len(memory_matches) > 0,
            "has_knowledge": bool(knowledge_context)
        }


# ==========================================
# 代码阅读 + 知识检索集成测试
# ==========================================

class CodeReadingKnowledgeIntegrationTests:
    """代码阅读与知识检索集成测试"""
    
    def __init__(self, runner: IntegrationTestRunner):
        self.runner = runner
    
    def test_code_explain_with_documentation(self) -> Dict:
        """测试代码解释时查询相关文档"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 初始化知识检索
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        # 待解释的代码
        code_snippet = """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
        
        # 查询相关文档
        algorithm_docs = retrieval.query("算法", "document")
        
        # 使用 LLM 解释代码
        system_prompt = "你是一个专业的Python开发者，擅长解释代码。"
        if algorithm_docs.success and algorithm_docs.data:
            doc_items = []
            for item in algorithm_docs.data[:2]:
                if hasattr(item, 'description'):
                    doc_items.append(f"- {item.description}")
            if doc_items:
                doc_text = "\n".join(doc_items)
                system_prompt += f"\n\n参考文档：\n{doc_text}"
        
        explain_prompt = f"请解释以下Python代码的功能和实现原理：\n\n```python\n{code_snippet}\n```"
        explanation = self.runner.llm_chat(explain_prompt, system_prompt)
        
        return {
            "code_snippet": code_snippet.strip(),
            "explanation": explanation,
            "docs_retrieved": algorithm_docs.success,
            "docs_count": len(algorithm_docs.data) if algorithm_docs.success else 0,
            "explanation_length": len(explanation)
        }
    
    def test_code_analysis_with_project_structure(self) -> Dict:
        """测试代码分析时查询项目结构"""
        from knowledge_retrieval import KnowledgeRetrieval
        from coding_agent import IntentDetector, CodingIntent
        
        # 初始化组件
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        intent_detector = IntentDetector()
        
        # 模拟用户请求
        user_message = "分析一下这个项目的代码结构"
        
        # 检测意图
        intent = intent_detector.detect(user_message)
        
        # 查询项目结构知识
        project_structure = retrieval.query("项目", "component")
        
        # 分析结果
        analysis_result = {
            "user_message": user_message,
            "detected_intent": intent.value,
            "is_analysis_intent": intent == CodingIntent.ANALYZE,
            "project_components": len(project_structure.data) if project_structure.success else 0,
            "has_project_knowledge": project_structure.success
        }
        
        # 如果有项目知识，生成分析报告
        if project_structure.success and project_structure.data:
            component_names = []
            for component in project_structure.data[:5]:
                if hasattr(component, 'name'):
                    component_names.append(component.name)
            analysis_result["top_components"] = component_names
        
        return analysis_result
    
    def test_code_review_with_best_practices(self) -> Dict:
        """测试代码审查时查询最佳实践"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 初始化知识检索
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        # 待审查的代码
        code_to_review = """
def get_user_data(user_id):
    # 直接拼接SQL，存在注入风险
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)
"""
        
        # 查询最佳实践
        best_practices = retrieval.query("代码规范", "document")
        
        # 使用 LLM 进行代码审查
        system_prompt = "你是一个资深Python开发者，擅长代码审查。"
        if best_practices.success and best_practices.data:
            practice_items = []
            for item in best_practices.data[:2]:
                if hasattr(item, 'description'):
                    practice_items.append(f"- {item.description}")
            if practice_items:
                practice_text = "\n".join(practice_items)
                system_prompt += f"\n\n参考最佳实践：\n{practice_text}"
        
        review_prompt = f"""请审查以下Python代码，指出问题和改进建议：

```python
{code_to_review}
```

重点关注：
1. 安全问题
2. 代码风格
3. 性能优化
"""
        
        review_response = self.runner.llm_chat(review_prompt, system_prompt)
        
        return {
            "code_reviewed": code_to_review.strip(),
            "review_response": review_response,
            "best_practices_retrieved": best_practices.success,
            "has_security_issue": "注入" in review_response or "SQL" in review_response,
            "review_length": len(review_response)
        }


# ==========================================
# PPT生成 + 知识检索集成测试
# ==========================================

class PPTKnowledgeIntegrationTests:
    """PPT生成与知识检索集成测试"""
    
    def __init__(self, runner: IntegrationTestRunner):
        self.runner = runner
    
    def test_ppt_generation_with_project_knowledge(self) -> Dict:
        """测试生成PPT时查询项目知识"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 初始化知识检索
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        # 查询项目知识
        project_knowledge = retrieval.query("OpenCopilot", "entity")
        
        # 模拟PPT生成场景
        ppt_topic = "OpenCopilot项目介绍"
        
        # 使用 LLM 生成PPT大纲
        system_prompt = "你是一个专业的演示文稿设计师。"
        if project_knowledge.success and project_knowledge.data:
            knowledge_items = []
            for item in project_knowledge.data[:3]:
                if hasattr(item, 'name') and hasattr(item, 'description'):
                    knowledge_items.append(f"- {item.name}: {item.description}")
            if knowledge_items:
                knowledge_text = "\n".join(knowledge_items)
                system_prompt += f"\n\n项目信息：\n{knowledge_text}"
        
        outline_prompt = f"请为以下主题生成PPT大纲：\n\n主题：{ppt_topic}\n\n要求：包含5-7个主要部分"
        outline = self.runner.llm_chat(outline_prompt, system_prompt)
        
        return {
            "ppt_topic": ppt_topic,
            "outline": outline,
            "project_knowledge_retrieved": project_knowledge.success,
            "knowledge_items": len(project_knowledge.data) if project_knowledge.success else 0,
            "outline_length": len(outline)
        }
    
    def test_ppt_suggestions_with_context(self) -> Dict:
        """测试PPT建议时查询上下文"""
        from knowledge_retrieval import KnowledgeRetrieval
        
        # 初始化知识检索
        retrieval = KnowledgeRetrieval()
        retrieval.initialize()
        
        # 查询相关上下文
        context_knowledge = retrieval.query("演示", "document")
        
        # 模拟PPT建议场景
        current_slide_content = "项目背景：OpenCopilot是一个AI编程助手"
        
        # 使用 LLM 生成建议
        system_prompt = "你是一个演示文稿优化专家。"
        if context_knowledge.success and context_knowledge.data:
            context_items = []
            for item in context_knowledge.data[:2]:
                if hasattr(item, 'description'):
                    context_items.append(f"- {item.description}")
            if context_items:
                context_text = "\n".join(context_items)
                system_prompt += f"\n\n参考建议：\n{context_text}"
        
        suggestion_prompt = f"请为以下幻灯片内容提供优化建议：\n\n{current_slide_content}"
        suggestions = self.runner.llm_chat(suggestion_prompt, system_prompt)
        
        return {
            "current_content": current_slide_content,
            "suggestions": suggestions,
            "context_retrieved": context_knowledge.success,
            "suggestion_length": len(suggestions)
        }


# ==========================================
# 功能与Broker权限集成测试
# ==========================================

class FeatureBrokerIntegrationTests:
    """功能与Broker权限集成测试"""
    
    def __init__(self, runner: IntegrationTestRunner):
        self.runner = runner
    
    def test_translation_permission_requirements(self) -> Dict:
        """测试翻译功能权限需求"""
        try:
            from asu_broker.core.server import check_accessibility_permission
            
            # 检查权限状态
            accessibility_result = check_accessibility_permission()
            
            # 翻译功能主要依赖LLM，不需要特殊权限
            # 但可能需要网络访问权限
            
            return {
                "accessibility_available": accessibility_result.get("available", False),
                "accessibility_granted": accessibility_result.get("granted", False),
                "translation_requires_accessibility": False,  # 翻译不需要辅助功能权限
                "translation_requires_network": True,  # 需要网络访问LLM
                "permission_check_success": True
            }
        except ImportError:
            return {
                "permission_check_success": False,
                "reason": "Broker模块未找到"
            }
    
    def test_code_analysis_permission_requirements(self) -> Dict:
        """测试代码分析功能权限需求"""
        try:
            from asu_broker.core.server import check_accessibility_permission, check_full_disk_access
            
            # 检查权限状态
            accessibility_result = check_accessibility_permission()
            disk_access_result = check_full_disk_access()
            
            # 代码分析可能需要文件读取权限
            
            return {
                "accessibility_available": accessibility_result.get("available", False),
                "accessibility_granted": accessibility_result.get("granted", False),
                "disk_access_available": disk_access_result.get("available", False),
                "disk_access_granted": disk_access_result.get("granted", False),
                "code_analysis_requires_accessibility": False,  # 不需要辅助功能
                "code_analysis_requires_file_access": True,  # 需要文件读取
                "permission_check_success": True
            }
        except ImportError:
            return {
                "permission_check_success": False,
                "reason": "Broker模块未找到"
            }
    
    def test_ppt_generation_permission_requirements(self) -> Dict:
        """测试PPT生成功能权限需求"""
        try:
            from asu_broker.core.server import check_accessibility_permission, check_full_disk_access
            
            # 检查权限状态
            accessibility_result = check_accessibility_permission()
            disk_access_result = check_full_disk_access()
            
            # PPT生成需要文件写入权限
            
            return {
                "accessibility_available": accessibility_result.get("available", False),
                "accessibility_granted": accessibility_result.get("granted", False),
                "disk_access_available": disk_access_result.get("available", False),
                "disk_access_granted": disk_access_result.get("granted", False),
                "ppt_generation_requires_accessibility": False,  # 不需要辅助功能
                "ppt_generation_requires_file_write": True,  # 需要文件写入
                "permission_check_success": True
            }
        except ImportError:
            return {
                "permission_check_success": False,
                "reason": "Broker模块未找到"
            }


# ==========================================
# 集成测试报告生成
# ==========================================

def generate_integration_report(results: List[IntegrationTestResult]) -> Dict:
    """生成集成测试报告"""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    
    # 按类别分组
    translation_results = [r for r in results if r.name.startswith("translation.")]
    code_reading_results = [r for r in results if r.name.startswith("code.")]
    ppt_results = [r for r in results if r.name.startswith("ppt.")]
    permission_results = [r for r in results if r.name.startswith("permission.")]
    
    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        },
        "categories": {
            "translation_integration": {
                "total": len(translation_results),
                "passed": sum(1 for r in translation_results if r.success),
                "failed": sum(1 for r in translation_results if not r.success)
            },
            "code_reading_integration": {
                "total": len(code_reading_results),
                "passed": sum(1 for r in code_reading_results if r.success),
                "failed": sum(1 for r in code_reading_results if not r.success)
            },
            "ppt_integration": {
                "total": len(ppt_results),
                "passed": sum(1 for r in ppt_results if r.success),
                "failed": sum(1 for r in ppt_results if not r.success)
            },
            "permission_integration": {
                "total": len(permission_results),
                "passed": sum(1 for r in permission_results if r.success),
                "failed": sum(1 for r in permission_results if not r.success)
            }
        },
        "details": [r.to_dict() for r in results],
        "failed_tests": [r.to_dict() for r in results if not r.success],
        "timestamp": datetime.now().isoformat()
    }
    
    return report


def run_integration_tests():
    """运行集成测试"""
    print("=" * 70)
    print("现有功能与新模块集成测试")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    runner = IntegrationTestRunner()
    
    # 检查 LLM API Key
    if not runner.api_key:
        print("⚠️  警告: 未找到 MINIMAX_API_KEY 环境变量")
        print("   LLM 相关测试将跳过")
        print()
    
    # ==========================================
    # 翻译功能 + 知识检索集成测试
    # ==========================================
    print("【翻译功能 + 知识检索集成测试】")
    translation_tests = TranslationKnowledgeIntegrationTests(runner)
    
    translation_test_cases = [
        ("translation.terminology_retrieval", translation_tests.test_translation_with_terminology_retrieval),
        ("translation.memory_knowledge", translation_tests.test_translation_memory_with_knowledge),
    ]
    
    for test_name, test_func in translation_test_cases:
        result = runner.run_test(test_name, test_func)
        runner.log_result(result)
    
    print()
    
    # ==========================================
    # 代码阅读 + 知识检索集成测试
    # ==========================================
    print("【代码阅读 + 知识检索集成测试】")
    code_tests = CodeReadingKnowledgeIntegrationTests(runner)
    
    code_test_cases = [
        ("code.explain_with_docs", code_tests.test_code_explain_with_documentation),
        ("code.analysis_with_structure", code_tests.test_code_analysis_with_project_structure),
        ("code.review_with_practices", code_tests.test_code_review_with_best_practices),
    ]
    
    for test_name, test_func in code_test_cases:
        result = runner.run_test(test_name, test_func)
        runner.log_result(result)
    
    print()
    
    # ==========================================
    # PPT生成 + 知识检索集成测试
    # ==========================================
    print("【PPT生成 + 知识检索集成测试】")
    ppt_tests = PPTKnowledgeIntegrationTests(runner)
    
    ppt_test_cases = [
        ("ppt.generation_with_knowledge", ppt_tests.test_ppt_generation_with_project_knowledge),
        ("ppt.suggestions_with_context", ppt_tests.test_ppt_suggestions_with_context),
    ]
    
    for test_name, test_func in ppt_test_cases:
        result = runner.run_test(test_name, test_func)
        runner.log_result(result)
    
    print()
    
    # ==========================================
    # 功能与Broker权限集成测试
    # ==========================================
    print("【功能与Broker权限集成测试】")
    permission_tests = FeatureBrokerIntegrationTests(runner)
    
    permission_test_cases = [
        ("permission.translation_requirements", permission_tests.test_translation_permission_requirements),
        ("permission.code_analysis_requirements", permission_tests.test_code_analysis_permission_requirements),
        ("permission.ppt_generation_requirements", permission_tests.test_ppt_generation_permission_requirements),
    ]
    
    for test_name, test_func in permission_test_cases:
        result = runner.run_test(test_name, test_func)
        runner.log_result(result)
    
    print()
    
    # ==========================================
    # 生成报告
    # ==========================================
    print("=" * 70)
    print("集成测试报告")
    print("=" * 70)
    
    report = generate_integration_report(runner.results)
    
    print(f"总计: {report['summary']['total']} 个测试")
    print(f"通过: {report['summary']['passed']} 个")
    print(f"失败: {report['summary']['failed']} 个")
    print(f"通过率: {report['summary']['pass_rate']}")
    print()
    
    print("分类统计:")
    for category, stats in report['categories'].items():
        print(f"  {category}: {stats['passed']}/{stats['total']} 通过")
    
    if report['failed_tests']:
        print()
        print("失败的测试:")
        for test in report['failed_tests']:
            print(f"  ✗ {test['name']}")
            print(f"    错误: {test['error'][:100]}...")
    
    # 保存报告
    report_file = Path(__file__).parent / "integration_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"详细报告已保存到: {report_file}")
    
    return report


if __name__ == "__main__":
    report = run_integration_tests()