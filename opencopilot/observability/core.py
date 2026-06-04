# observability_module/core.py

"""
可观测性模块核心模块
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple

from .models import (
    ObservabilityConfig, LogEntry, Metric, Trace, Span,
    HealthStatusModel, DashboardData, LogLevel
)
from .logger import StructuredLogger
from .metrics import MetricsCollector
from .tracer import DistributedTracer
from .health import HealthChecker

logger = logging.getLogger(__name__)


class ObservabilityModule:
    """可观测性模块
    
    提供监控、日志、追踪、指标收集功能，包括：
    - 结构化日志记录
    - 指标收集和查询
    - 分布式追踪
    - 健康检查
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """
        初始化可观测性模块
        
        Args:
            config: 可观测性配置
        """
        self.config = config or ObservabilityConfig()
        
        # 初始化子模块
        self.logger = StructuredLogger(self.config)
        self.metrics = MetricsCollector(self.config)
        self.tracer = DistributedTracer(self.config)
        self.health_checker = HealthChecker(self.config)
        
        # 统计信息
        self._stats = {
            "log_calls": 0,
            "metric_calls": 0,
            "trace_calls": 0,
            "health_checks": 0
        }
    
    # ========== 日志接口 ==========
    
    async def log(
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
        entry = self.logger.log(
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            context=context,
            trace_id=trace_id,
            span_id=span_id
        )
        
        # 更新统计
        self._stats["log_calls"] += 1
        
        return entry
    
    async def debug(
        self,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> LogEntry:
        """记录 DEBUG 级别日志"""
        return await self.log(
            level=LogLevel.DEBUG.value,
            message=message,
            module=module,
            context=context,
            trace_id=trace_id
        )
    
    async def info(
        self,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> LogEntry:
        """记录 INFO 级别日志"""
        return await self.log(
            level=LogLevel.INFO.value,
            message=message,
            module=module,
            context=context,
            trace_id=trace_id
        )
    
    async def warning(
        self,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> LogEntry:
        """记录 WARNING 级别日志"""
        return await self.log(
            level=LogLevel.WARNING.value,
            message=message,
            module=module,
            context=context,
            trace_id=trace_id
        )
    
    async def error(
        self,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> LogEntry:
        """记录 ERROR 级别日志"""
        return await self.log(
            level=LogLevel.ERROR.value,
            message=message,
            module=module,
            context=context,
            trace_id=trace_id
        )
    
    async def critical(
        self,
        message: str,
        module: str = "",
        context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> LogEntry:
        """记录 CRITICAL 级别日志"""
        return await self.log(
            level=LogLevel.CRITICAL.value,
            message=message,
            module=module,
            context=context,
            trace_id=trace_id
        )
    
    # ========== 指标接口 ==========
    
    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> Metric:
        """记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型
            tags: 标签
            unit: 单位
            
        Returns:
            Metric: 指标对象
        """
        if metric_type == "counter":
            metric = self.metrics.record_counter(name, value, tags, unit)
        elif metric_type == "gauge":
            metric = self.metrics.record_gauge(name, value, tags, unit)
        elif metric_type == "histogram":
            metric = self.metrics.record_histogram(name, value, tags, unit)
        elif metric_type == "summary":
            metric = self.metrics.record_summary(name, value, tags, unit)
        else:
            metric = self.metrics.record_gauge(name, value, tags, unit)
        
        # 更新统计
        self._stats["metric_calls"] += 1
        
        return metric
    
    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        time_range: Optional[Tuple[float, float]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取指标
        
        Args:
            metric_name: 指标名称
            time_range: 时间范围 (start_time, end_time)
            limit: 返回数量限制
            
        Returns:
            Dict[str, Any]: 指标数据
        """
        if metric_name:
            # 获取特定指标
            start_time = time_range[0] if time_range else None
            end_time = time_range[1] if time_range else None
            
            metrics = self.metrics.get_metric_history(
                metric_name, start_time, end_time, limit
            )
            
            stats = self.metrics.get_metric_stats(metric_name)
            
            return {
                "name": metric_name,
                "metrics": [
                    {
                        "value": m.value,
                        "timestamp": m.timestamp,
                        "tags": m.tags
                    }
                    for m in metrics
                ],
                "stats": stats
            }
        else:
            # 获取所有指标摘要
            return self.metrics.get_metrics_summary()
    
    # ========== 追踪接口 ==========
    
    async def start_trace(
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
        trace = self.tracer.start_trace(operation, tags)
        
        # 更新统计
        self._stats["trace_calls"] += 1
        
        return trace
    
    async def end_trace(
        self,
        trace_id: str,
        status: str = "ok"
    ) -> bool:
        """结束追踪
        
        Args:
            trace_id: 追踪 ID
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        return self.tracer.finish_trace(trace_id, status)
    
    async def start_span(
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
        return self.tracer.start_span(trace_id, operation, parent_id, tags)
    
    async def end_span(
        self,
        span_id: str,
        status: str = "ok"
    ) -> bool:
        """结束跨度
        
        Args:
            span_id: 跨度 ID
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        return self.tracer.finish_span(span_id, status)
    
    async def get_traces(
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
        return self.tracer.get_traces(
            operation=operation,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    # ========== 健康检查接口 ==========
    
    async def get_health_status(self, force: bool = False) -> HealthStatusModel:
        """获取健康状态
        
        Args:
            force: 是否强制检查
            
        Returns:
            HealthStatusModel: 健康状态模型
        """
        status = await self.health_checker.check_health(force)
        
        # 更新统计
        self._stats["health_checks"] += 1
        
        return status
    
    def register_module_health_checker(
        self,
        module_name: str,
        checker: Any
    ):
        """注册模块健康检查函数
        
        Args:
            module_name: 模块名称
            checker: 检查函数
        """
        self.health_checker.register_module_checker(module_name, checker)
    
    def register_dependency_health_checker(
        self,
        dependency_name: str,
        checker: Any
    ):
        """注册依赖健康检查函数
        
        Args:
            dependency_name: 依赖名称
            checker: 检查函数
        """
        self.health_checker.register_dependency_checker(dependency_name, checker)
    
    # ========== 日志查询接口 ==========
    
    async def get_logs(
        self,
        level: Optional[str] = None,
        module: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """获取日志
        
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
        return self.logger.get_entries(
            level=level,
            module=module,
            trace_id=trace_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    # ========== 仪表盘接口 ==========
    
    async def get_dashboard_data(self) -> DashboardData:
        """获取仪表盘数据
        
        Returns:
            DashboardData: 仪表盘数据
        """
        # 获取健康状态
        health_status = await self.get_health_status()
        
        # 获取最近日志
        recent_logs = self.logger.get_entries(limit=10)
        
        # 获取活跃追踪
        active_traces = self.tracer.get_traces(limit=10)
        
        # 获取指标摘要
        metrics_summary = self.metrics.get_metrics_summary()
        
        # 构建告警信息
        alerts = []
        
        # 检查不健康的模块
        for module_name, module_health in health_status.modules.items():
            if module_health.status != "healthy":
                alerts.append({
                    "type": "module_unhealthy",
                    "module": module_name,
                    "status": module_health.status,
                    "message": f"Module {module_name} is {module_health.status}"
                })
        
        # 检查性能指标
        if health_status.performance.cpu_usage_percent > 80:
            alerts.append({
                "type": "high_cpu",
                "value": health_status.performance.cpu_usage_percent,
                "message": f"CPU usage is {health_status.performance.cpu_usage_percent}%"
            })
        
        return DashboardData(
            health_status=health_status,
            recent_logs=recent_logs,
            active_traces=active_traces,
            metrics_summary=metrics_summary,
            alerts=alerts
        )
    
    # ========== 统计接口 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "log_calls": self._stats["log_calls"],
            "metric_calls": self._stats["metric_calls"],
            "trace_calls": self._stats["trace_calls"],
            "health_checks": self._stats["health_checks"],
            "logger": self.logger.get_stats(),
            "metrics": self.metrics.get_stats(),
            "tracer": self.tracer.get_stats(),
            "health_checker": self.health_checker.get_stats()
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """获取模块状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "status": "ready",
            "config": {
                "log_level": self.config.log_level,
                "log_max_entries": self.config.log_max_entries,
                "metrics_max_entries": self.config.metrics_max_entries,
                "enable_tracing": self.config.enable_tracing,
                "health_check_interval": self.config.health_check_interval
            },
            "stats": self.get_stats()
        }
    
    def cleanup(self):
        """清理过期数据"""
        self.logger.clear()
        self.metrics.cleanup()
        self.tracer.cleanup()
        logger.info("Observability module cleaned up")
