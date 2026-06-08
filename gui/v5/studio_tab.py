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


class StudioTabV5(QWidget):
    """Studio Tab: PPT 共创工作台入口"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self._session_id = telemetry().new_session_id()
        self._agent_worker = None  # 当前运行的 Agent Worker
        self._original_text = ""  # 保存用户原始输入，用于传入 Studio 的 Source Panel
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        # ── Launcher 卡片 ──
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-radius: 10px;
                border: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        # 图标 + 标题
        title_row = QHBoxLayout()
        icon_label = QLabel("🎨")
        icon_label.setStyleSheet(
            f"font-size: 24px; background: transparent; border: none;"
        )
        title_label = QLabel("Studio")
        title_label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: 16px; background: transparent; border: none;"
        )
        title_row.addWidget(icon_label)
        title_row.addWidget(title_label)
        title_row.addStretch()
        card_layout.addLayout(title_row)

        # 描述
        desc = QLabel("AI 驱动的 PPT 共创工作台")
        desc.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            "background: transparent; border: none;"
        )
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # 功能点列表
        features = QLabel(
            "• 智能大纲生成  • 4-Panel 编辑器  • 缩略图导航\n"
            "• Click-to-Edit  • AI 差异预览  • 一键导出 PPT"
        )
        features.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none; line-height: 1.6;"
        )
        features.setWordWrap(True)
        card_layout.addWidget(features)

        # 打开按钮
        self._open_btn = QPushButton("打开 Studio ▶")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setStyleSheet(self._cta_btn_style())
        self._open_btn.setMinimumHeight(T.BTN_LARGE_HEIGHT)
        self._open_btn.clicked.connect(self._on_open_studio)
        card_layout.addWidget(self._open_btn)

        layout.addWidget(card)

        # ── 快速输入区（使用 QTextEdit 支持长文本，避免 QLineEdit 截断）──
        self._quick_input = QTextEdit()
        self._quick_input.setPlaceholderText("粘贴文本、输入主题，或拖入文档...")
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
        layout.addWidget(self._quick_input)

        quick_btn = QPushButton("快速创建")
        quick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quick_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL};
                color: #000; border-radius: 6px;
                padding: 6px 14px; font-weight: bold;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        quick_btn.clicked.connect(self._on_quick_open)
        layout.addWidget(quick_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # ── 状态文案 ──
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"padding: 4px 0;"
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
        self._status_label.setText("🔄 AI 生成 PPT 内容中...")
        self._status_label.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
        )

        # 长文档智能截断提示：超过 8000 字符时告知 LLM 进行提炼
        text_len = len(text)
        length_hint = ""
        if text_len > 8000:
            length_hint = (
                f"\n\n注意：原始内容较长（{text_len} 字符），请重点提炼核心信息，"
                f"不要试图覆盖所有细节。优先保证结构清晰和要点精炼。"
            )

        # 通过 V5AgentWorker 生成 PPT 内容
        # 提示：persona 文件 (personas/ppt.md) 已包含详细的 JSON 输出格式要求，
        # prompt 只需传达主题和基本要求
        prompt = (
            f"请根据以下内容生成 PPT 大纲。\n\n"
            f"要求：\n"
            f"1. 严格输出纯 JSON 格式，不要输出任何其他文字、代码块标记或解释\n"
            f"2. 输出格式为 {{\"title\": \"演示文稿标题\", \"slides\": [...]}}\n"
            f"3. 每个 slide 包含 type, layout, title, items, source_excerpt 等字段\n"
            f"4. layout 可选值:\n"
            f"   - center: 居中标题页（封面/结尾）\n"
            f"   - text_only: 纯文字列表（默认）\n"
            f"   - image_right / image_left: 图文混排（案例说明/场景描述）\n"
            f"   - three_columns: 三栏并排（多维度对比）\n"
            f"   - table: 表格（结构化数据/参数对比/统计数据）\n"
            f"   - chart: 图表（数值趋势/占比/对比，支持 bar/line/pie）\n"
            f"   - flowchart: 流程图（步骤流程/决策树/工作流）\n"
            f"5. 智能选型规则：\n"
            f"   - 含数值数据、统计、趋势 → 用 chart\n"
            f"   - 含结构化对比、参数表、分类数据 → 用 table\n"
            f"   - 含步骤、流程、阶段、顺序 → 用 flowchart\n"
            f"   - 含案例、场景描述 → 用 image_right\n"
            f"   - 其他普通内容 → 用 text_only\n"
            f"6. 每页 3-5 个要点，每个要点一句话\n"
            f"7. 特殊布局的 items 数据结构：\n"
            f"   table 类型: items[0] 需含 content_type=\"table\" 和 table_data={{\"columns\":[\"列1\",\"列2\"],\"rows\":[[\"值1\",\"值2\"],...]}}\n"
            f"   chart 类型: items[0] 需含 content_type=\"chart\", chart_type=\"bar|line|pie\" 和 chart_data={{\"title\":\"图表标题\",\"labels\":[\"标签1\",\"标签2\"],\"datasets\":[{{\"label\":\"系列名\",\"data\":[10,20]}}]}}\n"
            f"   flowchart 类型: items[0] 需含 content_type=\"flowchart\" 和 flowchart_data={{\"title\":\"流程标题\",\"steps\":[\"步骤1\",\"步骤2\",\"步骤3\"],\"layout\":\"horizontal\"}}\n"
            f"8. source_excerpt 字段：每页 slide 必须包含，值为该页内容对应的原文片段（20-80字），从原始内容中直接摘录，用于原文高亮联动\n"
            f"9. 必须包含结尾页：type=ending, layout=center, title='谢谢', subtitle='Q & A'\n"
            f"10. 覆盖原文所有一级章节，不要遗漏任何主题\n"
            f"{length_hint}\n"
            f"原始内容：\n{text}"
        )
        
        # 结构化日志：记录 PPT 生成请求详情
        from opencopilot.agent.observability import PipelineObservability
        PipelineObservability.get_instance().log(
            "StudioTab", f"PPT generation request: text_len={text_len}",
            session_id=self._session_id, level="INFO",
            event="STUDIO_PPT_REQUEST",
            extra_data={
                "text_len": text_len,
                "prompt_len": len(prompt),
                "has_length_hint": bool(length_hint),
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
        
        # 埋点：记录原始文本和 AI 输出的长度
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT_GENERATED | original_text_len={len(self._original_text)} | ai_output_len={len(full_text)} | preview={full_text[:100]}",
                    session_id=self._session_id, event="PPT_GENERATED")
        
        # 尝试从 AI 输出中提取 JSON slides
        slides = self._parse_slides_from_text(full_text)
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
        """从 AI 输出文本中解析 JSON slides 数组

        优先使用 ppt_generator.extract_json_from_text（更健壮，含 Markdown 降级），
        若不可用则回退到本地解析逻辑。
        """
        # 优先使用 ppt_generator 的健壮解析（含 Markdown 降级）
        try:
            from ppt_generator import extract_json_from_text
            result = extract_json_from_text(text)
            if result:
                # extract_json_from_text 可能返回 dict（含 slides key）或 list
                if isinstance(result, dict) and "slides" in result:
                    slides = result["slides"]
                    if isinstance(slides, list) and len(slides) > 0:
                        return slides
                elif isinstance(result, list) and len(result) > 0:
                    return result
        except ImportError:
            pass
        except Exception as e:
            print(f"[v5] StudioTab: ppt_generator 解析异常: {e}")

        # 回退：本地 JSON 解析
        import json
        import re

        # 尝试提取 ```json ... ``` 代码块
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "slides" in data and isinstance(data["slides"], list):
                    return data["slides"]
                elif isinstance(data, list) and len(data) > 0:
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试提取花括号包裹的 JSON 对象
        obj_match = re.search(r"\{.*\}", text, re.DOTALL)
        if obj_match:
            try:
                data = json.loads(obj_match.group(0))
                if isinstance(data, dict) and "slides" in data and isinstance(data["slides"], list):
                    return data["slides"]
            except (json.JSONDecodeError, ValueError):
                pass

        # 尝试直接解析整个文本为 JSON
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and "slides" in data and isinstance(data["slides"], list):
                return data["slides"]
            elif isinstance(data, list) and len(data) > 0:
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试提取方括号包裹的数组
        array_match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
        if array_match:
            try:
                slides = json.loads(array_match.group(0))
                if isinstance(slides, list) and len(slides) > 0:
                    return slides
            except (json.JSONDecodeError, ValueError):
                pass

        print(f"[v5] StudioTab: 所有解析方式均失败，文本前 300 字符: {text[:300]}")
        return []

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
