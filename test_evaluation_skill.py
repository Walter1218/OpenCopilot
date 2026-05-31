#!/usr/bin/env python3
"""
EvaluationSkill 测试

测试 EvaluationSkill 的各项功能：
1. 初始化测试
2. can_handle 测试
3. 内容评价测试
4. 评分获取测试
5. 报告获取测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.evaluation_skill import EvaluationSkill
from skill_architecture.models import SkillContext, SkillStatus


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message:
        print(f"      {message}")


async def test_initialization():
    """测试初始化"""
    print_header("EvaluationSkill 初始化测试")
    
    try:
        skill = EvaluationSkill()
        
        # 验证元数据
        metadata = skill.metadata
        assert metadata.name == "evaluation_skill"
        assert metadata.version == "1.0.0"
        assert "evaluation" in metadata.tags
        assert "evaluate" in metadata.intents
        
        print_result("初始化测试", True, "元数据验证通过")
        return True
    except Exception as e:
        print_result("初始化测试", False, str(e))
        return False


async def test_can_handle():
    """测试 can_handle 方法"""
    print_header("EvaluationSkill can_handle 测试")
    
    try:
        skill = EvaluationSkill()
        
        # 测试意图匹配
        context1 = SkillContext(intent="evaluate", input_data={})
        confidence1 = await skill.can_handle(context1)
        assert confidence1 > 0.5
        print_result("意图匹配测试", True, f"置信度: {confidence1}")
        
        # 测试动作匹配
        context2 = SkillContext(intent="", input_data={"action": "quality_check"})
        confidence2 = await skill.can_handle(context2)
        assert confidence2 > 0.5
        print_result("动作匹配测试", True, f"置信度: {confidence2}")
        
        # 测试内容匹配
        context3 = SkillContext(intent="", input_data={"content": "请帮我评估这段代码的质量"})
        confidence3 = await skill.can_handle(context3)
        assert confidence3 > 0.5
        print_result("内容匹配测试", True, f"置信度: {confidence3}")
        
        # 测试不匹配
        context4 = SkillContext(intent="unknown", input_data={"action": "unknown"})
        confidence4 = await skill.can_handle(context4)
        assert confidence4 < 0.5
        print_result("不匹配测试", True, f"置信度: {confidence4}")
        
        return True
    except Exception as e:
        print_result("can_handle 测试", False, str(e))
        return False


async def test_evaluate_auto():
    """测试自动模式评价"""
    print_header("EvaluationSkill 自动模式评价测试")
    
    try:
        skill = EvaluationSkill()
        
        # 测试缺少内容
        context1 = SkillContext(
            intent="evaluate",
            input_data={"scene": "auto"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "content is required" in result1.error
        print_result("缺少内容测试", True, "正确返回错误")
        
        # 测试无效场景
        context2 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "测试内容",
                "scene": "invalid_scene"
            }
        )
        result2 = await skill.execute(context2)
        assert not result2.success
        assert "Invalid scene" in result2.error
        print_result("无效场景测试", True, "正确返回错误")
        
        # 测试正常自动模式评价
        context3 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "这是一个测试内容，用于评估自动模式的质量。",
                "scene": "auto",
                "input_text": "请帮我评估这段内容"
            }
        )
        result3 = await skill.execute(context3)
        
        if result3.success:
            print_result("自动模式评价测试", True, 
                        f"评分: {result3.data.get('score', 0):.1f}, 等级: {result3.data.get('level', '')}")
        else:
            print_result("自动模式评价测试", False, result3.error)
        
        return result3.success
    except Exception as e:
        print_result("自动模式评价测试", False, str(e))
        return False


async def test_evaluate_translate():
    """测试翻译场景评价"""
    print_header("EvaluationSkill 翻译场景评价测试")
    
    try:
        skill = EvaluationSkill()
        
        context = SkillContext(
            intent="evaluate",
            input_data={
                "content": "This is a test content for translation evaluation.",
                "scene": "translate",
                "input_text": "这是一个用于翻译评估的测试内容。",
                "reference": "This is a reference translation."
            }
        )
        result = await skill.execute(context)
        
        if result.success:
            print_result("翻译场景评价测试", True, 
                        f"评分: {result.data.get('score', 0):.1f}, 等级: {result.data.get('level', '')}")
        else:
            print_result("翻译场景评价测试", False, result.error)
        
        return result.success
    except Exception as e:
        print_result("翻译场景评价测试", False, str(e))
        return False


async def test_evaluate_code():
    """测试代码场景评价"""
    print_header("EvaluationSkill 代码场景评价测试")
    
    try:
        skill = EvaluationSkill()
        
        code_content = """
def calculate_sum(a, b):
    return a + b

