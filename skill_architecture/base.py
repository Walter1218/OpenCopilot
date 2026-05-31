# skill_architecture/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class BaseSkill(ABC):
    """Skill 基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Skill
        
        Args:
            config: 配置字典
        """
        self._config = config or {}
        self._status = SkillStatus.INITIALIZED
        self._validate_config()
    
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        pass
    
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        pass
    
    async def can_handle(self, context: SkillContext) -> float:
        """
        判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 默认实现：检查意图是否匹配
        if context.intent in self.metadata.intents:
            return 0.8
        return 0.0
    
    async def initialize(self) -> bool:
        """
        初始化 Skill（异步）
        
        Returns:
            bool: 是否成功
        """
        return True
    
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    def _validate_config(self) -> None:
        """验证配置"""
        # 子类可以覆盖此方法进行配置验证
        pass
    
    @property
    def status(self) -> SkillStatus:
        """获取状态"""
        return self._status
    
    @status.setter
    def status(self, value: SkillStatus) -> None:
        """设置状态"""
        self._status = value
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self._config.update(config)
        self._validate_config()