import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from AppKit import NSWorkspace, NSObject
    from Foundation import NSNotificationCenter, NSRunLoop, NSDate
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

_async_queue: Optional[asyncio.Queue] = None
_observer = None

if HAS_PYOBJC:
    class AppActivationObserver(NSObject):
        def appActivated_(self, notification):
            info = notification.userInfo()
            app = info.get("NSWorkspaceApplicationKey")
            if app:
                app_name = app.localizedName()
                bundle_id = app.bundleIdentifier()
                event = {
                    "type": "app_activated",
                    "app_name": app_name,
                    "bundle_id": bundle_id
                }
                logger.info(f"[EventsProbe] Real app activated: {app_name} ({bundle_id})")
                
                if _async_queue:
                    _async_queue.put_nowait(event)
else:
    class AppActivationObserver:
        pass

async def _pump_runloop():
    if not HAS_PYOBJC:
        return
    runloop = NSRunLoop.currentRunLoop()
    while True:
        # Pump the NSRunLoop so it can dispatch distributed notifications
        runloop.runMode_beforeDate_(
            "kCFRunLoopDefaultMode", 
            NSDate.dateWithTimeIntervalSinceNow_(0.01)
        )
        await asyncio.sleep(0.05)

def start_events_probe(loop: asyncio.AbstractEventLoop, async_queue: asyncio.Queue):
    """启动全局事件探针协程"""
    global _async_queue, _observer
    _async_queue = async_queue
    
    if not HAS_PYOBJC:
        logger.error("Cannot start events probe: PyObjC not installed.")
        return False
        
    workspace = NSWorkspace.sharedWorkspace()
    notification_center = workspace.notificationCenter()
    
    _observer = AppActivationObserver.alloc().init()
    
    notification_center.addObserver_selector_name_object_(
        _observer,
        b'appActivated:',
        "NSWorkspaceDidActivateApplicationNotification",
        None
    )
    
    logger.info("[EventsProbe] Started macOS NSWorkspace events probe.")
    asyncio.create_task(_pump_runloop())
    return True