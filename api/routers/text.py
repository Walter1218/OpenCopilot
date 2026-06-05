"""文本处理路由：/api/text/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from smart_copilot_api import TextProcessRequest, TextProcessResponse, _call_agent_pipeline

router = APIRouter(prefix="/api/text", tags=["text"])

ACTION_PERSONA = {
    "translate": "translate", "polish": "default",
    "explain": "code", "summarize": "default",
    "code": "code", "custom": "default",
}

PROMPTS = {
    "translate": lambda t, lang: f"请将以下文本翻译成{'中文' if lang == 'zh' else '英文'}：\n\n{t}",
    "polish": lambda t, _: f"请润色以下文本，使其更加专业和流畅：\n\n{t}",
    "explain": lambda t, _: f"请详细解释以下内容：\n\n{t}",
    "summarize": lambda t, _: f"请总结以下内容的要点：\n\n{t}",
    "code": lambda t, _: f"请解析以下代码，说明其功能和关键点：\n\n{t}",
}


async def _do_process(request: TextProcessRequest):
    if request.action == "custom" and request.custom_instruction:
        prompt = f"{request.custom_instruction}\n\n{request.text}"
    elif request.action in PROMPTS:
        prompt = PROMPTS[request.action](request.text, request.target_language or "zh")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {request.action}")

    resp = await _call_agent_pipeline(
        text=prompt,
        action_type=ACTION_PERSONA.get(request.action, "default"),
        context_source="chat",
        context_meta={"task": "text_process", "action": request.action},
        enable_web_search=False,
    )
    return TextProcessResponse(original=request.text, processed=resp, action=request.action)


@router.post("/process", response_model=TextProcessResponse)
async def process_text(request: TextProcessRequest):
    try:
        return await _do_process(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本处理失败: {str(e)}")


@router.post("/translate")
async def translate_text(text: str = "error"):
    return await _do_process(TextProcessRequest(text=text, action="translate"))


@router.post("/polish")
async def polish_text(text: str = "error"):
    return await _do_process(TextProcessRequest(text=text, action="polish"))


@router.post("/explain")
async def explain_text(text: str = "error"):
    return await _do_process(TextProcessRequest(text=text, action="explain"))
