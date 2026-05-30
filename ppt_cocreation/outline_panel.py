"""
编辑大纲面板

功能：
- 幻灯片导航列表（支持拖拽排序）
- 编辑表单（标题、副标题、版式、内容类型）
- 要点编辑区（支持多行、层级缩进）
- 多媒体内容支持
"""

import json
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QComboBox, QLabel, QPushButton, QFormLayout,
    QSplitter, QMenu, QInputDialog, QMessageBox, QFrame, QScrollArea,
    QSizePolicy, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QColor, QFont, QIcon, QDrag, QAction


class SlideListWidget(QListWidget):
    """支持拖拽排序的幻灯片列表"""
    
    slide_moved = pyqtSignal(int, int)  # 从 from_index 移动到 to_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSpacing(4)
        self.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                margin: 2px 0;
                color: #d4d4d4;
            }
            QListWidget::item:selected {
                background-color: #094771;
                border-color: #007acc;
            }
            QListWidget::item:hover {
                background-color: #383838;
            }
        """)
    
    def dropEvent(self, event):
        """处理拖拽放下事件"""
        source_row = self.currentRow()
        super().dropEvent(event)
        target_row = self.currentRow()
        if source_row != target_row:
            self.slide_moved.emit(source_row, target_row)


class ItemEditor(QWidget):
    """单个要点编辑器"""
    
    content_changed = pyqtSignal()
    remove_requested = pyqtSignal()
    
    CONTENT_TYPES = [
        ("text", "📝 文本"),
        ("image", "🖼️ 图片"),
        ("flowchart", "📊 流程图"),
        ("icon", "⭐ 图标"),
        ("table", "📋 表格"),
    ]
    
    def __init__(self, item_data: dict = None, parent=None):
        super().__init__(parent)
        self.item_data = item_data or {"text": "", "level": 0, "content_type": "text"}
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        
        # 缩进级别
        self.level_spin = QSpinBox()
        self.level_spin.setRange(0, 3)
        self.level_spin.setPrefix("L")
        self.level_spin.setFixedWidth(50)
        self.level_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.level_spin.valueChanged.connect(self._on_changed)
        layout.addWidget(self.level_spin)
        
        # 内容类型
        self.type_combo = QComboBox()
        for value, label in self.CONTENT_TYPES:
            self.type_combo.addItem(label, value)
        self.type_combo.setFixedWidth(100)
        self.type_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                selection-background-color: #094771;
            }
        """)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)
        
        # 内容输入
        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText("输入要点内容...")
        self.content_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 8px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)
        self.content_edit.textChanged.connect(self._on_changed)
        layout.addWidget(self.content_edit, 1)
        
        # 删除按钮
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #888;
                border: none;
                border-radius: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f14c4c;
                color: white;
            }
        """)
        self.remove_btn.clicked.connect(self.remove_requested.emit)
        layout.addWidget(self.remove_btn)
    
    def _load_data(self):
        """加载数据到 UI（必须 blockSignals 防止中间状态覆盖数据）"""
        self.level_spin.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.content_edit.blockSignals(True)
        
        self.level_spin.setValue(self.item_data.get("level", 0))
        
        content_type = self.item_data.get("content_type", "text")
        for i, (value, _) in enumerate(self.CONTENT_TYPES):
            if value == content_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        self.content_edit.setText(self.item_data.get("text", ""))
        
        self.level_spin.blockSignals(False)
        self.type_combo.blockSignals(False)
        self.content_edit.blockSignals(False)
    
    def _on_type_changed(self, index):
        """内容类型变化"""
        self.item_data["content_type"] = self.type_combo.currentData()
        self.content_changed.emit()
    
    def _on_changed(self):
        """内容变化"""
        self.item_data["level"] = self.level_spin.value()
        self.item_data["text"] = self.content_edit.text()
        self.content_changed.emit()
    
    def get_data(self) -> dict:
        """获取编辑后的数据"""
        return {
            "id": self.item_data.get("id", str(uuid.uuid4())[:8]),
            "text": self.content_edit.text(),
            "level": self.level_spin.value(),
            "content_type": self.type_combo.currentData(),
            "source_range": self.item_data.get("source_range")
        }


class OutlinePanel(QWidget):
    """编辑大纲面板"""
    
    # 信号
    slide_selected = pyqtSignal(int)  # 幻灯片被选中
    slide_changed = pyqtSignal(int, dict)  # 幻灯片内容变化
    slide_added = pyqtSignal(int, dict)  # 新增幻灯片
    slide_deleted = pyqtSignal(int)  # 删除幻灯片
    slide_moved = pyqtSignal(int, int)  # 幻灯片移动
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slides_data = []
        self.current_index = -1
        self.item_editors = []
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("📋 幻灯片大纲")
        title.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 0;
            }
        """)
        header.addWidget(title)
        header.addStretch()
        
        # 添加幻灯片按钮
        self.add_btn = QPushButton("➕ 新增")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #28a745;
                color: white;
                border-color: #28a745;
            }
        """)
        self.add_btn.clicked.connect(self._on_add_slide)
        header.addWidget(self.add_btn)
        
        layout.addLayout(header)
        
        # 分割器：左侧导航 + 右侧编辑
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：幻灯片导航
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        self.slide_list = SlideListWidget()
        self.slide_list.currentRowChanged.connect(self._on_slide_selected)
        self.slide_list.slide_moved.connect(self._on_slide_moved)
        self.slide_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.slide_list.customContextMenuRequested.connect(self._show_context_menu)
        nav_layout.addWidget(self.slide_list)
        
        splitter.addWidget(nav_widget)
        
        # 右侧：编辑表单
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)
        edit_layout.setContentsMargins(8, 0, 0, 0)
        
        # 编辑表单
        form_group = QGroupBox("幻灯片属性")
        form_group.setStyleSheet("""
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
        """)
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(8)
        
        # 标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("幻灯片标题")
        self.title_edit.setStyleSheet(self._input_style())
        self.title_edit.textChanged.connect(self._on_form_changed)
        form_layout.addRow("标题:", self.title_edit)
        
        # 副标题
        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("副标题（可选）")
        self.subtitle_edit.setStyleSheet(self._input_style())
        self.subtitle_edit.textChanged.connect(self._on_form_changed)
        form_layout.addRow("副标题:", self.subtitle_edit)
        
        # 幻灯片类型（用户友好显示）
        self.type_combo = QComboBox()
        self.type_combo.addItems(["🎯 封面页", "📄 内容页"])
        self.type_combo.setStyleSheet(self._combo_style())
        self.type_combo.currentTextChanged.connect(self._on_form_changed)
        form_layout.addRow("类型:", self.type_combo)
        
        # 版式（用户友好显示）
        self.layout_combo = QComboBox()
        self.LAYOUT_OPTIONS = [
            ("center", "🎯 居中封面"),
            ("text_only", "📄 纯文本"),
            ("image_right", "🖼️ 图右文左"),
            ("image_left", "🖼️ 图左文右"),
            ("three_columns", "📊 三栏对比"),
            ("two_columns", "📊 两栏布局"),
            ("full_image", "🖼️ 全图背景"),
        ]
        for _, label in self.LAYOUT_OPTIONS:
            self.layout_combo.addItem(label)
        self.layout_combo.setStyleSheet(self._combo_style())
        self.layout_combo.currentTextChanged.connect(self._on_form_changed)
        form_layout.addRow("版式:", self.layout_combo)
        
        edit_layout.addWidget(form_group)
        
        # 要点编辑区
        items_group = QGroupBox("内容要点")
        items_group.setStyleSheet(form_group.styleSheet())
        items_layout = QVBoxLayout(items_group)
        
        # 要点列表（滚动区域）
        self.items_scroll = QScrollArea()
        self.items_scroll.setWidgetResizable(True)
        self.items_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(4, 4, 4, 4)
        self.items_layout.setSpacing(4)
        self.items_layout.addStretch()
        
        self.items_scroll.setWidget(self.items_container)
        items_layout.addWidget(self.items_scroll)
        
        # 添加要点按钮
        add_item_btn = QPushButton("➕ 添加要点")
        add_item_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px dashed #555;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                border-color: #007acc;
                color: #007acc;
            }
        """)
        add_item_btn.clicked.connect(self._on_add_item)
        items_layout.addWidget(add_item_btn)
        
        edit_layout.addWidget(items_group, 1)
        
        splitter.addWidget(edit_widget)
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter, 1)
    
    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 8px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """
    
    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                selection-background-color: #094771;
            }
        """
    
    def set_slides_data(self, slides: list):
        """设置幻灯片数据"""
        self.slides_data = slides
        self._refresh_list()
        if slides:
            self.slide_list.setCurrentRow(0)
    
    def get_slides_data(self) -> list:
        """获取幻灯片数据"""
        return self.slides_data
    
    def _refresh_list(self):
        """刷新幻灯片列表"""
        self.slide_list.clear()
        for i, slide in enumerate(self.slides_data):
            title = slide.get('title', f'幻灯片 {i+1}')
            slide_type = slide.get('type', 'content')
            icon = "🎯" if slide_type == "title" else "📄"
            item = QListWidgetItem(f"{icon} {i+1}. {title}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.slide_list.addItem(item)
    
    def _on_slide_selected(self, row: int):
        """幻灯片被选中"""
        if row < 0 or row >= len(self.slides_data):
            return
        
        self.current_index = row
        slide = self.slides_data[row]
        
        # 更新表单
        self.title_edit.blockSignals(True)
        self.subtitle_edit.blockSignals(True)
        self.type_combo.blockSignals(True)
        self.layout_combo.blockSignals(True)
        
        self.title_edit.setText(slide.get('title', ''))
        self.subtitle_edit.setText(slide.get('subtitle', ''))
        
        # 类型映射：技术名称 -> 用户友好显示
        slide_type = slide.get('type', 'content')
        type_label = "🎯 封面页" if slide_type == "title" else "📄 内容页"
        type_idx = self.type_combo.findText(type_label)
        if type_idx >= 0:
            self.type_combo.setCurrentIndex(type_idx)
        
        # 版式映射：技术名称 -> 用户友好显示
        layout_value = slide.get('layout', 'text_only')
        for i, (value, label) in enumerate(self.LAYOUT_OPTIONS):
            if value == layout_value:
                self.layout_combo.setCurrentIndex(i)
                break
        
        self.title_edit.blockSignals(False)
        self.subtitle_edit.blockSignals(False)
        self.type_combo.blockSignals(False)
        self.layout_combo.blockSignals(False)
        
        # 更新要点编辑区
        self._refresh_items()
        
        self.slide_selected.emit(row)
    
    def _refresh_items(self):
        """刷新要点编辑区"""
        # 清除现有编辑器
        for editor in self.item_editors:
            editor.setParent(None)
            editor.deleteLater()
        self.item_editors.clear()
        
        if self.current_index < 0 or self.current_index >= len(self.slides_data):
            return
        
        slide = self.slides_data[self.current_index]
        items = slide.get('items', [])
        
        for item_data in items:
            editor = ItemEditor(item_data)
            editor.content_changed.connect(self._on_item_changed)
            editor.remove_requested.connect(lambda e=editor: self._on_remove_item(e))
            
            self.items_layout.insertWidget(self.items_layout.count() - 1, editor)
            self.item_editors.append(editor)
    
    def _on_form_changed(self):
        """表单内容变化"""
        if self.current_index < 0 or self.current_index >= len(self.slides_data):
            return
        
        slide = self.slides_data[self.current_index]
        slide['title'] = self.title_edit.text()
        slide['subtitle'] = self.subtitle_edit.text()
        
        # 类型映射：用户友好显示 -> 技术名称
        type_label = self.type_combo.currentText()
        slide['type'] = "title" if "封面" in type_label else "content"
        
        # 版式映射：用户友好显示 -> 技术名称
        layout_idx = self.layout_combo.currentIndex()
        if 0 <= layout_idx < len(self.LAYOUT_OPTIONS):
            slide['layout'] = self.LAYOUT_OPTIONS[layout_idx][0]
        
        # 优化：只更新当前选中项，避免重建整个列表
        self._update_current_list_item()
        
        self.slide_changed.emit(self.current_index, slide)
    
    def _update_current_list_item(self):
        """更新当前选中的列表项（避免重建整个列表）"""
        if self.current_index < 0 or self.current_index >= self.slide_list.count():
            return
        
        item = self.slide_list.item(self.current_index)
        if item:
            slide = self.slides_data[self.current_index]
            title = slide.get('title', f'幻灯片 {self.current_index + 1}')
            slide_type = slide.get('type', 'content')
            icon = "🎯" if slide_type == "title" else "📄"
            item.setText(f"{icon} {self.current_index + 1}. {title}")
    
    def _on_item_changed(self):
        """要点内容变化"""
        if self.current_index < 0 or self.current_index >= len(self.slides_data):
            return
        
        slide = self.slides_data[self.current_index]
        items = []
        for editor in self.item_editors:
            items.append(editor.get_data())
        slide['items'] = items
        
        self.slide_changed.emit(self.current_index, slide)
    
    def _on_add_item(self):
        """添加新要点"""
        if self.current_index < 0 or self.current_index >= len(self.slides_data):
            return
        
        new_item = {
            "id": str(uuid.uuid4())[:8],
            "text": "",
            "level": 0,
            "content_type": "text"
        }
        
        editor = ItemEditor(new_item)
        editor.content_changed.connect(self._on_item_changed)
        editor.remove_requested.connect(lambda e=editor: self._on_remove_item(e))
        
        self.items_layout.insertWidget(self.items_layout.count() - 1, editor)
        self.item_editors.append(editor)
        
        # 聚焦到新编辑器
        editor.content_edit.setFocus()
        
        self._on_item_changed()
    
    def _on_remove_item(self, editor: ItemEditor):
        """删除要点"""
        if editor in self.item_editors:
            self.item_editors.remove(editor)
            editor.setParent(None)
            editor.deleteLater()
            self._on_item_changed()
    
    def _on_add_slide(self):
        """添加新幻灯片"""
        new_slide = {
            "id": str(uuid.uuid4())[:8],
            "type": "content",
            "layout": "text_only",
            "title": "新幻灯片",
            "subtitle": "",
            "items": []
        }
        
        insert_pos = self.current_index + 1 if self.current_index >= 0 else len(self.slides_data)
        self.slides_data.insert(insert_pos, new_slide)
        
        self._refresh_list()
        self.slide_list.setCurrentRow(insert_pos)
        
        self.slide_added.emit(insert_pos, new_slide)
    
    def _on_slide_moved(self, from_idx: int, to_idx: int):
        """幻灯片移动"""
        if 0 <= from_idx < len(self.slides_data) and 0 <= to_idx < len(self.slides_data):
            slide = self.slides_data.pop(from_idx)
            self.slides_data.insert(to_idx, slide)
            self.current_index = to_idx
            # 刷新列表以更新序号和标题
            self._refresh_list()
            self.slide_list.setCurrentRow(to_idx)
            self.slide_moved.emit(from_idx, to_idx)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.slide_list.itemAt(pos)
        if not item:
            return
        
        row = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
        """)
        
        duplicate_action = menu.addAction("📋 复制幻灯片")
        delete_action = menu.addAction("🗑️ 删除幻灯片")
        
        action = menu.exec(self.slide_list.mapToGlobal(pos))
        
        if action == duplicate_action:
            self._duplicate_slide(row)
        elif action == delete_action:
            self._delete_slide(row)
    
    def _duplicate_slide(self, row: int):
        """复制幻灯片"""
        if 0 <= row < len(self.slides_data):
            import copy
            new_slide = copy.deepcopy(self.slides_data[row])
            new_slide['id'] = str(uuid.uuid4())[:8]
            new_slide['title'] = f"{new_slide.get('title', '')} (副本)"
            
            self.slides_data.insert(row + 1, new_slide)
            self._refresh_list()
            self.slide_list.setCurrentRow(row + 1)
    
    def _delete_slide(self, row: int):
        """删除幻灯片"""
        if 0 <= row < len(self.slides_data):
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除第 {row + 1} 页幻灯片吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.slides_data.pop(row)
                self._refresh_list()
                
                if self.current_index >= len(self.slides_data):
                    self.current_index = len(self.slides_data) - 1
                
                if self.current_index >= 0:
                    self.slide_list.setCurrentRow(self.current_index)
                
                self.slide_deleted.emit(row)
    
    def apply_theme(self, theme: dict):
        """应用主题样式"""
        # 更新幻灯片列表样式
        self.slide_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme['dialog_bg']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                background-color: {theme['button_bg']};
                border: 1px solid {theme['border_color']};
                border-radius: 4px;
                padding: 8px;
                margin: 2px 0;
                color: {theme['dialog_color']};
            }}
            QListWidget::item:selected {{
                background-color: {theme['accent_color']};
                border-color: {theme['accent_color']};
            }}
            QListWidget::item:hover {{
                background-color: {theme['button_hover']};
            }}
        """)
        
        # 更新表单样式
        for line_edit in self.findChildren(QLineEdit):
            line_edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QLineEdit:focus {{
                    border-color: {theme['accent_color']};
                }}
            """)
        
        for combo_box in self.findChildren(QComboBox):
            combo_box.setStyleSheet(f"""
                QComboBox {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QComboBox:hover {{
                    border-color: {theme['accent_color']};
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid {theme['dialog_color']};
                    width: 0;
                    height: 0;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    selection-background-color: {theme['accent_color']};
                }}
            """)
        
        for spin_box in self.findChildren(QSpinBox):
            spin_box.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                    padding: 4px;
                }}
                QSpinBox:hover {{
                    border-color: {theme['accent_color']};
                }}
            """)
        
        # 更新按钮样式
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme['button_bg']};
                    color: {theme['dialog_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: {theme['button_hover']};
                    border-color: {theme['accent_color']};
                }}
                QPushButton:pressed {{
                    background-color: {theme['button_pressed']};
                }}
            """)
        
        # 更新标签样式
        for label in self.findChildren(QLabel):
            label.setStyleSheet(f"""
                QLabel {{
                    color: {theme['dialog_color']};
                    font-size: 12px;
                    padding: 2px;
                }}
            """)
