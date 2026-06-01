#!/usr/bin/env python3
"""
工具系统验证脚本

快速验证工具系统的基本功能是否正常工作。
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def verify_tool_system():
    """验证工具系统"""
    print("=" * 60)
    print("工具系统验证")
    print("=" * 60)
    print()
    
    try:
        # 1. 导入测试
        print("1. 测试模块导入...")
        from tool_system.models import (
            ToolDefinition, ToolCall, ToolResult,
            ToolType, ToolCategory, ToolParameter, ToolStatus
        )
        from tool_system.registry import ToolRegistry
        from tool_system.executor import ToolExecutor
        print("   ✓ 模块导入成功")
        
        # 2. 创建注册表
        print("2. 创建工具注册表...")
        registry = ToolRegistry()
        print("   ✓ 注册表创建成功")
        
        # 3. 创建执行器
        print("3. 创建工具执行器...")
        executor = ToolExecutor(registry=registry)
        print("   ✓ 执行器创建成功")
        
        # 4. 注册工具
        print("4. 注册测试工具...")
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    required=True
                )
            ]
        )
        
        async def handler(input: str) -> str:
            return f"Processed: {input}"
        
        registry.register(definition, handler)
        print("   ✓ 工具注册成功")
        
        # 5. 查询工具
        print("5. 查询工具...")
        tool = registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "Test Tool"
        print("   ✓ 工具查询成功")
        
        # 6. 执行工具
        print("6. 执行工具...")
        call = ToolCall(
            tool_id="test_tool",
            parameters={"input": "hello"}
        )
        
        result = await executor.execute(call)
        assert result.success is True
        assert result.output == "Processed: hello"
        print("   ✓ 工具执行成功")
        
        # 7. 测试错误处理
        print("7. 测试错误处理...")
        
        # 7.1 工具不存在
        call = ToolCall(tool_id="nonexistent")
        result = await executor.execute(call)
        assert result.success is False
        assert "not found" in result.error.lower()
        print("   ✓ 工具不存在错误处理正确")
        
        # 7.2 参数验证失败
        call = ToolCall(tool_id="test_tool", parameters={})
        result = await executor.execute(call)
        assert result.success is False
        assert "validation" in result.error.lower()
        print("   ✓ 参数验证失败处理正确")
        
        # 8. 测试批量执行
        print("8. 测试批量执行...")
        calls = [
            ToolCall(tool_id="test_tool", parameters={"input": "test1"}),
            ToolCall(tool_id="test_tool", parameters={"input": "test2"}),
            ToolCall(tool_id="test_tool", parameters={"input": "test3"})
        ]
        
        results = await executor.batch_execute(calls)
        assert len(results) == 3
        assert all(r.success for r in results)
        print("   ✓ 批量执行成功")
        
        # 9. 测试统计信息
        print("9. 测试统计信息...")
        stats = executor.get_stats()
        assert stats["total_calls"] > 0
        assert stats["successful_calls"] > 0
        print("   ✓ 统计信息正确")
        
        # 10. 测试搜索功能
        print("10. 测试搜索功能...")
        results = registry.search_tools("test")
        assert len(results) == 1
        assert results[0].tool_id == "test_tool"
        print("   ✓ 搜索功能正常")
        
        print()
        print("=" * 60)
        print("✓ 所有验证通过!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ 验证失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


async def verify_skill_adapter():
    """验证 Skill 适配器"""
    print()
    print("=" * 60)
    print("Skill 适配器验证")
    print("=" * 60)
    print()
    
    try:
        from tool_system.registry import ToolRegistry
        from tool_system.adapters.skill_adapter import SkillAdapter
        from skill_architecture.registry import SkillRegistry
        from skill_architecture.base import BaseSkill
        from skill_architecture.models import SkillMetadata, SkillContext, SkillResult
        
        # 创建测试 Skill
        class TestSkill(BaseSkill):
            def __init__(self, config=None):
                super().__init__(config)
                self._metadata = SkillMetadata(
                    name="test_skill",
                    description="A test skill",
                    version="1.0.0",
                    tags=["test", "code"],
                    intents=["test_intent"]
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            async def execute(self, context: SkillContext) -> SkillResult:
                return SkillResult(
                    success=True,
                    data={"output": "Skill executed"}
                )
        
        # 创建注册表
        tool_registry = ToolRegistry()
        skill_registry = SkillRegistry()
        
        # 注册 Skill
        skill = TestSkill()
        skill_registry.register(skill)
        
        # 创建适配器
        adapter = SkillAdapter(
            tool_registry=tool_registry,
            skill_registry=skill_registry
        )
        
        # 注册所有 Skill
        count = adapter.register_all_skills()
        assert count == 1
        print("1. Skill 注册成功")
        
        # 验证工具注册
        tools = tool_registry.list_tools()
        assert len(tools) == 1
        assert tools[0].tool_id == "skill_test_skill"
        assert tools[0].tool_type.value == "skill"
        print("2. 工具注册验证成功")
        
        # 验证工具执行
        handler = tool_registry.get_handler("skill_test_skill")
        result = await handler(input="test")
        assert result == {"output": "Skill executed"}
        print("3. 工具执行验证成功")
        
        print()
        print("=" * 60)
        print("✓ Skill 适配器验证通过!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Skill 适配器验证失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("开始工具系统验证...")
    print()
    
    # 验证基本功能
    success1 = await verify_tool_system()
    
    # 验证 Skill 适配器
    success2 = await verify_skill_adapter()
    
    print()
    print("=" * 60)
    if success1 and success2:
        print("✓ 所有验证通过! 工具系统可以正常使用。")
        print()
        print("下一步:")
        print("  1. 运行完整测试: python run_tool_system_tests.py")
        print("  2. 查看测试报告: test_report.json")
        print("  3. 查看覆盖率报告: coverage.json")
    else:
        print("✗ 部分验证失败，请检查错误信息。")
    print("=" * 60)
    
    return success1 and success2


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
