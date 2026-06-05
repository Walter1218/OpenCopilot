"""配置路由：/api/config"""
import os, sys

from fastapi import APIRouter
from smart_copilot_api import ConfigRequest
from llm_provider import load_config, save_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_config():
    return load_config()


@router.post("")
async def update_config(request: ConfigRequest):
    current = load_config()
    updates = request.model_dump(exclude_none=True)
    for k, v in updates.items():
        if isinstance(v, dict):
            current.setdefault(k, {}).update(v)
        else:
            current[k] = v
    save_config(current)
    return {"success": True, "config": current}


@router.post("/scan-models")
async def scan_models():
    """扫描可用模型"""
    try:
        import httpx
        config = load_config()
        base = config.get("local_api_base", "http://localhost:11434/v1")
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{base.rstrip('/')}/models", timeout=5)
            if r.status_code == 200:
                models = r.json().get("data", [])
                return {"models": [m.get("id", m.get("name")) for m in models]}
    except:
        pass
    return {"models": []}
