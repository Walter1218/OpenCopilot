# observability_module/api.py

"""
可观测性模块 RESTful API 端点
"""

from typing import Dict, List, Optional, Any, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    ObservabilityConfig, LogEntry, Metric, Trace, Span,
    HealthStatusModel, DashboardData, LogLevel
)
from .core import ObservabilityModule


# Pydantic 模型（用于 API 请求/响应）

class LogRequest(BaseModel):
    """日志请求"""
    level: str = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    module: str = Field("", description="模块名")
    function: str = Field("", description="函数名")
    line_number: int = Field(0, description="行号")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    trace_id: Optional[str] = Field(None, description="追踪 ID")
    span_id: Optional[str] = Field(None, description="跨度 ID")


class MetricRequest(BaseModel):
    """指标请求"""
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="指标值")
    metric_type: str = Field("gauge", description="指标类型")
    tags: Optional[Dict[str, str]] = Field(None, description="标签")
    unit: str = Field("", description="单位")


class TraceStartRequest(BaseModel):
    """开始追踪请求"""
    operation: str = Field(..., description="操作名称")
    tags: Optional[Dict[str, Any]] = Field(None, description="标签")


class TraceEndRequest(BaseModel):
    """结束追踪请求"""
    trace_id: str = Field(..., description="追踪 ID")
    status: str = Field("ok", description="状态")


class SpanStartRequest(BaseModel):
    """开始跨度请求"""
    trace_id: str = Field(..., description="追踪 ID")
    operation: str = Field(..., description="操作名称")
    parent_id: Optional[str] = Field(None, description="父跨度 ID")
    tags: Optional[Dict[str, Any]] = Field(None, description="标签")


class SpanEndRequest(BaseModel):
    """结束跨度请求"""
    span_id: str = Field(..., description="跨度 ID")
    status: str = Field("ok", description="状态")


