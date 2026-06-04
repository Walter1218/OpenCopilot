"""
MiniMax 搜索提供者

使用 MiniMax Token Plan 搜索 API 进行网络搜索。

API 端点：
- 全球：https://api.minimax.io/v1/coding_plan/search
- 中国：https://api.minimaxi.com/v1/coding_plan/search
"""

import os
import json
import httpx
from typing import List, Optional, Dict, Any
from .core import SearchProvider, SearchResult, SearchType


class MiniMaxSearchProvider(SearchProvider):
    """
    MiniMax 网络搜索提供者
    
    使用 MiniMax Token Plan 搜索 API，返回结构化搜索结果。
    
    使用示例：
        provider = MiniMaxSearchProvider(api_key="your-api-key")
        results = provider.search("Python async await", count=5)
    """
    
    # API 端点
    ENDPOINTS = {
        "global": "https://api.minimax.io/v1/coding_plan/search",
        "cn": "https://api.minimaxi.com/v1/coding_plan/search"
    }
    
    def __init__(self, api_key: str = None, region: str = "cn"):
        """
        初始化 MiniMax 搜索提供者
        
        Args:
            api_key: MiniMax Token Plan API 密钥
            region: 区域，"global" 或 "cn"
        """
        self.api_key = api_key or self._get_api_key()
        self.region = region
        self.endpoint = self.ENDPOINTS.get(region, self.ENDPOINTS["cn"])
        
        if not self.api_key:
            print("Warning: MiniMax API key not set. Web search will not work.")
    
    def _get_api_key(self) -> Optional[str]:
        """获取 API 密钥"""
        # 优先级：环境变量 > 配置文件
        api_key = os.environ.get("MINIMAX_API_KEY")
        if api_key:
            return api_key
        
        # 尝试从配置文件读取
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("minimax_api_key")
            except:
                pass
        
        return None
    
    def search(self, query: str, count: int = 5, **kwargs) -> List[SearchResult]:
        """
        执行网络搜索
        
        Args:
            query: 搜索查询
            count: 返回结果数量 (1-10)
            **kwargs: 额外参数
            
        Returns:
            搜索结果列表
        """
        if not self.api_key:
            return []
        
        # 限制结果数量
        count = min(max(1, count), 10)
        
        try:
            # 调用 MiniMax 搜索 API
            response = self._call_api(query, count)
            
            # 解析结果
            return self._parse_response(response)
        except Exception as e:
            print(f"MiniMax search error: {e}")
            return []
    
    def _call_api(self, query: str, count: int) -> Dict[str, Any]:
        """
        调用 MiniMax 搜索 API
        
        Args:
            query: 搜索查询
            count: 结果数量
            
        Returns:
            API 响应
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "query": query,
            "count": count
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    def _parse_response(self, response: Dict[str, Any]) -> List[SearchResult]:
        """
        解析 API 响应
        
        Args:
            response: API 响应
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 解析搜索结果
        search_results = response.get("results", [])
        for item in search_results:
            result = SearchResult(
                title=item.get("title", ""),
                content=item.get("snippet", ""),
                url=item.get("url"),
                source=SearchType.WEB,
                score=item.get("score", 0.5),
                metadata={
                    "provider": "minimax",
                    "region": self.region,
                    "highlights": item.get("highlights", [])
                }
            )
            results.append(result)
        
        return results
    
    def set_region(self, region: str):
        """设置区域"""
        if region in self.ENDPOINTS:
            self.region = region
            self.endpoint = self.ENDPOINTS[region]
    
    def is_available(self) -> bool:
        """检查搜索是否可用"""
        return bool(self.api_key)
