# code_executor/handlers/shell_handler.py

"""
Shell 语言处理器
"""

import asyncio
import os
import tempfile
import shutil
from typing import Dict, List, Optional, Any
import platform

from .base import LanguageHandler
from ..models import (
    ExecutionResult, ValidationResult, LanguageInfo,
    SandboxConfig, ExecutionStatus, generate_execution_id
)


class ShellHandler(LanguageHandler):
    """Shell 语言处理器
    
    支持执行 Shell/Bash 脚本。
    """
    
    def __init__(self, shell_executable: Optional[str] = None):
        """
        初始化 Shell 处理器
        
        Args:
            shell_executable: Shell 可执行文件路径
        """
        super().__init__()
        
        # 根据操作系统选择默认 Shell
        if shell_executable:
            self.shell_executable = shell_executable
        else:
            system = platform.system()
            if system == "Windows":
                self.shell_executable = "powershell"
            else:
                self.shell_executable = "/bin/bash"
        
        self._version: Optional[str] = None
    
    @property
    def language(self) -> str:
        """返回语言名称"""
        if "powershell" in self.shell_executable.lower():
            return "powershell"
        return "bash"
    
    @property
    def file_extension(self) -> str:
        """返回文件扩展名"""
        if "powershell" in self.shell_executable.lower():
            return ".ps1"
        return ".sh"
    
    async def execute(
        self,
        code: str,
        timeout: float = 30.0,
        working_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
        sandbox_config: Optional[SandboxConfig] = None
    ) -> ExecutionResult:
        """执行 Shell 脚本
        
        Args:
            code: 要执行的 Shell 脚本
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
        temp_dir = tempfile.mkdtemp(prefix="opencopilot_shell_")
        temp_file = os.path.join(temp_dir, f"script{self.file_extension}")
        
        try:
            # 写入代码到临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 设置文件权限
            os.chmod(temp_file, 0o755)
            
            # 准备环境变量
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # 设置工作目录
            cwd = working_directory or temp_dir
            
            # 构建命令
            if "powershell" in self.shell_executable.lower():
                cmd = [self.shell_executable, "-ExecutionPolicy", "Bypass", "-File", temp_file]
            else:
                cmd = [self.shell_executable, temp_file]
            
            # 执行脚本
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
        """验证 Shell 脚本
        
        Args:
            code: 要验证的 Shell 脚本
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        suggestions = []
        syntax_valid = True
        security_issues = []
        
        # 1. 基本语法检查
        if self.language == "bash":
            # 使用 bash -n 检查语法
            temp_dir = tempfile.mkdtemp(prefix="opencopilot_shell_validate_")
            temp_file = os.path.join(temp_dir, "check.sh")
            
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                process = await asyncio.create_subprocess_exec(
                    self.shell_executable, "-n", temp_file,
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
        """检查 Shell 是否可用
        
        Returns:
            LanguageInfo: Shell 语言信息
        """
        try:
            # 获取 Shell 版本
            if "powershell" in self.shell_executable.lower():
                cmd = [self.shell_executable, "-Command", "$PSVersionTable.PSVersion.ToString()"]
            else:
                cmd = [self.shell_executable, "--version"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode('utf-8').strip()
                # 提取第一行
                version = version.split('\n')[0].strip()
                
                self._version = version
                
                return LanguageInfo(
                    language=self.language,
                    version=version,
                    available=True,
                    executable=self.shell_executable,
                    file_extension=self.file_extension,
                    syntax_check_cmd=f"{self.shell_executable} -n" if self.language == "bash" else None,
                    package_manager=None
                )
            else:
                return LanguageInfo(
                    language=self.language,
                    version="unknown",
                    available=False,
                    executable=self.shell_executable,
                    file_extension=self.file_extension
                )
                
        except Exception as e:
            return LanguageInfo(
                language=self.language,
                version="unknown",
                available=False,
                executable=self.shell_executable,
                file_extension=self.file_extension
            )
    
    def _check_security(self, code: str) -> List[str]:
        """检查脚本安全性
        
        Args:
            code: 要检查的脚本
            
        Returns:
            List[str]: 安全问题列表
        """
        issues = []
        
        # 危险的命令
        dangerous_commands = [
            'rm -rf', 'rm -r', 'rmdir',
            'mkfs', 'fdisk', 'dd',
            'chmod 777', 'chown',
            'sudo', 'su',
            'curl', 'wget',
            'nc', 'netcat',
            'iptables', 'firewall',
            'kill', 'killall',
            'shutdown', 'reboot',
            'passwd', 'useradd', 'userdel',
            'mount', 'umount'
        ]
        
        # 检查危险命令
        for cmd in dangerous_commands:
            if cmd in code:
                issues.append(f"Use of potentially dangerous command: {cmd}")
        
        # 检查管道到解释器
        if "| bash" in code or "| sh" in code:
            issues.append("Piping to shell interpreter detected")
        
        # 检查命令替换
        if "$(" in code and ")" in code:
            issues.append("Command substitution detected")
        
        # 检查反引号
        if "`" in code:
            issues.append("Backtick command substitution detected")
        
        # 检查文件描述符重定向
        if ">/dev/null" in code or "2>&1" in code:
            issues.append("Output redirection detected")
        
        return issues
    
    def _check_quality(self, code: str) -> List[str]:
        """检查脚本质量
        
        Args:
            code: 要检查的脚本
            
        Returns:
            List[str]: 警告列表
        """
        warnings = []
        
        lines = code.split('\n')
        
        # 检查是否有 shebang
        if lines and not lines[0].startswith('#!'):
            warnings.append("Missing shebang line (#!/bin/bash)")
        
        # 检查行数
        if len(lines) > 500:
            warnings.append(f"Script is very long ({len(lines)} lines)")
        
        # 检查行长度
        for i, line in enumerate(lines, 1):
            if len(line) > 200:
                warnings.append(f"Line {i} is too long ({len(line)} chars)")
        
        # 检查是否设置了 set -e
        if "set -e" not in code:
            warnings.append("Consider adding 'set -e' for error handling")
        
        # 检查变量引用
        if "$" in code and "${" not in code:
            warnings.append("Consider using ${} for variable references")
        
        return warnings
    
    def _generate_suggestions(self, code: str) -> List[str]:
        """生成脚本建议
        
        Args:
            code: 要分析的脚本
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        # 检查是否有错误处理
        if "set -e" not in code and "trap" not in code:
            suggestions.append("Consider adding error handling with 'set -e' or 'trap'")
        
        # 检查是否有注释
        if "#" not in code:
            suggestions.append("Consider adding comments to explain the script")
        
        # 检查是否有函数
        if len(code.split('\n')) > 20 and "function" not in code and "()" not in code:
            suggestions.append("Consider organizing code into functions")
        
        return suggestions
