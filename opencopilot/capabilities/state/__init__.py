"""
状态管理模块 - OpenCopilot Agent Core 模块

职责：
- 管理智能体的任务状态和会话状态
- 提供检查点和恢复机制
- 支持状态持久化和查询
- 与现有 ASUAgentMemory 完全兼容

设计原则：
- 乐高积木式：可独立使用，也可与其他模块组合
- 向后兼容：完全兼容现有 ASUAgentMemory 接口
- 可插拔替换：内部实现可替换，接口不变
"""

from .core import StateManager, TaskState, SessionState, TaskStatus
from .persistence import StatePersistence, SQLiteStateStorage, FileStateStorage
from .checkpoint import CheckpointManager, Checkpoint
from .recovery import RecoveryManager, RecoveryStrategy

__version__ = "1.0.0"
__all__ = [
    # 核心类
    "StateManager",
    "TaskState",
    "SessionState",
    "TaskStatus",
    
    # 持久化
    "StatePersistence",
    "SQLiteStateStorage",
    "FileStateStorage",
    
    # 检查点
    "CheckpointManager",
    "Checkpoint",
    
    # 恢复
    "RecoveryManager",
    "RecoveryStrategy",
]

# 默认实例（兼容现有用法）
_default_manager = None

def get_default_manager(db_path: str = "asu_agent.db") -> StateManager:
    """获取默认的状态管理器实例（单例模式）"""
    global _default_manager
    if _default_manager is None:
        _default_manager = StateManager(db_path)
    return _default_manager

def set_default_manager(manager: StateManager):
    """设置默认的状态管理器实例"""
    global _default_manager
    _default_manager = manager