class LogEntryResponse(BaseModel):
    """日志条目响应"""
    log_id: str
    timestamp: float
    level: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    context: Dict[str, Any] = {}
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class MetricResponse(BaseModel):
    """指标响应"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = {}
    unit: str = ""
    metric_type: str = ""


class TraceResponse(BaseModel):
    """追踪响应"""
    trace_id: str
    spans: List[Dict[str, Any]] = []
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str
    tags: Dict[str, Any] = {}


class HealthStatusResponse(BaseModel):
    """健康状态响应"""
    status: str
    version: str
    uptime: float
    modules: Dict[str, Any] = {}
    dependencies: Dict[str, Any] = {}
    performance: Dict[str, Any] = {}
    timestamp: float


class DashboardResponse(BaseModel):
    """仪表盘响应"""
    health_status: Dict[str, Any]
    recent_logs: List[Dict[str, Any]] = []
    active_traces: List[Dict[str, Any]] = []
    metrics_summary: Dict[str, Any] = {}
    alerts: List[Dict[str, Any]] = []


class StatsResponse(BaseModel):
    """统计响应"""
    log_calls: int
    metric_calls: int
    trace_calls: int
    health_checks: int
    logger: Dict[str, Any]
    metrics: Dict[str, Any]
    tracer: Dict[str, Any]
    health_checker: Dict[str, Any]


class StatusResponse(BaseModel):
    """状态响应"""
    status: str
    config: Dict[str, Any]
    stats: Dict[str, Any]


def create_observability_router(observability: ObservabilityModule) -> APIRouter:
    """
    创建可观测性模块 API 路由器
    
    Args:
        observability: 可观测性模块实例
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/observability", tags=["observability"])
    
    @router.post("/log", response_model=LogEntryResponse)
    async def log(request: LogRequest):
        """记录日志"""
        entry = await observability.log(
            level=request.level,
            message=request.message,
            module=request.module,
            function=request.function,
            line_number=request.line_number,
            context=request.context,
            trace_id=request.trace_id,
            span_id=request.span_id
        )
        
        if not entry:
            raise HTTPException(
                status_code=400,
                detail="Log entry not created (level filter)"
            )
        
        return LogEntryResponse(
            log_id=entry.log_id,
            timestamp=entry.timestamp,
            level=entry.level,
            message=entry.message,
            module=entry.module,
            function=entry.function,
            line_number=entry.line_number,
            context=entry.context,
            trace_id=entry.trace_id,
            span_id=entry.span_id
        )
    
    @router.post("/metrics", response_model=MetricResponse)
    async def record_metric(request: MetricRequest):
        """记录指标"""
        metric = await observability.record_metric(
            name=request.name,
            value=request.value,
            metric_type=request.metric_type,
            tags=request.tags,
            unit=request.unit
        )
        
        return MetricResponse(
            name=metric.name,
            value=metric.value,
            timestamp=metric.timestamp,
            tags=metric.tags,
            unit=metric.unit,
            metric_type=metric.metric_type
        )
    
    @router.post("/trace/start", response_model=TraceResponse)
    async def start_trace(request: TraceStartRequest):
        """开始追踪"""
        trace = await observability.start_trace(
            operation=request.operation,
            tags=request.tags
        )
        
        return TraceResponse(
            trace_id=trace.trace_id,
            spans=[],
            start_time=trace.start_time,
            status=trace.status,
            tags=trace.tags
        )
    
    @router.post("/trace/end")
    async def end_trace(request: TraceEndRequest):
        """结束追踪"""
        success = await observability.end_trace(
            trace_id=request.trace_id,
            status=request.status
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Trace not found: {request.trace_id}"
            )
        
        return {"status": "ended", "trace_id": request.trace_id}
    
    @router.post("/span/start")
    async def start_span(request: SpanStartRequest):
        """开始跨度"""
        span = await observability.start_span(
            trace_id=request.trace_id,
            operation=request.operation,
            parent_id=request.parent_id,
            tags=request.tags
        )
        
        if not span:
            raise HTTPException(
                status_code=404,
                detail=f"Trace not found: {request.trace_id}"
            )
        
        return {
            "span_id": span.span_id,
            "trace_id": request.trace_id,
            "operation": span.operation,
            "start_time": span.start_time
        }
    
    @router.post("/span/end")
    async def end_span(request: SpanEndRequest):
        """结束跨度"""
        success = await observability.end_span(
            span_id=request.span_id,
            status=request.status
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Span not found: {request.span_id}"
            )
        
        return {"status": "ended", "span_id": request.span_id}
    
    @router.get("/health", response_model=HealthStatusResponse)
    async def get_health_status(
        force: bool = Query(False, description="强制检查")
    ):
        """获取健康状态"""
        status = await observability.get_health_status(force)
        
        return HealthStatusResponse(
            status=status.status,
            version=status.version,
            uptime=status.uptime,
            modules={
                name: {
                    "module_name": m.module_name,
                    "status": m.status,
                    "last_check": m.last_check,
                    "error_count": m.error_count,
                    "avg_response_ms": m.avg_response_ms,
                    "details": m.details
                }
                for name, m in status.modules.items()
            },
            dependencies={
                name: {
                    "dependency_name": d.dependency_name,
                    "status": d.status,
                    "last_check": d.last_check,
                    "response_time_ms": d.response_time_ms,
                    "error_message": d.error_message
                }
                for name, d in status.dependencies.items()
            },
            performance={
                "cpu_usage_percent": status.performance.cpu_usage_percent,
                "memory_usage_mb": status.performance.memory_usage_mb,
                "memory_total_mb": status.performance.memory_total_mb,
                "disk_usage_percent": status.performance.disk_usage_percent
            },
            timestamp=status.timestamp
        )
    
    @router.get("/metrics")
    async def get_metrics(
        metric_name: Optional[str] = Query(None, description="指标名称"),
        start_time: Optional[float] = Query(None, description="开始时间"),
        end_time: Optional[float] = Query(None, description="结束时间"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取指标"""
        time_range = (start_time, end_time) if start_time and end_time else None
        
        return await observability.get_metrics(
            metric_name=metric_name,
            time_range=time_range,
            limit=limit
        )
    
    @router.get("/logs", response_model=List[LogEntryResponse])
    async def get_logs(
        level: Optional[str] = Query(None, description="日志级别过滤"),
        module: Optional[str] = Query(None, description="模块名过滤"),
        trace_id: Optional[str] = Query(None, description="追踪 ID 过滤"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取日志"""
        entries = await observability.get_logs(
            level=level,
            module=module,
            trace_id=trace_id,
            limit=limit
        )
        
        return [
            LogEntryResponse(
                log_id=e.log_id,
                timestamp=e.timestamp,
                level=e.level,
                message=e.message,
                module=e.module,
                function=e.function,
                line_number=e.line_number,
                context=e.context,
                trace_id=e.trace_id,
                span_id=e.span_id
            )
            for e in entries
        ]
    
    @router.get("/traces", response_model=List[TraceResponse])
    async def get_traces(
        operation: Optional[str] = Query(None, description="操作名称过滤"),
        status: Optional[str] = Query(None, description="状态过滤"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取追踪"""
        traces = await observability.get_traces(
            operation=operation,
            status=status,
            limit=limit
        )
        
        return [
            TraceResponse(
                trace_id=t.trace_id,
                spans=[
                    {
                        "span_id": s.span_id,
                        "parent_id": s.parent_id,
                        "operation": s.operation,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                        "duration_ms": s.duration_ms,
                        "status": s.status,
                        "tags": s.tags
                    }
                    for s in t.spans
                ],
                start_time=t.start_time,
                end_time=t.end_time,
                duration_ms=t.duration_ms,
                status=t.status,
                tags=t.tags
            )
            for t in traces
        ]
    
    @router.get("/dashboard", response_model=DashboardResponse)
    async def get_dashboard():
        """获取仪表盘数据"""
        data = await observability.get_dashboard_data()
        
        return DashboardResponse(
            health_status={
                "status": data.health_status.status,
                "version": data.health_status.version,
                "uptime": data.health_status.uptime,
                "timestamp": data.health_status.timestamp
            },
            recent_logs=[
                {
                    "log_id": e.log_id,
                    "timestamp": e.timestamp,
                    "level": e.level,
                    "message": e.message,
                    "module": e.module
                }
                for e in data.recent_logs
            ],
            active_traces=[
                {
                    "trace_id": t.trace_id,
                    "start_time": t.start_time,
                    "status": t.status,
                    "span_count": len(t.spans)
                }
                for t in data.active_traces
            ],
            metrics_summary=data.metrics_summary,
            alerts=data.alerts
        )
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = observability.get_stats()
        return StatsResponse(**stats)
    
    @router.get("/status", response_model=StatusResponse)
    async def get_status():
        """获取模块状态"""
        status = await observability.get_status()
        return StatusResponse(**status)
    
    return router
