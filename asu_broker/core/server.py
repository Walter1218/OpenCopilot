from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
import os
import asyncio
import time
import signal

# 确保能导入同级模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import verify_token
from probes.browser_probe import get_browser_tabs, get_active_tab_dom
from probes.window_probe import get_frontmost_app
from probes.selection_probe import get_clipboard_content, set_clipboard_content, get_selected_text_via_applescript
from probes.app_control_probe import get_notes_content, create_note
from probes.screen_probe import capture_front_window
from probes.fs_probe import read_file_as_context
from probes.office_probe import read_office_file

# ============================================================
# 默认超时配置（秒）
# ============================================================
TIMEOUT_BROWSER_DOM = 8.0      # DOM 提取可能因页面复杂度而异
TIMEOUT_BROWSER_TABS = 5.0     # 标签页枚举通常较快
TIMEOUT_FRONT_WINDOW = 3.0     # 截图是 I/O 操作
TIMEOUT_CLIPBOARD = 3.0        # pbpaste/pbcopy 很快
TIMEOUT_SELECTION = 4.0        # 模拟 Cmd+C 需要等待剪贴板更新
TIMEOUT_NOTES = 5.0            # 备忘录创建涉及 AppleScript
TIMEOUT_FRONT_APP = 3.0        # 前台应用探针轻量
TIMEOUT_FILE_READ = 5.0        # 文件 I/O
TIMEOUT_OFFICE_READ = 15.0     # Office 文档解析（含解压+遍历）
TIMEOUT_DEFAULT = 10.0         # 通用回退超时

# ============================================================
# FastAPI 应用实例
# ============================================================
app = FastAPI(
    title="ASU Privileged Broker",
    description="ASU 的高权限本地代理服务，用于沙盒穿透和跨进程系统探测。",
    version="1.1.0"
)


# ============================================================
# 统一错误格式 —— 异常处理器
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """将 HTTPException 包装为统一 JSON 错误结构"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": f"BROKER_HTTP_{exc.status_code}",
            "message": str(exc.detail)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """兜底异常处理器，防止 500 HTML 页面返回"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "BROKER_INTERNAL_ERROR",
            "message": str(exc)
        }
    )


