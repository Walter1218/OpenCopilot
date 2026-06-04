"""
记忆系统 API 模块

提供 RESTful API 接口，用于记忆管理功能。
"""

import time
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

from .core import MemoryManager, MemoryEntry, MemoryType


# Pydantic 模型
class MemoryCreateRequest(BaseModel):
    """创建记忆请求"""
    content: str = Field(..., description="记忆内容")
    memory_type: str = Field("short_term", description="记忆类型")
    session_id: str = Field(..., description="会话ID")
    importance: float = Field(0.5, description="重要性评分 (0.0-1.0)")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class MemoryUpdateRequest(BaseModel):
    """更新记忆请求"""
    content: Optional[str] = Field(None, description="记忆内容")
    importance: Optional[float] = Field(None, description="重要性评分")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class MemorySearchRequest(BaseModel):
    """搜索记忆请求"""
    query: str = Field(..., description="查询文本")
    limit: int = Field(10, description="返回数量限制")
    memory_types: Optional[List[str]] = Field(None, description="记忆类型过滤")
    min_importance: float = Field(0.0, description="最小重要性")
    session_id: Optional[str] = Field(None, description="会话ID过滤")


class MemoryResponse(BaseModel):
    """记忆响应"""
    memory_id: str
    session_id: str
    content: str
    memory_type: str
    importance: float
    access_count: int
    created_at: float
    updated_at: float
    last_accessed: float
    tags: List[str]
    metadata: Dict[str, Any]


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    memories: List[MemoryResponse]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """统计信息响应"""
    total_sessions: int
    total_messages: int
    total_memories: int
    memories_by_type: Dict[str, int]
    memories_by_importance: Dict[str, int]
    avg_importance: float
    avg_access_count: float


