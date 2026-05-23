import os
import re
import sys
import traceback
import time
import uuid
import threading
import tempfile
import subprocess
from pynput import mouse

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QDialog,
    QRadioButton, QLineEdit, QMessageBox, QTabWidget, QComboBox
)
import httpx
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QCursor, QColor

from cursor_effects import Ripple, CursorOverlay
from llm_provider import ProviderFactory, load_config, save_config
from markdown_renderer import render as md_render

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
                # 策略 1: 标准 OpenAI 兼容接口 /models
                try:
                    url = f"{self.api_base}/models"
                    response = client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data:
                            models = [m.get("id") for m in data["data"] if "id" in m]
                except Exception:
                    pass

                # 策略 2: Ollama 原生接口 /api/tags
                if not models:
                    try:
                        base_url = self.api_base.replace('/v1', '')
                        url = f"{base_url}/api/tags"
                        response = client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            if "models" in data:
                                models = [m.get("name") for m in data["models"] if "name" in m]
                    except Exception:
                        pass

                if not models:
                    error_msg = "连接成功，但未扫描到任何模型。请确保第三方服务已加载模型。"
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
        self.setWindowTitle("⚙️ ASU 引擎设置")
        self.setMinimumSize(500, 400)
        self.config = load_config()
        self.setup_ui()
        
    def setup_ui(self):
        from PyQt6.QtWidgets import QGroupBox, QStackedWidget, QFormLayout
        layout = QVBoxLayout(self)
        
        # 1. 引擎后端选择 (QButtonGroup)
        type_group = QGroupBox("选择 ASU 定制智能体后端引擎")
        type_layout = QHBoxLayout()
        self.radio_minimax = QRadioButton("云端 LLM (MiniMax)")
        self.radio_custom = QRadioButton("本地/第三方 LLM (Ollama/vLLM)")
        
        type_layout.addWidget(self.radio_minimax)
        type_layout.addWidget(self.radio_custom)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 2. 动态面板 (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        
        # 面板 A: MiniMax
        self.page_minimax = QWidget()
        layout_minimax = QFormLayout(self.page_minimax)
        
        default_minimax_key = self.config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY", "")
        self.input_minimax_key = QLineEdit(default_minimax_key)
        self.input_minimax_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_minimax_key.setPlaceholderText("请输入 MiniMax API Key (若已在 .env 配置可留空)")
        layout_minimax.addRow("API Key:", self.input_minimax_key)
        layout_minimax.addRow(QLabel("默认模型: MiniMax-M2.7"))
        
        # 面板 B: Custom LLM (Ollama 等)
        self.page_custom = QWidget()
        layout_custom = QFormLayout(self.page_custom)
        self.input_custom_base = QLineEdit(self.config.get("local_api_base", "http://localhost:11434/v1"))
        self.input_custom_base.setPlaceholderText("例如: http://localhost:11434/v1")
        self.input_custom_key = QLineEdit(self.config.get("local_api_key", ""))
        self.input_custom_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.input_custom_key.setPlaceholderText("API Key (Ollama可不填)")
        
        custom_probe_layout = QHBoxLayout()
        self.btn_custom_scan = QPushButton("🔍 探测模型")
        self.btn_custom_scan.clicked.connect(self.scan_custom_models)
        self.combo_custom_model = QComboBox()
        self.combo_custom_model.setEditable(True)
        self.combo_custom_model.setCurrentText(self.config.get("local_model", "llama3"))
        custom_probe_layout.addWidget(self.combo_custom_model, stretch=1)
        custom_probe_layout.addWidget(self.btn_custom_scan)
        
        layout_custom.addRow("API Base URL:", self.input_custom_base)
        layout_custom.addRow("API Key (选填):", self.input_custom_key)
        layout_custom.addRow("可用模型:", custom_probe_layout)
        
        # 添加到 StackedWidget
        self.stacked_widget.addWidget(self.page_minimax)
        self.stacked_widget.addWidget(self.page_custom)
        layout.addWidget(self.stacked_widget)
        
        # 3. 底部按钮
        btn_box = QHBoxLayout()
        btn_save = QPushButton("保存并关闭")
        btn_save.clicked.connect(self.save_settings)
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        
        # 信号连接与状态初始化
        self.radio_minimax.toggled.connect(self.update_ui_state)
        self.radio_custom.toggled.connect(self.update_ui_state)
        
        provider_type = self.config.get("provider_type", "minimax")
        if provider_type == "local":
            self.radio_custom.setChecked(True)
        else:
            self.radio_minimax.setChecked(True)
            
        self.update_ui_state()

    def update_ui_state(self):
        if self.radio_minimax.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_minimax)
        elif self.radio_custom.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_custom)

    def scan_custom_models(self):
        self.btn_custom_scan.setEnabled(False)
        self.btn_custom_scan.setText("扫描中...")
        self.scanner = ModelScannerWorker(self.input_custom_base.text().strip())
        self.scanner.scan_finished.connect(self.on_custom_scan_finished)
        self.scanner.start()
        
    def on_custom_scan_finished(self, models, error_msg):
        self.btn_custom_scan.setEnabled(True)
        self.btn_custom_scan.setText("🔍 探测模型")
        if error_msg:
            QMessageBox.critical(self, "探测失败", error_msg)
        else:
            self.combo_custom_model.clear()
            self.combo_custom_model.addItems(models)
            QMessageBox.information(self, "探测成功", "已更新本地 LLM 列表。")
            
    def save_settings(self):
        if self.radio_minimax.isChecked():
            provider_type = "minimax"
        else:
            provider_type = "local"
            
        self.config["provider_type"] = provider_type
        self.config["minimax_api_key"] = self.input_minimax_key.text().strip()
        self.config["local_api_base"] = self.input_custom_base.text().strip()
        self.config["local_model"] = self.combo_custom_model.currentText().strip()
        self.config["local_api_key"] = self.input_custom_key.text().strip()
        
        save_config(self.config)
        self.config_updated.emit()
        self.accept()
        QMessageBox.information(self, "成功", "配置已保存，下一次划词将生效！")

