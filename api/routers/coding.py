"""代码处理路由：/api/coding/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from smart_copilot_api import _call_agent_pipeline

router = APIRouter(prefix="/api/coding", tags=["coding"])


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"
    context: Optional[str] = None


class BugFixRequest(BaseModel):
    code: str
    error_message: Optional[str] = None
    language: str = "python"


class CodeExplainRequest(BaseModel):
    code: str
    language: str = "python"
    detail_level: str = "standard"


class RefactorRequest(BaseModel):
    code: str
    language: str = "python"
    goal: Optional[str] = None


class EnhanceApiRequest(BaseModel):
    code: str
    enhancement: str = ""
    language: str = "python"


def _build_prompt(intent: str, ctx: dict) -> str:
    code = ctx.get("code", "")
    lang = ctx.get("language", "python")
    if intent == "review":
        return f"请审查以下 {lang} 代码，指出问题、优化建议和安全隐患：\n\n```{lang}\n{code}\n```"
    elif intent == "bug_fix":
        err = ctx.get("error_message", "")
        return f"请分析并修复以下 {lang} 代码中的 Bug。{'错误信息: ' + err if err else ''}\n\n```{lang}\n{code}\n```"
    elif intent == "explain":
        return f"请解释以下 {lang} 代码的功能和逻辑（详细程度: {ctx.get('detail_level', 'standard')}）：\n\n```{lang}\n{code}\n```"
    elif intent == "refactor":
        goal = ctx.get("goal", f"优化代码质量和可读性")
        return f"请重构以下 {lang} 代码。重构目标: {goal}\n\n```{lang}\n{code}\n```"
    elif intent == "enhance_api":
        enhancement = ctx.get("enhancement", "")
        return f"请增强以下 {lang} API 的功能。{enhancement}\n\n```{lang}\n{code}\n```"
    return f"请处理以下 {lang} 代码：\n\n```{lang}\n{code}\n```"


@router.post("/review")
async def code_review(request: CodeReviewRequest):
    try:
        if not request.code.strip():
            raise HTTPException(status_code=400, detail="代码不能为空")
        resp = await _call_agent_pipeline(
            text=_build_prompt("review", request.model_dump()),
            action_type="coding", context_source="ide",
            context_meta={"task": "code_review", "language": request.language},
            enable_web_search=False,
        )
        return {"review": resp, "source": "agent_pipeline"}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"代码审查失败: {str(e)}")


@router.post("/bug-fix")
async def bug_fix(request: BugFixRequest):
    try:
        resp = await _call_agent_pipeline(
            text=_build_prompt("bug_fix", request.model_dump()),
            action_type="coding", context_source="ide",
            context_meta={"task": "bug_fix", "language": request.language},
            enable_web_search=False,
        )
        return {"fix": resp, "source": "agent_pipeline"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"Bug修复失败: {str(e)}")


@router.post("/explain")
async def code_explain(request: CodeExplainRequest):
    try:
        resp = await _call_agent_pipeline(
            text=_build_prompt("explain", request.model_dump()),
            action_type="coding", context_source="ide",
            context_meta={"task": "explain", "language": request.language},
            enable_web_search=False,
        )
        return {"explanation": resp, "source": "agent_pipeline"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"代码解释失败: {str(e)}")


@router.post("/refactor")
async def code_refactor(request: RefactorRequest):
    try:
        resp = await _call_agent_pipeline(
            text=_build_prompt("refactor", request.model_dump()),
            action_type="coding", context_source="ide",
            context_meta={"task": "refactor", "language": request.language},
            enable_web_search=False,
        )
        return {"refactored_code": resp, "source": "agent_pipeline"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"代码重构失败: {str(e)}")


@router.post("/enhance-api")
async def enhance_api(request: EnhanceApiRequest):
    try:
        resp = await _call_agent_pipeline(
            text=_build_prompt("enhance_api", request.model_dump()),
            action_type="coding", context_source="ide",
            context_meta={"task": "enhance_api", "language": request.language},
            enable_web_search=False,
        )
        return {"enhanced_code": resp, "source": "agent_pipeline"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"API增强失败: {str(e)}")


@router.post("/analyze")
async def code_analyze(data: dict):
    code = data.get("code", "")
    lang = data.get("language", "python")
    try:
        resp = await _call_agent_pipeline(
            text=f"请全面分析以下 {lang} 代码的结构、复杂度、质量指标和依赖关系：\n\n```{lang}\n{code}\n```",
            action_type="coding", context_source="ide",
            context_meta={"task": "analyze", "language": lang},
            enable_web_search=False,
        )
        return {"analysis": resp, "source": "agent_pipeline"}
    except Exception as e: raise HTTPException(status_code=500, detail=f"代码分析失败: {str(e)}")
