# tests/tool_system/test_skill_adapter.py

import pytest
from tool_system.models import (
    ToolDefinition, ToolType, ToolCategory
)
from tool_system.registry import ToolRegistry
from tool_system.adapters.skill_adapter import SkillAdapter
from skill_architecture.registry import SkillRegistry
from skill_architecture.base import BaseSkill
from skill_architecture.models import SkillMetadata, SkillContext, SkillResult


# 创建测试用 Skill
class TestSkill(BaseSkill):
    """测试用 Skill"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._metadata = SkillMetadata(
            name="test_skill",
            description="A test skill",
            version="1.0.0",
            author="test",
            tags=["test", "code"],
            intents=["test_intent"],
            input_schema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input text"
                    }
                },
                "required": ["input"]
            }
        )
    
    @property
    def metadata(self):
        return self._metadata
    
    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            success=True,
            data={"output": f"Processed: {context.input_data.get('input', '')}"}
        )


class TestSkillWithMultipleTags(BaseSkill):
    """带多个标签的测试 Skill"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._metadata = SkillMetadata(
            name="multi_tag_skill",
            description="A skill with multiple tags",
            version="1.0.0",
            tags=["file", "filesystem", "read"],
            intents=["file_read"],
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    }
                },
                "required": ["path"]
            }
        )
    
    @property
    def metadata(self):
        return self._metadata
    
    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            success=True,
            data={"content": f"File content from {context.input_data.get('path', '')}"}
        )


