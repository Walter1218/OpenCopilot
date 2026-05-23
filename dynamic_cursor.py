#!/usr/bin/env python3
"""动态光标特效——独立演示程序。

展示 CursorOverlay 的呼吸准星、拖尾轨迹和水波纹特效。
可作为独立脚本运行，仅供演示和调试用。
"""
import sys
import threading
from pynput import mouse
from PyQt6.QtWidgets import QApplication
from cursor_effects import CursorOverlay


def mouse_tracking_thread(overlay_widget):
    def on_move(x, y):
        overlay_widget.update_position_signal.emit()

    def on_click(x, y, button, pressed):
        if pressed:
            overlay_widget.add_ripple_signal.emit()

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    overlay = CursorOverlay(enable_transparent_for_input=True)
    listener_thread = threading.Thread(target=mouse_tracking_thread, args=(overlay,), daemon=True)
    listener_thread.start()

    print("✨ 精准定位版动态光标已启动...")
    print("✅ 修复了 macOS Retina 屏幕高DPI缩放导致的坐标飘移")
    print("✅ 增加了多显示器全屏覆盖支持")
    print("按 Ctrl+C 在终端中停止，或直接关闭终端。")
    sys.exit(app.exec())
