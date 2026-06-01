# tests/tool_system/test_tool_registry.py

import pytest
import tempfile
import os
from tool_system.models import (
    ToolDefinition, ToolType, ToolCategory, ToolParameter, ToolStatus
)
from tool_system.registry import ToolRegistry


class TestToolRegistry:
    """工具注册表测试"""
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        handler = lambda **kwargs: "result"
        
        tool_id = registry.register(definition, handler)
        
        assert tool_id == "test_tool"
        assert registry.get_tool("test_tool") == definition
        assert registry.get_handler("test_tool") == handler
    
    def test_register_tool_with_validation(self):
        """测试注册工具时的验证"""
        registry = ToolRegistry()
        
        # 缺少 tool_id
        with pytest.raises(ValueError, match="Tool ID is required"):
            definition = ToolDefinition(
                tool_id="",
                name="Test Tool",
                description="A test tool"
            )
            registry.register(definition, lambda: None)
        
        # 缺少 name
        with pytest.raises(ValueError, match="Tool name is required"):
            definition = ToolDefinition(
                tool_id="test_tool",
                name="",
                description="A test tool"
            )
            registry.register(definition, lambda: None)
        
        # 缺少 description
        with pytest.raises(ValueError, match="Tool description is required"):
            definition = ToolDefinition(
                tool_id="test_tool",
                name="Test Tool",
                description=""
            )
            registry.register(definition, lambda: None)
    
    def test_unregister_tool(self):
        """测试注销工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        registry.register(definition, lambda: None)
        
        success = registry.unregister("test_tool")
        
        assert success is True
        assert registry.get_tool("test_tool") is None
        assert registry.get_handler("test_tool") is None
        assert registry.get_status("test_tool") is None
    
    def test_unregister_nonexistent_tool(self):
        """测试注销不存在的工具"""
        registry = ToolRegistry()
        
        success = registry.unregister("nonexistent")
        
        assert success is False
    
    def test_list_tools_empty(self):
        """测试列出空工具列表"""
        registry = ToolRegistry()
        
        tools = registry.list_tools()
        
        assert len(tools) == 0
    
    def test_list_tools_with_filter(self):
        """测试过滤工具"""
        registry = ToolRegistry()
        
        # 注册多个工具
        for i in range(5):
            definition = ToolDefinition(
                tool_id=f"tool_{i}",
                name=f"Tool {i}",
                description=f"Tool {i}",
                tool_type=ToolType.FUNCTION,
                category=ToolCategory.CODE if i % 2 == 0 else ToolCategory.FILE,
                tags=["test"]
            )
            registry.register(definition, lambda: None)
        
        # 按类别过滤
        code_tools = registry.list_tools(category=ToolCategory.CODE)
        assert len(code_tools) == 3  # 0, 2, 4
        
        file_tools = registry.list_tools(category=ToolCategory.FILE)
        assert len(file_tools) == 2  # 1, 3
    
    def test_list_tools_by_type(self):
        """测试按类型过滤工具"""
        registry = ToolRegistry()
        
        # 注册不同类型工具
        for i, tool_type in enumerate([ToolType.FUNCTION, ToolType.HTTP_API, ToolType.SKILL]):
            definition = ToolDefinition(
                tool_id=f"tool_{i}",
                name=f"Tool {i}",
                description=f"Tool {i}",
                tool_type=tool_type,
                category=ToolCategory.CUSTOM
            )
            registry.register(definition, lambda: None)
        
        # 按类型过滤
        function_tools = registry.list_tools(tool_type=ToolType.FUNCTION)
        assert len(function_tools) == 1
        
        http_tools = registry.list_tools(tool_type=ToolType.HTTP_API)
        assert len(http_tools) == 1
        
        skill_tools = registry.list_tools(tool_type=ToolType.SKILL)
        assert len(skill_tools) == 1
    
    def test_list_tools_by_tags(self):
        """测试按标签过滤工具"""
        registry = ToolRegistry()
        
        # 注册带不同标签的工具
        definition1 = ToolDefinition(
            tool_id="tool_1",
            name="Tool 1",
            description="Tool 1",
            tags=["code", "python"]
        )
        registry.register(definition1, lambda: None)
        
        definition2 = ToolDefinition(
            tool_id="tool_2",
            name="Tool 2",
            description="Tool 2",
            tags=["file", "read"]
        )
        registry.register(definition2, lambda: None)
        
        # 按标签过滤
        code_tools = registry.list_tools(tags=["code"])
        assert len(code_tools) == 1
        assert code_tools[0].tool_id == "tool_1"
        
        file_tools = registry.list_tools(tags=["file"])
        assert len(file_tools) == 1
        assert file_tools[0].tool_id == "tool_2"
    
    def test_list_tools_by_status(self):
        """测试按状态过滤工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool"
        )
        registry.register(definition, lambda: None)
        
        # 初始状态
        available_tools = registry.list_tools(status=ToolStatus.AVAILABLE)
        assert len(available_tools) == 1
        
        busy_tools = registry.list_tools(status=ToolStatus.BUSY)
        assert len(busy_tools) == 0
        
        # 修改状态
        registry.set_status("test_tool", ToolStatus.BUSY)
        
        available_tools = registry.list_tools(status=ToolStatus.AVAILABLE)
        assert len(available_tools) == 0
        
        busy_tools = registry.list_tools(status=ToolStatus.BUSY)
        assert len(busy_tools) == 1
    
    def test_search_tools(self):
        """测试搜索工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="code_review",
            name="Code Review",
            description="Review code for issues",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CODE,
            tags=["code", "review"]
        )
        registry.register(definition, lambda: None)
        
        # 搜索名称
        results = registry.search_tools("review")
        assert len(results) == 1
        assert results[0].tool_id == "code_review"
        
        # 搜索描述
        results = registry.search_tools("issues")
        assert len(results) == 1
        
        # 搜索标签
        results = registry.search_tools("code")
        assert len(results) == 1
        
        # 搜索不存在
        results = registry.search_tools("nonexistent")
        assert len(results) == 0
    
    def test_search_tools_case_insensitive(self):
        """测试搜索工具大小写不敏感"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="code_review",
            name="Code Review",
            description="Review code",
            tags=["code"]
        )
        registry.register(definition, lambda: None)
        
        # 大小写不敏感
        results = registry.search_tools("CODE")
        assert len(results) == 1
        
        results = registry.search_tools("Review")
        assert len(results) == 1
    
    def test_find_by_capability(self):
        """测试根据能力查找工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="code_review",
            name="Code Review",
            description="Review code",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CODE,
            tags=["code"],
            metadata={"capabilities": ["code_review", "code_analysis"]}
        )
        registry.register(definition, lambda: None)
        
        results = registry.find_by_capability("code_review")
        assert len(results) == 1
        assert results[0].tool_id == "code_review"
        
        results = registry.find_by_capability("code_analysis")
        assert len(results) == 1
        
        results = registry.find_by_capability("nonexistent")
        assert len(results) == 0
    
    def test_tool_status_management(self):
        """测试工具状态管理"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        registry.register(definition, lambda: None)
        
        # 初始状态
        status = registry.get_status("test_tool")
        assert status == ToolStatus.AVAILABLE
        
        # 修改状态
        registry.set_status("test_tool", ToolStatus.BUSY)
        status = registry.get_status("test_tool")
        assert status == ToolStatus.BUSY
        
        # 再次修改
        registry.set_status("test_tool", ToolStatus.ERROR)
        status = registry.get_status("test_tool")
        assert status == ToolStatus.ERROR
    
    def test_persistence(self):
        """测试持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "tools.json")
            
            # 创建并保存
            registry1 = ToolRegistry(storage_path=storage_path)
            definition = ToolDefinition(
                tool_id="test_tool",
                name="Test Tool",
                description="A test tool",
                tool_type=ToolType.FUNCTION,
                category=ToolCategory.CUSTOM,
                tags=["test"]
            )
            registry1.register(definition, lambda: None)
            
            # 验证文件已创建
            assert os.path.exists(storage_path)
            
            # 重新加载
            registry2 = ToolRegistry(storage_path=storage_path)
            
            # 验证持久化
            assert registry2.get_tool("test_tool") is not None
            assert registry2.get_tool("test_tool").name == "Test Tool"
            assert registry2.get_tool("test_tool").tags == ["test"]
    
    def test_persistence_multiple_tools(self):
        """测试多个工具的持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "tools.json")
            
            # 创建并保存多个工具
            registry1 = ToolRegistry(storage_path=storage_path)
            for i in range(3):
                definition = ToolDefinition(
                    tool_id=f"tool_{i}",
                    name=f"Tool {i}",
                    description=f"Tool {i}",
                    tool_type=ToolType.FUNCTION,
                    category=ToolCategory.CUSTOM
                )
                registry1.register(definition, lambda: None)
            
            # 重新加载
            registry2 = ToolRegistry(storage_path=storage_path)
            
            # 验证所有工具都持久化了
            assert len(registry2.list_tools()) == 3
    
    def test_overwrite_existing_tool(self):
        """测试覆盖现有工具"""
        registry = ToolRegistry()
        
        # 注册工具
        definition1 = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool 1",
            description="First version"
        )
        registry.register(definition1, lambda: "result1")
        
        # 覆盖注册
        definition2 = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool 2",
            description="Second version"
        )
        registry.register(definition2, lambda: "result2")
        
        # 验证覆盖
        tool = registry.get_tool("test_tool")
        assert tool.name == "Test Tool 2"
        assert tool.description == "Second version"
        
        handler = registry.get_handler("test_tool")
        assert handler() == "result2"