class MemoryAPI:
    """记忆系统 API"""
    
    def __init__(self, manager: MemoryManager = None):
        """
        初始化 API
        
        Args:
            manager: 记忆管理器实例
        """
        self.manager = manager or MemoryManager()
        self.app = FastAPI(
            title="记忆系统 API",
            description="智能记忆管理系统的 RESTful API",
            version="1.0.0"
        )
        self._setup_routes()
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def root():
            """根路径"""
            return {
                "name": "记忆系统 API",
                "version": "1.0.0",
                "docs": "/docs",
                "endpoints": [
                    "/memories",
                    "/memories/{memory_id}",
                    "/memories/search",
                    "/memories/important",
                    "/memories/recent",
                    "/memories/tags/{tag}",
                    "/statistics",
                    "/compress",
                    "/forget"
                ]
            }
        
        @self.app.post("/memories", response_model=MemoryResponse)
        async def create_memory(request: MemoryCreateRequest):
            """创建记忆"""
            try:
                memory_type = MemoryType(request.memory_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid memory type: {request.memory_type}")
            
            memory = self.manager.store_memory(
                content=request.content,
                memory_type=memory_type,
                session_id=request.session_id,
                importance=request.importance,
                tags=request.tags,
                metadata=request.metadata
            )
            
            return MemoryResponse(**memory.to_dict())
        
        @self.app.get("/memories", response_model=MemoryListResponse)
        async def list_memories(
            limit: int = Query(10, description="返回数量限制"),
            offset: int = Query(0, description="偏移量"),
            session_id: Optional[str] = Query(None, description="会话ID过滤"),
            memory_type: Optional[str] = Query(None, description="记忆类型过滤")
        ):
            """列出记忆"""
            # 构建查询条件
            query = {}
            if session_id:
                query["session_id"] = session_id
            if memory_type:
                query["memory_type"] = memory_type
            
            # 获取记忆列表
            memories = self.manager.storage.search(query, limit=limit + offset)
            memories = memories[offset:offset + limit]
            
            # 转换为响应格式
            memory_responses = [MemoryResponse(**m) for m in memories]
            
            # 获取总数
            total = self.manager.storage.count(query)
            
            return MemoryListResponse(
                memories=memory_responses,
                total=total,
                limit=limit,
                offset=offset
            )
        
        @self.app.get("/memories/{memory_id}", response_model=MemoryResponse)
        async def get_memory(memory_id: str):
            """获取记忆"""
            memory_data = self.manager.storage.retrieve(memory_id)
            if not memory_data:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            return MemoryResponse(**memory_data)
        
        @self.app.put("/memories/{memory_id}", response_model=MemoryResponse)
        async def update_memory(memory_id: str, request: MemoryUpdateRequest):
            """更新记忆"""
            # 准备更新数据
            update_data = {}
            if request.content is not None:
                update_data["content"] = request.content
            if request.importance is not None:
                update_data["importance"] = request.importance
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.metadata is not None:
                update_data["metadata"] = request.metadata
            
            # 更新记忆
            memory = self.manager.update_memory(memory_id, **update_data)
            if not memory:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            return MemoryResponse(**memory.to_dict())
        
        @self.app.delete("/memories/{memory_id}")
        async def delete_memory(memory_id: str):
            """删除记忆"""
            success = self.manager.delete_memory(memory_id)
            if not success:
                raise HTTPException(status_code=404, detail="Memory not found")
            
            return {"message": "Memory deleted successfully"}
        
        @self.app.post("/memories/search", response_model=MemoryListResponse)
        async def search_memories(request: MemorySearchRequest):
            """搜索记忆"""
            # 转换记忆类型
            memory_types = None
            if request.memory_types:
                try:
                    memory_types = [MemoryType(mt) for mt in request.memory_types]
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
            
            # 检索记忆
            memories = self.manager.retrieve_memories(
                query=request.query,
                limit=request.limit,
                memory_types=memory_types,
                min_importance=request.min_importance,
                session_id=request.session_id
            )
            
            # 转换为响应格式
            memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
            
            return MemoryListResponse(
                memories=memory_responses,
                total=len(memory_responses),
                limit=request.limit,
                offset=0
            )
        
        @self.app.get("/memories/important", response_model=MemoryListResponse)
        async def get_important_memories(limit: int = Query(10, description="返回数量限制")):
            """获取重要记忆"""
            memories = self.manager.get_important_memories(limit)
            memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
            
            return MemoryListResponse(
                memories=memory_responses,
                total=len(memory_responses),
                limit=limit,
                offset=0
            )
        
        @self.app.get("/memories/recent", response_model=MemoryListResponse)
        async def get_recent_memories(limit: int = Query(10, description="返回数量限制")):
            """获取最近记忆"""
            memories = self.manager.get_recent_memories(limit)
            memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
            
            return MemoryListResponse(
                memories=memory_responses,
                total=len(memory_responses),
                limit=limit,
                offset=0
            )
        
        @self.app.get("/memories/tags/{tag}", response_model=MemoryListResponse)
        async def get_memories_by_tag(tag: str, limit: int = Query(10, description="返回数量限制")):
            """按标签获取记忆"""
            memories = self.manager.search_by_tags([tag], limit)
            memory_responses = [MemoryResponse(**m.to_dict()) for m in memories]
            
            return MemoryListResponse(
                memories=memory_responses,
                total=len(memory_responses),
                limit=limit,
                offset=0
            )
        
        @self.app.get("/statistics", response_model=StatsResponse)
        async def get_statistics():
            """获取统计信息"""
            stats = self.manager.get_statistics()
            return StatsResponse(**stats)
        
        @self.app.post("/compress")
        async def compress_memories(session_id: Optional[str] = Query(None, description="会话ID")):
            """压缩记忆"""
            result = self.manager.compress_memories(session_id)
            return result
        
        @self.app.post("/forget")
        async def forget_old_memories(days_threshold: int = Query(30, description="天数阈值")):
            """遗忘旧记忆"""
            result = self.manager.forget_old_memories(days_threshold)
            return result
        
        # 兼容 ASUAgentMemory 接口的 API
        @self.app.get("/context/{session_id}")
        async def get_context(session_id: str):
            """获取会话上下文（兼容）"""
            context = self.manager.get_context(session_id)
            return context
        
        @self.app.post("/context/{session_id}/messages")
        async def add_message(session_id: str, role: str, content: str):
            """添加消息（兼容）"""
            self.manager.add_message(session_id, role, content)
            return {"message": "Message added successfully"}
        
        @self.app.put("/context/{session_id}/persona")
        async def set_persona(session_id: str, persona: str):
            """设置人设（兼容）"""
            self.manager.set_persona(session_id, persona)
            return {"message": "Persona set successfully"}
        
        @self.app.delete("/context/{session_id}")
        async def clear_context(session_id: str):
            """清空会话（兼容）"""
            self.manager.clear(session_id)
            return {"message": "Context cleared successfully"}
        
        @self.app.get("/sessions/count")
        async def get_session_count():
            """获取会话数量（兼容）"""
            count = self.manager.session_count()
            return {"count": count}
    
    def run(self, host: str = "0.0.0.0", port: int = 8091):
        """
        运行 API 服务器
        
        Args:
            host: 主机地址
            port: 端口号
        """
        uvicorn.run(self.app, host=host, port=port)


# 便捷函数
def create_api(manager: MemoryManager = None) -> FastAPI:
    """
    创建 API 实例
    
    Args:
        manager: 记忆管理器实例
        
    Returns:
        FastAPI 实例
    """
    api = MemoryAPI(manager)
    return api.app


def run_api(manager: MemoryManager = None, host: str = "0.0.0.0", port: int = 8091):
    """
    运行 API 服务器
    
    Args:
        manager: 记忆管理器实例
        host: 主机地址
        port: 端口号
    """
    api = MemoryAPI(manager)
    api.run(host, port)
