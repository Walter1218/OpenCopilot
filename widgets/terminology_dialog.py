"""
术语库管理组件
支持术语库列表、术语编辑、导入导出、一致性检查
"""
import os
import json
import csv
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class MatchType(Enum):
    """匹配类型"""
    EXACT = "exact"      # 精确匹配
    FUZZY = "fuzzy"      # 模糊匹配
    PREFIX = "prefix"    # 前缀匹配
    SUFFIX = "suffix"    # 后缀匹配


@dataclass
class TerminologyEntry:
    """术语条目"""
    source: str
    target: str
    category: str = ""
    notes: str = ""
    context: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "source": self.source,
            "target": self.target,
            "category": self.category,
            "notes": self.notes,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TerminologyEntry':
        """从字典创建"""
        entry = cls(
            source=data["source"],
            target=data["target"],
            category=data.get("category", ""),
            notes=data.get("notes", ""),
            context=data.get("context", "")
        )
        if data.get("created_at"):
            entry.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            entry.updated_at = datetime.fromisoformat(data["updated_at"])
        return entry


@dataclass
class TerminologyDatabase:
    """术语库"""
    name: str
    description: str = ""
    entries: List[TerminologyEntry] = field(default_factory=list)
    categories: Set[str] = field(default_factory=set)
    
    def add_entry(self, entry: TerminologyEntry) -> bool:
        """添加术语条目"""
        # 检查是否已存在
        for existing in self.entries:
            if existing.source == entry.source:
                # 更新现有条目
                existing.target = entry.target
                existing.category = entry.category
                existing.notes = entry.notes
                existing.context = entry.context
                existing.updated_at = datetime.now()
                return True
        
        # 添加新条目
        self.entries.append(entry)
        if entry.category:
            self.categories.add(entry.category)
        return True
    
    def remove_entry(self, source: str) -> bool:
        """移除术语条目"""
        self.entries = [e for e in self.entries if e.source != source]
        return True
    
    def search_entries(self, query: str, match_type: MatchType = MatchType.FUZZY) -> List[TerminologyEntry]:
        """搜索术语条目"""
        results = []
        query_lower = query.lower()
        
        for entry in self.entries:
            if match_type == MatchType.EXACT:
                if entry.source == query or entry.target == query:
                    results.append(entry)
            elif match_type == MatchType.FUZZY:
                if (query_lower in entry.source.lower() or 
                    query_lower in entry.target.lower() or
                    query_lower in entry.notes.lower()):
                    results.append(entry)
            elif match_type == MatchType.PREFIX:
                if (entry.source.lower().startswith(query_lower) or 
                    entry.target.lower().startswith(query_lower)):
                    results.append(entry)
            elif match_type == MatchType.SUFFIX:
                if (entry.source.lower().endswith(query_lower) or 
                    entry.target.lower().endswith(query_lower)):
                    results.append(entry)
        
        return results
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "total_entries": len(self.entries),
            "categories": list(self.categories)
        }


