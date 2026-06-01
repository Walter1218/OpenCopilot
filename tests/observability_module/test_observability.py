# tests/observability_module/test_observability.py

"""
可观测性模块测试

测试可观测性模块的各项功能。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入可观测性模块
from observability_module.models import (
    ObservabilityConfig, LogEntry, Metric, Trace, Span,
    HealthStatusModel, DashboardData, LogLevel, MetricType,
    HealthStatus, TraceStatus, generate_log_id, generate_trace_id
)
from observability_module.core import ObservabilityModule
from observability_module.logger import StructuredLogger
from observability_module.metrics import MetricsCollector
from observability_module.tracer import DistributedTracer
from observability_module.health import HealthChecker


@pytest.fixture
def observability():
    """创建可观测性模块实例"""
    config = ObservabilityConfig(
        log_level=LogLevel.DEBUG.value,
        log_max_entries=1000,
        metrics_max_entries=1000,
        enable_tracing=True,
        health_check_interval=10.0
    )
    return ObservabilityModule(config=config)


@pytest.fixture
def structured_logger():
    """创建结构化日志器实例"""
    return StructuredLogger()


@pytest.fixture
def metrics_collector():
    """创建指标收集器实例"""
    return MetricsCollector()


@pytest.fixture
def distributed_tracer():
    """创建分布式追踪器实例"""
    return DistributedTracer()


@pytest.fixture
def health_checker():
    """创建健康检查器实例"""
    return HealthChecker()


class TestModels:
    """数据模型测试"""
    
    def test_generate_log_id(self):
        """测试生成日志 ID"""
        id1 = generate_log_id()
        id2 = generate_log_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_generate_trace_id(self):
        """测试生成追踪 ID"""
        id1 = generate_trace_id()
        id2 = generate_trace_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_log_entry_creation(self):
        """测试日志条目创建"""
        entry = LogEntry(
            log_id="test_log",
            timestamp=1234567890.0,
            level=LogLevel.INFO.value,
            message="Test message",
            module="test_module"
        )
        
        assert entry.log_id == "test_log"
        assert entry.level == LogLevel.INFO.value
        assert entry.message == "Test message"
    
    def test_metric_creation(self):
        """测试指标创建"""
        metric = Metric(
            name="test_metric",
            value=42.0,
            timestamp=1234567890.0,
            tags={"env": "test"},
            unit="count"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.tags["env"] == "test"
    
    def test_trace_creation(self):
        """测试追踪创建"""
        trace = Trace(
            trace_id="test_trace",
            start_time=1234567890.0
        )
        
        assert trace.trace_id == "test_trace"
        assert trace.status == TraceStatus.OK.value
    
    def test_span_creation(self):
        """测试跨度创建"""
        span = Span(
            span_id="test_span",
            parent_id=None,
            operation="test_operation",
            start_time=1234567890.0
        )
        
        assert span.span_id == "test_span"
        assert span.operation == "test_operation"
    
    def test_span_finish(self):
        """测试跨度完成"""
        span = Span(
            span_id="test_span",
            parent_id=None,
            operation="test_operation",
            start_time=1234567890.0
        )
        
        span.finish(TraceStatus.OK.value)
        
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.status == TraceStatus.OK.value


class TestStructuredLogger:
    """结构化日志器测试"""
    
    def test_log_entry(self, structured_logger):
        """测试记录日志"""
        entry = structured_logger.log(
            level=LogLevel.INFO.value,
            message="Test message",
            module="test_module"
        )
        
        assert entry is not None
        assert entry.level == LogLevel.INFO.value
        assert entry.message == "Test message"
    
    def test_log_levels(self, structured_logger):
        """测试日志级别"""
        # 设置日志级别为 DEBUG
        structured_logger.config.log_level = LogLevel.DEBUG.value
        
        # 记录不同级别的日志
        structured_logger.debug("Debug message")
        structured_logger.info("Info message")
        structured_logger.warning("Warning message")
        structured_logger.error("Error message")
        structured_logger.critical("Critical message")
        
        # 获取所有日志
        entries = structured_logger.get_entries()
        assert len(entries) == 5
    
    def test_log_filtering(self, structured_logger):
        """测试日志过滤"""
        # 记录不同级别的日志
        structured_logger.info("Info message 1")
        structured_logger.warning("Warning message")
        structured_logger.info("Info message 2")
        
        # 按级别过滤
        info_entries = structured_logger.get_entries(level=LogLevel.INFO.value)
        assert len(info_entries) == 2
        
        warning_entries = structured_logger.get_entries(level=LogLevel.WARNING.value)
        assert len(warning_entries) == 1
    
    def test_log_module_filtering(self, structured_logger):
        """测试模块过滤"""
        # 记录不同模块的日志
        structured_logger.info("Message 1", module="module1")
        structured_logger.info("Message 2", module="module2")
        structured_logger.info("Message 3", module="module1")
        
        # 按模块过滤
        module1_entries = structured_logger.get_entries(module="module1")
        assert len(module1_entries) == 2
    
    def test_get_stats(self, structured_logger):
        """测试获取统计信息"""
        # 记录一些日志
        structured_logger.info("Info message")
        structured_logger.warning("Warning message")
        
        stats = structured_logger.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["entries_by_level"][LogLevel.INFO.value] == 1
        assert stats["entries_by_level"][LogLevel.WARNING.value] == 1


class TestMetricsCollector:
    """指标收集器测试"""
    
    def test_record_counter(self, metrics_collector):
        """测试记录计数器"""
        metric = metrics_collector.record_counter("test_counter", 1.0)
        
        assert metric.name == "test_counter"
        assert metric.value == 1.0
        assert metric.metric_type == MetricType.COUNTER.value
        
        # 增加计数器
        metric = metrics_collector.record_counter("test_counter", 2.0)
        assert metric.value == 3.0
    
    def test_record_gauge(self, metrics_collector):
        """测试记录仪表"""
        metric = metrics_collector.record_gauge("test_gauge", 42.0)
        
        assert metric.name == "test_gauge"
        assert metric.value == 42.0
        assert metric.metric_type == MetricType.GAUGE.value
        
        # 更新仪表值
        metric = metrics_collector.record_gauge("test_gauge", 100.0)
        assert metric.value == 100.0
    
    def test_record_histogram(self, metrics_collector):
        """测试记录直方图"""
        metric = metrics_collector.record_histogram("test_histogram", 10.0)
        
        assert metric.name == "test_histogram"
        assert metric.value == 10.0
        assert metric.metric_type == MetricType.HISTOGRAM.value
    
    def test_get_counter(self, metrics_collector):
        """测试获取计数器值"""
        metrics_collector.record_counter("test_counter", 5.0)
        metrics_collector.record_counter("test_counter", 3.0)
        
        value = metrics_collector.get_counter("test_counter")
        assert value == 8.0
    
    def test_get_gauge(self, metrics_collector):
        """测试获取仪表值"""
        metrics_collector.record_gauge("test_gauge", 42.0)
        
        value = metrics_collector.get_gauge("test_gauge")
        assert value == 42.0
    
    def test_get_metric_stats(self, metrics_collector):
        """测试获取指标统计信息"""
        # 记录多个指标值
        metrics_collector.record_histogram("test_metric", 10.0)
        metrics_collector.record_histogram("test_metric", 20.0)
        metrics_collector.record_histogram("test_metric", 30.0)
        
        stats = metrics_collector.get_metric_stats("test_metric")
        
        assert stats["count"] == 3
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0
        assert stats["sum"] == 60.0
    
    def test_get_metrics_summary(self, metrics_collector):
        """测试获取指标摘要"""
        # 记录一些指标
        metrics_collector.record_counter("counter1", 5.0)
        metrics_collector.record_gauge("gauge1", 42.0)
        
        summary = metrics_collector.get_metrics_summary()
        
        assert "counter1" in summary
        assert "gauge1" in summary
        assert summary["counter1"]["latest_value"] == 5.0
        assert summary["gauge1"]["latest_value"] == 42.0


class TestDistributedTracer:
    """分布式追踪器测试"""
    
    def test_start_trace(self, distributed_tracer):
        """测试开始追踪"""
        trace = distributed_tracer.start_trace("test_operation")
        
        assert trace is not None
        assert trace.trace_id is not None
        assert trace.status == TraceStatus.OK.value
    
    def test_start_span(self, distributed_tracer):
        """测试开始跨度"""
        # 开始追踪
        trace = distributed_tracer.start_trace("test_operation")
        
        # 开始跨度
        span = distributed_tracer.start_span(
            trace.trace_id, "test_span"
        )
        
        assert span is not None
        assert span.span_id is not None
        assert span.operation == "test_span"
    
    def test_finish_span(self, distributed_tracer):
        """测试完成跨度"""
        # 开始追踪
        trace = distributed_tracer.start_trace("test_operation")
        
        # 开始跨度
        span = distributed_tracer.start_span(
            trace.trace_id, "test_span"
        )
        
        # 完成跨度
        success = distributed_tracer.finish_span(
            span.span_id, TraceStatus.OK.value
        )
        
        assert success is True
    
    def test_finish_trace(self, distributed_tracer):
        """测试完成追踪"""
        # 开始追踪
        trace = distributed_tracer.start_trace("test_operation")
        
        # 开始跨度
        span = distributed_tracer.start_span(
            trace.trace_id, "test_span"
        )
        
        # 完成追踪
        success = distributed_tracer.finish_trace(
            trace.trace_id, TraceStatus.OK.value
        )
        
        assert success is True
    
    def test_get_traces(self, distributed_tracer):
        """测试获取追踪列表"""
        # 创建一些追踪
        distributed_tracer.start_trace("operation1")
        distributed_tracer.start_trace("operation2")
        
        # 获取追踪列表
        traces = distributed_tracer.get_traces()
        
        assert len(traces) == 2
    
    def test_get_stats(self, distributed_tracer):
        """测试获取统计信息"""
        # 创建一些追踪和跨度
        trace = distributed_tracer.start_trace("test_operation")
        distributed_tracer.start_span(trace.trace_id, "test_span")
        
        stats = distributed_tracer.get_stats()
        
        assert stats["total_traces"] == 1
        assert stats["total_spans"] == 1


class TestHealthChecker:
    """健康检查器测试"""
    
    @pytest.mark.asyncio
    async def test_check_health(self, health_checker):
        """测试检查健康状态"""
        status = await health_checker.check_health()
        
        assert status is not None
        assert status.status == HealthStatus.HEALTHY.value
        assert status.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_register_module_checker(self, health_checker):
        """测试注册模块检查器"""
        async def test_checker():
            return {"status": HealthStatus.HEALTHY.value}
        
        health_checker.register_module_checker("test_module", test_checker)
        
        # 检查健康状态
        status = await health_checker.check_health(force=True)
        
        assert "test_module" in status.modules
        assert status.modules["test_module"].status == HealthStatus.HEALTHY.value
    
    @pytest.mark.asyncio
    async def test_register_dependency_checker(self, health_checker):
        """测试注册依赖检查器"""
        async def test_checker():
            return {"status": HealthStatus.HEALTHY.value}
        
        health_checker.register_dependency_checker("test_dep", test_checker)
        
        # 检查健康状态
        status = await health_checker.check_health(force=True)
        
        assert "test_dep" in status.dependencies
        assert status.dependencies["test_dep"].status == HealthStatus.HEALTHY.value
    
    def test_get_stats(self, health_checker):
        """测试获取统计信息"""
        stats = health_checker.get_stats()
        
        assert "total_checks" in stats
        assert "registered_modules" in stats
        assert "registered_dependencies" in stats


class TestObservabilityModule:
    """可观测性模块测试"""
    
    @pytest.mark.asyncio
    async def test_log(self, observability):
        """测试记录日志"""
        entry = await observability.log(
            level=LogLevel.INFO.value,
            message="Test message",
            module="test_module"
        )
        
        assert entry is not None
        assert entry.level == LogLevel.INFO.value
        assert entry.message == "Test message"
    
    @pytest.mark.asyncio
    async def test_record_metric(self, observability):
        """测试记录指标"""
        metric = await observability.record_metric(
            name="test_metric",
            value=42.0,
            metric_type="gauge"
        )
        
        assert metric is not None
        assert metric.name == "test_metric"
        assert metric.value == 42.0
    
    @pytest.mark.asyncio
    async def test_start_trace(self, observability):
        """测试开始追踪"""
        trace = await observability.start_trace("test_operation")
        
        assert trace is not None
        assert trace.trace_id is not None
    
    @pytest.mark.asyncio
    async def test_end_trace(self, observability):
        """测试结束追踪"""
        # 开始追踪
        trace = await observability.start_trace("test_operation")
        
        # 结束追踪
        success = await observability.end_trace(
            trace.trace_id, TraceStatus.OK.value
        )
        
        assert success is True
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, observability):
        """测试获取健康状态"""
        status = await observability.get_health_status()
        
        assert status is not None
        assert status.status == HealthStatus.HEALTHY.value
    
    @pytest.mark.asyncio
    async def test_get_logs(self, observability):
        """测试获取日志"""
        # 记录一些日志
        await observability.info("Info message")
        await observability.warning("Warning message")
        
        # 获取日志
        logs = await observability.get_logs()
        
        assert len(logs) == 2
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, observability):
        """测试获取指标"""
        # 记录一些指标
        await observability.record_metric("test_metric", 42.0)
        
        # 获取指标
        metrics = await observability.get_metrics("test_metric")
        
        assert metrics["name"] == "test_metric"
        assert len(metrics["metrics"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_traces(self, observability):
        """测试获取追踪"""
        # 创建一些追踪
        await observability.start_trace("operation1")
        await observability.start_trace("operation2")
        
        # 获取追踪
        traces = await observability.get_traces()
        
        assert len(traces) == 2
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, observability):
        """测试获取仪表盘数据"""
        # 记录一些数据
        await observability.info("Test message")
        await observability.record_metric("test_metric", 42.0)
        
        # 获取仪表盘数据
        dashboard = await observability.get_dashboard_data()
        
        assert dashboard is not None
        assert dashboard.health_status is not None
        assert len(dashboard.recent_logs) > 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self, observability):
        """测试获取统计信息"""
        # 执行一些操作
        await observability.info("Test message")
        await observability.record_metric("test_metric", 42.0)
        
        stats = observability.get_stats()
        
        assert stats["log_calls"] > 0
        assert stats["metric_calls"] > 0
    
    @pytest.mark.asyncio
    async def test_get_status(self, observability):
        """测试获取状态"""
        status = await observability.get_status()
        
        assert status["status"] == "ready"
        assert "config" in status
        assert "stats" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
