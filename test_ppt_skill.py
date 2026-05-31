"""
PPTSkill 测试

测试 PPT Skill 的各项功能。
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.ppt_skill import PPTSkill
from skill_architecture.models import SkillContext, SkillStatus


async def test_ppt_skill_initialization():
    """测试 PPTSkill 初始化"""
    print_header("PPTSkill 初始化测试")
    
    try:
        skill = PPTSkill()
        
        # 检查元数据
        metadata = skill.metadata
        assert metadata.name == "ppt_skill"
        assert metadata.version == "1.0.0"
        assert "ppt_generate" in metadata.intents
        assert "ppt_suggest" in metadata.intents
        assert "ppt_check" in metadata.intents
        assert "ppt_analyze" in metadata.intents
        assert "ppt_convert" in metadata.intents
        assert "ppt_cocreate" in metadata.intents
        
        print_result("PPTSkill 初始化", True, "元数据验证通过")
        return True
    except Exception as e:
        print_result("PPTSkill 初始化", False, str(e))
        return False


async def test_can_handle():
    """测试 can_handle 方法"""
    print_header("PPTSkill can_handle 测试")
    
    try:
        skill = PPTSkill()
        
        # 测试意图匹配
        context1 = SkillContext(
            intent="ppt_generate",
            input_data={"content": "测试内容"}
        )
        score1 = await skill.can_handle(context1)
        assert score1 >= 0.8, f"Expected score >= 0.8, got {score1}"
        print_result("意图匹配测试", True, f"置信度: {score1}")
        
        # 测试动作匹配
        context2 = SkillContext(
            intent="unknown",
            input_data={"action": "generate"}
        )
        score2 = await skill.can_handle(context2)
        assert score2 >= 0.7, f"Expected score >= 0.7, got {score2}"
        print_result("动作匹配测试", True, f"置信度: {score2}")
        
        # 测试内容匹配
        context3 = SkillContext(
            intent="unknown",
            input_data={"content": "帮我生成一个PPT"}
        )
        score3 = await skill.can_handle(context3)
        assert score3 >= 0.6, f"Expected score >= 0.6, got {score3}"
        print_result("内容匹配测试", True, f"置信度: {score3}")
        
        # 测试不匹配
        context4 = SkillContext(
            intent="unknown",
            input_data={"content": "今天天气怎么样"}
        )
        score4 = await skill.can_handle(context4)
        assert score4 < 0.5, f"Expected score < 0.5, got {score4}"
        print_result("不匹配测试", True, f"置信度: {score4}")
        
        return True
    except Exception as e:
        print_result("can_handle 测试", False, str(e))
        return False


async def test_generate_ppt():
    """测试 PPT 生成"""
    print_header("PPTSkill 生成测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少内容
        context1 = SkillContext(
            intent="ppt_generate",
            input_data={"action": "generate"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "Content is required" in result1.error
        print_result("缺少内容测试", True, "正确返回错误")
        
        # 测试正常生成（需要 ppt_generator 模块）
        context2 = SkillContext(
            intent="ppt_generate",
            input_data={
                "action": "generate",
                "content": "人工智能正在改变我们的生活。机器学习是AI的核心技术。深度学习在图像识别领域取得突破。",
                "title": "AI发展报告",
                "theme": "corporate"
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("PPT生成测试", True, 
                        f"输出路径: {result2.data.get('output_path')}, "
                        f"幻灯片数: {result2.data.get('slides_count')}")
        else:
            print_result("PPT生成测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("PPT生成测试", False, str(e))
        return False


async def test_generate_suggestions():
    """测试建议生成"""
    print_header("PPTSkill 建议生成测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少上下文
        context1 = SkillContext(
            intent="ppt_suggest",
            input_data={"action": "suggest"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "PPT context is required" in result1.error
        print_result("缺少上下文测试", True, "正确返回错误")
        
        # 测试正常建议生成
        context2 = SkillContext(
            intent="ppt_suggest",
            input_data={
                "action": "suggest",
                "context": {
                    "slides": [
                        {"title": "封面", "content": "AI发展报告", "layout": "center"},
                        {"title": "概述", "content": "人工智能正在改变我们的生活", "layout": "default"},
                        {"title": "总结", "content": "AI未来可期", "layout": "default"}
                    ],
                    "current_slide": 0
                }
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("建议生成测试", True, 
                        f"建议数量: {result2.data.get('count')}")
        else:
            print_result("建议生成测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("建议生成测试", False, str(e))
        return False


async def test_check_ppt():
    """测试 PPT 检查"""
    print_header("PPTSkill 检查测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少上下文
        context1 = SkillContext(
            intent="ppt_check",
            input_data={"action": "check"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "PPT context is required" in result1.error
        print_result("缺少上下文测试", True, "正确返回错误")
        
        # 测试正常检查
        context2 = SkillContext(
            intent="ppt_check",
            input_data={
                "action": "check",
                "context": {
                    "slides": [
                        {"title": "封面", "content": "AI发展报告", "layout": "center"},
                        {"title": "概述", "content": "人工智能正在改变我们的生活", "layout": "default"},
                        {"title": "技术", "content": "机器学习是AI的核心技术", "layout": "default"},
                        {"title": "应用", "content": "深度学习在图像识别领域取得突破", "layout": "default"},
                        {"title": "总结", "content": "AI未来可期", "layout": "default"}
                    ],
                    "current_slide": 0
                },
                "checks": ["content_quality", "style_consistency", "logical_flow"]
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("PPT检查测试", True, 
                        f"总分: {result2.data.get('total_score')}")
        else:
            print_result("PPT检查测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("PPT检查测试", False, str(e))
        return False


async def test_analyze_ppt():
    """测试 PPT 分析"""
    print_header("PPTSkill 分析测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少上下文
        context1 = SkillContext(
            intent="ppt_analyze",
            input_data={"action": "analyze"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "PPT context is required" in result1.error
        print_result("缺少上下文测试", True, "正确返回错误")
        
        # 测试正常分析
        context2 = SkillContext(
            intent="ppt_analyze",
            input_data={
                "action": "analyze",
                "context": {
                    "slides": [
                        {"title": "封面", "content": "AI发展报告", "layout": "center"},
                        {"title": "概述", "content": "人工智能正在改变我们的生活", "layout": "default"},
                        {"title": "总结", "content": "AI未来可期", "layout": "default"}
                    ],
                    "current_slide": 0
                }
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("PPT分析测试", True, 
                        f"总幻灯片数: {result2.data.get('summary', {}).get('total_slides')}")
        else:
            print_result("PPT分析测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("PPT分析测试", False, str(e))
        return False


async def test_convert_content():
    """测试内容转换"""
    print_header("PPTSkill 内容转换测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少内容
        context1 = SkillContext(
            intent="ppt_convert",
            input_data={"action": "convert"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "Content is required" in result1.error
        print_result("缺少内容测试", True, "正确返回错误")
        
        # 测试表格转换
        context2 = SkillContext(
            intent="ppt_convert",
            input_data={
                "action": "convert",
                "content": "产品A销量100万，产品B销量200万，产品C销量150万"
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("内容转换测试", True, 
                        f"最佳匹配: {result2.data.get('best_match')}")
        else:
            print_result("内容转换测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("内容转换测试", False, str(e))
        return False


async def test_cocreate_ppt():
    """测试 PPT 共创"""
    print_header("PPTSkill 共创测试")
    
    try:
        skill = PPTSkill()
        
        # 测试缺少消息
        context1 = SkillContext(
            intent="ppt_cocreate",
            input_data={"action": "cocreate"}
        )
        result1 = await skill.execute(context1)
        assert not result1.success
        assert "Message is required" in result1.error
        print_result("缺少消息测试", True, "正确返回错误")
        
        # 测试正常共创 - 使用转换相关消息
        context2 = SkillContext(
            intent="ppt_cocreate",
            input_data={
                "action": "cocreate",
                "message": "帮我把这些数据转换成表格",
                "context": {
                    "slides": [
                        {"title": "AI发展", "content": "人工智能正在改变我们的生活", "layout": "default"}
                    ],
                    "current_slide": {
                        "index": 0,
                        "title": "AI发展",
                        "content": "人工智能正在改变我们的生活",
                        "layout": "default"
                    }
                },
                "session_id": "test_session_1"
            }
        )
        result2 = await skill.execute(context2)
        
        if result2.success:
            print_result("PPT共创测试", True, 
                        f"响应: {result2.data.get('response', '')[:50]}...")
        else:
            print_result("PPT共创测试", False, result2.error)
        
        return result2.success
    except Exception as e:
        print_result("PPT共创测试", False, str(e))
        return False


def print_header(title: str):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"      {details}")


async def main():
    """主测试函数"""
    print_header("PPTSkill 全面测试")
    
    results = []
    
    # 运行所有测试
    results.append(await test_ppt_skill_initialization())
    results.append(await test_can_handle())
    results.append(await test_generate_ppt())
    results.append(await test_generate_suggestions())
    results.append(await test_check_ppt())
    results.append(await test_analyze_ppt())
    results.append(await test_convert_content())
    results.append(await test_cocreate_ppt())
    
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
