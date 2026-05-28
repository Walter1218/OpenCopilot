import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, 
    QPushButton, QLineEdit, QLabel, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt

from persona_manager import PersonaManager

class PersonaManagerDialog(QDialog):
    def __init__(self, parent=None, base_dir=None):
        super().__init__(parent)
        self.setWindowTitle("🎭 角色工坊 (Persona Workshop)")
        self.resize(800, 500)
        self.manager = PersonaManager(base_dir=base_dir)
        
        self.initUI()
        self.refresh_list()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # 使用 Splitter 分割左右两侧
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # --- 左侧：列表与新建 ---
        left_widget = QDialog()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self.list_widget)
        
        self.btn_new = QPushButton("➕ 新建角色")
        self.btn_new.clicked.connect(self._on_new_clicked)
        left_layout.addWidget(self.btn_new)
        
        splitter.addWidget(left_widget)
        
        # --- 右侧：编辑区 ---
        right_widget = QDialog()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 名字输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("标识符 (如: test 或 custom/test):"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("请输入英文字母及斜杠组合")
        name_layout.addWidget(self.input_name)
        right_layout.addLayout(name_layout)
        
        # Prompt 内容
        right_layout.addWidget(QLabel("系统提示词 (System Prompt):"))
        self.text_editor = QTextEdit()
        # 优化显示
        self.text_editor.setStyleSheet("font-family: monospace; font-size: 13px;")
        right_layout.addWidget(self.text_editor)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 保存")
        self.btn_save.clicked.connect(self._on_save_clicked)
        
        self.btn_delete = QPushButton("🗑️ 删除")
        self.btn_delete.setStyleSheet("color: red;")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        
        action_layout.addStretch()
        action_layout.addWidget(self.btn_delete)
        action_layout.addWidget(self.btn_save)
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 600])

    def refresh_list(self, select_name=None):
        """刷新列表并保持选中状态"""
        self.list_widget.clear()
        personas = self.manager.list_personas()
        for p in personas:
            self.list_widget.addItem(p)
            
        if select_name:
            items = self.list_widget.findItems(select_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.list_widget.setCurrentItem(items[0])
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _on_item_selected(self, current, previous):
        if not current:
            self.input_name.clear()
            self.text_editor.clear()
            self.input_name.setReadOnly(False)
            return
            
        name = current.text()
        content = self.manager.get_persona(name)
        if content is not None:
            self.input_name.setText(name)
            self.text_editor.setPlainText(content)
            # 编辑模式下名字不可更改（为了简便，防止重命名覆盖错乱）
            self.input_name.setReadOnly(True)

    def _on_new_clicked(self):
        """进入新建状态"""
        self.list_widget.clearSelection()
        self.input_name.clear()
        self.input_name.setReadOnly(False)
        self.text_editor.clear()
        self.text_editor.setPlainText("你是一个有用的AI助手...")
        self.input_name.setFocus()

    def _on_save_clicked(self):
        name = self.input_name.text().strip()
        content = self.text_editor.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "角色标识符不能为空。")
            return
        if not content:
            QMessageBox.warning(self, "错误", "提示词内容不能为空。")
            return
            
        self.manager.save_persona(name, content)
        # QMessageBox.information(self, "成功", f"角色 [{name}] 已保存。")
        self.refresh_list(select_name=name)
        self.input_name.setReadOnly(True)

    def _on_delete_clicked(self):
        name = self.input_name.text().strip()
        if not name:
            return
            
        reply = QMessageBox.question(self, "确认删除", f"确定要删除角色 [{name}] 吗？\n此操作不可逆！",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.manager.delete_persona(name)
            if success:
                self.refresh_list()
            else:
                QMessageBox.warning(self, "删除失败", msg)