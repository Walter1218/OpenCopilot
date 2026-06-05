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
    """轮询获取当前活跃应用"""
    if not HAS_PYOBJC:
        return
        
    last_bundle_id = None
    
    while True:
        try:
            # 必须在主线程环境或者带有有效 NSRunLoop 的上下文中调用
            workspace = NSWorkspace.sharedWorkspace()
            # frontmostApplication() 对于没有 GUI 的后台进程(比如 python 直接运行)，
            # 它返回的永远是运行这个 Python 脚本的终端应用（因为 Python 进程本身没有窗口焦点）
            # 这也是为什么你只能看到 Terminal 的原因。
            # 为了获取全系统的焦点，我们需要获取 activeApplication
            active_app = workspace.activeApplication()
            
            if active_app:
                bundle_id = active_app.get('NSApplicationBundleIdentifier')
                if bundle_id and bundle_id != last_bundle_id:
                    app_name = active_app.get('NSApplicationName', 'Unknown')
                    event = {
                        "type": "app_activated",
                        "app_name": app_name,
                        "bundle_id": bundle_id
                    }
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