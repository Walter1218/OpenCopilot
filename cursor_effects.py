"""光标特效层共享模块：水波纹 + 全屏光标特效覆盖层。

本模块提供 CursorOverlay 和 Ripple 类，
被 smart_copilot.py (主程序) 和 dynamic_cursor.py (独立演示) 共同引用，
消除代码重复。
"""

import time
from collections import deque

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor


class Ripple:
    """单击水波纹特效。"""
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
    """全屏鼠标穿透覆盖层，绘制呼吸准星 + 拖尾轨迹 + 水波纹特效。

    信号设计: 使用无参数信号，由外部驱动调用 update_cursor_position()。
    无论调用方传不传参数，内部都通过 QCursor.pos() 获取准确坐标，
    从而兼容多种 PyQt 信号连接方式。
    """

    update_position_signal = pyqtSignal()
    add_ripple_signal = pyqtSignal()

    def __init__(self, enable_transparent_for_input: bool = True):
        """初始化光标覆盖层。

        Args:
            enable_transparent_for_input: 是否启用鼠标穿透。
                主程序为 True (不遮挡用户操作)，独立演示可为 False。
        """
        super().__init__()
        self.cursor_x = -100.0
        self.cursor_y = -100.0
        self.trail = deque(maxlen=20)
        self.ripples = []

        self.base_radius = 8
        self.current_radius = 8
        self.growing = True
        self._transparent_for_input = enable_transparent_for_input

        self._init_ui()

        self.update_position_signal.connect(self.update_cursor_position)
        self.add_ripple_signal.connect(self.add_ripple)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30)

    def _init_ui(self):
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        if self._transparent_for_input:
            flags |= Qt.WindowType.WindowTransparentForInput

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 适配多显示器：获取所有屏幕的联合区域
        rect = QRect()
        for screen in QApplication.screens():
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)
        self.show()

    def _local_pos(self):
        """获取当前鼠标在覆盖层坐标系中的位置。"""
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        return local_pos.x(), local_pos.y()

    def update_cursor_position(self, *_args):
        """更新光标位置并记录拖尾轨迹。

        接受任意数量位置参数（兼容不同信号签名），
        实际坐标总从 QCursor.pos() 获取。
        """
        lx, ly = self._local_pos()
        self.cursor_x = lx
        self.cursor_y = ly
        self.trail.append((lx, ly))
        self.update()

    def add_ripple(self, *_args):
        """在当前位置添加水波纹。"""
        lx, ly = self._local_pos()
        self.ripples.append(Ripple(lx, ly))

    def _animate(self):
        """定时器驱动：更新准星呼吸动画和波纹生命周期。"""
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

        # 静止时缓慢减少拖尾
        if len(self.trail) > 0 and self.cursor_x == self.trail[-1][0] and self.cursor_y == self.trail[-1][1]:
            if int(time.time() * 10) % 2 == 0:
                self.trail.popleft()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 拖尾轨迹
        trail_length = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(255 * (i / trail_length) * 0.5)
            radius = self.base_radius * (i / trail_length) * 0.8
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(100, 200, 255, alpha))
            painter.drawEllipse(QPointF(tx, ty), radius, radius)

        # 2. 水波纹
        for ripple in self.ripples:
            alpha = max(0, min(255, ripple.alpha))
            pen = QPen(QColor(255, 150, 50, alpha), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(ripple.x, ripple.y), ripple.radius, ripple.radius)

        # 3. 呼吸准星
        if self.cursor_x >= 0 and self.cursor_y >= 0:
            pen = QPen(QColor(50, 150, 255, 200), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(50, 200, 255, 120))
            center = QPointF(self.cursor_x, self.cursor_y)
            painter.drawEllipse(center, self.current_radius, self.current_radius)

            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.drawLine(int(self.cursor_x - 4), int(self.cursor_y), int(self.cursor_x + 4), int(self.cursor_y))
            painter.drawLine(int(self.cursor_x), int(self.cursor_y - 4), int(self.cursor_x), int(self.cursor_y + 4))