# 测试函数
result = calculate_sum(1, 2)
print(result)
"""
        
        context = SkillContext(
            intent="evaluate",
            input_data={
                "content": code_content,
                "scene": "code",
                "input_text": "这是一个简单的Python函数"
            }
        )
        result = await skill.execute(context)
        
        if result.success:
            print_result("代码场景评价测试", True, 
                        f"评分: {result.data.get('score', 0):.1f}, 等级: {result.data.get('level', '')}")
        else:
            print_result("代码场景评价测试", False, result.error)
        
        return result.success
    except Exception as e:
        print_result("代码场景评价测试", False, str(e))
        return False


async def test_evaluate_polish():
    """测试润色场景评价"""
    print_header("EvaluationSkill 润色场景评价测试")
    
    try:
        skill = EvaluationSkill()
        
        context = SkillContext(
            intent="evaluate",
            input_data={
                "content": "这是一个经过润色的文本，语法正确，表达流畅。",
                "scene": "polish",
                "input_text": "这是一个需要润色的文本，语法有错误，表达不够流畅。"
            }
        )
        result = await skill.execute(context)
        
        if result.success:
            print_result("润色场景评价测试", True, 
                        f"评分: {result.data.get('score', 0):.1f}, 等级: {result.data.get('level', '')}")
        else:
            print_result("润色场景评价测试", False, result.error)
        
        return result.success
    except Exception as e:
        print_result("润色场景评价测试", False, str(e))
        return False


async def test_evaluate_custom():
    """测试自定义指令场景评价"""
    print_header("EvaluationSkill 自定义指令场景评价测试")
    
    try:
        skill = EvaluationSkill()
        
        # 测试缺少指令
        context1 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "测试内容",
                "scene": "custom"
            }
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "instruction is required" in result1.error
        print_result("缺少指令测试", True, "正确返回错误")
        
        # 测试正常自定义指令评价
        context2 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "根据您的要求，我已经完成了代码重构。",
                "scene": "custom",
                "instruction": "请帮我重构这段代码，提高可读性",
                "input_text": "def calc(a,b):return a+b"
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("自定义指令场景评价测试", True, 
                        f"评分: {result2.data.get('score', 0):.1f}, 等级: {result2.data.get('level', '')}")
        else:
            print_result("自定义指令场景评价测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("自定义指令场景评价测试", False, str(e))
        return False


async def test_evaluate_revision():
    """测试全文修订场景评价"""
    print_header("EvaluationSkill 全文修订场景评价测试")
    
    try:
        skill = EvaluationSkill()
        
        # 测试缺少完整文档
        context1 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "修订后的内容",
                "scene": "revision"
            }
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "full_document is required" in result1.error
        print_result("缺少完整文档测试", True, "正确返回错误")
        
        # 测试正常全文修订评价
        full_document = """
# 项目文档

## 1. 项目概述
这是一个测试项目。

## 2. 功能需求
- 功能1：用户登录
- 功能2：数据展示

## 3. 技术架构
使用Python开发。
"""
        
        context2 = SkillContext(
            intent="evaluate",
            input_data={
                "content": "修订后的项目文档，增加了详细说明。",
                "scene": "revision",
                "full_document": full_document
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("全文修订场景评价测试", True, 
                        f"评分: {result2.data.get('score', 0):.1f}, 等级: {result2.data.get('level', '')}")
        else:
            print_result("全文修订场景评价测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("全文修订场景评价测试", False, str(e))
        return False


async def test_get_score():
    """测试获取评分"""
    print_header("EvaluationSkill 获取评分测试")
    
    try:
        skill = EvaluationSkill()
        
        context = SkillContext(
            intent="evaluate",
            input_data={
                "content": "测试内容",
                "scene": "auto",
                "input_text": "请评估"
            }
        )
        
        # 调用 _get_score 方法
        result = await skill._get_score(context)
        
        if result.success:
            print_result("获取评分测试", True, 
                        f"评分: {result.data.get('score', 0):.1f}, 等级: {result.data.get('level', '')}")
        else:
            print_result("获取评分测试", False, result.error)
        
        return result.success
    except Exception as e:
        print_result("获取评分测试", False, str(e))
        return False


async def test_get_report():
    """测试获取详细报告"""
    print_header("EvaluationSkill 获取详细报告测试")
    
    try:
        skill = EvaluationSkill()
        
        context = SkillContext(
            intent="evaluate",
            input_data={
                "content": "测试内容",
                "scene": "auto",
                "input_text": "请评估"
            }
        )
        
        # 调用 _get_report 方法
        result = await skill._get_report(context)
        
        if result.success:
            report = result.data.get("report", {})
            print_result("获取详细报告测试", True, 
                        f"报告包含 {len(report.get('results', []))} 个维度")
        else:
            print_result("获取详细报告测试", False, result.error)
        
        return result.success
    except Exception as e:
        print_result("获取详细报告测试", False, str(e))
        return False


async def main():
    """主测试函数"""
    print_header("EvaluationSkill 全面测试")
    
    # 运行所有测试
    tests = [
        test_initialization,
        test_can_handle,
        test_evaluate_auto,
        test_evaluate_translate,
        test_evaluate_code,
        test_evaluate_polish,
        test_evaluate_custom,
        test_evaluate_revision,
        test_get_score,
        test_get_report
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {test.__name__} - {str(e)}")
            results.append(False)
    
    # 打印总结
    print_header("测试总结")
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())