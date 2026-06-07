"""
原文面板

功能：
- 显示 AI 原始输出的完整文本
- 已提炼内容用蓝色半透明背景高亮标记
- 未提炼内容正常显示，可被用户选中
- 选中工具：切换为"选中模式"后，用户拖选文本会以橙色高亮
- 支持双向联动
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QToolBar, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint
from PyQt6.QtGui import (
    QTextCharFormat, QColor, QBrush, QFont, QTextCursor,
    QAction, QKeySequence, QPainter, QPen, QDrag
)

from .source_matcher import SourceMatcher, TextRange


class SourceTextEdit(QTextEdit):
    """支持高亮标记的原文编辑器"""
    
    # 信号
    text_selected = pyqtSignal(str, int, int)  # 选中文本, 起始位置, 结束位置
    position_clicked = pyqtSignal(int)  # 点击位置
    
    # 高亮格式
    EXTRACTED_FORMAT = QTextCharFormat()
    EXTRACTED_FORMAT.setBackground(QColor(77, 166, 255, 60))  # 半透明蓝
    
    SELECTED_FORMAT = QTextCharFormat()
    SELECTED_FORMAT.setBackground(QColor(255, 153, 51, 80))  # 半透明橙
    
    HIGHLIGHT_FORMAT = QTextCharFormat()
    HIGHLIGHT_FORMAT.setBackground(QColor(255, 255, 0, 100))  # 半透明黄
    
    # 拖拽相关信号
    drag_started = pyqtSignal(str)  # 拖拽开始，携带文本
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.source_matcher = SourceMatcher()
        self.select_mode = False
        self.selection_start = -1
        self.current_highlight_range = None
        self._drag_start_pos = None
        self._drag_text = None
        
        # 启用拖拽
        self.setAcceptDrops(False)  # 不接受拖入
        
        # 设置字体
        font = QFont("Helvetica Neue", 13)
        self.setFont(font)
        
        # 样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 12px;
                selection-background-color: rgba(255, 153, 51, 120);
            }
        """)
    
    def set_source_matcher(self, matcher: SourceMatcher):
        """设置原文匹配器"""
        self.source_matcher = matcher
        self._apply_highlights()
    
    def set_select_mode(self, enabled: bool):
        """切换选中模式"""
        self.select_mode = enabled
        if enabled:
            self.setReadOnly(False)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setReadOnly(True)
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            self.selection_start = -1
    
    def _apply_highlights(self):
        """应用所有高亮（优化版：批量操作，减少重绘）"""
        # 使用批量更新减少重绘次数
        self.setUpdatesEnabled(False)
        
        try:
            # 清除所有格式
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.setCharFormat(QTextCharFormat())
            cursor.clearSelection()
            
            # 应用已提炼范围的高亮
            for text_range in self.source_matcher.get_extracted_ranges():
                self._apply_format_to_range(text_range, self.EXTRACTED_FORMAT)
            
            # 应用用户选中范围的高亮
            for text_range in self.source_matcher.get_selected_ranges():
                self._apply_format_to_range(text_range, self.SELECTED_FORMAT)
            
            cursor.endEditBlock()
        finally:
            self.setUpdatesEnabled(True)
    
    def _apply_format_to_range(self, text_range: TextRange, char_format: QTextCharFormat):
        """对指定范围应用格式"""
        cursor = self.textCursor()
        cursor.setPosition(text_range.start)
        cursor.setPosition(text_range.end, QTextCursor.MoveMode.KeepAnchor)
        cursor.mergeCharFormat(char_format)
    
    def highlight_range(self, text_range: TextRange):
        """临时高亮某个范围（用于双向联动）"""
        # 清除之前的临时高亮
        if self.current_highlight_range:
            self._apply_format_to_range(self.current_highlight_range, self.EXTRACTED_FORMAT)
        
        # 应用新高亮
        self.current_highlight_range = text_range
        self._apply_format_to_range(text_range, self.HIGHLIGHT_FORMAT)
        
        # 滚动到可见区域
        cursor = self.textCursor()
        cursor.setPosition(text_range.start)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def clear_temporary_highlight(self):
        """清除临时高亮"""
        if self.current_highlight_range:
            # 恢复原格式
            if self.source_matcher.is_position_extracted(self.current_highlight_range.start):
                self._apply_format_to_range(self.current_highlight_range, self.EXTRACTED_FORMAT)
            else:
                self._apply_format_to_range(self.current_highlight_range, QTextCharFormat())
            self.current_highlight_range = None
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        super().mousePressEvent(event)
        try:
            # 使用 pos() 方法代替 position().toPoint() 以提高兼容性
            cursor = self.cursorForPosition(event.pos())
            pos = cursor.position()
            self.position_clicked.emit(pos)
            
            # 记录拖拽起始位置
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
                # 获取选中文本或当前位置的文本
                cursor = self.textCursor()
                if cursor.hasSelection():
                    self._drag_text = cursor.selectedText()
                else:
                    # 获取当前行文本
                    cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                    self._drag_text = cursor.selectedText()
        except Exception as e:
            print(f"[ERROR] SourceTextEdit.mousePressEvent: {e}")
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理拖拽"""
        if self._drag_start_pos is not None and self._drag_text:
            # 检查是否超过拖拽阈值
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance >= 10:  # 拖拽阈值
                self._start_drag()
                return
        super().mouseMoveEvent(event)
    
    def _start_drag(self):
        """开始拖拽操作"""
        if not self._drag_text:
            return
        
        try:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self._drag_text)
            mime_data.setData("application/x-sourcetext", self._drag_text.encode('utf-8'))
            drag.setMimeData(mime_data)
            
            # 创建拖拽图标
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(200, 30)
            pixmap.fill(QColor(255, 153, 51, 180))
            from PyQt6.QtGui import QPainter as QP
            painter = QP(pixmap)
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Helvetica Neue", 11))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 
                            self._drag_text[:20] + "..." if len(self._drag_text) > 20 else self._drag_text)
            painter.end()
            drag.setPixmap(pixmap)
            
            # 发送信号
            self.drag_started.emit(self._drag_text)
            
            # 执行拖拽
            self._drag_start_pos = None
            self._drag_text = None
            drag.exec(Qt.DropAction.CopyAction)
        except Exception as e:
            print(f"[ERROR] SourceTextEdit._start_drag: {e}")
            self._drag_start_pos = None
            self._drag_text = None
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
        
        if self.select_mode:
            cursor = self.textCursor()
            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                selected_text = cursor.selectedText()
                
                # 检查是否与已提炼范围重叠
                is_extracted = False
                for r in self.source_matcher.get_extracted_ranges():
                    if r.start < end and start < r.end:
                        is_extracted = True
                        break
                
                if not is_extracted:
                    # 添加到选中范围
                    self.source_matcher.add_selected_range(TextRange(start=start, end=end, text=selected_text))
                    self._apply_highlights()
                    self.text_selected.emit(selected_text, start, end)
                else:
                    # 清除选择
                    cursor.clearSelection()
                    self.setTextCursor(cursor)


class SourcePanel(QWidget):
    """原文面板"""
    
    # 信号
    text_selected = pyqtSignal(str, int, int)  # 选中文本, 起始位置, 结束位置 (加入当前幻灯片)
    new_slide_requested = pyqtSignal(str, int, int)  # 请求创建新幻灯片, 起始位置, 结束位置
    position_clicked = pyqtSignal(int)  # 点击位置
    select_mode_changed = pyqtSignal(bool)  # 选中模式变化
    regenerate_slide_requested = pyqtSignal(str, str)  # 请求重新生成幻灯片 (选中文本, 表达方式)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_matcher = SourceMatcher()
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("📄 AI 原始输出")
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
        
        # 选中工具按钮
        self.select_btn = QPushButton("🎯 选中模式")
        self.select_btn.setCheckable(True)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #ff9933;
                color: white;
                border-color: #ff9933;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:checked:hover {
                background-color: #ff8800;
            }
        """)
        self.select_btn.toggled.connect(self._on_select_mode_toggled)
        header.addWidget(self.select_btn)
        
        layout.addLayout(header)
        
        # 图例
        legend = QHBoxLayout()
        legend.setSpacing(12)
        
        extracted_label = QLabel("■ 已提炼")
        extracted_label.setStyleSheet("color: rgba(77, 166, 255, 0.8); font-size: 11px;")
        legend.addWidget(extracted_label)
        
        selected_label = QLabel("■ 已选中")
        selected_label.setStyleSheet("color: rgba(255, 153, 51, 0.8); font-size: 11px;")
        legend.addWidget(selected_label)
        
        legend.addStretch()
        
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #888; font-size: 11px;")
        legend.addWidget(self.count_label)
        
        layout.addLayout(legend)
        
        # 原文编辑器
        self.text_edit = SourceTextEdit()
        self.text_edit.text_selected.connect(self._on_text_selected)
        self.text_edit.position_clicked.connect(self._on_position_clicked)
        layout.addWidget(self.text_edit)
        
        # 选中操作按钮（初始隐藏）
        self.action_bar = QHBoxLayout()
        self.action_bar.setSpacing(8)
        
        self.add_to_slide_btn = QPushButton("➕ 加入当前幻灯片")
        self.add_to_slide_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.add_to_slide_btn.clicked.connect(self._on_add_to_slide)
        self.action_bar.addWidget(self.add_to_slide_btn)
        
        self.create_slide_btn = QPushButton("📋 创建新幻灯片")
        self.create_slide_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.create_slide_btn.clicked.connect(self._on_create_slide)
        self.action_bar.addWidget(self.create_slide_btn)
        
        self.cancel_btn = QPushButton("✖ 取消选中")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel_selection)
        self.action_bar.addWidget(self.cancel_btn)
        
        # 重新生成当前幻灯片按钮
        self.regenerate_btn = QPushButton("🔄 重新生成幻灯片")
        self.regenerate_btn.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7b1fa2;
            }
        """)
        self.regenerate_btn.clicked.connect(self._on_regenerate_slide)
        self.action_bar.addWidget(self.regenerate_btn)
        
        self.action_bar_widget = QWidget()
        self.action_bar_widget.setLayout(self.action_bar)
        self.action_bar_widget.setVisible(False)
        layout.addWidget(self.action_bar_widget)
    
    def set_original_text(self, text: str):
        """设置原文"""
        self.text_edit.setPlainText(text)
        self._update_count_label()
    
    def set_source_matcher(self, matcher: SourceMatcher):
        """设置原文匹配器"""
        self.source_matcher = matcher
        self.text_edit.set_source_matcher(matcher)
        self._update_count_label()
    
    def _update_count_label(self):
        """更新统计标签"""
        total_len = len(self.text_edit.toPlainText())
        extracted_len = sum(r.length for r in self.source_matcher.get_extracted_ranges())
        selected_len = sum(r.length for r in self.source_matcher.get_selected_ranges())
        
        if total_len > 0:
            extracted_pct = int(extracted_len / total_len * 100)
            self.count_label.setText(f"总长: {total_len} | 已提炼: {extracted_pct}% | 已选中: {selected_len} 字")
    
    def _on_select_mode_toggled(self, checked: bool):
        """选中模式切换"""
        self.text_edit.set_select_mode(checked)
        self.select_mode_changed.emit(checked)
        
        if not checked:
            self.action_bar_widget.setVisible(False)
    
    def _on_text_selected(self, text: str, start: int, end: int):
        """文本被选中"""
        self.action_bar_widget.setVisible(True)
        self.text_selected.emit(text, start, end)
    
    def _on_position_clicked(self, pos: int):
        """位置被点击"""
        self.position_clicked.emit(pos)
        
        # 双向联动：找到对应的幻灯片
        result = self.source_matcher.find_slide_for_position(pos)
        if result:
            slide_idx, item_idx = result
            # 可以发送信号让大纲面板高亮对应的幻灯片
    
    def _on_add_to_slide(self):
        """将选中文本加入当前幻灯片"""
        selected_ranges = self.source_matcher.get_selected_ranges()
        if selected_ranges:
            last_range = selected_ranges[-1]
            text = self.text_edit.toPlainText()[last_range.start:last_range.end]
            # 发送信号，由主对话框处理
            self.text_selected.emit(text, last_range.start, last_range.end)
    
    def _on_create_slide(self):
        """基于选中内容创建新幻灯片"""
        selected_ranges = self.source_matcher.get_selected_ranges()
        if selected_ranges:
            last_range = selected_ranges[-1]
            text = self.text_edit.toPlainText()[last_range.start:last_range.end]
            # 发送信号，由主对话框处理创建新幻灯片
            self.new_slide_requested.emit(text, last_range.start, last_range.end)
            self.text_selected.emit(text, last_range.start, last_range.end)
    
    def _on_regenerate_slide(self):
        """重新生成当前幻灯片 - 弹出表达方式选择对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup
        
        selected_ranges = self.source_matcher.get_selected_ranges()
        if not selected_ranges:
            return
        
        # 获取选中的文本
        last_range = selected_ranges[-1]
        selected_text = self.text_edit.toPlainText()[last_range.start:last_range.end]
        
        # 创建表达方式选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("🔄 选择表达方式")
        dialog.setMinimumSize(350, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # 提示
        label = QLabel("请选择重新生成的表达方式：")
        label.setStyleSheet("color: #aaa; font-size: 13px;")
        layout.addWidget(label)
        
        # 预览选中的文本
        preview_text = selected_text[:80] + "..." if len(selected_text) > 80 else selected_text
        preview = QLabel(f"选中文本：{preview_text}")
        preview.setStyleSheet("color: #888; font-size: 11px; border: 1px solid #3c3c3c; padding: 6px; border-radius: 4px;")
        preview.setWordWrap(True)
        layout.addWidget(preview)
        
        # 表达方式选项
        button_group = QButtonGroup(dialog)
        
        options = [
            ("text", "📝 纯文本", "以要点形式呈现"),
            ("image_right", "🖼️ 图文混排（图右）", "右侧配图，左侧文字"),
            ("image_left", "🖼️ 图文混排（图左）", "左侧配图，右侧文字"),
            ("table", "📊 表格", "以表格形式呈现数据"),
            ("chart", "📈 图表", "以柱状图/折线图呈现"),
            ("flowchart", "🔀 流程图", "以流程图形式呈现"),
            ("three_columns", "📋 三栏布局", "三列并排展示"),
        ]
        
        for value, title, desc in options:
            radio = QRadioButton(f"{title}\n{desc}")
            radio.setStyleSheet("""
                QRadioButton {
                    color: #d4d4d4;
                    font-size: 12px;
                    padding: 6px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
            radio.setProperty("value", value)
            button_group.addButton(radio)
            layout.addWidget(radio)
            
            if value == "text":
                radio.setChecked(True)
        
        # 按钮
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
        
        generate_btn = QPushButton("🔄 重新生成")
        generate_btn.setStyleSheet("""
            QPushButton {
                background: #9c27b0; color: #fff; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #7b1fa2; }
        """)
        generate_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(generate_btn)
        
        layout.addLayout(btn_row)
        
        # 执行对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选中的表达方式
            selected_button = button_group.checkedButton()
            if selected_button:
                expression_type = selected_button.property("value")
                # 发送信号
                self.regenerate_slide_requested.emit(selected_text, expression_type)
    
    def apply_theme(self, theme: dict):
        """应用主题样式"""
        # 更新标题样式
        title = self.findChild(QLabel, "")
        if title:
            title.setStyleSheet(f"""
                QLabel {{
                    color: {theme['dialog_color']};
                    font-size: 14px;
                    font-weight: bold;
                    padding: 4px 0;
                }}
            """)
        
        # 更新按钮样式
        self.select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['dialog_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: {theme['accent_color']};
                color: white;
                border-color: {theme['accent_color']};
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QPushButton:checked:hover {{
                background-color: {theme['button_pressed']};
            }}
        """)
        
        # 更新图例标签颜色
        for label in self.findChildren(QLabel):
            text = label.text()
            if "已提炼" in text:
                label.setStyleSheet(f"color: rgba(77, 166, 255, 0.8); font-size: 11px;")
            elif "已选中" in text:
                label.setStyleSheet(f"color: rgba(255, 153, 51, 0.8); font-size: 11px;")
            elif "总长" in text:
                label.setStyleSheet(f"color: {theme['dialog_color']}; opacity: 0.7; font-size: 11px;")
        
        # 更新文本编辑器样式
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['dialog_bg']};
                color: {theme['dialog_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 6px;
                padding: 12px;
                selection-background-color: rgba(255, 153, 51, 120);
            }}
        """)
    
    def _on_cancel_selection(self):
        """取消所有选中"""
        self.source_matcher.clear_selected_ranges()
        self.text_edit._apply_highlights()
        self.action_bar_widget.setVisible(False)
        self._update_count_label()
    
    def highlight_slide_content(self, slide_index: int, item_index: int = None):
        """高亮对应的幻灯片内容（双向联动）"""
        try:
            text_range = self.source_matcher.find_source_position_for_item(slide_index, item_index)
            if text_range:
                self.text_edit.highlight_range(text_range)
        except Exception as e:
            print(f"[ERROR] SourcePanel.highlight_slide_content: slide={slide_index}, item={item_index}, err={e}")
