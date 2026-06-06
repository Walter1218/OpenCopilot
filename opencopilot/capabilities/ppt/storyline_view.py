"""
故事线视图 - 层级幻灯片导航

功能：
- 按章节（Topic）分组显示幻灯片
- 支持整章拖拽排序
- 章节级主题色自动分配
- 点击幻灯片/章节联动预览面板
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
    QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush

# 章节主题色轮
CHAPTER_COLORS = [
    QColor("#4da6ff"),  # 蓝
    QColor("#28a745"),  # 绿
    QColor("#ffc107"),  # 黄
    QColor("#dc3545"),  # 红
    QColor("#6f42c1"),  # 紫
    QColor("#17a2b8"),  # 青
    QColor("#fd7e14"),  # 橙
    QColor("#20c997"),  # 薄荷
]


class StorylineView(QWidget):
    """故事线层级视图"""

    slide_clicked = pyqtSignal(int)           # 点击幻灯片
    chapter_clicked = pyqtSignal(int, int)     # 点击章节 (chapter_index, first_slide_index)
    slide_moved = pyqtSignal(int, int)         # 幻灯片移动 (from, to)
    chapter_moved = pyqtSignal(int, int)       # 章节移动 (from, to)
    add_slide_requested = pyqtSignal(int)      # 在指定章节添加幻灯片

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapters = {}         # {chapter_index: QTreeWidgetItem}
        self._slide_items = {}      # {slide_index: QTreeWidgetItem}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题
        header = QHBoxLayout()
        title = QLabel("📖 故事线")
        title.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # 树形视图
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border-radius: 4px;
                margin: 1px 0;
            }
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            QTreeWidget::item:hover {
                background-color: #383838;
            }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree, 1)

    def set_chapters_and_slides(self, topics: list, slides: list, slide_to_chapter: dict = None):
        """设置章节和幻灯片数据

        Args:
            topics: Topic 列表 [{title, index}, ...]
            slides: slides JSON 数据列表
            slide_to_chapter: {slide_index: chapter_index} 映射
        """
        self.tree.clear()
        self._chapters.clear()
        self._slide_items.clear()

        if not slide_to_chapter:
            # 自动映射：按 slides 顺序分配到 topic
            slide_to_chapter = {}
            slides_per_topic = max(1, len(slides) // max(len(topics), 1))
            for i, _ in enumerate(slides):
                slide_to_chapter[i] = min(i // slides_per_topic, len(topics) - 1) if topics else 0

        for ch_idx, topic in enumerate(topics):
            color = CHAPTER_COLORS[ch_idx % len(CHAPTER_COLORS)]
            ch_item = QTreeWidgetItem()
            ch_title = topic.title if hasattr(topic, 'title') else (topic.get('title', f"章节 {ch_idx + 1}") if isinstance(topic, dict) else f"章节 {ch_idx + 1}")
            ch_item.setText(0, f"📘 {ch_title}")
            ch_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "chapter", "index": ch_idx})
            ch_item.setFlags(ch_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            ch_font = QFont("Helvetica Neue", 13)
            ch_font.setBold(True)
            ch_item.setFont(0, ch_font)
            ch_item.setForeground(0, QBrush(color))
            self.tree.addTopLevelItem(ch_item)
            self._chapters[ch_idx] = ch_item

        for s_idx, slide in enumerate(slides):
            ch_idx = slide_to_chapter.get(s_idx, 0)
            if ch_idx in self._chapters:
                parent = self._chapters[ch_idx]
            else:
                parent = self.tree

            s_item = QTreeWidgetItem()
            slide_type = slide.get("type", "content") if isinstance(slide, dict) else "content"
            slide_title = slide.get("title", f"幻灯片 {s_idx + 1}") if isinstance(slide, dict) else f"幻灯片 {s_idx + 1}"
            icon = "🎯" if slide_type == "title" else "📄"
            s_item.setText(0, f"{icon} {s_idx + 1}. {slide_title[:30]}")
            s_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "slide", "index": s_idx})
            s_item.setFlags(s_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            s_item.setFont(0, QFont("Helvetica Neue", 12))
            parent.addChild(s_item)
            self._slide_items[s_idx] = s_item

        self.tree.expandAll()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "slide":
            self.slide_clicked.emit(data["index"])
        elif data.get("type") == "chapter":
            ch_idx = data["index"]
            # 找到该章节第一张幻灯片
            for s_idx, s_item in self._slide_items.items():
                if s_item.parent() == item:
                    self.chapter_clicked.emit(ch_idx, s_idx)
                    return

    def set_selected_slide(self, index: int):
        for s_idx, item in self._slide_items.items():
            if s_idx == index:
                self.tree.setCurrentItem(item)
                break

    def highlight_slide(self, index: int, color: QColor = None):
        """临时高亮某张幻灯片"""
        if index in self._slide_items:
            item = self._slide_items[index]
            item.setBackground(0, QBrush(color or QColor(0, 123, 255, 80)))
