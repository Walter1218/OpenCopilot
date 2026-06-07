"""
PPT 共创嵌入式工作台 (Compact Widget)

嵌入式版本，用于 Smart Copilot 卡片 Tab 5。
复用 outline_panel.SlideListWidget、preview_panel.SlideRenderer/InlineEditor。

实现改进:
- 缩略图导航 (thumbnail strip with quality badges)
- 内联主题选择器 (theme color swatches)
- 统一撤销栈 (manual + AI edits)
- 上下文快捷指令 (contextual quick actions)
- 预览点击编辑 (click-to-edit via InlineEditor)
- 流式 AI 反馈 (typing indicator)
- 差异预览 (diff preview before apply)
"""

import copy
import json
import os
import re
import threading
import uuid
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QPushButton,
    QLabel, QLineEdit, QScrollArea, QFrame, QSizePolicy,
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
    QFileDialog, QApplication, QDialog, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QKeySequence, QShortcut, QGuiApplication

from .outline_panel import SlideListWidget, OutlinePanel
from .source_panel import SourcePanel
from .preview_panel import SlideRenderer, InlineEditor
from ppt_generator import generate_ppt_from_json, clean_markdown
from ppt_generator_via_html import generate_ppt_via_html


# ============================================================
# Theme definitions (mirrored from CoCreationDialog)
# ============================================================
THEMES = {
    "dark": {
        "name": "深色", "bg": "#1e1e1e", "fg": "#d4d4d4",
        "toolbar": "#2d2d2d", "btn": "#3c3c3c", "btn_hover": "#4c4c4c",
        "accent": "#007bff", "border": "#555",
    },
    "light": {
        "name": "浅色", "bg": "#f5f5f5", "fg": "#333",
        "toolbar": "#fff", "btn": "#e0e0e0", "btn_hover": "#d0d0d0",
        "accent": "#0066cc", "border": "#ccc",
    },
    "blue": {
        "name": "蓝", "bg": "#0d1b2a", "fg": "#e0e0e0",
        "toolbar": "#1b2838", "btn": "#2a4a6b", "btn_hover": "#3a5a7b",
        "accent": "#4da6ff", "border": "#3a5a7b",
    },
    "green": {
        "name": "绿", "bg": "#0a1f0a", "fg": "#d4d4d4",
        "toolbar": "#1a2a1a", "btn": "#2a4a2a", "btn_hover": "#3a5a3a",
        "accent": "#4dff4d", "border": "#3a5a3a",
    },
}


# ============================================================
# AI Worker (reuses Pipeline pattern)
# ============================================================
class _AIWorker(QThread):
    """AI 处理线程 — 通过 call_agent_pipeline_sync"""

    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instruction = ""
        self.slides_data: List[dict] = []
        self.current_index = -1
        self.session_id = ""
        self.cancel_event = threading.Event()
        self.is_new_task = True  # First call in session = new task; subsequent = False

    def set_task(self, instruction: str, slides_data: list, index: int, sid: str = ""):
        self.instruction = instruction
        self.slides_data = slides_data
        self.current_index = index
        self.session_id = sid

    def run(self):
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability

            user_msg = self._build_message()
            session_id = self.session_id or f"ppt_tab_{uuid.uuid4().hex[:8]}"

            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Tab5 START | text_len={len(user_msg)}",
                        session_id=session_id, event="PPT_TAB5_START")

            full = ""
            for chunk in call_agent_pipeline_sync(
                text=user_msg, action_type="chat",
                session_id=session_id,
                context_source="ppt_editor",
                cancel_event=self.cancel_event,
                is_new_task=self.is_new_task,
            ):
                if self.cancel_event.is_set():
                    break
                full += chunk

            # After first successful call, subsequent calls are NOT new tasks
            self.is_new_task = False

            if full:
                obs.gui_log(f"PPT Tab5 DONE | output_len={len(full)}",
                            session_id=session_id, event="PPT_TAB5_DONE")
                self.response_ready.emit(full)
            else:
                obs.gui_log("PPT Tab5 EMPTY response",
                            session_id=session_id, event="PPT_TAB5_EMPTY", level="WARN")
                self.error_occurred.emit("Agent 返回空响应，可能是模型配置问题")
        except Exception as e:
            try:
                from opencopilot.agent.observability import PipelineObservability
                obs = PipelineObservability.get_instance()
                obs.gui_log(f"PPT Tab5 ERROR | err={e}",
                            session_id=self.session_id, event="PPT_TAB5_ERROR", level="ERROR")
            except Exception:
                pass
            self.error_occurred.emit(f"Pipeline 调用失败: {e}")

    def _build_message(self) -> str:
        """构建用户消息 — 当前页完整 + 相邻页摘要（token 友好）"""
        total = len(self.slides_data)
        idx = max(0, self.current_index) if self.current_index >= 0 else 0
        slide = self.slides_data[idx] if self.slides_data and idx < total else {}

        # Adjacent slide summaries
        prev_summary = self._summarize_slide(idx - 1) if idx > 0 else None
        next_summary = self._summarize_slide(idx + 1) if idx < total - 1 else None

        parts = [f"PPT 共 {total} 页，当前第 {idx + 1} 页。"]

        if prev_summary:
            parts.append(f"\n前一页（第 {idx} 页）摘要：{prev_summary}")

        parts.append(f"\n当前幻灯片：\n```json\n{json.dumps(slide, ensure_ascii=False, indent=2)}\n```")

        if next_summary:
            parts.append(f"\n后一页（第 {idx + 2} 页）摘要：{next_summary}")

        parts.append(f"\n用户指令：{self.instruction}")
        parts.append("\n请优先使用局部修改模式，只返回修改指令 JSON（不要返回完整数据）：")
        return "\n".join(parts)

    def _summarize_slide(self, idx: int) -> str:
        """生成单页幻灯片摘要（token 友好）"""
        if idx < 0 or idx >= len(self.slides_data):
            return ""
        slide = self.slides_data[idx]
        title = slide.get("title", "(无标题)")
        layout = slide.get("layout", "text_only")
        items = slide.get("items", [])
        item_texts = [it.get("text", "")[:20] for it in items[:3] if it.get("text")]
        items_str = "、".join(item_texts) if item_texts else "无要点"
        return f"标题：{title}，版式：{layout}，要点：{items_str}"


# ============================================================
# Thumbnail Widget (mini slide preview for list items)
# ============================================================
class _ThumbnailWidget(QWidget):
    """80x45 mini slide preview for list item widget"""

    def __init__(self, slide_data: dict, index: int, badge: str = "", parent=None):
        super().__init__(parent)
        self.slide_data = slide_data
        self.index = index
        self.badge = badge
        self.setFixedSize(90, 58)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Slide background
        p.setPen(QPen(QColor("#555"), 1))
        p.setBrush(QColor("#fafafc"))
        p.drawRoundedRect(2, 2, 76, 43, 3, 3)

        # Title text
        title = clean_markdown(self.slide_data.get("title", ""))[:12]
        if title:
            p.setPen(QColor("#333"))
            p.setFont(QFont("Helvetica Neue", 7, QFont.Weight.Bold))
            p.drawText(6, 14, 68, 14, Qt.AlignmentFlag.AlignLeft, title)

        # Layout label
        layout = self.slide_data.get("layout", "text_only")
        p.setPen(QColor("#999"))
        p.setFont(QFont("Helvetica Neue", 6))
        p.drawText(6, 30, 68, 10, Qt.AlignmentFlag.AlignLeft, layout)

        # Items count
        items = self.slide_data.get("items", [])
        p.drawText(6, 40, 68, 10, Qt.AlignmentFlag.AlignLeft, f"{len(items)} items")

        # Page number
        p.setPen(QColor("#aaa"))
        p.setFont(QFont("Helvetica Neue", 6))
        p.drawText(2, 56, 20, 10, Qt.AlignmentFlag.AlignLeft, str(self.index + 1))

        # Quality badge
        if self.badge:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ff9800"))
            p.drawEllipse(72, 0, 14, 14)
            p.setPen(QColor("#fff"))
            p.setFont(QFont("Helvetica Neue", 7, QFont.Weight.Bold))
            p.drawText(72, 0, 14, 14, Qt.AlignmentFlag.AlignCenter, self.badge)

        p.end()


