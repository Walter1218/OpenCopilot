# 工具调用模块验证方案与兼容性处理

> **文档版本**: v1.0  
> **创建日期**: 2026-06-01  
> **状态**: 待实施

---

## 一、验证方案概述

### 1.1 验证原则

根据项目规范，验证必须遵循以下原则：

1. **真实代码验证**：不使用 mock，全部使用真实代码和真实调用
2. **全覆盖验证**：功能、性能、兼容性、边界条件全覆盖
3. **自动化验证**：所有测试用例可自动化执行
4. **可追溯性**：每个测试用例对应具体需求

### 1.2 验证层次

```
┌─────────────────────────────────────────────────────────────┐
│                    端到端测试 (E2E)                          │
│              真实场景、完整流程验证                            │
├─────────────────────────────────────────────────────────────┤
│                    集成测试 (Integration)                     │
│              模块间交互、API 端点验证                          │
├─────────────────────────────────────────────────────────────┤
│                    单元测试 (Unit)                            │
│              单个组件、函数验证                                │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 验证指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 代码覆盖率 | ≥ 90% | 核心模块必须达到 |
| 测试通过率 | 100% | 所有测试用例必须通过 |
| 功能完整性 | 100% | 所有功能点必须覆盖 |
| 性能基线 | 响应时间 < 100ms | 单次工具调用 |
| 兼容性 | 100% | 现有 Skill 功能不受影响 |

---

## 二、验证策略详细设计

### 2.1 单元测试策略

#### 2.1.1 数据模型测试 (`test_tool_models.py`)

```python
import pytest
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
    
    def test_tool_call_creation(self):
        """测试工具调用创建"""
        call = ToolCall(
            tool_id="test_tool",
            parameters={"input": "hello"}
        )
        
        assert call.tool_id == "test_tool"
        assert call.parameters == {"input": "hello"}
        assert call.call_id is not None  # 自动生成
    
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
        assert param.required is True
        assert param.default is None
    
    def test_tool_status_enum(self):
        """测试工具状态枚举"""
        assert ToolStatus.AVAILABLE.value == "available"
        assert ToolStatus.BUSY.value == "busy"
        assert ToolStatus.DISABLED.value == "disabled"
        assert ToolStatus.ERROR.value == "error"
```

#### 2.1.2 工具注册表测试 (`test_tool_registry.py`)

```python
import pytest
import tempfile
import os
from tool_system.models import (
    ToolDefinition, ToolType, ToolCategory, ToolParameter
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
                category=ToolCategory.CUSTOM
            )
            registry1.register(definition, lambda: None)
            
            # 重新加载
            registry2 = ToolRegistry(storage_path=storage_path)
            
            # 验证持久化
            assert registry2.get_tool("test_tool") is not None
            assert registry2.get_tool("test_tool").name == "Test Tool"
```

#### 2.1.3 工具执行器测试 (`test_tool_executor.py`)

```python
import pytest
import asyncio
from tool_system.models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolType, ToolCategory, ToolParameter, ToolStatus
)
from tool_system.registry import ToolRegistry
from tool_system.executor import ToolExecutor


