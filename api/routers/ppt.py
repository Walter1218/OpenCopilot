"""PPT 路由：/api/ppt/*"""
import os, sys, uuid, json, tempfile
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from smart_copilot_api import (
    PPTGenerateRequest, PPTGenerateResponse, _call_agent_pipeline, session_manager
)
from ppt_generator import generate_ppt_from_json, extract_json_from_text

router = APIRouter(prefix="/api/ppt", tags=["ppt"])


@router.post("/generate", response_model=PPTGenerateResponse)
async def generate_ppt(request: PPTGenerateRequest, background_tasks: BackgroundTasks):
    try:
        filename = request.filename or f"ppt_{uuid.uuid4().hex[:8]}.pptx"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        output_path = os.path.join(tempfile.gettempdir(), filename)
        generate_ppt_from_json(request.slides, output_path)
        return PPTGenerateResponse(
            file_path=output_path,
            file_size=os.path.getsize(output_path),
            slide_count=len(request.slides),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 生成失败: {str(e)}")


@router.post("/generate-and-download")
async def generate_and_download_ppt(request: PPTGenerateRequest):
    try:
        filename = request.filename or f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        output_path = os.path.join(tempfile.gettempdir(), filename)
        generate_ppt_from_json(request.slides, output_path)
        return FileResponse(path=output_path, filename=filename,
                           media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 生成失败: {str(e)}")


@router.post("/extract-from-text")
async def extract_ppt_from_text(text: str):
    try:
        response = await _call_agent_pipeline(
            text=f"请将以下文本转换为 PPT 大纲的 JSON 格式。要求输出 JSON 数组，每页含 type/title/items/layout 字段。\n\n{text}",
            action_type="ppt", context_source="ppt_editor", enable_web_search=False,
        )
        slides = extract_json_from_text(response)
        return {"original_text": text, "extracted_slides": slides, "slide_count": len(slides)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPT 提取失败: {str(e)}")


@router.post("/suggest")
async def suggest_ppt(data: dict):
    return {"suggestions": []}


@router.post("/analyze")
async def analyze_ppt(data: dict):
    return {"analysis": "ok"}


@router.post("/chat")
async def ppt_chat(data: dict):
    msg = data.get("message", "")
    sid = data.get("session_id")
    sid = session_manager.get_or_create(sid)
    resp = await _call_agent_pipeline(text=msg, session_id=sid, context_source="ppt_editor")
    return {"response": resp, "session_id": sid}


@router.get("/{session_id}/history")
async def ppt_chat_history(session_id: str):
    return {"session_id": session_id, "messages": session_manager.get_history(session_id)}


@router.post("/check")
async def ppt_check(data: dict):
    return {"check": "ok"}


# =============================================================================
# v5 新增端点
# =============================================================================

class ExportSlidesRequest(BaseModel):
    """导出 Slides 请求"""
    slides: List[Dict[str, Any]] = Field(..., description="Slides JSON 数据")
    filename: Optional[str] = Field(None, description="输出文件名（不含 .pptx 后缀）")


@router.post("/export-slides")
async def export_slides(request: ExportSlidesRequest):
    """
    导出 Slides 为 PPT 文件

    接收 slides JSON + filename，生成 .pptx 并返回下载路径。
    用于 Studio Window 底部 "导出 PPT" 按钮。
    """
    print(f"[V5-API] POST /api/ppt/export-slides | slides={len(request.slides)}, filename={request.filename}")
    try:
        filename = request.filename or f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith('.pptx'):
            filename += '.pptx'
        output_path = os.path.join(tempfile.gettempdir(), filename)
        generate_ppt_from_json(request.slides, output_path)
        file_size = os.path.getsize(output_path)
        print(f"[V5-API] export-slides: success, path={output_path}, size={file_size}")
        return {
            "success": True,
            "file_path": output_path,
            "filename": filename,
            "file_size": file_size,
            "slide_count": len(request.slides),
        }
    except Exception as e:
        print(f"[V5-API] export-slides error: {e}")
        raise HTTPException(status_code=500, detail=f"PPT 导出失败: {str(e)}")
