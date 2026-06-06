"""StudioWindowV5 — PPT 共创工作台 4-Panel 窗口壳 (~1200×800)"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSplitter, QTextEdit, QLineEdit,
    QFrame, QGraphicsDropShadowEffect, QApplication,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge


class StudioWindowV5(QWidget):
    """PPT 共创工作台：Source | Thumbs+Outline | Preview + AI Chat"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
        self.slides_data = []
        self._init_ui()
        telemetry().window_event("V5_SWIN_CREATE", "studio_window")

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(*T.WINDOW_STUDIO)
        self.setMinimumSize(*T.WINDOW_STUDIO_MIN)

        # 外层 Frame
        self._frame = QFrame(self)
        self._frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_PRIMARY};
                border-radius: {T.FRAME_RADIUS}px;
                border: 1.5px solid {T.STROKE_BORDER};
            }}
        """)
        self._frame.resize(T.WINDOW_STUDIO[0] - 20, T.WINDOW_STUDIO[1] - 20)
        self._frame.move(T.FRAME_MARGIN, T.FRAME_MARGIN)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(T.SHADOW_BLUR)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        self._frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        # ── Title Bar ──
        title_bar = QHBoxLayout()
        title_label = QLabel("🚦 PPT 人机共创工作台")
        title_label.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-weight: bold; "
            f"font-size: {T.FONT_TITLE[0]}px; background: transparent; border: none;"
        )

        self._stats_label = QLabel("幻灯片:0  要点:0  原文:0%")
        self._stats_label.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )

        btn_close = QPushButton("✕")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"font-size: 14px; color: #888; }}"
            f"QPushButton:hover {{ color: #ff5555; }}"
        )
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(title_label)
        title_bar.addStretch()
        title_bar.addWidget(self._stats_label)
        title_bar.addWidget(btn_close)
        layout.addLayout(title_bar)

        # ── 4-Panel Splitter ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel 1: Source (原文)
        source_panel = self._create_panel("📄 Source", "原文文本\n\n高亮已提取内容 (功能待接入)")
        splitter.addWidget(source_panel)

        # Panel 2: Thumbnails + Outline
        outline_panel = self._create_panel("📋 Outline", "缩略图导航 (功能待接入)\n\n标题 / 副标题\n版式 / 要点")
        splitter.addWidget(outline_panel)

        # Panel 3: Preview
        preview_panel = self._create_panel("👁 Preview", "WYSIWYG 预览 (功能待接入)\n\nClick-to-Edit\n实时渲染")
        splitter.addWidget(preview_panel)

        # 比例: 25% : 30% : 45%
        splitter.setSizes([300, 360, 540])
        layout.addWidget(splitter, stretch=1)

        # ── AI Chat 占位区 ──
        chat_frame = QFrame()
        chat_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-radius: 8px;
                border: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        chat_frame.setMaximumHeight(120)
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(10, 6, 10, 6)
        chat_layout.setSpacing(4)

        chat_header = QLabel("🤖 AI 助手  ● Pipeline 在线  ↩0 ↪0")
        chat_header.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            "background: transparent; border: none;"
        )
        chat_layout.addWidget(chat_header)

        chat_input_row = QHBoxLayout()
        chat_input = QLineEdit()
        chat_input.setPlaceholderText("输入 AI 指令... (功能待接入)")
        chat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T.BG_INPUT}; color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER}; border-radius: 4px;
                padding: 4px 8px; font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """)
        send_btn = QPushButton("发送")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.ACCENT_CONTROL}; color: #000;
                border-radius: 4px; padding: 4px 12px; font-weight: bold;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{ background-color: {T.ACCENT_HOVER}; }}
        """)
        chat_input_row.addWidget(chat_input, stretch=1)
        chat_input_row.addWidget(send_btn)
        chat_layout.addLayout(chat_input_row)

        layout.addWidget(chat_frame)

        # ── 底部按钮栏 ──
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        for label, tip, handler in [
            ("取消", "关闭工作台", self.close),
            ("🔍 全屏预览", "全屏幻灯片预览", self._on_fullscreen_preview),
            ("💾 导出 PPT", "导出为 .pptx 文件", self._on_export_ppt),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            is_cta = "导出" in label
            btn.setStyleSheet(self._bottom_btn_style(cta=is_cta))
            btn.clicked.connect(handler)
            bottom_bar.addWidget(btn)
        layout.addLayout(bottom_bar)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def load_text(self, text: str):
        """加载文本到 Source Panel（由 NavigationManager 调用）"""
        t = telemetry()
        t.emit("V5_SWIN_LOAD_TEXT", text_len=len(text))
        self._stats_label.setText(
            f"幻灯片:0  要点:0  原文:{min(len(text), 5000)}字符"
        )

    # =========================================================================
    # 生命周期
    # =========================================================================

    def closeEvent(self, event):
        t = telemetry()
        t.emit("V5_SWIN_CLOSE", slides_count=len(self.slides_data))
        super().closeEvent(event)

    # =========================================================================
    # 非AI 事件处理
    # =========================================================================

    def _on_export_ppt(self):
        """导出 PPT（非AI: 直接调用 bridge）"""
        t = telemetry()
        t.emit("V5_SWIN_EXPORT_PPT", slides_count=len(self.slides_data))

        if not self.slides_data:
            self._stats_label.setText("⚠️ 无幻灯片数据可导出")
            print("[v5] StudioWindow: 导出失败 — slides_data 为空")
            return

        result = bridge.do_export_ppt(self.slides_data)
        if result.get("success"):
            self._stats_label.setText(
                f"✅ 已导出: {result.get('filename', '')} "
                f"({result.get('slide_count', 0)} 页, "
                f"{result.get('file_size', 0) / 1024:.0f}KB)"
            )
            print(f"[v5] StudioWindow: PPT 导出 → {result.get('file_path')}")
        else:
            self._stats_label.setText(f"❌ 导出失败: {result.get('message', '')}")
            print(f"[v5] StudioWindow: PPT 导出失败 — {result.get('message')}")

    def _on_fullscreen_preview(self):
        """全屏预览（非AI: 展示幻灯片信息）"""
        t = telemetry()
        t.emit("V5_SWIN_FULLSCREEN", slides_count=len(self.slides_data))

        if self.slides_data:
            self._stats_label.setText(
                f"🔍 全屏预览: {len(self.slides_data)} 张幻灯片"
            )
            print(f"[v5] StudioWindow: 全屏预览 {len(self.slides_data)} 张")
        else:
            self._stats_label.setText("⚠️ 无幻灯片数据可预览")

    # =========================================================================
    # 工厂方法
    # =========================================================================

    @staticmethod
    def _create_panel(title: str, placeholder: str) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-radius: 8px;
                border: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel(title)
        header.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(header)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content.setPlainText(placeholder)
        content.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {T.TEXT_TERTIARY};
                font-size: {T.FONT_BODY[0]}px;
                border: none;
            }}
        """)
        layout.addWidget(content, stretch=1)
        return panel

    @staticmethod
    def _bottom_btn_style(cta=False):
        if cta:
            return f"""
                QPushButton {{
                    background-color: {T.BTN_PRIMARY_BG};
                    color: {T.BTN_PRIMARY_TEXT};
                    border: none; border-radius: 8px;
                    padding: {T.BTN_MEDIUM_PADDING};
                    font-size: {T.FONT_BODY[0]}px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
            """
        return f"""
            QPushButton {{
                background-color: {T.BTN_ACTION_BG};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 8px;
                padding: {T.BTN_MEDIUM_PADDING};
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_ACTION_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """
