"""
知识检索模块

提供统一的知识检索接口，封装底层知识图谱功能。
支持多种查询方式：实体查询、关系查询、路径查询等。
"""

from .core import KnowledgeRetrieval, RetrievalResult
from .query_interface import QueryInterface, QueryType

__version__ = "1.0.0"
__all__ = [
    "KnowledgeRetrieval", "RetrievalResult",
    "QueryInterface", "QueryType"
]
