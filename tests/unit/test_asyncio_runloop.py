import asyncio
from AppKit import NSWorkspace, NSObject
from Foundation import NSNotificationCenter, NSRunLoop, NSDate

class Observer(NSObject):
    def appActivated_(self, notification):
        info = notification.userInfo()
        app = info.get("NSWorkspaceApplicationKey")
        print(f"ACTIVATED via asyncio: {app.localizedName()}")

async def pump_runloop():
    runloop = NSRunLoop.currentRunLoop()
    while True:
        # Process events in the NSRunLoop
        runloop.runMode_beforeDate_(
            "kCFRunLoopDefaultMode", 
            NSDate.dateWithTimeIntervalSinceNow_(0.01)
        )
        await asyncio.sleep(0.05)

async def main():
    workspace = NSWorkspace.sharedWorkspace()
    nc = workspace.notificationCenter()
    
    obs = Observer.alloc().init()
    nc.addObserver_selector_name_object_(
        obs,
        b'appActivated:',
        "NSWorkspaceDidActivateApplicationNotification",
        None
    )
    
    print("Listening via asyncio...")
    asyncio.create_task(pump_runloop())
    
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())