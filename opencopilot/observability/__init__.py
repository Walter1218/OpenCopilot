# observability_module/__init__.py

"""
可观测性模块

提供监控、日志、追踪、指标收集功能，用于系统的可观测性。
"""

from .models import (
    ObservabilityConfig, LogEntry, Metric, Trace, Span,
    HealthStatusModel, DashboardData, LogLevel, MetricType,
    HealthStatus, TraceStatus, ModuleHealth, DependencyHealth,
    PerformanceMetrics,
    generate_log_id, generate_trace_id, generate_span_id
)
from .core import ObservabilityModule
from .logger import StructuredLogger
from .metrics import MetricsCollector
from .tracer import DistributedTracer
from .health import HealthChecker
from .api import create_observability_router

__version__ = "1.0.0"
__author__ = "OpenCopilot Team"

__all__ = [
    # 核心类
    "ObservabilityModule",
    "StructuredLogger",
    "MetricsCollector",
    "DistributedTracer",
    "HealthChecker",
    
    # 数据模型
    "ObservabilityConfig",
    "LogEntry",
    "Metric",
    "Trace",
    "Span",
    "HealthStatusModel",
    "DashboardData",
    "ModuleHealth",
    "DependencyHealth",
    "PerformanceMetrics",
    
    # 枚举类型
    "LogLevel",
    "MetricType",
    "HealthStatus",
    "TraceStatus",
    
    # 工具函数
    "generate_log_id",
    "generate_trace_id",
    "generate_span_id",
    
    # API
    "create_observability_router",
]