class TestToolExecutor:
    """工具执行器测试"""
    
    @pytest.fixture
    def registry(self):
        """创建注册表"""
        return ToolRegistry()
    
    @pytest.fixture
    def executor(self, registry):
        """创建执行器"""
        return ToolExecutor(registry=registry)
    
    @pytest.mark.asyncio
    async def test_execute_success(self, registry, executor):
        """测试成功执行"""
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
        
        call = ToolCall(
            tool_id="test_tool",
            parameters={"input": "hello"}
        )
        
        result = await executor.execute(call)
        
        assert result.success is True
        assert result.output == "Processed: hello"
        assert result.duration_ms > 0
        assert result.tool_call_id is not None
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, executor):
        """测试工具不存在"""
        call = ToolCall(tool_id="nonexistent_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_validation_error(self, registry, executor):
        """测试参数验证失败"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="required_param",
                    type="string",
                    required=True
                )
            ]
        )
        
        registry.register(definition, lambda **kwargs: "result")
        
        # 缺少必需参数
        call = ToolCall(tool_id="test_tool", parameters={})
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "validation" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, registry, executor):
        """测试超时"""
        definition = ToolDefinition(
            tool_id="slow_tool",
            name="Slow Tool",
            description="A slow tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            timeout=0.1  # 100ms 超时
        )
        
        async def handler():
            await asyncio.sleep(1)  # 1秒延迟
            return "done"
        
        registry.register(definition, handler)
        
        call = ToolCall(tool_id="slow_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_handler_error(self, registry, executor):
        """测试处理函数错误"""
        definition = ToolDefinition(
            tool_id="error_tool",
            name="Error Tool",
            description="A tool that errors",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        async def handler():
            raise ValueError("Test error")
        
        registry.register(definition, handler)
        
        call = ToolCall(tool_id="error_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "Test error" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_busy(self, registry, executor):
        """测试工具忙碌"""
        definition = ToolDefinition(
            tool_id="busy_tool",
            name="Busy Tool",
            description="A busy tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        registry.register(definition, lambda: "result")
        registry.set_status("busy_tool", ToolStatus.BUSY)
        
        call = ToolCall(tool_id="busy_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "not available" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_batch_execute(self, registry, executor):
        """测试批量执行"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        call_count = 0
        
        async def handler():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        registry.register(definition, handler)
        
        calls = [
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool")
        ]
        
        results = await executor.batch_execute(calls)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_stats(self, registry, executor):
        """测试执行统计"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        async def handler():
            return "result"
        
        registry.register(definition, handler)
        
        # 执行多次
        for _ in range(5):
            call = ToolCall(tool_id="test_tool")
            await executor.execute(call)
        
        stats = executor.get_stats()
        
        assert stats["total_calls"] == 5
        assert stats["successful_calls"] == 5
        assert stats["failed_calls"] == 0
        assert stats["success_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_execution_logs(self, registry, executor):
        """测试执行日志"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        async def handler():
            return "result"
        
        registry.register(definition, handler)
        
        call = ToolCall(tool_id="test_tool")
        await executor.execute(call, user_id="user1", session_id="session1")
        
        logs = executor.get_execution_logs(tool_id="test_tool")
        
        assert len(logs) == 1
        assert logs[0].tool_id == "test_tool"
        assert logs[0].user_id == "user1"
        assert logs[0].session_id == "session1"
```

### 2.2 集成测试策略

#### 2.2.1 Skill 适配器集成测试 (`test_skill_adapter.py`)

```python
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
    
    @pytest.mark.asyncio
    async def test_skill_handler_execution(self, tool_registry, skill_registry, adapter):
        """测试 Skill 处理函数执行"""
        skill = TestSkill()
        skill_registry.register(skill)
        adapter.register_all_skills()
        
        handler = tool_registry.get_handler("skill_test_skill")
        
        result = await handler(input="hello")
        
        assert result == {"output": "Processed: hello"}
    
    def test_multiple_skills(self, tool_registry, skill_registry, adapter):
        """测试多个 Skill 注册"""
        # 注册多个 Skill
        for i in range(3):
            skill = TestSkill()
            skill._metadata = SkillMetadata(
                name=f"test_skill_{i}",
                description=f"Test skill {i}",
                version="1.0.0",
                tags=["test"],
                intents=[f"intent_{i}"]
            )
            skill_registry.register(skill)
        
        count = adapter.register_all_skills()
        
        assert count == 3
        assert len(tool_registry.list_tools()) == 3
```

#### 2.2.2 API 端点集成测试 (`test_tool_api.py`)

```python
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from tool_system.models import (
    ToolDefinition, ToolType, ToolCategory, ToolParameter
)
from tool_system.registry import ToolRegistry
from tool_system.executor import ToolExecutor
from tool_system.api import create_tool_router


class TestToolAPI:
    """工具 API 测试"""
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    @pytest.fixture
    def executor(self, registry):
        return ToolExecutor(registry=registry)
    
    @pytest.fixture
    def app(self, registry, executor):
        app = FastAPI()
        router = create_tool_router(registry, executor)
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_list_tools_empty(self, client):
        """测试列出空工具列表"""
        response = client.get("/api/tools")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_tools(self, client, registry):
        """测试列出工具"""
        # 注册工具
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            tags=["test"]
        )
        registry.register(definition, lambda: None)
        
        response = client.get("/api/tools")
        
        assert response.status_code == 200
        tools = response.json()
        assert len(tools) == 1
        assert tools[0]["tool_id"] == "test_tool"
    
    def test_get_tool(self, client, registry):
        """测试获取工具详情"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        registry.register(definition, lambda: None)
        
        response = client.get("/api/tools/test_tool")
        
        assert response.status_code == 200
        tool = response.json()
        assert tool["tool_id"] == "test_tool"
        assert tool["name"] == "Test Tool"
    
    def test_get_tool_not_found(self, client):
        """测试获取不存在的工具"""
        response = client.get("/api/tools/nonexistent")
        
        assert response.status_code == 404
    
    def test_search_tools(self, client, registry):
        """测试搜索工具"""
        definition = ToolDefinition(
            tool_id="code_review",
            name="Code Review",
            description="Review code",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CODE,
            tags=["code", "review"]
        )
        registry.register(definition, lambda: None)
        
        response = client.get("/api/tools/search?q=review")
        
        assert response.status_code == 200
        tools = response.json()
        assert len(tools) == 1
        assert tools[0]["tool_id"] == "code_review"
    
    def test_call_tool(self, client, registry):
        """测试调用工具"""
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
        
        response = client.post(
            "/api/tools/call",
            json={
                "tool_id": "test_tool",
                "parameters": {"input": "hello"}
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["output"] == "Processed: hello"
    
    def test_call_tool_not_found(self, client):
        """测试调用不存在的工具"""
        response = client.post(
            "/api/tools/call",
            json={"tool_id": "nonexistent"}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_batch_call(self, client, registry):
        """测试批量调用"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        async def handler():
            return "result"
        
        registry.register(definition, handler)
        
        response = client.post(
            "/api/tools/batch-call",
            json={
                "calls": [
                    {"tool_id": "test_tool"},
                    {"tool_id": "test_tool"},
                    {"tool_id": "test_tool"}
                ]
            }
        )
        
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        assert all(r["success"] for r in results)
    
    def test_get_stats(self, client, executor):
        """测试获取统计信息"""
        response = client.get("/api/tools/stats")
        
        assert response.status_code == 200
        stats = response.json()
        assert "total_calls" in stats
        assert "successful_calls" in stats
        assert "failed_calls" in stats
        assert "success_rate" in stats
