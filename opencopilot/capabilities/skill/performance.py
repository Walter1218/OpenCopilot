# skill_architecture/performance.py

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 300.0  # 5分钟
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """访问缓存"""
        self.last_accessed = time.time()
        self.access_count += 1
        return self.value


class ResultCache:
    """结果缓存 - 支持LRU和TTL"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    self._hits += 1
                    return entry.access()
                else:
                    # 过期，删除
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存"""
        async with self._lock:
            # 如果缓存已满，删除最旧的
            if len(self._cache) >= self._max_size:
                self._evict()
            
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self._default_ttl
            )
    
    async def delete(self, key: str):
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self):
        """清除所有缓存"""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def _evict(self):
        """驱逐最旧的缓存"""
        if not self._cache:
            return
        
        # 找到最旧的条目
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "default_ttl": self._default_ttl
        }


class AsyncPool:
    """异步任务池"""
    
    def __init__(self, max_workers: int = 10):
        self._max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self._tasks: List[asyncio.Task] = []
        self._results: Dict[str, Any] = {}
        self._errors: Dict[str, Exception] = {}
    
    async def submit(
        self, 
        task_id: str,
        coro: Callable[..., Awaitable[Any]],
        *args, 
        **kwargs
    ) -> Any:
        """提交任务"""
        async with self._semaphore:
            try:
                result = await coro(*args, **kwargs)
                self._results[task_id] = result
                return result
            except Exception as e:
                self._errors[task_id] = e
                raise
    
    async def submit_batch(
        self, 
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量提交任务"""
        async_tasks = []
        
        for task_info in tasks:
            task_id = task_info.get("id", str(len(async_tasks)))
            coro = task_info["coro"]
            args = task_info.get("args", ())
            kwargs = task_info.get("kwargs", {})
            
            async_tasks.append(
                self.submit(task_id, coro, *args, **kwargs)
            )
        
        # 并行执行所有任务
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 组织结果
        result_dict = {}
        for i, result in enumerate(results):
            task_id = tasks[i].get("id", str(i))
            if isinstance(result, Exception):
                result_dict[task_id] = {"error": str(result)}
            else:
                result_dict[task_id] = result
        
        return result_dict
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "max_workers": self._max_workers,
            "pending_tasks": len(self._tasks),
            "completed_results": len(self._results),
            "errors": len(self._errors)
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, float] = {}
    
    def start_timer(self, name: str):
        """开始计时"""
        self._timers[name] = time.time()
    
    def stop_timer(self, name: str) -> float:
        """停止计时"""
        if name not in self._timers:
            return 0.0
        
        elapsed = time.time() - self._timers[name]
        self._metrics[name].append(elapsed)
        del self._timers[name]
        return elapsed
    
    def record_metric(self, name: str, value: float):
        """记录指标"""
        self._metrics[name].append(value)
    
    def increment_counter(self, name: str, value: int = 1):
        """增加计数器"""
        self._counters[name] += value
    
    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """获取指标统计"""
        if name not in self._metrics:
            return {}
        
        values = self._metrics[name]
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values)
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        stats = {
            "metrics": {},
            "counters": self._counters.copy()
        }
        
        for name in self._metrics:
            stats["metrics"][name] = self.get_metric_stats(name)
        
        return stats
    
    def reset(self):
        """重置所有统计"""
        self._metrics.clear()
        self._counters.clear()
        self._timers.clear()


def cache_result(ttl: float = 300.0, max_size: int = 1000):
    """缓存装饰器"""
    cache = ResultCache(max_size=max_size, default_ttl=ttl)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            key_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            
            # 检查缓存
            result = await cache.get(key)
            if result is not None:
                return result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            await cache.set(key, result)
            
            return result
        
        wrapper.cache = cache
        return wrapper
    
    return decorator


def monitor_performance(monitor: PerformanceMonitor):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = f"{func.__module__}.{func.__name__}"
            
            monitor.start_timer(name)
            try:
                result = await func(*args, **kwargs)
                monitor.increment_counter(f"{name}.success")
                return result
            except Exception as e:
                monitor.increment_counter(f"{name}.error")
                raise
            finally:
                elapsed = monitor.stop_timer(name)
                monitor.record_metric(f"{name}.time", elapsed)
        
        return wrapper
    
    return decorator


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self._cache = ResultCache()
        self._pool = AsyncPool()
        self._monitor = PerformanceMonitor()
        
        # 优化策略
        self._strategies: Dict[str, Callable] = {
            "cache": self._apply_cache_strategy,
            "parallel": self._apply_parallel_strategy,
            "batch": self._apply_batch_strategy,
            "lazy": self._apply_lazy_strategy
        }
    
    async def optimize(
        self, 
        func: Callable, 
        strategy: str,
        **kwargs
    ) -> Any:
        """应用优化策略"""
        if strategy not in self._strategies:
            raise ValueError(f"Unknown optimization strategy: {strategy}")
        
        return await self._strategies[strategy](func, **kwargs)
    
    async def _apply_cache_strategy(
        self, 
        func: Callable, 
        ttl: float = 300.0,
        **kwargs
    ) -> Any:
        """应用缓存策略"""
        # 生成缓存键
        key_data = {
            "func": func.__name__,
            "kwargs": kwargs
        }
        key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        
        # 检查缓存
        result = await self._cache.get(key)
        if result is not None:
            return result
        
        # 执行函数
        result = await func(**kwargs)
        
        # 缓存结果
        await self._cache.set(key, result, ttl=ttl)
        
        return result
    
    async def _apply_parallel_strategy(
        self, 
        func: Callable,
        tasks: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """应用并行策略"""
        return await self._pool.submit_batch(tasks)
    
    async def _apply_batch_strategy(
        self, 
        func: Callable,
        items: List[Any],
        batch_size: int = 10,
        **kwargs
    ) -> List[Any]:
        """应用批量策略"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await func(batch, **kwargs)
            results.extend(batch_results)
        
        return results
    
    async def _apply_lazy_strategy(
        self, 
        func: Callable,
        **kwargs
    ) -> Any:
        """应用懒加载策略"""
        # 延迟执行，等待实际需要时再执行
        return await func(**kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "cache": self._cache.get_stats(),
            "pool": self._pool.get_stats(),
            "monitor": self._monitor.get_all_stats()
        }
    
    async def cleanup(self):
        """清理资源"""
        await self._cache.clear()
        self._monitor.reset()