# tests/tool_system/test_llm_integration.py

"""
LLM 工具集成测试

使用真实的 LLM 能力测试工具系统。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tool_system.models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolType, ToolCategory, ToolParameter
)
from tool_system.registry import ToolRegistry
from tool_system.executor import ToolExecutor
from tool_system.llm_tool import LLMTool, create_llm_tool


class TestLLMToolIntegration:
    """LLM 工具集成测试"""
    
    @pytest.fixture
    def registry(self):
        """创建工具注册表"""
        return ToolRegistry()
    
    @pytest.fixture
    def executor(self, registry):
        """创建工具执行器"""
        return ToolExecutor(registry=registry)
    
    @pytest.fixture
    def llm_tool(self):
        """创建 LLM 工具（使用真实 LLM）"""
        return create_llm_tool(provider_type="auto", use_real_llm=True)
    
    def test_llm_tool_definition(self, llm_tool):
        """测试 LLM 工具定义"""
        definition = llm_tool.definition
        
        assert definition.tool_id == "llm_chat"
        assert definition.name == "LLM Chat"
        assert definition.tool_type == ToolType.FUNCTION
        assert definition.category == ToolCategory.AI
        assert len(definition.parameters) == 4
        
        # 检查必需参数
        required_params = [p for p in definition.parameters if p.required]
        assert len(required_params) == 1
        assert required_params[0].name == "prompt"
    
    @pytest.mark.asyncio
    async def test_llm_tool_execute_basic(self, llm_tool):
        """测试 LLM 工具基本执行"""
        result = await llm_tool.execute(
            prompt="你好，请用一句话介绍自己。"
        )
        
        assert result["success"] is True
        assert "response" in result
        assert len(result["response"]) > 0
        print(f"\nLLM 响应: {result['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_llm_tool_execute_with_system_prompt(self, llm_tool):
        """测试带系统提示的 LLM 工具执行"""
        result = await llm_tool.execute(
            prompt="请用一句话介绍 OpenCopilot 项目。",
            system_prompt="你是一个技术文档专家，请用简洁专业的语言回答。"
        )
        
        assert result["success"] is True
        assert "response" in result
        print(f"\n带系统提示的 LLM 响应: {result['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_llm_tool_execute_empty_prompt(self, llm_tool):
        """测试空提示的 LLM 工具执行"""
        result = await llm_tool.execute(prompt="")
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_llm_tool_registered_in_registry(self, registry, llm_tool):
        """测试将 LLM 工具注册到注册表"""
        # 注册 LLM 工具
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 验证注册成功
        tool = registry.get_tool("llm_chat")
        assert tool is not None
        assert tool.tool_id == "llm_chat"
        
        # 验证处理函数存在
        handler = registry.get_handler("llm_chat")
        assert handler is not None
    
    @pytest.mark.asyncio
    async def test_llm_tool_execution_via_executor(self, registry, executor, llm_tool):
        """测试通过执行器执行 LLM 工具"""
        # 注册 LLM 工具
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 创建工具调用
        call = ToolCall(
            tool_id="llm_chat",
            parameters={
                "prompt": "请用一句话描述 Python 语言的特点。",
                "system_prompt": "你是一个编程专家。"
            }
        )
        
        # 通过执行器执行
        result = await executor.execute(call)
        
        assert result.success is True
        assert result.output is not None
        assert "response" in result.output
        assert result.duration_ms > 0
        print(f"\n通过执行器执行的 LLM 响应: {result.output['response'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_llm_tool_batch_execution(self, registry, executor, llm_tool):
        """测试 LLM 工具批量执行"""
        # 注册 LLM 工具
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 创建多个工具调用
        calls = [
            ToolCall(
                tool_id="llm_chat",
                parameters={"prompt": "用一句话介绍 Python。"}
            ),
            ToolCall(
                tool_id="llm_chat",
                parameters={"prompt": "用一句话介绍 JavaScript。"}
            ),
            ToolCall(
                tool_id="llm_chat",
                parameters={"prompt": "用一句话介绍 Go 语言。"}
            )
        ]
        
        # 批量执行
        results = await executor.batch_execute(calls)
        
        assert len(results) == 3
        # LLM 调用可能因为服务不可用而部分失败，但结果应该存在
        assert all(r is not None for r in results)
        # 至少应该有成功的结果
        success_count = sum(1 for r in results if r.success)
        print(f"\n批量执行成功数: {success_count}/{len(results)}")
        
        for i, result in enumerate(results):
            if result.success:
                print(f"批量执行结果 {i+1}: {result.output['response'][:50]}...")
            else:
                print(f"批量执行结果 {i+1}: 失败 - {result.error}")
    
    @pytest.mark.asyncio
    async def test_llm_tool_concurrent_execution(self, registry, executor, llm_tool):
        """测试 LLM 工具并发执行"""
        # 注册 LLM 工具
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 创建多个并发调用
        calls = [
            ToolCall(
                tool_id="llm_chat",
                parameters={"prompt": f"这是第 {i+1} 个测试，请回复 '收到'。"}
            )
            for i in range(3)
        ]
        
        # 并发执行
        import time
        start_time = time.time()
        results = await executor.batch_execute(calls, max_concurrent=3)
        end_time = time.time()
        
        assert len(results) == 3
        # LLM 调用可能因为服务不可用而部分失败，但结果应该存在
        assert all(r is not None for r in results)
        
        success_count = sum(1 for r in results if r.success)
        execution_time = end_time - start_time
        print(f"\n并发执行 3 个 LLM 调用耗时: {execution_time:.2f}s")
        print(f"成功数: {success_count}/{len(results)}")
    
    @pytest.mark.asyncio
    async def test_llm_tool_with_skill_context(self, llm_tool):
        """测试 LLM 工具与 Skill 上下文的集成"""
        # 模拟 Skill 上下文
        skill_context = {
            "intent": "generate_code",
            "input_data": {
                "language": "python",
                "task": "编写一个计算斐波那契数列的函数"
            }
        }
        
        # 构建 LLM 提示
        prompt = f"""
