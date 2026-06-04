# observability_module/logger.py

"""
结构化日志器

提供结构化日志记录功能，支持日志级别、上下文、追踪等。
"""

import time
import logging
import json
from typing import Dict, List, Optional, Any
from collections import deque

from .models import LogEntry, LogLevel, ObservabilityConfig

logger = logging.getLogger(__name__)


class StructuredLogger:
    """结构化日志器
    
    提供结构化日志记录功能，支持：
    - 日志级别过滤
    - 上下文信息
    - 追踪 ID 关联
    - 日志查询和导出
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """
        初始化结构化日志器
        
        Args:
            config: 可观测性配置
        """
        self.config = config or ObservabilityConfig()
        
        # 日志存储
        self._entries: deque = deque(maxlen=self.config.log_max_entries)
        
        # 统计信息
        self._stats = {
            "total_entries": 0,
            "entries_by_level": {level.value: 0 for level in LogLevel},
            "entries_by_module": {}
        }
    
    def log(
        self,
        level: str,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            module: 模块名
            function: 函数名
            line_number: 行号
            context: 上下文信息
            trace_id: 追踪 ID
            span_id: 跨度 ID
            
        Returns:
            LogEntry: 日志条目
        """
        # 检查日志级别
        if not self._should_log(level):
            return None
        
        # 创建日志条目
        entry = LogEntry(
            log_id="",
            timestamp=time.time(),
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context or {},
            trace_id=trace_id,
            span_id=span_id
        )
        
        # 添加到存储
        self._entries.append(entry)
        
        # 更新统计
        self._update_stats(entry)
        
        # 输出到控制台
        self._output_to_console(entry)
        
        return entry
    
    def debug(
        self,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录 DEBUG 级别日志"""
        return self.log(
            level=LogLevel.DEBUG.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def info(
        self,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录 INFO 级别日志"""
        return self.log(
            level=LogLevel.INFO.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def warning(
        self,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录 WARNING 级别日志"""
        return self.log(
            level=LogLevel.WARNING.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def error(
        self,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录 ERROR 级别日志"""
        return self.log(
            level=LogLevel.ERROR.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def critical(
        self,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> LogEntry:
        """记录 CRITICAL 级别日志"""
        return self.log(
            level=LogLevel.CRITICAL.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
    
    def get_entries(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """获取日志条目
        
        Args:
            level: 日志级别过滤
            module: 模块名过滤
            trace_id: 追踪 ID 过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[LogEntry]: 日志条目列表
        """
        entries = list(self._entries)
        
        # 应用过滤器
        if level:
            entries = [e for e in entries if e.level == level]
        
        if module:
            entries = [e for e in entries if e.module == module]
        
        if trace_id:
            entries = [e for e in entries if e.trace_id == trace_id]
        
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        # 按时间倒序排列
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries[:limit]
    
    def get_entry_by_id(self, entry_id: str) -> Optional[LogEntry]:
        """根据 ID 获取日志条目
        
        Args:
            entry_id: 日志 ID
            
        Returns:
            Optional[LogEntry]: 日志条目
        """
        for entry in self._entries:
            if entry.log_id == entry_id:
                return entry
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_entries": self._stats["total_entries"],
            "entries_by_level": dict(self._stats["entries_by_level"]),
            "entries_by_module": dict(self._stats["entries_by_module"]),
            "current_entries": len(self._entries)
        }
    
    def _should_log(self, level: str) -> bool:
        """检查是否应该记录日志
        
        Args:
            level: 日志级别
            
        Returns:
            bool: 是否应该记录
        """
        level_order = {
            LogLevel.DEBUG.value: 0,
            LogLevel.INFO.value: 1,
            LogLevel.WARNING.value: 2,
            LogLevel.ERROR.value: 3,
            LogLevel.CRITICAL.value: 4
        }
        
        log_level = level_order.get(self.config.log_level, 0)
        entry_level = level_order.get(level, 0)
        
        return entry_level >= log_level
    
    def _update_stats(self, entry: LogEntry):
        """更新统计信息
        
        Args:
            entry: 日志条目
        """
        self._stats["total_entries"] += 1
        
        # 按级别统计
        level = entry.level
        if level in self._stats["entries_by_level"]:
            self._stats["entries_by_level"][level] += 1
        
        # 按模块统计
        module = entry.module
        if module:
            self._stats["entries_by_module"][module] = \
                self._stats["entries_by_module"].get(module, 0) + 1
    
    def _output_to_console(self, entry: LogEntry):
        """输出到控制台
        
        Args:
            entry: 日志条目
        """
        # 格式化日志消息
        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(entry.timestamp)
        )
        
        level_str = f"[{entry.level}]"
        module_str = f"[{entry.module}]" if entry.module else ""
        trace_str = f"[trace={entry.trace_id}]" if entry.trace_id else ""
        
        message = f"{timestamp} {level_str} {module_str} {trace_str} {entry.message}"
        
        # 根据级别输出
        if entry.level == LogLevel.DEBUG.value:
            logger.debug(message)
        elif entry.level == LogLevel.INFO.value:
            logger.info(message)
        elif entry.level == LogLevel.WARNING.value:
            logger.warning(message)
        elif entry.level == LogLevel.ERROR.value:
            logger.error(message)
        elif entry.level == LogLevel.CRITICAL.value:
            logger.critical(message)
    
    def clear(self):
        """清空日志"""
        self._entries.clear()
        self._stats = {
            "total_entries": 0,
            "entries_by_level": {level.value: 0 for level in LogLevel},
            "entries_by_module": {}
        }
        logger.info("Log entries cleared")
    
    def export_json(self, limit: Optional[int] = None) -> str:
        """导出日志为 JSON
        
        Args:
            limit: 导出数量限制
            
        Returns:
            str: JSON 字符串
        """
        entries = list(self._entries)
        
        if limit:
            entries = entries[-limit:]
        
        data = [
            {
                "log_id": e.log_id,
                "timestamp": e.timestamp,
                "level": e.level,
                "message": e.message,
                "module": e.module,
                "function": e.function,
                "line_number": e.line_number,
                "context": e.context,
                "trace_id": e.trace_id,
                "span_id": e.span_id
            }
            for e in entries
        ]
        
        return json.dumps(data, indent=2, default=str)
