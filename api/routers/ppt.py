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


# =============================================================================
# 渲染指令系统端点
# =============================================================================

class RenderCommandRequest(BaseModel):
    """渲染指令请求"""
    render_commands: List[Dict[str, Any]] = Field(..., description="渲染指令列表")
    slides_data: List[Dict[str, Any]] = Field(..., description="当前幻灯片数据")
    original_text: Optional[str] = Field("", description="原始文档文本")
    current_index: int = Field(0, description="当前幻灯片索引")
    session_id: Optional[str] = Field(None, description="会话ID")


class RenderCommandResponse(BaseModel):
    """渲染指令响应"""
    success: bool
    results: List[Dict[str, Any]]
    slides_data: List[Dict[str, Any]]
    message: str


@router.post("/render-commands")
async def execute_render_commands(request: RenderCommandRequest):
    """
    执行渲染指令

    接收渲染指令列表，执行并返回更新后的幻灯片数据。
    用于 AI 指令驱动的声明式渲染架构。
    """
    from opencopilot.capabilities.ppt.render_command import RenderCommand
    from opencopilot.capabilities.ppt.render_executor import RenderExecutor
    
    session_id = request.session_id or f"api_render_{uuid.uuid4().hex[:8]}"
    print(f"[V5-API] POST /api/ppt/render-commands | commands={len(request.render_commands)}, session={session_id}")
    
    try:
        # 创建渲染执行器
        executor = RenderExecutor(request.slides_data, request.original_text)
        
        # 解析渲染指令
        commands = []
        for cmd_data in request.render_commands:
            cmd = RenderCommand.from_dict(cmd_data)
            if cmd.slide_index < 0:
                cmd.slide_index = request.current_index
            commands.append(cmd)
        
        # 执行渲染指令
        results = []
        for cmd in commands:
            result = executor.execute(cmd)
            results.append({
                "success": result.success,
                "slide_index": result.slide_index,
                "message": result.message,
                "trace_id": result.trace_id,
            })
        
        # 埋点
        try:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log(
                f"API_RENDER_COMMANDS | commands={len(commands)} success={sum(1 for r in results if r['success'])}",
                session_id=session_id,
                event="API_RENDER_COMMANDS"
            )
        except Exception:
            pass
        
        return RenderCommandResponse(
            success=True,
            results=results,
            slides_data=request.slides_data,
            message=f"已执行 {len(commands)} 条渲染指令"
        )
    except Exception as e:
        print(f"[V5-API] render-commands error: {e}")
        raise HTTPException(status_code=500, detail=f"渲染指令执行失败: {str(e)}")


class ParseRenderCommandRequest(BaseModel):
    """解析渲染指令请求"""
    response: str = Field(..., description="AI 响应文本")
    original_text: Optional[str] = Field("", description="原始文档文本")


class ParseRenderCommandResponse(BaseModel):
    """解析渲染指令响应"""
    success: bool
    render_commands: List[Dict[str, Any]]
    count: int
    message: str


@router.post("/parse-render-commands")
async def parse_render_commands(request: ParseRenderCommandRequest):
    """
    解析渲染指令

    从 AI 响应中提取渲染指令。
    用于调试和测试。
    """
    from opencopilot.capabilities.ppt.render_command import RenderCommandParser
    
    print(f"[V5-API] POST /api/ppt/parse-render-commands | response_len={len(request.response)}")
    
    try:
        commands = RenderCommandParser.parse(request.response, request.original_text)
        
        return ParseRenderCommandResponse(
            success=True,
            render_commands=[cmd.to_dict() for cmd in commands],
            count=len(commands),
            message=f"解析到 {len(commands)} 条渲染指令"
        )
    except Exception as e:
        print(f"[V5-API] parse-render-commands error: {e}")
        raise HTTPException(status_code=500, detail=f"解析渲染指令失败: {str(e)}")


class QuickActionsRequest(BaseModel):
    """快捷指令请求"""
    selected_text: str = Field(..., description="选中的文本")
    slide_index: Optional[int] = Field(0, description="当前幻灯片索引")


class QuickActionsResponse(BaseModel):
    """快捷指令响应"""
    success: bool
    actions: List[Dict[str, str]]
    count: int


@router.post("/quick-actions")
async def get_quick_actions(request: QuickActionsRequest):
    """
    获取快捷指令

    根据选中文本生成快捷指令建议。
    """
    from opencopilot.capabilities.ppt.render_command import QuickActionGenerator
    
    print(f"[V5-API] POST /api/ppt/quick-actions | text_len={len(request.selected_text)}")
    
    try:
        actions = QuickActionGenerator.generate_actions(request.selected_text)
        
        return QuickActionsResponse(
            success=True,
            actions=actions,
            count=len(actions)
        )
    except Exception as e:
        print(f"[V5-API] quick-actions error: {e}")
        raise HTTPException(status_code=500, detail=f"生成快捷指令失败: {str(e)}")
