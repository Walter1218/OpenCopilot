"""StudioTabV5 — Studio Tab 入口壳（Launcher 卡片 + 状态文案）"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QHBoxLayout, QTextEdit,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge
from gui.v5.agent_worker import V5AgentWorker
from gui.v5.ppt_prompt import build_ppt_generation_prompt, parse_slides_from_text


class StudioTabV5(QWidget):
    """Studio Tab: PPT 共创工作台入口"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._session_id = telemetry().new_session_id()
        self._agent_worker = None  # 当前运行的 Agent Worker
        self._llm_ctx = None  # LLM trace context
        self._original_text = ""  # 保存用户原始输入，用于传入 Studio 的 Source Panel
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        # ── 居中容器 ──
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(24, 30, 24, 20)
        center_layout.setSpacing(12)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("PPT Co-Creation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: 16px; background: transparent; border: none;"
        )
        center_layout.addWidget(title)

        # 描述
        desc = QLabel("Create professional presentations from your documents")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            "background: transparent; border: none;"
        )
        center_layout.addWidget(desc)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._open_btn = QPushButton("Open Studio")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setFixedHeight(T.BTN_LARGE_HEIGHT)
        self._open_btn.setStyleSheet(self._neutral_btn_style())
        self._open_btn.clicked.connect(self._on_open_studio)
        btn_row.addWidget(self._open_btn)

        self._v5plus_btn = QPushButton("V5Plus CoCreation")
        self._v5plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._v5plus_btn.setFixedHeight(T.BTN_LARGE_HEIGHT)
        self._v5plus_btn.setStyleSheet(self._v5plus_btn_style())
        self._v5plus_btn.setToolTip("3 阶段 E2E 共创流程：输入 → 策略发现 → 编辑打磨")
        self._v5plus_btn.clicked.connect(self._on_open_v5plus)
        btn_row.addWidget(self._v5plus_btn)

        center_layout.addLayout(btn_row)

        # 快速输入区
        self._quick_input = QTextEdit()
        self._quick_input.setPlaceholderText("Quick paste text here to start...")
        self._quick_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QTextEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        self._quick_input.setMaximumHeight(80)
        self._quick_input.setAcceptRichText(False)
        center_layout.addWidget(self._quick_input)

        layout.addWidget(center)

        # ── 状态文案 ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"padding: 4px 16px;"
        )
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    # =========================================================================
    # 公共方法
    # =========================================================================

    def set_shared_text(self, text: str, source: str = "drag_drop"):
        """接收从 SmartCopilot 拖放/导入的共享文本"""
        t = telemetry()
        t.emit("V5_STAB_SHARED_TEXT", source=source, text_len=len(text),
               session_id=self._session_id)
        if text:
            self._quick_input.setPlainText(text)
            self.update_status(False, 0, True)
            self._status_label.setText(
                f"📄 已接收共享内容（{len(text)} 字符，来源: {source}），"
                f"点击「快速创建」即可生成 PPT"
            )

    def update_status(self, studio_open: bool, slides_count: int, has_text: bool):
        """更新状态文案（Tab 切换时调用）"""
        t = telemetry()
        t.emit("V5_STAB_STATUS", studio_open=studio_open,
               slides_count=slides_count, has_text=has_text)
        if studio_open:
            self._status_label.setText("✅ 共创工作台已打开，切换回去即可继续编辑")
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
        elif slides_count > 0:
            self._status_label.setText(
                f"上次编辑：{slides_count} 页幻灯片 — 点击按钮继续编辑"
            )
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_WARNING}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
        elif has_text:
            self._status_label.setText("📄 已导入文本，点击按钮即可打开共创工作台")
            self._status_label.setStyleSheet(
                f"color: {T.TEXT_ACCENT}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
        else:
            self._status_label.setText("💡 请先导入文本，或点击按钮直接粘贴内容")
            self._status_label.setStyleSheet(
                f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )

    # =========================================================================
    # 事件
    # =========================================================================

    def _on_open_studio(self):
        """打开 Studio 窗口"""
        telemetry().emit("V5_STAB_OPEN_STUDIO", session_id=self._session_id)
        self.nav.open_studio()

    def _on_open_v5plus(self):
        """打开 V5Plus 共创工作台（3 阶段 E2E 流程）"""
        text = self._quick_input.toPlainText().strip()
        telemetry().emit("V5_STAB_OPEN_V5PLUS", session_id=self._session_id,
                         text_len=len(text), has_text=bool(text))
        self.nav.open_cocreation(text)

    def _on_quick_open(self):
        """快速创建：通过 Agent Worker 生成 PPT 内容并打开 Studio"""
        text = self._quick_input.toPlainText().strip()
        if not text:
            self._status_label.setText("⚠️ 请输入内容或粘贴文本")
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_WARNING}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
            return

        # 如果已有 Worker 在运行，先取消
        if self._agent_worker is not None and self._agent_worker.isRunning():
            self._agent_worker.stop()
            # 使用 finished 信号异步清理，避免阻塞主线程
            self._agent_worker.finished_signal.connect(lambda _: self._reset_worker())
            telemetry().emit("V5_STAB_STOP", text_len=len(text),
                             session_id=self._session_id)
            self._status_label.setText("⏹️ 已取消生成")
            return

        # 仅在输入极短、看起来更像占位词时，才允许用剪贴板兜底。
        # 避免把用户已经明确输入的主题替换成历史日志等脏数据。
        if len(text) <= 3:
            clip = bridge.get_clipboard_text()
            clip_text = clip.get("text", "")
            if clip_text and len(clip_text) > len(text):
                print(f"[v5] StudioTab: 剪贴板内容更长 ({len(clip_text)} > {len(text)})，使用剪贴板")
                text = clip_text
                self._quick_input.setPlainText(text[:100] + "…")

        telemetry().emit("V5_STAB_QUICK_OPEN", text_len=len(text),
                         session_id=self._session_id)
        self._original_text = text  # 保存原始文本，用于传入 Studio 的 Source Panel

        # LLM 链路追踪 start
        self._llm_ctx = telemetry().llm_start(
            source_tab="STUDIO",
            action_type="ppt",
            session_id=self._session_id,
            text_len=len(text),
        )

        self._status_label.setText("🔄 AI 生成 PPT 内容中...")
        self._status_label.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
        )

        # 通过共享 prompt 构建器生成 PPT prompt（与 V5Plus 完全一致）
        text_len = len(text)
        prompt = build_ppt_generation_prompt(text=text)
        
        # 结构化日志：记录 PPT 生成请求详情
        from opencopilot.agent.observability import PipelineObservability
        PipelineObservability.get_instance().log(
            "StudioTab", f"PPT generation request: text_len={text_len}",
            session_id=self._session_id, level="INFO",
            event="STUDIO_PPT_REQUEST",
            extra_data={
                "text_len": text_len,
                "prompt_len": len(prompt),
                "has_length_hint": text_len > 8000,
            },
        )
        
        self._agent_worker = V5AgentWorker(
            prompt=prompt,
            action_type="ppt",
            session_id=self._session_id,
            context_source="studio",
            context_meta={"input_text_len": text_len},
            is_new_task=True,
        )
        self._agent_worker.finished_signal.connect(self._on_ppt_generated)
        self._agent_worker.error_signal.connect(self._on_ppt_error)
        self._agent_worker.start()
        print(f"[v5] StudioTab: 启动 PPT 生成 → {len(text)} 字符")

    def _on_ppt_generated(self, full_text: str):
        """PPT 内容生成完成回调"""
        # 安全清理：等待线程结束后再置空引用，避免 QThread 被销毁时仍在运行
        self._safely_reset_worker()

        # LLM 链路追踪 done
        t = telemetry()
        if self._llm_ctx:
            t.llm_done(self._llm_ctx, source_tab="STUDIO",
                       output_len=len(full_text))

        # 埋点：记录原始文本和 AI 输出的长度
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT_GENERATED | original_text_len={len(self._original_text)} | ai_output_len={len(full_text)} | preview={full_text[:100]}",
                    session_id=self._session_id, event="PPT_GENERATED")
        
        # 尝试从 AI 输出中提取 JSON slides
        slides = parse_slides_from_text(full_text)
        if slides:
            # 传入用户原始文本（而非 AI 输出）到 Source Panel
            self.nav.open_studio(text=self._original_text, slides=slides)
            self._status_label.setText(
                f"✅ 已生成 {len(slides)} 页幻灯片，Studio 已打开"
            )
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
            telemetry().emit("V5_STAB_PPT_DONE", session_id=self._session_id,
                             slide_count=len(slides), output_len=len(full_text))
            print(f"[v5] StudioTab: PPT 生成完成 → {len(slides)} 页")
        else:
            # 未解析到 slides，保存完整 AI 输出到文件以便排查
            import tempfile, os
            dump_path = os.path.join(tempfile.gettempdir(), f"ppt_ai_output_{self._session_id or 'unknown'}.txt")
            try:
                with open(dump_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
            except Exception:
                dump_path = "<写入失败>"
            
            # 详细诊断：打印前 500 字符供快速排查
            obs.gui_log(f"PPT_PARSE_FAILED | ai_output_len={len(full_text)} | dump={dump_path} | first500={full_text[:500]}",
                        session_id=self._session_id, event="PPT_PARSE_FAILED", level="ERROR")
            self.nav.open_studio(text=self._original_text)
            self._status_label.setText(
                "⚠️ 内容已生成但未解析到结构化 slides，请在 Studio 中手动处理"
            )
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_WARNING}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
            telemetry().emit("V5_STAB_PPT_DONE", session_id=self._session_id,
                             slide_count=0, output_len=len(full_text))
            print(f"[v5] StudioTab: PPT 生成完成 → 未解析到 slides，原始文本长度={len(full_text)}")
            print(f"[v5] StudioTab: AI 完整输出已保存到: {dump_path}")
            print(f"[v5] StudioTab: AI 输出前 500 字符: {full_text[:500]}")

    def _on_ppt_error(self, error_msg: str):
        """PPT 生成错误回调"""
        self._safely_reset_worker()

        # LLM 链路追踪 error
        t = telemetry()
        if self._llm_ctx:
            t.llm_error(self._llm_ctx, source_tab="STUDIO",
                        error_msg=error_msg)
        
        # 针对常见错误类型给出更具体的提示
        if "规则检查发现违规" in error_msg:
            display_msg = (
                f"⚠️ 内容被安全规则拦截: {error_msg}\n\n"
                f"提示：文档中可能包含代码示例（如 password/token 等），"
                f"请尝试移除这些内容后重试。"
            )
        elif "超时" in error_msg:
            display_msg = f"⏰ 生成超时: {error_msg}\n\n提示：请尝试使用更短的文本。"
        else:
            display_msg = f"❌ 生成失败: {error_msg}"
        
        self._status_label.setText(display_msg)
        self._status_label.setStyleSheet(
            f"color: {T.STATUS_WARNING}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
        )
        telemetry().emit("V5_STAB_PPT_ERROR", session_id=self._session_id,
                         error=error_msg)
        print(f"[v5] StudioTab: PPT 生成错误 → {error_msg}")

    def _reset_worker(self):
        """重置 Worker 引用（供异步清理使用）"""
        self._agent_worker = None
        self._status_label.setStyleSheet(
            f"color: {T.STATUS_OFFLINE}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
        )

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

    @staticmethod
    def _parse_slides_from_text(text: str) -> list:
        """从 AI 输出文本中解析 JSON slides 数组（代理到共享模块）"""
        return parse_slides_from_text(text)

    # =========================================================================
    # 样式
    # =========================================================================

    @staticmethod
    def _cta_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_PRIMARY_BG};
                color: {T.BTN_PRIMARY_TEXT};
                border: none; border-radius: 8px;
                padding: {T.BTN_LARGE_PADDING};
                font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {T.ACCENT_PRESSED}; }}
        """

    @staticmethod
    def _neutral_btn_style():
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {T.TEXT_PRIMARY};
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: {T.BTN_LARGE_PADDING};
                font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.16); }}
            QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.24); }}
        """

    @staticmethod
    def _v5plus_btn_style():
        return f"""
            QPushButton {{
                background-color: rgba(167, 139, 250, 180);
                color: #fff;
                border: none; border-radius: 8px;
                padding: {T.BTN_LARGE_PADDING};
                font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(167, 139, 250, 230); }}
            QPushButton:pressed {{ background-color: rgba(139, 92, 246, 230); }}
        """
