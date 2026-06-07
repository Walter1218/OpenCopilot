"""
记忆系统 API 路由：/api/memory/*
封装 MemoryManager 为 FastAPI APIRouter（替代原 MemoryAPI 的独立 FastAPI 应用）。
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# 复用原 MemoryAPI 的 Pydantic 模型（避免重复定义）
from opencopilot.capabilities.memory.api import (
    MemoryCreateRequest, MemoryUpdateRequest, MemorySearchRequest,
    MemoryResponse, MemoryListResponse, StatsResponse
)
from opencopilot.capabilities.memory.core import MemoryType


def create_memory_router(memory_manager) -> APIRouter:
    """
    创建记忆系统 API 路由器

    Args:
        memory_manager: MemoryManager 实例

    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/memory", tags=["memory"])

    @router.get("", response_model=MemoryListResponse)
    async def list_memories(
        limit: int = Query(10, description="返回数量限制"),
        offset: int = Query(0, description="偏移量"),
        session_id: Optional[str] = Query(None, description="会话ID过滤"),
        memory_type: Optional[str] = Query(None, description="记忆类型过滤")
    ):
        """列出记忆"""
        memories = memory_manager.list_memories(
            session_id=session_id,
            memory_type=memory_type,
            limit=limit,
            offset=offset
        )
        total = memory_manager.count_memories(
            session_id=session_id,
            memory_type=memory_type
        )
        memory_responses = [MemoryResponse(**m) for m in memories]

        return MemoryListResponse(
            memories=memory_responses,
            total=total,
            limit=limit,
            offset=offset
        )

    @router.post("", response_model=MemoryResponse)
    async def create_memory(request: MemoryCreateRequest):
        """创建记忆"""
        try:
            mt = MemoryType(request.memory_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid memory type: {request.memory_type}")

        memory = memory_manager.store_memory(
            content=request.content,
            memory_type=mt,
            session_id=request.session_id,
            importance=request.importance,
            tags=request.tags,
            metadata=request.metadata
        )
        return MemoryResponse(**memory.to_dict())

    @router.get("/item/{memory_id}", response_model=MemoryResponse)
    async def get_memory(memory_id: str):
        """获取记忆"""
        memory_data = memory_manager.get_memory_by_id(memory_id)
        if not memory_data:
            raise HTTPException(status_code=404, detail="Memory not found")
        return MemoryResponse(**memory_data)

    @router.put("/item/{memory_id}", response_model=MemoryResponse)
    async def update_memory(memory_id: str, request: MemoryUpdateRequest):
        """更新记忆"""
        update_data = {}
        if request.content is not None:
            update_data["content"] = request.content
        if request.importance is not None:
            update_data["importance"] = request.importance
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.metadata is not None:
            update_data["metadata"] = request.metadata

        memory = memory_manager.update_memory(memory_id, **update_data)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        return MemoryResponse(**memory.to_dict())

    @router.delete("/item/{memory_id}")
    async def delete_memory(memory_id: str):
        """删除记忆"""
        success = memory_manager.delete_memory(memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"message": "Memory deleted successfully"}

    @router.post("/search", response_model=MemoryListResponse)
    async def search_memories(request: MemorySearchRequest):
        """搜索记忆"""
        memory_types = None
        if request.memory_types:
            try:
                memory_types = [MemoryType(mt) for mt in request.memory_types]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        memories = memory_manager.retrieve_memories(
            query=request.query,
            limit=request.limit,
            memory_types=memory_types,
            min_importance=request.min_importance,
            session_id=request.session_id
        )
        memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses),
            limit=request.limit,
            offset=0
        )

    @router.get("/important/list", response_model=MemoryListResponse)
    async def get_important_memories(limit: int = Query(10, description="返回数量限制")):
        """获取重要记忆"""
        memories = memory_manager.get_important_memories(limit)
        memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses),
            limit=limit,
            offset=0
        )

    @router.get("/recent/list", response_model=MemoryListResponse)
    async def get_recent_memories(limit: int = Query(10, description="返回数量限制")):
        """获取最近记忆"""
        memories = memory_manager.get_recent_memories(limit)
        memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses),
            limit=limit,
            offset=0
        )

    @router.get("/tags/{tag}", response_model=MemoryListResponse)
    async def get_memories_by_tag(tag: str, limit: int = Query(10, description="返回数量限制")):
        """按标签获取记忆"""
        memories = memory_manager.search_by_tags([tag], limit)
        memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses),
            limit=limit,
            offset=0
        )

    @router.get("/statistics", response_model=StatsResponse)
    async def get_statistics():
        """获取统计信息"""
        stats = memory_manager.get_statistics()
        return StatsResponse(**stats)

    @router.post("/compress")
    async def compress_memories(session_id: Optional[str] = Query(None, description="会话ID")):
        """压缩记忆"""
        result = memory_manager.compress_memories(session_id)
        return result

    @router.post("/forget")
    async def forget_old_memories(days_threshold: int = Query(30, description="天数阈值")):
        """遗忘旧记忆"""
        result = memory_manager.forget_old_memories(days_threshold)
        return result

    @router.get("/info")
    async def memory_info():
        """API 信息"""
        return {
            "name": "记忆系统 API",
            "version": "1.0.0",
            "endpoints": [
                "/api/memory",
                "/api/memory/item/{memory_id}",
                "/api/memory/search",
                "/api/memory/important/list",
                "/api/memory/recent/list",
                "/api/memory/tags/{tag}",
                "/api/memory/statistics",
                "/api/memory/compress",
                "/api/memory/forget"
            ]
        }

    return router
