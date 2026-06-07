"""gui/dialogs/ppt_preview.py module

.. deprecated::
    此模块已废弃，请使用 opencopilot.capabilities.ppt 中的组件：
    - OutlinePanel: 大纲面板，支持拖拽排序和表单编辑
    - PreviewPanel: WYSIWYG预览面板，支持Click-to-Edit
    - AICopilotChatWidget: AI对话共创组件，支持流式反馈和Undo/Redo
    
    新版组件已集成到 gui.v5.studio_window.StudioWindowV5 中。
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QSplitter, QWidget, QListWidget, QFormLayout, QLineEdit, QComboBox
from PyQt6.QtCore import Qt
class PPTPreviewDialog(QDialog):
    def __init__(self, json_data, parent=None):
        super().__init__(parent)
        self.json_data = json_data
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("PPT 大纲排版器 - AI 伴生共创")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #e0e0e0;
            }
            QListWidget {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #4da6ff;
                color: white;
                border-radius: 4px;
            }
            QLineEdit, QTextEdit {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QLabel {
                font-weight: bold;
                margin-top: 10px;
            }
        """)

        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：缩略图导航
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.slide_list = QListWidget()
        for idx, slide in enumerate(self.json_data):
            title = slide.get('title', f'幻灯片 {idx+1}')
            item = QListWidgetItem(f"{idx+1}. {title}")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.slide_list.addItem(item)
            
        self.slide_list.currentRowChanged.connect(self._on_slide_selected)
        left_layout.addWidget(QLabel("幻灯片导航"))
        left_layout.addWidget(self.slide_list)
        
        # 中间：表单编辑区
        right_panel = QWidget()
        right_outer_layout = QVBoxLayout(right_panel)
        right_outer_layout.setContentsMargins(20, 10, 20, 10)

        self.right_layout = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.subtitle_edit = QLineEdit()
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["center", "text_only", "image_right", "image_left", "three_columns", "table"])
        self.items_edit = QTextEdit()
        self.items_edit.setMinimumHeight(200)
        
        # 绑定修改事件到 JSON 数据
        self.title_edit.textChanged.connect(self._update_current_slide)
        self.subtitle_edit.textChanged.connect(self._update_current_slide)
        self.layout_combo.currentTextChanged.connect(self._update_current_slide)
        self.items_edit.textChanged.connect(self._update_current_slide)

        self.right_layout.addRow("页面标题:", self.title_edit)
        self.right_layout.addRow("副标题:", self.subtitle_edit)
        self.right_layout.addRow("页面版式:", self.layout_combo)
        self.right_layout.addRow("内容要点\n(每行一条):", self.items_edit)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 确认并导出 PPT")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white; font-weight: bold; border-radius: 6px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)

        right_outer_layout.addLayout(self.right_layout)
        right_outer_layout.addStretch()
        right_outer_layout.addLayout(btn_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600])
        main_layout.addWidget(splitter)
        
        if self.slide_list.count() > 0:
            self.slide_list.setCurrentRow(0)

    def _on_slide_selected(self, row):
        if row < 0 or row >= len(self.json_data): return
        slide = self.json_data[row]
        
        # 暂时断开信号以避免更新数据
        self.title_edit.blockSignals(True)
        self.subtitle_edit.blockSignals(True)
        self.layout_combo.blockSignals(True)
        self.items_edit.blockSignals(True)
        
        self.title_edit.setText(slide.get("title", ""))
        self.subtitle_edit.setText(slide.get("subtitle", ""))
        self.layout_combo.setCurrentText(slide.get("layout", "text_only"))
        
        # 转换 items 为纯文本
        items_text = ""
        if "items" in slide:
            items_text = "\n".join([item.get("text", "") for item in slide["items"]])
        self.items_edit.setText(items_text)
        
        # 恢复信号
        self.title_edit.blockSignals(False)
        self.subtitle_edit.blockSignals(False)
        self.layout_combo.blockSignals(False)
        self.items_edit.blockSignals(False)

    def _update_current_slide(self):
        row = self.slide_list.currentRow()
        if row < 0 or row >= len(self.json_data): return
        
        slide = self.json_data[row]
        slide["title"] = self.title_edit.text()
        slide["subtitle"] = self.subtitle_edit.text()
        slide["layout"] = self.layout_combo.currentText()
        
        # 将纯文本转回 items 结构
        lines = self.items_edit.toPlainText().strip().split("\n")
        slide["items"] = [{"level": 0, "text": line.strip()} for line in lines if line.strip()]
        
        # 同步更新左侧列表标题
        self.slide_list.currentItem().setText(f"{row+1}. {slide['title']}")

    def get_final_json(self):
        return self.json_data


# ==========================================
# 1. 后台大模型请求线程 (避免阻塞UI)
# ==========================================