```

### 2.3 端到端测试策略

#### 2.3.1 完整流程测试 (`test_tool_e2e.py`)

```python
import pytest
import asyncio
from tool_system.integration import ToolSystemIntegration


class TestToolSystemE2E:
    """工具系统端到端测试"""
    
    @pytest.fixture
    def integration(self):
        return ToolSystemIntegration()
    
    @pytest.mark.asyncio
    async def test_full_initialization(self, integration):
        """测试完整初始化流程"""
        await integration.initialize()
        
        # 验证工具注册
        tools = integration.tool_registry.list_tools()
        assert len(tools) > 0
        
        # 验证 Skill 工具
        skill_tools = [
            t for t in tools 
            if t.tool_type.value == "skill"
        ]
        assert len(skill_tools) > 0
        
        # 验证内置工具
        builtin_tools = [
            t for t in tools 
            if t.metadata.get("builtin")
        ]
        assert len(builtin_tools) > 0
    
    @pytest.mark.asyncio
    async def test_skill_tool_execution(self, integration):
        """测试 Skill 工具执行"""
        await integration.initialize()
        
        # 获取第一个 Skill 工具
        skill_tools = [
            t for t in integration.tool_registry.list_tools()
            if t.tool_type.value == "skill"
        ]
        
        if skill_tools:
            tool = skill_tools[0]
            handler = integration.tool_registry.get_handler(tool.tool_id)
            
            # 执行工具
            result = await handler()
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_builtin_tool_execution(self, integration):
        """测试内置工具执行"""
        await integration.initialize()
        
        # 获取文件读取工具
        file_read_tool = integration.tool_registry.get_tool("builtin_file_read")
        
        if file_read_tool:
            handler = integration.tool_registry.get_handler("builtin_file_read")
            
            # 执行工具
            result = await handler(file_path="README.md")
            
            assert result is not None
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_tool_discovery(self, integration):
        """测试工具发现"""
        await integration.initialize()
        
        # 搜索工具
        code_tools = integration.tool_registry.search_tools("code")
        
        # 应该能找到代码相关工具
        assert len(code_tools) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, integration):
        """测试并发执行"""
        await integration.initialize()
        
        # 获取工具
        tools = integration.tool_registry.list_tools()
        
        if len(tools) >= 3:
            # 创建多个调用
            from tool_system.models import ToolCall
            
            calls = [
                ToolCall(tool_id=tools[0].tool_id),
                ToolCall(tool_id=tools[1].tool_id),
                ToolCall(tool_id=tools[2].tool_id)
            ]
            
            # 批量执行
            results = await integration.tool_executor.batch_execute(calls)
            
            assert len(results) == 3
            # 至少一些应该成功
            successful = [r for r in results if r.success]
            assert len(successful) > 0
