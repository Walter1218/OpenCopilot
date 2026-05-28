import time
from AppKit import NSWorkspace, NSObject, NSApplication
from Foundation import NSNotificationCenter, NSRunLoop, NSDate
from PyObjCTools import AppHelper

class Observer(NSObject):
    def appActivated_(self, notification):
        info = notification.userInfo()
        app = info.get("NSWorkspaceApplicationKey")
        print(f"ACTIVATED: {app.localizedName()}")

def main():
    NSApplication.sharedApplication() # Initialize NSApp
    workspace = NSWorkspace.sharedWorkspace()
    nc = workspace.notificationCenter()
    
    obs = Observer.alloc().init()
    nc.addObserver_selector_name_object_(
        obs,
        b'appActivated:',
        "NSWorkspaceDidActivateApplicationNotification",
        None
    )
    
    print("Listening for 10 seconds...")
    # AppHelper.runConsoleEventLoop()
    # run manually to timeout
    timeout = NSDate.dateWithTimeIntervalSinceNow_(10)
    NSRunLoop.currentRunLoop().runUntilDate_(timeout)

if __name__ == "__main__":
    main()