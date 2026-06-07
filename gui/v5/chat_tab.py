"""ChatTabV5 — Chat Tab 界面壳

布局: Context Panel (可折叠) → Conversation → Input + Send
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QComboBox,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge
from gui.v5.agent_worker import V5AgentWorker


class ChatTabV5(QWidget):
    """Chat Tab: 连续对话 + 可折叠 Context Panel"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._context_collapsed = True
        self._session_id = telemetry().new_session_id()
        self._llm_ctx = None  # LLM trace context
        self._message_count = 0
        self._agent_worker = None  # 当前运行的 Agent Worker
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        # ── Context Panel (可折叠) ──
        self._context_panel = QWidget()
        ctx_layout = QVBoxLayout(self._context_panel)
        ctx_layout.setContentsMargins(0, 0, 0, 0)
        ctx_layout.setSpacing(2)

        # 折叠按钮行
        toggle_row = QHBoxLayout()
        self._ctx_toggle_btn = QPushButton("Context ▸  0 sources")
        self._ctx_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ctx_toggle_btn.setStyleSheet(self._toggle_btn_style())
        self._ctx_toggle_btn.clicked.connect(self._toggle_context)
        toggle_row.addWidget(self._ctx_toggle_btn)
        toggle_row.addStretch()
        ctx_layout.addLayout(toggle_row)

        # 折叠内容（默认隐藏）
        self._ctx_content = QLabel("暂无上下文来源")
        self._ctx_content.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"padding: 4px 8px; background: {T.BG_ELEVATED}; border-radius: 4px;"
        )
        self._ctx_content.setWordWrap(True)
        self._ctx_content.hide()
        ctx_layout.addWidget(self._ctx_content)

        layout.addWidget(self._context_panel)

        # ── Conversation 显示区 ──
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {T.TEXT_PRIMARY};
                font-size: {T.FONT_BODY[0]}px;
                border: none; line-height: 1.6;
            }}
            QScrollBar:vertical {{
                width: 6px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 60); border-radius: 3px;
            }}
        """)
        layout.addWidget(self._chat_display, stretch=1)

        # ── 输入区 ──
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        # 会话选择器
        self._session_combo = QComboBox()
        self._session_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {T.BG_ELEVATED};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: {T.FONT_CAPTION[0]}px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
        """)
        self._session_combo.addItem("默认会话")
        self._session_combo.setToolTip("选择会话")
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        input_layout.addWidget(self._session_combo)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("输入消息，按 Enter 发送...")
        self._chat_input.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        self._chat_input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("发送")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL};
                color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        self._send_btn.clicked.connect(self._on_send)

        # 新建会话按钮
        self._new_session_btn = QPushButton("+")
        self._new_session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_session_btn.setToolTip("新建会话")
        self._new_session_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BG_ELEVATED};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: {T.FONT_BODY[0]}px; font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {T.BG_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """)
        self._new_session_btn.clicked.connect(self._on_new_session)

        input_layout.addWidget(self._chat_input, stretch=1)
        input_layout.addWidget(self._send_btn)
        input_layout.addWidget(self._new_session_btn)
        layout.addLayout(input_layout)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def focus_input(self):
        self._chat_input.setFocus()

    def inject_context(self, text: str, source: str):
        """从 Work Tab 跳转时注入上下文摘要"""
        t = telemetry()
        t.emit("V5_CHAT_INJECT", source=source, text_len=len(text),
               session_id=self._session_id)
        self._chat_display.clear()
        if text:
            preview = text[:150] + ("…" if len(text) > 150 else "")
            self.append_message(
                "系统",
                f"已将上下文带入，您可以继续追问。\n\n"
                f"📄 当前上下文（{len(text)} 字符，来源: {source}）:\n{preview}"
            )

    def set_shared_text(self, text: str, source: str = "drag_drop"):
        """接收从 SmartCopilot 拖放/导入的共享文本"""
        t = telemetry()
        t.emit("V5_CHAT_SHARED_TEXT", source=source, text_len=len(text),
               session_id=self._session_id)
        if text:
            preview = text[:120] + ("…" if len(text) > 120 else "")
            self.append_message(
                "系统",
                f"📄 已接收共享内容（{len(text)} 字符，来源: {source}）:\n{preview}\n\n"
                f"您可以直接在下方输入框提问，或继续对话。"
            )

    def append_message(self, role: str, text: str):
        """追加一条聊天消息"""
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

    # =========================================================================
    # 事件
    # =========================================================================

    def _on_send(self):
        """发送消息 → 本地 echo + 通过 V5AgentWorker 获取 AI 回复"""
        text = self._chat_input.text().strip()
        if not text:
            return

        # 如果已有 Worker 在运行，先取消（发送按钮变为停止功能）
        if self._agent_worker is not None and self._agent_worker.isRunning():
            self._agent_worker.stop()
            # 使用 finished 信号异步清理，避免阻塞主线程
            self._agent_worker.finished_signal.connect(lambda _: self._reset_worker())
            self._send_btn.setText("发送")
            telemetry().emit("V5_CHAT_STOP", session_id=self._session_id)
            return

        t = telemetry()
        self._message_count += 1
        self._llm_ctx = t.llm_start(
            source_tab="CHAT",
            action_type="chat",
            session_id=self._session_id,
            text_len=len(text),
        )
        t.emit("V5_CHAT_SEND", text_len=len(text),
               message_count=self._message_count,
               session_id=self._session_id,
               trace_id=self._llm_ctx["trace_id"])
        self._chat_input.clear()
        self.append_message("你", text)
        self._save_message("user", text)

        # 创建 AI 回复占位，后续流式更新
        self.append_message("AI", "🔄 思考中...")

        # 通过 V5AgentWorker 调用 Agent Pipeline
        self._send_btn.setText("停止")
        self._agent_worker = V5AgentWorker(
            prompt=text,
            action_type="chat",
            session_id=self._session_id,
            context_source="chat",
            context_meta={},
            is_new_task=False,
        )
        self._agent_worker.text_updated.connect(self._on_ai_chunk)
        self._agent_worker.finished_signal.connect(self._on_ai_finished)
        self._agent_worker.error_signal.connect(self._on_ai_error)
        self._agent_worker.start()

    def _on_ai_chunk(self, text: str):
        """AI 流式 chunk 回调 — 更新最后一条 AI 消息"""
        self._update_last_ai_message(text)

    def _on_ai_finished(self, full_text: str):
        """AI 完成回调"""
        self._send_btn.setText("发送")
        self._safely_reset_worker()
        self._save_message("assistant", full_text)
        t = telemetry()
        if self._llm_ctx:
            t.llm_done(self._llm_ctx, source_tab="CHAT",
                       chunk_count=0, output_len=len(full_text))
        else:
            t.emit("V5_CHAT_LLM_DONE", session_id=self._session_id,
                   output_len=len(full_text))
        print(f"[v5] ChatTab: AI 完成 → {len(full_text)} 字符")

    def _on_ai_error(self, error_msg: str):
        """AI 错误回调"""
        self._send_btn.setText("发送")
        self._update_last_ai_message(f"❌ {error_msg}")
        self._safely_reset_worker()
        t = telemetry()
        if self._llm_ctx:
            t.llm_error(self._llm_ctx, source_tab="CHAT", error_msg=error_msg)
        else:
            t.emit("V5_CHAT_LLM_ERROR", session_id=self._session_id,
                   error_msg=error_msg)

    def _reset_worker(self):
        """重置 Worker 引用（供异步清理使用）"""
        self._agent_worker = None

    def _safely_reset_worker(self):
        """安全重置 Worker：等待线程结束后再清理引用"""
        if self._agent_worker is not None:
            worker = self._agent_worker
            self._agent_worker = None
            if worker.isRunning():
                # 等待线程自然结束（最多3秒），不强制quit
                worker.finished.connect(worker.deleteLater)
                if not worker.wait(3000):
                    # 如果3秒后仍未结束，强制终止
                    worker.terminate()
                    worker.wait(1000)
            else:
                worker.deleteLater()

    def _update_last_ai_message(self, text: str):
        """增量更新最后一条 AI 消息的内容（避免全量重绘）"""
        # 使用 QTextCursor 定位到最后，删除旧的 AI 占位内容，插入新文本
        from PyQt6.QtGui import QTextCursor

        cursor = self._chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 找到最后一条 AI 消息的位置（通过 HTML 特征定位）
        # 策略：直接追加差异文本，利用 QTextEdit 的自动合并
        # 更简单的方式：直接替换整个 AI 消息行
        doc = self._chat_display.document()
        block = doc.lastBlock()

        # 删除最后一块（当前 AI 消息），重新插入
        cursor.setPosition(block.position())
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        # 插入更新后的 AI 消息
        self.append_message("AI", text)

    def _save_message(self, role: str, text: str):
        """保存消息到本地历史文件"""
        try:
            import json, os
            history_dir = os.path.expanduser("~/.opencopilot/chat_history")
            os.makedirs(history_dir, exist_ok=True)
            history_file = os.path.join(history_dir, f"{self._session_id}.json")

            history = []
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

            from datetime import datetime
            history.append({
                "role": role,
                "text": text,
                "timestamp": datetime.now().isoformat(),
            })

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[v5] ChatTab: 保存历史失败 → {e}")

    def _load_session_history(self, session_id: str):
        """加载指定会话的历史记录"""
        try:
            import json, os
            history_file = os.path.expanduser(
                f"~/.opencopilot/chat_history/{session_id}.json"
            )
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[v5] ChatTab: 加载历史失败 → {e}")
        return []

    def _on_new_session(self):
        """新建会话"""
        self._session_id = telemetry().new_session_id()
        self._message_count = 0
        self._chat_display.clear()
        self._chat_display.setPlainText("新会话已开始。输入消息开始对话。\n")
        # 添加到会话选择器
        session_name = f"会话 {self._session_combo.count() + 1}"
        self._session_combo.addItem(session_name, self._session_id)
        self._session_combo.setCurrentIndex(self._session_combo.count() - 1)
        telemetry().emit("V5_CHAT_NEW_SESSION", session_id=self._session_id)
        print(f"[v5] ChatTab: 新建会话 → {self._session_id[:8]}")

    def _on_session_changed(self, index: int):
        """切换会话"""
        if index < 0:
            return
        session_data = self._session_combo.itemData(index)
        if session_data:
            self._session_id = session_data
        self._message_count = 0
        self._chat_display.clear()
        history = self._load_session_history(self._session_id)
        if history:
            for msg in history:
                role_label = "你" if msg.get("role") == "user" else "AI"
                self.append_message(role_label, msg.get("text", ""))
        else:
            self._chat_display.setPlainText("会话历史为空。\n")
        telemetry().emit("V5_CHAT_SWITCH_SESSION",
                         session_id=self._session_id,
                         message_count=len(history))
        print(f"[v5] ChatTab: 切换会话 → {self._session_id[:8]}, {len(history)} 条历史")

    def _toggle_context(self):
        """折叠/展开 Context Panel"""
        self._context_collapsed = not self._context_collapsed
        t = telemetry()
        t.emit("V5_CHAT_CTX_TOGGLE", collapsed=self._context_collapsed,
               session_id=self._session_id)
        self._ctx_content.setVisible(not self._context_collapsed)
        arrow = "▾" if not self._context_collapsed else "▸"
        self._ctx_toggle_btn.setText(f"Context {arrow}  0 sources")

    # =========================================================================
    # 样式
    # =========================================================================

    @staticmethod
    def _toggle_btn_style():
        return f"""
            QPushButton {{
                background: transparent; border: none;
                color: {T.TEXT_SECONDARY};
                font-size: {T.FONT_CAPTION[0]}px;
                padding: 2px 4px; text-align: left;
            }}
            QPushButton:hover {{ color: {T.TEXT_PRIMARY}; }}
        """
