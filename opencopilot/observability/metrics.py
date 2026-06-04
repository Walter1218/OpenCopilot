# observability_module/metrics.py

"""
指标收集器

负责收集和管理各种指标数据。
"""

import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import Metric, MetricType, ObservabilityConfig

logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器
    
    收集和管理各种指标数据，支持：
    - 计数器 (Counter)
    - 仪表 (Gauge)
    - 直方图 (Histogram)
    - 摘要 (Summary)
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """
        初始化指标收集器
        
        Args:
            config: 可观测性配置
        """
        self.config = config or ObservabilityConfig()
        
        # 指标存储: metric_name -> List[Metric]
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        
        # 计数器值: metric_name -> float
        self._counters: Dict[str, float] = defaultdict(float)
        
        # 仪表值: metric_name -> float
        self._gauges: Dict[str, float] = defaultdict(float)
        
        # 统计信息
        self._stats = {
            "total_metrics": 0,
            "metrics_by_type": {t.value: 0 for t in MetricType}
        }
    
    def record_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> Metric:
        """记录计数器指标
        
        Args:
            name: 指标名称
            value: 增加的值
            tags: 标签
            unit: 单位
            
        Returns:
            Metric: 指标对象
        """
        # 更新计数器
        self._counters[name] += value
        
        # 创建指标对象
        metric = Metric(
            name=name,
            value=self._counters[name],
            timestamp=time.time(),
            tags=tags or {},
            unit=unit,
            metric_type=MetricType.COUNTER.value
        )
        
        # 存储指标
        self._store_metric(name, metric)
        
        return metric
    
    def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> Metric:
        """记录仪表指标
        
        Args:
            name: 指标名称
            value: 当前值
            tags: 标签
            unit: 单位
            
        Returns:
            Metric: 指标对象
        """
        # 更新仪表值
        self._gauges[name] = value
        
        # 创建指标对象
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            unit=unit,
            metric_type=MetricType.GAUGE.value
        )
        
        # 存储指标
        self._store_metric(name, metric)
        
        return metric
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> Metric:
        """记录直方图指标
        
        Args:
            name: 指标名称
            value: 观测值
            tags: 标签
            unit: 单位
            
        Returns:
            Metric: 指标对象
        """
        # 创建指标对象
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            unit=unit,
            metric_type=MetricType.HISTOGRAM.value
        )
        
        # 存储指标
        self._store_metric(name, metric)
        
        return metric
    
    def record_summary(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ) -> Metric:
        """记录摘要指标
        
        Args:
            name: 指标名称
            value: 观测值
            tags: 标签
            unit: 单位
            
        Returns:
            Metric: 指标对象
        """
        # 创建指标对象
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            unit=unit,
            metric_type=MetricType.SUMMARY.value
        )
        
        # 存储指标
        self._store_metric(name, metric)
        
        return metric
    
    def _store_metric(self, name: str, metric: Metric):
        """存储指标
        
        Args:
            name: 指标名称
            metric: 指标对象
        """
        # 添加到存储
        self._metrics[name].append(metric)
        
        # 限制存储数量
        if len(self._metrics[name]) > self.config.metrics_max_entries:
            self._metrics[name] = self._metrics[name][-self.config.metrics_max_entries:]
        
        # 更新统计
        self._stats["total_metrics"] += 1
        if metric.metric_type in self._stats["metrics_by_type"]:
            self._stats["metrics_by_type"][metric.metric_type] += 1
    
    def get_counter(self, name: str) -> float:
        """获取计数器值
        
        Args:
            name: 指标名称
            
        Returns:
            float: 计数器值
        """
        return self._counters.get(name, 0.0)
    
    def get_gauge(self, name: str) -> float:
        """获取仪表值
        
        Args:
            name: 指标名称
            
        Returns:
            float: 仪表值
        """
        return self._gauges.get(name, 0.0)
    
    def get_metric_history(
        self,
        name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Metric]:
        """获取指标历史
        
        Args:
            name: 指标名称
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[Metric]: 指标列表
        """
        metrics = self._metrics.get(name, [])
        
        # 应用时间过滤
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # 按时间倒序排列
        metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        return metrics[:limit]
    
    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """获取指标统计信息
        
        Args:
            name: 指标名称
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        metrics = self._metrics.get(name, [])
        
        if not metrics:
            return {
                "name": name,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
                "sum": 0.0
            }
        
        values = [m.value for m in metrics]
        
        return {
            "name": name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
            "latest": values[-1] if values else None
        }
    
    def get_all_metrics(self) -> List[str]:
        """获取所有指标名称
        
        Returns:
            List[str]: 指标名称列表
        """
        return list(self._metrics.keys())
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要
        
        Returns:
            Dict[str, Any]: 指标摘要
        """
        summary = {}
        
        for name, metrics in self._metrics.items():
            if metrics:
                latest = metrics[-1]
                summary[name] = {
                    "latest_value": latest.value,
                    "latest_timestamp": latest.timestamp,
                    "metric_type": latest.metric_type,
                    "count": len(metrics)
                }
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_metrics": self._stats["total_metrics"],
            "metrics_by_type": dict(self._stats["metrics_by_type"]),
            "unique_metric_names": len(self._metrics),
            "counters": len(self._counters),
            "gauges": len(self._gauges)
        }
    
    def cleanup(self, max_age_hours: float = 24.0):
        """清理过期指标
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for name in list(self._metrics.keys()):
            self._metrics[name] = [
                m for m in self._metrics[name]
                if now - m.timestamp <= max_age_seconds
            ]
            
            # 删除空列表
            if not self._metrics[name]:
                del self._metrics[name]
        
        logger.info(f"Cleaned up metrics older than {max_age_hours} hours")
    
    def clear(self):
        """清空所有指标"""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._stats = {
            "total_metrics": 0,
            "metrics_by_type": {t.value: 0 for t in MetricType}
        }
        logger.info("All metrics cleared")
    
    def export_json(self, limit: Optional[int] = None) -> str:
        """导出指标为 JSON
        
        Args:
            limit: 每个指标导出数量限制
            
        Returns:
            str: JSON 字符串
        """
        import json
        
        data = {}
        
        for name, metrics in self._metrics.items():
            if limit:
                metrics = metrics[-limit:]
            
            data[name] = [
                {
                    "value": m.value,
                    "timestamp": m.timestamp,
                    "tags": m.tags,
                    "unit": m.unit,
                    "metric_type": m.metric_type
                }
                for m in metrics
            ]
        
        return json.dumps(data, indent=2, default=str)
