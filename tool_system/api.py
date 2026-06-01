# tool_system/api.py

"""
工具系统 RESTful API 端点
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolCategory, ToolType, ToolStatus
)
from .registry import ToolRegistry
from .executor import ToolExecutor


# Pydantic 模型（用于 API 请求/响应）

class ToolParameterSchema(BaseModel):
    """工具参数模式"""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


class RegisterToolRequest(BaseModel):
    """注册工具请求"""
    tool_id: str
    name: str
    description: str
    tool_type: str = "custom"
    category: str = "custom"
    version: str = "1.0.0"
    author: str = ""
    parameters: List[ToolParameterSchema] = []
    output_schema: Optional[Dict] = None
    requires_approval: bool = False
    timeout: float = 30.0
    retry_count: int = 3
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class CallToolRequest(BaseModel):
    """调用工具请求"""
    tool_id: str
    parameters: Dict[str, Any] = {}
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = {}


class BatchCallRequest(BaseModel):
    """批量调用请求"""
    calls: List[CallToolRequest]
    max_concurrent: Optional[int] = None


class ToolResponse(BaseModel):
    """工具响应"""
    tool_id: str
    name: str
    description: str
    tool_type: str
    category: str
    version: str
    status: str
    parameters: List[ToolParameterSchema]
    tags: List[str]


class CallResultResponse(BaseModel):
    """调用结果响应"""
    tool_call_id: str
    tool_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float


class StatsResponse(BaseModel):
    """统计响应"""
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_duration_ms: float


def create_tool_router(
    registry: ToolRegistry,
    executor: ToolExecutor
) -> APIRouter:
    """
    创建工具 API 路由器
    
    Args:
        registry: 工具注册表
        executor: 工具执行器
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/tools", tags=["tools"])
    
    @router.get("", response_model=List[ToolResponse])
    async def list_tools(
        category: Optional[str] = Query(None, description="按类别过滤"),
        tool_type: Optional[str] = Query(None, description="按类型过滤"),
        tag: Optional[str] = Query(None, description="按标签过滤"),
        status: Optional[str] = Query(None, description="按状态过滤")
    ):
        """列出所有工具"""
        # 解析过滤参数
        cat = ToolCategory(category) if category else None
        tt = ToolType(tool_type) if tool_type else None
        ts = ToolStatus(status) if status else None
        tags = [tag] if tag else None
        
        tools = registry.list_tools(
            category=cat,
            tool_type=tt,
            tags=tags,
            status=ts
        )
        
        return [_tool_to_response(tool) for tool in tools]
    
    @router.get("/search", response_model=List[ToolResponse])
    async def search_tools(
        q: str = Query(..., description="搜索关键词")
    ):
        """搜索工具"""
        tools = registry.search_tools(q)
        return [_tool_to_response(tool) for tool in tools]
    
    @router.get("/{tool_id}", response_model=ToolResponse)
    async def get_tool(tool_id: str):
        """获取工具详情"""
        tool = registry.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
        return _tool_to_response(tool)
    
    @router.post("", response_model=Dict[str, str])
    async def register_tool(request: RegisterToolRequest):
        """注册工具"""
        # 注意：这里需要工具处理函数，实际实现需要更复杂的逻辑
        # 简化示例：只返回成功
        return {"tool_id": request.tool_id, "status": "registered"}
    
    @router.delete("/{tool_id}")
    async def unregister_tool(tool_id: str):
        """注销工具"""
        success = registry.unregister(tool_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
        return {"status": "unregistered"}
    
    @router.post("/call", response_model=CallResultResponse)
    async def call_tool(
        request: CallToolRequest,
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None)
    ):
        """调用工具"""
        call = ToolCall(
            tool_id=request.tool_id,
            parameters=request.parameters,
            timeout=request.timeout,
            metadata=request.metadata
        )
        
        result = await executor.execute(call, user_id, session_id)
        
        return CallResultResponse(
            tool_call_id=result.tool_call_id,
            tool_id=result.tool_id,
            tool_name=result.tool_name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms
        )
    
    @router.post("/batch-call", response_model=List[CallResultResponse])
    async def batch_call_tools(
        request: BatchCallRequest,
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None)
    ):
        """批量调用工具"""
        calls = [
            ToolCall(
                tool_id=c.tool_id,
                parameters=c.parameters,
                timeout=c.timeout,
                metadata=c.metadata
            )
            for c in request.calls
        ]
        
        results = await executor.batch_execute(
            calls, user_id, session_id, request.max_concurrent
        )
        
        return [
            CallResultResponse(
                tool_call_id=r.tool_call_id,
                tool_id=r.tool_id,
                tool_name=r.tool_name,
                success=r.success,
                output=r.output,
                error=r.error,
                duration_ms=r.duration_ms
            )
            for r in results
        ]
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = executor.get_stats()
        return StatsResponse(**stats)
    
    def _tool_to_response(tool: ToolDefinition) -> ToolResponse:
        """转换工具定义为响应"""
        return ToolResponse(
            tool_id=tool.tool_id,
            name=tool.name,
            description=tool.description,
            tool_type=tool.tool_type.value,
            category=tool.category.value,
            version=tool.version,
            status=registry.get_status(tool.tool_id).value if registry.get_status(tool.tool_id) else "unknown",
            parameters=[
                ToolParameterSchema(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default,
                    enum=p.enum
                )
                for p in tool.parameters
            ],
            tags=tool.tags
        )
    
    return router
