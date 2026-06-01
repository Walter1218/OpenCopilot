# observability_module/models.py

"""
可观测性模块数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import uuid
import time


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"              # 仪表
    HISTOGRAM = "histogram"      # 直方图
    SUMMARY = "summary"          # 摘要


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class TraceStatus(Enum):
    """追踪状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class LogEntry:
    """日志条目"""
    log_id: str
    timestamp: float
    level: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化日志 ID"""
        if not self.log_id:
            self.log_id = str(uuid.uuid4())


@dataclass
class Metric:
    """指标"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    metric_type: str = MetricType.GAUGE.value
    
    def __post_init__(self):
        """初始化时间戳"""
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class Span:
    """跨度"""
    span_id: str
    parent_id: Optional[str]
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    status: str = TraceStatus.OK.value
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化跨度 ID"""
        if not self.span_id:
            self.span_id = str(uuid.uuid4())
    
    def finish(self, status: str = TraceStatus.OK.value):
        """完成跨度"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
    
    def add_log(self, message: str, fields: Optional[Dict[str, Any]] = None):
        """添加日志"""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            "fields": fields or {}
        })


@dataclass
class Trace:
    """追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = TraceStatus.OK.value
    tags: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化追踪 ID"""
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())
    
    def add_span(self, span: Span):
        """添加跨度"""
        self.spans.append(span)
    
    def finish(self, status: str = TraceStatus.OK.value):
        """完成追踪"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """获取跨度"""
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None


@dataclass
class ModuleHealth:
    """模块健康状态"""
    module_name: str
    status: str = HealthStatus.HEALTHY.value
    last_check: float = field(default_factory=time.time)
    error_count: int = 0
    avg_response_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyHealth:
    """依赖健康状态"""
    dependency_name: str
    status: str = HealthStatus.HEALTHY.value
    last_check: float = field(default_factory=time.time)
    response_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """性能指标"""
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_usage_percent: float = 0.0
    active_connections: int = 0
    request_rate: float = 0.0
    error_rate: float = 0.0
    avg_response_ms: float = 0.0


@dataclass
class HealthStatusModel:
    """健康状态模型"""
    status: str = HealthStatus.HEALTHY.value
    version: str = "1.0.0"
    uptime: float = 0.0
    modules: Dict[str, ModuleHealth] = field(default_factory=dict)
    dependencies: Dict[str, DependencyHealth] = field(default_factory=dict)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DashboardData:
    """仪表盘数据"""
    health_status: HealthStatusModel
    recent_logs: List[LogEntry]
    active_traces: List[Trace]
    metrics_summary: Dict[str, Any]
    alerts: List[Dict[str, Any]]


@dataclass
class ObservabilityConfig:
    """可观测性配置"""
    # 日志配置
    log_level: str = LogLevel.INFO.value
    log_max_entries: int = 10000
    log_retention_hours: int = 24
    
    # 指标配置
    metrics_max_entries: int = 10000
    metrics_retention_hours: int = 24
    
    # 追踪配置
    traces_max_entries: int = 1000
    trace_retention_hours: int = 1
    enable_tracing: bool = True
    
    # 健康检查配置
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    
    # 性能监控配置
    enable_performance_monitoring: bool = True
    performance_sample_interval: float = 10.0


def generate_log_id() -> str:
    """生成日志 ID"""
    return str(uuid.uuid4())


def generate_trace_id() -> str:
    """生成追踪 ID"""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """生成跨度 ID"""
    return str(uuid.uuid4())
