"""ChatTabV5 — Chat Tab 界面壳

布局: Context Badge → Bubble Conversation → Input + Round Send
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QComboBox,
    QScrollArea, QFrame, QSizePolicy,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5.agent_worker import V5AgentWorker


class ChatTabV5(QWidget):
    """Chat Tab: 连续对话 + 可折叠 Context Panel"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._context_collapsed = True
        self._session_id = telemetry().new_session_id()
        self._llm_ctx = None  # LLM trace context
        self._chunk_count = 0  # 当前对话 chunk 计数器
        self._message_count = 0
        self._agent_worker = None  # 当前运行的 Agent Worker
        self._context_sources = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ── Context Badge（一行小标签）──
        ctx_row = QHBoxLayout()
        self._ctx_badge = QLabel("Context")
        self._ctx_badge.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; background: rgba(77,166,255,18); "
            f"border: 1px solid rgba(77,166,255,44); border-radius: 8px; "
            f"padding: 2px 8px; font-size: 9px; font-weight: 600;"
        )
        ctx_row.addWidget(self._ctx_badge)
        self._ctx_hint = QLabel("从 Work Tab 自动注入上下文")
        self._ctx_hint.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none;"
        )
        ctx_row.addWidget(self._ctx_hint)
        self._ctx_clear_btn = QPushButton("清空")
        self._ctx_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ctx_clear_btn.setStyleSheet(self._toggle_btn_style())
        self._ctx_clear_btn.clicked.connect(self._clear_context_sources)
        self._ctx_clear_btn.setVisible(False)
        ctx_row.addWidget(self._ctx_clear_btn)
        ctx_row.addStretch()
        layout.addLayout(ctx_row)

        # ── 会话选择器（隐藏但保留功能）──
        self._session_combo = QComboBox()
        self._session_combo.setVisible(False)
        self._session_combo.addItem("默认会话", self._session_id)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        layout.addWidget(self._session_combo)

        # ── Bubble Conversation（滚动区 + 气泡布局）──
        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._chat_scroll.verticalScrollBar().setStyleSheet(
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,60); border-radius: 3px; }"
        )

        self._bubble_container = QWidget()
        self._bubble_layout = QVBoxLayout(self._bubble_container)
        self._bubble_layout.setContentsMargins(0, 4, 0, 4)
        self._bubble_layout.setSpacing(8)
        self._bubble_layout.addStretch()  # 把气泡往上挤
        self._chat_scroll.setWidget(self._bubble_container)
        layout.addWidget(self._chat_scroll, stretch=1)

        # ── 输入区（Input + 圆形 Send 按钮）──
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Follow up...")
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

        self._send_btn = QPushButton("▶")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setFixedSize(28, 28)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL};
                color: #fff; border: none; border-radius: 14px;
                font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        self._send_btn.clicked.connect(self._on_send)

        # 新建会话按钮（保留，但改为小图标）
        self._new_session_btn = QPushButton("+")
        self._new_session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_session_btn.setToolTip("新建会话")
        self._new_session_btn.setFixedSize(28, 28)
        self._new_session_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.BG_ELEVATED};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 4px;
                font-size: 14px; font-weight: bold;
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
        self._refresh_context_panel()

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
        self._clear_bubbles()
        if text:
            preview = text[:150] + ("…" if len(text) > 150 else "")
            self.append_message(
                "系统",
                f"已将上下文带入，您可以继续追问。\n\n"
                f"📄 当前上下文（{len(text)} 字符，来源: {source}）:\n{preview}"
            )
            self._upsert_context_source(
                key=f"inject:{source}",
                label=f"Work/{source}",
                text=text,
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
            self._upsert_context_source(
                key=f"shared:{source}",
                label=f"Shared/{source}",
                text=text,
            )

    def append_message(self, role: str, text: str):
        """追加一条气泡消息"""
        is_user = (role == "你")
        is_system = (role == "系统")

        # 气泡容器
        bubble = QFrame()

        if is_user:
            # 用户气泡：右对齐，蓝色
            wrapper = QHBoxLayout()
            wrapper.addStretch()
            bubble.setStyleSheet(
                f"QFrame {{ background: {T.ACCENT_CONTROL}; border-radius: 10px; "
                f"padding: 8px 12px; max-width: 280px; }}"
            )
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(
                f"color: #fff; font-size: {T.FONT_BODY[0]}px; "
                "background: transparent; border: none;"
            )
            bubble_layout = QVBoxLayout(bubble)
            bubble_layout.setContentsMargins(0, 0, 0, 0)
            bubble_layout.setSpacing(0)
            bubble_layout.addWidget(label)
            wrapper.addWidget(bubble)
            # 在 stretch 之前插入（stretch 始终在最后）
            self._bubble_layout.insertLayout(
                self._bubble_layout.count() - 1, wrapper
            )
        elif is_system:
            # 系统消息：居中，灰色背景
            bubble.setStyleSheet(
                f"QFrame {{ background: rgba(77,166,255,12); "
                f"border: 1px solid rgba(77,166,255,30); border-radius: 6px; "
                f"padding: 6px 10px; }}"
            )
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(
                f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
                "background: transparent; border: none;"
            )
            bubble_layout = QVBoxLayout(bubble)
            bubble_layout.setContentsMargins(0, 0, 0, 0)
            bubble_layout.addWidget(label)
            self._bubble_layout.insertWidget(
                self._bubble_layout.count() - 1, bubble
            )
        else:
            # AI 气泡：左对齐，灰色
            bubble.setStyleSheet(
                f"QFrame {{ background: {T.BG_ELEVATED}; "
                f"border: 1px solid {T.STROKE_SUBTLE}; border-radius: 10px; "
                f"padding: 8px 12px; max-width: 320px; }}"
            )
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(
                f"color: {T.TEXT_PRIMARY}; font-size: {T.FONT_BODY[0]}px; "
                "background: transparent; border: none;"
            )
            bubble_layout = QVBoxLayout(bubble)
            bubble_layout.setContentsMargins(0, 0, 0, 0)
            bubble_layout.setSpacing(0)
            bubble_layout.addWidget(label)
            self._bubble_layout.insertWidget(
                self._bubble_layout.count() - 1, bubble
            )

        # 保存最后一个气泡引用（用于 AI 流式更新）
        self._last_bubble_label = label if hasattr(self, '_last_bubble_label') else None
        self._last_bubble_label = label

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
        self._chunk_count = 0
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
        self._send_btn.setText("■")
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
        """AI 流式 chunk 回调 — 更新最后一条 AI 消息 + 分块埋点"""
        self._chunk_count += 1
        self._update_last_ai_message(text)
        # 每 10 个 chunk 打一次链路埋点（避免每条都打）
        if self._chunk_count % 10 == 0 and self._llm_ctx:
            telemetry().llm_chunk(
                self._llm_ctx,
                source_tab="CHAT",
                chunk_count=self._chunk_count,
                output_len=len(text),
            )

    def _on_ai_finished(self, full_text: str):
        """AI 完成回调"""
        self._send_btn.setText("▶")
        self._safely_reset_worker()
        self._save_message("assistant", full_text)
        t = telemetry()
        if self._llm_ctx:
            t.llm_done(self._llm_ctx, source_tab="CHAT",
                       chunk_count=self._chunk_count, output_len=len(full_text))
        else:
            t.emit("V5_CHAT_LLM_DONE", session_id=self._session_id,
                   output_len=len(full_text))
        print(f"[v5] ChatTab: AI 完成 → {len(full_text)} 字符")

    def _on_ai_error(self, error_msg: str):
        """AI 错误回调"""
        self._send_btn.setText("▶")
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
        """增量更新最后一条 AI 气泡的内容"""
        if hasattr(self, '_last_bubble_label') and self._last_bubble_label:
            self._last_bubble_label.setText(text)

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

    def _clear_bubbles(self):
        """清空所有气泡消息"""
        while self._bubble_layout.count() > 1:  # 保留最后的 stretch
            item = self._bubble_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 清理 wrapper layout 中的气泡
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        self._last_bubble_label = None

    def _on_new_session(self):
        """新建会话"""
        self._session_id = telemetry().new_session_id()
        self._message_count = 0
        self._clear_bubbles()
        # 添加到会话选择器（会触发 currentIndexChanged）
        session_name = f"会话 {self._session_combo.count() + 1}"
        self._session_combo.addItem(session_name, self._session_id)
        self._session_combo.setCurrentIndex(self._session_combo.count() - 1)
        # ★ 在 combo 变更后再添加系统消息，避免被 session_changed 事件覆盖
        self._clear_bubbles()
        self.append_message("系统", "新会话已开始。输入消息开始对话。")
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
        self._clear_bubbles()
        history = self._load_session_history(self._session_id)
        if history:
            for msg in history:
                role = "你" if msg.get("role") == "user" else "AI"
                self.append_message(role, msg.get("text", ""))
        else:
            self.append_message("系统", "会话历史为空。")
        telemetry().emit("V5_CHAT_SWITCH_SESSION",
                         session_id=self._session_id,
                         message_count=len(history))
        print(f"[v5] ChatTab: 切换会话 → {self._session_id[:8]}, {len(history)} 条历史")

    def _toggle_context(self):
        """折叠/展开 Context Panel（兼容旧调用）"""
        self._context_collapsed = not self._context_collapsed

    def _upsert_context_source(self, key: str, label: str, text: str):
        preview = text[:120] + ("…" if len(text) > 120 else "")
        entry = {
            "key": key,
            "label": label,
            "text": text,
            "preview": preview,
            "char_count": len(text),
        }
        self._context_sources = [
            item for item in self._context_sources if item.get("key") != key
        ]
        self._context_sources.insert(0, entry)
        self._refresh_context_panel()

    def _refresh_context_panel(self):
        count = len(self._context_sources)
        self._ctx_clear_btn.setVisible(count > 0)
        self._ctx_hint.setText(
            f"{count} 个上下文来源" if count > 0 else "从 Work Tab 自动注入上下文"
        )

    def _clear_context_sources(self):
        cleared = len(self._context_sources)
        self._context_sources = []
        self._refresh_context_panel()
        telemetry().emit(
            "V5_CHAT_CTX_CLEAR",
            session_id=self._session_id,
            cleared_count=cleared,
        )

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
