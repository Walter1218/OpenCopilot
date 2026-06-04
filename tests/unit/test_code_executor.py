"""
代码执行器模块测试
"""
import pytest
import os



class TestExecutorConfig:
    """执行器配置"""

    def test_default(self):
        from opencopilot.capabilities.coding import ExecutorConfig
        c = ExecutorConfig()
        assert c.default_timeout > 0
        assert c.max_memory_mb > 0
        assert c.enable_sandbox is True

    def test_custom(self):
        from opencopilot.capabilities.coding import ExecutorConfig
        c = ExecutorConfig(
            default_timeout=10.0,
            max_memory_mb=256,
            enable_sandbox=False,
        )
        assert c.default_timeout == 10.0
        assert c.enable_sandbox is False


class TestCodeExecutor:
    """代码执行器"""

    @pytest.fixture
    def executor(self):
        from opencopilot.capabilities.coding import CodeExecutor, ExecutorConfig
        config = ExecutorConfig(default_timeout=5.0, max_memory_mb=128)
        return CodeExecutor(config=config)

    def test_init(self, executor):
        assert executor is not None
        assert executor.config.default_timeout == 5.0

    @pytest.mark.asyncio
    async def test_validate_code_valid(self, executor):
        result = await executor.validate_code("print('hello')", "python")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_get_supported_languages(self, executor):
        langs = await executor.get_supported_languages()
        assert isinstance(langs, list)
        assert len(langs) > 0
