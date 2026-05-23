import sys, time
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer
import AppKit

class TestWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.lbl = QLabel("Testing...", self)
        self.resize(200, 100)

app = QApplication(sys.argv)
win = TestWin()

def simulate_double_click():
    front_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().localizedName()
    print("Front app before show:", front_app)
    win.show()
    QTimer.singleShot(1000, sys.exit)

QTimer.singleShot(2000, simulate_double_click) # Wait 2 secs, giving me time to switch to Chrome
app.exec()