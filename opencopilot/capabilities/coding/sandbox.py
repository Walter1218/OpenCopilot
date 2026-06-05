# code_executor/sandbox.py

"""
沙盒管理器

提供代码执行的隔离环境，限制资源使用和系统访问。
"""

import asyncio
import os
import sys
import tempfile
import shutil
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None
    _HAS_PSUTIL = False
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .models import SandboxConfig, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class SandboxManager:
    """沙盒管理器
    
    提供代码执行的隔离环境，包括：
    - 资源限制（CPU、内存、磁盘）
    - 文件系统隔离
    - 网络限制
    - 进程隔离
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        初始化沙盒管理器
        
        Args:
            config: 沙盒配置
        """
        self.config = config or SandboxConfig()
        self._active_sandboxes: Dict[str, str] = {}  # sandbox_id -> temp_dir
    
    async def create_sandbox(self) -> str:
        """创建沙盒环境
        
        Returns:
            str: 沙盒 ID
        """
        import uuid
        sandbox_id = str(uuid.uuid4())
        
        # 创建临时目录作为沙盒
        temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id[:8]}_")
        
        # 设置权限
        os.chmod(temp_dir, 0o755)
        
        # 创建必要的子目录
        os.makedirs(os.path.join(temp_dir, "tmp"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "workspace"), exist_ok=True)
        
        # 记录沙盒
        self._active_sandboxes[sandbox_id] = temp_dir
        
        logger.info(f"Created sandbox {sandbox_id} at {temp_dir}")
        
        return sandbox_id
    
    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """销毁沙盒环境
        
        Args:
            sandbox_id: 沙盒 ID
            
        Returns:
            bool: 是否成功销毁
        """
        if sandbox_id not in self._active_sandboxes:
            return False
        
        temp_dir = self._active_sandboxes[sandbox_id]
        
        try:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 移除记录
            del self._active_sandboxes[sandbox_id]
            
            logger.info(f"Destroyed sandbox {sandbox_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy sandbox {sandbox_id}: {e}")
            return False
    
    async def get_sandbox_path(self, sandbox_id: str) -> Optional[str]:
        """获取沙盒路径
        
        Args:
            sandbox_id: 沙盒 ID
            
        Returns:
            Optional[str]: 沙盒路径
        """
        return self._active_sandboxes.get(sandbox_id)
    
    async def list_sandboxes(self) -> List[str]:
        """列出所有沙盒
        
        Returns:
            List[str]: 沙盒 ID 列表
        """
        return list(self._active_sandboxes.keys())
    
    async def cleanup_all(self) -> int:
        """清理所有沙盒
        
        Returns:
            int: 清理的沙盒数量
        """
        count = 0
        for sandbox_id in list(self._active_sandboxes.keys()):
            if await self.destroy_sandbox(sandbox_id):
                count += 1
        
        return count
    
    def get_resource_limits(self) -> Dict[str, Any]:
        """获取资源配置
        
        Returns:
            Dict[str, Any]: 资源限制配置
        """
        return {
            "max_memory_mb": self.config.max_memory_mb,
            "max_cpu_percent": self.config.max_cpu_percent,
            "max_disk_mb": self.config.max_disk_mb,
            "timeout": self.config.timeout,
            "allow_network": self.config.allow_network,
            "allowed_hosts": self.config.allowed_hosts,
            "read_only_paths": self.config.read_only_paths,
            "writable_paths": self.config.writable_paths
        }
    
    async def check_resource_usage(self, sandbox_id: str) -> Dict[str, Any]:
        """检查沙盒资源使用情况
        
        Args:
            sandbox_id: 沙盒 ID
            
        Returns:
            Dict[str, Any]: 资源使用情况
        """
        if sandbox_id not in self._active_sandboxes:
            return {"error": "Sandbox not found"}
        
        temp_dir = self._active_sandboxes[sandbox_id]
        
        try:
            # 检查磁盘使用
            disk_usage = shutil.disk_usage(temp_dir)
            
            # 检查目录大小
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(temp_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except:
                        pass
            
            return {
                "sandbox_id": sandbox_id,
                "path": temp_dir,
                "disk_total_mb": disk_usage.total / (1024 * 1024),
                "disk_used_mb": disk_usage.used / (1024 * 1024),
                "disk_free_mb": disk_usage.free / (1024 * 1024),
                "sandbox_size_mb": total_size / (1024 * 1024)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def enforce_limits(self, process: asyncio.subprocess.Process) -> bool:
        """强制执行资源限制
        
        Args:
            process: 进程对象
            
        Returns:
            bool: 是否在限制内
        """
        if not _HAS_PSUTIL:
            return True  # psutil 不可用时跳过资源限制
        
        try:
            # 获取进程信息
            p = psutil.Process(process.pid)
            
            # 检查内存使用
            memory_info = p.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            if memory_mb > self.config.max_memory_mb:
                logger.warning(f"Process {process.pid} exceeded memory limit: {memory_mb}MB > {self.config.max_memory_mb}MB")
                return False
            
            # 检查 CPU 使用
            cpu_percent = p.cpu_percent(interval=0.1)
            
            if cpu_percent > self.config.max_cpu_percent:
                logger.warning(f"Process {process.pid} exceeded CPU limit: {cpu_percent}% > {self.config.max_cpu_percent}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to enforce limits: {e}")
            return True
    
    def create_isolated_env(self, sandbox_id: str, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """创建隔离的环境变量
        
        Args:
            sandbox_id: 沙盒 ID
            base_env: 基础环境变量
            
        Returns:
            Dict[str, str]: 隔离的环境变量
        """
        env = base_env or {}
        
        # 添加沙盒特定的环境变量
        env["SANDBOX_ID"] = sandbox_id
        env["SANDBOX_PATH"] = self._active_sandboxes.get(sandbox_id, "")
        
        # 限制 PATH
        if self.config.restrict_syscalls:
            # 只保留基本路径
            basic_paths = ["/usr/bin", "/bin", "/usr/local/bin"]
            env["PATH"] = ":".join(basic_paths)
        
        # 添加用户配置的环境变量
        env.update(self.config.env_vars)
        
        return env
    
    def get_filesystem_restrictions(self) -> Dict[str, List[str]]:
        """获取文件系统限制
        
        Returns:
            Dict[str, List[str]]: 文件系统限制配置
        """
        return {
            "read_only": self.config.read_only_paths,
            "writable": self.config.writable_paths
        }


class ResourceMonitor:
    """资源监控器
    
    监控沙盒中的资源使用情况。
    """
    
    def __init__(self, sandbox_manager: SandboxManager):
        """
        初始化资源监控器
        
        Args:
            sandbox_manager: 沙盒管理器
        """
        self.sandbox_manager = sandbox_manager
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, sandbox_id: str, interval: float = 1.0):
        """开始监控
        
        Args:
            sandbox_id: 沙盒 ID
            interval: 监控间隔（秒）
        """
        self._monitoring = True
        
        async def monitor_loop():
            while self._monitoring:
                usage = await self.sandbox_manager.check_resource_usage(sandbox_id)
                logger.debug(f"Sandbox {sandbox_id} resource usage: {usage}")
                await asyncio.sleep(interval)
        
        self._monitor_task = asyncio.create_task(monitor_loop())
    
    async def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    async def get_usage_report(self, sandbox_id: str) -> Dict[str, Any]:
        """获取使用报告
        
        Args:
            sandbox_id: 沙盒 ID
            
        Returns:
            Dict[str, Any]: 使用报告
        """
        return await self.sandbox_manager.check_resource_usage(sandbox_id)
