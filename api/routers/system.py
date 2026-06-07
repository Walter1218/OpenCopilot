"""系统工具路由：/api/system/*"""
import os
import sys
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from smart_copilot_api import SystemStatusResponse
from system_probe_client import SystemProbeClient

router = APIRouter(prefix="/api/system", tags=["system"])


# =============================================================================
# Pydantic 模型（v5 新增）
# =============================================================================

class ApplyToIdeRequest(BaseModel):
    """应用到 IDE 请求"""
    text: str = Field(..., description="要插入的文本内容")
    action: str = Field("insert", description="操作类型: insert/replace/append")
    target: Optional[str] = Field(None, description="目标: cursor/selection/new_file")


@router.get("/status", response_model=SystemStatusResponse)
async def system_status():
    probe = SystemProbeClient()
    broker_ok = await _check_broker()
    ide_ok, browser_ok = False, False
    try:
        status = probe.get_status()
        ide_ok = status.get("ide_connected", False)
        browser_ok = status.get("browser_connected", False)
    except:
        pass
    return SystemStatusResponse(
        agent_online=True, broker_online=broker_ok,
        ide_connected=ide_ok, browser_connected=browser_ok,
    )


@router.get("/clipboard")
async def get_clipboard():
    try:
        import subprocess
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
        return {"text": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selection")
async def get_selection():
    try:
        probe = SystemProbeClient()
        return probe.get_selection()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/frontmost-app")
async def get_frontmost_app():
    try:
        probe = SystemProbeClient()
        return probe.get_frontmost_app()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/screenshot")
async def get_screenshot():
    try:
        probe = SystemProbeClient()
        return probe.take_screenshot()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


async def _check_broker():
    try:
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.get("http://127.0.0.1:18889/health", timeout=2)
            return r.status_code == 200
    except:
        return False


# =============================================================================
# v5 新增端点
# =============================================================================

@router.get("/active-document")
async def get_active_document():
    """
    获取当前活动文档信息

    通过 Broker 获取当前前台应用的活动文档内容（文件路径、光标位置、文档文本）。
    若 Broker 不支持 active-doc 接口，降级返回前台应用名称。
    """
    print("[V5-API] GET /api/system/active-document")
    try:
        probe = SystemProbeClient()
        app_name = probe.get_frontmost_app() or ""

        # 尝试通过 broker 获取活动文档详情
        doc_info = {
            "app_name": app_name,
            "file_path": "",
            "content": "",
            "cursor_line": 0,
            "cursor_column": 0,
            "line_count": 0,
            "status": "unavailable",
        }

        try:
            import httpx
            headers = probe.headers
            resp = httpx.get(
                "http://127.0.0.1:18889/api/v1/system/active-doc",
                headers=headers, timeout=3.0
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                doc_info.update({
                    "file_path": data.get("file_path", ""),
                    "content": data.get("content", ""),
                    "cursor_line": data.get("cursor_line", 0),
                    "cursor_column": data.get("cursor_column", 0),
                    "line_count": data.get("line_count", 0),
                    "status": "ok",
                })
            else:
                doc_info["status"] = f"broker_http_{resp.status_code}"
        except Exception as e:
            doc_info["status"] = f"broker_error: {str(e)[:100]}"

        print(f"[V5-API] active-document: app={app_name}, status={doc_info['status']}")
        return doc_info
    except Exception as e:
        print(f"[V5-API] active-document error: {e}")
        raise HTTPException(status_code=500, detail=f"获取活动文档失败: {str(e)}")


@router.post("/apply-to-ide")
async def apply_to_ide(request: ApplyToIdeRequest):
    """
    将文本应用到 IDE

    通过 Broker 将文本插入到 IDE 光标位置。若 Broker 不支持 insert-text 接口，
    降级到剪贴板写入（用户可手动 Cmd+V 粘贴）。
    """
    print(f"[V5-API] POST /api/system/apply-to-ide | action={request.action}, text_len={len(request.text)}")
    try:
        probe = SystemProbeClient()

        # 尝试通过 broker 插入文本
        try:
            import httpx
            headers = probe.headers
            payload = {
                "text": request.text,
                "action": request.action,
                "target": request.target or "cursor",
            }
            resp = httpx.post(
                "http://127.0.0.1:18889/api/v1/system/insert-text",
                json=payload, headers=headers, timeout=5.0
            )
            if resp.status_code == 200:
                print("[V5-API] apply-to-ide: success via broker insert-text")
                return {
                    "success": True,
                    "method": "broker_insert",
                    "action": request.action,
                    "text_len": len(request.text),
                }
        except Exception as e:
            print(f"[V5-API] apply-to-ide: broker failed ({e}), fallback to clipboard")

        # 降级：写入剪贴板
        import subprocess
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(input=request.text.encode("utf-8"))
        print("[V5-API] apply-to-ide: success via clipboard fallback")
        return {
            "success": True,
            "method": "clipboard",
            "action": request.action,
            "text_len": len(request.text),
            "message": "已复制到剪贴板，请在 IDE 中 Cmd+V 粘贴",
        }
    except Exception as e:
        print(f"[V5-API] apply-to-ide error: {e}")
        raise HTTPException(status_code=500, detail=f"应用到 IDE 失败: {str(e)}")


@router.get("/more-actions")
async def get_more_actions():
    """
    获取 Work Tab "More" 按钮的可用操作列表

    从 config.json 的 work_actions 配置读取，若无配置则返回默认操作列表。
    """
    print("[V5-API] GET /api/system/more-actions")
    try:
        from llm_provider import load_config
        config = load_config()
        custom_actions = config.get("work_actions", None)

        if custom_actions and isinstance(custom_actions, list):
            actions = custom_actions
        else:
            # 默认 More 操作列表
            actions = [
                {"id": "summarize", "label": "📝 Summarize", "description": "总结内容"},
                {"id": "custom", "label": "✏️ Custom", "description": "自定义指令"},
                {"id": "compare", "label": "🔀 Compare", "description": "对比两段文本"},
                {"id": "extract_keywords", "label": "🏷️ Keywords", "description": "提取关键词"},
                {"id": "generate_test", "label": "🧪 Generate Test", "description": "生成测试用例"},
            ]

        print(f"[V5-API] more-actions: returned {len(actions)} actions")
        return {"actions": actions, "total": len(actions)}
    except Exception as e:
        print(f"[V5-API] more-actions error: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作列表失败: {str(e)}")
