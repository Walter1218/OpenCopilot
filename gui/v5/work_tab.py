"""WorkTabV5 — Work Tab 界面壳 (v5.2 精简版)

3 层视觉区域:
  1. Context Header Bar  — 发光圆点 + 竖线 + 来源 + 字数 + 宿主badge + 刷新/关闭
  2. Toolbar Row         — 数据源icon按钮 + 分割线 + 操作按钮(Explain/Fix/Polish/Translate/Review)
  3. Result Area (Hero)  — header(action+streaming灯) + body + bottom(confidence+Copy/Export/Apply)
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QApplication,
    QComboBox, QSizePolicy,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge
from gui.v5.agent_worker import V5AgentWorker




class WorkTabV5(QWidget):
    """Work Tab: 快速操作（上下文感知 + 卡片式操作 + 结构化结果）"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._current_source = "selection"
        self._selected_text = ""
        self._session_id = telemetry().new_session_id()
        self._llm_ctx = None
        self._agent_worker = None
        self._last_result = ""
        self._last_action_id = ""
        self._source_lang = "auto"
        self._target_lang = "zh"
        self._app_name = ""
        self._init_ui()

    # =========================================================================
    # UI 构建
    # =========================================================================

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 1. Context Header Bar ──
        layout.addWidget(self._build_header_bar())

        # ── 2. Toolbar Row (sources + actions, single compact line) ──
        layout.addWidget(self._build_toolbar_row())

        # ── 3. Result Area (Hero — fills remaining space) ──
        layout.addWidget(self._build_result_area(), stretch=1)

    # ------------------------------------------------------------------
    # 1. Context Header Bar
    # ------------------------------------------------------------------

    def _build_header_bar(self):
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            f"background: {T.HEADER_BG}; "
            f"border-bottom: 1px solid {T.HEADER_BORDER};"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(8)

        # 发光圆点
        self._header_dot = QLabel("●")
        self._header_dot.setStyleSheet(
            f"color: {T.ACCENT_CONTROL}; font-size: 8px; "
            "background: transparent; border: none;"
        )
        h.addWidget(self._header_dot)

        # 来源类型
        self._header_source = QLabel("Selection")
        self._header_source.setStyleSheet(
            f"color: #e0e0e0; font-size: {T.FONT_CAPTION[0]}px; "
            f"font-weight: 600; background: transparent; border: none;"
        )
        h.addWidget(self._header_source)

        # 竖线
        h.addWidget(self._separator())

        # 字数
        self._header_chars = QLabel("0 chars")
        self._header_chars.setStyleSheet(
            f"color: #888; font-size: {T.FONT_TINY[0]}px; "
            "background: transparent; border: none;"
        )
        h.addWidget(self._header_chars)

        # 竖线
        h.addWidget(self._separator())

        # 宿主 app badge
        self._header_app_badge = QLabel("VS")
        self._header_app_badge.setFixedSize(18, 18)
        self._header_app_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_app_badge.setStyleSheet(
            f"color: {T.ACCENT_CONTROL}; background: rgba(77,166,255,34); "
            f"border-radius: 3px; font-size: 8px; font-weight: 700; border: none;"
        )
        h.addWidget(self._header_app_badge)

        self._header_app_name = QLabel("")
        self._header_app_name.setStyleSheet(
            f"color: #666; font-size: {T.FONT_TINY[0]}px; "
            "background: transparent; border: none;"
        )
        h.addWidget(self._header_app_name)

        h.addStretch()

        # 刷新按钮
        self._btn_refresh = QPushButton("↻")
        self._btn_refresh.setFixedSize(22, 22)
        self._btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refresh.setToolTip("刷新数据源")
        self._btn_refresh.setStyleSheet(self._mini_btn_style())
        self._btn_refresh.clicked.connect(self._on_header_refresh)
        h.addWidget(self._btn_refresh)

        # 关闭/清空按钮
        self._btn_clear = QPushButton("✕")
        self._btn_clear.setFixedSize(22, 22)
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setToolTip("清空上下文")
        self._btn_clear.setStyleSheet(self._mini_btn_style())
        self._btn_clear.clicked.connect(self._on_header_clear)
        h.addWidget(self._btn_clear)

        return bar

    # ------------------------------------------------------------------
    # 2. Toolbar Row (data sources + actions, single compact line)
    # ------------------------------------------------------------------

    def _build_toolbar_row(self):
        """两行工具栏：Row1=数据源+主操作，Row2=辅助操作+语言+提示"""
        bar = QWidget()
        bar.setStyleSheet(
            f"background: #1e1e1e; border-bottom: 1px solid #2d2d2d;"
        )
        vl = QVBoxLayout(bar)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ═══════════════════════════════════════════════════════
        # Row 1: Data sources + Primary actions
        # ═══════════════════════════════════════════════════════
        row1 = QWidget()
        row1.setFixedHeight(36)
        row1.setStyleSheet("background: transparent;")
        h1 = QHBoxLayout(row1)
        h1.setContentsMargins(20, 6, 20, 4)
        h1.setSpacing(6)

        # ── Data source icon buttons (24×24 square) ──
        self._strip_buttons = {}
        for source_id, label, tip, icon_letter in T.CONTEXT_SOURCES:
            is_default = (source_id == "selection")
            btn = QPushButton(icon_letter)
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn._source_id = source_id
            btn._active = is_default
            self._apply_source_btn_style(btn, is_default)
            btn.clicked.connect(lambda checked, sid=source_id: self._on_strip_clicked(sid))
            self._strip_buttons[source_id] = btn
            h1.addWidget(btn)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedSize(1, 18)
        sep.setStyleSheet("background: #3c3c3c; border: none;")
        h1.addWidget(sep)

        # ── Primary action buttons (icon + text, colored) ──
        self._action_cards = {}
        for card_def in T.PRIMARY_ACTION_CARDS:
            btn = QPushButton(f"{card_def['icon']} {card_def['label']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(card_def.get('desc', ''))
            btn.setFixedHeight(26)
            self._apply_action_btn_style(btn, card_def['accent'], primary=True)
            btn.clicked.connect(lambda checked, aid=card_def["id"]: self._on_action(aid))
            self._action_cards[card_def["id"]] = btn
            h1.addWidget(btn)

        h1.addStretch()
        vl.addWidget(row1)

        # ═══════════════════════════════════════════════════════
        # Row 2: Secondary actions + Language + Hint
        # ═══════════════════════════════════════════════════════
        row2 = QWidget()
        row2.setFixedHeight(30)
        row2.setStyleSheet("background: transparent;")
        h2 = QHBoxLayout(row2)
        h2.setContentsMargins(20, 2, 20, 4)
        h2.setSpacing(6)

        # ── Secondary action buttons (neutral color) ──
        for action_id, label, tip in T.SECONDARY_ACTIONS:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setFixedHeight(24)
            self._apply_action_btn_style(btn, "#888", primary=False)
            btn.clicked.connect(lambda checked, aid=action_id: self._on_action(aid))
            h2.addWidget(btn)

        # ── Language combo (compact) ──
        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(self._lang_combo_style())
        self._lang_combo.setToolTip("选择翻译方向")
        for code, name in T.TRANSLATE_LANG_PAIRS:
            self._lang_combo.addItem(name, code)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        h2.addWidget(self._lang_combo)

        h2.addStretch()

        # ── "→ Chat" shortcut hint ──
        self._toolbar_hint = QPushButton("→ Chat")
        self._toolbar_hint.setFixedHeight(20)
        self._toolbar_hint.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_hint.setToolTip("切换到 Chat Tab 进行深度对话")
        self._toolbar_hint.setStyleSheet(
            "QPushButton { background: #252526; color: #555; border: 1px solid #333; "
            "border-radius: 3px; padding: 2px 8px; font-size: 9px; }"
            "QPushButton:hover { background: #333; color: #aaa; }"
        )
        h2.addWidget(self._toolbar_hint)

        vl.addWidget(row2)

        return bar

    @staticmethod
    def _apply_source_btn_style(btn, active):
        if active:
            btn.setStyleSheet(
                "QPushButton { background: #4da6ff22; color: #4da6ff; "
                "border: 1px solid #4da6ff55; border-radius: 4px; "
                "font-size: 10px; font-weight: 700; }"
                "QPushButton:hover { background: #4da6ff33; }"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { background: #252526; color: #666; "
                "border: 1px solid #3c3c3c; border-radius: 4px; "
                "font-size: 10px; font-weight: 400; }"
                "QPushButton:hover { background: #333; color: #aaa; }"
            )

    @staticmethod
    def _apply_action_btn_style(btn, accent, primary):
        if primary:
            btn.setStyleSheet(
                f"QPushButton {{ background: {accent}12; color: {accent}; "
                f"border: 1px solid {accent}33; border-radius: 5px; "
                f"padding: 4px 10px; font-size: 11px; font-weight: 600; }}"
                f"QPushButton:hover {{ border: 2px solid {accent}; }}"
            )
        else:
            btn.setStyleSheet(
                "QPushButton { background: #252526; color: #999; "
                "border: 1px solid #3c3c3c; border-radius: 5px; "
                "padding: 4px 10px; font-size: 11px; font-weight: 400; }"
                "QPushButton:hover { background: #333; color: #ccc; }"
            )

    # ------------------------------------------------------------------
    # 5. Result Area (structured panel)
    # ------------------------------------------------------------------

    def _build_result_area(self):
        panel = QWidget()
        panel.setStyleSheet(
            f"background: transparent; border: 1px solid {T.PREVIEW_BORDER}; "
            f"border-radius: 8px; margin: 10px 16px 0;"
        )
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Result Header ──
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet(
            f"background: {T.PREVIEW_BG}; "
            f"border-bottom: 1px solid {T.PREVIEW_BORDER}; "
            f"border-top-left-radius: 8px; border-top-right-radius: 8px;"
        )
        hh = QHBoxLayout(header)
        hh.setContentsMargins(12, 0, 12, 0)
        hh.setSpacing(8)

        self._result_icon = QLabel("")
        self._result_icon.setStyleSheet(
            "font-size: 11px; background: transparent; border: none;"
        )
        hh.addWidget(self._result_icon)

        self._result_title = QLabel("Smart Copilot 已就绪")
        self._result_title.setStyleSheet(
            f"color: #e0e0e0; font-size: {T.FONT_CAPTION[0]}px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        hh.addWidget(self._result_title)

        hh.addStretch()

        # Streaming status indicator
        self._stream_dot = QLabel("●")
        self._stream_dot.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: 6px; "
            "background: transparent; border: none;"
        )
        self._stream_dot.setVisible(False)
        hh.addWidget(self._stream_dot)

        self._stream_label = QLabel("")
        self._stream_label.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: 9px; "
            "background: transparent; border: none;"
        )
        self._stream_label.setVisible(False)
        hh.addWidget(self._stream_label)

        vl.addWidget(header)

        # ── Result Body (QTextEdit) ──
        self._result_area = QTextEdit()
        self._result_area.setReadOnly(True)
        self._result_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._result_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.HEADER_BG};
                color: {T.TEXT_PRIMARY};
                font-size: {T.FONT_BODY[0]}px;
                border: none; padding: 10px 14px;
            }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 60); border-radius: 3px;
            }}
        """)
        self._result_area.setPlainText(
            "选中内容后双击右键即可使用。\n"
            "支持 Explain / Fix / Polish 等快捷操作。"
        )
        vl.addWidget(self._result_area, stretch=1)

        # ── Bottom Bar (confidence + action buttons merged) ──
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(40)
        bottom_bar.setStyleSheet(
            f"background: {T.PREVIEW_BG}; "
            f"border-top: 1px solid #333; "
            f"border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;"
        )
        bh = QHBoxLayout(bottom_bar)
        bh.setContentsMargins(14, 4, 14, 4)
        bh.setSpacing(8)

        # Confidence
        self._conf_label = QLabel("Confidence:")
        self._conf_label.setStyleSheet(
            f"color: #666; font-size: 9px; background: transparent; border: none;"
        )
        bh.addWidget(self._conf_label)

        self._conf_bar_bg = QFrame()
        self._conf_bar_bg.setFixedSize(80, 3)
        self._conf_bar_bg.setStyleSheet(
            f"background: {T.CONFIDENCE_BG}; border-radius: 2px;"
        )
        self._conf_bar_fill = QFrame(self._conf_bar_bg)
        self._conf_bar_fill.setFixedSize(0, 3)
        self._conf_bar_fill.setStyleSheet(
            f"background: {T.CONFIDENCE_HIGH}; border-radius: 2px;"
        )
        bh.addWidget(self._conf_bar_bg)

        self._conf_value = QLabel("")
        self._conf_value.setStyleSheet(
            f"color: {T.CONFIDENCE_HIGH}; font-size: 9px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        bh.addWidget(self._conf_value)

        bh.addStretch()

        # Action buttons: Copy / Export / Apply
        for label, icon, tip, style_fn in [
            ("Copy", "📋", "复制结果", self._action_btn_style),
            ("Export", "📤", "导出为 PPT", self._action_btn_style),
            ("Apply", "✓", "应用到 IDE", self._apply_btn_style),
        ]:
            btn = QPushButton(f"{icon} {label}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(style_fn())
            btn.clicked.connect(lambda checked, l=label: self._on_action_bar(l))
            bh.addWidget(btn)

        vl.addWidget(bottom_bar)

        return panel

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
            char_count = len(text)

            # 更新 Header Bar
            self._header_source.setText(self._current_source.capitalize())
            self._header_chars.setText(f"{char_count} chars")

    # =========================================================================
    # 事件处理
    # =========================================================================

    def _on_header_refresh(self):
        """Context Header 刷新按钮"""
        t = telemetry()
        t.emit("V5_WORK_HEADER_REFRESH",
               source_id=self._current_source,
               session_id=self._session_id)
        self._on_strip_clicked(self._current_source)

    def _on_header_clear(self):
        """Context Header 清空按钮"""
        t = telemetry()
        t.emit("V5_WORK_HEADER_CLEAR",
               source_id=self._current_source,
               session_id=self._session_id)
        self._selected_text = ""
        self._header_chars.setText("0 chars")
        self._header_app_name.setText("")
        self._result_area.setPlainText("上下文已清空。选中内容后双击右键即可使用。")

    def _on_strip_clicked(self, source_id: str):
        """Context Strip 切换 → 从 Bridge 获取上下文"""
        t = telemetry()
        t.emit("V5_WORK_STRIP_SWITCH", source_id=source_id,
               session_id=self._session_id)
        self._current_source = source_id

        # 更新所有 source 按钮样式
        for sid, btn in self._strip_buttons.items():
            is_active = (sid == source_id)
            btn._active = is_active
            self._apply_source_btn_style(btn, is_active)

        # Bridge: 获取数据源内容
        result = bridge.fetch_context(source_id)
        self._selected_text = result.get("text", "")
        status = result.get("status", "")
        char_count = len(self._selected_text)
        app_name = result.get("app_name", "")
        self._app_name = app_name

        t.emit("V5_WORK_CONTEXT_LOADED",
               session_id=self._session_id,
               source_id=source_id,
               status=status,
               char_count=char_count)

        # 更新 Header Bar
        source_labels = {s[0]: s[1].split(" ", 1)[-1] for s in T.CONTEXT_SOURCES}
        label = source_labels.get(source_id, source_id)
        self._header_source.setText(label)
        self._header_chars.setText(f"{char_count} chars" if char_count else "empty")

        if app_name:
            badge_text = app_name[:2].upper()
            self._header_app_badge.setText(badge_text)
            self._header_app_badge.setVisible(True)
            self._header_app_name.setText(app_name)
            self._header_app_name.setVisible(True)
        else:
            self._header_app_badge.setVisible(False)
            self._header_app_name.setVisible(False)

        print(f"[v5] WorkTab: 数据源 {source_id} → {char_count} 字符, status={status}")

    def _on_card_hover(self, action_id: str):
        """Primary Action Card hover 埋点"""
        telemetry().emit("V5_WORK_CARD_HOVER", action_id=action_id,
                         session_id=self._session_id)

    def _on_action(self, action_id: str):
        """Primary/Secondary 按钮点击"""
        t = telemetry()
        t.action_event("V5_WORK_ACTION", action_id=action_id,
                       source=self._current_source,
                       session_id=self._session_id)
        self._last_action_id = action_id

        # 更新 Action Bar 快捷键提示
        self._update_shortcut_hint(action_id)

        # 翻译操作时，将语言选择信息传入 context_meta
        context_meta = {"source_text": self._selected_text}
        if action_id == "translate":
            context_meta["source_lang"] = self._source_lang
            context_meta["target_lang"] = self._target_lang

        if action_id == "more":
            actions = bridge.get_more_actions()
            lines = [f"可用操作 ({len(actions)} 项):", ""]
            for a in actions:
                lines.append(f"  {a['label']}  — {a['description']}")
            self._result_area.setPlainText("\n".join(lines))
            self._result_title.setText("More Actions")
            self._result_icon.setText("⋯")
            t.emit("V5_WORK_MORE_SHOW",
                   session_id=self._session_id,
                   action_count=len(actions))
            return

        # 如果已有 Worker 在运行，先取消
        if self._agent_worker is not None and self._agent_worker.isRunning():
            self._agent_worker.stop()
            self._agent_worker.finished_signal.connect(lambda _: self._reset_worker())
            t.emit("V5_WORK_CANCEL", action_id=action_id,
                   session_id=self._session_id)
            self._result_area.setPlainText(f"[{action_id}] 已取消")
            self._update_streaming_state(action_id, False)
            return

        char_count = len(self._selected_text)
        if char_count == 0:
            self._result_area.setPlainText(
                f"[{action_id}] 当前数据源无内容，请先切换数据源或选中内容。"
            )
            return

        # 更新 Result Area header → streaming 态
        self._update_streaming_state(action_id, True)
        self._result_area.setPlainText("")

        # LLM 链路追踪 start
        self._llm_ctx = t.llm_start(
            source_tab="WORK",
            action_type=action_id,
            session_id=self._session_id,
            text_len=char_count,
        )
        t.emit("V5_WORK_STREAM_START",
               action_id=action_id,
               session_id=self._session_id,
               trace_id=self._llm_ctx.get("trace_id", ""))

        # AI 操作：通过 V5AgentWorker
        prompt = self._build_prompt(action_id, self._selected_text)
        self._agent_worker = V5AgentWorker(
            prompt=prompt,
            action_type=action_id,
            session_id=self._session_id,
            context_source=self._current_source,
            context_meta=context_meta,
            is_new_task=True,
        )
        self._agent_worker.text_updated.connect(
            lambda text: self._result_area.setPlainText(text)
        )
        self._agent_worker.finished_signal.connect(self._on_agent_finished)
        self._agent_worker.error_signal.connect(self._on_agent_error)
        self._agent_worker.start()

    def _build_prompt(self, action_id: str, text: str) -> str:
        """根据操作类型构建 prompt"""
        if action_id == "translate":
            lang_map = {
                "auto": "自动检测", "zh": "中文", "en": "英文",
                "ja": "日文", "ko": "韩文", "fr": "法文",
                "de": "德文", "es": "西班牙文", "ru": "俄文",
            }
            src = lang_map.get(self._source_lang, self._source_lang)
            tgt = lang_map.get(self._target_lang, self._target_lang)
            return f"请将以下文本从{src}翻译为{tgt}:\n\n{text}"

        templates = {
            "explain": f"请解释以下代码/文本:\n\n{text}",
            "fix": f"请修复以下代码中的问题:\n\n{text}",
            "polish": f"请润色优化以下文本:\n\n{text}",
            "code_review": f"请对以下代码进行审查:\n\n{text}",
        }
        return templates.get(action_id, text)

    def _on_agent_finished(self, full_text: str):
        """Agent Worker 完成回调"""
        self._last_result = full_text
        t = telemetry()

        # LLM 链路追踪 done
        if self._llm_ctx:
            t.llm_done(self._llm_ctx, source_tab="WORK",
                       output_len=len(full_text))

        action_id = getattr(self._agent_worker, 'action_type', 'unknown')
        t.emit("V5_WORK_STREAM_DONE",
               session_id=self._session_id,
               action_id=action_id,
               output_len=len(full_text))

        # 更新 streaming 状态 → 完成
        self._update_streaming_state(action_id, False)

        # 模拟 confidence（基于输出长度估算）
        score = min(95, max(50, 60 + len(full_text) // 100))
        self._update_confidence(score)

        print(f"[v5] WorkTab: Agent 完成 → {len(full_text)} 字符")
        self._safely_reset_worker()

    def _on_agent_error(self, error_msg: str):
        """Agent Worker 错误回调"""
        t = telemetry()
        if self._llm_ctx:
            t.llm_error(self._llm_ctx, source_tab="WORK",
                        error_msg=error_msg)
        self._result_area.setPlainText(f"❌ {error_msg}")
        self._update_streaming_state(self._last_action_id, False)
        self._result_title.setText("Error")
        self._result_icon.setText("❌")
        self._safely_reset_worker()

    def _reset_worker(self):
        self._agent_worker = None

    def _safely_reset_worker(self):
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

    def _on_action_bar(self, label: str):
        """Action Bar 按钮点击"""
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
            t.emit("V5_WORK_COPY_DONE",
                   session_id=self._session_id,
                   success=ok, text_len=len(text_to_copy))

        elif "Apply" in label:
            text = result_text if result_text else self._selected_text
            result = bridge.do_apply_to_ide(text)
            self._result_area.setPlainText(
                f"✅ 已应用到 IDE ({result.get('method', '')})\n{result.get('message', '')}"
                if result.get("success")
                else f"❌ 应用失败: {result.get('message', '')}"
            )
            t.emit("V5_WORK_APPLY_DONE",
                   session_id=self._session_id,
                   success=result.get("success", False),
                   method=result.get("method", ""),
                   text_len=len(text))

        elif "Export" in label:
            text = result_text if result_text else self._selected_text
            if not text.strip():
                self._result_area.setPlainText(
                    "⚠️ 当前没有可发送到 Studio 的内容。"
                )
                t.emit("V5_WORK_EXPORT_STUDIO",
                       session_id=self._session_id,
                       success=False, reason="empty_text")
                return

            if hasattr(self.nav, "open_studio"):
                self.nav.open_studio(text=text)
                self._result_area.setPlainText(
                    "💾 已将当前内容发送到 Studio。"
                )
                t.emit("V5_WORK_EXPORT_STUDIO",
                       session_id=self._session_id,
                       success=True, text_len=len(text))
            else:
                self._result_area.setPlainText(
                    "⚠️ 当前导航器不支持打开 Studio。"
                )
                t.emit("V5_WORK_EXPORT_STUDIO",
                       session_id=self._session_id,
                       success=False, reason="nav_unsupported")

    # =========================================================================
    # UI 状态更新方法
    # =========================================================================

    def _update_streaming_state(self, action_id: str, is_streaming: bool):
        """更新 Result Area header 的 streaming 状态"""
        # 查找 action card 定义
        card_def = None
        for cd in T.PRIMARY_ACTION_CARDS:
            if cd["id"] == action_id:
                card_def = cd
                break

        if is_streaming:
            icon = card_def["icon"] if card_def else "🔄"
            self._result_icon.setText(icon)
            self._result_title.setText(f"{action_id.capitalize()} Result")
            self._stream_dot.setVisible(True)
            self._stream_label.setText("Streaming...")
            self._stream_label.setVisible(True)
            # 隐藏 confidence
            self._conf_bar_fill.setFixedWidth(0)
            self._conf_value.setText("")
        else:
            self._stream_dot.setVisible(False)
            self._stream_label.setVisible(False)
            if action_id:
                icon = card_def["icon"] if card_def else "✓"
                self._result_icon.setText(icon)
                self._result_title.setText(f"{action_id.capitalize()} Result")

    def _update_confidence(self, score: int):
        """更新 Confidence Bar"""
        t = telemetry()
        t.emit("V5_WORK_CONFIDENCE",
               action_id=self._last_action_id,
               score=score,
               session_id=self._session_id)

        # 颜色选择
        if score >= 80:
            color = T.CONFIDENCE_HIGH
        elif score >= 50:
            color = T.CONFIDENCE_MID
        else:
            color = T.CONFIDENCE_LOW

        fill_width = int(80 * score / 100)
        self._conf_bar_fill.setFixedWidth(max(1, fill_width))
        self._conf_bar_fill.setStyleSheet(
            f"background: {color}; border-radius: 2px;"
        )
        self._conf_value.setText(f"{score}%")
        self._conf_value.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 600; "
            "background: transparent; border: none;"
        )

    def _update_shortcut_hint(self, action_id: str):
        """更新 Toolbar 提示（精简版：不再需要独立快捷键区域）"""
        pass  # 快捷键提示已合并到 toolbar hint 按钮

    # =========================================================================
    # 翻译语言
    # =========================================================================

    def _on_lang_changed(self, index: int):
        code = self._lang_combo.itemData(index)
        if code and "→" in code:
            parts = code.split("→")
            self._source_lang = parts[0]
            self._target_lang = parts[1]
            telemetry().emit("V5_WORK_LANG_CHANGE",
                             source_lang=self._source_lang,
                             target_lang=self._target_lang,
                             session_id=self._session_id)

    # =========================================================================
    # 样式工具
    # =========================================================================

    @staticmethod
    def _separator():
        sep = QFrame()
        sep.setFixedSize(1, 14)
        sep.setStyleSheet(
            f"background: #3c3c3c; border: none;"
        )
        return sep

    @staticmethod
    def _mini_btn_style():
        return (
            f"QPushButton {{ background: #252526; color: #666; "
            f"border: 1px solid #3c3c3c; border-radius: 4px; "
            f"font-size: 10px; }}"
            f"QPushButton:hover {{ background: #333; color: #aaa; }}"
        )

    @staticmethod
    def _secondary_btn_style():
        return (
            f"QPushButton {{ background: {T.PREVIEW_BG}; "
            f"color: #999; border: 1px solid {T.PREVIEW_BORDER}; "
            f"border-radius: 6px; padding: 4px 10px; "
            f"font-size: {T.FONT_CAPTION[0]}px; }}"
            f"QPushButton:hover {{ background: #333; color: #ccc; }}"
        )

    @staticmethod
    def _action_btn_style():
        return (
            f"QPushButton {{ background: {T.PREVIEW_BG}; "
            f"color: #aaa; border: 1px solid {T.PREVIEW_BORDER}; "
            f"border-radius: 5px; padding: 6px 14px; "
            f"font-size: 12px; }}"
            f"QPushButton:hover {{ background: #333; color: #e0e0e0; "
            f"border: 1px solid {T.STROKE_BORDER}; }}"
        )

    @staticmethod
    def _apply_btn_style():
        return (
            f"QPushButton {{ background: {T.BTN_APPLY_BG}; "
            f"color: {T.BTN_APPLY_TEXT}; border: none; "
            f"border-radius: 5px; padding: 6px 16px; "
            f"font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {T.BTN_APPLY_HOVER}; }}"
        )

    @staticmethod
    def _lang_combo_style():
        return f"""
            QComboBox {{
                background-color: {T.PREVIEW_BG};
                color: #999;
                border: 1px solid {T.PREVIEW_BORDER};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: {T.FONT_CAPTION[0]}px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                background-color: {T.PREVIEW_BG};
                color: #999;
                selection-background-color: {T.BG_SELECTED};
            }}
        """
