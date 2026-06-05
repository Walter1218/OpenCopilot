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

import json
import re
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

    def set_task(self, instruction: str, slides_data: list, current_index: int):
        """设置任务"""
        self.instruction = instruction
        self.slides_data = slides_data
        self.current_index = current_index

    def run(self):
        """执行任务 - 通过统一 Agent Pipeline 调用器"""
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability

            # 使用统一的 prompt 构建服务，context_source="ppt_editor" 会自动注入 PPT 编辑指令
            user_message = self._build_user_message()
            session_id = f"ppt_cocreation_{id(self)}"
            
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
        """构建用户消息"""
        return f"""当前幻灯片数据：
```json
{json.dumps({"slides": self.slides_data}, ensure_ascii=False, indent=2)}
```

当前正在编辑第 {self.current_index + 1} 页幻灯片。

用户指令：{self.instruction}

请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）："""


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
        
        shortcut_commands = [
            ("换个标题", "请为当前幻灯片建议一个新标题"),
            ("添加要点", "在当前幻灯片添加一个新的要点"),
            ("换版式", "将当前幻灯片改为更合适的版式"),
            ("精简内容", "精简当前幻灯片的内容，保留核心信息"),
            ("转图表", "分析当前幻灯片的内容，将适合的数据转换为图表或表格"),
        ]
        
        for label, command in shortcut_commands:
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
            btn.clicked.connect(lambda checked, cmd=command: self._execute_shortcut(cmd))
            shortcuts_layout.addWidget(btn)
        
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
    
    def _on_send(self):
        """发送消息"""
        instruction = self.input_edit.text().strip()
        if not instruction:
            return
        
        # 添加用户消息
        self._add_message(instruction, is_user=True)
        self.input_edit.clear()
        
        # 禁用输入
        self.input_edit.setEnabled(False)
        self.send_btn.setEnabled(False)
        
        # 创建 AI 工作线程
        self.worker = AIWorker(self.agent_url)
        self.worker.response_ready.connect(self._on_ai_response)
        self.worker.error_occurred.connect(self._on_ai_error)
        self.worker.set_task(instruction, self.slides_data, self.current_index)
        self.worker.start()
    
    def _on_ai_response(self, response: str):
        """AI 响应"""
        # 尝试解析 JSON
        try:
            # 提取 JSON（支持嵌套花括号）
            json_str = self._extract_json(response)
            if json_str is None:
                raise ValueError("无法找到 JSON 数据")
            
            data = json.loads(json_str)
            
            # 应用更新（支持局部更新和全量更新）
            success_msg = self._apply_update(data)
            
            # 显示成功消息
            self._add_message(f"✅ {success_msg}", is_user=False)
            
            # 新增：触发建议气泡（如果当前幻灯片有优化空间）
            self._trigger_suggestions_for_current_slide()
            
            # 新增：更新分析面板
            if self.analysis_panel.isVisible():
                self._analyze_current_slide()
        
        except json.JSONDecodeError as e:
            # JSON 解析失败，显示原始响应
            self._add_message(f"⚠️ 无法解析 AI 返回的数据：{str(e)}\n\n原始响应：\n{response}", is_user=False)
        
        except Exception as e:
            self._add_message(f"⚠️ 处理失败：{str(e)}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        # 先尝试从 ```json ... ``` 代码块中提取
        code_block = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if code_block:
            block_content = code_block.group(1).strip()
            if block_content.startswith('{') or block_content.startswith('['):
                return self._find_json_object(block_content)
        
        # 尝试直接从全文中提取
        return self._find_json_object(text)
    
    def _find_json_object(self, text: str) -> str:
        """用括号计数找到匹配的 JSON 对象"""
        start = text.find('{')
        if start == -1:
            return None
        
        depth = 0
        for idx in range(start, len(text)):
            if text[idx] == '{':
                depth += 1
            elif text[idx] == '}':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]
        return None
    
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
    
    def _apply_update(self, data: dict) -> str:
        """应用更新（支持局部更新和全量更新）"""
        action = data.get("action")
        
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
            self.slides_data = data["slides"]
            self.slides_updated.emit(self.slides_data)
            return "已全量更新幻灯片数据"
        
        raise ValueError("无法识别的更新格式")
    
    def _apply_field_update(self, data: dict) -> str:
        """应用字段更新"""
        slide_idx = data.get("slide_index")
        field = data.get("field")
        value = data.get("value")
        
        if slide_idx is None or field is None:
            raise ValueError("缺少 slide_index 或 field")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        self.slides_data[slide_idx][field] = value
        self.slides_updated.emit(self.slides_data)
        return f"已更新第 {slide_idx + 1} 页的 {field}"
    
    def _apply_item_update(self, data: dict) -> str:
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
        
        items[item_idx][field] = value
        self.slides_updated.emit(self.slides_data)
        return f"已更新第 {slide_idx + 1} 页第 {item_idx + 1} 个要点"
    
    def _apply_add_item(self, data: dict) -> str:
        """添加要点"""
        slide_idx = data.get("slide_index")
        item = data.get("item")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        self.slides_data[slide_idx].setdefault("items", []).append(item)
        self.slides_updated.emit(self.slides_data)
        return f"已在第 {slide_idx + 1} 页添加新要点"
    
    def _apply_remove_item(self, data: dict) -> str:
        """删除要点"""
        slide_idx = data.get("slide_index")
        item_idx = data.get("item_index")
        
        if not (0 <= slide_idx < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {slide_idx} 超出范围")
        
        items = self.slides_data[slide_idx].get("items", [])
        if not (0 <= item_idx < len(items)):
            raise ValueError(f"要点索引 {item_idx} 超出范围")
        
        items.pop(item_idx)
        self.slides_updated.emit(self.slides_data)
        return f"已删除第 {slide_idx + 1} 页第 {item_idx + 1} 个要点"
    
    def _apply_add_slide(self, data: dict) -> str:
        """添加幻灯片"""
        index = data.get("index", len(self.slides_data))
        slide = data.get("slide")
        
        if not (0 <= index <= len(self.slides_data)):
            raise ValueError(f"插入位置 {index} 超出范围")
        
        self.slides_data.insert(index, slide)
        self.slides_updated.emit(self.slides_data)
        return f"已在第 {index + 1} 页位置插入新幻灯片"
    
    def _apply_remove_slide(self, data: dict) -> str:
        """删除幻灯片"""
        index = data.get("index")
        
        if not (0 <= index < len(self.slides_data)):
            raise ValueError(f"幻灯片索引 {index} 超出范围")
        
        self.slides_data.pop(index)
        self.slides_updated.emit(self.slides_data)
        return f"已删除第 {index + 1} 页幻灯片"
    
    def _on_ai_error(self, error: str):
        """AI 错误"""
        self._add_message(f"❌ {error}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
    
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
