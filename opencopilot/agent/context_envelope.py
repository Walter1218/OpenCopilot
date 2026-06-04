"""
上下文信封模块

定义上下文数据结构和标准化函数。
"""

import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextEnvelope:
    """
    上下文信封
    
    统一的上下文数据结构，用于在不同模块间传递上下文信息。
    
    使用示例：
        envelope = ContextEnvelope(
            source="ide",
            content="代码内容...",
            task="修复 bug",
            meta={"file_name": "main.py", "language": "python"}
        )
    """
    source: str
    content: str
    selection: Optional[str] = None
    task: Optional[str] = None
    custom_instruction: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "content": self.content,
            "selection": self.selection,
            "task": self.task,
            "custom_instruction": self.custom_instruction,
            "meta": self.meta,
            "timestamp": self.timestamp,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextEnvelope':
        """从字典创建"""
        return cls(
            source=data.get("source", "unknown"),
            content=data.get("content", ""),
            selection=data.get("selection"),
            task=data.get("task"),
            custom_instruction=data.get("custom_instruction"),
            meta=data.get("meta", {}),
            timestamp=data.get("timestamp", time.time()),
            session_id=data.get("session_id")
        )


def normalize_context_envelope(request: Dict[str, Any], 
                               text: str = None,
                               context_source: str = None,
                               context_meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    标准化上下文信封
    
    兼容新旧两种格式：
    - 旧格式：text, context_source, context_meta
    - 新格式：context_envelope
    
    Args:
        request: 请求数据
        text: 文本内容（旧格式）
        context_source: 上下文来源（旧格式）
        context_meta: 上下文元数据（旧格式）
        
    Returns:
        标准化的上下文信封字典
    """
    # 优先使用新格式
    if "context_envelope" in request:
        envelope = request["context_envelope"]
        return {
            "source": envelope.get("source", "unknown"),
            "content": envelope.get("content", ""),
            "selection": envelope.get("selection"),
            "task": envelope.get("task"),
            "custom_instruction": envelope.get("custom_instruction"),
            "meta": envelope.get("meta", {}),
            "timestamp": envelope.get("timestamp", time.time())
        }
    
    # 兼容旧格式
    return {
        "source": context_source or request.get("context_source", "unknown"),
        "content": text or request.get("text", ""),
        "selection": request.get("selection"),
        "task": context_meta.get("task") if context_meta else request.get("task"),
        "custom_instruction": request.get("custom_instruction"),
        "meta": context_meta or request.get("context_meta", {}),
        "timestamp": time.time()
    }
