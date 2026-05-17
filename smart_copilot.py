import sys
import threading
import time
import platform
import pyautogui
import pyperclip
import re
from collections import deque
from pynput import mouse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, 
    QLabel, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRect, QPointF
from PyQt6.QtGui import QCursor, QColor, QPainter, QPen

from minimax_provider import MiniMaxProvider

# ==========================================
# 特效类：水波纹
# ==========================================
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

# ==========================================
# 1. 后台大模型请求线程 (避免阻塞UI)
# ==========================================
class AIWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, provider, prompt):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self._is_running = True

    def run(self):
        try:
            system_prompt = (
                "你是一个强大的AI划词助手。请对用户提供的文本进行处理：\n"
                "1. 如果是外语，请翻译为中文。\n"
                "2. 如果是代码，请简要解释代码的作用。\n"
                "3. 如果是普通文本，请进行简明扼要的总结或解释。\n"
                "输出要求：排版清晰，直接输出结果，不要说多余的客套话。"
            )
            
            full_text = ""
            for chunk in self.provider.stream_chat(self.prompt, system_prompt=system_prompt):
                if not self._is_running:
                    break
                full_text += chunk
                
                # 过滤掉已闭合的 <think>...</think> 标签块
                display_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
                
                # 如果存在未闭合的 <think> 标签，说明模型正在深度思考中
                if '<think>' in display_text:
                    display_text = display_text.split('<think>')[0] + "\n\n[🤔 AI正在深度思考中...]"
                    
                self.text_updated.emit(display_text.strip())
                
        except Exception as e:
            self.text_updated.emit(f"\n[错误]: {str(e)}")
            
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False

# ==========================================
# 2. 鼠标与剪贴板监听线程
# ==========================================
class MouseListenerWorker(QThread):
    text_selected = pyqtSignal(str)
    global_click = pyqtSignal(int, int)
    mouse_moved = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.is_dragging = False
        self.drag_start = None
        self.old_clipboard = pyperclip.paste()
        self.is_mac = platform.system() == 'Darwin'

    def run(self):
        def on_move(x, y):
            self.mouse_moved.emit(int(x), int(y))
            
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left:
                if pressed:
                    self.is_dragging = True
                    self.drag_start = (x, y)
                    self.global_click.emit(int(x), int(y))
                else:
                    if self.is_dragging:
                        drag_end = (x, y)
                        self.is_dragging = False
                        
                        if self.drag_start and drag_end:
                            dx = abs(drag_end[0] - self.drag_start[0])
                            dy = abs(drag_end[1] - self.drag_start[1])
                            
                            if dx > 10 or dy > 10:
                                threading.Timer(0.2, self.capture_selected_text).start()

        with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
            listener.join()

    def capture_selected_text(self):
        try:
            if self.is_mac:
                pyautogui.hotkey('command', 'c')
            else:
                pyautogui.hotkey('ctrl', 'c')
                
            time.sleep(0.2)
            new_clipboard = pyperclip.paste()
            
            if new_clipboard and new_clipboard != self.old_clipboard:
                self.old_clipboard = new_clipboard
                self.text_selected.emit(new_clipboard)
        except Exception as e:
            print(f"划词捕获失败: {e}")

# ==========================================
# 3. 智能悬浮卡片 (独立图层，可交互)
# ==========================================
class AICardWindow(QWidget):
    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.worker = None
        self.initUI()

    def initUI(self):
        # 无边框、置顶、绕过窗口管理器、不抢夺焦点
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.resize(380, 260)
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 35, 240);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 100);
            }
        """)
        self.frame.resize(360, 240)
        self.frame.move(10, 10)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(15, 15, 15, 15)

        self.title_label = QLabel("✨ MiniMax Copilot", self)
        self.title_label.setStyleSheet("color: #4da6ff; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        layout.addWidget(self.title_label)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #eeeeee;
                font-size: 13px;
                border: none;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 60);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.text_edit)

    def show_card(self, text, x, y):
        # 考虑到高DPI，使用 QCursor.pos() 获得准确逻辑坐标
        pos = QCursor.pos()
        self.move(pos.x() + 15, pos.y() + 15)
        
        self.text_edit.clear()
        self.text_edit.setPlainText("正在思考...\n")
        self.show()

        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.worker = AIWorker(self.provider, text)
        self.worker.text_updated.connect(self.on_text_updated)
        self.worker.start()

    def on_text_updated(self, text):
        if not text:
            self.text_edit.setPlainText("正在思考...\n")
        else:
            self.text_edit.setPlainText(text)
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def hide_card(self):
        self.hide()
        if self.worker and self.worker.isRunning():
            self.worker.stop()

# ==========================================
# 4. 全屏光标特效图层 (独立图层，鼠标穿透)
# ==========================================
class CursorOverlay(QWidget):
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
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_effects)
        self.timer.start(30)

    def initUI(self):
        # 必须开启鼠标穿透 (WindowTransparentForInput)，否则会挡住用户操作
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        rect = QRect()
        for screen in QApplication.screens():
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)
        self.show()

    def get_local_pos(self):
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        return local_pos.x(), local_pos.y()

    def update_cursor_position(self, x, y):
        lx, ly = self.get_local_pos()
        self.cursor_x = lx
        self.cursor_y = ly
        self.trail.append((lx, ly))
        self.update()

    def add_ripple(self, x, y):
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


# ==========================================
# 5. 总调度管理器
# ==========================================
class CopilotManager:
    def __init__(self):
        self.provider = MiniMaxProvider()
        
        # 实例化两个独立的图层：
        # 1. 光标特效图层（全屏、鼠标穿透）
        self.cursor_overlay = CursorOverlay()
        # 2. 智能卡片图层（局部、非穿透、可交互）
        self.ai_card = AICardWindow(self.provider)
        
        # 启动鼠标监听
        self.mouse_thread = MouseListenerWorker()
        self.mouse_thread.mouse_moved.connect(self.cursor_overlay.update_cursor_position)
        self.mouse_thread.text_selected.connect(self.on_text_selected)
        self.mouse_thread.global_click.connect(self.on_global_click)
        self.mouse_thread.start()

    def on_text_selected(self, text):
        pos = QCursor.pos()
        self.ai_card.show_card(text, pos.x(), pos.y())

    def on_global_click(self, x, y):
        self.cursor_overlay.add_ripple(x, y)
        if self.ai_card.isVisible():
            global_pos = QCursor.pos()
            # 判断点击位置是否在卡片区域内
            if not self.ai_card.geometry().contains(global_pos):
                self.ai_card.hide_card()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    manager = CopilotManager()
    
    print("🚀 智能悬浮划词 Copilot 已启动！")
    print("操作提示：")
    print("  1. 在任意地方用鼠标划选一段文字（代码、英文、普通文本均可）。")
    print("  2. 松开鼠标后，MiniMax 悬浮卡片将自动在鼠标旁弹出，并流式输出结果。")
    print("  3. 弹出的卡片支持滚动，并允许选中复制 AI 回复的内容。")
    print("  4. 点击卡片外部任意区域，卡片会自动消失。")
    print("🛑 按 Ctrl+C 在终端中停止，或直接关闭终端。")
    
    sys.exit(app.exec())