# ==========================================
# 1. 后台大模型请求线程 (避免阻塞UI)
# ==========================================
class AIWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, provider, prompt, action_type="auto", session_id="default",
                 context_source="drag", context_meta=None):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.action_type = action_type
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self._is_running = True

    def run(self):
        try:
            full_text = ""
            for chunk in self.provider.stream_agent_task(
                self.prompt, action_type=self.action_type,
                session_id=self.session_id, is_new_task=True,
                context_source=self.context_source,
                context_meta=self.context_meta
            ):
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

    def __init__(self, provider, text, session_id="default",
                 context_source="chat", context_meta=None):
        super().__init__()
        self.provider = provider
        self.text = text
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self._is_running = True

    def run(self):
        try:
            full_text = ""
            for chunk in self.provider.stream_agent_task(
                self.text, action_type="chat", session_id=self.session_id,
                is_new_task=False, context_source=self.context_source,
                context_meta=self.context_meta
            ):
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


class BrowserReaderWorker(QThread):
    """后台线程：执行 AppleScript 读取浏览器 DOM，避免阻塞 UI。"""
    finished = pyqtSignal(str, str)   # browser_name, text (empty on error)
    error = pyqtSignal(str)           # error message

    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    def run(self):
        # 构建 AppleScript
        if self.browser in ["Google Chrome", "Brave Browser", "Microsoft Edge", "Arc"]:
            script = f'''
            tell application "{self.browser}"
                execute front window's active tab javascript "document.body.innerText;"
            end tell
            '''
        elif self.browser == "Safari":
            script = '''
            tell application "Safari"
                do JavaScript "document.body.innerText;" in document 1
            end tell
            '''
        else:
            self.error.emit(f"浏览器 {self.browser} 不支持一键读取。")
            return

        try:
            text = subprocess.check_output(
                ['osascript', '-e', script], stderr=subprocess.STDOUT, timeout=10
            ).decode('utf-8').strip()
            self.finished.emit(self.browser, text)
        except subprocess.CalledProcessError as e:
            err = e.output.decode('utf-8')
            if "JavaScript" in err or "Apple Events" in err:
                self.error.emit(
                    f"❌ 读取失败：缺少权限。\n\n"
                    f"请在 {self.browser} 的菜单中启用：\n"
                    f"「允许来自 Apple 事件的 JavaScript (Allow JavaScript from Apple Events)」"
                )
            else:
                self.error.emit(f"❌ 跨进程执行失败: {err}")
        except subprocess.TimeoutExpired:
            self.error.emit(f"❌ 读取超时，{self.browser} 可能未响应。")
        except Exception as e:
            self.error.emit(f"❌ 读取过程中发生未知错误: {e}")


