#!/usr/bin/env python3
"""
大模型完整能力验证测试

真正调用大模型API，验证CodingSkill的各项功能。
"""

import asyncio
import sys
import os
import json
import time
from typing import Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.models import SkillContext
from skill_architecture.coding_skill import CodingSkill
from llm_provider import MiniMaxProvider


class LLMProviderAdapter:
    """
    LLM提供者适配器
    
    将MiniMaxProvider的stream_chat接口适配为CodingAgent期望的generate接口。
    """
    
    def __init__(self, provider: MiniMaxProvider):
        self.provider = provider
    
    async def generate(self, prompt: str) -> str:
        """
        生成响应（非流式）
        
        Args:
            prompt: 输入提示
            
        Returns:
            str: 生成的响应
        """
        # 收集流式响应
        response_parts = []
        for chunk in self.provider.stream_chat(prompt):
            response_parts.append(chunk)
        
        return "".join(response_parts)


class LLMIntegrationTestSuite:
    """大模型集成测试套件"""
    
    def __init__(self):
        self.results = []
        self.llm_provider = None
        self.skill = None
    
    async def setup(self):
        """初始化测试环境"""
        print("=" * 60)
        print("大模型完整能力验证测试")
        print("=" * 60)
        
        # 1. 初始化LLM提供者
        print("\n1. 初始化LLM提供者...")
        try:
            minimax_provider = MiniMaxProvider()
            self.llm_provider = LLMProviderAdapter(minimax_provider)
            print("   ✅ MiniMax提供者初始化成功")
        except Exception as e:
            print(f"   ❌ LLM提供者初始化失败: {e}")
            return False
        
        # 2. 初始化CodingSkill
        print("\n2. 初始化CodingSkill...")
        try:
            config = {
                "project_root": os.path.dirname(os.path.abspath(__file__)),
                "llm_provider": self.llm_provider
            }
            self.skill = CodingSkill(config)
            success = await self.skill.initialize()
            
            if success:
                print("   ✅ CodingSkill初始化成功")
            else:
                print("   ❌ CodingSkill初始化失败")
                return False
        except Exception as e:
            print(f"   ❌ CodingSkill初始化异常: {e}")
            return False
        
        return True
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        if not await self.setup():
            return {"error": "测试环境初始化失败"}
        
        start_time = time.time()
        
        # 测试用例列表
        test_cases = [
            ("Bug修复", self.test_bug_fix),
            ("代码审查", self.test_code_review),
            ("代码解释", self.test_code_explain),
            ("代码重构", self.test_code_refactor),
            ("代码分析", self.test_code_analyze),
        ]
        
        # 运行测试
        for test_name, test_func in test_cases:
            print(f"\n{'='*60}")
            print(f"测试: {test_name}")
            print('='*60)
            
            try:
                result = await test_func()
                self.results.append({
                    "name": test_name,
                    "passed": result.get("passed", False),
                    "duration": result.get("duration", 0),
                    "details": result
                })
            except Exception as e:
                print(f"   ❌ 测试异常: {e}")
                self.results.append({
                    "name": test_name,
                    "passed": False,
                    "error": str(e)
                })
        
        # 生成报告
        total_time = time.time() - start_time
        report = self._generate_report(total_time)
        
        # 清理资源
        await self.skill.cleanup()
        
        return report
    
    async def test_bug_fix(self) -> Dict[str, Any]:
        """测试Bug修复功能"""
        start_time = time.time()
        
        # 准备测试数据
        context = SkillContext(
            intent="bug_fix",
            input_data={
                "code": """def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

# 测试
result = calculate_average([])
print(result)""",
                "language": "python",
                "user_message": "这段代码在空列表时会报错，请修复"
            }
        )
        
        print("   输入代码:")
        print("   " + "-" * 40)
        for line in context.input_data["code"].split("\n")[:5]:
            print(f"   {line}")
        print("   ...")
        
        # 执行测试
        result = await self.skill.execute(context)
        duration = time.time() - start_time
        
        print(f"\n   执行结果: {'成功' if result.success else '失败'}")
        
        if result.success:
            analysis = result.data.get("analysis", "")
            fix_suggestion = result.data.get("fix_suggestion", "")
            confidence = result.data.get("confidence", 0)
            
            print(f"\n   分析结果:")
            print(f"   " + "-" * 40)
            # 只显示前200个字符
            print(f"   {analysis[:200]}...")
            
            print(f"\n   修复建议:")
            print(f"   " + "-" * 40)
            print(f"   {fix_suggestion[:200]}...")
            
            print(f"\n   置信度: {confidence}")
            print(f"   耗时: {duration:.2f}秒")
            
            return {
                "passed": True,
                "duration": duration,
                "analysis": analysis[:500],
                "fix_suggestion": fix_suggestion[:500],
                "confidence": confidence
            }
        else:
            print(f"   错误: {result.error}")
            return {
                "passed": False,
                "duration": duration,
                "error": result.error
            }
    
    async def test_code_review(self) -> Dict[str, Any]:
        """测试代码审查功能"""
        start_time = time.time()
        
        # 准备测试数据
        context = SkillContext(
            intent="code_review",
            input_data={
                "code": """def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def main():
    data = [1, -2, 3, -4, 5]
    processed = process_data(data)
    print(processed)

if __name__ == "__main__":
    main()""",
                "language": "python",
                "user_message": "请审查这段代码的质量"
            }
        )
        
        print("   输入代码:")
        print("   " + "-" * 40)
        for line in context.input_data["code"].split("\n")[:5]:
            print(f"   {line}")
        print("   ...")
        
        # 执行测试
        result = await self.skill.execute(context)
        duration = time.time() - start_time
        
        print(f"\n   执行结果: {'成功' if result.success else '失败'}")
        
        if result.success:
            review = result.data.get("review", "")
            issues = result.data.get("issues", [])
            suggestions = result.data.get("suggestions", [])
            score = result.data.get("score", 0)
            
            print(f"\n   审查结果:")
            print(f"   " + "-" * 40)
            print(f"   {review[:200]}...")
            
            print(f"\n   发现问题: {len(issues)}个")
            for i, issue in enumerate(issues[:3], 1):
                print(f"   {i}. {issue}")
            
            print(f"\n   改进建议: {len(suggestions)}个")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"   {i}. {suggestion}")
            
            print(f"\n   代码评分: {score}/100")
            print(f"   耗时: {duration:.2f}秒")
            
            return {
                "passed": True,
                "duration": duration,
                "review": review[:500],
                "issues_count": len(issues),
                "suggestions_count": len(suggestions),
                "score": score
            }
        else:
            print(f"   错误: {result.error}")
            return {
                "passed": False,
                "duration": duration,
                "error": result.error
            }
    
    async def test_code_explain(self) -> Dict[str, Any]:
        """测试代码解释功能"""
        start_time = time.time()
        
        # 准备测试数据
        context = SkillContext(
            intent="explain",
            input_data={
                "code": """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)""",
                "language": "python",
                "user_message": "请解释这段代码的工作原理"
            }
        )
        
        print("   输入代码:")
        print("   " + "-" * 40)
        for line in context.input_data["code"].split("\n"):
            print(f"   {line}")
        
        # 执行测试
        result = await self.skill.execute(context)
        duration = time.time() - start_time
        
        print(f"\n   执行结果: {'成功' if result.success else '失败'}")
        
        if result.success:
            explanation = result.data.get("explanation", "")
            
            print(f"\n   解释说明:")
            print(f"   " + "-" * 40)
            print(f"   {explanation[:300]}...")
            
            print(f"\n   耗时: {duration:.2f}秒")
            
            return {
                "passed": True,
                "duration": duration,
                "explanation": explanation[:500]
            }
        else:
            print(f"   错误: {result.error}")
            return {
                "passed": False,
                "duration": duration,
                "error": result.error
            }
    
    async def test_code_refactor(self) -> Dict[str, Any]:
        """测试代码重构功能"""
        start_time = time.time()
        
        # 准备测试数据
        context = SkillContext(
            intent="refactor",
            input_data={
                "code": """def get_user_info(user_id):
    # 查询用户
    sql = "SELECT * FROM users WHERE id = " + str(user_id)
    result = execute_sql(sql)
    if result:
        return {
            "name": result[0],
            "email": result[1],
            "age": result[2]
        }
    return None""",
                "language": "python",
                "user_message": "请重构这段代码，提高安全性和可读性"
            }
        )
        
        print("   输入代码:")
        print("   " + "-" * 40)
        for line in context.input_data["code"].split("\n")[:5]:
            print(f"   {line}")
        print("   ...")
        
        # 执行测试
        result = await self.skill.execute(context)
        duration = time.time() - start_time
        
        print(f"\n   执行结果: {'成功' if result.success else '失败'}")
        
        if result.success:
            refactored_code = result.data.get("refactored_code", "")
            changes = result.data.get("changes", [])
            explanation = result.data.get("explanation", "")
            
            print(f"\n   重构后的代码:")
            print(f"   " + "-" * 40)
            for line in refactored_code.split("\n")[:8]:
                print(f"   {line}")
            print("   ...")
            
            print(f"\n   修改说明:")
            print(f"   " + "-" * 40)
            print(f"   {explanation[:200]}...")
            
            print(f"\n   主要改动: {len(changes)}处")
            for i, change in enumerate(changes[:3], 1):
                print(f"   {i}. {change}")
            
            print(f"\n   耗时: {duration:.2f}秒")
            
            return {
                "passed": True,
                "duration": duration,
                "refactored_code": refactored_code[:500],
                "changes_count": len(changes),
                "explanation": explanation[:500]
            }
        else:
            print(f"   错误: {result.error}")
            return {
                "passed": False,
                "duration": duration,
                "error": result.error
            }
    
    async def test_code_analyze(self) -> Dict[str, Any]:
        """测试代码分析功能"""
        start_time = time.time()
        
        # 准备测试数据
        context = SkillContext(
            intent="analyze",
            input_data={
                "code": """class DataProcessor:
    def __init__(self):
        self.data = []
        self.cache = {}
    
    def load_data(self, file_path):
        with open(file_path, 'r') as f:
            self.data = json.load(f)
    
    def process(self):
        results = []
        for item in self.data:
            if item['id'] in self.cache:
                results.append(self.cache[item['id']])
            else:
                processed = self._transform(item)
                self.cache[item['id']] = processed
                results.append(processed)
        return results
    
    def _transform(self, item):
        return {
            'id': item['id'],
            'value': item['value'] * 2,
            'timestamp': time.time()
        }""",
                "language": "python",
                "user_message": "请分析这段代码的架构和潜在问题"
            }
        )
        
        print("   输入代码:")
        print("   " + "-" * 40)
        for line in context.input_data["code"].split("\n")[:5]:
            print(f"   {line}")
        print("   ...")
        
        # 执行测试
        result = await self.skill.execute(context)
        duration = time.time() - start_time
        
        print(f"\n   执行结果: {'成功' if result.success else '失败'}")
        
        if result.success:
            analysis = result.data.get("analysis", "")
            issues = result.data.get("issues", [])
            suggestions = result.data.get("suggestions", [])
            
            print(f"\n   分析结果:")
            print(f"   " + "-" * 40)
            print(f"   {analysis[:300]}...")
            
            print(f"\n   发现问题: {len(issues)}个")
            for i, issue in enumerate(issues[:3], 1):
                print(f"   {i}. {issue}")
            
            print(f"\n   改进建议: {len(suggestions)}个")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"   {i}. {suggestion}")
            
            print(f"\n   耗时: {duration:.2f}秒")
            
            return {
                "passed": True,
                "duration": duration,
                "analysis": analysis[:500],
                "issues_count": len(issues),
                "suggestions_count": len(suggestions)
            }
        else:
            print(f"   错误: {result.error}")
            return {
                "passed": False,
                "duration": duration,
                "error": result.error
            }
    
    def _generate_report(self, total_time: float) -> Dict[str, Any]:
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        # 统计结果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        print(f"\n测试摘要:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests}")
        print(f"  失败: {failed_tests}")
        print(f"  通过率: {pass_rate:.1%}")
        print(f"  总耗时: {total_time:.2f}秒")
        
        print(f"\n各测试结果:")
        print("-" * 40)
        for result in self.results:
            status = "✅" if result.get("passed", False) else "❌"
            name = result.get("name", "Unknown")
            duration = result.get("duration", 0)
            print(f"  {status} {name} ({duration:.2f}s)")
            
            if not result.get("passed", False) and "error" in result:
                print(f"     错误: {result['error'][:100]}")
        
        # 性能统计
        durations = [r.get("duration", 0) for r in self.results if r.get("passed", False)]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            print(f"\n性能统计:")
            print("-" * 40)
            print(f"  平均耗时: {avg_duration:.2f}秒")
            print(f"  最大耗时: {max_duration:.2f}秒")
            print(f"  最小耗时: {min_duration:.2f}秒")
        
        print("\n" + "=" * 60)
        
        # 生成报告数据
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": pass_rate,
                "total_time": total_time
            },
            "results": self.results,
            "performance": {
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0
            }
        }
        
        return report


async def main():
    """主函数"""
    test_suite = LLMIntegrationTestSuite()
    report = await test_suite.run_all_tests()
    
    # 保存报告
    report_path = "llm_integration_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已保存到: {report_path}")
    
    # 返回退出码
    if report.get("summary", {}).get("pass_rate", 0) == 1.0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)