"""StudioTabV5 — Studio Tab 入口壳（Launcher 卡片 + 状态文案）"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QHBoxLayout, QLineEdit,
)

from gui.v5 import tokens as T
from gui.v5.telemetry import telemetry
from gui.v5 import bridge


class StudioTabV5(QWidget):
    """Studio Tab: PPT 共创工作台入口"""

    def __init__(self, nav):
        super().__init__()
        self.nav = nav
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

        # ── 快速输入区 ──
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)

        self._quick_input = QLineEdit()
        self._quick_input.setPlaceholderText("粘贴文本或输入主题，直接打开 Studio...")
        self._quick_input.setStyleSheet(f"""
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
        self._quick_input.returnPressed.connect(self._on_quick_open)

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

        quick_row.addWidget(self._quick_input, stretch=1)
        quick_row.addWidget(quick_btn)
        layout.addLayout(quick_row)

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
        telemetry().emit("V5_STAB_OPEN_STUDIO")
        self.nav.open_studio()

    def _on_quick_open(self):
        """快速创建：读取输入文本并打开 Studio"""
        text = self._quick_input.text().strip()
        if not text:
            self._status_label.setText("⚠️ 请输入内容或粘贴文本")
            self._status_label.setStyleSheet(
                f"color: {T.STATUS_WARNING}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
            )
            return

        # 尝试从剪贴板补充
        if len(text) < 50:
            clip = bridge.get_clipboard_text()
            clip_text = clip.get("text", "")
            if clip_text and len(clip_text) > len(text):
                text = clip_text
                self._quick_input.setText(text[:100] + "…")

        telemetry().emit("V5_STAB_QUICK_OPEN", text_len=len(text))
        self.nav.open_studio(text=text)
        self._status_label.setText(f"✅ 已打开 Studio，导入 {len(text)} 字符")
        self._status_label.setStyleSheet(
            f"color: {T.STATUS_ONLINE}; font-size: {T.FONT_CAPTION[0]}px; padding: 4px 0;"
        )
        print(f"[v5] StudioTab: 快速创建 → {len(text)} 字符")

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
