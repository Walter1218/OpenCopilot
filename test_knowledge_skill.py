"""
KnowledgeSkill 集成测试

测试 KnowledgeSkill 的各项功能。
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_architecture.models import SkillContext
from skill_architecture.knowledge_skill import KnowledgeSkill


async def test_knowledge_skill():
    """测试 KnowledgeSkill"""
    print("=== KnowledgeSkill 集成测试 ===\n")
    
    # 创建 KnowledgeSkill 实例，指定配置
    config = {
        "project_root": os.path.dirname(os.path.abspath(__file__)),
        "graph_file": os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   "knowledge_graph", "opencopilot_knowledge_graph.json")
    }
    skill = KnowledgeSkill(config)
    
    # 测试 1: 初始化
    print("1. 测试初始化...")
    success = await skill.initialize()
    print(f"   初始化结果: {'成功' if success else '失败'}")
    assert success, "初始化失败"
    print("   ✅ 初始化测试通过\n")
    
    # 测试 2: 获取统计信息
    print("2. 测试获取统计信息...")
    context = SkillContext(
        intent="get_statistics",
        input_data={}
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   统计信息: {result.data}")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "获取统计信息失败"
    print("   ✅ 获取统计信息测试通过\n")
    
    # 测试 3: 搜索实体
    print("3. 测试搜索实体...")
    context = SkillContext(
        intent="search_entity",
        input_data={
            "query": "Agent",
            "entity_type": "component"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   找到 {result.data['count']} 个实体")
        if result.data['entities']:
            print(f"   第一个实体: {result.data['entities'][0]['name']}")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "搜索实体失败"
    print("   ✅ 搜索实体测试通过\n")
    
    # 测试 4: 知识查询
    print("4. 测试知识查询...")
    context = SkillContext(
        intent="knowledge_query",
        input_data={
            "query": "Broker"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   找到 {result.data['count']} 个实体")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "知识查询失败"
    print("   ✅ 知识查询测试通过\n")
    
    # 测试 5: 查找相关实体（如果有实体）
    if result.success and result.data['entities']:
        entity_id = result.data['entities'][0]['id']
        print(f"5. 测试查找相关实体 (实体ID: {entity_id})...")
        context = SkillContext(
            intent="find_related",
            input_data={
                "entity_id": entity_id,
                "max_depth": 1
            }
        )
        result = await skill.execute(context)
        print(f"   执行结果: {'成功' if result.success else '失败'}")
        if result.success:
            print(f"   找到 {result.data['count']} 个相关实体")
        else:
            print(f"   错误: {result.error}")
        assert result.success, "查找相关实体失败"
        print("   ✅ 查找相关实体测试通过\n")
    
    # 测试 6: 知识导出
    print("6. 测试知识导出...")
    context = SkillContext(
        intent="knowledge_export",
        input_data={
            "format": "json"
        }
    )
    result = await skill.execute(context)
    print(f"   执行结果: {'成功' if result.success else '失败'}")
    if result.success:
        print(f"   导出数据包含 {len(result.data.get('entities', []))} 个实体")
    else:
        print(f"   错误: {result.error}")
    assert result.success, "知识导出失败"
    print("   ✅ 知识导出测试通过\n")
    
    # 测试 7: can_handle 方法
    print("7. 测试 can_handle 方法...")
    context = SkillContext(
        intent="knowledge_query",
        input_data={"query": "test"}
    )
    confidence = await skill.can_handle(context)
    print(f"   置信度: {confidence}")
    assert confidence > 0, "can_handle 返回的置信度应该大于 0"
    print("   ✅ can_handle 测试通过\n")
    
    # 测试 8: 清理资源
    print("8. 测试清理资源...")
    await skill.cleanup()
    print("   ✅ 清理资源测试通过\n")
    
    print("=== 所有测试通过 ===")


async def test_with_registry():
    """测试与注册表集成"""
    print("\n=== 测试与注册表集成 ===\n")
    
    from skill_architecture import SkillRegistry, SkillContext
    
    # 创建注册表
    registry = SkillRegistry()
    
    # 创建并注册 KnowledgeSkill
    skill = KnowledgeSkill()
    registry.register(skill)
    
    # 列出所有 Skill
    skills = registry.list_skills()
    print(f"已注册的 Skill: {skills}")
    assert "knowledge" in skills, "KnowledgeSkill 未注册"
    print("✅ KnowledgeSkill 注册成功\n")
    
    # 通过注册表获取 Skill
    knowledge_skill = registry.get_skill("knowledge")
    assert knowledge_skill is not None, "无法通过注册表获取 KnowledgeSkill"
    print("✅ 通过注册表获取 KnowledgeSkill 成功\n")
    
    # 测试通过注册表执行
    await knowledge_skill.initialize()
    context = SkillContext(
        intent="get_statistics",
        input_data={}
    )
    result = await knowledge_skill.execute(context)
    print(f"通过注册表执行结果: {'成功' if result.success else '失败'}")
    assert result.success, "通过注册表执行失败"
    print("✅ 通过注册表执行测试通过\n")
    
    # 清理
    await knowledge_skill.cleanup()
    print("=== 注册表集成测试完成 ===")


async def main():
    """主测试函数"""
    try:
        await test_knowledge_skill()
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