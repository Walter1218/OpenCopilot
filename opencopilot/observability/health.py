# observability_module/health.py

"""
健康检查器

负责检查系统和模块的健康状态。
"""

import time
import asyncio
import logging
import psutil
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .models import (
    HealthStatus, HealthStatusModel, ModuleHealth,
    DependencyHealth, PerformanceMetrics, ObservabilityConfig
)

logger = logging.getLogger(__name__)


class HealthChecker:
    """健康检查器
    
    检查系统和模块的健康状态，支持：
    - 模块健康检查
    - 依赖健康检查
    - 性能监控
    - 健康状态查询
    """
    
    def __init__(self, config: Optional[ObservabilityConfig] = None):
        """
        初始化健康检查器
        
        Args:
            config: 可观测性配置
        """
        self.config = config or ObservabilityConfig()
        
        # 模块健康检查函数
        self._module_checkers: Dict[str, Callable] = {}
        
        # 依赖健康检查函数
        self._dependency_checkers: Dict[str, Callable] = {}
        
        # 健康状态缓存
        self._health_status: Optional[HealthStatusModel] = None
        
        # 上次检查时间
        self._last_check_time: float = 0
        
        # 启动时间
        self._start_time: float = time.time()
        
        # 统计信息
        self._stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "unhealthy_checks": 0
        }
    
    def register_module_checker(
        self,
        module_name: str,
        checker: Callable[[], Awaitable[Dict[str, Any]]]
    ):
        """注册模块健康检查函数
        
        Args:
            module_name: 模块名称
            checker: 检查函数
        """
        self._module_checkers[module_name] = checker
        logger.info(f"Registered health checker for module: {module_name}")
    
    def register_dependency_checker(
        self,
        dependency_name: str,
        checker: Callable[[], Awaitable[Dict[str, Any]]]
    ):
        """注册依赖健康检查函数
        
        Args:
            dependency_name: 依赖名称
            checker: 检查函数
        """
        self._dependency_checkers[dependency_name] = checker
        logger.info(f"Registered health checker for dependency: {dependency_name}")
    
    async def check_health(self, force: bool = False) -> HealthStatusModel:
        """检查健康状态
        
        Args:
            force: 是否强制检查
            
        Returns:
            HealthStatusModel: 健康状态模型
        """
        now = time.time()
        
        # 检查是否需要更新
        if not force and self._health_status:
            if now - self._last_check_time < self.config.health_check_interval:
                return self._health_status
        
        # 更新检查时间
        self._last_check_time = now
        
        # 检查模块健康状态
        modules = await self._check_modules()
        
        # 检查依赖健康状态
        dependencies = await self._check_dependencies()
        
        # 获取性能指标
        performance = await self._get_performance_metrics()
        
        # 确定整体状态
        overall_status = self._determine_overall_status(
            modules, dependencies, performance
        )
        
        # 创建健康状态模型
        self._health_status = HealthStatusModel(
            status=overall_status,
            version="1.0.0",
            uptime=now - self._start_time,
            modules=modules,
            dependencies=dependencies,
            performance=performance,
            timestamp=now
        )
        
        # 更新统计
        self._stats["total_checks"] += 1
        if overall_status == HealthStatus.HEALTHY.value:
            self._stats["healthy_checks"] += 1
        else:
            self._stats["unhealthy_checks"] += 1
        
        return self._health_status
    
    async def _check_modules(self) -> Dict[str, ModuleHealth]:
        """检查模块健康状态
        
        Returns:
            Dict[str, ModuleHealth]: 模块健康状态字典
        """
        modules = {}
        
        for module_name, checker in self._module_checkers.items():
            try:
                start_time = time.time()
                
                # 执行检查
                if asyncio.iscoroutinefunction(checker):
                    result = await asyncio.wait_for(
                        checker(),
                        timeout=self.config.health_check_timeout
                    )
                else:
                    result = checker()
                
                # 计算响应时间
                response_time_ms = (time.time() - start_time) * 1000
                
                # 创建模块健康状态
                modules[module_name] = ModuleHealth(
                    module_name=module_name,
                    status=result.get("status", HealthStatus.HEALTHY.value),
                    last_check=time.time(),
                    error_count=result.get("error_count", 0),
                    avg_response_ms=response_time_ms,
                    details=result.get("details", {})
                )
                
            except asyncio.TimeoutError:
                modules[module_name] = ModuleHealth(
                    module_name=module_name,
                    status=HealthStatus.UNHEALTHY.value,
                    last_check=time.time(),
                    error_count=1,
                    details={"error": "Health check timed out"}
                )
                
            except Exception as e:
                modules[module_name] = ModuleHealth(
                    module_name=module_name,
                    status=HealthStatus.UNHEALTHY.value,
                    last_check=time.time(),
                    error_count=1,
                    details={"error": str(e)}
                )
        
        return modules
    
    async def _check_dependencies(self) -> Dict[str, DependencyHealth]:
        """检查依赖健康状态
        
        Returns:
            Dict[str, DependencyHealth]: 依赖健康状态字典
        """
        dependencies = {}
        
        for dep_name, checker in self._dependency_checkers.items():
            try:
                start_time = time.time()
                
                # 执行检查
                if asyncio.iscoroutinefunction(checker):
                    result = await asyncio.wait_for(
                        checker(),
                        timeout=self.config.health_check_timeout
                    )
                else:
                    result = checker()
                
                # 计算响应时间
                response_time_ms = (time.time() - start_time) * 1000
                
                # 创建依赖健康状态
                dependencies[dep_name] = DependencyHealth(
                    dependency_name=dep_name,
                    status=result.get("status", HealthStatus.HEALTHY.value),
                    last_check=time.time(),
                    response_time_ms=response_time_ms,
                    error_message=result.get("error")
                )
                
            except asyncio.TimeoutError:
                dependencies[dep_name] = DependencyHealth(
                    dependency_name=dep_name,
                    status=HealthStatus.UNHEALTHY.value,
                    last_check=time.time(),
                    error_message="Dependency check timed out"
                )
                
            except Exception as e:
                dependencies[dep_name] = DependencyHealth(
                    dependency_name=dep_name,
                    status=HealthStatus.UNHEALTHY.value,
                    last_check=time.time(),
                    error_message=str(e)
                )
        
        return dependencies
    
    async def _get_performance_metrics(self) -> PerformanceMetrics:
        """获取性能指标
        
        Returns:
            PerformanceMetrics: 性能指标
        """
        try:
            # 获取 CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 获取内存信息
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # 获取磁盘信息
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            return PerformanceMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_usage_mb,
                memory_total_mb=memory_total_mb,
                disk_usage_percent=disk_usage_percent
            )
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics()
    
    def _determine_overall_status(
        self,
        modules: Dict[str, ModuleHealth],
        dependencies: Dict[str, DependencyHealth],
        performance: PerformanceMetrics
    ) -> str:
        """确定整体状态
        
        Args:
            modules: 模块健康状态
            dependencies: 依赖健康状态
            performance: 性能指标
            
        Returns:
            str: 整体状态
        """
        # 检查是否有不健康的模块
        for module in modules.values():
            if module.status == HealthStatus.UNHEALTHY.value:
                return HealthStatus.UNHEALTHY.value
        
        # 检查是否有不健康的依赖
        for dep in dependencies.values():
            if dep.status == HealthStatus.UNHEALTHY.value:
                return HealthStatus.UNHEALTHY.value
        
        # 检查性能指标
        if performance.cpu_usage_percent > 90:
            return HealthStatus.DEGRADED.value
        
        if performance.memory_usage_mb / performance.memory_total_mb > 0.9:
            return HealthStatus.DEGRADED.value
        
        # 检查是否有降级的模块
        for module in modules.values():
            if module.status == HealthStatus.DEGRADED.value:
                return HealthStatus.DEGRADED.value
        
        return HealthStatus.HEALTHY.value
    
    def get_cached_health_status(self) -> Optional[HealthStatusModel]:
        """获取缓存的健康状态
        
        Returns:
            Optional[HealthStatusModel]: 健康状态模型
        """
        return self._health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_checks": self._stats["total_checks"],
            "healthy_checks": self._stats["healthy_checks"],
            "unhealthy_checks": self._stats["unhealthy_checks"],
            "registered_modules": len(self._module_checkers),
            "registered_dependencies": len(self._dependency_checkers),
            "last_check_time": self._last_check_time
        }
    
    def clear(self):
        """清空所有检查器"""
        self._module_checkers.clear()
        self._dependency_checkers.clear()
        self._health_status = None
        self._last_check_time = 0
        self._stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "unhealthy_checks": 0
        }
        logger.info("Health checkers cleared")
