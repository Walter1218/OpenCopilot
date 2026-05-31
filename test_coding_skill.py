"""
CodingSkill 集成测试

测试 CodingSkill 的各项功能。
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.models import SkillContext
from skill_architecture.coding_skill import CodingSkill


async def test_coding_skill():
    """测试 CodingSkill"""
    print("=== CodingSkill 集成测试 ===\n")
    
    # 创建 CodingSkill 实例
    config = {
        "project_root": os.path.dirname(os.path.abspath(__file__))
    }
    skill = CodingSkill(config)
    
    # 测试 1: 初始化
    print("1. 测试初始化...")
    success = await skill.initialize()
    print(f"   初始化结果: {'成功' if success else '失败'}")
    assert success, "初始化失败"
    print("   ✅ 初始化测试通过\n")
    
    # 测试 2: Bug 修复
    print("2. 测试 Bug 修复...")
    context = SkillContext(
        intent="bug_fix",
        input_data={
            "file_path": "test.py",
            "error_message": "NameError: name 'undefined_var' is not defined",
            "line_number": 10,
            "user_message": "修复这个错误",
            "language": "python"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   分析: {result.data.get('analysis', '')[:100]}...")
        print(f"   置信度: {result.data.get('confidence', 0)}")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "Bug 修复失败"
    print("   ✅ Bug 修复测试通过\n")
    
    # 测试 3: 代码审查
    print("3. 测试代码审查...")
    context = SkillContext(
        intent="code_review",
        input_data={
            "code": "def add(a, b):\n    return a + b",
            "language": "python",
            "user_message": "审查这段代码"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   评分: {result.data.get('score', 0)}")
        print(f"   问题数: {len(result.data.get('issues', []))}")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "代码审查失败"
    print("   ✅ 代码审查测试通过\n")
    
    # 测试 4: 代码解释
    print("4. 测试代码解释...")
    context = SkillContext(
        intent="explain",
        input_data={
            "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
            "language": "python",
            "user_message": "解释这段代码"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   解释: {result.data.get('explanation', '')[:100]}...")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "代码解释失败"
    print("   ✅ 代码解释测试通过\n")
    
    # 测试 5: 代码重构
    print("5. 测试代码重构...")
    context = SkillContext(
        intent="refactor",
        input_data={
            "code": "def add(a, b):\n    result = a + b\n    return result",
            "language": "python",
            "user_message": "重构这段代码"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   重构后的代码: {result.data.get('refactored_code', '')[:100]}...")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "代码重构失败"
    print("   ✅ 代码重构测试通过\n")
    
    # 测试 6: 代码分析
    print("6. 测试代码分析...")
    context = SkillContext(
        intent="analyze",
        input_data={
            "code": "def add(a, b):\n    return a + b",
            "language": "python",
            "user_message": "分析这段代码"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   分析: {result.data.get('analysis', '')[:100]}...")
        print(f"   问题数: {len(result.data.get('issues', []))}")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "代码分析失败"
    print("   ✅ 代码分析测试通过\n")
    
    # 测试 7: API 结果增强
    print("7. 测试 API 结果增强...")
    context = SkillContext(
        intent="enhance_api",
        input_data={
            "original_request": {"text": "分析代码质量"},
            "api_result": "代码质量良好",
            "file_path": "test.py"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   增强结果: {result.data.get('enhanced_result', '')[:100]}...")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "API 结果增强失败"
    print("   ✅ API 结果增强测试通过\n")
    
    # 测试 8: can_handle 方法
    print("8. 测试 can_handle 方法...")
    context = SkillContext(
        intent="bug_fix",
        input_data={"file_path": "test.py"}
    )
    confidence = await skill.can_handle(context)
    print(f"   置信度: {confidence}")
    assert confidence > 0, "can_handle 返回的置信度应该大于 0"
    print("   ✅ can_handle 测试通过\n")
    
    # 测试 9: 清理资源
    print("9. 测试清理资源...")
    await skill.cleanup()
    print("   ✅ 清理资源测试通过\n")
    
    print("=== 所有测试通过 ===")


async def test_with_registry():
    """测试与注册表集成"""
    print("\n=== 测试与注册表集成 ===\n")
    
    from skill_architecture import SkillRegistry, SkillContext
    
    # 创建注册表
    registry = SkillRegistry()
    
    # 创建并注册 CodingSkill
    skill = CodingSkill()
    registry.register(skill)
    
    # 列出所有 Skill
    skills = registry.list_skills()
    print(f"已注册的 Skill: {skills}")
    assert "coding" in skills, "CodingSkill 未注册"
    print("✅ CodingSkill 注册成功\n")
    
    # 通过注册表获取 Skill
    coding_skill = registry.get_skill("coding")
    assert coding_skill is not None, "无法通过注册表获取 CodingSkill"
    print("✅ 通过注册表获取 CodingSkill 成功\n")
    
    # 测试通过注册表执行
    await coding_skill.initialize()
    context = SkillContext(
        intent="analyze",
        input_data={
            "code": "def add(a, b):\n    return a + b",
            "language": "python"
        }
    )
    result = await coding_skill.execute(context)
    print(f"通过注册表执行结果: {'成功' if result.success else '失败'}")
    assert result.success, "通过注册表执行失败"
    print("✅ 通过注册表执行测试通过\n")
    
    # 清理
    await coding_skill.cleanup()
    print("=== 注册表集成测试完成 ===")


async def main():
    """主测试函数"""
    try:
        await test_coding_skill()
        await test_with_registry()
        print("\n🎉 所有测试通过！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())