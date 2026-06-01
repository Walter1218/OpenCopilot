# tests/tool_system/test_tool_executor.py

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
        return ToolRegistry()
    
    @pytest.fixture
    def executor(self, registry):
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
    async def test_execute_with_custom_call_id(self, registry, executor):
        """测试自定义调用 ID"""
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
        
        call = ToolCall(
            tool_id="test_tool",
            call_id="custom_call_id"
        )
        
        result = await executor.execute(call)
        
        assert result.tool_call_id == "custom_call_id"
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, executor):
        """测试工具不存在"""
        call = ToolCall(tool_id="nonexistent_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_no_handler(self, registry, executor):
        """测试没有处理函数"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        # 只注册定义，不注册处理函数
        registry._tools["test_tool"] = definition
        
        call = ToolCall(tool_id="test_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "no handler" in result.error.lower()
    
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
    async def test_execute_custom_timeout(self, registry, executor):
        """测试自定义超时"""
        definition = ToolDefinition(
            tool_id="slow_tool",
            name="Slow Tool",
            description="A slow tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            timeout=10.0  # 默认 10 秒
        )
        
        async def handler():
            await asyncio.sleep(0.5)  # 500ms 延迟
            return "done"
        
        registry.register(definition, handler)
        
        # 使用自定义超时
        call = ToolCall(
            tool_id="slow_tool",
            timeout=0.1  # 100ms 超时
        )
        
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
    async def test_execute_tool_disabled(self, registry, executor):
        """测试工具禁用"""
        definition = ToolDefinition(
            tool_id="disabled_tool",
            name="Disabled Tool",
            description="A disabled tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        registry.register(definition, lambda: "result")
        registry.set_status("disabled_tool", ToolStatus.DISABLED)
        
        call = ToolCall(tool_id="disabled_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "not available" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_sync_handler(self, registry, executor):
        """测试同步处理函数"""
        definition = ToolDefinition(
            tool_id="sync_tool",
            name="Sync Tool",
            description="A sync tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        def handler():
            return "sync result"
        
        registry.register(definition, handler)
        
        call = ToolCall(tool_id="sync_tool")
        
        result = await executor.execute(call)
        
        assert result.success is True
        assert result.output == "sync result"
    
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
    async def test_batch_execute_with_failures(self, registry, executor):
        """测试批量执行中的失败"""
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
            if call_count == 2:
                raise ValueError("Error on second call")
            return f"result_{call_count}"
        
        registry.register(definition, handler)
        
        calls = [
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool")
        ]
        
        results = await executor.batch_execute(calls)
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
    
    @pytest.mark.asyncio
    async def test_batch_execute_empty(self, executor):
        """测试空批量执行"""
        results = await executor.batch_execute([])
        
        assert len(results) == 0
    
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
        assert stats["avg_duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_execute_stats_with_failures(self, registry, executor):
        """测试包含失败的执行统计"""
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
            if call_count % 2 == 0:
                raise ValueError("Error")
            return "result"
        
        registry.register(definition, handler)
        
        # 执行多次
        for _ in range(10):
            call = ToolCall(tool_id="test_tool")
            await executor.execute(call)
        
        stats = executor.get_stats()
        
        assert stats["total_calls"] == 10
        assert stats["successful_calls"] == 5
        assert stats["failed_calls"] == 5
        assert stats["success_rate"] == 0.5
    
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
        assert logs[0].result.success is True
    
    @pytest.mark.asyncio
    async def test_execution_logs_limit(self, registry, executor):
        """测试执行日志限制"""
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
        for _ in range(1500):
            call = ToolCall(tool_id="test_tool")
            await executor.execute(call)
        
        logs = executor.get_execution_logs()
        
        # 日志应该被限制
        assert len(logs) <= 1000
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, registry, executor):
        """测试并发执行"""
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        async def handler():
            await asyncio.sleep(0.1)  # 100ms 延迟
            return "result"
        
        registry.register(definition, handler)
        
        # 创建多个并发调用
        calls = [ToolCall(tool_id="test_tool") for _ in range(5)]
        
        # 并发执行
        start_time = asyncio.get_event_loop().time()
        results = await executor.batch_execute(calls, max_concurrent=5)
        end_time = asyncio.get_event_loop().time()
        
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # 并发执行应该比串行快
        # 串行需要 500ms，并发应该接近 100ms
        execution_time = end_time - start_time
        assert execution_time < 0.3  # 300ms 内完成
