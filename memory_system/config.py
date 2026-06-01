"""
记忆系统配置模块

提供记忆类型配额管理、动态预算调整等功能。
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"   # 短期记忆（会话内）
    LONG_TERM = "long_term"     # 长期记忆（跨会话）
    WORKING = "working"         # 工作记忆（当前任务）
    EPISODIC = "episodic"       # 情景记忆（特定事件）
    SEMANTIC = "semantic"       # 语义记忆（知识事实）
    PROCEDURAL = "procedural"   # 程序记忆（操作步骤）


@dataclass
class MemoryTypeQuota:
    """记忆类型配额配置"""
    max_count: int = 1000  # 最大记忆条数
    max_chars: int = 500000  # 最大字符数
    max_age_days: int = 365  # 最大保留天数
    importance_threshold: float = 0.3  # 重要性阈值
    access_count_threshold: int = 2  # 访问次数阈值


@dataclass
class ContextBudgetConfig:
    """上下文预算配置"""
    max_input_chars: int = 120000  # 最大输入字符数
    reserve_output_chars: int = 30000  # 预留输出字符数
    recent_turns: int = 12  # 保留的最近对话轮数
    max_history_msg_chars: int = 8000  # 单条历史消息最大字符数
    
    # 预算分配比例
    history_budget_ratio: float = 0.45  # 历史消息预算比例
    user_budget_ratio: float = 0.55  # 当前输入预算比例
    
    # 动态调整参数
    enable_dynamic_adjustment: bool = True  # 启用动态调整
    model_limits: Dict[str, int] = field(default_factory=lambda: {
        "minimax-m2.7": 200000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
    })


@dataclass
class MemorySystemConfig:
    """记忆系统完整配置"""
    # 记忆类型配额
    memory_type_quotas: Dict[MemoryType, MemoryTypeQuota] = field(default_factory=lambda: {
        MemoryType.SHORT_TERM: MemoryTypeQuota(
            max_count=100,
            max_chars=50000,
            max_age_days=1,
            importance_threshold=0.2,
            access_count_threshold=1
        ),
        MemoryType.LONG_TERM: MemoryTypeQuota(
            max_count=1000,
            max_chars=500000,
            max_age_days=365,
            importance_threshold=0.5,
            access_count_threshold=3
        ),
        MemoryType.WORKING: MemoryTypeQuota(
            max_count=50,
            max_chars=25000,
            max_age_days=7,
            importance_threshold=0.4,
            access_count_threshold=2
        ),
        MemoryType.EPISODIC: MemoryTypeQuota(
            max_count=200,
            max_chars=100000,
            max_age_days=90,
            importance_threshold=0.3,
            access_count_threshold=2
        ),
        MemoryType.SEMANTIC: MemoryTypeQuota(
            max_count=500,
            max_chars=250000,
            max_age_days=180,
            importance_threshold=0.6,
            access_count_threshold=4
        ),
        MemoryType.PROCEDURAL: MemoryTypeQuota(
            max_count=100,
            max_chars=50000,
            max_age_days=30,
            importance_threshold=0.4,
            access_count_threshold=3
        ),
    })
    
    # 上下文预算配置
    context_budget: ContextBudgetConfig = field(default_factory=ContextBudgetConfig)
    
    # 遗忘机制配置
    forgetting_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_auto_forgetting": True,
        "forgetting_interval_hours": 24,
        "min_importance_to_keep": 0.3,
        "min_access_count_to_keep": 2,
    })
    
    # 压缩机制配置
    compression_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_auto_compression": True,
        "compression_interval_hours": 12,
        "compression_ratio_threshold": 0.7,
    })
    
    # 缓存配置
    cache_config: Dict[str, Any] = field(default_factory=lambda: {
        "enable_memory_cache": True,
        "cache_size_limit": 1000,
        "cache_ttl_seconds": 3600,
    })


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径（可选）
        """
        self.config_file = config_file
        self.config = MemorySystemConfig()
        
        # 从环境变量加载配置
        self._load_from_env()
        
        # 从文件加载配置（如果提供）
        if config_file:
            self._load_from_file(config_file)
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # 上下文预算配置
        self.config.context_budget.max_input_chars = int(
            os.getenv("ASU_MAX_INPUT_CHARS", str(self.config.context_budget.max_input_chars))
        )
        self.config.context_budget.reserve_output_chars = int(
            os.getenv("ASU_RESERVE_OUTPUT_CHARS", str(self.config.context_budget.reserve_output_chars))
        )
        self.config.context_budget.recent_turns = int(
            os.getenv("ASU_RECENT_TURNS", str(self.config.context_budget.recent_turns))
        )
        self.config.context_budget.max_history_msg_chars = int(
            os.getenv("ASU_MAX_HISTORY_MSG_CHARS", str(self.config.context_budget.max_history_msg_chars))
        )
    
    def _load_from_file(self, config_file: str):
        """从文件加载配置"""
        # 这里可以实现从 JSON/YAML 文件加载配置的逻辑
        pass
    
    def get_memory_type_quota(self, memory_type: MemoryType) -> MemoryTypeQuota:
        """获取记忆类型配额"""
        return self.config.memory_type_quotas.get(memory_type, MemoryTypeQuota())
    
    def get_context_budget(self) -> ContextBudgetConfig:
        """获取上下文预算配置"""
        return self.config.context_budget
    
    def get_model_limit(self, model_name: str) -> int:
        """获取模型上下文限制"""
        return self.config.context_budget.model_limits.get(model_name, 200000)
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "memory_type_quotas": {
                k.value: {
                    "max_count": v.max_count,
                    "max_chars": v.max_chars,
                    "max_age_days": v.max_age_days,
                    "importance_threshold": v.importance_threshold,
                    "access_count_threshold": v.access_count_threshold,
                }
                for k, v in self.config.memory_type_quotas.items()
            },
            "context_budget": {
                "max_input_chars": self.config.context_budget.max_input_chars,
                "reserve_output_chars": self.config.context_budget.reserve_output_chars,
                "recent_turns": self.config.context_budget.recent_turns,
                "max_history_msg_chars": self.config.context_budget.max_history_msg_chars,
                "history_budget_ratio": self.config.context_budget.history_budget_ratio,
                "user_budget_ratio": self.config.context_budget.user_budget_ratio,
                "enable_dynamic_adjustment": self.config.context_budget.enable_dynamic_adjustment,
            },
            "forgetting_config": self.config.forgetting_config,
            "compression_config": self.config.compression_config,
            "cache_config": self.config.cache_config,
        }


# 默认配置实例
default_config = ConfigManager()


def get_config() -> ConfigManager:
    """获取默认配置管理器"""
    return default_config


def create_config(config_file: Optional[str] = None) -> ConfigManager:
    """创建配置管理器"""
    return ConfigManager(config_file)