"""
搜索 API 路由：/api/search/*
封装 SearchCapability 为 FastAPI Router。
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询")
    type: str = Field("all", description="搜索类型: all/web/code/doc/knowledge")
    count: int = Field(5, description="返回结果数量")
    scope: Optional[str] = Field(None, description="搜索范围（代码/文档搜索时使用）")


class SearchResultItem(BaseModel):
    """搜索结果项"""
    title: str
    content: str
    url: Optional[str] = None
    source: str
    score: float = 0.0
    timestamp: str


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    type: str
    results: List[SearchResultItem]
    total: int


def create_search_router(search_capability) -> APIRouter:
    """
    创建搜索 API 路由器

    Args:
        search_capability: SearchCapability 实例

    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/search", tags=["search"])

    @router.post("", response_model=SearchResponse)
    async def search(request: SearchRequest):
        """统一搜索"""
        from opencopilot.capabilities.search.core import SearchType
        try:
            st = SearchType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的搜索类型: {request.type}")

        kwargs = {}
        if request.scope:
            kwargs["scope"] = request.scope

        results = search_capability.search(
            query=request.query,
            search_type=st,
            count=request.count,
            **kwargs
        )

        items = [
            SearchResultItem(
                title=r.title,
                content=r.content,
                url=r.url,
                source=r.source.value,
                score=r.score,
                timestamp=r.timestamp.isoformat()
            )
            for r in results
        ]

        return SearchResponse(
            query=request.query,
            type=request.type,
            results=items,
            total=len(items)
        )

    @router.post("/code", response_model=SearchResponse)
    async def code_search(
        query: str = Query(..., description="搜索查询"),
        scope: Optional[str] = Query(None, description="搜索范围"),
        count: int = Query(5, description="返回数量")
    ):
        """代码搜索"""
        results = search_capability.code_search(query=query, scope=scope, count=count)
        items = [
            SearchResultItem(
                title=r.title, content=r.content, url=r.url,
                source=r.source.value, score=r.score,
                timestamp=r.timestamp.isoformat()
            )
            for r in results
        ]
        return SearchResponse(query=query, type="code", results=items, total=len(items))

    @router.post("/doc", response_model=SearchResponse)
    async def doc_search(
        query: str = Query(..., description="搜索查询"),
        scope: Optional[str] = Query(None, description="搜索范围"),
        count: int = Query(5, description="返回数量")
    ):
        """文档搜索"""
        results = search_capability.doc_search(query=query, scope=scope, count=count)
        items = [
            SearchResultItem(
                title=r.title, content=r.content, url=r.url,
                source=r.source.value, score=r.score,
                timestamp=r.timestamp.isoformat()
            )
            for r in results
        ]
        return SearchResponse(query=query, type="doc", results=items, total=len(items))

    @router.get("/providers")
    async def list_providers():
        """列出可用搜索提供者"""
        return {"providers": search_capability.list_providers()}

    return router
