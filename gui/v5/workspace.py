"""WorkspaceV5 — Agent Workspace 2.0 (Sidebar + 5-Panel) (1000×700)"""
import re
import uuid
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget,
    QGraphicsDropShadowEffect, QApplication, QTextEdit,
    QLineEdit, QComboBox,
)

from gui.v5 import tokens as T
from gui.shared import make_panel_persistent
from gui.v5.telemetry import telemetry
from gui.v5 import bridge
from gui.v5.agent_worker import V5AgentWorker


# =============================================================================
# Action Type 选项 + 意图检测
# =============================================================================

# (action_type_id, 显示标签, tooltip)
ACTION_TYPE_OPTIONS = [
    ("auto",         "🤖 Auto",        "自动检测意图"),
    ("chat",         "💬 Chat",        "自由对话"),
    ("research",     "🔎 Research",    "联网调研+报告"),
    ("ppt",          "📊 PPT",         "生成 PPT 大纲"),
    ("translate",    "🌐 Translate",   "翻译文本"),
    ("explain",      "🔍 Explain",     "解释代码/文本"),
    ("fix",          "🔧 Fix",         "修复代码问题"),
    ("polish",       "✨ Polish",      "润色优化文本"),
    ("code_review",  "📝 Review",      "代码审查"),
]

# 意图检测关键词映射：action_type → [(pattern, weight), ...]
# weight 用于多意图命中时取最高分
_INTENT_PATTERNS = {
    "research": [
        (r"调研|research|调查报告|最新进展|技术趋势|行业分析", 3),
        (r"帮我查一下|搜索一下|联网.*搜|web search|online search", 3),
        (r"最新.*技术|前沿.*研究|state.of.the.art|SOTA|论文.*综述", 4),
        (r"以.*md.*文件|输出.*报告|生成.*文档.*形式|写.*调研报告", 4),
    ],
    "ppt": [
        (r"PPT|ppt|幻灯片|演示文稿|presentation|slides|slide deck", 3),
        (r"做成\s*PPT|生成\s*PPT|写.*PPT|做个.*PPT|制作.*幻灯片|生成.*演示", 5),
        (r"大纲.*PPT|PPT.*大纲|outline.*ppt", 4),
    ],
    "translate": [
        (r"翻译|translate|translation|译成|译?为|翻译成", 3),
        (r"中\s*→\s*英|英\s*→\s*中|en\s*→\s*zh|zh\s*→\s*en|中文.*英文|英文.*中文", 4),
        (r"翻译.*成|translate.*to|convert.*language", 3),
    ],
    "explain": [
        (r"解释|explain|explanation|什么意思|怎么理解|分析一下", 2),
        (r"这段代码|这个函数|这个类|this code|this function", 3),
        (r"帮我看看.*代码|解释一下|说明一下.*原理", 3),
    ],
    "fix": [
        (r"修复|fix|debug|排错|报错|出错了", 4),
        (r"bug|error|异常|traceback", 3),
        (r"代码.*有.*问题|这段.*不对|编译.*失败|运行.*报错", 4),
        (r"TypeError|NameError|SyntaxError|KeyError|ValueError|ImportError", 5),
    ],
    "polish": [
        (r"润色|polish|优化.*文本|改写|美化.*文字|让.*更.*专业|提升.*表达", 2),
        (r"文笔|措辞|表述.*优化|语言.*流畅|更.*通顺", 3),
    ],
    "code_review": [
        (r"代码审查|code review|review|CR|审查.*代码|检查一下.*代码", 3),
        (r"代码质量|代码规范|best practice|安全漏洞|性能.*问题", 3),
    ],
}


