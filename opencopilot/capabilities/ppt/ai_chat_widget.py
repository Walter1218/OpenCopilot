"""
AI 对话共创组件

功能：
- 用户输入自然语言指令修改幻灯片
- AI 理解指令并返回修改建议
- 支持多种指令类型：
  - 修改标题/副标题
  - 修改版式
  - 添加/删除/修改要点
  - 修改内容类型（文本/图片/流程图等）
  - 插入新幻灯片
- 集成智能建议气泡和内容分析面板
"""

import copy
import json
import re
import uuid
import urllib.request
import urllib.error

# requests 兼容层：当 requests 未安装时使用 urllib 实现相同接口
_json_mod = json  # 保存 json 模块引用，避免被参数名覆盖
try:
    import requests
except ImportError:
    # 轻量级 requests 兼容层
    class _RequestsResponse:
        """模拟 requests.Response"""
        def __init__(self, resp):
            self._resp = resp
            self.status_code = resp.status
            self._content = None  # 延迟读取
        
        def json(self):
            if self._content is None:
                self._content = self._resp.read()
            return _json_mod.loads(self._content)
        
        @property
        def content(self):
            if self._content is None:
                self._content = self._resp.read()
            return self._content
        
        def iter_lines(self):
            """SSE 流式读取 - 逐行读取"""
            while True:
                line = self._resp.readline()
                if not line:
                    break
                yield line.strip()
    
    class _RequestsExceptions:
        ConnectionError = urllib.error.URLError
        Timeout = urllib.error.URLError
    
    class _RequestsModule:
        """最小化 requests 兼容层"""
        exceptions = _RequestsExceptions()
        
        @staticmethod
        def get(url, timeout=None):
            try:
                req = urllib.request.Request(url, method='GET')
                resp = urllib.request.urlopen(req, timeout=timeout)
                return _RequestsResponse(resp)
            except urllib.error.HTTPError as e:
                return _RequestsResponse(e)
        
        @staticmethod
        def post(url, json=None, stream=False, timeout=None):
            payload = json  # 重命名避免与 json 模块冲突
            data = _json_mod.dumps(payload).encode('utf-8') if payload else None
            req = urllib.request.Request(
                url, data=data, method='POST',
                headers={'Content-Type': 'application/json'}
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            return _RequestsResponse(resp)
    
    requests = _RequestsModule()

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor, QKeyEvent

# 导入新的UI组件
from .suggestion_bubble import SuggestionBubble, SuggestionBubbleManager
from .content_analysis_panel import ContentAnalysisPanel, AnalysisPanelManager


class ChatMessageWidget(QFrame):
    """聊天消息组件"""
    
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._init_ui(text)
    
    def _init_ui(self, text: str):
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        if self.is_user:
            layout.addStretch()
        
        # 消息气泡
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        if self.is_user:
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #007bff;
                    color: white;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 13px;
                    max-width: 300px;
                }
            """)
        else:
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #2d2d2d;
                    color: #d4d4d4;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 13px;
                    max-width: 300px;
                    border: 1px solid #3c3c3c;
                }
            """)
        
        layout.addWidget(bubble)
        
        if not self.is_user:
            layout.addStretch()