# ============================================================
# 请求日志中间件
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录每个请求的方法、路径、响应状态和耗时"""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if request.url.path != "/health":
        print(f"[Broker] {request.method} {request.url.path} → {response.status_code} ({duration:.2f}s)")
    return response


# ============================================================
# 路由
# ============================================================

# ---------- 能力发现 ----------

@app.get("/api/v1/system/capabilities", dependencies=[Depends(verify_token)])
async def api_get_capabilities():
    """返回 Broker 当前拥有的全部能力清单，方便 ASU 动态适配"""
    return {
        "status": "success",
        "data": {
            "version": "1.1.0",
            "broker": {
                "port": 18889,
                "auth": "bearer_token",
                "token_file": os.path.expanduser("~/.asu_broker_token")
            },
            "capabilities": {
                "browser": {
                    "dom_extraction": {
                        "supported": True,
                        "browsers": ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"],
                        "method": "applescript_javascript_injection",
                        "endpoint": "POST /api/v1/browser/dom"
                    },
                    "tabs_listing": {
                        "supported": True,
                        "browsers": ["Google Chrome"],
                        "endpoint": "GET /api/v1/browser/tabs"
                    }
                },
                "system": {
                    "frontmost_app": {
                        "supported": True,
                        "method": "applescript_system_events",
                        "endpoint": "GET /api/v1/system/frontmost",
                        "returns": ["app_name"]
                    },
                    "clipboard_read": {
                        "supported": True,
                        "method": "pbpaste",
                        "endpoint": "GET /api/v1/system/clipboard"
                    },
                    "clipboard_write": {
                        "supported": True,
                        "method": "pbcopy",
                        "endpoint": "POST /api/v1/system/clipboard"
                    },
                    "selection_read": {
                        "supported": True,
                        "method": "applescript_cmd_c",
                        "endpoint": "GET /api/v1/system/selection",
                        "note": "模拟 Cmd+C 实现，可能对某些应用有副作用"
                    },
                    "screenshot_front_window": {
                        "supported": True,
                        "format": "base64_png",
                        "endpoint": "GET /api/v1/system/screen/front"
                    },
                    "shutdown": {
                        "supported": True,
                        "endpoint": "POST /api/v1/system/shutdown"
                    }
                },
                "filesystem": {
                    "file_read": {
                        "supported": True,
                        "method": "python_open",
                        "endpoint": "POST /api/v1/system/fs/read"
                    },
                    "office_read": {
                        "supported": True,
                        "formats": ["docx", "pptx"],
                        "method": "python-docx / python-pptx",
                        "endpoint": "POST /api/v1/system/fs/office/read"
                    }
                },
                "apps": {
                    "notes_create": {
                        "supported": True,
                        "method": "applescript_notes",
                        "endpoint": "POST /api/v1/apps/notes"
                    }
                },
                "realtime": {
                    "websocket_events": {
                        "supported": False,
                        "planned": "v2.0",
                        "description": "前台应用切换、浏览器标签变更等事件主动推送"
                    }
                }
            }
        }
    }


# ---------- 健康检查 ----------

@app.get("/health", dependencies=[Depends(verify_token)])
async def health_check():
    """健康检查，同时验证探针是否真正可用"""
    probes_ok = False
    try:
        app_name = await asyncio.wait_for(get_frontmost_app(), timeout=TIMEOUT_FRONT_APP)
        probes_ok = bool(app_name)
    except Exception:
        probes_ok = False

    return {
        "status": "ok",
        "message": "Privileged Broker is running.",
        "probes_available": probes_ok,
        "version": "1.1.0"
    }


# ---------- 前台应用探测 ----------

@app.get("/api/v1/system/frontmost", dependencies=[Depends(verify_token)])
async def api_get_frontmost():
    try:
        app_name = await asyncio.wait_for(get_frontmost_app(), timeout=TIMEOUT_FRONT_APP)
        return {"status": "success", "data": {"app_name": app_name}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe frontmost_app timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 剪贴板读写 ----------

@app.get("/api/v1/system/clipboard", dependencies=[Depends(verify_token)])
async def api_get_clipboard():
    try:
        content = await asyncio.wait_for(get_clipboard_content(), timeout=TIMEOUT_CLIPBOARD)
        return {"status": "success", "data": {"content": content}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe clipboard_read timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClipboardRequest(BaseModel):
    content: str


@app.post("/api/v1/system/clipboard", dependencies=[Depends(verify_token)])
async def api_set_clipboard(req: ClipboardRequest):
    try:
        success = await asyncio.wait_for(set_clipboard_content(req.content), timeout=TIMEOUT_CLIPBOARD)
        return {"status": "success" if success else "error"}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe clipboard_write timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 选区提取 ----------

@app.get("/api/v1/system/selection", dependencies=[Depends(verify_token)])
async def api_get_selection():
    try:
        content = await asyncio.wait_for(get_selected_text_via_applescript(), timeout=TIMEOUT_SELECTION)
        return {"status": "success", "data": {"content": content}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe selection_read timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 备忘录操作 ----------

class NoteRequest(BaseModel):
    title: str
    body: str


@app.post("/api/v1/apps/notes", dependencies=[Depends(verify_token)])
async def api_create_note(req: NoteRequest):
    try:
        success = await asyncio.wait_for(create_note(req.title, req.body), timeout=TIMEOUT_NOTES)
        return {"status": "success" if success else "error"}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe notes_create timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 屏幕截图 ----------

@app.get("/api/v1/system/screen/front", dependencies=[Depends(verify_token)])
async def api_capture_front_window():
    try:
        b64_image = await asyncio.wait_for(capture_front_window(), timeout=TIMEOUT_FRONT_WINDOW)
        return {"status": "success", "data": {"image_base64": b64_image}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe screenshot timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 文件系统读取 ----------

class FileRequest(BaseModel):
    file_path: str


@app.post("/api/v1/system/fs/read", dependencies=[Depends(verify_token)])
async def api_read_file(req: FileRequest):
    try:
        content = await asyncio.wait_for(read_file_as_context(req.file_path), timeout=TIMEOUT_FILE_READ)
        return {"status": "success", "data": {"content": content}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe file_read timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Office 文档解析（.docx / .pptx）----------

@app.post("/api/v1/system/fs/office/read", dependencies=[Depends(verify_token)])
async def api_read_office_file(req: FileRequest):
    """解析 .docx 或 .pptx 文件，提取纯文本内容供全文修订等场景使用。"""
    try:
        result = await asyncio.wait_for(read_office_file(req.file_path), timeout=TIMEOUT_OFFICE_READ)
        return {"status": "success", "data": result}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe office_read timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 浏览器标签页 ----------

@app.get("/api/v1/browser/tabs", dependencies=[Depends(verify_token)])
async def api_get_browser_tabs():
    try:
        tabs_info = await asyncio.wait_for(get_browser_tabs(), timeout=TIMEOUT_BROWSER_TABS)
        return {"status": "success", "data": {"tabs": tabs_info}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe browser_tabs timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 浏览器 DOM 提取 ----------

class DOMRequest(BaseModel):
    browser_name: str


@app.post("/api/v1/browser/dom", dependencies=[Depends(verify_token)])
async def api_get_browser_dom(req: DOMRequest):
    try:
        content = await asyncio.wait_for(get_active_tab_dom(req.browser_name), timeout=TIMEOUT_BROWSER_DOM)
        return {"status": "success", "data": {"content": content}}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Probe browser_dom timed out")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 优雅关闭 ----------

@app.post("/api/v1/system/shutdown", dependencies=[Depends(verify_token)])
async def api_shutdown(background_tasks: BackgroundTasks):
    """优雅关闭 Broker 进程"""
    async def _graceful_shutdown():
        await asyncio.sleep(0.3)  # 确保 HTTP 响应已发出
        print("\n[Broker] 收到 shutdown 请求，正在优雅关闭...")
        os.kill(os.getpid(), signal.SIGTERM)

    background_tasks.add_task(_graceful_shutdown)
    return {"status": "success", "message": "Broker is shutting down gracefully"}