def _detect_action_type(text: str) -> tuple:
    """根据用户输入文本检测意图，返回 (action_type, confidence, matched_keywords)

    Returns:
        (action_type, confidence, matched_keywords):
            action_type: 检测到的 action_type（如 'ppt'/'translate' 等）
            confidence: 置信度 0.0-1.0
            matched_keywords: 命中的关键词列表（用于埋点和展示）
    """
    text_lower = text.lower().strip()
    if not text_lower:
        return "chat", 0.0, []

    scores = {}        # action_type → max_weight
    matched = {}       # action_type → [matched_keywords]

    for action_type, patterns in _INTENT_PATTERNS.items():
        max_weight = 0
        hits = []
        for pattern, weight in patterns:
            m = re.search(pattern, text_lower, re.IGNORECASE)
            if m:
                max_weight = max(max_weight, weight)
                hits.append(m.group(0))
        if hits:
            scores[action_type] = max_weight
            matched[action_type] = hits

    if not scores:
        return "chat", 0.5, []

    # 取最高分意图
    best_action = max(scores, key=scores.get)
    best_score = scores[best_action]
    # 归一化到 0-1（最大 weight=5 → confidence=1.0）
    confidence = min(best_score / 5.0, 1.0)
    return best_action, round(confidence, 2), matched.get(best_action, [])


