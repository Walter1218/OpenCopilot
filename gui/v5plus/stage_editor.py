"""Stage 3: 编辑打磨 — IDE 式双面板布局

60% 中间 PPT 编辑区（缩略图 + 预览 + 版式标签）
40% 右侧原文面板（映射标签 + 重新提炼 + AI 输入）

AI 部分通过 V5AgentWorker 走标准 Agent Pipeline 协议。
"""
import logging
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPointF
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QFrame,
    QSplitter, QScrollArea, QSizePolicy, QProgressBar,
)


class DraggableLabel(QLabel):
    """支持拖拽的 QLabel — 拖拽超过 5px 阈值时启动 QDrag
    
    携带 application/x-sourcetext 自定义 MIME 格式，
    SlideRenderer.dragEnterEvent 已支持此格式。
    """
    drag_started = pyqtSignal(str)  # 拖拽开始时发射文本内容

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.position() - self._drag_start_pos
            if (delta.x() ** 2 + delta.y() ** 2) ** 0.5 > 5:
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        """启动 QDrag"""
        text = self.text()
        if not text:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(text)
        mime.setData("application/x-sourcetext", text.encode("utf-8"))
        drag.setMimeData(mime)
        self.drag_started.emit(text)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start_pos = None

from gui.v5plus import tokens_plus as T
from gui.v5.telemetry import telemetry
from gui.v5.agent_worker import V5AgentWorker
from gui.v5.ppt_prompt import (
    build_ppt_modify_prompt, build_ppt_reextract_prompt, parse_slides_from_text
)
from opencopilot.capabilities.ppt.preview_panel import SlideRenderer, InlineEditor
from opencopilot.capabilities.ppt.render_command import RenderCommandParser
from opencopilot.capabilities.ppt.render_executor import RenderDispatcher

logger = logging.getLogger(__name__)


