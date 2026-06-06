"""WorkspaceV5 — Agent Workspace 2.0 (Sidebar + 5-Panel) (1000×700)"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget,
    QGraphicsDropShadowEffect, QApplication, QTextEdit,
    QLineEdit,
)

from gui.v5 import tokens as T
from gui.shared import make_panel_persistent
from gui.v5.telemetry import telemetry
from gui.v5 import bridge


class WorkspaceV5(QWidget):
    """Agent Workspace v5.0: Sidebar(180px) + 5-Panel"""

    task_changed = pyqtSignal(str)

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._user_initiated_hide = False
        self._allow_close = False
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

        # 切换到 Files/Memory/Task 时刷新数据
        if sid == "files":
            self._refresh_files()
        elif sid == "memory":
            self._refresh_memory()
        elif sid == "task":
            self._refresh_task_history()

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
        task_input = QTextEdit()
        task_input.setPlaceholderText("例如：审查支付模块安全漏洞 (功能待接入)")
        task_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QTextEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        task_input.setMaximumHeight(120)
        layout.addWidget(task_input)

        # 任务历史（占位）
        self._task_history_label = QLabel("📜 任务历史")
        self._task_history_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(self._task_history_label)

        self._task_history_list = QLabel("")
        self._task_history_list.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
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

        display = QTextEdit()
        display.setReadOnly(True)
        display.setPlainText("对话区 (功能待接入)")
        display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_ELEVATED}; color: {T.TEXT_TERTIARY};
                border: 1px solid {T.STROKE_SUBTLE}; border-radius: 8px;
                padding: 10px; font-size: {T.FONT_BODY[0]}px;
            }}
        """)
        layout.addWidget(display, stretch=1)

        input_row = QHBoxLayout()
        inp = QLineEdit()
        inp.setPlaceholderText("输入消息... (功能待接入)")
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 6px;
                padding: 6px 10px; font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        send = QPushButton("发送")
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL}; color: #000;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        input_row.addWidget(inp, stretch=1)
        input_row.addWidget(send)
        layout.addLayout(input_row)
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
                lines.append(f"  📋 {title}  ({created})")
            self._task_history_list.setText("\n".join(lines))
        else:
            self._task_history_list.setText("暂无任务历史")

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
