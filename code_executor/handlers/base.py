# code_executor/handlers/base.py

"""
语言处理器基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio

from ..models import (
    ExecutionResult, ValidationResult, LanguageInfo,
    SandboxConfig, ExecutionStatus
)


class LanguageHandler(ABC):
    """语言处理器基类
    
    所有语言处理器都需要继承此类并实现抽象方法。
    """
    
    def __init__(self):
        """初始化语言处理器"""
        self._language_info: Optional[LanguageInfo] = None
    
    @property
    @abstractmethod
    def language(self) -> str:
        """返回语言名称"""
        pass
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """返回文件扩展名"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        code: str,
        timeout: float = 30.0,
        working_directory: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
        sandbox_config: Optional[SandboxConfig] = None
    ) -> ExecutionResult:
        """执行代码
        
        Args:
            code: 要执行的代码
            timeout: 超时时间（秒）
            working_directory: 工作目录
            env_vars: 环境变量
            input_data: 标准输入数据
            sandbox_config: 沙盒配置
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    async def validate(self, code: str) -> ValidationResult:
        """验证代码
        
        Args:
            code: 要验证的代码
            
        Returns:
            ValidationResult: 验证结果
        """
        pass
    
    @abstractmethod
    async def check_availability(self) -> LanguageInfo:
        """检查语言是否可用
        
        Returns:
            LanguageInfo: 语言信息
        """
        pass
    
    async def get_language_info(self) -> LanguageInfo:
        """获取语言信息
        
        Returns:
            LanguageInfo: 语言信息
        """
        if self._language_info is None:
            self._language_info = await self.check_availability()
        return self._language_info
    
    async def is_available(self) -> bool:
        """检查语言是否可用
        
        Returns:
            bool: 是否可用
        """
        info = await self.get_language_info()
        return info.available
    
    def _create_error_result(
        self,
        request_id: str,
        error: str,
        duration_ms: float = 0.0
    ) -> ExecutionResult:
        """创建错误结果
        
        Args:
            request_id: 请求 ID
            error: 错误信息
            duration_ms: 执行耗时
            
        Returns:
            ExecutionResult: 错误结果
        """
        return ExecutionResult(
            execution_id="",
            request_id=request_id,
            success=False,
            status=ExecutionStatus.FAILED,
            error=error,
            duration_ms=duration_ms,
            language=self.language
        )
    
    def _create_timeout_result(
        self,
        request_id: str,
        timeout: float,
        duration_ms: float
    ) -> ExecutionResult:
        """创建超时结果
        
        Args:
            request_id: 请求 ID
            timeout: 超时时间
            duration_ms: 执行耗时
            
        Returns:
            ExecutionResult: 超时结果
        """
        return ExecutionResult(
            execution_id="",
            request_id=request_id,
            success=False,
            status=ExecutionStatus.TIMEOUT,
            error=f"Execution timed out after {timeout}s",
            duration_ms=duration_ms,
            language=self.language
        )
    
    def _truncate_output(self, output: str, max_size: int = 1024 * 1024) -> str:
        """截断输出
        
        Args:
            output: 输出内容
            max_size: 最大大小（字节）
            
        Returns:
            str: 截断后的输出
        """
        if len(output.encode('utf-8')) > max_size:
            # 截断到最大大小
            truncated = output[:max_size]
            # 找到最后一个换行符
            last_newline = truncated.rfind('\n')
            if last_newline > 0:
                truncated = truncated[:last_newline]
            return truncated + "\n... (output truncated)"
        return output
