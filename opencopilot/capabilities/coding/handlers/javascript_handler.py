# code_executor/handlers/javascript_handler.py

"""
JavaScript 语言处理器
"""

import asyncio
import os
import tempfile
import shutil
import json
from typing import Dict, List, Optional, Any

from .base import LanguageHandler
from ..models import (
    ExecutionResult, ValidationResult, LanguageInfo,
    SandboxConfig, ExecutionStatus, generate_execution_id
)


class JavaScriptHandler(LanguageHandler):
    """JavaScript 语言处理器
    
    支持执行 JavaScript 代码（Node.js）。
    """
    
    def __init__(self, node_executable: Optional[str] = None):
        """
        初始化 JavaScript 处理器
        
        Args:
            node_executable: Node.js 可执行文件路径
        """
        super().__init__()
        self.node_executable = node_executable or "node"
        self._version: Optional[str] = None
    
    @property
    def language(self) -> str:
        """返回语言名称"""
        return "javascript"
    
    @property
    def file_extension(self) -> str:
        """返回文件扩展名"""
        return ".js"
    
    async def execute(
        self,
        code: str,
        timeout: float = 30.0,
        working_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
        sandbox_config: Optional[SandboxConfig] = None
    ) -> ExecutionResult:
        """执行 JavaScript 代码
        
        Args:
            code: 要执行的 JavaScript 代码
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
        temp_dir = tempfile.mkdtemp(prefix="opencopilot_js_")
        temp_file = os.path.join(temp_dir, "script.js")
        
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
            cmd = [self.node_executable, temp_file]
            
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
        """验证 JavaScript 代码
        
        Args:
            code: 要验证的 JavaScript 代码
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        suggestions = []
        syntax_valid = True
        security_issues = []
        
        # 1. 基本语法检查
        # 使用 Node.js 的 --check 选项
        temp_dir = tempfile.mkdtemp(prefix="opencopilot_js_validate_")
        temp_file = os.path.join(temp_dir, "check.js")
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            process = await asyncio.create_subprocess_exec(
                self.node_executable, "--check", temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                syntax_valid = False
                error_msg = stderr.decode('utf-8', errors='replace')
                errors.append(f"Syntax error: {error_msg}")
                
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
        
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
        """检查 Node.js 是否可用
        
        Returns:
            LanguageInfo: JavaScript 语言信息
        """
        try:
            # 获取 Node.js 版本
            process = await asyncio.create_subprocess_exec(
                self.node_executable, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode('utf-8').strip()
                # 移除 'v' 前缀
                if version.startswith('v'):
                    version = version[1:]
                
                self._version = version
                
                return LanguageInfo(
                    language=self.language,
                    version=version,
                    available=True,
                    executable=self.node_executable,
                    file_extension=self.file_extension,
                    syntax_check_cmd=f"{self.node_executable} --check",
                    package_manager="npm"
                )
            else:
                return LanguageInfo(
                    language=self.language,
                    version="unknown",
                    available=False,
                    executable=self.node_executable,
                    file_extension=self.file_extension
                )
                
        except Exception as e:
            return LanguageInfo(
                language=self.language,
                version="unknown",
                available=False,
                executable=self.node_executable,
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
        
        # 危险的全局对象/函数
        dangerous_globals = [
            'eval', 'Function', 'setTimeout', 'setInterval',
            'exec', 'execSync', 'spawn', 'spawnSync',
            'require', 'import'
        ]
        
        # 危险的模块
        dangerous_modules = [
            'child_process', 'fs', 'net', 'http', 'https',
            'dgram', 'dns', 'tls', 'crypto', 'os',
            'process', 'cluster', 'worker_threads',
            'vm', 'v8', 'perf_hooks'
        ]
        
        # 检查危险全局对象
        for global_name in dangerous_globals:
            if global_name in code:
                # 检查是否在字符串中
                if not self._is_in_string(code, global_name):
                    issues.append(f"Use of potentially dangerous global: {global_name}")
        
        # 检查危险模块导入
        for module in dangerous_modules:
            if f"require('{module}')" in code or f'require("{module}")' in code:
                issues.append(f"Import of potentially dangerous module: {module}")
        
        # 检查文件操作
        if "fs." in code:
            issues.append("File system operation detected")
        
        # 检查网络操作
        if "http." in code or "https." in code or "net." in code:
            issues.append("Network operation detected")
        
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
        
        # 检查 console.log
        if "console.log" in code:
            warnings.append("Code contains console.log statements")
        
        # 检查 var 使用
        if "var " in code:
            warnings.append("Consider using 'let' or 'const' instead of 'var'")
        
        # 检查 == 使用
        if " == " in code and " === " not in code:
            warnings.append("Consider using '===' instead of '=='")
        
        return warnings
    
    def _generate_suggestions(self, code: str) -> List[str]:
        """生成代码建议
        
        Args:
            code: 要分析的代码
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        # 检查是否使用严格模式
        if "'use strict'" not in code and '"use strict"' not in code:
            suggestions.append("Consider adding 'use strict' at the beginning")
        
        # 检查是否有错误处理
        if "try" not in code and ("require" in code or "fetch" in code):
            suggestions.append("Consider adding error handling")
        
        # 检查是否有 JSDoc
        if "function " in code and "/**" not in code:
            suggestions.append("Consider adding JSDoc comments to functions")
        
        return suggestions
    
    def _is_in_string(self, code: str, word: str) -> bool:
        """检查单词是否在字符串中
        
        Args:
            code: 代码内容
            word: 要检查的单词
            
        Returns:
            bool: 是否在字符串中
        """
        import re
        # 查找所有字符串
        strings = re.findall(r'["\'].*?["\']', code)
        for s in strings:
            if word in s:
                return True
        return False