```

---

## 三、兼容性处理策略

### 3.1 兼容性设计原则

1. **向后兼容**：现有 Skill 功能完全保留
2. **渐进式迁移**：支持逐步从 Skill 迁移到 Tool
3. **双轨运行**：Skill 和 Tool 系统可以同时运行
4. **无缝切换**：上层调用者无需感知底层变化

### 3.2 兼容性架构

```
┌─────────────────────────────────────────────────────────────┐
│                    上层应用层                                 │
│              (smart_copilot_api.py 等)                       │
├─────────────────────────────────────────────────────────────┤
│                    统一调用接口                               │
│              (tool_system/api.py)                            │
├─────────────────────────────────────────────────────────────┤
│         ┌──────────────────────────────────────┐            │
│         │           工具系统                    │            │
│         │  (ToolRegistry + ToolExecutor)        │            │
│         └──────────────────────────────────────┘            │
│                           ↑                                 │
│                    SkillAdapter                              │
│                           ↑                                 │
│         ┌──────────────────────────────────────┐            │
│         │           Skill 系统                  │            │
│         │  (SkillRegistry + SkillExecutor)      │            │
│         └──────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 兼容性实现细节

#### 3.3.1 Skill 适配器实现

```python
# adapters/skill_adapter.py

class SkillAdapter:
    """Skill 适配器 - 兼容性核心"""
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry
    ):
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
    
    def register_all_skills(self) -> int:
        """注册所有 Skill 为工具"""
        count = 0
        
        for skill_name in self._skill_registry.list_skills():
            skill = self._skill_registry.get_skill(skill_name)
            if skill:
                self._register_skill(skill)
                count += 1
        
        return count
    
    def _register_skill(self, skill: BaseSkill) -> None:
        """注册单个 Skill"""
        metadata = skill.metadata
        
        # 创建工具定义
        definition = self._skill_to_tool_definition(metadata)
        
        # 创建处理函数（保持原有执行逻辑）
        handler = self._create_skill_handler(skill)
        
        # 注册到工具系统
        self._tool_registry.register(definition, handler)
    
    def _create_skill_handler(self, skill: BaseSkill):
        """创建 Skill 处理函数 - 保持原有行为"""
        async def handler(**kwargs) -> Any:
            # 创建 Skill 上下文（与原有逻辑一致）
            context = SkillContext(
                intent=kwargs.get("intent", "execute"),
                input_data=kwargs,
                config=skill.config
            )
            
            # 执行 Skill（使用原有执行逻辑）
            result = await skill.execute(context)
            
            if result.success:
                return result.data
            else:
                raise Exception(result.error or "Skill execution failed")
        
        return handler
```

#### 3.3.2 渐进式迁移支持

```python
# integration.py

class ToolSystemIntegration:
    """工具系统集成器 - 支持渐进式迁移"""
    
    def __init__(self):
        # 创建工具系统
        self.tool_registry = ToolRegistry()
        self.tool_executor = ToolExecutor(registry=self.tool_registry)
        
        # 获取现有 Skill 系统
        self.skill_registry = SkillRegistry()
        self.skill_executor = SkillExecutor(
            registry=self.skill_registry,
            router=IntentRouter()
        )
        
        # 创建适配器
        self.skill_adapter = SkillAdapter(
            tool_registry=self.tool_registry,
            skill_registry=self.skill_registry
        )
    
    async def execute_skill(
        self,
        skill_name: str,
        input_data: Dict[str, Any],
        use_tool_system: bool = True
    ) -> Any:
        """
        执行 Skill - 支持新旧系统切换
        
        Args:
            skill_name: Skill 名称
            input_data: 输入数据
            use_tool_system: 是否使用工具系统（默认 True）
        
        Returns:
            Any: 执行结果
        """
        if use_tool_system:
            # 使用新工具系统
            return await self._execute_via_tool_system(skill_name, input_data)
        else:
            # 使用旧 Skill 系统
            return await self._execute_via_skill_system(skill_name, input_data)
    
    async def _execute_via_tool_system(
        self,
        skill_name: str,
        input_data: Dict[str, Any]
    ) -> Any:
        """通过工具系统执行"""
        tool_id = f"skill_{skill_name}"
        
        call = ToolCall(
            tool_id=tool_id,
            parameters=input_data
        )
        
        result = await self.tool_executor.execute(call)
        
        if result.success:
            return result.output
        else:
            raise Exception(result.error)
    
    async def _execute_via_skill_system(
        self,
        skill_name: str,
        input_data: Dict[str, Any]
    ) -> Any:
        """通过 Skill 系统执行"""
        context = SkillContext(
            intent="execute",
            input_data=input_data
        )
        
        result = await self.skill_executor.execute(
            context=context,
            skill_name=skill_name
        )
        
        if result.success:
            return result.data
        else:
            raise Exception(result.error)
```

