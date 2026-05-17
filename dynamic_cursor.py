import sys
import threading
import time
from collections import deque
from pynput import mouse
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor

class Ripple:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 5.0
        self.alpha = 255
        self.active = True

    def update(self):
        self.radius += 2.0  
        self.alpha -= 15    
        if self.alpha <= 0:
            self.active = False

class CursorOverlay(QWidget):
    # 信号现在不需要传递 pynput 的 x, y，直接触发即可
    update_position_signal = pyqtSignal()
    add_ripple_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.cursor_x = -100.0
        self.cursor_y = -100.0
        self.trail = deque(maxlen=20)
        self.ripples = []
        
        self.base_radius = 8
        self.current_radius = 8
        self.growing = True
        
        self.initUI()
        
        self.update_position_signal.connect(self.update_cursor_position)
        self.add_ripple_signal.connect(self.add_ripple)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_effects)
        self.timer.start(30)

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput | 
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 适配多显示器：获取所有屏幕的联合区域
        rect = QRect()
        for screen in QApplication.screens():
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)
        
        self.show()

    def get_local_pos(self):
        # 关键修复：获取 PyQt 视角的全局逻辑坐标，并映射到当前窗口的局部坐标
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        return local_pos.x(), local_pos.y()

    def update_cursor_position(self):
        lx, ly = self.get_local_pos()
        self.cursor_x = lx
        self.cursor_y = ly
        self.trail.append((lx, ly))
        self.update()

    def add_ripple(self):
        lx, ly = self.get_local_pos()
        self.ripples.append(Ripple(lx, ly))

    def animate_effects(self):
        if self.growing:
            self.current_radius += 0.5
            if self.current_radius >= 12:
                self.growing = False
        else:
            self.current_radius -= 0.5
            if self.current_radius <= 8:
                self.growing = True
                
        for ripple in self.ripples:
            ripple.update()
        self.ripples = [r for r in self.ripples if r.active]
        
        if len(self.trail) > 0 and self.cursor_x == self.trail[-1][0] and self.cursor_y == self.trail[-1][1]:
            if int(time.time() * 10) % 2 == 0:
                self.trail.popleft()
        
        if self.cursor_x >= 0 or len(self.trail) > 0 or len(self.ripples) > 0:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        trail_length = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(255 * (i / trail_length) * 0.5)
            radius = self.base_radius * (i / trail_length) * 0.8
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(100, 200, 255, alpha))
            painter.drawEllipse(QPointF(tx, ty), radius, radius)

        for ripple in self.ripples:
            alpha = max(0, min(255, ripple.alpha))
            pen = QPen(QColor(255, 150, 50, alpha), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(ripple.x, ripple.y), ripple.radius, ripple.radius)

        if self.cursor_x >= 0 and self.cursor_y >= 0:
            pen = QPen(QColor(50, 150, 255, 200), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(50, 200, 255, 120))
            
            center = QPointF(self.cursor_x, self.cursor_y)
            painter.drawEllipse(center, self.current_radius, self.current_radius)
            
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.drawLine(int(self.cursor_x - 4), int(self.cursor_y), int(self.cursor_x + 4), int(self.cursor_y))
            painter.drawLine(int(self.cursor_x), int(self.cursor_y - 4), int(self.cursor_x), int(self.cursor_y + 4))

def mouse_tracking_thread(overlay_widget):
    def on_move(x, y):
        # 不再传递 pynput 的坐标，直接通知 UI 更新
        overlay_widget.update_position_signal.emit()
        
    def on_click(x, y, button, pressed):
        if pressed:
            overlay_widget.add_ripple_signal.emit()

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = CursorOverlay()
    listener_thread = threading.Thread(target=mouse_tracking_thread, args=(overlay,), daemon=True)
    listener_thread.start()
    
    print("✨ 精准定位版动态光标已启动...")
    print("✅ 修复了 macOS Retina 屏幕高DPI缩放导致的坐标飘移")
    print("✅ 增加了多显示器全屏覆盖支持")
    print("按 Ctrl+C 在终端中停止，或直接关闭终端。")
    sys.exit(app.exec())
