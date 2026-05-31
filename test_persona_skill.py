"""
PersonaSkill 测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture import PersonaSkill, SkillContext


def print_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} | {test_name}")
    if details:
        print(f"   详情: {details}")


async def test_persona_skill():
    """测试 PersonaSkill"""
    print("\n" + "=" * 60)
    print("PersonaSkill 测试")
    print("=" * 60)
    
    skill = PersonaSkill()
    
    # 1. 测试初始化
    print("\n--- 初始化测试 ---")
    assert skill.metadata.name == "persona_skill"
    print_result("初始化测试", True, f"技能名称: {skill.metadata.name}")
    
    # 2. 测试 can_handle
    print("\n--- can_handle 测试 ---")
    
    # 测试意图匹配
    context1 = SkillContext(intent="persona", input_data={})
    confidence1 = await skill.can_handle(context1)
    assert confidence1 > 0.5
    print_result("意图匹配测试", True, f"置信度: {confidence1}")
    
    # 测试动作匹配
    context2 = SkillContext(intent="", input_data={"action": "list"})
    confidence2 = await skill.can_handle(context2)
    assert confidence2 > 0.5
    print_result("动作匹配测试", True, f"置信度: {confidence2}")
    
    # 测试内容匹配
    context3 = SkillContext(intent="", input_data={"content": "请帮我管理人设"})
    confidence3 = await skill.can_handle(context3)
    assert confidence3 > 0.5
    print_result("内容匹配测试", True, f"置信度: {confidence3}")
    
    # 测试不匹配
    context4 = SkillContext(intent="unknown", input_data={"action": "unknown"})
    confidence4 = await skill.can_handle(context4)
    assert confidence4 < 0.5
    print_result("不匹配测试", True, f"置信度: {confidence4}")
    
    # 3. 测试列出人设
    print("\n--- 列出人设测试 ---")
    context_list = SkillContext(
        intent="persona_list",
        input_data={"action": "list"}
    )
    result_list = await skill.execute(context_list)
    assert result_list.success
    assert "personas" in result_list.data
    print_result("列出人设测试", True, 
                 f"人设数量: {result_list.data.get('total', 0)}")
    
    # 4. 测试获取人设
    print("\n--- 获取人设测试 ---")
    context_get = SkillContext(
        intent="persona_get",
        input_data={
            "action": "get",
            "name": "default"
        }
    )
    result_get = await skill.execute(context_get)
    assert result_get.success
    assert result_get.data["name"] == "default"
    assert "content" in result_get.data
    print_result("获取人设测试", True, 
                 f"人设名称: {result_get.data['name']}, 内容长度: {result_get.data.get('length', 0)}")
    
    # 5. 测试保存人设
    print("\n--- 保存人设测试 ---")
    test_persona_content = """# 测试人设

这是一个测试人设，用于验证 PersonaSkill 的保存功能。

## 特点

- 测试用途
- 临时创建
"""
    context_save = SkillContext(
        intent="persona_save",
        input_data={
            "action": "save",
            "name": "test_persona",
            "content": test_persona_content
        }
    )
    result_save = await skill.execute(context_save)
    assert result_save.success
    assert result_save.data["name"] == "test_persona"
    print_result("保存人设测试", True, 
                 f"人设名称: {result_save.data['name']}, 操作: {result_save.data.get('action', 'N/A')}")
    
    # 6. 测试获取保存的人设
    print("\n--- 获取保存的人设测试 ---")
    context_get_saved = SkillContext(
        intent="persona_get",
        input_data={
            "action": "get",
            "name": "test_persona"
        }
    )
    result_get_saved = await skill.execute(context_get_saved)
    assert result_get_saved.success
    assert result_get_saved.data["name"] == "test_persona"
    print_result("获取保存的人设测试", True, 
                 f"人设名称: {result_get_saved.data['name']}")
    
    # 7. 测试删除人设
    print("\n--- 删除人设测试 ---")
    context_delete = SkillContext(
        intent="persona_delete",
        input_data={
            "action": "delete",
            "name": "test_persona"
        }
    )
    result_delete = await skill.execute(context_delete)
    assert result_delete.success
    assert result_delete.data["action"] == "deleted"
    print_result("删除人设测试", True, 
                 f"人设名称: {result_delete.data['name']}, 操作: {result_delete.data.get('action', 'N/A')}")
    
    # 8. 测试删除内置人设（应该失败）
    print("\n--- 删除内置人设测试 ---")
    context_delete_builtin = SkillContext(
        intent="persona_delete",
        input_data={
            "action": "delete",
            "name": "default"
        }
    )
    result_delete_builtin = await skill.execute(context_delete_builtin)
    assert not result_delete_builtin.success
    assert "内置角色无法删除" in result_delete_builtin.error
    print_result("删除内置人设测试", True, "内置人设保护生效")
    
    # 9. 测试错误处理
    print("\n--- 错误处理测试 ---")
    context_empty = SkillContext(
        intent="persona_get",
        input_data={
            "action": "get",
            "name": ""
        }
    )
    result_empty = await skill.execute(context_empty)
    assert not result_empty.success
    assert "缺少人设名称" in result_empty.error
    print_result("错误处理测试", True, "空名称正确返回错误")
    
    # 10. 测试不存在的人设
    print("\n--- 不存在人设测试 ---")
    context_not_exist = SkillContext(
        intent="persona_get",
        input_data={
            "action": "get",
            "name": "nonexistent_persona"
        }
    )
    result_not_exist = await skill.execute(context_not_exist)
    assert not result_not_exist.success
    assert "不存在" in result_not_exist.error
    print_result("不存在人设测试", True, "不存在的人设正确返回错误")
    
    # 测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("\n支持的功能:")
    print("  1. 列出所有人设")
    print("  2. 获取指定人设内容")
    print("  3. 保存人设（新建或覆盖）")
    print("  4. 删除自定义人设")
    print("  5. 内置人设保护")
    print("  6. 错误处理机制")


if __name__ == "__main__":
    asyncio.run(test_persona_skill())