# ==========================================
# 2. 鼠标监听线程（双击 + 三击右键）
# ==========================================
class MouseListenerWorker(QThread):
    mouse_moved = pyqtSignal(int, int)
    global_click = pyqtSignal(int, int)
    right_clicked = pyqtSignal(int, int, int)  # x, y, click_count

    def __init__(self):
        super().__init__()
        self.last_right_click_time = 0
        self.click_threshold = 0.4  # 400ms
        self._right_click_count = 0

    def run(self):
        def on_move(x, y):
            self.mouse_moved.emit(int(x), int(y))
            
        def on_click(x, y, button, pressed):
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

        with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
            listener.join()


# ==========================================
# 3. 智能悬浮卡片 (独立图层，可交互)
# ==========================================
class AICardWindow(QWidget):
    ide_probe_result = pyqtSignal(bool)
    browser_probe_result = pyqtSignal(str)

    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.worker = None
        self.chat_worker = None
        self.current_text = ""
        self.chat_history = []
        self.session_id = str(uuid.uuid4())
        self.active_browser = None
        self._temp_chat_pos = 0
        self._pending_hide = False
        # 上下文感知
        self.context_source = "drag"
        self.context_meta = {}
        self.task_context = ""  # 工作台注入的任务上下文
        self.initUI()

    def initUI(self):
        # 无边框、置顶、绕过窗口管理器、不抢夺焦点
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)  # 启用鼠标追踪，用于拖拽缩放
        self._resize_margin = 14
        self._resizing = False
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None

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
        
        # IDE 插件探测状态栏
        self.ide_status_layout = QHBoxLayout()
        self.ide_status_layout.setContentsMargins(0, 0, 0, 5)
        self.btn_read_ide = QPushButton("📥 极速读取当前 IDE 全文")
        self.btn_read_ide.setStyleSheet("""
            QPushButton {
                background-color: rgba(77, 166, 255, 180);
                color: #fff;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(77, 166, 255, 255);
            }
            QPushButton:hover {
                background-color: rgba(77, 166, 255, 255);
            }
        """)
        self.btn_read_ide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_read_ide.clicked.connect(self.read_from_ide_extension)
        self.btn_read_ide.hide() # 默认隐藏，探测到才显示
        self.ide_probe_result.connect(self._update_ide_btn)
        
        self.ide_status_layout.addWidget(self.btn_read_ide)
        self.ide_status_layout.addStretch()
        quick_layout.addLayout(self.ide_status_layout)

        # 浏览器探测状态栏
        self.browser_status_layout = QHBoxLayout()
        self.browser_status_layout.setContentsMargins(0, 0, 0, 5)
        self.btn_read_browser = QPushButton("🌐 一键读取当前网页全文")
        self.btn_read_browser.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 140, 0, 180);
                color: #fff;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255, 140, 0, 255);
            }
            QPushButton:hover {
                background-color: rgba(255, 140, 0, 255);
            }
        """)
        self.btn_read_browser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_read_browser.clicked.connect(self.read_from_browser)
        self.btn_read_browser.hide() # 默认隐藏
        self.browser_probe_result.connect(self._update_browser_btn)
        
        self.browser_status_layout.addWidget(self.btn_read_browser)
        self.browser_status_layout.addStretch()
        quick_layout.addLayout(self.browser_status_layout)

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
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_display.setStyleSheet(self.text_edit.styleSheet())
        chat_layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit(self.tab_chat)
        self.chat_input.setPlaceholderText("输入消息，按 Enter 发送...")
        self.chat_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
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
        self.tabs.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def jump_to_chat(self):
        # 切换到聊天 Tab，不再手动发送历史记录，因为后端 Agent 已有记忆
        self.chat_display.clear()
        self.append_chat_message("系统", "已将上下文带入，您可以继续追问。")
        self.tabs.setCurrentIndex(1)
        self.chat_input.setFocus()

    def _get_ide_port(self):
        """从临时文件读取当前激活的 IDE 插件端口"""
        port_file = os.path.join(tempfile.gettempdir(), 'asu_ide_port.txt')
        if os.path.exists(port_file):
            try:
                with open(port_file, 'r') as f:
                    port = f.read().strip()
                    if port.isdigit():
                        return port
            except Exception:
                print(f"[ASU] 读取 IDE 端口文件失败: {traceback.format_exc()}")
        return None

    def read_from_ide_extension(self):
        port = self._get_ide_port()
        if not port:
            self.text_edit.setPlainText("❌ 无法找到 IDE 插件端口信息，请确认已在当前 VSCode/Trae 窗口中激活了插件。")
            return
            
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/context", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                filename = data.get("fileName", "Unknown")
                if content:
                    self.current_text = content
                    self.context_source = "ide"
                    self.context_meta = {
                        "file_name": data.get("fileName", "Unknown"),
                        "language": data.get("languageId", ""),
                    }
                    self.text_edit.clear()
                    self.text_edit.setPlainText(f"✅ 已成功从 IDE 插件读取全文 [{filename}]\n\n文件大小: {len(content)} 字符\n\n请点击下方快捷指令进行分析。")
                    self.tabs.setCurrentIndex(0)
                    self.btn_read_ide.setText("✅ 已读取全文")
                    self.btn_read_ide.setStyleSheet(self.btn_read_ide.styleSheet().replace("rgba(77, 166, 255, 180)", "rgba(40, 167, 69, 180)").replace("rgba(77, 166, 255, 255)", "rgba(40, 167, 69, 255)"))
                else:
                    self.text_edit.setPlainText("❌ 从 IDE 读取的文件内容为空")
            else:
                self.text_edit.setPlainText(f"❌ 读取失败，插件返回状态码: {response.status_code}")
        except Exception as e:
            self.text_edit.setPlainText(f"❌ 无法连接到 IDE 伴生插件，请确认已在 VSCode/Trae 中安装并激活插件。\n\n错误信息: {e}")

    def send_chat_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        self.chat_input.clear()
        self.append_chat_message("你", user_text)
        
        self.append_chat_message("AI", "正在思考...", is_temp=True)
        
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()
            self.chat_worker.wait()

        # 合并工作台任务上下文
        meta = dict(self.context_meta)
        if self.task_context:
            meta["task"] = self.task_context
        self.chat_worker = ChatWorker(self.provider, user_text, self.session_id,
                                      self.context_source, meta)
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
        cursor.insertHtml(md_render(text))
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_chat_finished(self):
        pass

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.config_updated.connect(self.reload_provider)
        dialog.exec()

    def reload_provider(self):
        self.provider = ProviderFactory.create_provider()

    def dragEnterEvent(self, event):
        # 有拖拽进入卡片，取消任何待执行的延迟隐藏
        self._pending_hide = False
        if event.mimeData().hasText():
            event.acceptProposedAction()

    # ---- 拖拽缩放支持 ----
    def _get_resize_edge(self, pos):
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        b, r = y > h - m, x > w - m
        t, l = y < m, x < m
        if b and r: return 'br'
        if b and l: return 'bl'
        if t and r: return 'tr'
        if t and l: return 'tl'
        if b: return 'b'
        if r: return 'r'
        if t: return 't'
        if l: return 'l'
        return None

    _EDGE_CURSORS = {
        'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
        't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor,
        'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
        'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                QApplication.setOverrideCursor(self._EDGE_CURSORS[edge])
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = self._resize_start_geo
            e = self._resize_edge
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            min_w, min_h = 300, 200

            if 'r' in e: w = max(min_w, g.width() + delta.x())
            if 'l' in e: x = g.x() + delta.x(); w = max(min_w, g.width() - delta.x())
            if 'b' in e: h = max(min_h, g.height() + delta.y())
            if 't' in e: y = g.y() + delta.y(); h = max(min_h, g.height() - delta.y())
            self.setGeometry(x, y, w, h)
            self.frame.resize(w - 20, h - 22)
            return

        edge = self._get_resize_edge(event.pos())
        if edge:
            self.setCursor(self._EDGE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            QApplication.restoreOverrideCursor()
            self._resizing = False
            self._resize_edge = None
        super().mouseReleaseEvent(event)
    # ---- 缩放支持结束 ----

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text:
            self.current_text = text
            self.context_source = "drag"
            self.context_meta = {}
            self.tabs.setCurrentIndex(0)
            self.trigger_ai("auto")

    def show_card(self, x, y):
        self.current_text = ""
        self.context_source = "drag"
        self.context_meta = {}
        self.session_id = str(uuid.uuid4())
        
        self.text_edit.clear()
        self.text_edit.setPlainText("🎯 请将划选的文本拖拽到此窗口中...")
        self.tabs.setCurrentIndex(0)
        
        # 重置 IDE 按钮状态
        self.btn_read_ide.setText("📥 极速读取当前 IDE 全文")
        self.btn_read_ide.setStyleSheet("""
            QPushButton {
                background-color: rgba(77, 166, 255, 180);
                color: #fff;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(77, 166, 255, 255);
            }
            QPushButton:hover {
                background-color: rgba(77, 166, 255, 255);
            }
        """)

        # 重置浏览器按钮状态
        self.btn_read_browser.setText("🌐 一键读取当前网页全文")
        self.btn_read_browser.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 140, 0, 180);
                color: #fff;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(255, 140, 0, 255);
            }
            QPushButton:hover {
                background-color: rgba(255, 140, 0, 255);
            }
        """)

        # 异步探测
        threading.Thread(target=self._probe_ide_extension, daemon=True).start()
        threading.Thread(target=self._probe_browser, daemon=True).start()

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

    def _probe_browser(self):
        try:
            # 使用 AppleScript 获取当前处于激活状态的应用程序名称
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            front_app = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            
            supported_browsers = ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"]
            if front_app in supported_browsers:
                self.browser_probe_result.emit(front_app)
            else:
                self.browser_probe_result.emit("")
        except Exception:
            print(f"[ASU] 浏览器探测失败: {traceback.format_exc()}")
            self.browser_probe_result.emit("")

    def _probe_ide_extension(self):
        port = self._get_ide_port()
        if not port:
            self.ide_probe_result.emit(False)
            return
            
        try:
            # 使用 GET 请求进行探活
            response = httpx.get(f"http://127.0.0.1:{port}/context", timeout=0.3)
            # 只要能连上（不管是不是404没打开文件），都说明插件在运行
            if response.status_code in [200, 404]:
                self.ide_probe_result.emit(True)
                return
        except Exception:
            print(f"[ASU] IDE 插件探测失败: {traceback.format_exc()}")
        self.ide_probe_result.emit(False)

    def _update_ide_btn(self, is_active):
        if is_active:
            self.btn_read_ide.show()
        else:
            self.btn_read_ide.hide()

    def _update_browser_btn(self, browser_name):
        if browser_name:
            self.active_browser = browser_name
            self.btn_read_browser.setText(f"🌐 一键读取当前网页 ({browser_name})")
            self.btn_read_browser.show()
        else:
            self.active_browser = None
            self.btn_read_browser.hide()

    def read_from_browser(self):
        if not self.active_browser:
            return

        browser = self.active_browser
        self.btn_read_browser.setEnabled(False)
        self.btn_read_browser.setText("⏳ 读取中...")
        self.text_edit.setPlainText(f"正在从 {browser} 读取网页内容...")

        self._browser_worker = BrowserReaderWorker(browser)
        self._browser_worker.finished.connect(self._on_browser_text_ready)
        self._browser_worker.error.connect(self._on_browser_error)
        self._browser_worker.start()

    def _on_browser_text_ready(self, browser, text):
        self.btn_read_browser.setEnabled(True)
        if text:
            self.current_text = text
            self.context_source = "browser"
            self.context_meta = {"app_name": browser}
            self.text_edit.clear()
            self.text_edit.setPlainText(f"✅ 已成功从 {browser} 读取网页全文\n\n网页大小: {len(text)} 字符\n\n请点击下方快捷指令进行分析。")
            self.tabs.setCurrentIndex(0)
            self.btn_read_browser.setText("✅ 已读取全文")
            self.btn_read_browser.setStyleSheet(self.btn_read_browser.styleSheet().replace("rgba(255, 140, 0, 180)", "rgba(40, 167, 69, 180)").replace("rgba(255, 140, 0, 255)", "rgba(40, 167, 69, 255)"))
        else:
            self.text_edit.setPlainText(f"❌ 从 {browser} 读取的内容为空。")
            self.btn_read_browser.setText("🌐 一键读取当前网页全文")

    def _on_browser_error(self, err_msg):
        self.btn_read_browser.setEnabled(True)
        self.text_edit.setPlainText(err_msg)
        self.btn_read_browser.setText("🌐 一键读取当前网页全文")

    def trigger_ai(self, action_type):
        if not self.current_text:
            return
            
        self.text_edit.clear()
        self.text_edit.setPlainText("正在思考...\n")
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        # 合并工作台任务上下文到来源上下文中
        meta = dict(self.context_meta)
        if self.task_context:
            meta["task"] = self.task_context
        self.worker = AIWorker(self.provider, self.current_text, action_type,
                               self.session_id, self.context_source, meta)
        self.worker.text_updated.connect(self.on_text_updated)
        self.worker.start()

    def on_text_updated(self, text):
        if not text:
            self.text_edit.setPlainText("正在思考...\n")
        else:
            self.text_edit.setHtml(md_render(text))
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _delayed_hide(self):
        """延迟隐藏：如果 _pending_hide 仍为 True（无拖拽进入），则隐藏卡片。"""
        if self._pending_hide:
            self.hide()
            if self.worker and self.worker.isRunning():
                self.worker.stop()
        self._pending_hide = False

    def hide_card(self):
        self._pending_hide = False
        self.hide()
        if self.worker and self.worker.isRunning():
            self.worker.stop()


