# code_executor/core.py

"""
代码执行引擎核心模块
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any

from .models import (
    ExecutorConfig, SandboxConfig, CodeExecutionRequest,
    ExecutionResult, ValidationResult, LanguageInfo,
    ExecutionLog, ExecutionStatus, generate_execution_id
)
from .handlers.base import LanguageHandler
from .handlers.python_handler import PythonHandler
from .handlers.javascript_handler import JavaScriptHandler
from .handlers.shell_handler import ShellHandler
from .sandbox import SandboxManager, ResourceMonitor

logger = logging.getLogger(__name__)


class CodeExecutor:
    """代码执行引擎
    
    负责安全地执行代码，支持多种语言和沙盒环境。
    
    核心功能：
    1. 代码执行：支持 Python、JavaScript、Shell 等语言
    2. 沙盒环境：提供隔离的执行环境
    3. 资源限制：控制 CPU、内存、磁盘使用
    4. 安全检查：验证代码安全性
    5. 执行日志：记录执行历史
    """
    
    def __init__(self, config: Optional[ExecutorConfig] = None):
        """
        初始化代码执行引擎
        
        Args:
            config: 执行器配置
        """
        self.config = config or ExecutorConfig()
        self.sandbox_manager = SandboxManager()
        self.resource_monitor = ResourceMonitor(self.sandbox_manager)
        
        # 语言处理器
        self._handlers: Dict[str, LanguageHandler] = {}
        
        # 执行日志
        self._execution_logs: List[ExecutionLog] = []
        
        # 统计信息
        self._stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_executions": 0,
            "total_duration_ms": 0.0
        }
        
        # 初始化默认语言处理器
        self._init_default_handlers()
    
    def _init_default_handlers(self):
        """初始化默认语言处理器"""
        # Python
        python_handler = PythonHandler()
        self._handlers["python"] = python_handler
        
        # JavaScript
        js_handler = JavaScriptHandler()
        self._handlers["javascript"] = js_handler
        self._handlers["js"] = js_handler
        
        # Shell/Bash
        shell_handler = ShellHandler()
        self._handlers["shell"] = shell_handler
        self._handlers["bash"] = shell_handler
        
        # PowerShell (Windows)
        if shell_handler.language == "powershell":
            self._handlers["powershell"] = shell_handler
    
    async def execute_code(
        self,
        code: str,
        language: str,
        timeout: Optional[float] = None,
        working_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
        use_sandbox: bool = True
    ) -> ExecutionResult:
        """执行代码
        
        Args:
            code: 要执行的代码
            language: 编程语言
            timeout: 超时时间（秒）
            working_directory: 工作目录
            env_vars: 环境变量
            input_data: 标准输入数据
            use_sandbox: 是否使用沙盒
            
        Returns:
            ExecutionResult: 执行结果
        """
        start_time = time.time()
        execution_id = generate_execution_id()
        
        # 获取语言处理器
        handler = self._get_handler(language)
        if not handler:
            return ExecutionResult(
                execution_id=execution_id,
                request_id="",
                success=False,
                status=ExecutionStatus.FAILED,
                error=f"Unsupported language: {language}",
                language=language
            )
        
        # 检查语言是否可用
        if not await handler.is_available():
            return ExecutionResult(
                execution_id=execution_id,
                request_id="",
                success=False,
                status=ExecutionStatus.FAILED,
                error=f"Language not available: {language}",
                language=language
            )
        
        # 确定超时时间
        actual_timeout = timeout or self.config.default_timeout
        actual_timeout = min(actual_timeout, self.config.max_timeout)
        
        # 准备环境变量
        actual_env_vars = self.config.env_vars.copy()
        if env_vars:
            actual_env_vars.update(env_vars)
        
        # 准备工作目录
        actual_working_dir = working_directory or self.config.working_directory
        
        # 创建沙盒（如果需要）
        sandbox_id = None
        if use_sandbox and self.config.enable_sandbox:
            sandbox_id = await self.sandbox_manager.create_sandbox()
            actual_working_dir = await self.sandbox_manager.get_sandbox_path(sandbox_id)
            actual_env_vars = self.sandbox_manager.create_isolated_env(sandbox_id, actual_env_vars)
        
        try:
            # 执行代码
            result = await handler.execute(
                code=code,
                timeout=actual_timeout,
                working_directory=actual_working_dir,
                env_vars=actual_env_vars,
                input_data=input_data
            )
            
            # 更新统计
            self._update_stats(result)
            
            # 记录日志
            self._log_execution(
                execution_id=execution_id,
                language=language,
                code=code,
                result=result,
                start_time=start_time,
                user_id=None,
                session_id=None
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                execution_id=execution_id,
                request_id="",
                success=False,
                status=ExecutionStatus.FAILED,
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration_ms,
                language=language
            )
            
            # 更新统计
            self._update_stats(result)
            
            return result
            
        finally:
            # 清理沙盒
            if sandbox_id:
                await self.sandbox_manager.destroy_sandbox(sandbox_id)
    
    async def execute_in_sandbox(
        self,
        code: str,
        language: str,
        sandbox_config: Optional[SandboxConfig] = None,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """在沙盒中执行代码
        
        Args:
            code: 要执行的代码
            language: 编程语言
            sandbox_config: 沙盒配置
            timeout: 超时时间（秒）
            
        Returns:
            ExecutionResult: 执行结果
        """
        # 更新沙盒配置
        if sandbox_config:
            self.sandbox_manager.config = sandbox_config
        
        return await self.execute_code(
            code=code,
            language=language,
            timeout=timeout,
            use_sandbox=True
        )
    
    async def validate_code(
        self,
        code: str,
        language: str
    ) -> ValidationResult:
        """验证代码
        
        Args:
            code: 要验证的代码
            language: 编程语言
            
        Returns:
            ValidationResult: 验证结果
        """
        handler = self._get_handler(language)
        if not handler:
            return ValidationResult(
                valid=False,
                language=language,
                errors=[f"Unsupported language: {language}"]
            )
        
        return await handler.validate(code)
    
    async def get_supported_languages(self) -> List[LanguageInfo]:
        """获取支持的语言列表
        
        Returns:
            List[LanguageInfo]: 语言信息列表
        """
        languages = []
        
        for handler in self._handlers.values():
            try:
                info = await handler.get_language_info()
                # 避免重复
                if not any(l.language == info.language for l in languages):
                    languages.append(info)
            except Exception as e:
                logger.error(f"Failed to get language info: {e}")
        
        return languages
    
    async def install_package(
        self,
        package: str,
        language: str
    ) -> bool:
        """安装包
        
        Args:
            package: 包名
            language: 编程语言
            
        Returns:
            bool: 是否安装成功
        """
        handler = self._get_handler(language)
        if not handler:
            return False
        
        # 根据语言执行安装命令
        if language == "python":
            cmd = f"pip install {package}"
        elif language in ["javascript", "js"]:
            cmd = f"npm install {package}"
        else:
            return False
        
        # 执行安装命令
        result = await self.execute_code(
            code=cmd,
            language="shell",
            timeout=120.0,
            use_sandbox=False
        )
        
        return result.success
    
    def register_handler(self, language: str, handler: LanguageHandler):
        """注册语言处理器
        
        Args:
            language: 语言名称
            handler: 语言处理器
        """
        self._handlers[language.lower()] = handler
        logger.info(f"Registered handler for language: {language}")
    
    def _get_handler(self, language: str) -> Optional[LanguageHandler]:
        """获取语言处理器
        
        Args:
            language: 语言名称
            
        Returns:
            Optional[LanguageHandler]: 语言处理器
        """
        return self._handlers.get(language.lower())
    
    def _update_stats(self, result: ExecutionResult):
        """更新统计信息
        
        Args:
            result: 执行结果
        """
        self._stats["total_executions"] += 1
        self._stats["total_duration_ms"] += result.duration_ms
        
        if result.success:
            self._stats["successful_executions"] += 1
        elif result.status == ExecutionStatus.TIMEOUT:
            self._stats["timeout_executions"] += 1
        else:
            self._stats["failed_executions"] += 1
    
    def _log_execution(
        self,
        execution_id: str,
        language: str,
        code: str,
        result: ExecutionResult,
        start_time: float,
        user_id: Optional[str],
        session_id: Optional[str]
    ):
        """记录执行日志
        
        Args:
            execution_id: 执行 ID
            language: 编程语言
            code: 代码内容
            result: 执行结果
            start_time: 开始时间
            user_id: 用户 ID
            session_id: 会话 ID
        """
        log = ExecutionLog(
            log_id=str(uuid.uuid4()),
            execution_id=execution_id,
            request_id=result.request_id,
            language=language,
            code_snippet=code[:500],  # 只记录前 500 字符
            start_time=start_time,
            end_time=time.time(),
            duration_ms=result.duration_ms,
            success=result.success,
            exit_code=result.exit_code,
            error=result.error,
            user_id=user_id,
            session_id=session_id
        )
        
        self._execution_logs.append(log)
        
        # 限制日志数量
        if len(self._execution_logs) > 1000:
            self._execution_logs = self._execution_logs[-500:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = self._stats.copy()
        
        if stats["total_executions"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_executions"]
            stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
        else:
            stats["avg_duration_ms"] = 0.0
            stats["success_rate"] = 0.0
        
        return stats
    
    def get_execution_logs(
        self,
        language: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionLog]:
        """获取执行日志
        
        Args:
            language: 编程语言过滤
            limit: 返回数量限制
            
        Returns:
            List[ExecutionLog]: 执行日志列表
        """
        logs = self._execution_logs
        
        if language:
            logs = [log for log in logs if log.language == language]
        
        return logs[-limit:]
    
    async def get_status(self) -> Dict[str, Any]:
        """获取执行器状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        languages = await self.get_supported_languages()
        
        return {
            "status": "ready",
            "config": {
                "default_timeout": self.config.default_timeout,
                "max_timeout": self.config.max_timeout,
                "max_memory_mb": self.config.max_memory_mb,
                "enable_sandbox": self.config.enable_sandbox
            },
            "supported_languages": [
                {
                    "language": lang.language,
                    "version": lang.version,
                    "available": lang.available
                }
                for lang in languages
            ],
            "active_sandboxes": len(await self.sandbox_manager.list_sandboxes()),
            "stats": self.get_stats()
        }
