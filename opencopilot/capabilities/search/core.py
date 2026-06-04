"""
搜索能力核心模块

提供统一的搜索接口，支持多种搜索后端。
"""

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class SearchType(str, Enum):
    """搜索类型"""
    WEB = "web"           # 网络搜索
    CODE = "code"         # 代码搜索
    DOC = "doc"           # 文档搜索
    KNOWLEDGE = "knowledge"  # 知识库搜索
    ALL = "all"           # 全部搜索


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    content: str
    url: Optional[str] = None
    source: SearchType = SearchType.WEB
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source.value,
            "score": self.score,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class SearchProvider:
    """搜索提供者基类"""
    
    def search(self, query: str, count: int = 5, **kwargs) -> List[SearchResult]:
        """执行搜索"""
        raise NotImplementedError


class SearchCapability:
    """
    搜索能力模块 - 乐高积木式设计
    
    支持多种搜索后端：
    - MiniMax 网络搜索
    - 本地代码搜索
    - 本地文档搜索
    - 知识库搜索
    
    使用示例：
        search = SearchCapability()
        
        # 网络搜索
        results = search.web_search("Python async await")
        
        # 代码搜索
        results = search.code_search("def process_data", scope="./src")
        
        # 统一搜索接口
        results = search.search("机器学习", search_type=SearchType.ALL)
    """
    
    def __init__(self, minimax_api_key: str = None, workspace: str = None):
        self.workspace = workspace or os.getcwd()
        self.providers: Dict[SearchType, SearchProvider] = {}
        
        # 初始化搜索提供者
        self._init_providers(minimax_api_key)
    
    def _init_providers(self, minimax_api_key: str = None):
        """初始化搜索提供者"""
        # MiniMax 网络搜索
        try:
            from .minimax_search import MiniMaxSearchProvider
            self.providers[SearchType.WEB] = MiniMaxSearchProvider(minimax_api_key)
        except Exception as e:
            print(f"Warning: MiniMax search provider init failed: {e}")
        
        # 代码搜索
        try:
            from .code_search import CodeSearchProvider
            self.providers[SearchType.CODE] = CodeSearchProvider(self.workspace)
        except Exception as e:
            print(f"Warning: Code search provider init failed: {e}")
        
        # 文档搜索
        try:
            from .doc_search import DocSearchProvider
            self.providers[SearchType.DOC] = DocSearchProvider(self.workspace)
        except Exception as e:
            print(f"Warning: Doc search provider init failed: {e}")
    
    def search(self, query: str, search_type: SearchType = SearchType.ALL, 
               count: int = 5, **kwargs) -> List[SearchResult]:
        """
        统一搜索接口
        
        Args:
            query: 搜索查询
            search_type: 搜索类型
            count: 返回结果数量
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        results = []
        
        if search_type == SearchType.ALL:
            # 搜索所有类型
            for provider_type, provider in self.providers.items():
                try:
                    provider_results = provider.search(query, count=count, **kwargs)
                    results.extend(provider_results)
                except Exception as e:
                    print(f"Search error ({provider_type}): {e}")
        elif search_type in self.providers:
            # 搜索指定类型
            try:
                results = self.providers[search_type].search(query, count=count, **kwargs)
            except Exception as e:
                print(f"Search error ({search_type}): {e}")
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:count]
    
    def web_search(self, query: str, count: int = 5, **kwargs) -> List[SearchResult]:
        """网络搜索"""
        return self.search(query, SearchType.WEB, count, **kwargs)
    
    def code_search(self, query: str, scope: str = None, count: int = 5, **kwargs) -> List[SearchResult]:
        """代码搜索"""
        kwargs['scope'] = scope or self.workspace
        return self.search(query, SearchType.CODE, count, **kwargs)
    
    def doc_search(self, query: str, scope: str = None, count: int = 5, **kwargs) -> List[SearchResult]:
        """文档搜索"""
        kwargs['scope'] = scope or self.workspace
        return self.search(query, SearchType.DOC, count, **kwargs)
    
    def get_provider(self, search_type: SearchType) -> Optional[SearchProvider]:
        """获取搜索提供者"""
        return self.providers.get(search_type)
    
    def list_providers(self) -> List[str]:
        """列出可用的搜索提供者"""
        return [t.value for t in self.providers.keys()]
