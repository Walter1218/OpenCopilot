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
        return """你是一个 PPT 编辑助手。优先进行局部修改，而不是重新生成整个PPT。

修改模式（按优先级排序）：

1. **局部修改**（推荐）：只修改用户指定的部分
   - 修改标题：{"action": "update", "slide_index": 1, "field": "title", "value": "新标题"}
   - 修改副标题：{"action": "update", "slide_index": 0, "field": "subtitle", "value": "新副标题"}
   - 修改版式：{"action": "update", "slide_index": 0, "field": "layout", "value": "image_right"}
   
2. **修改要点**：
   - 更新要点：{"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "新内容"}
   - 添加要点：{"action": "add_item", "slide_index": 1, "item": {"text": "新要点", "level": 0, "content_type": "text"}}
   - 删除要点：{"action": "remove_item", "slide_index": 1, "item_index": 0}
   
3. **幻灯片操作**：
   - 添加幻灯片：{"action": "add_slide", "index": 2, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": []}}
   - 删除幻灯片：{"action": "remove_slide", "index": 2}

4. **内容转换**（当用户要求转换为图表/表格时）：
   - 转为表格：{"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "标题", "columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}
   - 转为柱状图：{"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "标题", "labels": ["标签1", "标签2"], "datasets": [{"label": "系列", "data": [10, 20], "color": "#007bff"}]}}}
   - 转为折线图：同上，chart_type 改为 "line"
   - 转为饼图：同上，chart_type 改为 "pie"

5. **全局修改**（仅当用户明确要求"重新生成"时使用）：
   - 返回 {"slides": [...]}

内容类型：text / image / flowchart / icon / table / chart
版式类型：center / text_only / image_right / image_left / three_columns / two_columns / full_image"""
    
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
