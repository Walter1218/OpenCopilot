"""
搜索能力模块 (Search Capability)

统一搜索接口，支持：
- 网络搜索 (MiniMax API)
- 代码搜索
- 文档搜索
- 知识库搜索
"""

from .core import SearchCapability, SearchResult, SearchType
from .minimax_search import MiniMaxSearchProvider
from .code_search import CodeSearchProvider
from .doc_search import DocSearchProvider

__all__ = [
    "SearchCapability",
    "SearchResult", 
    "SearchType",
    "MiniMaxSearchProvider",
    "CodeSearchProvider",
    "DocSearchProvider"
]
