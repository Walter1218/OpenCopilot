# observability_module/tracer.py

"""
分布式追踪器

负责追踪请求在系统中的流转路径。
"""

import time
import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from .models import Trace, Span, TraceStatus, ObservabilityConfig

logger = logging.getLogger(__name__)


class DistributedTracer:
    """分布式追踪器
    
    追踪请求在系统中的流转路径，支持：
    - 创建追踪
    - 创建跨度
    - 跨度嵌套
    - 追踪查询
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """
        初始化分布式追踪器
        
        Args:
            config: 可观测性配置
        """
        self.config = config or ObservabilityConfig()
        
        # 追踪存储: trace_id -> Trace
        self._traces: Dict[str, Trace] = {}
        
        # 活跃跨度: span_id -> Span
        self._active_spans: Dict[str, Span] = {}
        
        # 统计信息
        self._stats = {
            "total_traces": 0,
            "total_spans": 0,
            "completed_traces": 0,
            "completed_spans": 0
        }
    
    def start_trace(
        self,
        operation: str,
        tags: Optional[Dict[str, Any]] = None
    ) -> Trace:
        """开始追踪
        
        Args:
            operation: 操作名称
            tags: 标签
            
        Returns:
            Trace: 追踪对象
        """
        trace = Trace(
            trace_id="",
            start_time=time.time(),
            tags=tags or {}
        )
        
        # 存储追踪
        self._traces[trace.trace_id] = trace
        
        # 更新统计
        self._stats["total_traces"] += 1
        
        logger.debug(f"Started trace: {trace.trace_id}, operation={operation}")
        
        return trace
    
    def start_span(
        self,
        trace_id: str,
        operation: str,
        parent_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> Optional[Span]:
        """开始跨度
        
        Args:
            trace_id: 追踪 ID
            operation: 操作名称
            parent_id: 父跨度 ID
            tags: 标签
            
        Returns:
            Optional[Span]: 跨度对象
        """
        # 获取追踪
        trace = self._traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace not found: {trace_id}")
            return None
        
        # 创建跨度
        span = Span(
            span_id="",
            parent_id=parent_id,
            operation=operation,
            start_time=time.time(),
            tags=tags or {}
        )
        
        # 添加到追踪
        trace.add_span(span)
        
        # 存储活跃跨度
        self._active_spans[span.span_id] = span
        
        # 更新统计
        self._stats["total_spans"] += 1
        
        logger.debug(
            f"Started span: {span.span_id}, "
            f"trace={trace_id}, operation={operation}"
        )
        
        return span
    
    def finish_span(
        self,
        span_id: str,
        status: str = TraceStatus.OK.value
    ) -> bool:
        """完成跨度
        
        Args:
            span_id: 跨度 ID
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Active span not found: {span_id}")
            return False
        
        # 完成跨度
        span.finish(status)
        
        # 从活跃跨度中移除
        del self._active_spans[span_id]
        
        # 更新统计
        self._stats["completed_spans"] += 1
        
        logger.debug(
            f"Finished span: {span_id}, "
            f"duration={span.duration_ms:.2f}ms, status={status}"
        )
        
        return True
    
    def finish_trace(
        self,
        trace_id: str,
        status: str = TraceStatus.OK.value
    ) -> bool:
        """完成追踪
        
        Args:
            trace_id: 追踪 ID
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        trace = self._traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace not found: {trace_id}")
            return False
        
        # 完成所有活跃跨度
        for span in trace.spans:
            if span.end_time is None:
                span.finish(status)
        
        # 完成追踪
        trace.finish(status)
        
        # 更新统计
        self._stats["completed_traces"] += 1
        
        logger.debug(
            f"Finished trace: {trace_id}, "
            f"duration={trace.duration_ms:.2f}ms, status={status}"
        )
        
        return True
    
    def add_span_log(
        self,
        span_id: str,
        message: str,
        fields: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加跨度日志
        
        Args:
            span_id: 跨度 ID
            message: 日志消息
            fields: 字段
            
        Returns:
            bool: 是否成功
        """
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Active span not found: {span_id}")
            return False
        
        span.add_log(message, fields)
        
        return True
    
    def add_span_tag(
        self,
        span_id: str,
        key: str,
        value: Any
    ) -> bool:
        """添加跨度标签
        
        Args:
            span_id: 跨度 ID
            key: 标签键
            value: 标签值
            
        Returns:
            bool: 是否成功
        """
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Active span not found: {span_id}")
            return False
        
        span.tags[key] = value
        
        return True
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪
        
        Args:
            trace_id: 追踪 ID
            
        Returns:
            Optional[Trace]: 追踪对象
        """
        return self._traces.get(trace_id)
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """获取跨度
        
        Args:
            span_id: 跨度 ID
            
        Returns:
            Optional[Span]: 跨度对象
        """
        # 先从活跃跨度中查找
        if span_id in self._active_spans:
            return self._active_spans[span_id]
        
        # 从追踪中查找
        for trace in self._traces.values():
            span = trace.get_span(span_id)
            if span:
                return span
        
        return None
    
    def get_traces(
        self,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Trace]:
        """获取追踪列表
        
        Args:
            operation: 操作名称过滤
            status: 状态过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[Trace]: 追踪列表
        """
        traces = list(self._traces.values())
        
        # 应用过滤器
        if operation:
            traces = [
                t for t in traces
                if any(s.operation == operation for s in t.spans)
            ]
        
        if status:
            traces = [t for t in traces if t.status == status]
        
        if start_time:
            traces = [t for t in traces if t.start_time >= start_time]
        
        if end_time:
            traces = [t for t in traces if t.start_time <= end_time]
        
        # 按开始时间倒序排列
        traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return traces[:limit]
    
    def get_active_spans(self) -> List[Span]:
        """获取活跃跨度
        
        Returns:
            List[Span]: 活跃跨度列表
        """
        return list(self._active_spans.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_traces": self._stats["total_traces"],
            "total_spans": self._stats["total_spans"],
            "completed_traces": self._stats["completed_traces"],
            "completed_spans": self._stats["completed_spans"],
            "active_traces": len(self._traces) - self._stats["completed_traces"],
            "active_spans": len(self._active_spans)
        }
    
    def cleanup(self, max_age_hours: float = 1.0):
        """清理过期追踪
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        # 清理过期追踪
        expired_trace_ids = [
            trace_id for trace_id, trace in self._traces.items()
            if now - trace.start_time > max_age_seconds
        ]
        
        for trace_id in expired_trace_ids:
            del self._traces[trace_id]
        
        if expired_trace_ids:
            logger.info(f"Cleaned up {len(expired_trace_ids)} expired traces")
    
    def clear(self):
        """清空所有追踪"""
        self._traces.clear()
        self._active_spans.clear()
        self._stats = {
            "total_traces": 0,
            "total_spans": 0,
            "completed_traces": 0,
            "completed_spans": 0
        }
        logger.info("All traces cleared")
    
    @contextmanager
    def trace(self, operation: str, tags: Optional[Dict[str, Any]] = None):
        """追踪上下文管理器
        
        Args:
            operation: 操作名称
            tags: 标签
            
        Yields:
            Trace: 追踪对象
        """
        trace = self.start_trace(operation, tags)
        try:
            yield trace
        except Exception as e:
            trace.finish(TraceStatus.ERROR.value)
            raise
        else:
            trace.finish(TraceStatus.OK.value)
    
    @contextmanager
    def span(
        self,
        trace_id: str,
        operation: str,
        parent_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """跨度上下文管理器
        
        Args:
            trace_id: 追踪 ID
            operation: 操作名称
            parent_id: 父跨度 ID
            tags: 标签
            
        Yields:
            Span: 跨度对象
        """
        span = self.start_span(trace_id, operation, parent_id, tags)
        try:
            yield span
        except Exception as e:
            if span:
                self.finish_span(span.span_id, TraceStatus.ERROR.value)
            raise
        else:
            if span:
                self.finish_span(span.span_id, TraceStatus.OK.value)
