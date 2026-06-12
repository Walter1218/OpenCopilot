"""Stage 1: 输入原文 — 空状态引导页

仅在无文本上下文时显示。用户粘贴/输入原文后点击"分析文档结构"进入 Stage 2。
支持文件拖放（.txt/.md），拖入后自动读取并跳转。
"""
import os
import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame,
)

from gui.v5plus import tokens_plus as T
from gui.v5.telemetry import telemetry

logger = logging.getLogger(__name__)


class StageInputWidget(QWidget):
    """Stage 1：输入原文（空状态页）"""

    # 信号：用户提交文本 → 进入 Stage 2
    submitted = pyqtSignal(str)  # text

    def __init__(self, session_id: str = "", parent=None):
        super().__init__(parent)
        self._session_id = session_id
        self._init_ui()
        telemetry().emit("V5PLUS_STAGE1_OPEN", session_id=self._session_id)
        logger.info("Stage 1: opened (session=%s)", self._session_id[:8])

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(16)

        # ── 标题区 ──
        title_row = QHBoxLayout()
        icon = QLabel("🚦")
        icon.setStyleSheet(f"font-size: 22px; background: transparent; border: none;")
        title = QLabel("PPT 共创工作台")
        title.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_TITLE[0] + 2}px; background: transparent; border: none;"
        )
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # ── 引导文案 ──
        hint = QLabel("粘贴或输入你的原文，支持技术方案、工作报告、产品介绍等")
        hint.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: transparent; border: none;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ── 输入区 ──
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            "在此粘贴文档内容...\n\n"
            "支持 .txt / .md 文件拖放\n"
            "粘贴后自动统计字数和段落"
        )
        self._text_edit.setAcceptDrops(True)
        self._text_edit.setAcceptRichText(False)
        self._text_edit.setMinimumHeight(200)
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1.5px solid {T.STROKE_BORDER};
                border-radius: 8px;
                padding: 12px 14px;
                font-size: {T.FONT_BODY[0] + 1}px;
                selection-background-color: {T.BG_SELECTED};
            }}
            QTextEdit:focus {{
                border: 1.5px solid {T.STROKE_FOCUS};
            }}
        """)
        self._text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._text_edit, stretch=1)

        # ── 统计栏 ──
        self._stats_row = QHBoxLayout()
        self._char_label = QLabel("已输入 0 字")
        self._char_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: transparent; border: none;"
        )
        self._para_label = QLabel("检测到 0 个段落")
        self._para_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: transparent; border: none;"
        )
        self._stats_row.addWidget(self._char_label)
        self._stats_row.addStretch()
        self._stats_row.addWidget(self._para_label)
        layout.addLayout(self._stats_row)

        # ── CTA 按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._submit_btn = QPushButton("分析文档结构 →")
        self._submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._submit_btn.setMinimumHeight(T.BTN_LARGE_HEIGHT)
        self._submit_btn.setMinimumWidth(180)
        self._submit_btn.setStyleSheet(self._cta_btn_style())
        self._submit_btn.setEnabled(False)
        self._submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(self._submit_btn)
        layout.addLayout(btn_row)

        # ── 拖放提示 ──
        drag_hint = QLabel("💡 也可以直接拖放 .txt / .md 文件到上方区域")
        drag_hint.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none; padding-top: 4px;"
        )
        drag_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(drag_hint)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def set_text(self, text: str):
        """外部设置文本（如从剪贴板恢复）"""
        if text:
            self._text_edit.setPlainText(text)

    def get_text(self) -> str:
        return self._text_edit.toPlainText().strip()

    # =========================================================================
    # 事件
    # =========================================================================

    def _on_text_changed(self):
        """实时字数统计 + 段落检测（纯前端，<50ms）"""
        text = self._text_edit.toPlainText()
        char_count = len(text)
        # 段落检测：按连续空行分割
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        # 如果没有空行分隔，退化为按单行分割
        if len(paragraphs) <= 1 and "\n" in text:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        para_count = len(paragraphs)

        self._char_label.setText(f"已输入 {char_count:,} 字")
        self._para_label.setText(f"检测到 {para_count} 个段落")

        # 启用/禁用 CTA
        has_content = char_count > 10
        self._submit_btn.setEnabled(has_content)

        if has_content:
            telemetry().emit(
                "V5PLUS_STAGE1_INPUT",
                session_id=self._session_id,
                text_len=char_count,
                paragraph_count=para_count,
            )

    def _on_submit(self):
        """点击"分析文档结构"→ emit submitted 信号"""
        text = self.get_text()
        if not text:
            return

        char_count = len(text)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) <= 1 and "\n" in text:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        telemetry().emit(
            "V5PLUS_STAGE1_SUBMIT",
            session_id=self._session_id,
            text_len=char_count,
            paragraph_count=len(paragraphs),
        )
        logger.info("Stage 1: submitted %d chars, %d paragraphs",
                     char_count, len(paragraphs))
        self.submitted.emit(text)

    # =========================================================================
    # 拖放支持
    # =========================================================================

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path and path.lower().endswith((".txt", ".md", ".rst")):
                    event.acceptProposedAction()
                    self._text_edit.setStyleSheet(f"""
                        QTextEdit {{
                            background-color: {T.BG_SELECTED};
                            border: 2px dashed {T.STROKE_FOCUS};
                            border-radius: 8px;
                            padding: 12px 14px;
                            font-size: {T.FONT_BODY[0] + 1}px;
                        }}
                    """)
                    return
        if mime.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._reset_text_edit_style()

    def dropEvent(self, event):
        self._reset_text_edit_style()
        mime = event.mimeData()

        # 优先处理文件
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path and path.lower().endswith((".txt", ".md", ".rst")):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        file_name = os.path.basename(path)
                        self._text_edit.setPlainText(content)
                        telemetry().emit(
                            "V5PLUS_STAGE1_DRAG",
                            session_id=self._session_id,
                            file_type=os.path.splitext(file_name)[1],
                            file_name=file_name,
                            text_len=len(content),
                        )
                        logger.info("Stage 1: drag-drop file '%s' (%d chars)",
                                     file_name, len(content))
                        # 自动提交
                        self._on_submit()
                        event.acceptProposedAction()
                        return
                    except Exception as e:
                        logger.error("Stage 1: failed to read file '%s': %s", path, e)

        # 处理文本拖放
        if mime.hasText():
            text = mime.text()
            if text:
                self._text_edit.setPlainText(text)
                telemetry().emit(
                    "V5PLUS_STAGE1_DRAG",
                    session_id=self._session_id,
                    file_type="text",
                    text_len=len(text),
                )
                logger.info("Stage 1: drag-drop text (%d chars)", len(text))

        event.acceptProposedAction()

    # =========================================================================
    # 样式工具
    # =========================================================================

    def _reset_text_edit_style(self):
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1.5px solid {T.STROKE_BORDER};
                border-radius: 8px;
                padding: 12px 14px;
                font-size: {T.FONT_BODY[0] + 1}px;
                selection-background-color: {T.BG_SELECTED};
            }}
            QTextEdit:focus {{
                border: 1.5px solid {T.STROKE_FOCUS};
            }}
        """)

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
            QPushButton:disabled {{
                background-color: {T.BTN_ACTION_BG};
                color: {T.TEXT_TERTIARY};
            }}
        """