class WorkspaceV5(QWidget):
    """Agent Workspace v5.0: Sidebar(180px) + 5-Panel"""

    task_changed = pyqtSignal(str)

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._user_initiated_hide = False
        self._allow_close = False
        # Chat 状态
        self._session_id = telemetry().new_session_id()
        self._agent_worker = None   # 当前运行的 Chat V5AgentWorker
        self._chat_stream_pos = 0   # 流式输出起始光标位置
        self._llm_ctx = None        # LLM trace context（llm_start 返回）
        self._chunk_count = 0       # 当前对话 chunk 计数器
        # Task 状态
        self._current_task = ""
        self._init_ui()
        telemetry().window_event("V5_WS_CREATE", "workspace")

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.resize(*T.WINDOW_WORKSPACE)
        self.setMinimumSize(*T.WINDOW_WORKSPACE_MIN)

        # 外层 Frame
        self._frame = QFrame(self)
        self._frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_PRIMARY};
                border-radius: {T.FRAME_RADIUS}px;
                border: 1.5px solid {T.STROKE_BORDER};
            }}
        """)
        self._frame.resize(T.WINDOW_WORKSPACE[0] - 20, T.WINDOW_WORKSPACE[1] - 20)
        self._frame.move(T.FRAME_MARGIN, T.FRAME_MARGIN)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(T.SHADOW_BLUR)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self._frame.setGraphicsEffect(shadow)

        outer_layout = QHBoxLayout(self._frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ── 左侧 Sidebar (180px) ──
        sidebar = QFrame()
        sidebar.setFixedWidth(T.SIDEBAR_WIDTH)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-right: 1px solid {T.STROKE_SUBTLE};
                border-top-left-radius: {T.FRAME_RADIUS}px;
                border-bottom-left-radius: {T.FRAME_RADIUS}px;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 12)
        sidebar_layout.setSpacing(2)

        # Logo
        logo = QLabel("🤖 Agent Workspace")
        logo.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-weight: bold; "
            f"font-size: {T.FONT_TITLE[0]}px; padding: 0 12px 12px 12px; "
            "background: transparent; border: none;"
        )
        logo.setWordWrap(True)
        sidebar_layout.addWidget(logo)

        # 导航按钮
        self._nav_buttons = {}
        for idx, (sid, label, _tip) in enumerate(T.WORKSPACE_NAV_ITEMS):
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(_tip)
            btn.setStyleSheet(self._nav_btn_style(selected=(idx == 0)))
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons[sid] = btn

        sidebar_layout.addStretch()

        # 底部按钮行
        bottom_row = QHBoxLayout()

        settings_btn = QPushButton("  ⚙️ Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {T.TEXT_TERTIARY}; "
            f"border: none; padding: 8px 12px; font-size: {T.FONT_BODY[0]}px; text-align: left; }}"
            f"QPushButton:hover {{ color: {T.TEXT_PRIMARY}; }}"
        )
        settings_btn.clicked.connect(lambda: self.nav.open_settings())
        bottom_row.addWidget(settings_btn)

        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("关闭 Workspace")
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {T.TEXT_SECONDARY}; "
            f"border: none; padding: 8px 12px; font-size: {T.FONT_BODY[0]}px; }}"
            f"QPushButton:hover {{ color: #ff5555; }}"
        )
        close_btn.clicked.connect(self._close_workspace)
        bottom_row.addWidget(close_btn)

        sidebar_layout.addLayout(bottom_row)

        outer_layout.addWidget(sidebar)

        # ── 右侧 Content Area ──
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(8)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; border: none; }")

        # Panel 1: Task
        self._stack.addWidget(self._create_task_panel())
        # Panel 2: Chat
        self._stack.addWidget(self._create_chat_panel())
        # Panel 3: Files
        self._stack.addWidget(self._create_files_panel())
        # Panel 4: Memory
        self._stack.addWidget(self._create_memory_panel())
        # Panel 5: Settings
        self._stack.addWidget(self._create_settings_panel())

        content_layout.addWidget(self._stack, stretch=1)
        outer_layout.addWidget(content_area, stretch=1)

    # =========================================================================
    # 事件
    # =========================================================================

    def showEvent(self, event):
        telemetry().window_event("V5_WS_SHOW", "workspace")
        super().showEvent(event)

    def _close_workspace(self):
        """关闭 Workspace 窗口"""
        telemetry().window_event("V5_WS_CLOSE", "workspace")
        self._allow_close = True
        self.close()

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            self.hide()
            event.ignore()

    def _on_nav_clicked(self, index: int):
        self._stack.setCurrentIndex(index)
        sid = T.WORKSPACE_NAV_ITEMS[index][0]
        t = telemetry()
        t.emit("V5_WS_PANEL_SWITCH", panel_id=sid, panel_index=index)
        for s, btn in self._nav_buttons.items():
            btn.setChecked(s == sid)
            btn.setStyleSheet(self._nav_btn_style(selected=(s == sid)))

        # 切换到 Files/Memory/Task 时刷新数据；Chat 面板时聚焦输入框
        if sid == "files":
            self._refresh_files()
        elif sid == "memory":
            self._refresh_memory()
        elif sid == "task":
            self._refresh_task_history()
        elif sid == "chat":
            self._chat_input.setFocus()

    # =========================================================================
    # 面板创建
    # =========================================================================

    def _create_task_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel("📋 Task — 任务定义与管理")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        desc = QLabel("定义当前任务背景，任务上下文将自动注入到 Smart Copilot 的所有 AI 请求中。")
        desc.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            "background: transparent; border: none;"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Task 输入
        self._task_input = QTextEdit()
        self._task_input.setPlaceholderText("例如：审查支付模块安全漏洞，重点关注 SQL 注入和 XSS 风险...")
        self._task_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QTextEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        self._task_input.setMaximumHeight(140)
        layout.addWidget(self._task_input)

        # 操作按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._save_task_btn = QPushButton("✅ 设定任务")
        self._save_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_task_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL}; color: #000;
                border-radius: 6px; padding: 6px 16px; font-weight: bold;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {T.ACCENT_CONTROL}; }}
        """)
        self._save_task_btn.clicked.connect(self._on_save_task)
        btn_row.addWidget(self._save_task_btn)

        self._clear_task_btn = QPushButton("🗑 清除任务")
        self._clear_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_task_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 6px 14px; font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.BG_HOVER}; color: {T.TEXT_PRIMARY}; }}
        """)
        self._clear_task_btn.clicked.connect(self._on_clear_task)
        btn_row.addWidget(self._clear_task_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 任务状态标签
        self._task_status_label = QLabel("")
        self._task_status_label.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_BODY[0]}px; "
            f"background: {T.BG_ELEVATED}; border-radius: 6px; padding: 6px 10px;"
        )
        self._task_status_label.setWordWrap(True)
        self._task_status_label.hide()
        layout.addWidget(self._task_status_label)

        # 任务历史
        self._task_history_label = QLabel("📜 任务历史")
        self._task_history_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none; margin-top: 8px;"
        )
        layout.addWidget(self._task_history_label)

        self._task_history_list = QLabel("")
        self._task_history_list.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: {T.BG_ELEVATED}; border-radius: 6px; padding: 6px 10px;"
        )
        self._task_history_list.setWordWrap(True)
        layout.addWidget(self._task_history_list)

        layout.addStretch()
        return panel

    def _create_chat_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        header = QLabel("💬 Chat — 连续对话")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        # 会话状态行
        status_row = QHBoxLayout()
        self._chat_session_label = QLabel(f"📌 会话: {self._session_id[:8]}...")
        self._chat_session_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )
        status_row.addWidget(self._chat_session_label)
        status_row.addStretch()

        new_session_btn = QPushButton("+ 新会话")
        new_session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_session_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {T.TEXT_ACCENT};
                border: none; font-size: {T.FONT_CAPTION[0]}px; padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {T.ACCENT_HOVER}; text-decoration: underline; }}
        """)
        new_session_btn.clicked.connect(self._on_new_chat_session)
        status_row.addWidget(new_session_btn)
        layout.addLayout(status_row)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_SUBTLE}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px; line-height: 1.6;
            }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 60); border-radius: 3px;
            }}
        """)
        layout.addWidget(self._chat_display, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        # Action Type 选择器
        self._action_combo = QComboBox()
        self._action_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_combo.setToolTip("选择能力模式（Auto = 自动检测意图）")
        for action_id, label, tip in ACTION_TYPE_OPTIONS:
            self._action_combo.addItem(label, action_id)
            # 设置 item tooltip
            idx = self._action_combo.count() - 1
            self._action_combo.setItemData(idx, tip, Qt.ItemDataRole.ToolTipRole)
        self._action_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 4px 8px; font-size: {T.FONT_CAPTION[0]}px;
                min-width: 90px; max-width: 130px;
            }}
            QComboBox::drop-down {{
                border: none; width: 20px;
                subcontrol-origin: padding; subcontrol-position: top right;
            }}
            QComboBox QAbstractItemView {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; selection-background-color: {T.BG_SELECTED};
            }}
        """)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("输入消息，按 Enter 发送...（Auto 模式自动检测意图）")
        self._chat_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 6px 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        self._chat_input.returnPressed.connect(self._on_chat_send)

        self._chat_send_btn = QPushButton("发送")
        self._chat_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chat_send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL}; color: #000;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        self._chat_send_btn.clicked.connect(self._on_chat_send)

        input_row.addWidget(self._action_combo)
        input_row.addWidget(self._chat_input, stretch=1)
        input_row.addWidget(self._chat_send_btn)
        layout.addLayout(input_row)

        # 意图检测状态提示（显示 Auto 模式下检测到的 action type）
        self._intent_hint_label = QLabel("")
        self._intent_hint_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none; padding: 0 4px;"
        )
        self._intent_hint_label.hide()
        layout.addWidget(self._intent_hint_label)

        return panel

    def _create_placeholder_panel(self, title: str, content: str) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel(title)
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        text = QLabel(content)
        text.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_BODY[0]}px; "
            "background: transparent; border: none; line-height: 1.6;"
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
        return panel

    def _create_files_panel(self) -> QWidget:
        """Files 面板 — 展示最近文件列表"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel("📁 Files — 最近文件")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        self._files_content = QTextEdit()
        self._files_content.setReadOnly(True)
        self._files_content.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_SUBTLE}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px;
            }}
        """)
        self._files_content.setPlainText("加载中...")
        layout.addWidget(self._files_content, stretch=1)

        # 初始加载
        self._refresh_files()
        return panel

    def _create_memory_panel(self) -> QWidget:
        """Memory 面板 — 知识图谱 / 翻译记忆 / 术语库统计"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel("🧠 Memory — 知识记忆")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        self._memory_content = QTextEdit()
        self._memory_content.setReadOnly(True)
        self._memory_content.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_SUBTLE}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px;
            }}
        """)
        self._memory_content.setPlainText("加载中...")
        layout.addWidget(self._memory_content, stretch=1)

        # 初始加载
        self._refresh_memory()
        return panel

    def _create_settings_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel("⚙️ Settings — 引擎 / 主题 / 快捷键 / 角色")
        header.setStyleSheet(self._header_style())
        layout.addWidget(header)

        # 四宫格卡片
        grid = QHBoxLayout()
        grid.setSpacing(10)
        for section_id, label, tip in [
            ("engine", "🔌 Engine", "Cloud/Local LLM"),
            ("appearance", "🎨 Theme", "Dark/Light/System"),
            ("shortcuts", "⌨️ Shortcuts", "快捷键绑定"),
            ("advanced", "🔧 Advanced", "高级配置"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {T.BG_ELEVATED};
                    border-radius: 8px;
                    border: 1px solid {T.STROKE_SUBTLE};
                }}
                QFrame:hover {{
                    border: 1px solid {T.STROKE_BORDER};
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)

            card_label = QLabel(label)
            card_label.setStyleSheet(
                f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
                f"font-size: {T.FONT_BODY[0]}px; background: transparent; border: none;"
            )
            card_tip = QLabel(tip)
            card_tip.setStyleSheet(
                f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )

            open_btn = QPushButton("配置 →")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {T.TEXT_ACCENT}; "
                f"border: none; font-size: {T.FONT_CAPTION[0]}px; padding: 2px 0; }}"
                f"QPushButton:hover {{ color: {T.ACCENT_HOVER}; }}"
            )
            open_btn.clicked.connect(lambda checked, sid=section_id: self.nav.open_settings(sid))

            card_layout.addWidget(card_label)
            card_layout.addWidget(card_tip)
            card_layout.addWidget(open_btn)
            grid.addWidget(card)

        layout.addLayout(grid)
        layout.addStretch()
        return panel

    # =========================================================================
    # 数据刷新
    # =========================================================================

    def _refresh_files(self):
        """刷新最近文件列表"""
        files = bridge.get_recent_files(limit=20)
        if files:
            lines = [f"最近文件 ({len(files)} 个):\n"]
            for f in files:
                name = f.get("name", "?")
                size = f.get("size", 0)
                modified = f.get("modified", "")[:16]
                size_str = f"{size / 1024:.1f}KB" if size < 1048576 else f"{size / 1048576:.1f}MB"
                lines.append(f"  📄 {name}  ({size_str}, {modified})")
            self._files_content.setPlainText("\n".join(lines))
        else:
            self._files_content.setPlainText("暂无最近文件。\n\n使用 Work Tab 的文件上传功能添加文件。")

    def _refresh_memory(self):
        """刷新知识记忆统计"""
        stats = bridge.get_memory_stats()
        lines = ["知识记忆统计:\n"]
        kg = stats.get("knowledge_graph", {})
        lines.append(f"📊 知识图谱: {kg.get('entities', 0)} 实体 / {kg.get('relations', 0)} 关系 ({kg.get('status', '?')})")
        tm = stats.get("translation_memory", {})
        lines.append(f"🌐 翻译记忆: {tm.get('entries', 0)} 条 ({tm.get('status', '?')})")
        gl = stats.get("glossary", {})
        lines.append(f"📖 术语库: {gl.get('terms', 0)} 条 ({gl.get('status', '?')})")
        self._memory_content.setPlainText("\n".join(lines))

    def _refresh_task_history(self):
        """刷新任务历史"""
        tasks = bridge.get_task_history(limit=10)
        if tasks:
            lines = [f"最近 {len(tasks)} 个任务:\n"]
            for t in tasks:
                title = t.get("title", t.get("description", ""))[:40]
                created = t.get("created_at", "")[:16]
                status = "✅" if t.get("status", "") == "done" else "⏳"
                lines.append(f"  {status} {title}  ({created})")
            self._task_history_list.setText("\n".join(lines))
        else:
            self._task_history_list.setText("暂无任务历史")

    # =========================================================================
    # Chat — AI 对话能力接入
    # =========================================================================

    def _on_chat_send(self):
        """发送消息 → 意图检测/选择 → 动态路由 action_type → V5AgentWorker"""
        text = self._chat_input.text().strip()
        if not text:
            return

        # 如果已有 Worker 在运行，先停止（发送按钮变为停止功能）
        if self._agent_worker is not None and self._agent_worker.isRunning():
            self._agent_worker.stop()
            self._agent_worker.finished_signal.connect(
                lambda _: self._safely_reset_worker()
            )
            self._chat_send_btn.setText("发送")
            telemetry().emit("V5_WS_CHAT_STOP", session_id=self._session_id,
                             worker_id=getattr(self._agent_worker, '_wid', '?'))
            return

        # ── 解析 action_type：优先用户显式选择，否则走意图检测 ──
        selected_id = self._action_combo.currentData()  # action_type_id
        action_source = "user_selected"
        detected_keywords = []
        intent_confidence = 0.0

        if selected_id == "auto":
            resolved_action, intent_confidence, detected_keywords = _detect_action_type(text)
            action_source = "auto_detected"
            # 显示意图检测提示
            if resolved_action != "chat" and detected_keywords:
                hint = f"🤖 检测到意图: {resolved_action} (置信度 {intent_confidence:.0%}, 命中: {', '.join(detected_keywords[:3])})"
                self._intent_hint_label.setText(hint)
                self._intent_hint_label.show()
            else:
                self._intent_hint_label.hide()
        else:
            resolved_action = selected_id
            self._intent_hint_label.hide()

        t = telemetry()

        # LLM 全链路追踪：记录开始时间 + 生成 trace_id
        self._llm_ctx = t.llm_start(
            source_tab="WS",
            action_type=resolved_action,
            session_id=self._session_id,
            text_len=len(text),
        )
        self._chunk_count = 0

        t.emit("V5_WS_CHAT_SEND",
               text_len=len(text),
               prompt_len=len(text),
               session_id=self._session_id,
               action_type=resolved_action,
               action_source=action_source,
               intent_confidence=intent_confidence,
               detected_keywords=",".join(detected_keywords),
               has_task=bool(self._current_task),
               context_source="chat",
               trace_id=self._llm_ctx["trace_id"])
        self._chat_input.clear()

        # 用户消息 echo（显示路由结果）
        if action_source == "auto_detected" and resolved_action != "chat":
            self._append_chat_message("系统",
                f"🤖 自动路由 → **{resolved_action}** 模式 (置信度 {intent_confidence:.0%})")
        self._append_chat_message("你", text)
        # AI 占位
        self._append_chat_message("AI", "🔄 思考中...")
        # 记录流式替换起始位置
        self._chat_stream_pos = self._chat_display.textCursor().position()

        # 构建 context_meta：注入当前任务上下文
        context_meta = {"context_source": "workspace_chat"}
        if self._current_task:
            context_meta["task"] = self._current_task
            context_meta["source_text"] = self._current_task
            context_meta["source_type"] = "workspace_task"

        # PPT 模式追加特殊 context_meta（与 CapabilityRouter/PPT persona 对齐）
        if resolved_action == "ppt":
            context_meta["ppt_mode"] = True
            context_meta["output_format"] = "json_slides"

        # Research 模式：开启联网搜索 + 调研报告 context
        enable_ws = False
        if resolved_action == "research":
            enable_ws = True
            context_meta["research_mode"] = True
            context_meta["output_format"] = "markdown_report"

        self._chat_send_btn.setText("停止")
        self._agent_worker = V5AgentWorker(
            prompt=text,
            action_type=resolved_action,
            session_id=self._session_id,
            context_source="chat",
            context_meta=context_meta,
            is_new_task=(resolved_action != "chat"),
            enable_web_search=enable_ws,
        )
        self._agent_worker.text_updated.connect(self._on_ai_chunk)
        self._agent_worker.finished_signal.connect(self._on_ai_finished)
        self._agent_worker.error_signal.connect(self._on_ai_error)
        self._agent_worker.start()
        print(f"[v5] Workspace Chat 启动 | session={self._session_id[:8]} | "
              f"action={resolved_action} ({action_source}) | "
              f"trace={self._llm_ctx['trace_id'][:8]} | "
              f"task={bool(self._current_task)} | prompt_len={len(text)}")

    def _on_ai_chunk(self, text: str):
        """AI 流式 chunk 回调 — 增量替换最后一条 AI 消息 + 关键节点埋点"""
        self._chunk_count += 1
        self._update_last_ai_message(text)
        # 每 10 个 chunk 打一次链路埋点（避免每条都打）
        if self._chunk_count % 10 == 0 and self._llm_ctx:
            telemetry().llm_chunk(
                self._llm_ctx,
                source_tab="WS",
                chunk_count=self._chunk_count,
                output_len=len(text),
            )

    def _on_ai_finished(self, full_text: str):
        """AI 完成回调 — 重置按钮 + 保存历史 + LLM 链路闭环"""
        self._chat_send_btn.setText("发送")
        self._safely_reset_worker()
        t = telemetry()
        # LLM 全链路追踪：done（含 elapsed_ms 耗时）
        if self._llm_ctx:
            t.llm_done(
                self._llm_ctx,
                source_tab="WS",
                chunk_count=self._chunk_count,
                output_len=len(full_text),
            )
        else:
            t.emit("V5_WS_CHAT_DONE",
                   session_id=self._session_id,
                   output_len=len(full_text),
                   chunk_count=self._chunk_count)
        print(f"[v5] Workspace Chat 完成 | chunks={self._chunk_count} | "
              f"output={len(full_text)} 字符")
        # 持久化到本地历史
        self._save_chat_history("assistant", full_text)

    def _on_ai_error(self, error_msg: str):
        """AI 错误回调 — 展示错误信息 + LLM 链路 error 闭环"""
        self._chat_send_btn.setText("发送")
        self._update_last_ai_message(f"❌ 发生错误: {error_msg}")
        self._safely_reset_worker()
        t = telemetry()
        # LLM 全链路追踪：error（含耗时 + context_source）
        if self._llm_ctx:
            t.llm_error(
                self._llm_ctx,
                source_tab="WS",
                error_msg=error_msg,
            )
        else:
            t.emit("V5_WS_CHAT_ERROR",
                   session_id=self._session_id,
                   error_msg=error_msg,
                   context_source="chat")
        print(f"[v5] Workspace Chat 错误 | error={error_msg}")

    def _update_last_ai_message(self, text: str):
        """流式更新最后一条 AI 消息（增量替换，不重绘全部）"""
        cursor = self._chat_display.textCursor()
        cursor.setPosition(self._chat_stream_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        safe_text = (text
                     .replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('\n', '<br>'))
        color = T.STATUS_ONLINE
        cursor.insertHtml(f'<b style="color:{color};">AI:</b> {safe_text}')
        # 自动滚动到底部
        scrollbar = self._chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_chat_message(self, role: str, text: str):
        """追加一条聊天消息到显示区"""
        color_map = {
            "你": T.TEXT_ACCENT,
            "AI": T.STATUS_ONLINE,
            "系统": T.TEXT_TERTIARY,
        }
        color = color_map.get(role, T.TEXT_SECONDARY)
        safe_text = (text
                     .replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('\n', '<br>'))
        html = f'<b style="color:{color};">{role}:</b> {safe_text}'
        self._chat_display.append(html)

    def _safely_reset_worker(self):
        """安全重置 Worker：等待线程结束后再清理引用"""
        if self._agent_worker is not None:
            worker = self._agent_worker
            self._agent_worker = None
            if worker.isRunning():
                worker.finished.connect(worker.deleteLater)
                if not worker.wait(3000):
                    worker.terminate()
                    worker.wait(1000)
            else:
                worker.deleteLater()

    def _on_new_chat_session(self):
        """新建对话会话 — 清空历史、重置 session_id"""
        self._session_id = telemetry().new_session_id()
        self._chat_display.clear()
        self._append_chat_message("系统", "新会话已开始，输入消息开始对话。")
        self._chat_session_label.setText(f"📌 会话: {self._session_id[:8]}...")
        telemetry().emit("V5_WS_CHAT_NEW_SESSION", session_id=self._session_id)
        print(f"[v5] Workspace Chat: 新建会话 → {self._session_id[:8]}")

    def _save_chat_history(self, role: str, text: str):
        """持久化聊天历史到本地文件"""
        try:
            import json, os
            from datetime import datetime
            history_dir = os.path.expanduser("~/.opencopilot/chat_history")
            os.makedirs(history_dir, exist_ok=True)
            history_file = os.path.join(history_dir, f"{self._session_id}.json")
            history = []
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append({
                "role": role, "text": text,
                "timestamp": datetime.now().isoformat(),
            })
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[v5] Workspace Chat: 保存历史失败 → {e}")

    # =========================================================================
    # Task — 任务定义与上下文注入
    # =========================================================================

    def _on_save_task(self):
        """保存当前任务 → emit task_changed 信号，注入后续所有 AI 请求上下文"""
        task_text = self._task_input.toPlainText().strip()
        if not task_text:
            self._task_status_label.setText("⚠️ 请输入任务描述后再设定")
            self._task_status_label.setStyleSheet(
                f"color: #ffa500; font-size: {T.FONT_BODY[0]}px; "
                f"background: {T.BG_ELEVATED}; border-radius: 6px; padding: 6px 10px;"
            )
            self._task_status_label.show()
            telemetry().emit("V5_WS_TASK_SAVE_EMPTY",
                             session_id=self._session_id,
                             context_source="workspace_task")
            return

        self._current_task = task_text
        # emit 信号，通知 CopilotManager / Nav 更新全局 task 上下文
        self.task_changed.emit(task_text)

        # 显示状态
        preview = task_text[:50] + ("…" if len(task_text) > 50 else "")
        self._task_status_label.setText(f"✅ 任务已激活: {preview}  ({len(task_text)} 字符)")
        self._task_status_label.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_BODY[0]}px; "
            f"background: {T.BG_ELEVATED}; border-radius: 6px; padding: 6px 10px;"
        )
        self._task_status_label.show()

        t = telemetry()
        t.emit("V5_WS_TASK_SAVE",
               task_len=len(task_text),
               task_preview=preview,
               session_id=self._session_id,
               context_source="workspace_task")
        print(f"[v5] Workspace Task 保存 | task={preview} | len={len(task_text)}")

        # 持久化到 smart_copilot_api.tasks_storage（可选，记录历史）
        try:
            from smart_copilot_api import tasks_storage
            task_id = str(uuid.uuid4())[:8]
            tasks_storage[task_id] = {
                "id": task_id,
                "title": task_text[:60],
                "description": task_text,
                "status": "active",
                "session_id": self._session_id,
                "created_at": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"[v5] Workspace Task: 持久化失败（可忽略）→ {e}")

        # 刷新任务历史
        self._refresh_task_history()

    def _on_clear_task(self):
        """清除当前任务上下文"""
        prev_len = len(self._current_task)
        self._current_task = ""
        self._task_input.clear()
        self.task_changed.emit("")
        self._task_status_label.setText("🗑 任务已清除")
        self._task_status_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: {T.BG_ELEVATED}; border-radius: 6px; padding: 6px 10px;"
        )
        self._task_status_label.show()
        telemetry().emit("V5_WS_TASK_CLEAR",
                         session_id=self._session_id,
                         prev_task_len=prev_len,
                         context_source="workspace_task")
        print(f"[v5] Workspace Task: 任务已清除 | prev_len={prev_len}")

    # =========================================================================
    # 样式
    # =========================================================================

    @staticmethod
    def _nav_btn_style(selected=False):
        if selected:
            return (
                f"QPushButton {{ background: {T.BG_SELECTED}; color: {T.TEXT_ACCENT}; "
                f"border: none; border-radius: 6px; padding: 8px 12px; "
                f"font-size: {T.FONT_BODY[0]}px; font-weight: bold; text-align: left; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {T.TEXT_SECONDARY}; "
            f"border: none; border-radius: 6px; padding: 8px 12px; "
            f"font-size: {T.FONT_BODY[0]}px; text-align: left; }}"
            f"QPushButton:hover {{ background: {T.BG_HOVER}; color: {T.TEXT_PRIMARY}; }}"
        )

    @staticmethod
    def _header_style():
        return (
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: 16px; background: transparent; border: none;"
        )
