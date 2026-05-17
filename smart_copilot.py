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
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QDialog, QRadioButton, QLineEdit, QButtonGroup, QMessageBox, QTabWidget, QComboBox
)
import httpx
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QRect, QPointF, QEvent
from PyQt6.QtGui import QCursor, QColor, QPainter, QPen

from llm_provider import ProviderFactory, load_config, save_config

# ==========================================
# 后台模型探测线程
# ==========================================
class ModelScannerWorker(QThread):
    scan_finished = pyqtSignal(list, str)  # 返回模型列表或错误信息

    def __init__(self, api_base):
        super().__init__()
        self.api_base = api_base.strip().rstrip('/')

    def run(self):
        models = []
        error_msg = ""
        try:
            with httpx.Client(timeout=5.0, verify=False) as client:
                # 策略 1: 尝试标准的 OpenAI 接口 /models
                try:
                    url = f"{self.api_base}/models"
                    response = client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data:
                            models = [m.get("id") for m in data["data"] if "id" in m]
                except Exception as e:
                    pass

                # 策略 2: 如果为空，尝试 Ollama 原生接口 /api/tags
                # 策略 3: 如果还是空，探测类似 OpenClaw Control 这样的 Web 界面
                if not models:
                    try:
                        base_url = self.api_base.replace('/v1', '')
                        response = client.get(base_url)
                        if response.status_code == 200 and "openclaw" in response.text.lower():
                            # 对于这种带有 Web 界面的服务，它的模型名通常在前端或用户手动配置，
                            # 如果我们确认它是 OpenClaw，可以提供一个默认标识提示用户
                            models = ["openclaw-model (自动探测)"]
                    except Exception as e:
                        pass
                
                if not models:
                    try:
                        base_url = self.api_base.replace('/v1', '')
                        url = f"{base_url}/api/tags"
                        response = client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            if "models" in data:
                                models = [m.get("name") for m in data["models"] if "name" in m]
                    except Exception as e:
                        pass
                
                if not models:
                    error_msg = "连接成功，但未扫描到任何模型。请确保第三方智能体已加载模型。"
        except Exception as e:
            error_msg = f"连接失败: {str(e)}\n请检查 API Base URL 是否正确以及服务是否启动。"

        self.scan_finished.emit(models, error_msg)

# ==========================================
# 设置对话框 UI
# ==========================================
class SettingsDialog(QDialog):
    config_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("大模型配置 (LLM Settings)")
        self.setFixedSize(400, 250)
        self.config = load_config()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 引擎选择
        layout.addWidget(QLabel("<b>选择大模型引擎:</b>"))
        self.btn_group = QButtonGroup(self)
        
        self.radio_minimax = QRadioButton("MiniMax (云端)")
        self.radio_local = QRadioButton("第三方智能体 (OpenClaw / Hermes / Ollama等)")
        
        self.btn_group.addButton(self.radio_minimax)
        self.btn_group.addButton(self.radio_local)
        
        layout.addWidget(self.radio_minimax)
        layout.addWidget(self.radio_local)
        
        # 本地配置项
        self.local_config_frame = QFrame()
        local_layout = QVBoxLayout(self.local_config_frame)
        local_layout.setContentsMargins(20, 0, 0, 10)
        
        local_layout.addWidget(QLabel("API Base URL:"))
        
        api_layout = QHBoxLayout()
        self.input_api_base = QLineEdit()
        self.input_api_base.setPlaceholderText("例如: http://localhost:11434/v1")
        self.btn_scan = QPushButton("🔍 探测模型")
        self.btn_scan.clicked.connect(self.start_scan)
        api_layout.addWidget(self.input_api_base)
        api_layout.addWidget(self.btn_scan)
        local_layout.addLayout(api_layout)
        
        local_layout.addWidget(QLabel("Model Name:"))
        self.combo_model = QComboBox()
        self.combo_model.setEditable(True)  # 允许手动输入以防探测不到
        self.combo_model.setPlaceholderText("例如: hermes 或 openclaw")
        local_layout.addWidget(self.combo_model)
        
        layout.addWidget(self.local_config_frame)
        
        # 绑定事件
        self.radio_minimax.toggled.connect(self.update_ui_state)
        self.radio_local.toggled.connect(self.update_ui_state)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存配置")
        self.btn_cancel = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)
        
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.load_current_settings()

    def load_current_settings(self):
        if self.config.get("provider_type") == "local":
            self.radio_local.setChecked(True)
        else:
            self.radio_minimax.setChecked(True)
            
        self.input_api_base.setText(self.config.get("local_api_base", "http://localhost:11434/v1"))
        
        saved_model = self.config.get("local_model", "")
        if saved_model:
            self.combo_model.addItem(saved_model)
            self.combo_model.setCurrentText(saved_model)
            
        self.update_ui_state()

    def start_scan(self):
        api_base = self.input_api_base.text().strip()
        if not api_base:
            QMessageBox.warning(self, "警告", "请先输入 API Base URL")
            return
            
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("探测中...")
        
        self.scanner = ModelScannerWorker(api_base)
        self.scanner.scan_finished.connect(self.on_scan_finished)
        self.scanner.start()

    def on_scan_finished(self, models, error_msg):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 探测模型")
        
        if error_msg:
            QMessageBox.critical(self, "探测失败", error_msg)
        else:
            self.combo_model.clear()
            self.combo_model.addItems(models)
            QMessageBox.information(self, "探测成功", f"成功发现 {len(models)} 个本地模型，请在下拉列表中选择。")

    def update_ui_state(self):
        self.local_config_frame.setEnabled(self.radio_local.isChecked())

    def save_settings(self):
        self.config["provider_type"] = "local" if self.radio_local.isChecked() else "minimax"
        self.config["local_api_base"] = self.input_api_base.text().strip()
        self.config["local_model"] = self.combo_model.currentText().strip()
        
        save_config(self.config)
        self.config_updated.emit()
        self.accept()
        QMessageBox.information(self, "成功", "配置已保存，下一次划词将生效！")

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

    def __init__(self, provider, prompt, action_type="auto"):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.action_type = action_type
        self._is_running = True

    def run(self):
        try:
            if self.action_type == "translate":
                system_prompt = "你是一个金牌翻译官。请将用户提供的文本翻译为中文（如果是中文则翻译为英文）。要求信达雅，只输出翻译结果，不带任何解释和废话。"
            elif self.action_type == "code":
                system_prompt = "你是一个资深架构师。请对用户提供的代码进行深度解析：\n1. 总结这段代码的核心功能。\n2. 指出潜在的漏洞或优化空间。\n要求排版清晰，直接输出解析结果。"
            elif self.action_type == "polish":
                system_prompt = "你是一个资深编辑。请对用户提供的文本进行润色，修正语病，提升表达的专业度和流畅度，使其更具逻辑性。只输出润色后的结果，不解释。"
            else:
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

class ChatWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, provider, messages):
        super().__init__()
        self.provider = provider
        self.messages = messages
        self._is_running = True

    def run(self):
        try:
            full_text = ""
            for chunk in self.provider.stream_chat_with_history(self.messages):
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
        self.chat_worker = None
        self.current_text = ""
        self.chat_history = []  # 存储多轮对话历史
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

        self.resize(400, 300)
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 35, 240);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 100, 100);
            }
        """)
        self.frame.resize(380, 280)
        self.frame.move(10, 10)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(15, 15, 15, 15)

        title_layout = QHBoxLayout()
        self.title_label = QLabel("✨ Smart Copilot", self)
        self.title_label.setStyleSheet("color: #4da6ff; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        
        self.btn_settings = QPushButton("⚙️", self)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #fff;
            }
        """)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.open_settings)
        
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_settings)
        layout.addLayout(title_layout)

        # --- TabWidget ---
        self.tabs = QTabWidget(self.frame)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: rgba(40, 40, 45, 200);
                color: #aaa;
                padding: 6px 12px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: rgba(60, 60, 70, 240);
                color: #fff;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.tabs)

        # ==========================
        # Tab 1: 快捷划词
        # ==========================
        self.tab_quick = QWidget()
        quick_layout = QVBoxLayout(self.tab_quick)
        quick_layout.setContentsMargins(0, 10, 0, 0)
        
        # 快捷指令工具栏
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setContentsMargins(0, 0, 0, 5)
        self.btn_layout.setSpacing(8)
        
        button_style = """
            QPushButton {
                background-color: rgba(60, 60, 70, 200);
                color: #ddd;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 11px;
                border: 1px solid rgba(100, 100, 100, 100);
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 100, 255);
                color: #fff;
                border: 1px solid #4da6ff;
            }
        """
        
        self.btn_auto = QPushButton("✨ 自动")
        self.btn_trans = QPushButton("🌐 翻译")
        self.btn_code = QPushButton("💻 代码解析")
        self.btn_polish = QPushButton("✍️ 润色")
        
        for btn in [self.btn_auto, self.btn_trans, self.btn_code, self.btn_polish]:
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_layout.addWidget(btn)
            
        self.btn_layout.addStretch()
        quick_layout.addLayout(self.btn_layout)
        
        # 绑定点击事件
        self.btn_auto.clicked.connect(lambda: self.trigger_ai("auto"))
        self.btn_trans.clicked.connect(lambda: self.trigger_ai("translate"))
        self.btn_code.clicked.connect(lambda: self.trigger_ai("code"))
        self.btn_polish.clicked.connect(lambda: self.trigger_ai("polish"))

        self.text_edit = QTextEdit(self.tab_quick)
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
        quick_layout.addWidget(self.text_edit)

        # 追问按钮
        ask_more_layout = QHBoxLayout()
        self.btn_ask_more = QPushButton("💬 进一步追问")
        self.btn_ask_more.setStyleSheet(button_style)
        self.btn_ask_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ask_more.clicked.connect(self.jump_to_chat)
        ask_more_layout.addStretch()
        ask_more_layout.addWidget(self.btn_ask_more)
        quick_layout.addLayout(ask_more_layout)

        # ==========================
        # Tab 2: 连续对话
        # ==========================
        self.tab_chat = QWidget()
        chat_layout = QVBoxLayout(self.tab_chat)
        chat_layout.setContentsMargins(0, 10, 0, 0)

        self.chat_display = QTextEdit(self.tab_chat)
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(self.text_edit.styleSheet())
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit(self.tab_chat)
        self.chat_input.setPlaceholderText("输入消息，按 Enter 发送...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 35, 200);
                color: #fff;
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4da6ff;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        self.btn_send = QPushButton("发送", self.tab_chat)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff;
                color: #000;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b3ff;
            }
        """)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_chat_message)

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)

        self.tabs.addTab(self.tab_quick, "⚡️ 快捷划词")
        self.tabs.addTab(self.tab_chat, "💬 连续对话")

    def jump_to_chat(self):
        # 提取当前划词上下文和 AI 回复，并切换到聊天 Tab
        system_msg = "你是一个强大的AI助手，以下是用户刚才划选的内容以及你给出的解释，请基于此继续回答用户的问题。"
        context = f"【用户划选内容】:\n{self.current_text}\n\n【你的初步回答】:\n{self.text_edit.toPlainText()}"
        
        self.chat_history = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "请看看这段内容：\n" + self.current_text},
            {"role": "assistant", "content": self.text_edit.toPlainText()}
        ]
        
        self.chat_display.clear()
        self.append_chat_message("系统", "已将上下文带入，您可以继续追问。")
        self.tabs.setCurrentIndex(1)
        self.chat_input.setFocus()

    def send_chat_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        self.chat_input.clear()
        self.append_chat_message("你", user_text)
        
        if not self.chat_history:
            self.chat_history.append({"role": "system", "content": "你是一个强大的AI助手，请帮助用户解决问题。"})
            
        self.chat_history.append({"role": "user", "content": user_text})
        
        self.append_chat_message("AI", "正在思考...", is_temp=True)
        
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()
            self.chat_worker.wait()

        self.chat_worker = ChatWorker(self.provider, self.chat_history)
        self.chat_worker.text_updated.connect(self.on_chat_updated)
        self.chat_worker.finished_signal.connect(self.on_chat_finished)
        self.chat_worker.start()

    def append_chat_message(self, role, text, is_temp=False):
        color = "#4da6ff" if role == "你" else "#42f554" if role == "AI" else "#aaaaaa"
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        if is_temp:
            self._temp_chat_pos = cursor.position()
            self.chat_display.insertHtml(f'<b style="color:{color};">{role}:</b> {text}<br><br>')
        else:
            self.chat_display.insertHtml(f'<b style="color:{color};">{role}:</b> {text}<br><br>')
            
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_chat_updated(self, text):
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._temp_chat_pos)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 重新插入更新后的文本
        cursor.insertHtml(f'<b style="color:#42f554;">AI:</b> {text}<br><br>')
        
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_chat_finished(self):
        # 记录 AI 最终的完整回复到历史记录
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._temp_chat_pos)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        final_text = cursor.selectedText().replace("AI: ", "").strip()
        
        self.chat_history.append({"role": "assistant", "content": final_text})

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.config_updated.connect(self.reload_provider)
        dialog.exec()

    def reload_provider(self):
        self.provider = ProviderFactory.create_provider()

    def show_card(self, text, x, y):
        self.current_text = text
        # 考虑到高DPI，使用 QCursor.pos() 获得准确逻辑坐标
        pos = QCursor.pos()
        
        # 获取当前鼠标所在的屏幕
        screen = QApplication.screenAt(pos)
        if not screen:
            screen = QApplication.primaryScreen()
        screen_rect = screen.geometry()
        
        card_w = self.width()
        card_h = self.height()
        
        # 默认显示在鼠标右下方
        target_x = pos.x() + 15
        target_y = pos.y() + 15
        
        # 边缘碰撞检测：如果右侧超出屏幕，则翻转显示在鼠标左侧
        if target_x + card_w > screen_rect.right():
            target_x = pos.x() - card_w - 15
            
        # 边缘碰撞检测：如果底部超出屏幕，则翻转显示在鼠标上方
        if target_y + card_h > screen_rect.bottom():
            target_y = pos.y() - card_h - 15
            
        # 终极安全边界保护：确保无论如何卡片都不会超出当前屏幕的可视区域
        target_x = max(screen_rect.left(), min(target_x, screen_rect.right() - card_w))
        target_y = max(screen_rect.top(), min(target_y, screen_rect.bottom() - card_h))
        
        self.move(target_x, target_y)
        self.show()
        self.trigger_ai("auto")

    def trigger_ai(self, action_type):
        if not self.current_text:
            return
            
        self.text_edit.clear()
        self.text_edit.setPlainText("正在思考...\n")
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.worker = AIWorker(self.provider, self.current_text, action_type)
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
        self.provider = ProviderFactory.create_provider()
        
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