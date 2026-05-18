import sys
import threading
import time
import platform
import subprocess
import re
from collections import deque
from pynput import mouse, keyboard

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
        # 如果用户选择探测 OpenClaw CLI，直接通过命令行获取 agents
        if "openclaw" in self.api_base.lower() or "cli" in self.api_base.lower() or not self.api_base.startswith("http"):
            try:
                import subprocess
                import json
                import re
                result = subprocess.run(["openclaw", "agents", "list", "--json"], capture_output=True, text=True)
                output = result.stdout
                
                # 使用正则精确提取 JSON 数组，避免被前后的日志干扰
                match = re.search(r"\[\s*\{.*?\}\s*\]", output, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    models = [agent.get("name", agent.get("id")) for agent in data if "id" in agent]
                    self.api_base = "openclaw-cli" # 更新标志
                    self.scan_finished.emit(models, "")
                    return
            except Exception as e:
                print(f"OpenClaw CLI probe failed: {e}")
                pass # 回退到普通的 HTTP 探测
                
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
                            # 如果识别出是 18789 面板端口，自动推导底层的 18791 API 端口
                            if ":18789" in base_url:
                                self.api_base = base_url.replace(":18789", ":18791")
                            models = ["openclaw-agent (网关模式)"]
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

        self.scan_finished.emit(models, error_msg)  # emit signal

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
        
        # 1. 引擎类型选择 (QButtonGroup)
        type_group = QGroupBox("选择 AI 引擎类型")
        type_layout = QHBoxLayout()
        self.radio_minimax = QRadioButton("云端 LLM (MiniMax)")
        self.radio_custom = QRadioButton("本地/第三方 LLM (Ollama/vLLM)")
        self.radio_agent = QRadioButton("本地智能体 (OpenClaw Agent)")
        
        type_layout.addWidget(self.radio_minimax)
        type_layout.addWidget(self.radio_custom)
        type_layout.addWidget(self.radio_agent)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 2. 动态面板 (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        
        # 面板 A: MiniMax
        self.page_minimax = QWidget()
        layout_minimax = QFormLayout(self.page_minimax)
        
        import os
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
        
        # 面板 C: OpenClaw Agent
        self.page_agent = QWidget()
        layout_agent = QFormLayout(self.page_agent)
        layout_agent.addRow(QLabel("说明: 将通过系统原生 openclaw CLI 调度智能体，无需配置端口。"))
        
        agent_probe_layout = QHBoxLayout()
        self.btn_agent_scan = QPushButton("🔍 获取本机智能体")
        self.btn_agent_scan.clicked.connect(self.scan_agents)
        self.combo_agent_name = QComboBox()
        self.combo_agent_name.setEditable(True)
        self.combo_agent_name.setCurrentText(self.config.get("agent_name", "main"))
        agent_probe_layout.addWidget(self.combo_agent_name, stretch=1)
        agent_probe_layout.addWidget(self.btn_agent_scan)
        
        layout_agent.addRow("目标 Agent:", agent_probe_layout)
        
        # 添加到 StackedWidget
        self.stacked_widget.addWidget(self.page_minimax)
        self.stacked_widget.addWidget(self.page_custom)
        self.stacked_widget.addWidget(self.page_agent)
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
        self.radio_agent.toggled.connect(self.update_ui_state)
        
        provider_type = self.config.get("provider_type", "minimax")
        if provider_type == "local":
            self.radio_custom.setChecked(True)
        elif provider_type == "openclaw":
            self.radio_agent.setChecked(True)
        else:
            self.radio_minimax.setChecked(True)
            
        self.update_ui_state()

    def update_ui_state(self):
        if self.radio_minimax.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_minimax)
        elif self.radio_custom.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_custom)
        elif self.radio_agent.isChecked():
            self.stacked_widget.setCurrentWidget(self.page_agent)

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
            if ":18791" in self.scanner.api_base or "openclaw-cli" in self.scanner.api_base:
                self.input_custom_base.setText(self.scanner.api_base)
            self.combo_custom_model.clear()
            self.combo_custom_model.addItems(models)
            QMessageBox.information(self, "探测成功", "已更新本地 LLM 列表。")
            
    def scan_agents(self):
        self.btn_agent_scan.setEnabled(False)
        self.btn_agent_scan.setText("扫描中...")
        self.scanner = ModelScannerWorker("openclaw-cli")
        self.scanner.scan_finished.connect(self.on_agent_scan_finished)
        self.scanner.start()
        
    def on_agent_scan_finished(self, models, error_msg):
        self.btn_agent_scan.setEnabled(True)
        self.btn_agent_scan.setText("🔍 获取本机智能体")
        if error_msg:
            QMessageBox.critical(self, "获取失败", error_msg)
        else:
            self.combo_agent_name.clear()
            self.combo_agent_name.addItems(models)
            QMessageBox.information(self, "获取成功", "已更新 OpenClaw 智能体列表。")

    def save_settings(self):
        if self.radio_minimax.isChecked():
            provider_type = "minimax"
        elif self.radio_custom.isChecked():
            provider_type = "local"
        else:
            provider_type = "openclaw"
            
        self.config["provider_type"] = provider_type
        self.config["minimax_api_key"] = self.input_minimax_key.text().strip()
        self.config["local_api_base"] = self.input_custom_base.text().strip()
        self.config["local_model"] = self.combo_custom_model.currentText().strip()
        self.config["local_api_key"] = self.input_custom_key.text().strip()
        self.config["agent_name"] = self.combo_agent_name.currentText().strip()
        
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
    mouse_moved = pyqtSignal(int, int)
    text_selected = pyqtSignal(str)
    global_click = pyqtSignal(int, int)
    capture_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_dragging = False
        self.drag_start = None
        self.old_clipboard = self._get_clipboard()
        self.is_mac = platform.system() == 'Darwin'
        self.keyboard_controller = keyboard.Controller()
        # Connect the signal to the slot (this executes in the thread that created the QThread, i.e., main thread)
        self.capture_requested.connect(self.execute_capture)

    def _get_clipboard(self):
        try:
            if platform.system() == 'Darwin':
                return subprocess.check_output(['pbpaste'], text=True)
            else:
                # Add Windows/Linux clipboard command if needed in future
                return ""
        except Exception:
            return ""

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
                                # Safe: emits signal to be handled in main GUI thread
                                self.capture_requested.emit()

        with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
            listener.join()

    def execute_capture(self):
        # This now runs in the main GUI thread!
        QTimer.singleShot(200, self._do_hotkey_and_read)

    def _do_hotkey_and_read(self):
        try:
            if self.is_mac:
                with self.keyboard_controller.pressed(keyboard.Key.cmd):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
            else:
                with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
            # Wait for clipboard to update
            QTimer.singleShot(200, self._read_clipboard)
        except Exception as e:
            print(f"划词快捷键捕获失败: {e}")

    def _read_clipboard(self):
        try:
            new_clipboard = self._get_clipboard()
            if new_clipboard and new_clipboard != self.old_clipboard:
                self.old_clipboard = new_clipboard
                self.text_selected.emit(new_clipboard)
        except Exception as e:
            print(f"读取剪贴板失败: {e}")

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
# 5. 总调度管理器与生命周期管理
# ==========================================
class CopilotManager:
    def __init__(self):
        self.openclaw_process = None
        self._check_and_start_openclaw()
        
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

    def _check_and_start_openclaw(self):
        import socket
        import subprocess
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 18791))
        if result == 0:
            print("[OpenClaw] 服务端已在 18791 端口运行。")
        else:
            print("[OpenClaw] 18791 端口未占用，正在启动后台服务...")
            try:
                # 隐藏终端窗口启动子进程
                self.openclaw_process = subprocess.Popen(
                    ["openclaw", "start"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"[OpenClaw] 启动失败: {e}")
        sock.close()

    def cleanup(self):
        if self.openclaw_process:
            print("[OpenClaw] 正在关闭后台服务...")
            self.openclaw_process.terminate()
            self.openclaw_process.wait(timeout=3)
        self.mouse_thread.quit()

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
    
    ret = app.exec()
    manager.cleanup()
    sys.exit(ret)