### 3.4 兼容性测试用例

```python
# test_compatibility.py

import pytest
from tool_system.integration import ToolSystemIntegration


class TestCompatibility:
    """兼容性测试"""
    
    @pytest.fixture
    def integration(self):
        return ToolSystemIntegration()
    
    @pytest.mark.asyncio
    async def test_skill_execution_compatibility(self, integration):
        """测试 Skill 执行兼容性"""
        # 初始化系统
        await integration.initialize()
        
        # 获取一个 Skill
        skill_names = integration.skill_registry.list_skills()
        
        if skill_names:
            skill_name = skill_names[0]
            input_data = {"test": "data"}
            
            # 通过新系统执行
            result_new = await integration.execute_skill(
                skill_name,
                input_data,
                use_tool_system=True
            )
            
            # 通过旧系统执行
            result_old = await integration.execute_skill(
                skill_name,
                input_data,
                use_tool_system=False
            )
            
            # 结果应该一致
            assert result_new == result_old
    
    @pytest.mark.asyncio
    async def test_tool_system_fallback(self, integration):
        """测试工具系统回退"""
        await integration.initialize()
        
        # 尝试执行不存在的工具
        try:
            result = await integration.execute_skill(
                "nonexistent_skill",
                {},
                use_tool_system=True
            )
            # 应该抛出异常
            assert False, "Should have raised exception"
        except Exception as e:
            assert "not found" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_mixed_execution(self, integration):
        """测试混合执行"""
        await integration.initialize()
        
        skill_names = integration.skill_registry.list_skills()
        
        if len(skill_names) >= 2:
            # 一个通过新系统
            result1 = await integration.execute_skill(
                skill_names[0],
                {"input": "test1"},
                use_tool_system=True
            )
            
            # 另一个通过旧系统
            result2 = await integration.execute_skill(
                skill_names[1],
                {"input": "test2"},
                use_tool_system=False
            )
            
            # 两者都应该成功
            assert result1 is not None
            assert result2 is not None
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, integration):
        """测试性能对比"""
        import time
        
        await integration.initialize()
        
        skill_names = integration.skill_registry.list_skills()
        
        if skill_names:
            skill_name = skill_names[0]
            input_data = {"test": "data"}
            
            # 测试新系统性能
            start_time = time.time()
            for _ in range(10):
                await integration.execute_skill(
                    skill_name,
                    input_data,
                    use_tool_system=True
                )
            new_system_time = time.time() - start_time
            
            # 测试旧系统性能
            start_time = time.time()
            for _ in range(10):
                await integration.execute_skill(
                    skill_name,
                    input_data,
                    use_tool_system=False
                )
            old_system_time = time.time() - start_time
            
            # 新系统不应该显著慢于旧系统
            # 允许 20% 的性能差异
            assert new_system_time < old_system_time * 1.2
```

---

## 四、验证执行计划

### 4.1 验证阶段

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **阶段 1** | 单元测试开发 | 1 天 | test_tool_models.py, test_tool_registry.py, test_tool_executor.py |
| **阶段 2** | 集成测试开发 | 1 天 | test_skill_adapter.py, test_tool_api.py |
| **阶段 3** | 端到端测试开发 | 1 天 | test_tool_e2e.py, test_compatibility.py |
| **阶段 4** | 测试执行与修复 | 2 天 | 测试报告、问题修复 |
| **阶段 5** | 性能优化 | 1 天 | 性能报告、优化建议 |
| **总计** | | **6 天** | |

### 4.2 验证检查清单