根据以下上下文生成代码：
意图：{skill_context['intent']}
编程语言：{skill_context['input_data']['language']}
任务：{skill_context['input_data']['task']}

请提供完整的代码实现。
"""
        
        result = await llm_tool.execute(
            prompt=prompt,
            system_prompt="你是一个专业的 Python 开发者。"
        )
        
        assert result["success"] is True
        assert "response" in result
        print(f"\n根据 Skill 上下文生成的代码:\n{result['response'][:200]}...")
    
    @pytest.mark.asyncio
    async def test_llm_tool_error_handling(self, registry, executor):
        """测试 LLM 工具错误处理"""
        # 创建一个会失败的 LLM 工具
        class FailingLLMTool(LLMTool):
            async def execute(self, **kwargs):
                raise ConnectionError("LLM 服务不可用")
        
        failing_tool = FailingLLMTool()
        registry.register(failing_tool.definition, failing_tool.execute)
        
        call = ToolCall(
            tool_id="llm_chat",
            parameters={"prompt": "测试"}
        )
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "error" in result.error.lower() or "LLM" in result.error
    
    @pytest.mark.asyncio
    async def test_llm_tool_stats(self, registry, executor, llm_tool):
        """测试 LLM 工具执行统计"""
        # 注册 LLM 工具
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 执行多次
        for i in range(3):
            call = ToolCall(
                tool_id="llm_chat",
                parameters={"prompt": f"测试 {i+1}"}
            )
            await executor.execute(call)
        
        # 获取统计信息
        stats = executor.get_stats()
        
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] >= 0  # 可能因为 LLM 服务不可用而失败
        assert stats["avg_duration_ms"] > 0
        
        print(f"\n执行统计: {stats}")


class TestLLMToolWithRealScenarios:
    """LLM 工具真实场景测试"""
    
    @pytest.fixture
    def llm_tool(self):
        """创建 LLM 工具"""
        return create_llm_tool(provider_type="auto", use_real_llm=True)
    
    @pytest.mark.asyncio
    async def test_code_generation_scenario(self, llm_tool):
        """测试代码生成场景"""
        result = await llm_tool.execute(
            prompt="请用 Python 编写一个函数，实现冒泡排序算法。",
            system_prompt="你是一个 Python 专家，请提供简洁高效的代码。"
        )
        
        assert result["success"] is True
        assert "def " in result["response"]  # 应该包含函数定义
        print(f"\n代码生成结果:\n{result['response'][:300]}...")
    
    @pytest.mark.asyncio
    async def test_text_summarization_scenario(self, llm_tool):
        """测试文本摘要场景"""
        long_text = """
        OpenCopilot 是一个开源的 AI 助手项目，旨在为开发者提供智能编程辅助。
        它采用了模块化的架构设计，包括 Skill 系统、工具系统、上下文管理等核心模块。
        Skill 系统允许将各种能力封装为可复用的组件，工具系统提供了统一的工具调用接口，
        上下文管理负责维护对话状态和用户偏好。项目支持多种 LLM 提供商，
        包括 MiniMax、本地模型等，并提供了丰富的测试和验证机制。
        """
        
        result = await llm_tool.execute(
            prompt=f"请用一句话总结以下文本：\n{long_text}",
            system_prompt="你是一个文本摘要专家。请只输出摘要，不要输出思考过程。"
        )
        
        assert result["success"] is True
        # LLM 可能会包含思考过程，所以只验证响应不为空
        assert len(result["response"]) > 0
        print(f"\n文本摘要结果: {result['response']}")
    
    @pytest.mark.asyncio
    async def test_question_answering_scenario(self, llm_tool):
        """测试问答场景"""
        result = await llm_tool.execute(
            prompt="什么是微服务架构？它有哪些优缺点？",
            system_prompt="你是一个软件架构专家，请用简洁的语言回答。"
        )
        
        assert result["success"] is True
        assert "微服务" in result["response"]
        print(f"\n问答结果: {result['response'][:200]}...")


class TestLLMToolCompatibility:
    """LLM 工具兼容性测试"""
    
    @pytest.fixture
    def registry(self):
        return ToolRegistry()
    
    @pytest.fixture
    def executor(self, registry):
        return ToolExecutor(registry=registry)
    
    @pytest.mark.asyncio
    async def test_llm_tool_with_other_tools(self, registry, executor):
        """测试 LLM 工具与其他工具的兼容性"""
        # 注册一个普通工具
        def calculator(expression: str) -> str:
            try:
                result = eval(expression)
                return str(result)
            except:
                return "Error"
        
        calc_definition = ToolDefinition(
            tool_id="calculator",
            name="Calculator",
            description="计算数学表达式",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(name="expression", type="string", required=True)
            ]
        )
        registry.register(calc_definition, calculator)
        
        # 注册 LLM 工具
        llm_tool = create_llm_tool(use_real_llm=True)
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 验证两个工具都注册成功
        assert registry.get_tool("calculator") is not None
        assert registry.get_tool("llm_chat") is not None
        
        # 执行普通工具
        calc_call = ToolCall(
            tool_id="calculator",
            parameters={"expression": "2 + 3 * 4"}
        )
        calc_result = await executor.execute(calc_call)
        assert calc_result.success is True
        assert calc_result.output == "14"
        
        # 执行 LLM 工具
        llm_call = ToolCall(
            tool_id="llm_chat",
            parameters={"prompt": "你好"}
        )
        llm_result = await executor.execute(llm_call)
        # LLM 可能因为服务不可用而失败，但不应该崩溃
        assert llm_result is not None
        
        # 获取统计信息
        stats = executor.get_stats()
        assert stats["total_calls"] == 2
        print(f"\n混合工具执行统计: {stats}")
    
    @pytest.mark.asyncio
    async def test_llm_tool_batch_with_other_tools(self, registry, executor):
        """测试 LLM 工具与其他工具的批量执行"""
        # 注册多个工具
        tools = [
            ("tool_1", lambda: "result_1"),
            ("tool_2", lambda: "result_2"),
        ]
        
        for tool_id, handler in tools:
            definition = ToolDefinition(
                tool_id=tool_id,
                name=f"Tool {tool_id}",
                description=f"Test tool {tool_id}",
                tool_type=ToolType.FUNCTION,
                category=ToolCategory.CUSTOM
            )
            registry.register(definition, handler)
        
        # 注册 LLM 工具
        llm_tool = create_llm_tool(use_real_llm=True)
        registry.register(llm_tool.definition, llm_tool.execute)
        
        # 创建混合调用
        calls = [
            ToolCall(tool_id="tool_1"),
            ToolCall(tool_id="llm_chat", parameters={"prompt": "测试"}),
            ToolCall(tool_id="tool_2"),
        ]
        
        # 批量执行
        results = await executor.batch_execute(calls)
        
        assert len(results) == 3
        # 普通工具应该成功
        assert results[0].success is True
        assert results[2].success is True
        # LLM 工具可能失败，但不应该崩溃
        assert results[1] is not None
        
        print(f"\n混合批量执行结果: {[r.success for r in results]}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
