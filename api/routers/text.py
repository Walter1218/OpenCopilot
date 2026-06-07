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

LANG_MAP = {
    "auto": "自动检测", "zh": "中文", "en": "英文",
    "ja": "日文", "ko": "韩文", "fr": "法文",
    "de": "德文", "es": "西班牙文", "ru": "俄文",
}

PROMPTS = {
    "translate": lambda t, src, tgt: (
        f"请将以下文本从{LANG_MAP.get(src, src)}翻译为{LANG_MAP.get(tgt, tgt)}：\n\n{t}"
        if src != "auto"
        else f"请将以下文本翻译为{LANG_MAP.get(tgt, tgt)}：\n\n{t}"
    ),
    "polish": lambda t, _: f"请润色以下文本，使其更加专业和流畅：\n\n{t}",
    "explain": lambda t, _: f"请详细解释以下内容：\n\n{t}",
    "summarize": lambda t, _: f"请总结以下内容的要点：\n\n{t}",
    "code": lambda t, _: f"请解析以下代码，说明其功能和关键点：\n\n{t}",
}


async def _do_process(request: TextProcessRequest):
    if request.action == "custom" and request.custom_instruction:
        prompt = f"{request.custom_instruction}\n\n{request.text}"
    elif request.action in PROMPTS:
        # 翻译操作：解析 source_lang 和 target_language
        if request.action == "translate":
            src_lang = getattr(request, "source_language", "auto") or "auto"
            tgt_lang = request.target_language or "zh"
            prompt = PROMPTS[request.action](request.text, src_lang, tgt_lang)
        else:
            prompt = PROMPTS[request.action](request.text, request.target_language or "zh")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {request.action}")

    context_meta = {"task": "text_process", "action": request.action}
    if request.action == "translate":
        context_meta["source_lang"] = getattr(request, "source_language", "auto") or "auto"
        context_meta["target_lang"] = request.target_language or "zh"

    resp = await _call_agent_pipeline(
        text=prompt,
        action_type=ACTION_PERSONA.get(request.action, "default"),
        context_source="chat",
        context_meta=context_meta,
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