#### 功能验证
- [ ] 工具注册、注销功能
- [ ] 工具查询、搜索功能
- [ ] 工具执行（成功、失败、超时）
- [ ] 批量执行功能
- [ ] 参数验证功能
- [ ] 状态管理功能
- [ ] 持久化功能

#### 兼容性验证
- [ ] Skill 自动注册为工具
- [ ] Skill 执行结果一致性
- [ ] 现有 API 兼容性
- [ ] 错误处理兼容性
- [ ] 性能兼容性

#### 集成验证
- [ ] API 端点功能
- [ ] 错误响应格式
- [ ] 并发处理
- [ ] 资源清理

#### 性能验证
- [ ] 单次调用响应时间 < 100ms
- [ ] 批量调用吞吐量
- [ ] 内存使用情况
- [ ] 并发处理能力

### 4.3 验证报告模板

```markdown
# 工具调用模块验证报告

## 1. 测试概览
- 测试日期: YYYY-MM-DD
- 测试环境: 开发环境
- 测试版本: v1.0.0

## 2. 测试结果汇总
| 测试类别 | 用例数 | 通过数 | 失败数 | 通过率 |
|---------|--------|--------|--------|--------|
| 单元测试 | XX | XX | XX | XX% |
| 集成测试 | XX | XX | XX | XX% |
| 端到端测试 | XX | XX | XX | XX% |
| 兼容性测试 | XX | XX | XX | XX% |
| **总计** | XX | XX | XX | XX% |

## 3. 功能验证结果
### 3.1 核心功能
- [x] 工具注册
- [x] 工具执行
- [ ] ...

### 3.2 兼容性功能
- [x] Skill 适配
- [x] 现有 API 兼容
- [ ] ...

## 4. 性能测试结果
- 单次调用平均响应时间: XXms
- 批量调用吞吐量: XX calls/s
- 内存使用: XX MB

## 5. 问题与建议
### 5.1 发现问题
1. [问题描述]
2. [问题描述]

### 5.2 优化建议
1. [建议]
2. [建议]

## 6. 结论
[总体评价和建议]
```

---

## 五、风险与缓解措施

### 5.1 兼容性风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Skill 执行行为变化 | 现有功能异常 | 1. 保持原有执行逻辑<br>2. 充分的兼容性测试 |
| API 响应格式变化 | 上层调用失败 | 1. 保持原有响应格式<br>2. 版本控制 |
| 性能下降 | 用户体验变差 | 1. 性能基准测试<br>2. 优化关键路径 |

### 5.2 验证风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 测试覆盖不全 | 遗留问题 | 1. 代码覆盖率检查<br>2. 边界条件测试 |
| 测试环境差异 | 测试结果不准确 | 1. 统一测试环境<br>2. 真实代码验证 |
| 测试时间不足 | 验证不充分 | 1. 优先核心功能<br>2. 自动化测试 |

---

## 六、总结

### 6.1 验证策略总结

1. **分层验证**：单元测试 → 集成测试 → 端到端测试
2. **真实验证**：不使用 mock，全部真实代码调用
3. **全覆盖验证**：功能、兼容性、性能全覆盖
4. **自动化验证**：所有测试用例可自动化执行

### 6.2 兼容性策略总结

1. **向后兼容**：现有 Skill 功能完全保留
2. **渐进迁移**：支持新旧系统双轨运行
3. **无缝切换**：上层调用者无需感知变化
4. **充分测试**：兼容性测试用例全覆盖

### 6.3 下一步行动

1. **立即开始**：单元测试开发
2. **并行进行**：集成测试和兼容性测试开发
3. **持续集成**：测试自动化执行
4. **迭代优化**：根据测试结果持续优化

---

## 附录：测试文件清单

```
tests/
├── test_tool_models.py           # 数据模型测试
├── test_tool_registry.py         # 注册表测试
├── test_tool_executor.py         # 执行器测试
├── test_skill_adapter.py         # Skill 适配器测试
├── test_tool_api.py              # API 端点测试
├── test_tool_e2e.py              # 端到端测试
└── test_compatibility.py         # 兼容性测试
```

---

## 参考文档

- [Tool_System_Design.md](./Tool_System_Design.md) - 工具系统设计文档
- [Agent_Core_Modules_Design.md](./Agent_Core_Modules_Design.md) - 核心模块设计
- [skill_architecture/](./skill_architecture/) - 现有 Skill 架构
