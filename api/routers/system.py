"""系统工具路由：/api/system/*"""
import os, sys

from fastapi import APIRouter, HTTPException
from smart_copilot_api import SystemStatusResponse
from system_probe_client import SystemProbeClient

router = APIRouter(prefix="/api/system", tags=["system"])


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