class TerminologyDialog(QDialog):
    """术语库管理对话框"""
    
    # 信号
    entry_added = pyqtSignal(str)  # 术语添加信号
    entry_removed = pyqtSignal(str)  # 术语移除信号
    
    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        self.setWindowTitle("术语库管理")
        self.setMinimumSize(900, 600)
        
        # 数据
        self.databases: List[TerminologyDatabase] = []
        self.current_database: Optional[TerminologyDatabase] = None
        
        # 初始化默认数据库
        self._init_default_databases()
        
        # 初始化UI
        self._init_ui()
    
    def _init_default_databases(self):
        """初始化默认数据库"""
        # 通用术语库
        general_db = TerminologyDatabase(name="通用术语库", description="通用术语")
        self.databases.append(general_db)
        
        # 技术术语库
        tech_db = TerminologyDatabase(name="技术术语库", description="技术领域术语")
        self.databases.append(tech_db)
        
        # 商务术语库
        business_db = TerminologyDatabase(name="商务术语库", description="商务领域术语")
        self.databases.append(business_db)
        
        # 设置默认数据库
        self.current_database = self.databases[0]
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 术语管理标签页
        management_tab = self._create_management_tab()
        self.tab_widget.addTab(management_tab, "术语管理")
        
        # 导入导出标签页
        import_export_tab = self._create_import_export_tab()
        self.tab_widget.addTab(import_export_tab, "导入导出")
        
        # 一致性检查标签页
        consistency_tab = self._create_consistency_tab()
        self.tab_widget.addTab(consistency_tab, "一致性检查")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
    
    def _create_management_tab(self) -> QWidget:
        """创建术语管理标签页"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # 左侧：术语库列表
        left_group = QGroupBox("术语库")
        left_layout = QVBoxLayout()
        
        self.list_databases = QListWidget()
        self.list_databases.currentItemChanged.connect(self._on_database_selected)
        left_layout.addWidget(self.list_databases)
        
        db_btn_layout = QHBoxLayout()
        self.btn_add_db = QPushButton("添加")
        self.btn_add_db.clicked.connect(self._on_add_database)
        db_btn_layout.addWidget(self.btn_add_db)
        
        self.btn_remove_db = QPushButton("移除")
        self.btn_remove_db.clicked.connect(self._on_remove_database)
        db_btn_layout.addWidget(self.btn_remove_db)
        
        left_layout.addLayout(db_btn_layout)
        left_group.setLayout(left_layout)
        layout.addWidget(left_group)
        
        # 右侧：术语列表和编辑
        right_layout = QVBoxLayout()
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("搜索术语...")
        self.edit_search.textChanged.connect(self._on_search)
        search_layout.addWidget(self.edit_search)
        
        self.combo_match_type = QComboBox()
        self.combo_match_type.addItems(["模糊匹配", "精确匹配", "前缀匹配", "后缀匹配"])
        search_layout.addWidget(self.combo_match_type)
        
        right_layout.addLayout(search_layout)
        
        # 术语表格
        self.table_entries = QTableWidget()
        self.table_entries.setColumnCount(5)
        self.table_entries.setHorizontalHeaderLabels(["源术语", "目标术语", "分类", "备注", "操作"])
        self.table_entries.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_entries.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table_entries)
        
        # 编辑区域
        edit_group = QGroupBox("编辑术语")
        edit_layout = QFormLayout()
        
        self.edit_source = QLineEdit()
        edit_layout.addRow("源术语:", self.edit_source)
        
        self.edit_target = QLineEdit()
        edit_layout.addRow("目标术语:", self.edit_target)
        
        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        self.combo_category.addItems(["技术", "商务", "学术", "通用"])
        edit_layout.addRow("分类:", self.combo_category)
        
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(60)
        edit_layout.addRow("备注:", self.edit_notes)
        
        self.edit_context = QLineEdit()
        edit_layout.addRow("上下文:", self.edit_context)
        
        edit_group.setLayout(edit_layout)
        right_layout.addWidget(edit_group)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.btn_add_entry = QPushButton("添加")
        self.btn_add_entry.clicked.connect(self._on_add_entry)
        action_layout.addWidget(self.btn_add_entry)
        
        self.btn_update_entry = QPushButton("更新")
        self.btn_update_entry.clicked.connect(self._on_update_entry)
        action_layout.addWidget(self.btn_update_entry)
        
        self.btn_remove_entry = QPushButton("移除")
        self.btn_remove_entry.clicked.connect(self._on_remove_entry)
        action_layout.addWidget(self.btn_remove_entry)
        
        self.btn_clear_form = QPushButton("清空")
        self.btn_clear_form.clicked.connect(self._on_clear_form)
        action_layout.addWidget(self.btn_clear_form)
        
        right_layout.addLayout(action_layout)
        
        layout.addLayout(right_layout)
        
        # 更新数据库列表
        self._update_database_list()
        
        return widget
    
    def _create_import_export_tab(self) -> QWidget:
        """创建导入导出标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 导入区域
        import_group = QGroupBox("导入术语")
        import_layout = QVBoxLayout()
        
        import_btn_layout = QHBoxLayout()
        
        self.btn_import_json = QPushButton("从JSON导入")
        self.btn_import_json.clicked.connect(self._on_import_json)
        import_btn_layout.addWidget(self.btn_import_json)
        
        self.btn_import_csv = QPushButton("从CSV导入")
        self.btn_import_csv.clicked.connect(self._on_import_csv)
        import_btn_layout.addWidget(self.btn_import_csv)
        
        import_layout.addLayout(import_btn_layout)
        
        self.lbl_import_status = QLabel("")
        import_layout.addWidget(self.lbl_import_status)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # 导出区域
        export_group = QGroupBox("导出术语")
        export_layout = QVBoxLayout()
        
        export_btn_layout = QHBoxLayout()
        
        self.btn_export_json = QPushButton("导出为JSON")
        self.btn_export_json.clicked.connect(self._on_export_json)
        export_btn_layout.addWidget(self.btn_export_json)
        
        self.btn_export_csv = QPushButton("导出为CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        export_btn_layout.addWidget(self.btn_export_csv)
        
        export_layout.addLayout(export_btn_layout)
        
        self.lbl_export_status = QLabel("")
        export_layout.addWidget(self.lbl_export_status)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_consistency_tab(self) -> QWidget:
        """创建一致性检查标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 检查选项
        options_group = QGroupBox("检查选项")
        options_layout = QVBoxLayout()
        
        self.check_duplicate = QCheckBox("检查重复术语")
        self.check_duplicate.setChecked(True)
        options_layout.addWidget(self.check_duplicate)
        
        self.check_inconsistent = QCheckBox("检查不一致翻译")
        self.check_inconsistent.setChecked(True)
        options_layout.addWidget(self.check_inconsistent)
        
        self.check_missing = QCheckBox("检查缺失翻译")
        self.check_missing.setChecked(True)
        options_layout.addWidget(self.check_missing)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 检查按钮
        self.btn_check = QPushButton("开始检查")
        self.btn_check.clicked.connect(self._on_check_consistency)
        layout.addWidget(self.btn_check)
        
        # 结果显示
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        layout.addWidget(self.text_results)
        
        return widget
    
    def add_entry(self, entry: TerminologyEntry) -> bool:
        """添加术语条目"""
        if self.current_database is None:
            return False
        
        result = self.current_database.add_entry(entry)
        if result:
            self._update_table()
            self.entry_added.emit(entry.source)
        return result
    
    def remove_entry(self, source: str) -> bool:
        """移除术语条目"""
        if self.current_database is None:
            return False
        
        result = self.current_database.remove_entry(source)
        if result:
            self._update_table()
            self.entry_removed.emit(source)
        return result
    
    def search_entries(self, query: str) -> List[TerminologyEntry]:
        """搜索术语条目"""
        if self.current_database is None:
            return []
        
        # 获取匹配类型
        match_type_text = self.combo_match_type.currentText()
        match_type_map = {
            "模糊匹配": MatchType.FUZZY,
            "精确匹配": MatchType.EXACT,
            "前缀匹配": MatchType.PREFIX,
            "后缀匹配": MatchType.SUFFIX
        }
        match_type = match_type_map.get(match_type_text, MatchType.FUZZY)
        
        return self.current_database.search_entries(query, match_type)
    
    def clear_entries(self):
        """清空所有术语"""
        if self.current_database:
            self.current_database.entries.clear()
            self._update_table()
    
    def export_to_json(self, file_path: str) -> bool:
        """导出为JSON格式"""
        if self.current_database is None:
            return False
        
        try:
            data = {
                "database": self.current_database.name,
                "description": self.current_database.description,
                "entries": [entry.to_dict() for entry in self.current_database.entries],
                "exported_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            return False
    
    def import_from_json(self, file_path: str) -> bool:
        """从JSON格式导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = data.get("entries", [])
            for entry_data in entries:
                entry = TerminologyEntry.from_dict(entry_data)
                self.add_entry(entry)
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
            return False
    
    def _update_database_list(self):
        """更新数据库列表"""
        self.list_databases.clear()
        for db in self.databases:
            item = QListWidgetItem(f"{db.name} ({len(db.entries)})")
            item.setData(Qt.ItemDataRole.UserRole, db)
            self.list_databases.addItem(item)
        
        if self.databases:
            self.list_databases.setCurrentRow(0)
    
    def _update_table(self):
        """更新术语表格"""
        if self.current_database is None:
            return
        
        self.table_entries.setRowCount(len(self.current_database.entries))
        
        for row, entry in enumerate(self.current_database.entries):
            self.table_entries.setItem(row, 0, QTableWidgetItem(entry.source))
            self.table_entries.setItem(row, 1, QTableWidgetItem(entry.target))
            self.table_entries.setItem(row, 2, QTableWidgetItem(entry.category))
            self.table_entries.setItem(row, 3, QTableWidgetItem(entry.notes))
            
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(lambda checked, s=entry.source: self.remove_entry(s))
            self.table_entries.setCellWidget(row, 4, btn_remove)
    
    def _on_database_selected(self, current, previous):
        """数据库选择改变"""
        if current:
            self.current_database = current.data(Qt.ItemDataRole.UserRole)
            self._update_table()
    
    def _on_add_database(self):
        """添加数据库"""
        name = "新建术语库"
        db = TerminologyDatabase(name=name, description="自定义术语库")
        self.databases.append(db)
        self._update_database_list()
    
    def _on_remove_database(self):
        """移除数据库"""
        if len(self.databases) <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个术语库")
            return
        
        current_item = self.list_databases.currentItem()
        if current_item:
            db = current_item.data(Qt.ItemDataRole.UserRole)
            self.databases.remove(db)
            self._update_database_list()
    
    def _on_search(self, text):
        """搜索术语"""
        if not text:
            self._update_table()
            return
        
        results = self.search_entries(text)
        self.table_entries.setRowCount(len(results))
        
        for row, entry in enumerate(results):
            self.table_entries.setItem(row, 0, QTableWidgetItem(entry.source))
            self.table_entries.setItem(row, 1, QTableWidgetItem(entry.target))
            self.table_entries.setItem(row, 2, QTableWidgetItem(entry.category))
            self.table_entries.setItem(row, 3, QTableWidgetItem(entry.notes))
            
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(lambda checked, s=entry.source: self.remove_entry(s))
            self.table_entries.setCellWidget(row, 4, btn_remove)
    
    def _on_add_entry(self):
        """添加术语"""
        source = self.edit_source.text().strip()
        target = self.edit_target.text().strip()
        
        if not source or not target:
            QMessageBox.warning(self, "警告", "源术语和目标术语不能为空")
            return
        
        entry = TerminologyEntry(
            source=source,
            target=target,
            category=self.combo_category.currentText(),
            notes=self.edit_notes.toPlainText(),
            context=self.edit_context.text()
        )
        
        self.add_entry(entry)
        self._on_clear_form()
    
    def _on_update_entry(self):
        """更新术语"""
        selected_rows = self.table_files.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要更新的术语")
            return
        
        row = selected_rows[0].row()
        if row < len(self.current_database.entries):
            entry = self.current_database.entries[row]
            entry.target = self.edit_target.text().strip()
            entry.category = self.combo_category.currentText()
            entry.notes = self.edit_notes.toPlainText()
            entry.context = self.edit_context.text()
            entry.updated_at = datetime.now()
            self._update_table()
    
    def _on_remove_entry(self):
        """移除术语"""
        selected_rows = self.table_entries.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要移除的术语")
            return
        
        row = selected_rows[0].row()
        if row < len(self.current_database.entries):
            source = self.current_database.entries[row].source
            self.remove_entry(source)
    
    def _on_clear_form(self):
        """清空表单"""
        self.edit_source.clear()
        self.edit_target.clear()
        self.combo_category.setCurrentIndex(0)
        self.edit_notes.clear()
        self.edit_context.clear()
    
    def _on_import_json(self):
        """从JSON导入"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择JSON文件", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            if self.import_from_json(file_path):
                self.lbl_import_status.setText(f"导入成功: {file_path}")
                self._update_table()
    
    def _on_import_csv(self):
        """从CSV导入"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        entry = TerminologyEntry(
                            source=row.get('source', ''),
                            target=row.get('target', ''),
                            category=row.get('category', ''),
                            notes=row.get('notes', '')
                        )
                        self.add_entry(entry)
                
                self.lbl_import_status.setText(f"导入成功: {file_path}")
                self._update_table()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def _on_export_json(self):
        """导出为JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出JSON", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            if self.export_to_json(file_path):
                self.lbl_export_status.setText(f"导出成功: {file_path}")
    
    def _on_export_csv(self):
        """导出为CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['source', 'target', 'category', 'notes', 'context'])
                    writer.writeheader()
                    
                    for entry in self.current_database.entries:
                        writer.writerow({
                            'source': entry.source,
                            'target': entry.target,
                            'category': entry.category,
                            'notes': entry.notes,
                            'context': entry.context
                        })
                
                self.lbl_export_status.setText(f"导出成功: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def _on_check_consistency(self):
        """检查一致性"""
        results = []
        
        if self.current_database is None:
            return
        
        # 检查重复术语
        if self.check_duplicate.isChecked():
            seen = {}
            duplicates = []
            for entry in self.current_database.entries:
                if entry.source in seen:
                    duplicates.append(entry.source)
                else:
                    seen[entry.source] = entry
            
            if duplicates:
                results.append(f"发现重复术语: {', '.join(duplicates)}")
            else:
                results.append("未发现重复术语")
        
        # 检查不一致翻译
        if self.check_inconsistent.isChecked():
            inconsistent = []
            for entry in self.current_database.entries:
                # 这里可以添加更复杂的不一致性检查逻辑
                pass
            
            if inconsistent:
                results.append(f"发现不一致翻译: {', '.join(inconsistent)}")
            else:
                results.append("未发现不一致翻译")
        
        # 检查缺失翻译
        if self.check_missing.isChecked():
            missing = []
            for entry in self.current_database.entries:
                if not entry.target:
                    missing.append(entry.source)
            
            if missing:
                results.append(f"发现缺失翻译: {', '.join(missing)}")
            else:
                results.append("未发现缺失翻译")
        
        self.text_results.setText("\n".join(results))