class TestSkillWithNoInputSchema(BaseSkill):
    """没有输入模式的测试 Skill"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._metadata = SkillMetadata(
            name="no_input_skill",
            description="A skill with no input schema",
            version="1.0.0",
            tags=["system"],
            intents=["system_info"]
        )
    
    @property
    def metadata(self):
        return self._metadata
    
    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            success=True,
            data={"info": "System information"}
        )


class TestSkillAdapter:
    """Skill 适配器测试"""
    
    @pytest.fixture
    def tool_registry(self):
        return ToolRegistry()
    
    @pytest.fixture
    def skill_registry(self):
        return SkillRegistry()
    
    @pytest.fixture
    def adapter(self, tool_registry, skill_registry):
        return SkillAdapter(
            tool_registry=tool_registry,
            skill_registry=skill_registry
        )
    
    def test_register_skill(self, tool_registry, skill_registry, adapter):
        """测试注册单个 Skill"""
        # 注册 Skill
        skill = TestSkill()
        skill_registry.register(skill)
        
        # 注册为工具
        count = adapter.register_all_skills()
        
        assert count == 1
        
        # 验证工具注册
        tools = tool_registry.list_tools()
        assert len(tools) == 1
        assert tools[0].tool_id == "skill_test_skill"
        assert tools[0].tool_type == ToolType.SKILL
    
    def test_register_multiple_skills(self, tool_registry, skill_registry, adapter):
        """测试注册多个 Skill"""
        # 注册多个 Skill
        skills = [
            TestSkill(),
            TestSkillWithMultipleTags(),
            TestSkillWithNoInputSchema()
        ]
        
        for skill in skills:
            skill_registry.register(skill)
        
        count = adapter.register_all_skills()
        
        assert count == 3
        assert len(tool_registry.list_tools()) == 3
    
    def test_skill_to_tool_definition(self, tool_registry, skill_registry, adapter):
        """测试 Skill 到工具定义的转换"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        tool = tool_registry.get_tool("skill_test_skill")
        
        assert tool is not None
        assert tool.name == "test_skill"
        assert tool.description == "A test skill"
        assert tool.category == ToolCategory.CODE  # 根据标签自动判断
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "input"
        assert tool.parameters[0].required is True
    
    def test_skill_category_detection(self, tool_registry, skill_registry, adapter):
        """测试 Skill 类别自动检测"""
        # 注册不同类别的 Skill
        skills = [
            TestSkill(),  # code 标签
            TestSkillWithMultipleTags(),  # file 标签
            TestSkillWithNoInputSchema()  # system 标签
        ]
        
        for skill in skills:
            skill_registry.register(skill)
        
        adapter.register_all_skills()
        
        # 验证类别
        code_tool = tool_registry.get_tool("skill_test_skill")
        assert code_tool.category == ToolCategory.CODE
        
        file_tool = tool_registry.get_tool("skill_multi_tag_skill")
        assert file_tool.category == ToolCategory.FILE
        
        system_tool = tool_registry.get_tool("skill_no_input_skill")
        assert system_tool.category == ToolCategory.SYSTEM
    
    def test_skill_parameters_conversion(self, tool_registry, skill_registry, adapter):
        """测试 Skill 参数转换"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        tool = tool_registry.get_tool("skill_test_skill")
        
        assert len(tool.parameters) == 1
        param = tool.parameters[0]
        assert param.name == "input"
        assert param.type == "string"
        assert param.description == "Input text"
        assert param.required is True
    
    def test_skill_parameters_no_schema(self, tool_registry, skill_registry, adapter):
        """测试没有输入模式的 Skill 参数"""
        skill = TestSkillWithNoInputSchema()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        tool = tool_registry.get_tool("skill_no_input_skill")
        
        assert len(tool.parameters) == 0
    
    def test_skill_metadata_preservation(self, tool_registry, skill_registry, adapter):
        """测试 Skill 元数据保留"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        tool = tool_registry.get_tool("skill_test_skill")
        
        assert tool.version == "1.0.0"
        assert tool.author == "test"
        assert "test" in tool.tags
        assert "code" in tool.tags
        assert "skill" in tool.tags
        assert "internal" in tool.tags
    
    def test_skill_capabilities_in_metadata(self, tool_registry, skill_registry, adapter):
        """测试 Skill 能力信息在元数据中"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        tool = tool_registry.get_tool("skill_test_skill")
        
        assert "skill_name" in tool.metadata
        assert tool.metadata["skill_name"] == "test_skill"
        assert "intents" in tool.metadata
        assert "test_intent" in tool.metadata["intents"]
        assert "capabilities" in tool.metadata
        assert "test" in tool.metadata["capabilities"]
        assert "code" in tool.metadata["capabilities"]
    
    @pytest.mark.asyncio
    async def test_skill_handler_execution(self, tool_registry, skill_registry, adapter):
        """测试 Skill 处理函数执行"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        handler = tool_registry.get_handler("skill_test_skill")
        
        result = await handler(input="hello")
        
        assert result == {"output": "Processed: hello"}
    
    @pytest.mark.asyncio
    async def test_skill_handler_with_context(self, tool_registry, skill_registry, adapter):
        """测试 Skill 处理函数上下文传递"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        handler = tool_registry.get_handler("skill_test_skill")
        
        # 传递额外参数
        result = await handler(
            input="hello",
            intent="custom_intent"
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_skill_handler_error_handling(self, tool_registry, skill_registry, adapter):
        """测试 Skill 处理函数错误处理"""
        # 创建一个会失败的 Skill
        class FailingSkill(BaseSkill):
            def __init__(self, config=None):
                super().__init__(config)
                self._metadata = SkillMetadata(
                    name="failing_skill",
                    description="A skill that fails",
                    version="1.0.0",
                    tags=["test"]
                )
            
            @property
            def metadata(self):
                return self._metadata
            
            async def execute(self, context: SkillContext) -> SkillResult:
                return SkillResult(
                    success=False,
                    data={},
                    error="Skill execution failed"
                )
        
        skill = FailingSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        handler = tool_registry.get_handler("skill_failing_skill")
        
        with pytest.raises(Exception, match="Skill execution failed"):
            await handler()
    
    def test_adapter_with_existing_skills(self, tool_registry, skill_registry, adapter):
        """测试适配器与现有 Skill"""
        # 注册 Skill
        skill = TestSkill()
        skill_registry.register(skill)
        
        # 先注册到 Skill 系统
        skill_registry.register(skill)
        
        # 然后适配到工具系统
        count = adapter.register_all_skills()
        
        assert count == 1
        
        # 验证两个系统都有注册
        assert skill_registry.get_skill("test_skill") is not None
        assert tool_registry.get_tool("skill_test_skill") is not None
    
    def test_adapter_idempotent(self, tool_registry, skill_registry, adapter):
        """测试适配器幂等性"""
        skill = TestSkill()
        skill_registry.register(skill)
        
        # 多次注册
        count1 = adapter.register_all_skills()
        count2 = adapter.register_all_skills()
        
        # 应该都能成功，但不会重复注册
        assert count1 == 1
        assert count2 == 1
        
        # 工具数量应该还是 1
        assert len(tool_registry.list_tools()) == 1
    
    def test_adapter_with_no_skills(self, tool_registry, skill_registry, adapter):
        """测试没有 Skill 时的适配器"""
        count = adapter.register_all_skills()
        
        assert count == 0
        assert len(tool_registry.list_tools()) == 0
