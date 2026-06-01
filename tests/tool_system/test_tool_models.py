# tests/tool_system/test_tool_models.py

import pytest
import uuid
from tool_system.models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolType, ToolCategory, ToolParameter,
    ToolStatus, ToolExecutionLog
)


class TestToolModels:
    """数据模型测试"""
    
    def test_tool_definition_creation(self):
        """测试工具定义创建"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    required=True
                )
            ]
        )
        
        assert definition.tool_id == "test_tool"
        assert definition.name == "Test Tool"
        assert definition.tool_type == ToolType.FUNCTION
        assert definition.category == ToolCategory.CODE
        assert len(definition.parameters) == 1
    
    def test_tool_definition_defaults(self):
        """测试工具定义默认值"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool"
        )
        
        assert definition.version == "1.0.0"
        assert definition.author == ""
        assert definition.parameters == []
        assert definition.output_schema is None
        assert definition.requires_approval is False
        assert definition.timeout == 30.0
        assert definition.retry_count == 3
        assert definition.tags == []
        assert definition.metadata == {}
    
    def test_tool_call_creation(self):
        """测试工具调用创建"""
        call = ToolCall(
            tool_id="test_tool",
            parameters={"input": "hello"}
        )
        
        assert call.tool_id == "test_tool"
        assert call.parameters == {"input": "hello"}
        assert call.call_id is not None  # 自动生成
        assert call.timeout is None
        assert call.metadata == {}
    
    def test_tool_call_with_custom_id(self):
        """测试自定义 ID 的工具调用"""
        custom_id = str(uuid.uuid4())
        call = ToolCall(
            tool_id="test_tool",
            call_id=custom_id
        )
        
        assert call.call_id == custom_id
    
    def test_tool_result_success(self):
        """测试成功结果创建"""
        result = ToolResult(
            tool_call_id="call_123",
            tool_id="test_tool",
            tool_name="Test Tool",
            success=True,
            output="result",
            duration_ms=10.5
        )
        
        assert result.success is True
        assert result.output == "result"
        assert result.error is None
        assert result.duration_ms == 10.5
    
    def test_tool_result_failure(self):
        """测试失败结果创建"""
        result = ToolResult(
            tool_call_id="call_123",
            tool_id="test_tool",
            tool_name="Test Tool",
            success=False,
            error="Tool execution failed",
            duration_ms=5.0
        )
        
        assert result.success is False
        assert result.error == "Tool execution failed"
        assert result.output is None
    
    def test_tool_parameter_validation(self):
        """测试参数定义验证"""
        param = ToolParameter(
            name="file_path",
            type="string",
            description="文件路径",
            required=True
        )
        
        assert param.name == "file_path"
        assert param.type == "string"
        assert param.description == "文件路径"
        assert param.required is True
        assert param.default is None
        assert param.enum is None
        assert param.schema is None
    
    def test_tool_parameter_with_default(self):
        """测试带默认值的参数"""
        param = ToolParameter(
            name="encoding",
            type="string",
            default="utf-8"
        )
        
        assert param.default == "utf-8"
    
    def test_tool_parameter_with_enum(self):
        """测试带枚举值的参数"""
        param = ToolParameter(
            name="log_level",
            type="string",
            enum=["DEBUG", "INFO", "WARNING", "ERROR"]
        )
        
        assert param.enum == ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    def test_tool_status_enum(self):
        """测试工具状态枚举"""
        assert ToolStatus.AVAILABLE.value == "available"
        assert ToolStatus.BUSY.value == "busy"
        assert ToolStatus.DISABLED.value == "disabled"
        assert ToolStatus.ERROR.value == "error"
    
    def test_tool_type_enum(self):
        """测试工具类型枚举"""
        assert ToolType.SKILL.value == "skill"
        assert ToolType.HTTP_API.value == "http_api"
        assert ToolType.CLI.value == "cli"
        assert ToolType.MCP.value == "mcp"
        assert ToolType.FUNCTION.value == "function"
    
    def test_tool_category_enum(self):
        """测试工具类别枚举"""
        assert ToolCategory.CODE.value == "code"
        assert ToolCategory.FILE.value == "file"
        assert ToolCategory.WEB.value == "web"
        assert ToolCategory.KNOWLEDGE.value == "knowledge"
        assert ToolCategory.SYSTEM.value == "system"
        assert ToolCategory.CUSTOM.value == "custom"
    
    def test_tool_execution_log(self):
        """测试工具执行日志"""
        log = ToolExecutionLog(
            log_id="log_123",
            tool_id="test_tool",
            tool_name="Test Tool",
            call_id="call_123",
            parameters={"input": "hello"},
            result=ToolResult(
                tool_call_id="call_123",
                tool_id="test_tool",
                tool_name="Test Tool",
                success=True,
                output="result"
            ),
            start_time=1000.0,
            end_time=1001.0,
            duration_ms=1000.0,
            user_id="user1",
            session_id="session1"
        )
        
        assert log.log_id == "log_123"
        assert log.tool_id == "test_tool"
        assert log.user_id == "user1"
        assert log.session_id == "session1"
        assert log.error is None