# ==========================================
# 4. 任务工作台 (三击右键唤出)
# ==========================================
class AgentWorkspace(QWidget):
    """独立智能体工作台 —— 三连击右键唤出。

    用于：定义任务背景、独立对话、全局设置。
    设定的任务上下文会自动注入到双击右键快捷卡片的 AI 请求中。
    """
    task_changed = pyqtSignal(str)  # 任务变更时通知 CopilotManager

    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.chat_worker = None
        self.current_task = ""
        self.session_id = str(uuid.uuid4())
        self._temp_chat_pos = 0
        self._pending_hide = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._resize_margin = 14
        self._resizing = False
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None
        self.resize(520, 480)

        # 外层 Frame
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 25, 32, 245);
                border-radius: 14px;
                border: 1.5px solid rgba(77, 166, 255, 80);
            }
        """)
        self.frame.resize(500, 460)
        self.frame.move(10, 10)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # --- 标题栏 ---
        title_layout = QHBoxLayout()
        self.title_label = QLabel("🧠 ASU Agent Workspace")
        self.title_label.setStyleSheet(
            "color: #4da6ff; font-weight: bold; font-size: 14px; background: transparent; border: none;"
        )

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; }
            QPushButton:hover { color: #fff; }
        """)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self._open_settings)

        self.btn_close = QPushButton("✕")
        self.btn_close.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; color: #888; }
            QPushButton:hover { color: #ff5555; }
        """)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide_workspace)

        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_settings)
        title_layout.addWidget(self.btn_close)
        layout.addLayout(title_layout)

        # --- 任务定义区 ---
        task_label = QLabel("📋 当前任务（注入到所有划词请求中）")
        task_label.setStyleSheet("color: #aaa; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(task_label)

        task_input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("例：我正在审查支付模块的安全漏洞...")
        self.task_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(40, 40, 50, 200);
                color: #eee; border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 6px; padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """)
        self.task_input.returnPressed.connect(self._save_task)

        self.btn_save_task = QPushButton("设定")
        self.btn_save_task.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #66b3ff; }
        """)
        self.btn_save_task.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_task.clicked.connect(self._save_task)

        task_input_layout.addWidget(self.task_input, stretch=1)
        task_input_layout.addWidget(self.btn_save_task)
        layout.addLayout(task_input_layout)

        # 当前任务状态标签
        self.task_status = QLabel("")
        self.task_status.setStyleSheet(
            "color: #42f554; font-size: 11px; background: transparent; border: none;"
        )
        self.task_status.hide()
        layout.addWidget(self.task_status)

        # --- 对话区 ---
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: transparent; color: #eee; font-size: 13px;
                border: none; line-height: 1.5;
            }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,40); border-radius: 3px; }
        """)
        layout.addWidget(self.chat_display, stretch=1)

        # --- 输入栏 ---
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入消息，按 Enter 发送...")
        self.chat_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(40, 40, 50, 200); color: #fff;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 6px; padding: 6px 10px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #4da6ff; }
        """)
        self.chat_input.returnPressed.connect(self._send_message)

        self.btn_send = QPushButton("发送")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #4da6ff; color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #66b3ff; }
        """)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._send_message)

        input_layout.addWidget(self.chat_input, stretch=1)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

    def _save_task(self):
        task = self.task_input.text().strip()
        self.current_task = task
        if task:
            self.task_status.setText(f"✅ 激活任务: {task}")
            self.task_status.show()
            self.task_changed.emit(task)
            self._append_message("系统", f"任务已设定: {task}")
        else:
            self.task_status.hide()
            self.task_changed.emit("")
            self._append_message("系统", "任务已清除。")

    def _send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self._append_message("你", text)
        self._append_message("AI", "思考中...", is_temp=True)

        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()
            self.chat_worker.wait()

        # 聊天模式，带当前任务上下文
        meta = {"task": self.current_task} if self.current_task else {}
        self.chat_worker = ChatWorker(
            self.provider, text, self.session_id,
            context_source="chat", context_meta=meta
        )
        self.chat_worker.text_updated.connect(self._on_chat_update)
        self.chat_worker.finished_signal.connect(lambda: None)
        self.chat_worker.start()

    def _append_message(self, role, text, is_temp=False):
        color = "#4da6ff" if role == "你" else "#42f554" if role == "AI" else "#aaaaaa"
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

        if is_temp:
            self._temp_chat_pos = cursor.position()

        self.chat_display.insertHtml(
            f'<b style="color:{color};">{role}:</b> {text}<br><br>'
        )
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_chat_update(self, text):
        cursor = self.chat_display.textCursor()
        cursor.setPosition(self._temp_chat_pos)
        cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(md_render(text))
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _open_settings(self):
        from PyQt6.QtWidgets import QDialog as QDlg
        dialog = SettingsDialog(self)
        dialog.config_updated.connect(self._reload_provider)
        dialog.exec()

    def _reload_provider(self):
        self.provider = ProviderFactory.create_provider()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text:
            self.task_input.setText(text)
            self._save_task()

    # ---- 拖拽缩放支持 ----
    def _get_resize_edge(self, pos):
        m = self._resize_margin
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        b, r = y > h - m, x > w - m
        t, l = y < m, x < m
        if b and r: return 'br'
        if b and l: return 'bl'
        if t and r: return 'tr'
        if t and l: return 'tl'
        if b: return 'b'
        if r: return 'r'
        if t: return 't'
        if l: return 'l'
        return None

    _EDGE_CURSORS = {
        'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
        't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor,
        'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
        'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
    }

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True; self._resize_edge = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                QApplication.setOverrideCursor(self._EDGE_CURSORS[edge])
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = self._resize_start_geo; e = self._resize_edge
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            min_w, min_h = 380, 300
            if 'r' in e: w = max(min_w, g.width() + delta.x())
            if 'l' in e: x = g.x() + delta.x(); w = max(min_w, g.width() - delta.x())
            if 'b' in e: h = max(min_h, g.height() + delta.y())
            if 't' in e: y = g.y() + delta.y(); h = max(min_h, g.height() - delta.y())
            self.setGeometry(x, y, w, h)
            self.frame.resize(w - 20, h - 22)
            return
        edge = self._get_resize_edge(event.pos())
        self.setCursor(self._EDGE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            QApplication.restoreOverrideCursor()
            self._resizing = False; self._resize_edge = None
        super().mouseReleaseEvent(event)

    def show_workspace(self, x, y):
        self.session_id = str(uuid.uuid4())
        self.chat_display.clear()
        if self.current_task:
            self._append_message("系统", f"当前任务: {self.current_task}")

        pos = QCursor.pos()
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        sr = screen.geometry()
        w, h = self.width(), self.height()

        tx = pos.x() + 20
        ty = pos.y() + 20
        if tx + w > sr.right():
            tx = pos.x() - w - 20
        if ty + h > sr.bottom():
            ty = pos.y() - h - 20
        tx = max(sr.left(), min(tx, sr.right() - w))
        ty = max(sr.top(), min(ty, sr.bottom() - h))

        self.move(tx, ty)
        self.show()
        self.chat_input.setFocus()

    def hide_workspace(self):
        self._pending_hide = False
        self.hide()
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.stop()

    def _delayed_hide(self):
        if self._pending_hide:
            self.hide_workspace()
        self._pending_hide = False


# ==========================================
# 5. 总调度管理器与生命周期管理
# ==========================================
class CopilotManager:
    def __init__(self):
        self.agent_process = None
        self._check_and_start_agent()
        
        self.provider = ProviderFactory.create_provider()
        
        # 三个独立图层：
        # 1. 光标特效图层（全屏、鼠标穿透）
        self.cursor_overlay = CursorOverlay()
        # 2. 智能卡片图层（双击右键，快捷交互）
        self.ai_card = AICardWindow(self.provider)
        # 3. 任务工作台图层（三击右键，任务定义 + 独立对话）
        self.workspace = AgentWorkspace(self.provider)
        
        # 三击 vs 双击仲裁状态
        self._pending_clicks = 0
        self._pending_click_x = 0
        self._pending_click_y = 0
        self._click_resolve_timer = None

        # 启动鼠标监听
        self.mouse_thread = MouseListenerWorker()
        self.mouse_thread.mouse_moved.connect(self.cursor_overlay.update_cursor_position)
        self.mouse_thread.right_clicked.connect(self._on_right_clicked)
        self.mouse_thread.global_click.connect(self._on_global_click)
        self.mouse_thread.start()
        
        # 任务上下文同步：工作台任务 → 快捷卡片
        self.workspace.task_changed.connect(self._sync_task_context)

    def _sync_task_context(self, task):
        """工作台设定的任务合并到快捷卡片（不覆盖 IDE/浏览器来源信息）。"""
        if task:
            self.ai_card.task_context = task
        else:
            self.ai_card.task_context = ""

    def _on_right_clicked(self, x, y, count):
        """右键点击仲裁：用 QTimer 区分双击 vs 三击。"""
        self._pending_clicks = count
        self._pending_click_x = x
        self._pending_click_y = y

        if count == 2:
            # 可能是双击，但也可能是三击的中间状态，延迟判决
            if self._click_resolve_timer is None:
                self._click_resolve_timer = QTimer()
                self._click_resolve_timer.setSingleShot(True)
                self._click_resolve_timer.timeout.connect(self._resolve_right_clicks)
            self._click_resolve_timer.start(400)  # 等待 400ms 看有没有第三次点击
        elif count >= 3:
            # 三击确认，立即执行
            if self._click_resolve_timer:
                self._click_resolve_timer.stop()
            self._resolve_right_clicks()

    def _resolve_right_clicks(self):
        """根据最终点击次数决定行为。"""
        clicks = self._pending_clicks
        self._pending_clicks = 0

        if clicks == 2:
            self._on_double_right_click(self._pending_click_x, self._pending_click_y)
        elif clicks >= 3:
            self._on_triple_right_click(self._pending_click_x, self._pending_click_y)

    def _on_double_right_click(self, x, y):
        pos = QCursor.pos()
        self.ai_card.show_card(pos.x(), pos.y())

    def _on_triple_right_click(self, x, y):
        pos = QCursor.pos()
        self.workspace.show_workspace(pos.x(), pos.y())

    def _on_global_click(self, x, y):
        self.cursor_overlay.add_ripple(x, y)
        # 快捷卡片：点击外部延迟隐藏
        if self.ai_card.isVisible():
            global_pos = QCursor.pos()
            if not self.ai_card.geometry().contains(global_pos):
                self.ai_card._pending_hide = True
                QTimer.singleShot(300, self.ai_card._delayed_hide)
        # 工作台：点击外部延迟隐藏
        if self.workspace.isVisible():
            global_pos = QCursor.pos()
            if not self.workspace.geometry().contains(global_pos):
                self.workspace._pending_hide = True
                QTimer.singleShot(300, self.workspace._delayed_hide)

    def cleanup(self):
        if self.agent_process:
            print("[ASU Agent] 正在关闭后台服务...")
            self.agent_process.terminate()
            self.agent_process.wait(timeout=3)
        self.mouse_thread.quit()

    def _check_and_start_agent(self):
        # 使用健康检查端点检测 Agent 是否存活
        try:
            resp = httpx.get("http://127.0.0.1:18888/health", timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                print(f"[ASU Agent] 服务端已在 18888 端口运行 (活跃会话: {data.get('active_sessions', 0)})")
                return
        except Exception:
            # Agent 未运行，继续启动流程
            pass

        print("[ASU Agent] 18888 端口未占用，正在启动 ASU 定制智能体...")
        try:
            agent_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asu_custom_agent.py")
            self.agent_process = subprocess.Popen(
                [sys.executable, agent_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1)
        except Exception as e:
            print(f"[ASU Agent] 启动失败: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    manager = CopilotManager()
    
    print("🚀 ASU Smart Copilot 已启动！")
    print("操作提示：")
    print("  ┌─ 双击右键 → 快捷悬浮卡片（翻译/解释/润色）")
    print("  ├─ 三击右键 → 任务工作台（设定任务 + 独立对话）")
    print("  ├─ 拖拽文本到卡片 → 自动 AI 解析")
    print("  ├─ 点击卡片外部 → 300ms 后自动消失")
    print("  └─ 工作台设定的任务会自动注入到快捷卡片中")
    print("🛑 按 Ctrl+C 停止。")
    
    ret = app.exec()
    manager.cleanup()
    sys.exit(ret)