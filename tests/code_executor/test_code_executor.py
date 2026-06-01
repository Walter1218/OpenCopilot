# tests/code_executor/test_code_executor.py

"""
代码执行引擎测试

使用真实代码执行测试代码执行引擎功能。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入代码执行引擎模块
try:
    from code_executor.models import (
        ExecutorConfig, SandboxConfig, ExecutionResult, ValidationResult,
        LanguageInfo, ExecutionStatus, generate_execution_id
    )
    from code_executor.core import CodeExecutor
    from code_executor.sandbox import SandboxManager
    from code_executor.handlers.python_handler import PythonHandler
    from code_executor.handlers.javascript_handler import JavaScriptHandler
    from code_executor.handlers.shell_handler import ShellHandler
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Python path: {sys.path}")
    raise


@pytest.fixture
def executor():
    """创建代码执行引擎实例"""
    config = ExecutorConfig(
        default_timeout=10.0,
        max_timeout=30.0,
        enable_sandbox=False  # 测试时禁用沙盒
    )
    return CodeExecutor(config=config)


@pytest.fixture
def sandbox_manager():
    """创建沙盒管理器实例"""
    return SandboxManager()


class TestModels:
    """数据模型测试"""
    
    def test_generate_execution_id(self):
        """测试生成执行 ID"""
        id1 = generate_execution_id()
        id2 = generate_execution_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_executor_config(self):
        """测试执行器配置"""
        config = ExecutorConfig()
        
        assert config.default_timeout == 30.0
        assert config.max_timeout == 300.0
        assert config.max_memory_mb == 512
        assert config.enable_sandbox is True
    
    def test_sandbox_config(self):
        """测试沙盒配置"""
        config = SandboxConfig()
        
        assert config.max_memory_mb == 512
        assert config.max_cpu_percent == 100.0
        assert config.allow_network is False


class TestPythonHandler:
    """Python 处理器测试"""
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self, executor):
        """测试简单代码执行"""
        code = """
print("Hello, World!")
x = 1 + 2
print(f"1 + 2 = {x}")
"""
        result = await executor.execute_code(code, "python")
        
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert "1 + 2 = 3" in result.stdout
        assert result.exit_code == 0
        assert result.language == "python"
    
    @pytest.mark.asyncio
    async def test_code_with_error(self, executor):
        """测试有错误的代码"""
        code = """
print("Before error")
raise ValueError("Test error")
print("After error")
"""
        result = await executor.execute_code(code, "python")
        
        assert result.success is False
        assert "Before error" in result.stdout
        assert "ValueError: Test error" in result.stderr
        assert result.exit_code != 0
    
    @pytest.mark.asyncio
    async def test_code_with_input(self, executor):
        """测试带输入的代码"""
        code = """
name = input()
print(f"Hello, {name}!")
"""
        result = await executor.execute_code(code, "python", input_data="Alice")
        
        assert result.success is True
        assert "Hello, Alice!" in result.stdout
    
    @pytest.mark.asyncio
    async def test_code_validation(self, executor):
        """测试代码验证"""
        # 有效代码
        valid_code = "print('Hello')"
        result = await executor.validate_code(valid_code, "python")
        
        assert result.valid is True
        assert result.syntax_valid is True
        
        # 无效代码
        invalid_code = "print('Hello'"
        result = await executor.validate_code(invalid_code, "python")
        
        assert result.valid is False
        assert result.syntax_valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_security_check(self, executor):
        """测试安全检查"""
        code = """
import os
os.system("rm -rf /")
"""
        result = await executor.validate_code(code, "python")
        
        assert len(result.security_issues) > 0


class TestJavaScriptHandler:
    """JavaScript 处理器测试"""
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self, executor):
        """测试简单代码执行"""
        code = """
console.log("Hello, World!");
const x = 1 + 2;
console.log(`1 + 2 = ${x}`);
"""
        result = await executor.execute_code(code, "javascript")
        
        # 检查 Node.js 是否可用
        if result.success:
            assert "Hello, World!" in result.stdout
            assert "1 + 2 = 3" in result.stdout
        else:
            # Node.js 可能未安装
            assert "not available" in result.error.lower() or "not found" in result.error.lower()


class TestShellHandler:
    """Shell 处理器测试"""
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self, executor):
        """测试简单代码执行"""
        code = """
#!/bin/bash
echo "Hello, World!"
x=$((1 + 2))
echo "1 + 2 = $x"
"""
        result = await executor.execute_code(code, "bash")
        
        assert result.success is True
        assert "Hello, World!" in result.stdout
        assert "1 + 2 = 3" in result.stdout


class TestSandboxManager:
    """沙盒管理器测试"""
    
    @pytest.mark.asyncio
    async def test_create_and_destroy_sandbox(self, sandbox_manager):
        """测试创建和销毁沙盒"""
        # 创建沙盒
        sandbox_id = await sandbox_manager.create_sandbox()
        
        assert sandbox_id is not None
        assert sandbox_id in await sandbox_manager.list_sandboxes()
        
        # 获取沙盒路径
        path = await sandbox_manager.get_sandbox_path(sandbox_id)
        
        assert path is not None
        assert os.path.exists(path)
        
        # 销毁沙盒
        success = await sandbox_manager.destroy_sandbox(sandbox_id)
        
        assert success is True
        assert sandbox_id not in await sandbox_manager.list_sandboxes()
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, sandbox_manager):
        """测试资源限制"""
        limits = sandbox_manager.get_resource_limits()
        
        assert "max_memory_mb" in limits
        assert "max_cpu_percent" in limits
        assert "timeout" in limits
    
    @pytest.mark.asyncio
    async def test_cleanup_all(self, sandbox_manager):
        """测试清理所有沙盒"""
        # 创建多个沙盒
        sandbox1 = await sandbox_manager.create_sandbox()
        sandbox2 = await sandbox_manager.create_sandbox()
        
        assert len(await sandbox_manager.list_sandboxes()) == 2
        
        # 清理所有沙盒
        count = await sandbox_manager.cleanup_all()
        
        assert count == 2
        assert len(await sandbox_manager.list_sandboxes()) == 0


class TestCodeExecutor:
    """代码执行引擎测试"""
    
    @pytest.mark.asyncio
    async def test_get_supported_languages(self, executor):
        """测试获取支持的语言"""
        languages = await executor.get_supported_languages()
        
        assert len(languages) > 0
        
        # 检查 Python 是否可用
        python_lang = next((l for l in languages if l.language == "python"), None)
        assert python_lang is not None
        assert python_lang.available is True
    
    @pytest.mark.asyncio
    async def test_get_status(self, executor):
        """测试获取状态"""
        status = await executor.get_status()
        
        assert status["status"] == "ready"
        assert "config" in status
        assert "supported_languages" in status
        assert "stats" in status
    
    @pytest.mark.asyncio
    async def test_get_stats(self, executor):
        """测试获取统计信息"""
        # 执行一些代码
        await executor.execute_code("print('test')", "python")
        
        stats = executor.get_stats()
        
        assert stats["total_executions"] > 0
        assert stats["successful_executions"] > 0
    
    @pytest.mark.asyncio
    async def test_execution_logs(self, executor):
        """测试执行日志"""
        # 执行代码
        await executor.execute_code("print('test')", "python")
        
        logs = executor.get_execution_logs()
        
        assert len(logs) > 0
        assert logs[0].language == "python"
    
    @pytest.mark.asyncio
    async def test_unsupported_language(self, executor):
        """测试不支持的语言"""
        result = await executor.execute_code("print('test')", "unknown_language")
        
        assert result.success is False
        assert "Unsupported language" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
