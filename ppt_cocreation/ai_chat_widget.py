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
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor, QKeyEvent


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
    """AI 处理线程"""
    
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, agent_url: str = None, parent=None):
        super().__init__(parent)
        self.agent_url = agent_url or "http://127.0.0.1:18888"
        self.instruction = ""
        self.slides_data = []
        self.current_index = -1
    
    def set_task(self, instruction: str, slides_data: list, current_index: int):
        """设置任务"""
        self.instruction = instruction
        self.slides_data = slides_data
        self.current_index = current_index
    
    def run(self):
        """执行任务"""
        try:
            # 先做探活检测（短超时）
            health_url = f"{self.agent_url}/health"
            try:
                health_resp = requests.get(health_url, timeout=3.0)
                if health_resp.status_code != 200:
                    self.error_occurred.emit(
                        f"Agent 服务异常（状态码: {health_resp.status_code}）\n"
                        f"请尝试重启 Agent：python asu_custom_agent.py"
                    )
                    return
            except requests.exceptions.ConnectionError:
                self.error_occurred.emit(
                    f"无法连接到 Agent 服务 ({self.agent_url})\n"
                    f"请启动 Agent：python asu_custom_agent.py"
                )
                return
            except requests.exceptions.Timeout:
                self.error_occurred.emit(
                    f"Agent 服务无响应（探活超时）\n"
                    f"服务可能已卡死，请重启：kill $(lsof -t -i:18888) && python asu_custom_agent.py"
                )
                return
            
            # 探活通过，构建用户消息并发送
            system_prompt = self._build_system_prompt()
            user_message = self._build_user_message()
            full_message = f"{system_prompt}\n\n{user_message}"
            
            payload = {
                "text": full_message,
                "context_source": "ppt_editor",
                "persona": "code",
                "action_type": "chat",
                "session_id": f"ppt_cocreation_{id(self)}"
            }
            
            resp = requests.post(
                f"{self.agent_url}/v1/agent/chat",
                json=payload,
                stream=True,
                timeout=120.0
            )
            
            if resp.status_code == 200:
                # 流式解析 SSE 响应
                full_text = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_str)
                            chunk = data_json.get("chunk", "")
                            if chunk:
                                full_text += chunk
                        except json.JSONDecodeError:
                            pass
                
                if full_text:
                    self.response_ready.emit(full_text)
                else:
                    self.error_occurred.emit("Agent 返回空响应，可能是模型配置问题")
            else:
                self.error_occurred.emit(f"Agent 返回错误: {resp.status_code}")
        
        except requests.exceptions.Timeout:
            self.error_occurred.emit(
                "Agent 响应超时（120秒）\n"
                "任务可能过于复杂，请简化指令后重试"
            )
        except Exception as e:
            self.error_occurred.emit(f"调用 Agent 失败: {str(e)}")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        return """你是一个 PPT 编辑助手。用户会给你当前的幻灯片数据和修改指令，你需要返回修改后的幻灯片数据。

返回格式要求：
1. 返回完整的 JSON 数据，格式为 {"slides": [...]}
2. 保持原有的数据结构
3. 只修改用户要求修改的部分
4. 如果指令不明确，保持原有数据不变

内容类型说明：
- text: 纯文本
- image: 图片（需要指定 image_source）
- flowchart: 流程图（需要指定 flowchart_data）
- icon: 图标（需要指定 icon_name）

版式说明：
- center: 居中封面
- text_only: 纯文本
- image_right: 图右文左
- image_left: 图左文右
- three_columns: 三栏对比
- two_columns: 两栏布局
- full_image: 全图背景"""
    
    def _build_user_message(self) -> str:
        """构建用户消息"""
        return f"""当前幻灯片数据：
```json
{json.dumps({"slides": self.slides_data}, ensure_ascii=False, indent=2)}
```

当前正在编辑第 {self.current_index + 1} 页幻灯片。

用户指令：{self.instruction}

请返回修改后的完整幻灯片 JSON 数据（只返回 JSON，不要其他内容）："""


class AICopilotChatWidget(QWidget):
    """AI 对话共创组件"""
    
    # 信号
    slides_updated = pyqtSignal(list)  # 幻灯片数据更新
    
    def __init__(self, agent_url: str = None, parent=None):
        super().__init__(parent)
        self.agent_url = agent_url
        self.slides_data = []
        self.current_index = -1
        self.worker = None
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
        
        layout.addWidget(self.chat_area)
        
        # 添加欢迎消息
        self._add_message("你好！我是 PPT 编辑助手。你可以用自然语言告诉我如何修改幻灯片，例如：\n\n• 把第2页的标题改为'核心优势'\n• 在第3页添加一个流程图\n• 把第1页改为图文混排", is_user=False)
    
    def _toggle_chat(self):
        """折叠/展开聊天区域"""
        is_visible = self.chat_area.isVisible()
        self.chat_area.setVisible(not is_visible)
        self.toggle_btn.setText("▲" if not is_visible else "▼")
    
    def _check_agent_health(self):
        """异步检测 Agent 服务状态"""
        self._health_checker = HealthChecker(self.agent_url)
        self._health_checker.result.connect(self._on_health_result)
        self._health_checker.start()
    
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
            json_str = None
            # 先尝试从 ```json ... ``` 代码块中提取
            code_block = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if code_block:
                block_content = code_block.group(1).strip()
                if block_content.startswith('{') or block_content.startswith('['):
                    brace_start = block_content.find('{')
                    bracket_start = block_content.find('[')
                    if brace_start != -1 and (bracket_start == -1 or brace_start < bracket_start):
                        # 用括号计数找到匹配的闭合花括号
                        depth = 0
                        for idx in range(brace_start, len(block_content)):
                            if block_content[idx] == '{':
                                depth += 1
                            elif block_content[idx] == '}':
                                depth -= 1
                                if depth == 0:
                                    json_str = block_content[brace_start:idx + 1]
                                    break
                    elif bracket_start != -1:
                        depth = 0
                        for idx in range(bracket_start, len(block_content)):
                            if block_content[idx] == '[':
                                depth += 1
                            elif block_content[idx] == ']':
                                depth -= 1
                                if depth == 0:
                                    json_str = block_content[bracket_start:idx + 1]
                                    break
            if json_str is None:
                # 尝试直接从全文中用括号计数提取
                start = response.find('{')
                if start != -1:
                    depth = 0
                    for idx in range(start, len(response)):
                        if response[idx] == '{':
                            depth += 1
                        elif response[idx] == '}':
                            depth -= 1
                            if depth == 0:
                                json_str = response[start:idx + 1]
                                break
                if json_str is None:
                    raise ValueError("无法找到 JSON 数据")
            
            data = json.loads(json_str)
            
            if 'slides' in data:
                # 更新幻灯片数据
                self.slides_data = data['slides']
                self.slides_updated.emit(self.slides_data)
                
                # 显示成功消息
                self._add_message("✅ 已更新幻灯片数据！", is_user=False)
            else:
                self._add_message("⚠️ 返回的数据格式不正确，缺少 slides 字段", is_user=False)
        
        except json.JSONDecodeError as e:
            # JSON 解析失败，显示原始响应
            self._add_message(f"⚠️ 无法解析 AI 返回的数据：{str(e)}\n\n原始响应：\n{response}", is_user=False)
        
        except Exception as e:
            self._add_message(f"⚠️ 处理失败：{str(e)}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
    
    def _on_ai_error(self, error: str):
        """AI 错误"""
        self._add_message(f"❌ {error}", is_user=False)
        
        # 恢复输入
        self.input_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
