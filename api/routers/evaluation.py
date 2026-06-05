"""评估路由：/api/evaluation/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


class EvaluateRequest(BaseModel):
    content: str
    criteria: Optional[Dict[str, Any]] = None
    language: str = "zh"


class ScoreRequest(BaseModel):
    content: str
    rubric: Optional[Dict[str, Any]] = None


class QualityCheckRequest(BaseModel):
    content: str
    checks: Optional[List[str]] = None


@router.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    import asu_custom_agent
    from smart_copilot_api import _call_agent_pipeline
    try:
        prompt = f"请评估以下内容的质量，根据{'中文' if request.language == 'zh' else 'English'}标准给出评价和改进建议：\n\n{request.content}"
        resp = await _call_agent_pipeline(
            text=prompt, action_type="evaluation", context_source="chat",
            context_meta={"task": "evaluate", "language": request.language},
            enable_web_search=False,
        )
        return {"evaluation": resp, "content": request.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.post("/score")
async def score(request: ScoreRequest):
    from smart_copilot_api import _call_agent_pipeline
    try:
        prompt = f"请对以下内容进行打分（1-10分），并从多个维度给出具体评分和理由：\n\n{request.content}"
        resp = await _call_agent_pipeline(
            text=prompt, action_type="evaluation", context_source="chat",
            context_meta={"task": "score"},
            enable_web_search=False,
        )
        return {"score": resp, "content": request.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评分失败: {str(e)}")


@router.post("/quality-check")
async def quality_check(request: QualityCheckRequest):
    from smart_copilot_api import _call_agent_pipeline
    try:
        checks = ", ".join(request.checks) if request.checks else "语法,风格,逻辑,完整性"
        prompt = f"请对以下内容进行质量检查，检查项包括 {checks}：\n\n{request.content}"
        resp = await _call_agent_pipeline(
            text=prompt, action_type="evaluation", context_source="chat",
            context_meta={"task": "quality_check"},
            enable_web_search=False,
        )
        return {"quality_check": resp, "content": request.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"质量检查失败: {str(e)}")
