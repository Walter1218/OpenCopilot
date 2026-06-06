"""WorkTabV5 — Work Tab 界面壳

布局: Context Header → Context Strip → Primary Actions → Secondary Actions
      → Result Area → Action Bar
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QApplication,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge


class WorkTabV5(QWidget):
    """Work Tab: 快速操作（上下文感知 + Primary/Secondary 按钮分层）"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._current_source = "selection"
        self._selected_text = ""  # 当前数据源获取的文本
        self._session_id = telemetry().new_session_id()
        self._llm_ctx = None  # LLM trace context (active request)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        # ── Context Header ──
        self._header = QLabel(self)
        self._header.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: {T.BG_ELEVATED}; border-radius: 6px; "
            f"padding: 5px 10px; border: 1px solid {T.STROKE_SUBTLE};"
        )
        self._header.setText("📎 [VS Code] main.py · Line 42  ● Online")
        layout.addWidget(self._header)

        # ── Context Strip（5 个 toggle 按钮）──
        strip_layout = QHBoxLayout()
        strip_layout.setContentsMargins(0, 0, 0, 0)
        strip_layout.setSpacing(4)
        self._strip_buttons = {}
        for source_id, label, _tip in T.CONTEXT_SOURCES:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(_tip)
            is_default = (source_id == "selection")
            btn.setChecked(is_default)
            btn.setStyleSheet(self._strip_btn_style(selected=is_default))
            btn.clicked.connect(lambda checked, sid=source_id: self._on_strip_clicked(sid))
            strip_layout.addWidget(btn)
            self._strip_buttons[source_id] = btn
        strip_layout.addStretch()
        layout.addLayout(strip_layout)

        # ── Primary Actions（3 个大填充按钮）──
        primary_layout = QHBoxLayout()
        primary_layout.setSpacing(8)
        primary_layout.setContentsMargins(0, 4, 0, 0)
        for action_id, label, tip in T.PRIMARY_ACTIONS:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(self._primary_btn_style())
            btn.setMinimumHeight(T.BTN_MEDIUM_HEIGHT)
            btn.clicked.connect(lambda checked, aid=action_id: self._on_action(aid))
            primary_layout.addWidget(btn)
        primary_layout.addStretch()
        layout.addLayout(primary_layout)

        # ── Secondary Actions（3 个小描边按钮）──
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(6)
        for action_id, label, tip in T.SECONDARY_ACTIONS:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(self._secondary_btn_style())
            btn.setMinimumHeight(T.BTN_SMALL_HEIGHT)
            btn.clicked.connect(lambda checked, aid=action_id: self._on_action(aid))
            secondary_layout.addWidget(btn)
        secondary_layout.addStretch()
        layout.addLayout(secondary_layout)

        # ── Result Area ──
        self._result_area = QTextEdit()
        self._result_area.setReadOnly(True)
        self._result_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._result_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {T.TEXT_PRIMARY};
                font-size: {T.FONT_BODY[0]}px;
                border: none; line-height: 1.5;
            }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 60); border-radius: 3px;
            }}
        """)
        self._result_area.setPlainText(
            "✨ Smart Copilot v5.0 已就绪。\n\n"
            "选中内容后双击右键即可使用。\n"
            "支持 Explain / Fix / Polish 等快捷操作。"
        )
        layout.addWidget(self._result_area, stretch=1)

        # ── Action Bar ──
        action_bar = QHBoxLayout()
        action_bar.addStretch()
        for label, tip, color in [
            ("📋 Copy", "复制结果", T.BTN_ACTION_BG),
            ("💾 Export PPT", "导出为 PPT", T.BTN_ACTION_BG),
            ("📝 Apply", "应用到 IDE", T.BTN_ACTION_BG),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(self._action_btn_style(color))
            btn.clicked.connect(lambda checked, l=label: self._on_action_bar(l))
            action_bar.addWidget(btn)
        layout.addLayout(action_bar)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def set_context_text(self, text: str):
        """设置当前上下文文本（由 SmartCopilot 调用）"""
        self._selected_text = text
        t = telemetry()
        t.emit("V5_WORK_SET_CONTEXT", text_len=len(text),
               session_id=self._session_id)
        if text:
            preview = text[:120] + ("…" if len(text) > 120 else "")
            char_count = len(text)
            self._header.setText(f"📎 [{self._current_source}] {char_count} 字符")
            self._result_area.setPlainText(
                f"📄 已获取内容（{char_count} 字符）:\n\n{preview}\n\n"
                f"👇 点击上方操作按钮进行处理。"
            )

    # =========================================================================
    # 事件处理（壳 — 仅显示占位反馈）
    # =========================================================================

    def _on_strip_clicked(self, source_id: str):
        """Context Strip 切换 → 从 Bridge 获取上下文"""
        t = telemetry()
        t.emit("V5_WORK_STRIP_SWITCH", source_id=source_id,
               session_id=self._session_id)
        self._current_source = source_id
        for sid, btn in self._strip_buttons.items():
            btn.setChecked(sid == source_id)
            btn.setStyleSheet(self._strip_btn_style(selected=(sid == source_id)))

        # Bridge: 获取数据源内容
        source_labels = {s[0]: s[1] for s in T.CONTEXT_SOURCES}
        result = bridge.fetch_context(source_id)
        self._selected_text = result.get("text", "")
        status = result.get("status", "")
        char_count = len(self._selected_text)

        label = source_labels.get(source_id, source_id)
        if char_count > 0:
            app_name = result.get("app_name", "")
            self._header.setText(
                f"📎 [{label}] {char_count} 字符"
                + (f" · {app_name}" if app_name else "")
                + f"  ({status})"
            )
        else:
            self._header.setText(f"📎 [{label}] 暂无内容  ({status})")
        print(f"[v5] WorkTab: 数据源 {source_id} → {char_count} 字符, status={status}")

    def _on_action(self, action_id: str):
        """Primary/Secondary 按钮点击 → 非AI操作直接处理，AI操作标记TODO"""
        t = telemetry()
        self._llm_ctx = t.llm_start(
            source_tab="WORK",
            action_type=action_id,
            session_id=self._session_id,
            text_len=len(self._selected_text),
        )
        t.action_event("V5_WORK_ACTION", action_id=action_id,
                       source=self._current_source,
                       session_id=self._session_id)

        if action_id == "more":
            # 非AI: 展示 More 操作列表
            actions = bridge.get_more_actions()
            lines = [f"可用操作 ({len(actions)} 项):", ""]
            for a in actions:
                lines.append(f"  {a['label']}  — {a['description']}")
            self._result_area.setPlainText("\n".join(lines))
            return

        # AI 操作：标记待接入，给出视觉反馈
        char_count = len(self._selected_text)
        if char_count > 0:
            preview = self._selected_text[:150] + ("…" if char_count > 150 else "")
            self._result_area.setPlainText(
                f"🔄 [{action_id}] 处理中... (AI 能力待接入 Agent Pipeline)\n\n"
                f"📄 选区内容 ({char_count} 字符):\n{preview}\n\n"
                f"trace_id: {self._llm_ctx['trace_id']}"
            )
        else:
            self._result_area.setPlainText(
                f"🔄 [{action_id}] 处理中... (AI 能力待接入 Agent Pipeline)\n\n"
                f"⚠️ 当前数据源无内容，请先切换数据源或选中内容。\n"
                f"trace_id: {self._llm_ctx['trace_id']}"
            )

    def _on_action_bar(self, label: str):
        """Action Bar 按钮点击 → 通过 Bridge 执行非AI操作"""
        t = telemetry()
        t.emit("V5_WORK_ACTIONBAR", label=label,
               session_id=self._session_id)
        result_text = self._result_area.toPlainText()

        if "Copy" in label:
            text_to_copy = result_text if result_text else self._selected_text
            ok = bridge.do_copy_to_clipboard(text_to_copy)
            self._result_area.setPlainText(
                f"✅ 已复制到剪贴板 ({len(text_to_copy)} 字符)" if ok
                else "❌ 复制失败"
            )

        elif "Apply" in label:
            text = result_text if result_text else self._selected_text
            result = bridge.do_apply_to_ide(text)
            self._result_area.setPlainText(
                f"✅ 已应用到 IDE ({result.get('method', '')})\n{result.get('message', '')}"
                if result.get("success")
                else f"❌ 应用失败: {result.get('message', '')}"
            )

        elif "Export" in label:
            self._result_area.setPlainText(
                "💾 PPT 导出功能需要 slides 数据。\n"
                "请通过 Studio Tab 生成 PPT 后导出。\n"
                "(AI 能力待接入 Agent Pipeline)"
            )

    # =========================================================================
    # 样式
    # =========================================================================

    @staticmethod
    def _strip_btn_style(selected=False):
        if selected:
            return (
                f"QPushButton {{ background: {T.BG_SELECTED}; color: {T.TEXT_ACCENT}; "
                f"border: 1px solid {T.STROKE_FOCUS}; border-radius: 4px; "
                f"padding: 3px 8px; font-size: {T.FONT_CAPTION[0]}px; }}"
                f"QPushButton:hover {{ background: rgba(77, 166, 255, 60); }}"
            )
        return (
            f"QPushButton {{ background: {T.BG_ELEVATED}; color: {T.TEXT_SECONDARY}; "
            f"border: 1px solid {T.STROKE_SUBTLE}; border-radius: 4px; "
            f"padding: 3px 8px; font-size: {T.FONT_CAPTION[0]}px; }}"
            f"QPushButton:hover {{ background: {T.BG_HOVER}; color: {T.TEXT_PRIMARY}; }}"
        )

    @staticmethod
    def _primary_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_PRIMARY_BG};
                color: {T.BTN_PRIMARY_TEXT};
                border: none; border-radius: 6px;
                padding: {T.BTN_MEDIUM_PADDING};
                font-size: {T.FONT_BODY[0]}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {T.ACCENT_PRESSED}; }}
        """

    @staticmethod
    def _secondary_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_SECONDARY_BG};
                color: {T.BTN_SECONDARY_TEXT};
                border: 1px solid {T.BTN_SECONDARY_BORDER};
                border-radius: 6px;
                padding: {T.BTN_SMALL_PADDING};
                font-size: {T.FONT_CAPTION[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_SECONDARY_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def _action_btn_style(bg_color):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: {T.FONT_CAPTION[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_ACTION_HOVER};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
            }}
        """
