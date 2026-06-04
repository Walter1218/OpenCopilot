"""
翻译记忆系统
支持翻译对存储、搜索、导入导出
"""
import os
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from difflib import SequenceMatcher

from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


@dataclass
class TranslationUnit:
    """翻译单元"""
    source: str
    target: str
    source_lang: str
    target_lang: str
    context: str = ""
    domain: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    quality_score: float = 0.0
    
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
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "context": self.context,
            "domain": self.domain,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count,
            "quality_score": self.quality_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TranslationUnit':
        """从字典创建"""
        unit = cls(
            source=data["source"],
            target=data["target"],
            source_lang=data["source_lang"],
            target_lang=data["target_lang"],
            context=data.get("context", ""),
            domain=data.get("domain", ""),
            usage_count=data.get("usage_count", 0),
            quality_score=data.get("quality_score", 0.0)
        )
        if data.get("created_at"):
            unit.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            unit.updated_at = datetime.fromisoformat(data["updated_at"])
        return unit
    
    def get_language_pair(self) -> str:
        """获取语言对"""
        return f"{self.source_lang}-{self.target_lang}"


class TranslationMemory:
    """翻译记忆系统"""
    
    def __init__(self):
        """初始化"""
        self.units: List[TranslationUnit] = []
        self._index: Dict[str, List[int]] = {}  # 语言对索引
    
    def add_unit(self, unit: TranslationUnit) -> bool:
        """添加翻译单元"""
        # 检查是否已存在
        for i, existing in enumerate(self.units):
            if (existing.source == unit.source and 
                existing.source_lang == unit.source_lang and
                existing.target_lang == unit.target_lang):
                # 更新现有单元
                existing.target = unit.target
                existing.context = unit.context
                existing.domain = unit.domain
                existing.updated_at = datetime.now()
                return True
        
        # 添加新单元
        self.units.append(unit)
        
        # 更新索引
        pair = unit.get_language_pair()
        if pair not in self._index:
            self._index[pair] = []
        self._index[pair].append(len(self.units) - 1)
        
        return True
    
    def remove_unit(self, source: str, source_lang: str, target_lang: str) -> bool:
        """移除翻译单元"""
        for i, unit in enumerate(self.units):
            if (unit.source == source and 
                unit.source_lang == source_lang and
                unit.target_lang == target_lang):
                self.units.pop(i)
                self._rebuild_index()
                return True
        return False
    
    def clear(self):
        """清空所有翻译单元"""
        self.units.clear()
        self._index.clear()
    
    def search_exact(self, source: str, source_lang: str = None, 
                    target_lang: str = None) -> List[TranslationUnit]:
        """精确搜索"""
        results = []
        
        for unit in self.units:
            if unit.source != source:
                continue
            
            if source_lang and unit.source_lang != source_lang:
                continue
            
            if target_lang and unit.target_lang != target_lang:
                continue
            
            unit.usage_count += 1
            results.append(unit)
        
        return results
    
    def search_fuzzy(self, source: str, source_lang: str = None,
                    target_lang: str = None, threshold: float = 0.5) -> List[Tuple[TranslationUnit, float]]:
        """模糊搜索"""
        results = []
        
        for unit in self.units:
            if source_lang and unit.source_lang != source_lang:
                continue
            
            if target_lang and unit.target_lang != target_lang:
                continue
            
            # 计算相似度
            similarity = SequenceMatcher(None, source.lower(), unit.source.lower()).ratio()
            
            if similarity >= threshold:
                unit.usage_count += 1
                results.append((unit, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def search_by_context(self, context: str, source_lang: str = None,
                         target_lang: str = None) -> List[TranslationUnit]:
        """按上下文搜索"""
        results = []
        context_lower = context.lower()
        
        for unit in self.units:
            if source_lang and unit.source_lang != source_lang:
                continue
            
            if target_lang and unit.target_lang != target_lang:
                continue
            
            if context_lower in unit.context.lower():
                unit.usage_count += 1
                results.append(unit)
        
        return results
    
    def search_by_domain(self, domain: str, source_lang: str = None,
                        target_lang: str = None) -> List[TranslationUnit]:
        """按领域搜索"""
        results = []
        domain_lower = domain.lower()
        
        for unit in self.units:
            if source_lang and unit.source_lang != source_lang:
                continue
            
            if target_lang and unit.target_lang != target_lang:
                continue
            
            if domain_lower in unit.domain.lower():
                unit.usage_count += 1
                results.append(unit)
        
        return results
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        if not self.units:
            return {
                "total_units": 0,
                "language_pairs": 0,
                "domains": [],
                "avg_quality_score": 0.0,
                "most_used": None
            }
        
        # 语言对统计
        language_pairs = set()
        domains = set()
        total_quality = 0.0
        most_used = None
        
        for unit in self.units:
            language_pairs.add(unit.get_language_pair())
            if unit.domain:
                domains.add(unit.domain)
            total_quality += unit.quality_score
            
            if most_used is None or unit.usage_count > most_used.usage_count:
                most_used = unit
        
        return {
            "total_units": len(self.units),
            "language_pairs": len(language_pairs),
            "domains": list(domains),
            "avg_quality_score": total_quality / len(self.units) if self.units else 0.0,
            "most_used": most_used.to_dict() if most_used else None
        }
    
    def export_to_json(self, file_path: str) -> bool:
        """导出为JSON格式"""
        try:
            data = {
                "version": "1.0",
                "units": [unit.to_dict() for unit in self.units],
                "exported_at": datetime.now().isoformat(),
                "statistics": self.get_statistics()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            return False
    
    def import_from_json(self, file_path: str) -> bool:
        """从JSON格式导入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            units_data = data.get("units", [])
            for unit_data in units_data:
                unit = TranslationUnit.from_dict(unit_data)
                self.add_unit(unit)
            
            return True
        except Exception as e:
            return False
    
    def export_to_tmx(self, file_path: str) -> bool:
        """导出为TMX格式"""
        try:
            # 创建TMX XML
            tmx = ET.Element("tmx")
            tmx.set("version", "1.4")
            
            header = ET.SubElement(tmx, "header")
            header.set("creationtool", "OpenCopilot")
            header.set("creationtoolversion", "1.0")
            header.set("datatype", "plaintext")
            header.set("segtype", "sentence")
            header.set("adminlang", "en")
            header.set("srclang", "*all*")
            
            body = ET.SubElement(tmx, "body")
            
            for unit in self.units:
                tu = ET.SubElement(body, "tu")
                
                # 源语言
                tuv_source = ET.SubElement(tu, "tuv")
                tuv_source.set("xml:lang", unit.source_lang)
                seg_source = ET.SubElement(tuv_source, "seg")
                seg_source.text = unit.source
                
                # 目标语言
                tuv_target = ET.SubElement(tu, "tuv")
                tuv_target.set("xml:lang", unit.target_lang)
                seg_target = ET.SubElement(tuv_target, "seg")
                seg_target.text = unit.target
                
                # 添加上下文和领域信息
                if unit.context:
                    note = ET.SubElement(tu, "note")
                    note.text = f"Context: {unit.context}"
                
                if unit.domain:
                    note = ET.SubElement(tu, "note")
                    note.text = f"Domain: {unit.domain}"
            
            # 写入文件
            tree = ET.ElementTree(tmx)
            ET.indent(tree, space="  ")
            tree.write(file_path, encoding="utf-8", xml_declaration=True)
            
            return True
        except Exception as e:
            return False
    
    def import_from_tmx(self, file_path: str) -> bool:
        """从TMX格式导入"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 查找body元素
            body = root.find("body")
            if body is None:
                return False
            
            # 解析翻译单元
            for tu in body.findall("tu"):
                tuvs = tu.findall("tuv")
                if len(tuvs) < 2:
                    continue
                
                # 获取源语言和目标语言
                source_lang = tuvs[0].get("xml:lang", "")
                target_lang = tuvs[1].get("xml:lang", "")
                
                source_text = tuvs[0].find("seg").text or ""
                target_text = tuvs[1].find("seg").text or ""
                
                # 获取上下文和领域信息
                context = ""
                domain = ""
                for note in tu.findall("note"):
                    note_text = note.text or ""
                    if note_text.startswith("Context:"):
                        context = note_text[8:].strip()
                    elif note_text.startswith("Domain:"):
                        domain = note_text[7:].strip()
                
                # 创建翻译单元
                unit = TranslationUnit(
                    source=source_text,
                    target=target_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    context=context,
                    domain=domain
                )
                
                self.add_unit(unit)
            
            return True
        except Exception as e:
            return False
    
    def _rebuild_index(self):
        """重建索引"""
        self._index.clear()
        for i, unit in enumerate(self.units):
            pair = unit.get_language_pair()
            if pair not in self._index:
                self._index[pair] = []
            self._index[pair].append(i)


class TranslationMemoryDialog(QDialog):
    """翻译记忆管理对话框"""
    
    # 信号
    unit_added = pyqtSignal(str)  # 翻译单元添加信号
    unit_removed = pyqtSignal(str)  # 翻译单元移除信号
    
    def __init__(self, parent=None):
        """初始化"""
        super().__init__(parent)
        self.setWindowTitle("翻译记忆管理")
        self.setMinimumSize(900, 600)
        
        # 数据
        self.memory = TranslationMemory()
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.btn_import = QPushButton("导入")
        self.btn_import.clicked.connect(self._on_import)
        toolbar_layout.addWidget(self.btn_import)
        
        self.btn_export = QPushButton("导出")
        self.btn_export.clicked.connect(self._on_export)
        toolbar_layout.addWidget(self.btn_export)
        
        toolbar_layout.addStretch()
        
        # 搜索选项
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("搜索翻译记忆...")
        self.edit_search.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self.edit_search)
        
        self.combo_search_type = QComboBox()
        self.combo_search_type.addItems(["精确匹配", "模糊匹配", "按上下文", "按领域"])
        toolbar_layout.addWidget(self.combo_search_type)
        
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.0, 1.0)
        self.spin_threshold.setValue(0.5)
        self.spin_threshold.setSingleStep(0.1)
        self.spin_threshold.setPrefix("阈值: ")
        toolbar_layout.addWidget(self.spin_threshold)
        
        layout.addLayout(toolbar_layout)
        
        # 翻译单元表格
        self.table_units = QTableWidget()
        self.table_units.setColumnCount(7)
        self.table_units.setHorizontalHeaderLabels([
            "源文本", "目标文本", "源语言", "目标语言", "上下文", "领域", "操作"
        ])
        self.table_units.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_units.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_units)
        
        # 编辑区域
        edit_group = QGroupBox("编辑翻译单元")
        edit_layout = QFormLayout()
        
        self.edit_source = QLineEdit()
        edit_layout.addRow("源文本:", self.edit_source)
        
        self.edit_target = QLineEdit()
        edit_layout.addRow("目标文本:", self.edit_target)
        
        self.combo_source_lang = QComboBox()
        self.combo_source_lang.addItems(["en", "zh", "ja", "ko", "fr", "de", "es", "ru"])
        edit_layout.addRow("源语言:", self.combo_source_lang)
        
        self.combo_target_lang = QComboBox()
        self.combo_target_lang.addItems(["zh", "en", "ja", "ko", "fr", "de", "es", "ru"])
        self.combo_target_lang.setCurrentIndex(1)
        edit_layout.addRow("目标语言:", self.combo_target_lang)
        
        self.edit_context = QLineEdit()
        edit_layout.addRow("上下文:", self.edit_context)
        
        self.edit_domain = QLineEdit()
        edit_layout.addRow("领域:", self.edit_domain)
        
        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("添加")
        self.btn_add.clicked.connect(self._on_add)
        action_layout.addWidget(self.btn_add)
        
        self.btn_update = QPushButton("更新")
        self.btn_update.clicked.connect(self._on_update)
        action_layout.addWidget(self.btn_update)
        
        self.btn_remove = QPushButton("移除")
        self.btn_remove.clicked.connect(self._on_remove)
        action_layout.addWidget(self.btn_remove)
        
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._on_clear)
        action_layout.addWidget(self.btn_clear)
        
        action_layout.addStretch()
        
        # 统计信息
        self.lbl_statistics = QLabel("总计: 0 个翻译单元")
        action_layout.addWidget(self.lbl_statistics)
        
        layout.addLayout(action_layout)
        
        # 初始化数据
        self._update_table()
    
    def add_unit(self, unit: TranslationUnit):
        """添加翻译单元"""
        self.memory.add_unit(unit)
        self._update_table()
        self.unit_added.emit(unit.source)
    
    def remove_unit(self, source: str, source_lang: str, target_lang: str):
        """移除翻译单元"""
        self.memory.remove_unit(source, source_lang, target_lang)
        self._update_table()
        self.unit_removed.emit(source)
    
    def _update_table(self):
        """更新表格显示"""
        self.table_units.setRowCount(len(self.memory.units))
        
        for row, unit in enumerate(self.memory.units):
            self.table_units.setItem(row, 0, QTableWidgetItem(unit.source))
            self.table_units.setItem(row, 1, QTableWidgetItem(unit.target))
            self.table_units.setItem(row, 2, QTableWidgetItem(unit.source_lang))
            self.table_units.setItem(row, 3, QTableWidgetItem(unit.target_lang))
            self.table_units.setItem(row, 4, QTableWidgetItem(unit.context))
            self.table_units.setItem(row, 5, QTableWidgetItem(unit.domain))
            
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(
                lambda checked, s=unit.source, sl=unit.source_lang, tl=unit.target_lang: 
                self.remove_unit(s, sl, tl)
            )
            self.table_units.setCellWidget(row, 6, btn_remove)
        
        # 更新统计信息
        stats = self.memory.get_statistics()
        self.lbl_statistics.setText(f"总计: {stats['total_units']} 个翻译单元")
    
    def _on_search(self, text):
        """搜索翻译记忆"""
        if not text:
            self._update_table()
            return
        
        search_type = self.combo_search_type.currentText()
        results = []
        
        if search_type == "精确匹配":
            results = self.memory.search_exact(text)
        elif search_type == "模糊匹配":
            threshold = self.spin_threshold.value()
            fuzzy_results = self.memory.search_fuzzy(text, threshold=threshold)
            results = [unit for unit, score in fuzzy_results]
        elif search_type == "按上下文":
            results = self.memory.search_by_context(text)
        elif search_type == "按领域":
            results = self.memory.search_by_domain(text)
        
        self.table_units.setRowCount(len(results))
        
        for row, unit in enumerate(results):
            self.table_units.setItem(row, 0, QTableWidgetItem(unit.source))
            self.table_units.setItem(row, 1, QTableWidgetItem(unit.target))
            self.table_units.setItem(row, 2, QTableWidgetItem(unit.source_lang))
            self.table_units.setItem(row, 3, QTableWidgetItem(unit.target_lang))
            self.table_units.setItem(row, 4, QTableWidgetItem(unit.context))
            self.table_units.setItem(row, 5, QTableWidgetItem(unit.domain))
            
            btn_remove = QPushButton("移除")
            btn_remove.clicked.connect(
                lambda checked, s=unit.source, sl=unit.source_lang, tl=unit.target_lang: 
                self.remove_unit(s, sl, tl)
            )
            self.table_units.setCellWidget(row, 6, btn_remove)
    
    def _on_add(self):
        """添加翻译单元"""
        source = self.edit_source.text().strip()
        target = self.edit_target.text().strip()
        
        if not source or not target:
            QMessageBox.warning(self, "警告", "源文本和目标文本不能为空")
            return
        
        unit = TranslationUnit(
            source=source,
            target=target,
            source_lang=self.combo_source_lang.currentText(),
            target_lang=self.combo_target_lang.currentText(),
            context=self.edit_context.text(),
            domain=self.edit_domain.text()
        )
        
        self.add_unit(unit)
        self._on_clear_form()
    
    def _on_update(self):
        """更新翻译单元"""
        selected_rows = self.table_units.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要更新的翻译单元")
            return
        
        row = selected_rows[0].row()
        if row < len(self.memory.units):
            unit = self.memory.units[row]
            unit.target = self.edit_target.text().strip()
            unit.context = self.edit_context.text()
            unit.domain = self.edit_domain.text()
            unit.updated_at = datetime.now()
            self._update_table()
    
    def _on_remove(self):
        """移除翻译单元"""
        selected_rows = self.table_units.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要移除的翻译单元")
            return
        
        row = selected_rows[0].row()
        if row < len(self.memory.units):
            unit = self.memory.units[row]
            self.remove_unit(unit.source, unit.source_lang, unit.target_lang)
    
    def _on_clear(self):
        """清空所有翻译单元"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有翻译记忆吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.memory.clear()
            self._update_table()
    
    def _on_clear_form(self):
        """清空表单"""
        self.edit_source.clear()
        self.edit_target.clear()
        self.combo_source_lang.setCurrentIndex(0)
        self.combo_target_lang.setCurrentIndex(0)
        self.edit_context.clear()
        self.edit_domain.clear()
    
    def _on_import(self):
        """导入翻译记忆"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入翻译记忆", "", 
            "JSON文件 (*.json);;TMX文件 (*.tmx);;所有文件 (*)"
        )
        
        if file_path:
            if file_path.endswith('.json'):
                success = self.memory.import_from_json(file_path)
            elif file_path.endswith('.tmx'):
                success = self.memory.import_from_tmx(file_path)
            else:
                QMessageBox.warning(self, "警告", "不支持的文件格式")
                return
            
            if success:
                QMessageBox.information(self, "成功", "导入成功")
                self._update_table()
            else:
                QMessageBox.critical(self, "错误", "导入失败")
    
    def _on_export(self):
        """导出翻译记忆"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出翻译记忆", "", 
            "JSON文件 (*.json);;TMX文件 (*.tmx)"
        )
        
        if file_path:
            if file_path.endswith('.json'):
                success = self.memory.export_to_json(file_path)
            elif file_path.endswith('.tmx'):
                success = self.memory.export_to_tmx(file_path)
            else:
                # 默认导出为JSON
                if not file_path.endswith('.json'):
                    file_path += '.json'
                success = self.memory.export_to_json(file_path)
            
            if success:
                QMessageBox.information(self, "成功", f"导出成功: {file_path}")
            else:
                QMessageBox.critical(self, "错误", "导出失败")
