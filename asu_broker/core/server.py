from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import sys
import os

# 确保能导入同级模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import verify_token
from probes.browser_probe import get_browser_tabs, get_active_tab_dom
from probes.window_probe import get_frontmost_app
from probes.selection_probe import get_clipboard_content, set_clipboard_content, get_selected_text_via_applescript
from probes.app_control_probe import get_notes_content, create_note
from probes.screen_probe import capture_front_window
from probes.fs_probe import read_file_as_context

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

# ==========================================
# 预埋的高级系统交互路由 (草案)
# ==========================================

@app.get("/api/v1/system/clipboard", dependencies=[Depends(verify_token)])
async def api_get_clipboard():
    try:
        content = await get_clipboard_content()
        return {"status": "success", "data": {"content": content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ClipboardRequest(BaseModel):
    content: str

@app.post("/api/v1/system/clipboard", dependencies=[Depends(verify_token)])
async def api_set_clipboard(req: ClipboardRequest):
    try:
        success = await set_clipboard_content(req.content)
        return {"status": "success" if success else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/selection", dependencies=[Depends(verify_token)])
async def api_get_selection():
    try:
        content = await get_selected_text_via_applescript()
        return {"status": "success", "data": {"content": content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class NoteRequest(BaseModel):
    title: str
    body: str

@app.post("/api/v1/apps/notes", dependencies=[Depends(verify_token)])
async def api_create_note(req: NoteRequest):
    try:
        success = await create_note(req.title, req.body)
        return {"status": "success" if success else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/screen/front", dependencies=[Depends(verify_token)])
async def api_capture_front_window():
    try:
        b64_image = await capture_front_window()
        return {"status": "success", "data": {"image_base64": b64_image}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FileRequest(BaseModel):
    file_path: str

@app.post("/api/v1/system/fs/read", dependencies=[Depends(verify_token)])
async def api_read_file(req: FileRequest):
    try:
        content = await read_file_as_context(req.file_path)
        return {"status": "success", "data": {"content": content}}
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
