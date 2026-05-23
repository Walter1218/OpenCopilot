from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import sys
import os

# 确保能导入同级模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import verify_token
from probes.browser_probe import get_browser_tabs, get_active_tab_dom
from probes.window_probe import get_frontmost_app

app = FastAPI(
    title="ASU Privileged Broker",
    description="ASU 的高权限本地代理服务，用于沙盒穿透和跨进程系统探测。",
    version="1.0.0"
)

# 全局依赖：所有接口必须验证 Token
@app.get("/health", dependencies=[Depends(verify_token)])
async def health_check():
    return {"status": "ok", "message": "Privileged Broker is running."}

@app.get("/api/v1/system/frontmost", dependencies=[Depends(verify_token)])
async def api_get_frontmost():
    try:
        app_name = await get_frontmost_app()
        return {"status": "success", "data": {"app_name": app_name}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/browser/tabs", dependencies=[Depends(verify_token)])
async def api_get_browser_tabs():
    try:
        tabs_info = await get_browser_tabs()
        return {"status": "success", "data": {"tabs": tabs_info}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DOMRequest(BaseModel):
    browser_name: str

@app.post("/api/v1/browser/dom", dependencies=[Depends(verify_token)])
async def api_get_browser_dom(req: DOMRequest):
    try:
        content = await get_active_tab_dom(req.browser_name)
        return {"status": "success", "data": {"content": content}}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
