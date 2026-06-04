# skill_architecture/config_manager.py

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


@dataclass
class ConfigSource:
    """配置源"""
    name: str
    path: str
    format: str = "yaml"  # yaml, json, env
    priority: int = 0
    watch: bool = False
    last_modified: Optional[datetime] = None


class ConfigManager:
    """配置管理器 - 增强版
    
    功能：
    1. YAML配置文件支持
    2. 环境变量支持
    3. 动态配置更新
    4. 配置验证
    5. 配置合并策略
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        self._config_dir = config_dir or os.path.join(os.getcwd(), "config")
        self._configs: Dict[str, Any] = {}
        self._sources: Dict[str, ConfigSource] = {}
        self._watchers: Dict[str, Observer] = {}
        self._callbacks: List[callable] = []
        self._lock = asyncio.Lock()
        
        # 默认配置
        self._defaults: Dict[str, Any] = {
            "skill_architecture": {
                "cache_size": 100,
                "cache_ttl": 300,
                "max_retries": 3,
                "retry_delay": 1.0,
                "backoff_factor": 2.0,
                "default_timeout": 30,
                "max_concurrent": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
        
        # 初始化配置目录
        self._init_config_dir()
    
    def _init_config_dir(self):
        """初始化配置目录"""
        os.makedirs(self._config_dir, exist_ok=True)
        
        # 创建默认配置文件
        default_config_path = os.path.join(self._config_dir, "default.yaml")
        if not os.path.exists(default_config_path):
            self._save_yaml(default_config_path, self._defaults)
    
    async def load_config(
        self, 
        name: str, 
        path: Optional[str] = None,
        format: str = "yaml",
        priority: int = 0,
        watch: bool = False
    ) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            name: 配置名称
            path: 配置文件路径
            format: 配置格式 (yaml, json, env)
            priority: 优先级（数字越大优先级越高）
            watch: 是否监听文件变化
        
        Returns:
            Dict[str, Any]: 配置数据
        """
        async with self._lock:
            # 如果没有指定路径，使用默认路径
            if not path:
                path = os.path.join(self._config_dir, f"{name}.{format}")
            
            # 创建配置源
            source = ConfigSource(
                name=name,
                path=path,
                format=format,
                priority=priority,
                watch=watch
            )
            
            # 加载配置
            config_data = await self._load_from_source(source)
            
            if config_data:
                self._configs[name] = config_data
                self._sources[name] = source
                
                # 设置文件监听
                if watch:
                    self._setup_watch(source)
                
                logger.info(f"Loaded config: {name} from {path}")
                return config_data
            
            return {}
    
    async def _load_from_source(self, source: ConfigSource) -> Dict[str, Any]:
        """从配置源加载"""
        try:
            if not os.path.exists(source.path):
                logger.warning(f"Config file not found: {source.path}")
                return {}
            
            # 检查文件修改时间
            mtime = datetime.fromtimestamp(os.path.getmtime(source.path))
            if source.last_modified and mtime <= source.last_modified:
                return self._configs.get(source.name, {})
            
            source.last_modified = mtime
            
            # 根据格式加载
            if source.format == "yaml":
                return self._load_yaml(source.path)
            elif source.format == "json":
                return self._load_json(source.path)
            elif source.format == "env":
                return self._load_env(source.path)
            else:
                logger.error(f"Unsupported config format: {source.format}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to load config from {source.path}: {e}")
            return {}
    
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """加载YAML配置"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_json(self, path: str) -> Dict[str, Any]:
        """加载JSON配置"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_env(self, path: str) -> Dict[str, Any]:
        """加载环境变量配置"""
        config = {}
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        config[key] = value
        return config
    
    def _save_yaml(self, path: str, data: Dict[str, Any]):
        """保存YAML配置"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def _setup_watch(self, source: ConfigSource):
        """设置文件监听"""
        if source.name in self._watchers:
            return
        
        class ConfigHandler(FileSystemEventHandler):
            def __init__(self, manager, source):
                self.manager = manager
                self.source = source
            
            def on_modified(self, event):
                if event.src_path == self.source.path:
                    asyncio.run(self.manager._on_config_changed(self.source))
        
        handler = ConfigHandler(self, source)
        observer = Observer()
        observer.schedule(handler, os.path.dirname(source.path), recursive=False)
        observer.start()
        
        self._watchers[source.name] = observer
        logger.info(f"Started watching config: {source.name}")
    
    async def _on_config_changed(self, source: ConfigSource):
        """配置文件变化处理"""
        logger.info(f"Config file changed: {source.path}")
        
        # 重新加载配置
        config_data = await self._load_from_source(source)
        if config_data:
            self._configs[source.name] = config_data
            
            # 通知回调
            for callback in self._callbacks:
                try:
                    await callback(source.name, config_data)
                except Exception as e:
                    logger.warning(f"Config callback failed: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔，如 "skill_architecture.cache_size"）
            default: 默认值
        
        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self._configs
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, source_name: str = "runtime"):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            source_name: 配置源名称
        """
        keys = key.split('.')
        
        if source_name not in self._configs:
            self._configs[source_name] = {}
        
        config = self._configs[source_name]
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_merged_config(self) -> Dict[str, Any]:
        """获取合并后的配置（按优先级）"""
        merged = self._defaults.copy()
        
        # 按优先级排序
        sorted_sources = sorted(
            self._sources.values(),
            key=lambda x: x.priority
        )
        
        # 合并配置
        for source in sorted_sources:
            if source.name in self._configs:
                self._deep_merge(merged, self._configs[source.name])
        
        return merged
    
    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def add_callback(self, callback: callable):
        """添加配置变化回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: callable):
        """移除配置变化回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        return self._configs.copy()
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """获取所有配置源"""
        return [
            {
                "name": source.name,
                "path": source.path,
                "format": source.format,
                "priority": source.priority,
                "watch": source.watch
            }
            for source in self._sources.values()
        ]
    
    async def reload_all(self):
        """重新加载所有配置"""
        async with self._lock:
            for name, source in self._sources.items():
                config_data = await self._load_from_source(source)
                if config_data:
                    self._configs[name] = config_data
                    logger.info(f"Reloaded config: {name}")
    
    def stop_watchers(self):
        """停止所有文件监听"""
        for name, observer in self._watchers.items():
            observer.stop()
            observer.join()
            logger.info(f"Stopped watching config: {name}")
        
        self._watchers.clear()
    
    def __del__(self):
        """析构函数"""
        self.stop_watchers()


class EnvironmentConfig:
    """环境变量配置"""
    
    def __init__(self, prefix: str = "OPENCOPILOT_"):
        self._prefix = prefix
        self._cache: Dict[str, str] = {}
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        full_key = f"{self._prefix}{key}"
        
        if full_key in self._cache:
            return self._cache[full_key]
        
        value = os.environ.get(full_key, default)
        if value is not None:
            self._cache[full_key] = value
        
        return value
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数环境变量"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数环境变量"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔环境变量"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_list(self, key: str, separator: str = ",", default: Optional[List[str]] = None) -> List[str]:
        """获取列表环境变量"""
        value = self.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator)]
    
    def set(self, key: str, value: str):
        """设置环境变量"""
        full_key = f"{self._prefix}{key}"
        os.environ[full_key] = str(value)
        self._cache[full_key] = str(value)
    
    def get_all(self) -> Dict[str, str]:
        """获取所有相关环境变量"""
        result = {}
        for key, value in os.environ.items():
            if key.startswith(self._prefix):
                result[key[len(self._prefix):]] = value
        return result