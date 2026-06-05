# code_executor/handlers/python_handler.py

"""
Python 语言处理器
"""

import asyncio
import sys
import os
import tempfile
import shutil
from typing import Dict, List, Optional, Any
import ast

from .base import LanguageHandler
from ..models import (
    ExecutionResult, ValidationResult, LanguageInfo,
    SandboxConfig, ExecutionStatus, generate_execution_id
)


class PythonHandler(LanguageHandler):
    """Python 语言处理器
    
    支持执行 Python 代码，包括语法检查、安全验证等功能。
    """
    
    def __init__(self, python_executable: Optional[str] = None):
        """
        初始化 Python 处理器
        
        Args:
            python_executable: Python 可执行文件路径，默认使用当前 Python
        """
        super().__init__()
        self.python_executable = python_executable or sys.executable
        self._version: Optional[str] = None
    
    @property
    def language(self) -> str:
        """返回语言名称"""
        return "python"
    
    @property
    def file_extension(self) -> str:
        """返回文件扩展名"""
        return ".py"
    
    async def execute(
        self,
        code: str,
        timeout: float = 30.0,
        working_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
        sandbox_config: Optional[SandboxConfig] = None
    ) -> ExecutionResult:
        """执行 Python 代码
        
        Args:
            code: 要执行的 Python 代码
            timeout: 超时时间（秒）
            working_directory: 工作目录
            env_vars: 环境变量
            input_data: 标准输入数据
            sandbox_config: 沙盒配置
            
        Returns:
            ExecutionResult: 执行结果
        """
        import time
        start_time = time.time()
        execution_id = generate_execution_id()
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp(prefix="opencopilot_python_")
        temp_file = os.path.join(temp_dir, "script.py")
        
        try:
            # 写入代码到临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 准备环境变量
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # 设置工作目录
            cwd = working_directory or temp_dir
            
            # 构建命令
            cmd = [self.python_executable, temp_file]
            
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else asyncio.subprocess.DEVNULL,
                cwd=cwd,
                env=env
            )
            
            # 发送输入数据并等待完成
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(
                        input=input_data.encode('utf-8') if input_data else None
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # 超时，终止进程
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                duration_ms = (time.time() - start_time) * 1000
                return self._create_timeout_result(
                    request_id="",
                    timeout=timeout,
                    duration_ms=duration_ms
                )
            
            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 解码输出
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            # 截断输出
            stdout_str = self._truncate_output(stdout_str)
            stderr_str = self._truncate_output(stderr_str)
            
            # 检查执行结果
            success = process.returncode == 0
            
            return ExecutionResult(
                execution_id=execution_id,
                request_id="",
                success=success,
                status=ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode,
                duration_ms=duration_ms,
                language=self.language
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return self._create_error_result(
                request_id="",
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration_ms
            )
        
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
    
    async def validate(self, code: str) -> ValidationResult:
        """验证 Python 代码
        
        Args:
            code: 要验证的 Python 代码
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        suggestions = []
        syntax_valid = True
        security_issues = []
        
        # 1. 语法检查
        try:
            ast.parse(code)
        except SyntaxError as e:
            syntax_valid = False
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        
        # 2. 安全检查
        security_issues = self._check_security(code)
        
        # 3. 代码质量检查
        quality_warnings = self._check_quality(code)
        warnings.extend(quality_warnings)
        
        # 4. 生成建议
        suggestions = self._generate_suggestions(code)
        
        return ValidationResult(
            valid=len(errors) == 0 and len(security_issues) == 0,
            language=self.language,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            syntax_valid=syntax_valid,
            security_issues=security_issues
        )
    
    async def check_availability(self) -> LanguageInfo:
        """检查 Python 是否可用
        
        Returns:
            LanguageInfo: Python 语言信息
        """
        try:
            # 获取 Python 版本
            process = await asyncio.create_subprocess_exec(
                self.python_executable, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode('utf-8').strip()
                # 提取版本号
                if version.startswith("Python "):
                    version = version[7:]
                
                self._version = version
                
                return LanguageInfo(
                    language=self.language,
                    version=version,
                    available=True,
                    executable=self.python_executable,
                    file_extension=self.file_extension,
                    syntax_check_cmd=f"{self.python_executable} -m py_compile",
                    package_manager="pip"
                )
            else:
                return LanguageInfo(
                    language=self.language,
                    version="unknown",
                    available=False,
                    executable=self.python_executable,
                    file_extension=self.file_extension
                )
                
        except Exception as e:
            return LanguageInfo(
                language=self.language,
                version="unknown",
                available=False,
                executable=self.python_executable,
                file_extension=self.file_extension
            )
    
    def _check_security(self, code: str) -> List[str]:
        """检查代码安全性
        
        Args:
            code: 要检查的代码
            
        Returns:
            List[str]: 安全问题列表
        """
        issues = []
        
        # 危险的内置函数
        dangerous_functions = [
            'eval', 'exec', 'compile', '__import__',
            'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr',
            'open', 'file', 'input', 'raw_input'
        ]
        
        # 危险的模块
        dangerous_modules = [
            'os', 'sys', 'subprocess', 'shutil',
            'socket', 'http', 'urllib', 'requests',
            'ctypes', 'signal', 'multiprocessing',
            'threading', 'asyncio'
        ]
        
        # 检查危险函数
        for func in dangerous_functions:
            if func in code:
                # 检查是否在字符串中
                if not self._is_in_string(code, func):
                    issues.append(f"Use of potentially dangerous function: {func}")
        
        # 检查危险模块导入
        for module in dangerous_modules:
            if f"import {module}" in code or f"from {module}" in code:
                issues.append(f"Import of potentially dangerous module: {module}")
        
        # 检查文件操作
        if "open(" in code and "with open" not in code:
            issues.append("File operation without context manager (with statement)")
        
        # 检查网络操作
        network_patterns = ['requests.', 'urllib.', 'http.client', 'socket.']
        for pattern in network_patterns:
            if pattern in code:
                issues.append(f"Network operation detected: {pattern}")
        
        return issues
    
    def _check_quality(self, code: str) -> List[str]:
        """检查代码质量
        
        Args:
            code: 要检查的代码
            
        Returns:
            List[str]: 警告列表
        """
        warnings = []
        
        lines = code.split('\n')
        
        # 检查行数
        if len(lines) > 1000:
            warnings.append(f"Code is very long ({len(lines)} lines)")
        
        # 检查行长度
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                warnings.append(f"Line {i} is too long ({len(line)} chars)")
        
        # 检查未使用的导入
        if "import " in code:
            warnings.append("Consider checking for unused imports")
        
        # 检查 print 语句
        if "print(" in code:
            warnings.append("Code contains print statements")
        
        return warnings
    
    def _generate_suggestions(self, code: str) -> List[str]:
        """生成代码建议
        
        Args:
            code: 要分析的代码
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        # 检查是否有类型注解
        if "def " in code and "->" not in code:
            suggestions.append("Consider adding type hints to functions")
        
        # 检查是否有文档字符串
        if "def " in code and '"""' not in code and "'''" not in code:
            suggestions.append("Consider adding docstrings to functions")
        
        # 检查是否有异常处理
        if "try:" not in code and ("open(" in code or "requests." in code):
            suggestions.append("Consider adding error handling for I/O operations")
        
        return suggestions
    
    def _is_in_string(self, code: str, word: str) -> bool:
        """检查单词是否在字符串中
        
        Args:
            code: 代码内容
            word: 要检查的单词
            
        Returns:
            bool: 是否在字符串中
        """
        # 简单的检查，实际应该使用 AST
        import re
        # 查找所有字符串
        strings = re.findall(r'["\'].*?["\']', code)
        for s in strings:
            if word in s:
                return True
        return False
