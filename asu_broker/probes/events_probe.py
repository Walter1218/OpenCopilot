import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from AppKit import NSWorkspace
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

_async_queue: Optional[asyncio.Queue] = None

async def _poll_active_app():
    """轮询获取当前活跃应用，避免与 Uvicorn/asyncio 事件循环冲突"""
    if not HAS_PYOBJC:
        return
        
    last_bundle_id = None
    workspace = NSWorkspace.sharedWorkspace()
    
    while True:
        try:
            app = workspace.frontmostApplication()
            if app:
                bundle_id = app.bundleIdentifier()
                if bundle_id != last_bundle_id:
                    app_name = app.localizedName()
                    event = {
                        "type": "app_activated",
                        "app_name": app_name,
                        "bundle_id": bundle_id
                    }
                    # 确保打印到终端
                    print(f"[EventsProbe] Real app activated: {app_name} ({bundle_id})")
                    logger.info(f"[EventsProbe] Real app activated: {app_name} ({bundle_id})")
                    
                    if _async_queue:
                        _async_queue.put_nowait(event)
                    
                    last_bundle_id = bundle_id
        except Exception as e:
            logger.error(f"[EventsProbe] Error polling active app: {e}")
            
        await asyncio.sleep(0.5)

def start_events_probe(loop: asyncio.AbstractEventLoop, async_queue: asyncio.Queue):
    """启动全局事件探针协程"""
    global _async_queue
    _async_queue = async_queue
    
    if not HAS_PYOBJC:
        logger.error("Cannot start events probe: PyObjC not installed.")
        print("❌ Cannot start events probe: PyObjC not installed. Please run `pip install pyobjc`.")
        return False
        
    print("[EventsProbe] Started macOS active app polling probe.")
    logger.info("[EventsProbe] Started macOS active app polling probe.")
    
    # 将轮询任务加入当前事件循环
    loop.create_task(_poll_active_app())
    return True