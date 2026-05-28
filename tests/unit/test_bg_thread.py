import threading
import time
from AppKit import NSWorkspace, NSObject, NSApplication
from Foundation import NSNotificationCenter, NSRunLoop, NSDate
from PyObjCTools import AppHelper

class TestBgObserver(NSObject):
    def appActivated_(self, notification):
        info = notification.userInfo()
        app = info.get("NSWorkspaceApplicationKey")
        print(f"ACTIVATED in thread: {app.localizedName()}")

def run_loop_in_bg():
    # NSApplication.sharedApplication() # Calling this in bg thread might crash or not work
    workspace = NSWorkspace.sharedWorkspace()
    nc = workspace.notificationCenter()
    
    obs = TestBgObserver.alloc().init()
    nc.addObserver_selector_name_object_(
        obs,
        b'appActivated:',
        "NSWorkspaceDidActivateApplicationNotification",
        None
    )
    print("BG thread listening...")
    AppHelper.runConsoleEventLoop(installInterrupt=False)

def main():
    t = threading.Thread(target=run_loop_in_bg, daemon=True)
    t.start()
    
    print("Main thread sleeping for 10 seconds...")
    time.sleep(10)
    print("Done")

if __name__ == "__main__":
    main()