class StageEditorWidget(QWidget):
    """Stage 3：IDE 式编辑打磨"""

    # 信号：导出 PPT
    export_requested = pyqtSignal(list)  # slides_data

    def __init__(self, session_id: str = "", parent=None):
        super().__init__(parent)
        self._session_id = session_id
        self._text = ""
        self._strategy_config = {}
        self._slides_data = []
        self._current_slide = 0
        self._paragraph_widgets = []  # 跟踪原文段落 widgets，便于重建
        self._paragraph_slide_map = []  # 每个段落对应的 slide_index
        self._ai_worker = None  # 当前 AI worker 引用
        self._render_dispatcher = None  # 渲染指令调度器
        self._last_instruction = ""  # 最近一次用户指令（用于批量操作检测）
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # ── IDE 式双面板 ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {T.STROKE_SUBTLE};
            }}
        """)

        # 中间 PPT 编辑区（60%）
        self._center_panel = self._create_center_panel()
        splitter.addWidget(self._center_panel)

        # 右侧原文面板（40%）
        self._right_panel = self._create_right_panel()
        splitter.addWidget(self._right_panel)

        # 设置比例
        splitter.setStretchFactor(0, T.SPLIT_CENTER)
        splitter.setStretchFactor(1, T.SPLIT_RIGHT)

        layout.addWidget(splitter, stretch=1)

        # ── 底部导出栏 ──
        export_bar = self._create_export_bar()
        layout.addWidget(export_bar)

    # =========================================================================
    # 顶部工具栏
    # =========================================================================

    def _create_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-bottom: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        icon = QLabel("🎨")
        icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        title = QLabel("编辑打磨")
        title.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; background: transparent; border: none;"
        )
        layout.addWidget(icon)
        layout.addWidget(title)

        layout.addStretch()

        # 幻灯片计数
        self._slide_counter = QLabel("幻灯片: 0")
        self._slide_counter.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(self._slide_counter)

        return bar

    # =========================================================================
    # 中间 PPT 编辑区
    # =========================================================================

    def _create_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 缩略图条 ──
        self._thumb_strip = self._create_thumb_strip()
        layout.addWidget(self._thumb_strip)

        # ── 幻灯片预览区 ──
        self._preview_area = self._create_preview_area()
        layout.addWidget(self._preview_area, stretch=1)

        # ── 版式标签栏 ──
        self._layout_bar = self._create_layout_bar()
        layout.addWidget(self._layout_bar)

        return panel

    def _create_thumb_strip(self) -> QFrame:
        """缩略图导航条（顶部水平滚动）"""
        frame = QFrame()
        frame.setFixedHeight(T.THUMB_HEIGHT + 20)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-bottom: 1px solid {T.STROKE_SUBTLE};
            }}
        """)

        # ★ 必须将 scroll 添加到 frame 的 layout 中
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._thumb_container = QWidget()
        self._thumb_layout = QHBoxLayout(self._thumb_container)
        self._thumb_layout.setContentsMargins(8, 6, 8, 6)
        self._thumb_layout.setSpacing(6)
        scroll.setWidget(self._thumb_container)
        frame_layout.addWidget(scroll)

        # 占位提示
        self._thumb_placeholder = QLabel("（生成幻灯片后显示缩略图）")
        self._thumb_placeholder.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none;"
        )
        self._thumb_layout.addWidget(self._thumb_placeholder)

        return frame

    def _create_preview_area(self) -> QWidget:
        """幻灯片预览区（16:9 白色画布）"""
        area = QWidget()
        area.setStyleSheet(f"background-color: {T.BG_PRIMARY};")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(20, 16, 20, 16)

        # 使用 Studio 的 SlideRenderer 进行可视化渲染
        # 支持图表、流程图、表格、图文混排等全部 layout 类型
        self._preview_renderer = SlideRenderer()
        self._preview_renderer.setStyleSheet("border-radius: 4px; border: 1px solid #e0e0e0;")
        self._preview_renderer.setMinimumHeight(300)
        # 连接 SlideRenderer 全部信号（与 Studio 对齐）
        self._preview_renderer.title_double_clicked.connect(self._on_title_dblclick)
        self._preview_renderer.element_clicked.connect(self._on_element_clicked)
        self._preview_renderer.edit_requested.connect(self._on_edit_requested)
        self._preview_renderer.text_dropped.connect(self._on_text_dropped)
        self._preview_renderer.item_reorder_requested.connect(self._on_item_reorder)
        self._preview_renderer.item_moved.connect(self._on_item_moved)
        self._preview_renderer.table_cell_edit_requested.connect(self._on_table_cell_edit)
        layout.addWidget(self._preview_renderer, stretch=1)

        # InlineEditor（内联编辑器，悬浮在 renderer 上方）
        self._inline_editor = InlineEditor(self._preview_renderer)
        self._inline_editor.hide()
        self._inline_editor.editing_finished.connect(self._on_inline_edit_done)
        self._inline_editor.editing_cancelled.connect(self._on_inline_edit_cancel)

        # 状态 overlay（加载中/错误时显示，正常渲染时隐藏）
        self._status_overlay = QLabel("")
        self._status_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_overlay.setWordWrap(True)
        self._status_overlay.setVisible(False)
        self._status_overlay.setStyleSheet(
            "background: #fafafa; border: 1px solid #e0e0e0; "
            "border-radius: 6px; padding: 20px; font-size: 14px;"
        )
        # overlay 覆盖在 renderer 上方
        self._status_overlay.setParent(self._preview_renderer)
        self._status_overlay.setGeometry(self._preview_renderer.rect())
        self._status_overlay.raise_()

        # 页码
        self._page_label = QLabel("— / —")
        self._page_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none;"
        )
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._page_label)

        return area

    def _create_layout_bar(self) -> QFrame:
        """版式标签栏（底部）"""
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-top: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        for tag_label, tag_key, tag_tip in T.LAYOUT_TAGS:
            btn = QPushButton(tag_label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setToolTip(tag_tip)
            btn.setStyleSheet(self._tag_style(tag_key == "text"))
            btn.clicked.connect(lambda checked, k=tag_key: self._on_layout_change(k))
            layout.addWidget(btn)

        layout.addStretch()
        return frame

    # =========================================================================
    # 右侧原文面板
    # =========================================================================

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {T.BG_ELEVATED};
                border-left: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 原文头部 ──
        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-bottom: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        source_icon = QLabel("📄")
        source_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        source_label = QLabel("原文")
        source_label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; background: transparent; border: none;"
        )
        header_layout.addWidget(source_icon)
        header_layout.addWidget(source_label)
        header_layout.addStretch()

        # 覆盖率进度条
        self._coverage_bar = QProgressBar()
        self._coverage_bar.setFixedWidth(100)
        self._coverage_bar.setFixedHeight(8)
        self._coverage_bar.setRange(0, 100)
        self._coverage_bar.setValue(0)
        self._coverage_bar.setTextVisible(False)
        self._coverage_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {T.BG_INPUT};
                border-radius: 4px; border: none;
            }}
            QProgressBar::chunk {{
                background-color: {T.STATUS_ONLINE};
                border-radius: 4px;
            }}
        """)
        header_layout.addWidget(self._coverage_bar)
        self._coverage_label = QLabel("0%")
        self._coverage_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none;"
        )
        header_layout.addWidget(self._coverage_label)
        layout.addWidget(header)

        # ── 重新提炼栏 ──
        reextract = QFrame()
        reextract.setFixedHeight(38)
        reextract.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_PRIMARY};
                border-bottom: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        reextract_layout = QHBoxLayout(reextract)
        reextract_layout.setContentsMargins(10, 4, 10, 4)
        reextract_layout.setSpacing(6)

        self._reextract_input = QLineEdit()
        self._reextract_input.setPlaceholderText("更关注...")
        self._reextract_input.setStyleSheet(self._input_style())
        self._reextract_input.setMaximumWidth(160)
        reextract_layout.addWidget(self._reextract_input)

        reextract_btn = QPushButton("↻ 重新提炼")
        reextract_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reextract_btn.setFixedHeight(26)
        reextract_btn.setStyleSheet(self._small_btn_style())
        reextract_btn.clicked.connect(self._on_reextract)
        reextract_layout.addWidget(reextract_btn)
        reextract_layout.addStretch()
        layout.addWidget(reextract)

        # ── 原文文本区（映射标签占位）──
        self._source_scroll = QScrollArea()
        self._source_scroll.setWidgetResizable(True)
        self._source_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._source_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self._source_content = QWidget()
        self._source_layout = QVBoxLayout(self._source_content)
        self._source_layout.setContentsMargins(12, 8, 12, 8)
        self._source_layout.setSpacing(6)

        # 占位提示
        self._source_placeholder = QLabel("（加载原文后显示段落和映射标签）")
        self._source_placeholder.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: transparent; border: none;"
        )
        self._source_layout.addWidget(self._source_placeholder)

        self._source_scroll.setWidget(self._source_content)
        layout.addWidget(self._source_scroll, stretch=1)

        # ── AI 输入（底部）──
        ai_bar = QFrame()
        ai_bar.setFixedHeight(44)
        ai_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_PRIMARY};
                border-top: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        ai_layout = QHBoxLayout(ai_bar)
        ai_layout.setContentsMargins(10, 6, 10, 6)
        ai_layout.setSpacing(6)

        ai_icon = QLabel("🤖")
        ai_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
        ai_layout.addWidget(ai_icon)

        self._ai_input = QLineEdit()
        self._ai_input.setPlaceholderText("如：把第2段移到第4页、标题改短...")
        self._ai_input.setStyleSheet(self._input_style())
        self._ai_input.returnPressed.connect(self._on_ai_send)
        ai_layout.addWidget(self._ai_input)

        ai_send_btn = QPushButton("▶")
        ai_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_send_btn.setFixedSize(28, 28)
        ai_send_btn.setStyleSheet(self._send_btn_style())
        ai_send_btn.clicked.connect(self._on_ai_send)
        ai_layout.addWidget(ai_send_btn)

        layout.addWidget(ai_bar)

        return panel

    # =========================================================================
    # 导出栏
    # =========================================================================

    def _create_export_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-top: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)

        layout.addStretch()

        export_btn = QPushButton("💾 导出 PPT")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setMinimumHeight(T.BTN_LARGE_HEIGHT)
        export_btn.setMinimumWidth(140)
        export_btn.setStyleSheet(self._cta_btn_style())
        export_btn.clicked.connect(self._on_export)
        layout.addWidget(export_btn)

        return bar

    # =========================================================================
    # 公共方法
    # =========================================================================

    def load_data(self, text: str, strategy_config: dict, slides_data: list = None,
                   preserve_slide: bool = False):
        """加载数据（Stage 2 提交后调用）

        Args:
            preserve_slide: True 时保留当前幻灯片位置（AI 修改后刷新用），
                           False 时重置到第一页（首次加载用）
        """
        saved_slide = self._current_slide if preserve_slide else 0
        self._text = text
        self._strategy_config = strategy_config
        self._slides_data = slides_data or []

        # 初始化渲染指令调度器
        if self._slides_data:
            try:
                self._render_dispatcher = RenderDispatcher(self._slides_data, text)
            except Exception as e:
                logger.warning("Stage 3: RenderDispatcher init failed: %s", e)
                self._render_dispatcher = None
        else:
            self._render_dispatcher = None

        # ★ 先加载幻灯片（确保 _slides_data 已更新）→ 再加载原文（构建正确的映射标签）
        if self._slides_data:
            self._load_slides(self._slides_data, saved_slide)
            print(f"[v5plus] Stage3: loaded {len(self._slides_data)} slides")
        else:
            self._show_loading_state()
            print("[v5plus] Stage3: showing loading state (no slides yet)")

        # 加载原文到右侧面板（依赖 self._slides_data 构建映射标签）
        self._load_source_text(text)

        # 高亮当前幻灯片对应的原文段落
        if self._slides_data:
            self._highlight_source_paragraphs(self._current_slide)

        self._slide_counter.setText(f"幻灯片: {len(self._slides_data)}")
        logger.info("Stage 3: loaded %d chars, strategy=%s, %d slides",
                     len(text), strategy_config.get("strategy", "?"),
                     len(self._slides_data))

    def _show_loading_state(self):
        """显示 PPT 生成中的加载状态"""
        # 清空旧缩略图
        while self._thumb_layout.count():
            item = self._thumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._thumb_layout.addStretch()

        # 预览区显示加载提示（通过 overlay）
        self._status_overlay.setText(
            "<div style='color: #4da6ff; font-size: 18px; font-weight: bold;'>"
            "⏳ PPT 正在生成中...</div>"
            "<div style='color: #888; margin-top: 12px;'>"
            "AI 正在分析文档并生成幻灯片，请稍候...<br>"
            "生成完成后将自动显示。</div>"
        )
        self._status_overlay.setGeometry(self._preview_renderer.rect())
        self._status_overlay.raise_()
        self._status_overlay.setVisible(True)
        self._page_label.setText("0 / 0")

    def show_error_state(self, error_msg: str):
        """显示 PPT 生成失败的错误状态"""
        # 清空旧缩略图
        while self._thumb_layout.count():
            item = self._thumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._thumb_layout.addStretch()

        # 预览区显示错误提示（通过 overlay）
        self._status_overlay.setText(
            f"<div style='color: #e74c3c; font-size: 18px; font-weight: bold;'>"
            f"❗ PPT 生成失败</div>"
            f"<div style='color: #c0392b; font-size: 12px; margin-top: 12px;'>"
            f"生成幻灯片时发生错误：{error_msg}<br><br>"
            f"请返回上一步重试。</div>"
        )
        self._status_overlay.setGeometry(self._preview_renderer.rect())
        self._status_overlay.raise_()
        self._status_overlay.setVisible(True)
        self._page_label.setText("0 / 0")
        self._slide_counter.setText("幻灯片: 0")

    # =========================================================================
    # SlideRenderer 信号处理（与 Studio 完全对齐）
    # =========================================================================

    def _on_title_dblclick(self):
        """Click-to-Edit: 双击标题"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        slide = self._slides_data[self._current_slide]
        title = slide.get("title", "")
        telemetry().emit(
            "V5PLUS_STAGE3_EDIT_TITLE",
            session_id=self._session_id,
            slide_index=self._current_slide,
        )
        # 通过 InlineEditor 弹出编辑框
        self._inline_editor.element_type = "title"
        self._inline_editor.element_index = -1
        self._inline_editor.setText(title)
        self._inline_editor.show()
        self._inline_editor.setFocus()
        self._inline_editor.selectAll()
        logger.info("Stage 3: title click-to-edit (slide %d)", self._current_slide)

    def _on_element_clicked(self, elem_type: str, elem_index: int):
        """元素点击（记录选中状态）"""
        logger.debug("Stage 3: element clicked %s[%d]", elem_type, elem_index)

    def _on_edit_requested(self, elem_type: str, elem_index: int, text: str):
        """双击元素触发内联编辑"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        # InlineEditor 弹出编辑框（rect() 返回 QRect，需转为 QRectF）
        from PyQt6.QtCore import QRectF
        self._inline_editor.start_editing(elem_type, elem_index, text,
                                           QRectF(self._preview_renderer.rect()))
        telemetry().emit(
            "V5PLUS_STAGE3_EDIT_COMMIT",
            session_id=self._session_id,
            slide_index=self._current_slide,
            field=elem_type,
        )
        logger.info("Stage 3: edit requested %s[%d] (slide %d)",
                     elem_type, elem_index, self._current_slide)

    def _on_inline_edit_done(self, elem_type: str, new_text: str, elem_index: int):
        """内联编辑确认：更新 slides_data + 刷新预览"""
        self._inline_editor.hide()
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        slide = self._slides_data[self._current_slide]
        changed = False
        if elem_type == "title":
            old = slide.get("title", "")
            if old != new_text:
                slide["title"] = new_text
                changed = True
        elif elem_type == "subtitle":
            old = slide.get("subtitle", "")
            if old != new_text:
                slide["subtitle"] = new_text
                changed = True
        elif elem_type == "item" and 0 <= elem_index < len(slide.get("items", [])):
            item = slide["items"][elem_index]
            old = item.get("text", "") if isinstance(item, dict) else str(item)
            if old != new_text:
                if isinstance(item, dict):
                    item["text"] = new_text
                else:
                    slide["items"][elem_index] = {"text": new_text}
                changed = True

        elif elem_type == "table_cell":
            # 更新表格单元格
            t_row = elem_index // 1000
            t_col = elem_index % 1000
            for item in slide.get("items", []):
                if item.get("content_type") == "table":
                    table_data = item.get("table_data", {})
                    rows = table_data.get("rows", [])
                    if 0 <= t_row < len(rows) and 0 <= t_col < len(rows[t_row]):
                        old_val = str(rows[t_row][t_col])
                        if old_val != new_text:
                            rows[t_row][t_col] = new_text
                            changed = True
                    break

        if changed:
            self._update_preview(self._current_slide)
            self._update_thumb(self._current_slide)
            logger.info("Stage 3: inline edit applied %s[%d] (slide %d)",
                         elem_type, elem_index, self._current_slide)

    def _on_inline_edit_cancel(self):
        """内联编辑取消"""
        self._inline_editor.hide()

    def _on_text_dropped(self, text: str, elem_type: str, elem_index: int):
        """拖放文本到元素"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        slide = self._slides_data[self._current_slide]
        if elem_type == "title":
            slide["title"] = text
        elif elem_type == "subtitle":
            slide["subtitle"] = text
        elif elem_type == "item" and 0 <= elem_index < len(slide.get("items", [])):
            item = slide["items"][elem_index]
            if isinstance(item, dict):
                item["text"] = text
            else:
                slide["items"][elem_index] = {"text": text}
        self._update_preview(self._current_slide)
        self._update_thumb(self._current_slide)
        telemetry().emit(
            "V5PLUS_STAGE3_TEXT_DROPPED",
            session_id=self._session_id,
            slide_index=self._current_slide,
            elem_type=elem_type,
        )
        logger.info("Stage 3: text dropped on %s[%d] (slide %d)",
                     elem_type, elem_index, self._current_slide)

    def _on_item_reorder(self, from_idx: int, to_idx: int):
        """元素拖拽重排（slide 内 items 顺序调整）"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        slide = self._slides_data[self._current_slide]
        items = slide.get("items", [])
        if not (0 <= from_idx < len(items) and 0 <= to_idx <= len(items)):
            return
        if from_idx == to_idx or from_idx == to_idx - 1:
            return  # 无需移动

        # 执行重排
        item = items.pop(from_idx)
        # 调整插入位置：pop 之后，如果 to_idx > from_idx，需要减 1
        insert_at = to_idx if to_idx < from_idx else to_idx - 1
        items.insert(insert_at, item)

        self._update_preview(self._current_slide)
        self._update_thumb(self._current_slide)
        telemetry().emit(
            "V5PLUS_STAGE3_ITEM_REORDER",
            session_id=self._session_id,
            slide_index=self._current_slide,
            from_idx=from_idx,
            to_idx=to_idx,
        )
        print(f"[V5Plus] item reorder: {from_idx} → {insert_at} (slide {self._current_slide})")

    def _on_item_moved(self, item_idx: int, new_x: float, new_y: float):
        """元素自由拖拽定位完成"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return
        slide = self._slides_data[self._current_slide]
        items = slide.get("items", [])
        if not (0 <= item_idx < len(items)):
            return
        # custom_x/custom_y 已在 SlideRenderer.mouseMoveEvent 中实时更新
        # 这里只需埋点和刷新缩略图
        self._update_preview(self._current_slide)
        self._update_thumb(self._current_slide)
        telemetry().emit(
            "V5PLUS_STAGE3_ITEM_MOVED",
            session_id=self._session_id,
            slide_index=self._current_slide,
            item_idx=item_idx,
            new_x=round(new_x),
            new_y=round(new_y),
        )
        print(f"[V5Plus] item moved: idx={item_idx}, pos=({new_x:.0f},{new_y:.0f}) (slide {self._current_slide})")

    def _on_table_cell_edit(self, row: int, col: int, value: str):
        """表格单元格双击编辑"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return

        # 计算单元格在 renderer widget 中的坐标
        renderer = self._preview_renderer
        sf = renderer.scale_factor
        ox = renderer._offset_x
        oy = renderer._offset_y
        x_start, y_start, row_height = 100, 200, 45

        # 查找 table item 获取 col_width
        slide = self._slides_data[self._current_slide]
        col_width = 200  # 默认
        for item in slide.get('items', []):
            if item.get('content_type') == 'table':
                cols = item.get('table_data', {}).get('columns',
                        item.get('table_data', {}).get('headers', []))
                if cols:
                    col_width = min(200, (renderer.SLIDE_WIDTH - 200) // len(cols))
                break

        cell_x = ox + (x_start + col * col_width) * sf
        cell_y = oy + (y_start + (row + 1) * row_height) * sf
        cell_w = col_width * sf
        cell_h = row_height * sf

        from PyQt6.QtCore import QRectF
        rect = QRectF(cell_x, cell_y, cell_w, cell_h)

        # 设置 InlineEditor 定位到单元格
        self._inline_editor.element_type = "table_cell"
        self._inline_editor.element_index = row * 1000 + col
        self._inline_editor.setText(value)
        self._inline_editor.setGeometry(rect.toRect())
        self._inline_editor.show()
        self._inline_editor.setFocus()
        self._inline_editor.selectAll()

        # 暂存单元格坐标，编辑完成后更新
        self._editing_table_cell = (row, col)
        telemetry().emit(
            "V5PLUS_STAGE3_TABLE_CELL_EDIT",
            session_id=self._session_id,
            slide_index=self._current_slide,
            row=row, col=col,
        )

    def _on_layout_change(self, layout_key: str):
        """版式切换 → 更新数据 + 刷新预览"""
        if not self._slides_data or self._current_slide >= len(self._slides_data):
            return

        old_layout = self._slides_data[self._current_slide].get("layout", "text_only")
        self._slides_data[self._current_slide]["layout"] = layout_key
        telemetry().emit(
            "V5PLUS_STAGE3_LAYOUT_CHANGE",
            session_id=self._session_id,
            slide_index=self._current_slide,
            old_layout=old_layout,
            new_layout=layout_key,
        )
        self._update_preview(self._current_slide)
        logger.info("Stage 3: layout %s → %s (slide %d)",
                     old_layout, layout_key, self._current_slide)

    def _on_reextract(self):
        """重新提炼（通过 V5AgentWorker 走 LLM）"""
        instruction = self._reextract_input.text().strip()
        telemetry().emit(
            "V5PLUS_STAGE3_REEXTRACT",
            session_id=self._session_id,
            instruction_len=len(instruction),
        )

        if not self._text:
            print("[V5Plus] re-extract: no source text")
            self._reextract_input.clear()
            return

        # 使用共享 prompt 构建器（与 Studio 一致）
        reextract_prompt = build_ppt_reextract_prompt(instruction, self._text)

        self._reextract_input.clear()
        self._start_ai_worker(
            reextract_prompt,
            action_type="ppt",
            on_finished=self._on_reextract_finished,
        )
        print(f"[V5Plus] re-extract: sent to LLM (instruction='{instruction[:50]}...')")

    def _on_ai_send(self):
        """AI 指令发送（通过 V5AgentWorker 走 LLM）"""
        instruction = self._ai_input.text().strip()
        if not instruction:
            return

        self._last_instruction = instruction
        telemetry().emit(
            "V5PLUS_STAGE3_AI_SEND",
            session_id=self._session_id,
            instruction_len=len(instruction),
            slide_index=self._current_slide,
        )

        if not self._slides_data:
            print("[V5Plus] AI send: no slides data")
            self._ai_input.clear()
            return

        # 使用共享 prompt 构建器（与 Studio 一致，render_commands 格式）
        ai_prompt = build_ppt_modify_prompt(
            instruction, self._slides_data,
            current_slide_index=self._current_slide,
            original_text=self._text,
        )

        self._ai_input.clear()
        self._start_ai_worker(
            ai_prompt,
            action_type="ppt",
            on_finished=self._on_ai_modify_finished,
        )
        print(f"[V5Plus] AI send: sent to LLM (slide={self._current_slide}, "
              f"instruction='{instruction[:60]}...')")

    def _on_export(self):
        """导出 PPT"""
        telemetry().emit(
            "V5PLUS_STAGE3_EXPORT",
            session_id=self._session_id,
            slide_count=len(self._slides_data),
        )
        logger.info("Stage 3: export requested (%d slides)", len(self._slides_data))
        self.export_requested.emit(self._slides_data)

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _load_source_text(self, text: str):
        """加载原文到右侧面板（段落切分 + 映射标签）"""
        # 清空旧的段落 widgets（保留 placeholder）
        for w in self._paragraph_widgets:
            w.deleteLater()
        self._paragraph_widgets.clear()
        if self._source_placeholder:
            self._source_placeholder.deleteLater()
            self._source_placeholder = None

        # 清理旧 stretch items
        while self._source_layout.count():
            item = self._source_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                # 非 stretch 的 widget 不应该出现在这里（已清理过）
                break
            elif item.spacerItem() is not None:
                # 删除 stretch spacer
                continue
            else:
                break

        # 段落切分
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1 and "\n" in text:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        slide_count = len(self._slides_data)
        total_paras = max(len(paragraphs), 1)
        self._paragraph_slide_map.clear()
        mapped_count = 0
        for i, para in enumerate(paragraphs):  # 显示所有段落
            # 计算该段落对应的 slide_index
            if slide_count > 0:
                si = min(int(i * slide_count / max(total_paras, 1)), slide_count - 1)
                mapped_count += 1
            else:
                si = -1
            self._paragraph_slide_map.append(si)
            row = self._create_paragraph_row(para, i, total_paras)
            self._source_layout.addWidget(row)
            self._paragraph_widgets.append(row)

        self._source_layout.addStretch()

        # 更新覆盖率
        coverage = int(mapped_count / max(1, len(paragraphs)) * 100)
        self._coverage_bar.setValue(coverage)
        self._coverage_label.setText(f"{coverage}%")
        print(f"[v5plus] Stage3: source loaded — {len(paragraphs)} paragraphs, {slide_count} slides, coverage={coverage}%")

    def _create_paragraph_row(self, text: str, index: int, total_paras: int = 0) -> QFrame:
        """创建单段原文 + 映射标签"""
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-bottom: 1px solid {T.STROKE_SUBTLE};
                padding: 4px 0;
            }}
        """)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # 文本行
        text_row = QHBoxLayout()
        text_row.setSpacing(8)

        slide_count = len(self._slides_data)
        # 智能映射：按比例将段落分配给幻灯片
        if slide_count > 0:
            tp = total_paras or min(20, max(slide_count, 1))
            slide_idx = min(int(index * slide_count / max(tp, 1)), slide_count - 1)
            is_mapped = True
        else:
            slide_idx = 0
            is_mapped = False

        tag_color = T.SLIDE_TAG_COLORS[slide_idx % len(T.SLIDE_TAG_COLORS)]
        tag_text = f"S{slide_idx + 1}" if is_mapped else "+"
        tag_label = QLabel(tag_text)
        tag_label.setFixedHeight(20)
        tag_label.setMinimumWidth(28)
        tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_mapped:
            tag_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {tag_color};
                    color: #fff;
                    font-size: {T.FONT_TINY[0]}px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 1px 5px;
                }}
            """)
            tag_label.setCursor(Qt.CursorShape.PointingHandCursor)
            tag_label.setToolTip(f"点击跳转到幻灯片 {slide_idx + 1}")
            tag_label.mousePressEvent = lambda e, si=slide_idx: self._on_mapping_tag_click(si)
        else:
            tag_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #3c3c3c;
                    color: #888;
                    font-size: {T.FONT_TINY[0]}px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 1px 5px;
                }}
            """)
        text_row.addWidget(tag_label)

        # 段落文本（完整显示，支持拖拽到 SlideRenderer）
        display_text = text
        para_label = DraggableLabel(display_text)
        para_label.setWordWrap(True)
        para_label.setCursor(Qt.CursorShape.OpenHandCursor)
        para_label.setToolTip("可拖拽到左侧 PPT 预览区")
        para_label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: transparent; border: none;"
        )
        # 拖拽时发射埋点
        para_label.drag_started.connect(
            lambda t, idx=index: telemetry().emit(
                "V5PLUS_STAGE3_PARA_DRAG", session_id=self._session_id, para_index=idx
            )
        )
        text_row.addWidget(para_label, stretch=1)
        layout.addLayout(text_row)

        return row

    def _on_mapping_tag_click(self, slide_index: int):
        """点击映射标签 → 跳转到对应幻灯片 + 高亮原文段落"""
        telemetry().emit(
            "V5PLUS_STAGE3_MAPPING_CLICK",
            session_id=self._session_id,
            tag=f"S{slide_index + 1}",
            direction="tag_to_slide",
        )
        self._current_slide = slide_index
        self._update_preview(slide_index)
        self._update_thumb_selection(slide_index)
        self._highlight_source_paragraphs(slide_index)
        logger.info("Stage 3: mapping tag click → slide %d", slide_index)

    def _on_slide_select(self, slide_index: int):
        """点击缩略图 → 切换幻灯片 + 高亮对应原文段落"""
        telemetry().emit(
            "V5PLUS_STAGE3_SLIDE_SELECT",
            session_id=self._session_id,
            slide_index=slide_index,
        )
        self._current_slide = slide_index
        self._update_preview(slide_index)
        self._update_thumb_selection(slide_index)
        self._highlight_source_paragraphs(slide_index)

    def _update_preview(self, slide_index: int):
        """更新预览区内容（通过 SlideRenderer 可视化渲染）"""
        if not self._slides_data or slide_index >= len(self._slides_data):
            print(f"[V5Plus] _update_preview SKIP: slides={len(self._slides_data) if self._slides_data else 0}, idx={slide_index}")
            return

        slide = self._slides_data[slide_index]
        items = slide.get('items', [])
        item_types = [it.get('content_type', 'text') for it in items]
        print(f"[V5Plus] _update_preview: slide={slide_index}, items={len(items)}, types={item_types}")
        telemetry().emit(
            "V5PLUS_STAGE3_PREVIEW_UPDATE",
            session_id=self._session_id,
            slide_index=slide_index,
            items_count=len(items),
            item_types=item_types,
        )

        # 使用 Studio 的 SlideRenderer 进行可视化渲染
        # 自动处理 chart/flowchart/table/three_columns/image_right 等全部 layout 类型
        self._preview_renderer.set_slide(slide)

        self._page_label.setText(f"{slide_index + 1} / {len(self._slides_data)}")

    def _highlight_source_paragraphs(self, slide_index: int):
        """高亮映射到指定幻灯片的原文段落"""
        highlight_color = T.ACCENT_CONTROL
        for i, (widget, mapped_si) in enumerate(
            zip(self._paragraph_widgets, self._paragraph_slide_map)
        ):
            if mapped_si == slide_index:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(59, 130, 246, 0.08);
                        border-left: 3px solid {highlight_color};
                        border-bottom: 1px solid {T.STROKE_SUBTLE};
                        padding: 4px 0;
                    }}
                """)
            else:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                        border-bottom: 1px solid {T.STROKE_SUBTLE};
                        padding: 4px 0;
                    }}
                """)

    def _update_thumb_selection(self, slide_index: int):
        """更新缩略图选中状态"""
        for i in range(self._thumb_layout.count()):
            item = self._thumb_layout.itemAt(i)
            if item and item.widget():
                thumb = item.widget()
                is_selected = (i == slide_index)
                border_color = T.ACCENT_CONTROL if is_selected else T.STROKE_SUBTLE
                thumb.setStyleSheet(f"""
                    QFrame {{
                        background-color: {"#eef4ff" if is_selected else "#f8f8f8"};
                        border: 2px solid {border_color};
                        border-radius: 3px;
                    }}
                """)

    def _start_ai_worker(self, prompt: str, action_type: str = "ppt",
                         on_finished=None):
        """启动 V5AgentWorker 执行 AI 任务"""
        # 清理旧 worker：断开信号 → 停止 → 释放
        if self._ai_worker is not None:
            old = self._ai_worker
            try:
                old.finished_signal.disconnect(self._on_ai_worker_finished)
                old.error_signal.disconnect(self._on_ai_worker_error)
            except (TypeError, RuntimeError):
                pass
            if old.isRunning():
                old.stop()
                old.wait(2000)
            self._ai_worker = None

        self._ai_worker = V5AgentWorker(
            prompt=prompt,
            action_type=action_type,
            session_id=self._session_id,
            context_source="v5plus_stage3",
            is_new_task=True,
        )
        # 存储回调
        self._ai_on_finished = on_finished
        self._ai_worker.finished_signal.connect(self._on_ai_worker_finished)
        self._ai_worker.error_signal.connect(self._on_ai_worker_error)
        self._ai_worker.start()
        print(f"[V5Plus] AI worker started (action={action_type})")

    def _on_ai_worker_finished(self, full_text: str):
        """AI worker 完成回调"""
        print(f"[V5Plus] AI worker done — response {len(full_text)} chars")
        self._safely_reset_worker()
        # 调用存储的回调
        if hasattr(self, '_ai_on_finished') and self._ai_on_finished:
            cb = self._ai_on_finished
            self._ai_on_finished = None
            cb(full_text)

    def _on_ai_worker_error(self, error_msg: str):
        """AI worker 错误回调"""
        print(f"[V5Plus] AI worker ERROR — {error_msg}")
        logger.error("Stage 3: AI worker error: %s", error_msg)
        self._safely_reset_worker()
        # 用户可见的错误反馈
        if hasattr(self, '_ai_input') and self._ai_input:
            self._ai_input.setPlaceholderText(
                f"⚠️ AI 错误: {error_msg[:60]}"
            )

    def _safely_reset_worker(self):
        """安全清理 AI worker 引用"""
        if self._ai_worker is not None:
            worker = self._ai_worker
            self._ai_worker = None
            if worker.isRunning():
                worker.finished.connect(worker.deleteLater)
                if not worker.wait(3000):
                    worker.terminate()
                    worker.wait(1000)
            else:
                worker.deleteLater()

    def _on_ai_modify_finished(self, full_text: str):
        """AI 修改指令完成：批量操作 → 渲染指令 → JSON 解析（三级降级）"""
        from opencopilot.capabilities.ppt.render_command import BatchOperationParser

        # 0. 检查是否是批量操作
        if self._last_instruction and BatchOperationParser.is_batch_operation(self._last_instruction):
            batch_commands = BatchOperationParser.parse_batch_operation(
                self._last_instruction, self._slides_data, self._text
            )
            if batch_commands and self._render_dispatcher:
                results = self._render_dispatcher.dispatch_from_render_commands(
                    batch_commands, self._current_slide
                )
                success_count = sum(1 for r in results if r.success)
                if success_count > 0:
                    print(f"[V5Plus] AI modify: batch operation applied ({success_count}/{len(results)} operations)")
                    telemetry().emit(
                        "V5PLUS_STAGE3_BATCH_APPLIED",
                        session_id=self._session_id,
                        success=success_count,
                        total=len(results),
                    )
                    self.load_data(self._text, self._strategy_config, self._slides_data,
                                    preserve_slide=True)
                    return

        # 1. 优先尝试渲染指令解析
        if self._render_dispatcher:
            try:
                render_commands = RenderCommandParser.parse(full_text, self._text)
                if render_commands:
                    # 设置默认 slide_index 和 instruction（与 Studio 一致）
                    for cmd in render_commands:
                        if cmd.slide_index < 0:
                            cmd.slide_index = self._current_slide
                        cmd.instruction = self._last_instruction

                    print(f"[V5Plus] AI modify: parsed {len(render_commands)} render commands")
                    telemetry().emit(
                        "V5PLUS_STAGE3_RENDER_COMMANDS",
                        session_id=self._session_id,
                        count=len(render_commands),
                        types=[c.render_type for c in render_commands],
                    )
                    results = self._render_dispatcher.dispatch_from_render_commands(
                        render_commands, self._current_slide
                    )
                    success_count = sum(1 for r in results if r.success)
                    print(f"[V5Plus] dispatch result: {success_count}/{len(results)} success, slide={self._current_slide}, "
                          f"items_before={len(self._slides_data[self._current_slide].get('items', []))}")
                    if success_count > 0:
                        items_after = len(self._slides_data[self._current_slide].get('items', []))
                        print(f"[V5Plus] items_after={items_after}, calling load_data(preserve_slide=True)")
                        telemetry().emit(
                            "V5PLUS_STAGE3_LOAD_DATA_BEFORE",
                            session_id=self._session_id,
                            current_slide=self._current_slide,
                            items_count=items_after,
                        )
                        self.load_data(self._text, self._strategy_config, self._slides_data,
                                        preserve_slide=True)
                        telemetry().emit(
                            "V5PLUS_STAGE3_LOAD_DATA_AFTER",
                            session_id=self._session_id,
                            current_slide=self._current_slide,
                            slides_count=len(self._slides_data),
                        )
                        print(f"[V5Plus] load_data done, current_slide={self._current_slide}")
                        return
                    else:
                        print("[V5Plus] WARNING: dispatch reported 0 success, falling through to JSON")
            except Exception as e:
                logger.warning("Stage 3: render command parse failed, fallback to JSON: %s", e)
                print(f"[V5Plus] render command EXCEPTION: {e}")

        # 2. 回退到 JSON 解析
        slides = self._parse_slides_from_text(full_text)
        if slides:
            print(f"[V5Plus] AI modify: parsed {len(slides)} slides, reloading")
            self.load_data(self._text, self._strategy_config, slides, preserve_slide=True)
        else:
            print("[V5Plus] AI modify: failed to parse slides from response")
            logger.error("Stage 3: AI modify failed to parse response (%d chars): %s",
                        len(full_text), full_text[:200])
            telemetry().emit(
                "V5PLUS_STAGE3_PARSE_FAILED",
                session_id=self._session_id,
                response_len=len(full_text),
                preview=full_text[:200],
            )
            # 用户可见的错误反馈
            if hasattr(self, '_ai_input') and self._ai_input:
                self._ai_input.setPlaceholderText(
                    "⚠️ AI 响应解析失败，请重试或换个指令"
                )

    def _on_reextract_finished(self, full_text: str):
        """重新提炼完成：解析新 slides 并重新加载"""
        slides = self._parse_slides_from_text(full_text)
        if slides:
            print(f"[V5Plus] Re-extract: parsed {len(slides)} slides, reloading")
            self.load_data(self._text, self._strategy_config, slides, preserve_slide=True)
        else:
            print("[V5Plus] Re-extract: failed to parse slides from response")

    @staticmethod
    def _parse_slides_from_text(text: str) -> list:
        """从 AI 输出文本中解析 JSON slides（代理到共享模块）"""
        return parse_slides_from_text(text)

    def _load_slides(self, slides: list, target_slide: int = 0):
        """加载幻灯片数据 → 更新缩略图 + 预览"""
        self._slides_data = slides

        # 隐藏加载/错误 overlay
        self._status_overlay.setVisible(False)
        self._status_overlay.setGeometry(self._preview_renderer.rect())
        self._status_overlay.raise_()

        # 清空缩略图（立即销毁旧 widget，避免 deleteLater 延迟干扰）
        while self._thumb_layout.count():
            item = self._thumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 生成缩略图
        for i, slide in enumerate(slides):
            thumb = self._create_thumb(i, slide)
            self._thumb_layout.addWidget(thumb)

        self._thumb_layout.addStretch()

        # 显示目标幻灯片（AI 修改后保留原位，首次加载显示第一页）
        if slides:
            self._current_slide = max(0, min(target_slide, len(slides) - 1))
            self._update_preview(self._current_slide)

        self._slide_counter.setText(f"幻灯片: {len(slides)}")

    def _update_thumb(self, slide_index: int):
        """更新指定缩略图的标题文本"""
        if 0 <= slide_index < self._thumb_layout.count():
            item = self._thumb_layout.itemAt(slide_index)
            if item and item.widget():
                thumb = item.widget()
                labels = thumb.findChildren(QLabel)
                if labels and self._slides_data and slide_index < len(self._slides_data):
                    labels[0].setText(self._slides_data[slide_index].get("title", f"S{slide_index + 1}")[:8])

    def _create_thumb(self, index: int, slide: dict) -> QFrame:
        """创建单个缩略图"""
        thumb = QFrame()
        thumb.setFixedSize(T.THUMB_WIDTH, T.THUMB_HEIGHT)
        thumb.setCursor(Qt.CursorShape.PointingHandCursor)

        is_selected = (index == self._current_slide)
        border_color = T.ACCENT_CONTROL if is_selected else T.STROKE_SUBTLE
        thumb.setStyleSheet(f"""
            QFrame {{
                background-color: #f8f8f8;
                border: 2px solid {border_color};
                border-radius: 3px;
            }}
        """)

        layout = QVBoxLayout(thumb)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(0)

        title = QLabel(slide.get("title", f"S{index + 1}")[:8])
        title.setStyleSheet(
            "color: #333; font-size: 7px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        layout.addWidget(title)

        num = QLabel(str(index + 1))
        num.setStyleSheet(
            "color: #999; font-size: 8px; "
            "background: transparent; border: none;"
        )
        num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(num)

        thumb.mousePressEvent = lambda e, idx=index: self._on_slide_select(idx)
        return thumb

    # =========================================================================
    # 样式工具
    # =========================================================================

    @staticmethod
    def _tag_style(is_active: bool) -> str:
        bg = T.ACCENT_CONTROL if is_active else T.BTN_ACTION_BG
        color = "#fff" if is_active else T.TEXT_SECONDARY
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: none; border-radius: 4px;
                padding: 2px 8px;
                font-size: {T.FONT_TINY[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.ACCENT_HOVER if is_active else T.BTN_ACTION_HOVER};
                color: #fff;
            }}
        """

    @staticmethod
    def _input_style():
        return f"""
            QLineEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                border-radius: 5px;
                padding: 4px 8px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """

    @staticmethod
    def _small_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_ACTION_BG};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 5px;
                padding: 2px 10px;
                font-size: {T.FONT_CAPTION[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_ACTION_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """

    @staticmethod
    def _send_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL};
                color: #fff;
                border: none; border-radius: 14px;
                font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """

    @staticmethod
    def _cta_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_PRIMARY_BG};
                color: {T.BTN_PRIMARY_TEXT};
                border: none; border-radius: 8px;
                padding: 8px 24px;
                font-size: {T.FONT_BODY[0] + 1}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
        """