class HealthChecker(QThread):
    """Agent 服务健康检查线程"""
    
    result = pyqtSignal(bool, str)
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
    
    def run(self):
        try:
            r = requests.get(f"{self.url}/health", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                sessions = data.get("active_sessions", 0)
                self.result.emit(True, f"● 在线 (会话: {sessions})")
            else:
                self.result.emit(False, f"● 异常 ({r.status_code})")
        except requests.exceptions.ConnectionError:
            self.result.emit(False, "● 离线")
        except requests.exceptions.Timeout:
            self.result.emit(False, "● 无响应")
        except Exception:
            self.result.emit(False, "● 未知")


class AIWorker(QThread):
    """AI 处理线程（内嵌 Pipeline 模式）"""

    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, agent_url: str = None, parent=None):
        super().__init__(parent)
        # agent_url 参数保留用于向后兼容，不再使用（统一走 Pipeline）
        self.instruction = ""
        self.slides_data = []
        self.current_index = -1
        self.session_id = ""

    def set_task(self, instruction: str, slides_data: list, current_index: int, session_id: str = ""):
        """设置任务"""
        self.instruction = instruction
        self.slides_data = slides_data
        self.current_index = current_index
        self.session_id = session_id

    def run(self):
        """执行任务 - 通过统一 Agent Pipeline 调用器"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability

            # 使用统一的 prompt 构建服务，context_source="ppt_editor" 会自动注入 PPT 编辑指令
            user_message = self._build_user_message()
            session_id = self.session_id or f"ppt_cocreation_{uuid.uuid4().hex[:8]}"
            
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Cocreation START | text_len={len(user_message)}",
                        session_id=session_id, event="PPT_COCREATION_START")

            full_text = ""
            for chunk in call_agent_pipeline_sync(
                text=user_message,
                action_type="chat",
                session_id=session_id,
                context_source="ppt_editor",
            ):
                full_text += chunk

            if full_text:
                obs.gui_log(f"PPT Cocreation DONE | output_len={len(full_text)}",
                            session_id=session_id, event="PPT_COCREATION_DONE")
                self.response_ready.emit(full_text)
            else:
                obs.gui_log("PPT Cocreation EMPTY response",
                            session_id=session_id, event="PPT_COCREATION_EMPTY", level="WARN")
                self.error_occurred.emit("Agent 返回空响应，可能是模型配置问题")

        except Exception as e:
            self.error_occurred.emit(f"调用 Agent Pipeline 失败: {str(e)}")
    
    # _build_system_prompt 已移除，PPT 编辑指令统一由 prompt_builder.py 的 CONTEXT_DESCRIPTIONS["ppt_editor"] 管理
    
    def _build_user_message(self) -> str:
        """构建用户消息 — 增量发送：当前页完整 + 相邻页摘要"""
        total = len(self.slides_data)
        idx = self.current_index if self.current_index >= 0 else 0
        
        # 当前页完整数据
        current_slide = self.slides_data[idx] if self.slides_data and idx < total else {}
        
        # 相邻页摘要
        prev_summary = self._summarize_slide(idx - 1) if idx > 0 else None
        next_summary = self._summarize_slide(idx + 1) if idx < total - 1 else None
        
        parts = [f"PPT 总共 {total} 页，当前正在编辑第 {idx + 1} 页。"]
        
        if prev_summary:
            parts.append(f"\n前一页（第 {idx} 页）摘要：{prev_summary}")
        
        parts.append(f"\n当前幻灯片数据：\n```json\n{json.dumps(current_slide, ensure_ascii=False, indent=2)}\n```")
        
        if next_summary:
            parts.append(f"\n后一页（第 {idx + 2} 页）摘要：{next_summary}")
        
        parts.append(f"\n用户指令：{self.instruction}")
        parts.append("\n请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：")
        
        return "\n".join(parts)
    
    def _summarize_slide(self, idx: int) -> str:
        """生成单页幻灯片摘要（token 友好）"""
        if idx < 0 or idx >= len(self.slides_data):
            return ""
        slide = self.slides_data[idx]
        title = slide.get("title", "(无标题)")
        layout = slide.get("layout", "text_only")
        items = slide.get("items", [])
        # 只取前3个要点文本摘要
        item_texts = [it.get("text", "")[:20] for it in items[:3] if it.get("text")]
        items_str = "、".join(item_texts) if item_texts else "无要点"
        return f"标题：{title}，版式：{layout}，要点：{items_str}"


class AICopilotChatWidget(QWidget):
    """AI 对话共创组件"""
    
    # 信号
    slides_updated = pyqtSignal(list)  # 幻灯片数据更新
    
    def __init__(self, agent_url: str = None, parent=None):
        super().__init__(parent)
        # agent_url 参数保留用于向后兼容，不再使用（统一走 Pipeline）
        self.agent_url = agent_url
        self.slides_data = []
        self.current_index = -1
        self.worker = None
        self._session_id = f"ppt_cocreation_{uuid.uuid4().hex[:8]}"  # 稳定会话 ID，支持多轮对话
        self._last_instruction = ""  # 保存最近一次用户指令，用于 undo 描述
        
        # Undo/Redo 操作栈
        self._undo_stack = []       # [(slides_data_deepcopy, description), ...]
        self._redo_stack = []       # [(slides_data_deepcopy, description), ...]
        self._max_history = 50
        
        # 新增：智能建议和分析面板
        self.suggestion_manager = None
        self.analysis_manager = None
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("🤖 AI 助手")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0;
            }
        """)
        header.addWidget(title)
        
        # Agent 状态指示灯
        self.status_indicator = QLabel("● 检测中...")
        self.status_indicator.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(self.status_indicator)
        
        # 异步探活
        QTimer.singleShot(500, self._check_agent_health)
        
        # Undo / Redo 按钮
        self.undo_btn = QPushButton("↩")
        self.undo_btn.setFixedSize(24, 24)
        self.undo_btn.setToolTip("撤销 (Ctrl+Z)")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #888;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                color: #d4d4d4;
            }
            QPushButton:disabled {
                color: #555;
            }
        """)
        self.undo_btn.clicked.connect(self.undo)
        header.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("↪")
        self.redo_btn.setFixedSize(24, 24)
        self.redo_btn.setToolTip("重做 (Ctrl+Y)")
        self.redo_btn.setEnabled(False)
        self.redo_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #888;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                color: #d4d4d4;
            }
            QPushButton:disabled {
                color: #555;
            }
        """)
        self.redo_btn.clicked.connect(self.redo)
        header.addWidget(self.redo_btn)
        
        # 内容分析面板切换按钮
        self.analysis_toggle_btn = QPushButton("📊")
        self.analysis_toggle_btn.setFixedSize(24, 24)
        self.analysis_toggle_btn.setToolTip("显示/隐藏内容分析面板")
        self.analysis_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #888;
                border: none;
                border-radius: 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4a9eff;
                color: white;
            }
        """)
        self.analysis_toggle_btn.setCheckable(True)
        self.analysis_toggle_btn.clicked.connect(self._toggle_analysis_panel)
        header.addWidget(self.analysis_toggle_btn)
        
        header.addStretch()
        
        # 折叠按钮
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #888;
                border: none;
                border-radius: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                color: #e0e0e0;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle_chat)
        header.addWidget(self.toggle_btn)
        
        layout.addLayout(header)
        
        # 主内容区域：聊天 + 分析面板
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(2)
        
        # 聊天区域
        self.chat_area = QWidget()
        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(4)
        
        # 消息滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_container)
        chat_layout.addWidget(self.scroll_area, 1)
        
        # 快捷指令区域
        shortcuts_layout = QHBoxLayout()
        shortcuts_layout.setSpacing(8)
        
        shortcut_labels = ["换个标题", "添加要点", "换版式", "精简内容", "转图表"]
        self._shortcut_buttons = []
        
        for label in shortcut_labels:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #888;
                    border: 1px solid #3c3c3c;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #3c3c3c;
                    color: #d4d4d4;
                    border-color: #555;
                }
            """)
            btn.clicked.connect(lambda checked, lbl=label: self._execute_shortcut(self._build_shortcut_command(lbl)))
            shortcuts_layout.addWidget(btn)
            self._shortcut_buttons.append(btn)
        
        shortcuts_layout.addStretch()
        chat_layout.addLayout(shortcuts_layout)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入指令，如：把第2页的标题改为'核心优势'...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)
        self.input_edit.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input_edit)
        
        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #666;
            }
        """)
        self.send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addLayout(input_layout)
        
        # 将聊天区域添加到splitter
        self.main_splitter.addWidget(self.chat_area)
        
        # 创建分析面板（初始隐藏）
        self.analysis_panel = ContentAnalysisPanel()
        self.analysis_panel.setMinimumWidth(200)
        self.analysis_panel.setMaximumWidth(350)
        self.main_splitter.addWidget(self.analysis_panel)
        
        # 设置splitter比例
        self.main_splitter.setSizes([400, 250])
        self.main_splitter.setStretchFactor(0, 1)  # 聊天区域可拉伸
        self.main_splitter.setStretchFactor(1, 0)  # 分析面板固定
        
        # 默认隐藏分析面板
        self.analysis_panel.setVisible(False)
        
        # 初始化分析面板管理器
        self.analysis_manager = AnalysisPanelManager(self.analysis_panel)
        
        # 添加splitter到主布局
        layout.addWidget(self.main_splitter)
        
        # 添加欢迎消息
        self._add_message("你好！我是 PPT 编辑助手。你可以用自然语言告诉我如何修改幻灯片，例如：\n\n• 把第2页的标题改为'核心优势'\n• 在第3页添加一个流程图\n• 把第1页改为图文混排\n\n💡 提示：点击标题栏的 📊 按钮可打开内容分析面板", is_user=False)
    
    def _toggle_chat(self):
        """折叠/展开聊天区域"""
        is_visible = self.chat_area.isVisible()
        self.chat_area.setVisible(not is_visible)
        self.toggle_btn.setText("▲" if not is_visible else "▼")
    
    def _toggle_analysis_panel(self):
        """显示/隐藏内容分析面板"""
        is_visible = self.analysis_panel.isVisible()
        self.analysis_panel.setVisible(not is_visible)
        self.analysis_toggle_btn.setChecked(not is_visible)
        
        # 如果显示面板，触发当前幻灯片的分析
        if not is_visible:
            self._analyze_current_slide()
    
    def _check_agent_health(self):
        """异步检测 Agent Pipeline 状态"""
        import asu_custom_agent
        is_alive = hasattr(asu_custom_agent, 'pipeline') and asu_custom_agent.pipeline is not None
        text = "🟢 Agent Pipeline 在线" if is_alive else "🔴 Agent Pipeline 未就绪"
        self._on_health_result(is_alive, text)
    
    def _on_health_result(self, is_alive: bool, text: str):
        """更新状态指示灯"""
        if is_alive:
            self.status_indicator.setStyleSheet("color: #4caf50; font-size: 11px;")
        else:
            self.status_indicator.setStyleSheet("color: #f44336; font-size: 11px;")
        self.status_indicator.setText(text)
    
    def set_slides_data(self, slides: list, current_index: int = -1):
        """设置幻灯片数据"""
        self.slides_data = slides
        self.current_index = current_index
        
        # 如果分析面板可见，自动分析当前幻灯片
        if self.analysis_panel.isVisible() and current_index >= 0:
            self._analyze_current_slide()
    
    def _analyze_current_slide(self):
        """分析当前幻灯片内容（TODO: 迁移到 Pipeline 模式）"""
        if not self.slides_data or self.current_index < 0:
            return
        
        if self.current_index >= len(self.slides_data):
            return
        
        current_slide = self.slides_data[self.current_index]
        content = current_slide.get("content", "")
        title = current_slide.get("title", "")
        
        full_content = f"{title}\n{content}".strip()
        if not full_content:
            return
        
        # TODO: PPT 分析 API 待迁移到 Pipeline 模式下的独立端点
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability
            
            session_id = f"ppt_analyze_{self.current_index}"
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Analyze START | slide={self.current_index} text_len={len(full_content)}",
                        session_id=session_id, event="PPT_ANALYZE_START")
            
            result = ""
            for chunk in call_agent_pipeline_sync(
                text=f"请分析以下PPT幻灯片内容：\n{full_content}",
                action_type="ppt",
                session_id=session_id,
                context_source="ppt_editor",
            ):
                result += chunk
            if result and self.analysis_manager:
                obs.gui_log(f"PPT Analyze DONE | output_len={len(result)}",
                            session_id=session_id, event="PPT_ANALYZE_DONE")
                self.analysis_manager.update_analysis_debounced({"analysis": result})
        except Exception as e:
            print(f"PPT 分析失败: {e}")
    
    def _add_message(self, text: str, is_user: bool = True):
        """添加消息"""
        msg_widget = ChatMessageWidget(text, is_user)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, msg_widget)
        
        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        """滚动到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _execute_shortcut(self, command: str):
        """执行快捷指令"""
        self.input_edit.setText(command)
        self._on_send()

    def send_instruction(self, instruction: str):
        """程序化发送指令（供外部组件调用，如 SourcePanel 重新生成）"""
        if not instruction:
            return
        # 添加用户消息（标记来源）
        self._add_message(f"🔄 {instruction[:100]}{'...' if len(instruction) > 100 else ''}", is_user=True)

        # 禁用输入
        self.input_edit.setEnabled(False)
        self.send_btn.setEnabled(False)

        # 断开旧工作线程信号，防止信号泄漏
        if hasattr(self, 'worker') and self.worker is not None:
            try:
                self.worker.response_ready.disconnect(self._on_ai_response)
            except TypeError:
                pass
            try:
                self.worker.error_occurred.disconnect(self._on_ai_error)
            except TypeError:
                pass
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(2000)

        # 创建 AI 工作线程
        self.worker = AIWorker(self.agent_url)
        self.worker.response_ready.connect(self._on_ai_response)
        self.worker.error_occurred.connect(self._on_ai_error)
        self.worker.set_task(instruction, self.slides_data, self.current_index, self._session_id)
        self._last_instruction = instruction
        self.worker.start()
    
    def _build_shortcut_command(self, label: str) -> str:
        """根据当前幻灯片上下文构建快捷指令"""
        idx = self.current_index if self.current_index >= 0 else 0
        slide = self.slides_data[idx] if self.slides_data and idx < len(self.slides_data) else {}
        title = slide.get("title", "无标题")
        items = slide.get("items", [])
        items_summary = "、".join([item.get("text", "")[:30] for item in items[:5]]) or "无"
        
        context = f"（第{idx+1}页，标题：{title}" + (f"，要点：{items_summary}" if items_summary else "") + "）"
        
        commands = {
            "换个标题": f"当前幻灯片{context}，请为它建议一个新的、更有吸引力的标题",
            "添加要点": f"当前幻灯片{context}，请为它添加一个新的、有价值的要点",
            "换版式": f"当前幻灯片{context}，版式为{slide.get('layout','text_only')}，请根据内容特点建议更合适的版式",
            "精简内容": f"当前幻灯片{context}，请精简内容，保留最核心的信息",
            "转图表": f"当前幻灯片{context}，请分析内容，将适合的部分转换为图表或表格展示",
        }
        return commands.get(label, f"请处理当前幻灯片{context}")
    
    def _on_send(self):
        """发送消息"""
        instruction = self.input_edit.text().strip()
        if not instruction:
            return
        
        # 埋点：记录发送的指令
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT_COCREATION_SEND | instruction_len={len(instruction)} | slide_count={len(self.slides_data)} | current_index={self.current_index}",
                    session_id=self._session_id, event="PPT_COCREATION_SEND")
        
        # 添加用户消息
        self._add_message(instruction, is_user=True)
        self.input_edit.clear()
        
        # 禁用输入
        self.input_edit.setEnabled(False)
        self.send_btn.setEnabled(False)
        
        # 断开旧工作线程信号，防止信号泄漏
        if hasattr(self, 'worker') and self.worker is not None:
            try:
                self.worker.response_ready.disconnect(self._on_ai_response)
            except TypeError:
                pass
            try:
                self.worker.error_occurred.disconnect(self._on_ai_error)
            except TypeError:
                pass
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(2000)
        # 创建 AI 工作线程
        self.worker = AIWorker(self.agent_url)
        self.worker.response_ready.connect(self._on_ai_response)
        self.worker.error_occurred.connect(self._on_ai_error)
        self.worker.set_task(instruction, self.slides_data, self.current_index, self._session_id)
        self._last_instruction = instruction  # 保存指令用于 undo 描述
        self.worker.start()
    
    def _on_ai_response(self, response: str):
        """AI 响应 — 支持处理多个 JSON 动作"""
        try:
            # 埋点：记录 AI 响应
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT_COCREATION_RESPONSE | response_len={len(response)} | preview={response[:100]}",
                        session_id=self._session_id, event="PPT_COCREATION_RESPONSE")
            
            # 提取所有 JSON 对象（AI 可能返回多个操作指令）
            json_objects = self._extract_all_json(response)
            if not json_objects:
                raise ValueError("无法找到 JSON 数据")
            
            # 埋点：记录提取到的 JSON 对象数量
            obs.gui_log(f"PPT_COCREATION_JSON_EXTRACTED | json_count={len(json_objects)}",
                        session_id=self._session_id, event="PPT_COCREATION_JSON_EXTRACTED")
            
            # 保存操作前状态（用于撤销）
            self._push_undo_state(self._last_instruction[:40] + ("..." if len(self._last_instruction) > 40 else ""))
            
            success_msgs = []
            first_error = None
            
            for json_str in json_objects:
                try:
                    data = json.loads(json_str)
                    msg = self._apply_update(data)
                    success_msgs.append(msg)
                except Exception as e:
                    if first_error is None:
                        first_error = str(e)
                    continue
            
            if success_msgs:
                # 构建带对比的反馈消息
                if len(success_msgs) == 1 and isinstance(success_msgs[0], dict):
                    # 单条改动，显示 before/after 对比
                    self._add_message(self._format_diff_message(success_msgs[0]), is_user=False)
                elif len(success_msgs) <= 2:
                    # 多条改动，简洁汇总
                    self._add_message("✅ 已完成以下修改：\n" + "\n".join(
                        f"  • {m.get('summary', str(m))}" for m in success_msgs if isinstance(m, dict)
                    ), is_user=False)
                    # 为每条改动显示对比
                    for m in success_msgs:
                        if isinstance(m, dict) and m.get("old_value") is not None:
                            self._add_message(self._format_diff_message(m), is_user=False)
                else:
                    summaries = [m.get("summary", str(m)) if isinstance(m, dict) else str(m) for m in success_msgs]
                    self._add_message(f"✅ 已应用 {len(success_msgs)} 项更新", is_user=False)
                    for s in summaries[:5]:
                        self._add_message(f"  • {s}", is_user=False)
                
                # 触发建议气泡
                self._trigger_suggestions_for_current_slide()
                
                # 更新分析面板
                if self.analysis_panel.isVisible():
                    self._analyze_current_slide()
            elif first_error:
                raise ValueError(first_error)
            else:
                raise ValueError("所有 JSON 对象解析失败")
        
        except json.JSONDecodeError as e:
            self._add_message(f"⚠️ 无法解析 AI 返回的数据：{str(e)}\n\n原始响应：\n{response}", is_user=False)
        
        except Exception as e:
            self._add_message(f"⚠️ 处理失败：{str(e)}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    def _format_diff_message(self, diff_info: dict) -> str:
        """格式化改动对比消息"""
        old_val = diff_info.get("old_value")
        new_val = diff_info.get("new_value")
        summary = diff_info.get("summary", "")
        field = diff_info.get("field", "")
        
        if old_val is None and new_val is None:
            return f"✅ {summary}"
        
        # 截断长文本
        def _truncate(v, max_len=60):
            s = str(v) if v is not None else ""
            return s[:max_len] + "..." if len(s) > max_len else s
        
        old_str = _truncate(old_val) or "(空)"
        new_str = _truncate(new_val) or "(空)"
        
        lines = [f"✅ {summary}"]
        if field:
            lines.append(f"  `{field}`: ~~{old_str}~~ → **{new_str}**")
        else:
            lines.append(f"  ~~{old_str}~~ → **{new_str}**")
        
        return "\n".join(lines)
    
    def _extract_all_json(self, text: str) -> list:
        """从文本中提取所有 JSON 对象（支持多个操作指令）"""
        # 先尝试从 ```json ... ``` 代码块中提取
        code_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if code_blocks:
            all_objects = []
            for block_content in code_blocks:
                block_content = block_content.strip()
                if block_content.startswith('{') or block_content.startswith('['):
                    all_objects.extend(self._find_all_json_objects(block_content))
            if all_objects:
                return all_objects
        
        # 尝试直接从全文中提取所有 JSON 对象
        return self._find_all_json_objects(text)
    
    def _find_all_json_objects(self, text: str) -> list:
        """用括号计数找到所有匹配的 JSON 对象"""
        objects = []
        i = 0
        n = len(text)
        while i < n:
            start = text.find('{', i)
            if start == -1:
                break
            
            depth = 0
            for j in range(start, n):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        objects.append(text[start:j + 1])
                        i = j + 1
                        break
            else:
                # 括号未闭合，跳过
                i = start + 1
        
        return objects
    
    def _trigger_suggestions_for_current_slide(self):
        """为当前幻灯片触发建议气泡（通过 Pipeline）"""
        if not self.slides_data or self.current_index < 0:
            return
        
        if self.current_index >= len(self.slides_data):
            return
        
        current_slide = self.slides_data[self.current_index]
        content = current_slide.get("content", "")
        title = current_slide.get("title", "")
        
        full_content = f"{title}\n{content}".strip()
        if not full_content:
            return
        
        try:
            from PyQt6.QtCore import QPoint
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability
            import json
            
            session_id = f"ppt_suggest_{self.current_index}"
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Suggest START | slide={self.current_index} text_len={len(full_content)}",
                        session_id=session_id, event="PPT_SUGGEST_START")
            
            result = ""
            for chunk in call_agent_pipeline_sync(
                text=f"请为以下PPT幻灯片提供1-2条优化建议：\n{full_content}",
                action_type="ppt",
                session_id=session_id,
                context_source="ppt_editor",
            ):
                result += chunk
            
            if result.strip():
                obs.gui_log(f"PPT Suggest DONE | output_len={len(result)}",
                            session_id=session_id, event="PPT_SUGGEST_DONE")
                suggestion = {"title": "AI优化建议", "content": result[:200]}
                if not self.suggestion_manager:
                    self.suggestion_manager = SuggestionBubbleManager(self)
                pos = self.mapToGlobal(QPoint(self.width() // 2, 50))
                self.suggestion_manager.show_suggestion(
                    suggestion, pos,
                    on_accept=self._on_suggestion_accepted,
                    on_dismiss=self._on_suggestion_dismissed
                )
        except Exception as e:
            print(f"获取建议失败: {e}")
    
    def _on_suggestion_accepted(self, suggestion: dict):
        """建议被接受"""
        self._add_message(f"💡 已应用AI建议：{suggestion.get('title', '优化建议')}", is_user=False)
        # 可以在这里触发实际的优化操作
    
    def _on_suggestion_dismissed(self):
        """建议被忽略"""
        pass  # 静默忽略
    
    # ==========================================
    # 内容转换本地 ETL（P2-3）
    # ==========================================
    
    def _normalize_content_item(self, item: dict) -> dict:
        """本地校验并补全内容转换数据（chart/table/flowchart）"""
        ct = item.get("content_type", "")
        
        if ct == "table":
            td = item.get("table_data", {})
            if not isinstance(td, dict):
                td = {}
            td.setdefault("title", "数据表")
            td.setdefault("columns", ["项目", "内容"])
            td.setdefault("rows", [])
            # 确保每行列数一致
            col_count = len(td["columns"])
            td["rows"] = [r[:col_count] if len(r) > col_count else r + [""] * (col_count - len(r)) for r in td["rows"]]
            item["table_data"] = td
            
        elif ct == "chart":
            cd = item.get("chart_data", {})
            ct = item.get("chart_type", "bar")
            if not isinstance(cd, dict):
                cd = {}
            cd.setdefault("title", "图表")
            cd.setdefault("labels", [])
            cd.setdefault("datasets", [])
            # 确保 datasets 格式正确
            if cd["datasets"] and isinstance(cd["datasets"][0], dict):
                cd["datasets"][0].setdefault("label", "数据")
                cd["datasets"][0].setdefault("data", [])
                cd["datasets"][0].setdefault("color", "#007bff")
            item["chart_data"] = cd
            
        elif ct == "flowchart":
            fd = item.get("flowchart_data", {})
            if not isinstance(fd, dict):
                fd = {}
            fd.setdefault("title", "流程图")
            fd.setdefault("steps", [])
            item["flowchart_data"] = fd
        
        return item
    
    def _apply_update(self, data: dict) -> dict:
        """应用更新（支持局部更新和全量更新），返回 diff 字典"""
        action = data.get("action")
        
        # 埋点：记录应用的更新类型
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT_COCREATION_APPLY_UPDATE | action={action} | data_keys={list(data.keys())}",
                    session_id=self._session_id, event="PPT_COCREATION_APPLY_UPDATE")
        
        # 局部更新模式
        if action == "update":
            return self._apply_field_update(data)
        elif action == "update_item":
            return self._apply_item_update(data)
        elif action == "add_item":
            return self._apply_add_item(data)
        elif action == "remove_item":
            return self._apply_remove_item(data)
        elif action == "add_slide":
            return self._apply_add_slide(data)
        elif action == "remove_slide":
            return self._apply_remove_slide(data)
        
        # 全量更新模式（兼容旧模式）
        if "slides" in data:
            old_len = len(self.slides_data)
            new_len = len(data["slides"])
            self.slides_data = data["slides"]
            self.slides_updated.emit(self.slides_data)
            return {
                "summary": f"已全量更新幻灯片（{old_len}页 → {new_len}页）",
                "field": "slides", "old_value": f"{old_len}页", "new_value": f"{new_len}页"
            }
        
        raise ValueError("无法识别的更新格式")
    
    def _apply_field_update(self, data: dict) -> dict:
        """应用字段更新"""
        slide_idx = data.get("slide_index")
        field = data.get("field")
        value = data.get("value")
        
        if slide_idx is None or field is None:
            raise ValueError("缺少 slide_index 或 field")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        old_value = self.slides_data[slide_idx].get(field)
        self.slides_data[slide_idx][field] = value
        self.slides_updated.emit(self.slides_data)
        return {
            "summary": f"已更新第 {slide_idx + 1} 页的 {field}",
            "field": field, "old_value": old_value, "new_value": value
        }
    
    def _apply_item_update(self, data: dict) -> dict:
        """应用要点更新"""
        slide_idx = data.get("slide_index")
        item_idx = data.get("item_index")
        field = data.get("field")
        value = data.get("value")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        items = self.slides_data[slide_idx].get("items", [])
        if not (0 <= item_idx < len(items)):
            raise ValueError(f"要点索引 {item_idx} 超出范围")
        
        old_value = items[item_idx].get(field)
        items[item_idx][field] = value
        self.slides_updated.emit(self.slides_data)
        return {
            "summary": f"已更新第 {slide_idx + 1} 页第 {item_idx + 1} 个要点的 {field}",
            "field": field, "old_value": old_value, "new_value": value
        }
    
    def _apply_add_item(self, data: dict) -> dict:
        """添加要点"""
        slide_idx = data.get("slide_index")
        item = data.get("item")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        # 内容转换项：本地 ETL 校验 & 补全
        item = self._normalize_content_item(item)
        
        # 埋点：记录添加的内容类型
        content_type = item.get("content_type", "text")
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT_COCREATION_ADD_ITEM | slide_idx={slide_idx} | content_type={content_type}",
                    session_id=self._session_id, event="PPT_COCREATION_ADD_ITEM")
        
        old_count = len(self.slides_data[slide_idx].get("items", []))
        self.slides_data[slide_idx].setdefault("items", []).append(item)
        self.slides_updated.emit(self.slides_data)
        item_preview = item.get("text", item.get("content_type", "要点"))[:30]
        return {
            "summary": f"已在第 {slide_idx + 1} 页添加要点",
            "field": "items", "old_value": f"{old_count}个要点", "new_value": f"+ {item_preview}"
        }
    
    def _apply_remove_item(self, data: dict) -> dict:
        """删除要点"""
        slide_idx = data.get("slide_index")
        item_idx = data.get("item_index")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        items = self.slides_data[slide_idx].get("items", [])
        if not (0 <= item_idx < len(items)):
            raise ValueError(f"要点索引 {item_idx} 超出范围")
        
        removed_text = items[item_idx].get("text", "")[:30]
        items.pop(item_idx)
        self.slides_updated.emit(self.slides_data)
        return {
            "summary": f"已删除第 {slide_idx + 1} 页第 {item_idx + 1} 个要点",
            "field": "items", "old_value": f"'{removed_text}'", "new_value": "(已删除)"
        }
    
    def _apply_add_slide(self, data: dict) -> dict:
        """添加幻灯片"""
        index = data.get("index", len(self.slides_data))
        slide = data.get("slide")
        
        if not (0 <= index <= len(self.slides_data)):
            raise ValueError(f"插入位置 {index} 超出范围")
        
        old_count = len(self.slides_data)
        self.slides_data.insert(index, slide)
        self.slides_updated.emit(self.slides_data)
        return {
            "summary": f"已在第 {index + 1} 页位置插入新幻灯片",
            "field": "slides", "old_value": f"{old_count}页", "new_value": f"{old_count + 1}页"
        }
    
    def _apply_remove_slide(self, data: dict) -> dict:
        """删除幻灯片"""
        index = data.get("index")
        
        if not (0 <= index < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {index} 超出范围")
        
        old_count = len(self.slides_data)
        removed_title = self.slides_data[index].get("title", "")[:30]
        self.slides_data.pop(index)
        self.slides_updated.emit(self.slides_data)
        return {
            "summary": f"已删除第 {index + 1} 页幻灯片（{removed_title}）",
            "field": "slides", "old_value": f"{old_count}页", "new_value": f"{old_count - 1}页"
        }
    
    def _on_ai_error(self, error: str):
        """AI 错误"""
        self._add_message(f"❌ {error}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    # ==========================================
    # Undo / Redo 操作栈
    # ==========================================
    
    def _push_undo_state(self, description: str):
        """保存当前状态到撤销栈"""
        self._undo_stack.append((copy.deepcopy(self.slides_data), description))
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()
    
    def undo(self):
        """撤销上一次操作"""
        if not self._undo_stack:
            return
        # 当前状态 push 到 redo 栈
        self._redo_stack.append((copy.deepcopy(self.slides_data), self._undo_stack[-1][1]))
        # 恢复上一状态
        prev_data, description = self._undo_stack.pop()
        self.slides_data = prev_data
        self.slides_updated.emit(self.slides_data)
        self._add_message(f"↩ 已撤销：{description}", is_user=False)
        self._update_undo_redo_buttons()
    
    def redo(self):
        """重做上一次撤销的操作"""
        if not self._redo_stack:
            return
        # 当前状态 push 到 undo 栈
        self._undo_stack.append((copy.deepcopy(self.slides_data), self._redo_stack[-1][1]))
        # 恢复 redo 状态
        next_data, description = self._redo_stack.pop()
        self.slides_data = next_data
        self.slides_updated.emit(self.slides_data)
        self._add_message(f"↪ 已重做：{description}", is_user=False)
        self._update_undo_redo_buttons()
    
    def _update_undo_redo_buttons(self):
        """更新撤销/重做按钮状态"""
        self.undo_btn.setEnabled(len(self._undo_stack) > 0)
        self.undo_btn.setToolTip(
            f"撤销 ({len(self._undo_stack)}) — Ctrl+Z" if self._undo_stack else "无可撤销操作"
        )
        self.redo_btn.setEnabled(len(self._redo_stack) > 0)
        self.redo_btn.setToolTip(
            f"重做 ({len(self._redo_stack)}) — Ctrl+Y" if self._redo_stack else "无可重做操作"
        )
    
    def keyPressEvent(self, event):
        """键盘事件：Ctrl+Z 撤销，Ctrl+Y 重做"""
        from PyQt6.QtCore import Qt
        modifiers = event.modifiers()
        
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                return
        
        super().keyPressEvent(event)
    
    # ==========================================
    # 主题
    # ==========================================

    def apply_theme(self, theme: dict):
        """应用主题样式"""
        # 更新滚动区域样式（聊天显示区域）
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme['dialog_bg']};
                color: {theme['dialog_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
            }}
        """)
        
        # 更新输入框样式
        self.input_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['button_bg']};
                color: {theme['dialog_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {theme['accent_color']};
            }}
        """)
        
        # 更新发送按钮样式
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['accent_color']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['button_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {theme['button_bg']};
                color: {theme['dialog_color']};
                opacity: 0.5;
            }}
        """)
        
        # 更新快捷指令按钮样式
        for button in self.findChildren(QPushButton):
            if button != self.send_btn:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme['button_bg']};
                        color: {theme['dialog_color']};
                        border: 1px solid {theme['border_color']};
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['button_hover']};
                        border-color: {theme['accent_color']};
                    }}
                    QPushButton:pressed {{
                        background-color: {theme['button_pressed']};
                    }}
                """)
        
        # 更新标签样式
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"""
                QLabel {{
                    color: {theme['dialog_color']};
                    font-size: 12px;
                    padding: 2px;
                }}
            """)
