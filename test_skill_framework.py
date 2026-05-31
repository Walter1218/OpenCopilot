#!/usr/bin/env python3
"""
Skill 化框架测试脚本
"""

import asyncio
from skill_architecture import (
    BaseSkill, SkillRegistry, IntentRouter, SkillExecutor,
    SkillMetadata, SkillContext, SkillResult, SkillStatus
)


class TestSkill(BaseSkill):
    """测试 Skill"""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="test_skill",
            version="1.0.0",
            description="测试 Skill",
            author="OpenCopilot",
            tags=["test", "demo"],
            intents=["test", "demo", "hello"],
            dependencies=[]
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行测试"""
        print(f"TestSkill executed with intent: {context.intent}")
        print(f"Input data: {context.input_data}")
        
        return SkillResult(
            success=True,
            data={"message": "Hello from TestSkill!", "input": context.input_data},
            status=SkillStatus.COMPLETED
        )
    
    async def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理"""
        if context.intent in self.metadata.intents:
            return 0.9
        return 0.0


async def main():
    """主测试函数"""
    print("=== Skill 化框架测试 ===")
    
    # 1. 创建注册表
    registry = SkillRegistry()
    print("1. 创建注册表")
    
    # 2. 注册 Skill
    test_skill = TestSkill()
    registry.register(test_skill)
    print(f"2. 注册 Skill: {test_skill.metadata.name}")
    
    # 3. 列出所有 Skill
    skills = registry.list_skills()
    print(f"3. 已注册的 Skill: {skills}")
    
    # 4. 创建路由器
    router = IntentRouter(registry)
    print("4. 创建路由器")
    
    # 5. 创建执行器
    executor = SkillExecutor(registry, router)
    print("5. 创建执行器")
    
    # 6. 测试执行
    context = SkillContext(
        intent="test",
        input_data={"test_key": "test_value"}
    )
    
    print("\n--- 测试执行 ---")
    result = await executor.execute(context)
    
    print(f"执行结果: {result.success}")
    print(f"结果数据: {result.data}")
    print(f"状态: {result.status}")
    
    # 7. 测试指定 Skill 执行
    print("\n--- 测试指定 Skill 执行 ---")
    result2 = await executor.execute(context, skill_name="test_skill")
    
    print(f"执行结果: {result2.success}")
    print(f"结果数据: {result2.data}")
    
    # 8. 测试不存在的 Skill
    print("\n--- 测试不存在的 Skill ---")
    result3 = await executor.execute(context, skill_name="nonexistent_skill")
    
    print(f"执行结果: {result3.success}")
    print(f"错误信息: {result3.error}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())