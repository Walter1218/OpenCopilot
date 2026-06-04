"""任务管理路由：/api/tasks/*"""
import os, sys, uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from smart_copilot_api import session_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_tasks: Dict[str, Dict[str, Any]] = {}


class TaskCreateRequest(BaseModel):
    task_type: str
    description: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskTemplate(BaseModel):
    name: str
    task_type: str
    system_prompt: str
    suggested_actions: list = []


TEMPLATES = {
    "code_review": TaskTemplate(name="代码审查", task_type="code_review",
        system_prompt="你是一个资深代码审查专家。", suggested_actions=["code_review"]),
    "bug_fix": TaskTemplate(name="Bug修复", task_type="bug_fix",
        system_prompt="你是一个Bug修复专家。", suggested_actions=["bug_fix"]),
    "doc_summary": TaskTemplate(name="文档总结", task_type="doc_summary",
        system_prompt="你是文档分析专家。", suggested_actions=["summarize"]),
    "translate": TaskTemplate(name="翻译", task_type="translate",
        system_prompt="你是一个专业翻译。", suggested_actions=["translate"]),
    "ppt_create": TaskTemplate(name="PPT制作", task_type="ppt_create",
        system_prompt="你是PPT制作专家。", suggested_actions=["ppt_generate"]),
}


@router.post("/create")
async def create_task(request: TaskCreateRequest):
    task_id = str(uuid.uuid4())
    sid = request.session_id or session_manager.get_or_create()
    task = {
        "task_id": task_id, "session_id": sid,
        "task_type": request.task_type, "description": request.description,
        "status": "pending", "progress": 0.0,
        "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat(),
        "completed_at": None, "result": None, "error": None,
        "context": [], "metadata": request.metadata or {},
    }
    _tasks[task_id] = task
    return {"status": "success", "task": task}


@router.get("/{task_id}")
async def get_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return {"status": "success", "task": _tasks[task_id]}


@router.put("/{task_id}")
async def update_task(task_id: str, request: TaskUpdateRequest):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    t = _tasks[task_id]
    if request.status: t["status"] = request.status
    if request.progress is not None:
        t["progress"] = min(1.0, max(0.0, request.progress))
    if request.result is not None: t["result"] = request.result
    if request.error: t["error"] = request.error
    t["updated_at"] = datetime.now().isoformat()
    return {"status": "success", "task": t}


@router.get("")
async def list_tasks():
    return {"tasks": list(_tasks.values()), "total": len(_tasks)}


@router.get("/templates")
async def get_templates():
    return {"templates": {k: v.model_dump() for k, v in TEMPLATES.items()}}
