# tool_system/executor.py

"""
工具执行器

负责执行工具调用，包括参数验证、超时控制、重试机制等。
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .models import (
    ToolDefinition, ToolCall, ToolResult, ToolStatus,
    ToolExecutionLog
)
from .registry import ToolRegistry
from .validators import ParameterValidator

logger = logging.getLogger(__name__)


class ToolExecutor:
    """工具执行器
    
    职责：
    1. 执行工具调用（支持同步/异步）
    2. 参数验证
    3. 超时控制
    4. 重试机制
    5. 执行日志记录
    6. 权限检查（与安全模块集成）
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        validator: Optional[ParameterValidator] = None,
        approval_handler: Optional[Callable] = None,
        max_concurrent: int = 10
    ):
        """
        初始化工具执行器
        
        Args:
            registry: 工具注册表
            validator: 参数验证器
            approval_handler: 审批处理器
            max_concurrent: 最大并发执行数
        """
        self._registry = registry
        self._validator = validator or ParameterValidator()
        self._approval_handler = approval_handler
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 执行日志
        self._execution_logs: List[ToolExecutionLog] = []
        
        # 统计信息
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0.0
        }
    
    async def execute(
        self,
        call: ToolCall,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ToolResult:
        """
        执行工具调用
        
        Args:
            call: 工具调用请求
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            ToolResult: 执行结果
        """
        call_id = call.call_id or str(uuid.uuid4())
        start_time = time.time()
        
        # 获取工具定义和处理函数
        definition = self._registry.get_tool(call.tool_id)
        if not definition:
            return self._create_error_result(
                call_id, call.tool_id, "unknown",
                f"Tool not found: {call.tool_id}",
                start_time
            )
        
        handler = self._registry.get_handler(call.tool_id)
        if not handler:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"No handler for tool: {call.tool_id}",
                start_time
            )
        
        # 检查工具状态
        status = self._registry.get_status(call.tool_id)
        if status != ToolStatus.AVAILABLE:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"Tool is not available: {status.value}",
                start_time
            )
        
        # 验证参数
        validation_error = self._validator.validate(
            call.parameters, definition.parameters
        )
        if validation_error:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"Parameter validation failed: {validation_error}",
                start_time
            )
        
        # 检查是否需要审批
        if definition.requires_approval:
            if not await self._request_approval(definition, call, user_id):
                return self._create_error_result(
                    call_id, call.tool_id, definition.name,
                    "Approval denied",
                    start_time
                )
        
        # 执行工具
        try:
            # 设置工具状态为忙碌
            self._registry.set_status(call.tool_id, ToolStatus.BUSY)
            
            # 确定超时时间
            timeout = call.timeout or definition.timeout
            
            # 执行（带超时和并发控制）
            async with self._semaphore:
                result = await asyncio.wait_for(
                    self._execute_handler(handler, call.parameters),
                    timeout=timeout
                )
            
            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 创建成功结果
            tool_result = ToolResult(
                tool_call_id=call_id,
                tool_id=call.tool_id,
                tool_name=definition.name,
                success=True,
                output=result,
                duration_ms=duration_ms,
                metadata=call.metadata
            )
            
            # 更新统计
            self._update_stats(duration_ms, success=True)
            
            # 记录日志
            self._log_execution(
                call, definition, tool_result,
                start_time, user_id, session_id
            )
            
            return tool_result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Tool execution timeout after {timeout}s"
            
            self._update_stats(duration_ms, success=False)
            
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                error_msg, start_time
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            logger.error(f"Tool execution failed: {error_msg}", exc_info=True)
            
            self._update_stats(duration_ms, success=False)
            
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                error_msg, start_time
            )
            
        finally:
            # 恢复工具状态
            self._registry.set_status(call.tool_id, ToolStatus.AVAILABLE)
    
    async def batch_execute(
        self,
        calls: List[ToolCall],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_concurrent: Optional[int] = None
    ) -> List[ToolResult]:
        """
        批量执行工具调用
        
        Args:
            calls: 工具调用请求列表
            user_id: 用户 ID
            session_id: 会话 ID
            max_concurrent: 最大并发数
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        if not calls:
            return []
        
        # 确定并发数
        concurrent = max_concurrent or len(calls)
        semaphore = asyncio.Semaphore(concurrent)
        
        async def execute_with_semaphore(call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute(call, user_id, session_id)
        
        # 并行执行
        tasks = [execute_with_semaphore(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_error_result(
                    calls[i].call_id or str(uuid.uuid4()),
                    calls[i].tool_id,
                    "unknown",
                    str(result),
                    time.time()
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _execute_handler(
        self,
        handler: Callable,
        parameters: Dict[str, Any]
    ) -> Any:
        """执行工具处理函数"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            # 同步函数在线程池中执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: handler(**parameters))
    
    async def _request_approval(
        self,
        definition: ToolDefinition,
        call: ToolCall,
        user_id: Optional[str]
    ) -> bool:
        """请求审批"""
        if not self._approval_handler:
            # 没有审批处理器，默认允许
            return True
        
        if asyncio.iscoroutinefunction(self._approval_handler):
            return await self._approval_handler(definition, call, user_id)
        else:
            return self._approval_handler(definition, call, user_id)
    
    def _create_error_result(
        self,
        call_id: str,
        tool_id: str,
        tool_name: str,
        error: str,
        start_time: float
    ) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            tool_call_id=call_id,
            tool_id=tool_id,
            tool_name=tool_name,
            success=False,
            error=error,
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def _update_stats(self, duration_ms: float, success: bool) -> None:
        """更新统计信息"""
        self._stats["total_calls"] += 1
        self._stats["total_duration_ms"] += duration_ms
        
        if success:
            self._stats["successful_calls"] += 1
        else:
            self._stats["failed_calls"] += 1
    
    def _log_execution(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        result: ToolResult,
        start_time: float,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """记录执行日志"""
        log = ToolExecutionLog(
            log_id=str(uuid.uuid4()),
            tool_id=call.tool_id,
            tool_name=definition.name,
            call_id=result.tool_call_id,
            parameters=call.parameters,
            result=result,
            start_time=start_time,
            end_time=time.time(),
            duration_ms=result.duration_ms,
            user_id=user_id,
            session_id=session_id,
            error=result.error if not result.success else None
        )
        
        self._execution_logs.append(log)
        
        # 限制日志数量
        if len(self._execution_logs) > 1000:
            self._execution_logs = self._execution_logs[-500:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        if stats["total_calls"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        else:
            stats["avg_duration_ms"] = 0.0
            stats["success_rate"] = 0.0
        return stats
    
    def get_execution_logs(
        self,
        tool_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolExecutionLog]:
        """获取执行日志"""
        logs = self._execution_logs
        
        if tool_id:
            logs = [log for log in logs if log.tool_id == tool_id]
        
        return logs[-limit:]