# ============================================================
# CoCreationWidget (main)
# ============================================================
class CoCreationWidget(QWidget):
    """嵌入式 PPT 共创工作台"""

    # Signals
    slides_updated = pyqtSignal(list)
    slide_selected = pyqtSignal(int)
    export_requested = pyqtSignal(list)

    # Contextual quick action definitions by content type
    _ACTIONS_BY_TYPE = {
        "text": ["优化标题", "添加要点", "换版式", "精简内容", "转图表"],
        "table": ["格式化表格", "添加行", "添加列", "排序数据", "转图表"],
        "chart": ["更换图表类型", "更新数据", "调整配色", "添加图例"],
        "flowchart": ["添加步骤", "调整方向", "美化样式"],
        "image": ["更换图片", "调整布局", "添加说明"],
    }

    _ACTION_PROMPTS = {
        "优化标题": "请为当前幻灯片建议一个更有吸引力的标题",
        "添加要点": "请为当前幻灯片添加一个有价值的新要点",
        "换版式": "请根据当前内容特点建议更合适的版式",
        "精简内容": "请精简当前幻灯片内容，保留核心信息",
        "转图表": "请分析当前内容，将适合的部分转换为图表或表格",
        "格式化表格": "请优化当前表格的格式和排版",
        "添加行": "请为当前表格添加一行有价值的数据",
        "添加列": "请为当前表格添加一列",
        "排序数据": "请对当前表格数据按逻辑排序",
        "更换图表类型": "请根据数据特点建议更合适的图表类型",
        "更新数据": "请优化当前图表的数据展示",
        "调整配色": "请为当前图表建议更好的配色方案",
        "添加图例": "请为当前图表添加图例说明",
        "添加步骤": "请为当前流程图添加一个关键步骤",
        "调整方向": "请调整当前流程图的布局方向",
        "美化样式": "请美化当前幻灯片的视觉样式",
        "更换图片": "请建议适合当前内容的配图描述",
        "调整布局": "请调整当前图片布局",
        "添加说明": "请为当前图片添加说明文字",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 计时开始
        import time
        t0 = time.time()

        # State
        self.slides_data: List[dict] = []
        self.original_text: str = ""
        self.current_index: int = 0
        self._session_id = f"ppt_tab_{uuid.uuid4().hex[:8]}"
        self._theme = "dark"
        self._worker: Optional[_AIWorker] = None
        self._is_waiting: bool = False  # True when AI is generating outline
        self._is_generating: bool = False  # True when any AI generation is in progress

        # Unified undo stack: [(slides_snapshot, description, edit_type)]
        # edit_type: "ai" | "manual"
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._max_history = 50

        # Pending diff (before apply)
        self._pending_diff: Optional[Dict] = None
        self._last_instruction: str = ""

        # Sync guard — prevents recursive signal loops with OutlinePanel
        self._syncing: bool = False

        # SourceMatcher — 双向联动核心（load_slides 时初始化）
        self.source_matcher = None

        self._init_ui()
        self._connect_signals()
        self._update_empty_state()
        
        # 计时结束
        init_time = (time.time() - t0) * 1000
        try:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"CoCreationWidget INIT | elapsed={init_time:.0f}ms",
                        session_id=self._session_id, event="COCREATION_WIDGET_INIT")
        except Exception:
            pass

        # Async agent health check
        QTimer.singleShot(500, self._check_agent_health)

    # ============================================================
    # UI Construction
    # ============================================================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # --- Toolbar ---
        layout.addWidget(self._build_toolbar())

        # --- Main area: splitter (source | thumbnails | outline+form | preview) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel 1: Source panel (原文面板)
        self.source_panel = SourcePanel()
        self.source_panel.setMinimumWidth(150)
        self.splitter.addWidget(self.source_panel)

        # Panel 2: Thumbnail strip (缩略图导航)
        self.slide_list = SlideListWidget()
        self.slide_list.setMaximumWidth(130)
        self.slide_list.setMinimumWidth(90)
        self.splitter.addWidget(self.slide_list)

        # Panel 3: Outline + form editing panel (大纲+表单编辑)
        self.outline_panel = OutlinePanel()
        self.outline_panel.setMinimumWidth(280)
        self.splitter.addWidget(self.outline_panel)

        # Panel 4: Preview area
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        self.renderer = SlideRenderer()
        self.renderer.setMinimumSize(200, 112)
        self.renderer.setStyleSheet("""
            SlideRenderer {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)
        right_layout.addWidget(self.renderer, 1)

        # Inline editor for click-to-edit
        self.inline_editor = InlineEditor(self)
        self.inline_editor.hide()
        right_layout.addWidget(self.inline_editor)

        # Page indicator
        page_row = QHBoxLayout()
        self.page_label = QLabel("0 / 0")
        self.page_label.setStyleSheet("color: #888; font-size: 11px;")
        page_row.addStretch()
        page_row.addWidget(self.page_label)
        page_row.addStretch()
        right_layout.addLayout(page_row)

        self.splitter.addWidget(right)
        self.splitter.setSizes([200, 100, 320, 500])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setStretchFactor(3, 2)

        layout.addWidget(self.splitter, 1)

        # --- Quality badge area ---
        self.quality_bar = QLabel("")
        self.quality_bar.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 152, 0, 0.15);
                color: #ffb74d;
                border: 1px solid rgba(255, 152, 0, 0.3);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }
        """)
        self.quality_bar.setWordWrap(True)
        self.quality_bar.hide()
        layout.addWidget(self.quality_bar)

        # --- Quick actions ---
        self.actions_row = QHBoxLayout()
        self.actions_row.setSpacing(6)
        self._action_buttons: List[QPushButton] = []
        layout.addLayout(self.actions_row)

        # --- Diff preview area (hidden by default) ---
        self.diff_frame = QFrame()
        self.diff_frame.setStyleSheet("""
            QFrame {
                background-color: #1a2a1a;
                border: 1px solid #2a4a2a;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        diff_layout = QVBoxLayout(self.diff_frame)
        diff_layout.setContentsMargins(8, 6, 8, 6)
        diff_layout.setSpacing(4)
        self.diff_label = QLabel("")
        self.diff_label.setStyleSheet("color: #ccc; font-size: 11px; border: none; background: transparent;")
        self.diff_label.setWordWrap(True)
        diff_layout.addWidget(self.diff_label)
        diff_btns = QHBoxLayout()
        self.diff_accept_btn = QPushButton("Accept")
        self.diff_accept_btn.setStyleSheet("""
            QPushButton { background: #28a745; color: #fff; border: none; border-radius: 4px;
                          padding: 4px 12px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: #218838; }
        """)
        self.diff_reject_btn = QPushButton("Reject")
        self.diff_reject_btn.setStyleSheet("""
            QPushButton { background: #dc3545; color: #fff; border: none; border-radius: 4px;
                          padding: 4px 12px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: #c82333; }
        """)
        diff_btns.addWidget(self.diff_accept_btn)
        diff_btns.addWidget(self.diff_reject_btn)
        diff_btns.addStretch()
        diff_layout.addLayout(diff_btns)
        self.diff_frame.hide()
        layout.addWidget(self.diff_frame)

        # --- AI input row ---
        ai_row = QHBoxLayout()
        ai_row.setSpacing(6)

        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("输入 AI 指令，如：把标题改为...")
        self.ai_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c; color: #d4d4d4;
                border: 1px solid #555; border-radius: 4px;
                padding: 6px 10px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #007acc; }
        """)
        self.ai_input.returnPressed.connect(self._send_ai)
        ai_row.addWidget(self.ai_input)

        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setStyleSheet("""
            QPushButton { background: #007bff; color: #fff; border: none;
                          border-radius: 15px; font-size: 14px; }
            QPushButton:hover { background: #0056b3; }
            QPushButton:disabled { background: #3c3c3c; color: #666; }
        """)
        self.send_btn.clicked.connect(self._send_ai)
        ai_row.addWidget(self.send_btn)

        layout.addLayout(ai_row)

        # --- Typing indicator (hidden by default) ---
        self.typing_label = QLabel("")
        self.typing_label.setStyleSheet("color: #888; font-size: 11px;")
        self.typing_label.hide()
        layout.addWidget(self.typing_label)

        # --- Empty state panel (rich guidance) ---
        self.empty_panel = QWidget()
        empty_layout = QVBoxLayout(self.empty_panel)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(16)
        empty_layout.setContentsMargins(40, 40, 40, 40)

        # Status icon
        self.empty_icon = QLabel("📄")
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_icon.setStyleSheet("font-size: 48px; border: none; background: transparent;")
        empty_layout.addWidget(self.empty_icon)

        # Status title
        self.empty_title = QLabel("尚未加载 PPT 内容")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title.setStyleSheet("""
            QLabel {
                color: #d4d4d4; font-size: 18px; font-weight: bold;
                border: none; background: transparent;
            }
        """)
        empty_layout.addWidget(self.empty_title)

        # Status description
        self.empty_desc = QLabel("请粘贴或输入文本内容，AI 将自动生成 PPT 大纲")
        self.empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_desc.setWordWrap(True)
        self.empty_desc.setStyleSheet("""
            QLabel {
                color: #888; font-size: 13px;
                border: none; background: transparent;
            }
        """)
        empty_layout.addWidget(self.empty_desc)

        # Paste button
        self.paste_btn = QPushButton("📋 粘贴内容生成 PPT")
        self.paste_btn.setFixedSize(200, 40)
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background: #007bff; color: #fff; border: none;
                border-radius: 6px; padding: 8px 20px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #0056b3; }
        """)
        self.paste_btn.clicked.connect(self._paste_and_generate)
        empty_layout.addWidget(self.paste_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hint text
        self.empty_hint = QLabel("提示：也可以从左侧 Tab 1 或 Tab 3 导入内容")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setStyleSheet("""
            QLabel {
                color: #666; font-size: 11px;
                border: none; background: transparent;
            }
        """)
        empty_layout.addWidget(self.empty_hint)

        layout.addWidget(self.empty_panel)

        # Apply theme
        self._apply_theme()

    def _build_toolbar(self) -> QWidget:
        """Build compact toolbar: stats + theme picker + undo/redo + export"""
        bar = QWidget()
        bar.setStyleSheet(f"background: {THEMES[self._theme]['toolbar']}; border-radius: 4px;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(10)

        # Stats
        self.stats_label = QLabel("幻灯片: 0 | 要点: 0")
        self.stats_label.setStyleSheet("color: #888; font-size: 11px; border: none;")
        h.addWidget(self.stats_label)

        # Agent status indicator
        self.agent_status = QLabel("●")
        self.agent_status.setStyleSheet("color: #888; font-size: 11px; border: none;")
        self.agent_status.setToolTip("Agent Pipeline 状态检测中...")
        h.addWidget(self.agent_status)

        h.addStretch()

        # Theme picker (color swatches)
        for key, t in THEMES.items():
            swatch = QPushButton()
            swatch.setFixedSize(16, 16)
            swatch.setToolTip(t["name"])
            swatch.setStyleSheet(f"""
                QPushButton {{
                    background: {t['bg']};
                    border: {'2px solid ' + t['accent'] if key == self._theme else '1px solid #555'};
                    border-radius: 4px;
                }}
                QPushButton:hover {{ border: 2px solid {t['accent']}; }}
            """)
            swatch.clicked.connect(lambda checked, k=key: self._set_theme(k))
            h.addWidget(swatch)

        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        sep.setStyleSheet("background: #555; border: none;")
        h.addWidget(sep)

        # Undo
        self.undo_btn = QPushButton("↩")
        self.undo_btn.setFixedSize(22, 22)
        self.undo_btn.setToolTip("撤销 (Ctrl+Z)")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setStyleSheet("""
            QPushButton { background: #3c3c3c; color: #888; border: none;
                          border-radius: 11px; font-size: 13px; }
            QPushButton:hover { background: #4a4a4a; color: #ddd; }
            QPushButton:disabled { color: #555; }
        """)
        self.undo_btn.clicked.connect(self._undo)
        h.addWidget(self.undo_btn)

        # Redo
        self.redo_btn = QPushButton("↪")
        self.redo_btn.setFixedSize(22, 22)
        self.redo_btn.setToolTip("重做 (Ctrl+Y)")
        self.redo_btn.setEnabled(False)
        self.redo_btn.setStyleSheet("""
            QPushButton { background: #3c3c3c; color: #888; border: none;
                          border-radius: 11px; font-size: 13px; }
            QPushButton:hover { background: #4a4a4a; color: #ddd; }
            QPushButton:disabled { color: #555; }
        """)
        self.redo_btn.clicked.connect(self._redo)
        h.addWidget(self.redo_btn)

        # Source panel toggle
        self.source_toggle_btn = QPushButton("📄")
        self.source_toggle_btn.setFixedSize(22, 22)
        self.source_toggle_btn.setToolTip("显示/隐藏原文面板")
        self.source_toggle_btn.setCheckable(True)
        self.source_toggle_btn.setChecked(True)  # 默认选中，显示原文面板
        self.source_toggle_btn.setStyleSheet("""
            QPushButton { background: #3c3c3c; color: #888; border: none;
                          border-radius: 11px; font-size: 11px; }
            QPushButton:hover { background: #4a4a4a; color: #ddd; }
            QPushButton:checked { background: #007acc; color: #fff; }
        """)
        self.source_toggle_btn.toggled.connect(self._toggle_source_panel)
        h.addWidget(self.source_toggle_btn)

        # Separator
        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(16)
        sep2.setStyleSheet("background: #555; border: none;")
        h.addWidget(sep2)

        # Goal模式开关
        self.goal_mode_checkbox = QCheckBox("🎯 Goal模式")
        self.goal_mode_checkbox.setChecked(False)  # 默认关闭
        self.goal_mode_checkbox.setToolTip("开启后，AI会自动重试直到生成高质量产物（最多99次）")
        self.goal_mode_checkbox.setStyleSheet("""
            QCheckBox {
                color: #888;
                font-size: 11px;
                border: none;
                spacing: 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #555;
                background: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background: #007acc;
                border-color: #007acc;
            }
            QCheckBox::indicator:hover {
                border-color: #007acc;
            }
        """)
        self.goal_mode_checkbox.toggled.connect(self._on_goal_mode_toggled)
        h.addWidget(self.goal_mode_checkbox)

        # Goal模式状态指示器
        self.goal_status_label = QLabel("")
        self.goal_status_label.setStyleSheet("color: #888; font-size: 10px; border: none;")
        self.goal_status_label.setVisible(False)
        h.addWidget(self.goal_status_label)

        # Export button
        export_btn = QPushButton("💾 导出")
        export_btn.setStyleSheet("""
            QPushButton { background: #28a745; color: #fff; border: none;
                          border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: #218838; }
        """)
        export_btn.clicked.connect(self._on_export)
        h.addWidget(export_btn)

        return bar

    # ============================================================
    # Signal wiring
    # ============================================================
    def _connect_signals(self):
        self.slide_list.currentRowChanged.connect(self._on_slide_selected)
        self.slide_list.slide_moved.connect(self._on_slide_moved)
        self.renderer.title_double_clicked.connect(self._on_title_double_click)
        self.renderer.element_clicked.connect(self._on_element_clicked)
        self.inline_editor.editing_finished.connect(self._on_inline_edit_done)
        self.inline_editor.editing_cancelled.connect(self._on_inline_edit_cancel)
        self.diff_accept_btn.clicked.connect(self._accept_diff)
        self.diff_reject_btn.clicked.connect(self._reject_diff)

        # OutlinePanel signals → sync to CoCreationWidget master data
        self.outline_panel.slide_selected.connect(self._on_outline_slide_selected)
        self.outline_panel.slide_changed.connect(self._on_outline_slide_changed)
        self.outline_panel.slide_added.connect(self._on_outline_slide_added)
        self.outline_panel.slide_deleted.connect(self._on_outline_slide_deleted)
        self.outline_panel.slide_moved.connect(self._on_outline_slide_moved)

        # 原文面板信号 → 双向联动：点击原文时跳转到对应幻灯片
        self.source_panel.position_clicked.connect(self._on_source_position_clicked)
        
        # 原文面板信号 → 重新生成幻灯片
        self.source_panel.regenerate_slide_requested.connect(self._on_regenerate_slide)

    def _check_agent_health(self):
        """轻量级 Pipeline 探活"""
        try:
            import asu_custom_agent
            is_alive = hasattr(asu_custom_agent, 'pipeline') and asu_custom_agent.pipeline is not None
        except Exception:
            is_alive = False
        if is_alive:
            self.agent_status.setStyleSheet("color: #4caf50; font-size: 11px; border: none;")
            self.agent_status.setToolTip("🟢 Agent Pipeline 在线")
        else:
            self.agent_status.setStyleSheet("color: #f44336; font-size: 11px; border: none;")
            self.agent_status.setToolTip("🔴 Agent Pipeline 未就绪")

    def _on_goal_mode_toggled(self, checked: bool):
        """Goal模式开关切换"""
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        
        if checked:
            self.goal_status_label.setText("🎯 已开启")
            self.goal_status_label.setStyleSheet("color: #4caf50; font-size: 10px; border: none;")
            self.goal_status_label.setVisible(True)
            obs.gui_log("Goal模式已开启", session_id=self._session_id, event="GOAL_MODE_ON")
        else:
            self.goal_status_label.setText("")
            self.goal_status_label.setVisible(False)
            obs.gui_log("Goal模式已关闭", session_id=self._session_id, event="GOAL_MODE_OFF")

    def is_goal_mode_enabled(self) -> bool:
        """检查Goal模式是否开启"""
        return self.goal_mode_checkbox.isChecked()

    def _toggle_source_panel(self, checked: bool):
        """Toggle source panel visibility"""
        self.source_panel.setVisible(checked)

    # ============================================================
    # Public API
    # ============================================================
    def load_slides(self, text: str, json_data: list):
        """Load slides programmatically (from Tab 1/3)"""
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        slides_count = len(json_data) if isinstance(json_data, list) else len(json_data.get("slides", []))
        obs.gui_log(f"PPT Tab5 load_slides | slides={slides_count} | text_len={len(text)}",
                    session_id=self._session_id, event="PPT_TAB5_LOAD_SLIDES")
        self.original_text = text
        self.slides_data = json_data if isinstance(json_data, list) else json_data.get("slides", [])
        self.current_index = 0
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._refresh_all()

        # Sync to OutlinePanel (deep copy to prevent shared reference)
        self._syncing = True
        self.outline_panel.set_slides_data(copy.deepcopy(self.slides_data))
        self._syncing = False

        # Sync to SourcePanel (always visible, placeholder when empty)
        self.source_panel.set_original_text(text or "")

        # 构建原文与幻灯片的映射关系（双向联动核心）
        if text and self.slides_data:
            from .source_matcher import SourceMatcher
            self.source_matcher = SourceMatcher()
            self.source_matcher.build_mappings(text, self.slides_data)
            self.source_panel.set_source_matcher(self.source_matcher)
            print(f"[CoCreation] SourceMatcher 初始化完成，映射数: {len(self.source_matcher.mappings)}")
        else:
            self.source_matcher = None

    def get_slides_data(self) -> list:
        return self.slides_data

    # ============================================================
    # Refresh helpers
    # ============================================================
    def _refresh_all(self):
        """Refresh slide list, preview, stats, actions, quality badges"""
        # Clamp current_index after data mutation (e.g. remove_slide)
        if self.slides_data:
            self.current_index = max(0, min(self.current_index, len(self.slides_data) - 1))
        else:
            self.current_index = 0
        self._refresh_slide_list()
        self._refresh_preview()
        self._refresh_stats()
        self._refresh_actions()
        self._refresh_quality()
        self._update_undo_redo_buttons()
        self._update_empty_state()

        # Sync OutlinePanel data (guarded to prevent signal loops, deep copy to prevent shared reference)
        self._syncing = True
        self.outline_panel.set_slides_data(copy.deepcopy(self.slides_data))
        if self.slides_data:
            self.outline_panel.slide_list.setCurrentRow(self.current_index)
        self._syncing = False

    def _update_empty_state(self, is_waiting: bool = False):
        """Update empty state panel based on current state.
        
        Args:
            is_waiting: True when AI is generating outline (from Tab 3 trigger)
        """
        has_data = bool(self.slides_data)
        self._is_waiting = is_waiting
        
        # Update empty panel content based on state
        if not has_data:
            if is_waiting:
                # Waiting for AI generation
                self.empty_icon.setText("⏳")
                self.empty_title.setText("AI 正在生成 PPT 大纲")
                self.empty_desc.setText("请稍候，AI 正在分析内容并生成大纲...")
                self.paste_btn.hide()
                self.empty_hint.hide()
            else:
                # No data, need user input
                self.empty_icon.setText("📄")
                self.empty_title.setText("尚未加载 PPT 内容")
                self.empty_desc.setText("请粘贴或输入文本内容，AI 将自动生成 PPT 大纲")
                self.paste_btn.show()
                self.empty_hint.show()
        
        # Visibility
        self.empty_panel.setVisible(not has_data)
        self.splitter.setVisible(has_data)
        self.ai_input.setEnabled(has_data)
        self.send_btn.setEnabled(has_data)
        # Source panel: always visible (show placeholder when no text)
        self.source_panel.show()
        # Outline panel: always show when data exists
        self.outline_panel.setVisible(has_data)

    def _paste_and_generate(self):
        """Handle paste button click: show text input dialog and generate outline"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📝 输入 PPT 内容")
        dialog.setMinimumSize(520, 420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Prompt
        label = QLabel("请输入或粘贴内容，AI 将自动生成 PPT 大纲：")
        label.setStyleSheet("color: #aaa; font-size: 13px; border: none;")
        layout.addWidget(label)
        
        # Text edit area
        text_edit = QTextEdit()
        text_edit.setPlaceholderText(
            "例如：\n\n"
            "一、项目背景\n"
            "- 市场需求分析\n"
            "- 竞争格局\n\n"
            "二、技术方案\n"
            "- 架构设计\n"
            "- 核心技术\n\n"
            "三、实施计划\n"
            "- 时间节点\n"
            "- 里程碑"
        )
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        layout.addWidget(text_edit)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #555; color: #fff; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #666; }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(cancel_btn)
        
        generate_btn = QPushButton("🚀 生成 PPT")
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #007bff; color: #fff; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #0056b3; }
        """)
        generate_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(generate_btn)
        
        layout.addLayout(btn_row)
        
        # Execute dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = text_edit.toPlainText().strip()
            if text:
                if self._is_generating:
                    QMessageBox.information(self, "生成中", "当前有正在进行的 AI 生成任务，请稍后再试。")
                    return
                # Update source panel
                self.source_panel.set_original_text(text)
                self.original_text = text
                
                # Show waiting state
                self._update_empty_state(is_waiting=True)
                
                # Trigger AI generation in background
                QTimer.singleShot(100, lambda: self._generate_outline_from_text(text))

    def _generate_outline_from_text(self, text: str):
        """Generate outline from text using AI (background task)"""
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        
        sid = f"ppt_paste_{uuid.uuid4().hex[:8]}"
        obs.gui_log(f"PPT Tab5 PASTE GENERATE | text_len={len(text)}",
                    session_id=sid, event="PPT_TAB5_PASTE_GENERATE")
        
        try:
            # Use main window's generation methods
            main_window = self.window()
            if hasattr(main_window, '_generate_ppt_outline_with_ai'):
                # Generate in background thread
                self._generate_outline_sync(text)
            else:
                # Fallback: use simple generation
                self._generate_outline_simple(text)
        except Exception as e:
            obs.gui_log(f"PPT Tab5 PASTE GENERATE FAIL | err={e}",
                        session_id=sid, event="PPT_TAB5_PASTE_FAIL", level="ERROR")
            print(f"[PPT Tab5] 粘贴生成失败: {e}")
            import traceback
            traceback.print_exc()
            # Show error state
            self._update_empty_state(is_waiting=False)

    def _generate_outline_sync(self, text: str):
        """Generate outline in background thread"""
        import threading
        
        # 设置生成状态
        self._is_generating = True
        
        def _worker():
            try:
                main_window = self.window()
                if hasattr(main_window, '_generate_ppt_outline_with_ai'):
                    json_data = main_window._generate_ppt_outline_with_ai(text)
                    if json_data:
                        slides = json_data.get("slides", []) if isinstance(json_data, dict) else json_data
                        # Update UI in main thread
                        QTimer.singleShot(0, lambda: self._on_outline_generated(slides))
                    else:
                        # Try fallback
                        if hasattr(main_window, '_generate_fallback_outline'):
                            fallback = main_window._generate_fallback_outline(text)
                            if fallback:
                                slides = fallback.get("slides", []) if isinstance(fallback, dict) else fallback
                                QTimer.singleShot(0, lambda: self._on_outline_generated(slides))
                            else:
                                QTimer.singleShot(0, lambda: self._update_empty_state(is_waiting=False))
                        else:
                            QTimer.singleShot(0, lambda: self._update_empty_state(is_waiting=False))
                else:
                    QTimer.singleShot(0, lambda: self._update_empty_state(is_waiting=False))
            except Exception as e:
                print(f"[PPT Tab5] 生成失败: {e}")
                QTimer.singleShot(0, lambda: self._update_empty_state(is_waiting=False))
            finally:
                # 重置生成状态
                QTimer.singleShot(0, lambda: self._reset_generating_state())
        
        threading.Thread(target=_worker, daemon=True).start()
    
    def _reset_generating_state(self):
        """重置生成状态"""
        self._is_generating = False

    def _generate_outline_simple(self, text: str):
        """Simple fallback generation without AI"""
        import re
        
        # Extract sections from text
        lines = text.split('\n')
        sections = []
        current_title = ""
        current_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect headers
            is_header = False
            title_text = ""
            
            # Check for markdown headers
            if line.startswith('#'):
                is_header = True
                title_text = re.sub(r'^#+\s*', '', line)
            # Check for numbered sections
            elif re.match(r'^[一二三四五六七八九十]+[、.]', line):
                is_header = True
                title_text = line
            elif re.match(r'^\d+[、.]', line):
                is_header = True
                title_text = line
            
            if is_header:
                if current_title:
                    sections.append((current_title, current_items[:]))
                current_title = title_text
                current_items = []
            elif line.startswith('-') or line.startswith('*'):
                current_items.append(line[1:].strip())
            elif current_title:
                current_items.append(line)
        
        if current_title:
            sections.append((current_title, current_items))
        
        # Generate slides
        slides = []
        for title, items in sections[:10]:  # Limit to 10 slides
            slide = {
                "title": title,
                "items": [{"text": item} for item in items[:6]]  # Limit items per slide
            }
            slides.append(slide)
        
        # If no sections found, create a single slide
        if not slides:
            slides = [{
                "title": "演示文稿",
                "items": [{"text": text[:200]}]
            }]
        
        self._on_outline_generated(slides)

    def _on_outline_generated(self, slides: list):
        """Callback when outline generation completes"""
        # 重置生成状态
        self._is_generating = False
        
        if slides:
            self.load_slides(self.original_text, slides)
        else:
            self._update_empty_state(is_waiting=False)

    def _refresh_slide_list(self):
        """Rebuild slide list with thumbnail widgets"""
        self.slide_list.blockSignals(True)
        self.slide_list.clear()
        for i, slide in enumerate(self.slides_data):
            badge = self._quality_badge(slide)
            item = QListWidgetItem()
            item.setSizeHint(QSize(90, 62))
            self.slide_list.addItem(item)
            thumb = _ThumbnailWidget(slide, i, badge)
            self.slide_list.setItemWidget(item, thumb)
        if self.slides_data and 0 <= self.current_index < len(self.slides_data):
            self.slide_list.setCurrentRow(self.current_index)
        self.slide_list.blockSignals(False)

    def _quality_badge(self, slide: dict) -> str:
        """Return badge character if quality issues detected, else ''"""
        items = slide.get("items", [])
        title = slide.get("title", "")
        total_text = len(title) + sum(len(it.get("text", "")) for it in items)
        if len(items) > 8:
            return "!"
        if total_text > 200:
            return "!"
        if len(title) > 25:
            return "~"
        return ""

    def _refresh_preview(self):
        """Update SlideRenderer with current slide"""
        if not self.slides_data:
            self.renderer.set_slide(None)
            self.page_label.setText("0 / 0")
            return
        idx = max(0, min(self.current_index, len(self.slides_data) - 1))
        self.renderer.set_slide(self.slides_data[idx])
        self.page_label.setText(f"{idx + 1} / {len(self.slides_data)}")

    def _refresh_stats(self):
        total = len(self.slides_data)
        items = sum(len(s.get("items", [])) for s in self.slides_data)
        self.stats_label.setText(f"幻灯片: {total} | 要点: {items}")

    def _refresh_actions(self):
        """Rebuild contextual quick action buttons"""
        # Clear all items including spacers
        while self.actions_row.count():
            item = self.actions_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._action_buttons.clear()

        if not self.slides_data:
            return

        slide = self.slides_data[self.current_index]
        items = slide.get("items", [])
        # Detect dominant content type
        content_type = "text"
        if items:
            ct = items[0].get("content_type", "text")
            if ct in self._ACTIONS_BY_TYPE:
                content_type = ct

        labels = self._ACTIONS_BY_TYPE.get(content_type, self._ACTIONS_BY_TYPE["text"])
        for label in labels:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: #2d2d2d; color: #aaa;
                    border: 1px solid #3c3c3c; border-radius: 10px;
                    padding: 3px 10px; font-size: 10px;
                }
                QPushButton:hover { background: #3c3c3c; color: #ddd; border-color: #555; }
            """)
            prompt = self._ACTION_PROMPTS.get(label, label)
            btn.clicked.connect(lambda checked, p=prompt: self._send_quick_action(p))
            self.actions_row.addWidget(btn)
            self._action_buttons.append(btn)
        self.actions_row.addStretch()

    def _refresh_quality(self):
        """Show quality warning if current slide has issues"""
        if not self.slides_data:
            self.quality_bar.hide()
            return
        slide = self.slides_data[self.current_index]
        badge = self._quality_badge(slide)
        if badge:
            items = slide.get("items", [])
            title = slide.get("title", "")
            total_text = len(title) + sum(len(it.get("text", "")) for it in items)
            msgs = []
            if len(items) > 8:
                msgs.append("⚠️ 要点过多 (>8)，建议拆分")
            if total_text > 200:
                msgs.append("⚠️ 内容过密 (>200字)，建议精简")
            if len(title) > 25:
                msgs.append("⚠️ 标题过长，建议精简到25字以内")
            self.quality_bar.setText("  ".join(msgs))
            self.quality_bar.show()
        else:
            self.quality_bar.hide()

    # ============================================================
    # Theme
    # ============================================================
    def _set_theme(self, key: str):
        self._theme = key
        self._apply_theme()
        self._refresh_slide_list()

    def _apply_theme(self):
        t = THEMES[self._theme]
        self.setStyleSheet(f"""
            QWidget {{ background-color: {t['bg']}; color: {t['fg']}; }}
            QSplitter::handle {{ background-color: {t['border']}; }}
        """)

    # ============================================================
    # Slide navigation
    # ============================================================
    def _on_slide_selected(self, row: int):
        if 0 <= row < len(self.slides_data):
            self.current_index = row
            self._refresh_preview()
            self._refresh_actions()
            self._refresh_quality()
            # Sync OutlinePanel selection (guarded)
            self._syncing = True
            self.outline_panel.slide_list.setCurrentRow(row)
            self._syncing = False
            self.slide_selected.emit(row)

    def _on_slide_moved(self, from_idx: int, to_idx: int):
        """Handle drag reorder in slide list"""
        if 0 <= from_idx < len(self.slides_data) and 0 <= to_idx < len(self.slides_data):
            self._push_undo("拖拽排序", "manual")
            slide = self.slides_data.pop(from_idx)
            self.slides_data.insert(to_idx, slide)
            self.current_index = to_idx
            self._refresh_all()  # Syncs OutlineList + OutlinePanel + Preview
            self.slides_updated.emit(self.slides_data)

    # ============================================================
    # OutlinePanel signal handlers (bidirectional sync)
    # ============================================================
    def _on_outline_slide_selected(self, row: int):
        """OutlinePanel navigation → sync thumbnail + preview"""
        if self._syncing:
            return
        if 0 <= row < len(self.slides_data):
            self.current_index = row
            self._syncing = True
            self.slide_list.setCurrentRow(row)
            self._syncing = False
            self._refresh_preview()
            self._refresh_actions()
            self._refresh_quality()
            self.slide_selected.emit(row)

    def _on_outline_slide_changed(self, idx: int, slide: dict):
        """OutlinePanel form edit → sync master data + preview"""
        if self._syncing:
            return
        if 0 <= idx < len(self.slides_data):
            self._push_undo(f"编辑第{idx+1}页: {slide.get('title', '')[:15]}", "manual")
            self.slides_data[idx] = copy.deepcopy(slide)  # Deep copy from OutlinePanel's copy
            self._refresh_slide_list()
            self._refresh_preview()
            self._refresh_stats()
            self._refresh_actions()
            self.slides_updated.emit(self.slides_data)

    def _on_outline_slide_added(self, idx: int, slide: dict):
        """OutlinePanel add slide → sync master data"""
        if self._syncing:
            return
        self._push_undo(f"新增第{idx+1}页: {slide.get('title', '')[:15]}", "manual")
        # OutlinePanel already inserted into its own copy — apply same to master
        if 0 <= idx <= len(self.slides_data):
            self.slides_data.insert(idx, copy.deepcopy(slide))
        else:
            self.slides_data.append(copy.deepcopy(slide))
        self.current_index = idx
        self._refresh_all()
        self.slides_updated.emit(self.slides_data)

    def _on_outline_slide_deleted(self, idx: int):
        """OutlinePanel delete slide → sync master data"""
        if self._syncing:
            return
        if 0 <= idx < len(self.slides_data):
            self._push_undo(f"删除第{idx+1}页", "manual")
            self.slides_data.pop(idx)
            self._refresh_all()
            self.slides_updated.emit(self.slides_data)

    def _on_outline_slide_moved(self, from_idx: int, to_idx: int):
        """OutlinePanel drag reorder → sync master data"""
        if self._syncing:
            return
        if 0 <= from_idx < len(self.slides_data) and 0 <= to_idx < len(self.slides_data):
            self._push_undo("拖拽排序", "manual")
            # OutlinePanel already moved in its own copy — apply same to master
            slide = self.slides_data.pop(from_idx)
            self.slides_data.insert(to_idx, slide)
            self.current_index = to_idx
            self._refresh_all()
            self.slides_updated.emit(self.slides_data)

    # ============================================================
    # Click-to-edit on preview
    # ============================================================
    def _on_title_double_click(self):
        """Title double-clicked on preview -> show inline editor"""
        if not self.slides_data:
            return
        slide = self.slides_data[self.current_index]
        title = slide.get("title", "")
        self.inline_editor.element_type = "title"
        self.inline_editor.element_index = -1
        self.inline_editor.setText(title)
        self.inline_editor.show()
        self.inline_editor.setFocus()
        self.inline_editor.selectAll()

    def _on_element_clicked(self, elem_type: str, elem_index: int):
        """Element clicked on preview"""
        pass  # Future: right-click context menu

    def _on_inline_edit_done(self, elem_type: str, new_text: str, elem_index: int):
        """Inline editor confirmed"""
        self.inline_editor.hide()
        if not self.slides_data:
            return
        slide = self.slides_data[self.current_index]
        if elem_type == "title":
            old = slide.get("title", "")
            if old != new_text:
                self._push_undo(f"编辑标题: {old[:15]}→{new_text[:15]}", "manual")
                slide["title"] = new_text
                self._refresh_all()
                self.slides_updated.emit(self.slides_data)

    def _on_inline_edit_cancel(self):
        self.inline_editor.hide()

    def _on_source_position_clicked(self, pos: int):
        """原文面板中点击某个位置 → 跳转到对应的幻灯片"""
        if not self.slides_data or not self.source_matcher:
            return
        
        try:
            # find_slide_for_position 返回 Optional[Tuple[int, Optional[int]]]
            result = self.source_matcher.find_slide_for_position(pos)
            if result is None:
                return

            slide_index, item_index = result
            if slide_index < 0 or slide_index >= len(self.slides_data):
                return
            
            # 更新当前幻灯片索引
            self.current_index = slide_index
            
            # 更新大纲列表选中状态（blockSignals 防止循环触发）
            self.slide_list.blockSignals(True)
            self.slide_list.setCurrentRow(slide_index)
            self.slide_list.blockSignals(False)
            
            # 刷新预览面板
            self._refresh_all()
            
            # 高亮原文对应内容（双向联动）
            self.source_panel.highlight_slide_content(slide_index, item_index)
            
            # 显示提示
            self.stats_label.setText(f"📍 已跳转到幻灯片 {slide_index + 1}")
            print(f"[CoCreation] 原文点击 → 幻灯片 {slide_index+1} (pos={pos})")
        except Exception as e:
            print(f"[ERROR] CoCreation._on_source_position_clicked: {e}")

    def _on_regenerate_slide(self, selected_text: str, expression_type: str):
        """原文面板请求重新生成当前幻灯片"""
        if not self.slides_data or not selected_text:
            return
        
        # 获取当前幻灯片索引
        slide_index = self.current_index
        if slide_index < 0 or slide_index >= len(self.slides_data):
            return
        
        # 构建AI指令，要求根据选中文本和指定表达方式重新生成当前幻灯片
        instruction = f"""请根据以下选中的原文内容，重新生成第 {slide_index + 1} 页幻灯片。

要求：
1. 使用选中的原文内容作为核心素材
2. 采用"{expression_type}"的表达方式
3. 保持与原有大纲的逻辑一致性
4. 生成适合当前表达方式的结构化内容

选中的原文内容：
{selected_text}

当前幻灯片索引：{slide_index}
请返回修改该幻灯片的JSON指令。"""
        
        # 调用AI进行重新生成
        self._do_ai_request(instruction)
        
        # 显示提示
        self.stats_label.setText(f"🔄 正在根据选中文本重新生成幻灯片 {slide_index + 1}...")

    # ============================================================
    # AI interaction
    # ============================================================
    def _send_ai(self):
        instruction = self.ai_input.text().strip()
        if not instruction or not self.slides_data:
            return
        if self._is_generating:
            self.typing_label.setText("⏳ 大纲生成中，请稍后再输入 AI 指令")
            self.typing_label.show()
            QTimer.singleShot(3000, self.typing_label.hide)
            return
        self.ai_input.clear()
        self._do_ai_request(instruction)

    def _send_quick_action(self, prompt: str):
        if not self.slides_data:
            return
        self._do_ai_request(prompt)

    def _do_ai_request(self, instruction: str):
        """Start AI worker"""
        self._last_instruction = instruction

        # Show typing indicator
        self.typing_label.setText("● AI 正在思考...")
        self.typing_label.show()
        self.ai_input.setEnabled(False)
        self.send_btn.setEnabled(False)

        # Kill old worker via cooperative cancellation
        if self._worker and self._worker.isRunning():
            self._worker.cancel_event.set()
            try:
                self._worker.response_ready.disconnect(self._on_ai_response)
            except TypeError:
                pass
            try:
                self._worker.error_occurred.disconnect(self._on_ai_error)
            except TypeError:
                pass

        self._worker = _AIWorker()
        self._worker.response_ready.connect(self._on_ai_response)
        self._worker.error_occurred.connect(self._on_ai_error)
        self._worker.set_task(instruction, self.slides_data, self.current_index, self._session_id)
        self._worker.start()

    def _on_ai_response(self, response: str):
        """AI returned — parse ALL JSON objects and apply/preview"""
        self.typing_label.hide()
        self.ai_input.setEnabled(True)
        self.send_btn.setEnabled(True)

        try:
            json_objects = self._extract_all_json(response)
            if not json_objects:
                raise ValueError("无法找到 JSON 数据，AI 可能返回了非预期格式")

            # Parse all actions
            actions = []
            first_error = None
            for json_str in json_objects:
                try:
                    data = json.loads(json_str)
                    actions.append(data)
                except json.JSONDecodeError as e:
                    if first_error is None:
                        first_error = str(e)
                    continue

            if not actions:
                raise ValueError(f"无法解析任何 JSON 动作: {first_error}")

            # Compute diffs for preview
            diffs = []
            for data in actions:
                diff_info = self._compute_diff(data)
                if diff_info:
                    diffs.append(diff_info)

            if diffs:
                # Show diff preview with summary of all changes
                summary_parts = [d["summary"] for d in diffs]
                combined_summary = "\n".join(f"• {s}" for s in summary_parts[:5])
                if len(diffs) > 5:
                    combined_summary += f"\n... 还有 {len(diffs) - 5} 项修改"

                self._pending_diff = {"actions": actions, "diffs": diffs}
                self.diff_label.setText(combined_summary)
                self.diff_frame.show()
            else:
                # Apply directly if no meaningful diff
                self._apply_ai_actions(actions)

        except Exception as e:
            self.typing_label.setText(f"⚠️ {e}")
            self.typing_label.show()
            QTimer.singleShot(4000, self.typing_label.hide)

    def _on_ai_error(self, error: str):
        self.typing_label.setText(f"❌ {error}")
        self.typing_label.show()
        self.ai_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        QTimer.singleShot(4000, self.typing_label.hide)

    def _extract_all_json(self, text: str) -> List[str]:
        """Extract ALL JSON objects from AI response (may contain multiple actions)"""
        results = []

        # Try code blocks first
        blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        for block in blocks:
            block = block.strip()
            if block.startswith("{") or block.startswith("["):
                results.append(block)

        if results:
            return results

        # Fallback: find all top-level JSON objects by brace matching
        i = 0
        while i < len(text):
            start = text.find("{", i)
            if start < 0:
                break
            depth = 0
            in_string = False
            escape = False
            for j in range(start, len(text)):
                c = text[j]
                if escape:
                    escape = False
                    continue
                if c == '\\':
                    escape = True
                    continue
                if c == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        results.append(text[start:j + 1])
                        i = j + 1
                        break
            else:
                break

        return results

    def _compute_diff(self, data: dict) -> Optional[Dict]:
        """Compute human-readable diff summary"""
        action = data.get("action")
        if action == "update":
            idx = data.get("slide_index", 0)
            field = data.get("field", "")
            new_val = data.get("value", "")
            if 0 <= idx < len(self.slides_data):
                old_val = self.slides_data[idx].get(field, "")
                return {
                    "summary": f"第{idx+1}页 {field}: 「{str(old_val)[:20]}」→「{str(new_val)[:20]}」",
                    "old": old_val, "new": new_val,
                }
        elif action == "update_item":
            idx = data.get("slide_index", 0)
            iidx = data.get("item_index", 0)
            field = data.get("field", "")
            new_val = data.get("value", "")
            if 0 <= idx < len(self.slides_data):
                items = self.slides_data[idx].get("items", [])
                if 0 <= iidx < len(items):
                    old_val = items[iidx].get(field, "")
                    return {
                        "summary": f"第{idx+1}页 要点{iidx+1} {field}: 「{str(old_val)[:15]}」→「{str(new_val)[:15]}」",
                        "old": old_val, "new": new_val,
                    }
        elif action == "add_item":
            idx = data.get("slide_index", 0)
            item = data.get("item", {})
            return {"summary": f"第{idx+1}页 +要点: 「{item.get('text', '')[:25]}」"}
        elif action == "add_slide":
            slide = data.get("slide", {})
            return {"summary": f"+新页: 「{slide.get('title', '')[:20]}」"}
        elif action == "remove_item":
            idx = data.get("slide_index", 0)
            iidx = data.get("item_index", 0)
            return {"summary": f"第{idx+1}页 -要点{iidx+1}"}
        elif action == "remove_slide":
            idx = data.get("index", 0)
            if 0 <= idx < len(self.slides_data):
                title = self.slides_data[idx].get("title", "")[:15]
                return {"summary": f"-删除第{idx+1}页: 「{title}」"}
        elif "slides" in data:
            return {"summary": f"全量更新: {len(self.slides_data)}页 → {len(data['slides'])}页"}
        return None

    def _accept_diff(self):
        """User accepted the diff — apply pending actions"""
        self.diff_frame.hide()
        if self._pending_diff:
            actions = self._pending_diff.get("actions", [])
            if actions:
                from opencopilot.agent.observability import PipelineObservability
                obs = PipelineObservability.get_instance()
                obs.gui_log(f"PPT Tab5 DIFF ACCEPT | actions={len(actions)}",
                            session_id=self._session_id, event="PPT_TAB5_DIFF_ACCEPT")
                self._apply_ai_actions(actions)
            self._pending_diff = None

    def _reject_diff(self):
        """User rejected the diff"""
        self.diff_frame.hide()
        if self._pending_diff:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log("PPT Tab5 DIFF REJECT",
                        session_id=self._session_id, event="PPT_TAB5_DIFF_REJECT")
        self._pending_diff = None

    def _apply_ai_actions(self, actions: list):
        """Apply a list of AI JSON update actions"""
        if not actions:
            return

        # Push undo once for the whole batch
        desc = self._last_instruction[:40] if hasattr(self, '_last_instruction') else "AI 修改"
        self._push_undo(desc, "ai")

        applied = 0
        errors = []
        for data in actions:
            try:
                self._apply_single_action(data)
                applied += 1
            except ValueError as e:
                errors.append(str(e))

        self._refresh_all()
        self.slides_updated.emit(self.slides_data)

        # Feedback
        if errors and not applied:
            self.typing_label.setText(f"⚠️ {'; '.join(errors)}")
            self.typing_label.show()
            QTimer.singleShot(4000, self.typing_label.hide)
        elif errors:
            self.typing_label.setText(f"✅ {applied}项成功, ⚠️ {len(errors)}项失败")
            self.typing_label.show()
            QTimer.singleShot(3000, self.typing_label.hide)

    def _apply_single_action(self, data: dict):
        """Apply a single AI update action with validation. Raises ValueError on bad input."""
        action = data.get("action")

        if action == "update":
            idx = data.get("slide_index")
            field = data.get("field")
            value = data.get("value")
            if idx is None or field is None:
                raise ValueError("update 缺少 slide_index 或 field")
            if not (0 <= idx < len(self.slides_data)):
                raise ValueError(f"幻灯片索引 {idx} 超出范围")
            self.slides_data[idx][field] = value

        elif action == "update_item":
            idx = data.get("slide_index")
            iidx = data.get("item_index")
            field = data.get("field")
            value = data.get("value")
            if idx is None or iidx is None or field is None:
                raise ValueError("update_item 缺少必要参数")
            if not (0 <= idx < len(self.slides_data)):
                raise ValueError(f"幻灯片索引 {idx} 超出范围")
            items = self.slides_data[idx].get("items", [])
            if not (0 <= iidx < len(items)):
                raise ValueError(f"要点索引 {iidx} 超出范围")
            items[iidx][field] = value

        elif action == "add_item":
            idx = data.get("slide_index")
            item = data.get("item", {})
            if idx is None:
                raise ValueError("add_item 缺少 slide_index")
            if not (0 <= idx < len(self.slides_data)):
                raise ValueError(f"幻灯片索引 {idx} 超出范围")
            item = self._normalize_content_item(item)
            self.slides_data[idx].setdefault("items", []).append(item)

        elif action == "remove_item":
            idx = data.get("slide_index")
            iidx = data.get("item_index")
            if idx is None or iidx is None:
                raise ValueError("remove_item 缺少必要参数")
            if not (0 <= idx < len(self.slides_data)):
                raise ValueError(f"幻灯片索引 {idx} 超出范围")
            items = self.slides_data[idx].get("items", [])
            if not (0 <= iidx < len(items)):
                raise ValueError(f"要点索引 {iidx} 超出范围")
            items.pop(iidx)

        elif action == "add_slide":
            pos = data.get("index", len(self.slides_data))
            slide = data.get("slide", {})
            if not (0 <= pos <= len(self.slides_data)):
                raise ValueError(f"插入位置 {pos} 超出范围")
            self.slides_data.insert(pos, slide)

        elif action == "remove_slide":
            idx = data.get("index")
            if idx is None:
                raise ValueError("remove_slide 缺少 index")
            if not (0 <= idx < len(self.slides_data)):
                raise ValueError(f"幻灯片索引 {idx} 超出范围")
            self.slides_data.pop(idx)

        elif "slides" in data:
            self.slides_data = data["slides"]

        else:
            raise ValueError(f"无法识别的动作: {action or '(无 action)'}")

    def _normalize_content_item(self, item: dict) -> dict:
        """本地校验并补全内容转换数据（chart/table/flowchart）"""
        ct = item.get("content_type", "")

        if ct == "table":
            td = item.get("table_data", {})
            if not isinstance(td, dict):
                td = {}
            td.setdefault("title", "数据表")
            td.setdefault("columns", ["项目", "内容"])
            td.setdefault("rows", [])
            col_count = len(td["columns"])
            td["rows"] = [r[:col_count] if len(r) > col_count else r + [""] * (col_count - len(r)) for r in td["rows"]]
            item["table_data"] = td

        elif ct == "chart":
            cd = item.get("chart_data", {})
            if not isinstance(cd, dict):
                cd = {}
            cd.setdefault("title", "图表")
            cd.setdefault("labels", [])
            cd.setdefault("datasets", [])
            if cd["datasets"] and isinstance(cd["datasets"][0], dict):
                cd["datasets"][0].setdefault("label", "数据")
                cd["datasets"][0].setdefault("data", [])
                cd["datasets"][0].setdefault("color", "#007bff")
            item["chart_data"] = cd

        elif ct == "flowchart":
            fd = item.get("flowchart_data", {})
            if not isinstance(fd, dict):
                fd = {}
            fd.setdefault("title", "流程图")
            fd.setdefault("steps", [])
            item["flowchart_data"] = fd

        return item

    # ============================================================
    # Unified Undo / Redo
    # ============================================================
    def _push_undo(self, description: str, edit_type: str = "manual"):
        """Save current state to undo stack"""
        self._undo_stack.append((copy.deepcopy(self.slides_data), description, edit_type))
        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _undo(self):
        if not self._undo_stack:
            return
        snap, desc, etype = self._undo_stack.pop()
        self._redo_stack.append((copy.deepcopy(self.slides_data), desc, etype))
        self.slides_data = snap
        self._refresh_all()
        self.slides_updated.emit(self.slides_data)
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT Tab5 UNDO | desc={desc} | type={etype}",
                    session_id=self._session_id, event="PPT_TAB5_UNDO")

    def _redo(self):
        if not self._redo_stack:
            return
        snap, desc, etype = self._redo_stack.pop()
        self._undo_stack.append((copy.deepcopy(self.slides_data), desc, etype))
        self.slides_data = snap
        self._refresh_all()
        self.slides_updated.emit(self.slides_data)
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.gui_log(f"PPT Tab5 REDO | desc={desc} | type={etype}",
                    session_id=self._session_id, event="PPT_TAB5_REDO")

    def _update_undo_redo_buttons(self):
        self.undo_btn.setEnabled(len(self._undo_stack) > 0)
        n_undo = len(self._undo_stack)
        self.undo_btn.setToolTip(f"撤销 ({n_undo})" if n_undo else "无可撤销")
        self.redo_btn.setEnabled(len(self._redo_stack) > 0)
        n_redo = len(self._redo_stack)
        self.redo_btn.setToolTip(f"重做 ({n_redo})" if n_redo else "无可重做")

    # ============================================================
    # Export
    # ============================================================
    def _on_export(self):
        if not self.slides_data:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出 PPT",
            os.path.expanduser("~/Desktop/generated_presentation.pptx"),
            "PowerPoint Files (*.pptx)",
        )
        if not save_path:
            return
        try:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Tab5 EXPORT START | slides={len(self.slides_data)} | path={save_path}",
                        session_id=self._session_id, event="PPT_TAB5_EXPORT_START")
            generate_ppt_via_html(self.slides_data, save_path)
            obs.gui_log(f"PPT Tab5 EXPORT DONE | path={save_path}",
                        session_id=self._session_id, event="PPT_TAB5_EXPORT_DONE")
            self.export_requested.emit(self.slides_data)
            QMessageBox.information(self, "导出成功", f"PPT 已导出至:\n{save_path}")
        except Exception as e:
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            obs.gui_log(f"PPT Tab5 EXPORT FAIL | err={e}",
                        session_id=self._session_id, event="PPT_TAB5_EXPORT_FAIL", level="ERROR")
            QMessageBox.critical(self, "导出失败", str(e))


# ============================================================
# CoCreationWindow — 全屏共创工作台窗口
# ============================================================
class CoCreationWindow(QDialog):
    """
    PPT 共创工作台 — 独立大窗口版本。

    从 Tab 5 启动器按钮打开，窗口自适应屏幕大小（~1200x800）。
    内部包裹 CoCreationWidget，提供与交互迭代方案一致的大屏编辑体验。
    """

    export_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎨 PPT 共创工作台")

        # 自适应窗口大小（参考 CoCreationDialog）
        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            width = min(int(available.width() * 0.85), 1600)
            height = min(int(available.height() * 0.85), 1000)
            width = max(width, 1100)
            height = max(height, 700)
            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            self.setGeometry(x, y, width, height)
        else:
            self.setMinimumSize(1100, 700)
            self.resize(1200, 800)

        # 样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        # 头部标题栏
        header = QWidget()
        header.setFixedHeight(42)
        header.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 6px 6px 0 0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)

        title_label = QLabel("🎨 PPT 共创工作台")
        title_label.setStyleSheet("color: #4da6ff; font-size: 15px; font-weight: bold; border: none;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        status_label = QLabel("输入 AI 指令或直接编辑幻灯片")
        status_label.setStyleSheet("color: #888; font-size: 11px; border: none;")
        header_layout.addWidget(status_label)

        layout.addWidget(header)

        # 核心工作区 — CoCreationWidget
        self.cocreation_widget = CoCreationWidget(parent=self)
        layout.addWidget(self.cocreation_widget, 1)

        # 底部按钮栏
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(44)
        bottom_bar.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 0 0 6px 6px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 6, 16, 6)

        bottom_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #3c3c3c; color: #ccc; border: 1px solid #555;
                border-radius: 4px; padding: 5px 20px; font-size: 12px;
            }
            QPushButton:hover { background: #4c4c4c; }
        """)
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)

        export_btn = QPushButton("💾 导出 PPT")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #28a745; color: #fff; border: none;
                border-radius: 4px; padding: 5px 20px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
        """)
        export_btn.clicked.connect(self.cocreation_widget._on_export)
        bottom_layout.addWidget(export_btn)

        layout.addWidget(bottom_bar)

        # 转发信号
        self.cocreation_widget.export_requested.connect(self.export_requested)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.close)

    def load_slides(self, text: str, json_data: list):
        """加载幻灯片数据"""
        self.cocreation_widget.load_slides(text, json_data)

    def get_slides_data(self) -> list:
        return self.cocreation_widget.get_slides_data()

    @property
    def slides_data(self):
        return self.cocreation_widget.slides_data
