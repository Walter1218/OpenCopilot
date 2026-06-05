"""知识图谱路由：/api/knowledge/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    query: str
    entity_type: Optional[str] = None


class KnowledgeBuildRequest(BaseModel):
    content: str
    source: Optional[str] = None


class KnowledgeExportRequest(BaseModel):
    format: str = "json"
    entity_type: Optional[str] = None


@router.post("/query")
async def knowledge_query(request: KnowledgeQueryRequest):
    try:
        from opencopilot.capabilities.knowledge import KnowledgeRetrieval
        kr = KnowledgeRetrieval()
        result = kr.query(request.query)
        return {"results": result} if isinstance(result, list) else result
    except Exception as e:
        raise HTTPException(status_code=503 if "not initialized" in str(e).lower() else 500,
                           detail=f"知识查询失败: {str(e)}")


@router.post("/build")
async def knowledge_build(request: KnowledgeBuildRequest):
    try:
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        result = kg.build(request.content, request.source)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识构建失败: {str(e)}")


@router.post("/export")
async def knowledge_export(request: KnowledgeExportRequest):
    try:
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        return kg.export(format=request.format, entity_type=request.entity_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识导出失败: {str(e)}")


@router.post("/search-entity")
async def search_entity(data: dict):
    from opencopilot.capabilities.knowledge import KnowledgeRetrieval
    kr = KnowledgeRetrieval()
    return kr.find_entity(data.get("name", ""))


@router.post("/find-related")
async def find_related(data: dict):
    from opencopilot.capabilities.knowledge import KnowledgeRetrieval
    kr = KnowledgeRetrieval()
    return kr.find_related(data.get("name", ""), data.get("relation", ""))


@router.post("/find-path")
async def find_path(data: dict):
    from opencopilot.capabilities.knowledge import KnowledgeRetrieval
    kr = KnowledgeRetrieval()
    return kr.find_path(data.get("from", ""), data.get("to", ""))


@router.get("/statistics")
async def knowledge_statistics():
    try:
        from opencopilot.capabilities.knowledge import KnowledgeRetrieval
        kr = KnowledgeRetrieval()
        return kr.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"知识图谱未就绪: {str(e)}")
