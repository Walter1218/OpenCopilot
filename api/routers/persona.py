"""Persona 路由：/api/persona/* 和 /v1/agent/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from asu_custom_agent import load_persona
from opencopilot.capabilities.memory import MemoryManager

router = APIRouter(tags=["persona"])


@router.post("/api/persona/list")
async def list_personas():
    personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personas")
    if os.path.exists(personas_dir):
        return [f.replace(".md", "") for f in os.listdir(personas_dir) if f.endswith(".md")]
    return []


@router.post("/api/persona/get")
async def get_persona(data: dict):
    name = data.get("name", "default")
    content = load_persona(name)
    if not content:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' 不存在")
    return {"name": name, "content": content}


@router.post("/api/persona/save")
async def save_persona(data: dict):
    name = data.get("name", "")
    content = data.get("content", "")
    if not name or not content:
        raise HTTPException(status_code=400, detail="name 和 content 不能为空")
    personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personas")
    os.makedirs(personas_dir, exist_ok=True)
    path = os.path.join(personas_dir, f"{name}.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"success": True, "name": name}


@router.post("/api/persona/delete")
async def delete_persona(data: dict):
    name = data.get("name", "")
    if name in ("default", "code", "translate", "polish", "revision"):
        raise HTTPException(status_code=400, detail="内置 Persona 不可删除")
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personas", f"{name}.md")
    if os.path.exists(path):
        os.remove(path)
        return {"success": True}
    raise HTTPException(status_code=404, detail="Persona 不存在")


@router.get("/v1/agent/personas")
async def v1_personas():
    personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "personas")
    if os.path.exists(personas_dir):
        return [f.replace(".md", "") for f in os.listdir(personas_dir) if f.endswith(".md")]
    return []


@router.post("/v1/agent/personas/reload")
async def reload_personas():
    return {"success": True, "message": "Personas 重新加载"}


@router.get("/v1/agent/sessions")
async def v1_sessions():
    mem = MemoryManager()
    try:
        count = mem.session_count()
        return {"sessions": [], "total": count}
    finally:
        del mem


@router.post("/v1/agent/session/clear")
async def clear_session(data: dict):
    sid = data.get("session_id", "")
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    mem = MemoryManager()
    try:
        mem.clear(sid)
        return {"success": True, "session_id": sid}
    finally:
        del mem
