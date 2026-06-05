"""
上下文管理模块 (Context Manager)

从 asu_custom_agent.py 抽取的独立模块，提供：
- 上下文窗口管理
- 上下文裁剪策略
- 模型适配
"""

from .core import ContextManager, ContextWindowManager
from .context_envelope import ContextEnvelope, normalize_context_envelope

__all__ = [
    "ContextManager",
    "ContextWindowManager",
    "ContextEnvelope",
    "normalize_context_envelope"
]
