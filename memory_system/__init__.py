"""
记忆系统模块

提供智能记忆管理功能，完全兼容现有 ASUAgentMemory 接口。
支持长期记忆、语义检索、自动组织、遗忘机制等高级功能。
"""

from .core import MemoryManager, MemoryEntry, MemoryType
from .storage import MemoryStorage, SQLiteMemoryStorage
from .retrieval import MemoryRetrieval, SemanticRetrieval
from .organization import MemoryOrganization, AutoTagger
from .forgetting import MemoryForgetting, ForgettingStrategy
from .compression import MemoryCompression, CompressionStrategy
from .api import MemoryAPI
from .config import ConfigManager, MemoryTypeQuota, ContextBudgetConfig, MemorySystemConfig
from .quota_manager import QuotaManager, MemoryStats

__version__ = "1.1.0"
__all__ = [
    # 核心类
    "MemoryManager",
    "MemoryEntry",
    "MemoryType",
    
    # 存储
    "MemoryStorage",
    "SQLiteMemoryStorage",
    
    # 检索
    "MemoryRetrieval",
    "SemanticRetrieval",
    
    # 组织
    "MemoryOrganization",
    "AutoTagger",
    
    # 遗忘
    "MemoryForgetting",
    "ForgettingStrategy",
    
    # 压缩
    "MemoryCompression",
    "CompressionStrategy",
    
    # API
    "MemoryAPI",
    
    # 配置
    "ConfigManager",
    "MemoryTypeQuota",
    "ContextBudgetConfig",
    "MemorySystemConfig",
    
    # 配额管理
    "QuotaManager",
    "MemoryStats",
]

# 默认实例
_default_manager = None
_default_config = None
_default_quota_manager = None

def get_default_manager() -> MemoryManager:
    """获取默认的记忆管理器实例"""
    global _default_manager
    if _default_manager is None:
        _default_manager = MemoryManager()
    return _default_manager

def set_default_manager(manager: MemoryManager):
    """设置默认的记忆管理器实例"""
    global _default_manager
    _default_manager = manager

def get_default_config() -> ConfigManager:
    """获取默认的配置管理器实例"""
    global _default_config
    if _default_config is None:
        from .config import get_config
        _default_config = get_config()
    return _default_config

def get_default_quota_manager() -> QuotaManager:
    """获取默认的配额管理器实例"""
    global _default_quota_manager
    if _default_quota_manager is None:
        from .quota_manager import get_quota_manager
        _default_quota_manager = get_quota_manager()
    return _default_quota_manager
