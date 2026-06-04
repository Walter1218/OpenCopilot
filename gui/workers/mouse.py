"""gui/workers/mouse.py module"""
from PyQt6.QtCore import pyqtSignal, QThread
from pynput import mouse
import sys as _sys
class MouseListenerWorker(QThread):
    mouse_moved = pyqtSignal(int, int)
    global_click = pyqtSignal(int, int)
    right_clicked = pyqtSignal(int, int, int)  # x, y, click_count
    listener_error = pyqtSignal(str)
    listener_died = pyqtSignal()  # listener 非正常退出时通知主线程重启

    def __init__(self):
        super().__init__()
        self.last_right_click_time = 0
        self.click_threshold = 0.55  # 550ms，适配触控板/蓝牙鼠标的双击节奏
        self._right_click_count = 0
        self._listener = None
        self._stop_requested = False

    def run(self):
        self._stop_requested = False

        def on_move(x, y):
            try:
                self.mouse_moved.emit(int(x), int(y))
            except Exception:
                pass  # 回调异常不能向外抛，否则 pynput 会静默终止 listener
            
        def on_click(x, y, button, pressed):
            try:
                if pressed:
                    self.global_click.emit(int(x), int(y))
                    if button == mouse.Button.right:
                        current_time = time.time()
                        if current_time - self.last_right_click_time < self.click_threshold:
                            self._right_click_count += 1
                        else:
                            self._right_click_count = 1
                        self.last_right_click_time = current_time
                        self.right_clicked.emit(int(x), int(y), self._right_click_count)
            except Exception:
                pass  # 同上

        try:
            self._listener = mouse.Listener(on_move=on_move, on_click=on_click)
            self._listener.start()
            self._listener.join()
        except Exception:
            err = traceback.format_exc()
            self.listener_error.emit(err)

        # 如果不是主动 stop 导致的退出，通知主线程
        if not self._stop_requested:
            self.listener_died.emit()

    def stop(self):
        """停止 pynput 鼠标监听器。"""
        self._stop_requested = True
        if self._listener:
            self._listener.stop()


# ==========================================
# 3. 智能悬浮卡片 (独立图层，可交互)
# ==========================================
