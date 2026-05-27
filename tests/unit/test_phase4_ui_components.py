"""
阶段4 UI组件测试用例
测试批量处理界面、术语库管理、翻译记忆系统
"""
import pytest
import sys
import os
import tempfile
import json
from unittest.mock import MagicMock, patch, AsyncMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, pyqtSignal

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 创建QApplication实例（UI测试需要）
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ==================== 批量处理测试 ====================

class TestBatchDialog:
    """批量处理对话框测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.batch_dialog import BatchDialog, FileItem, BatchStatus
        
        dialog = BatchDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "批量处理"
        assert len(dialog.file_items) == 0
        assert dialog.batch_status == BatchStatus.IDLE
    
    def test_add_files(self, qapp):
        """测试添加文件"""
        from widgets.batch_dialog import BatchDialog, FileItem
        
        dialog = BatchDialog()
        
        # 添加单个文件
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        dialog.add_file(item)
        assert len(dialog.file_items) == 1
        
        # 添加多个文件
        items = [
            FileItem(file_path="doc1.docx", file_name="doc1.docx", file_size=2048),
            FileItem(file_path="doc2.pdf", file_name="doc2.pdf", file_size=4096)
        ]
        dialog.add_files(items)
        assert len(dialog.file_items) == 3
    
    def test_remove_file(self, qapp):
        """测试移除文件"""
        from widgets.batch_dialog import BatchDialog, FileItem
        
        dialog = BatchDialog()
        
        # 添加文件
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        dialog.add_file(item)
        assert len(dialog.file_items) == 1
        
        # 移除文件
        dialog.remove_file(item.file_path)
        assert len(dialog.file_items) == 0
    
    def test_get_statistics(self, qapp):
        """测试获取统计信息"""
        from widgets.batch_dialog import BatchDialog, FileItem, FileStatus
        
        dialog = BatchDialog()
        
        # 添加文件
        items = [
            FileItem(file_path="test1.txt", file_name="test1.txt", file_size=1024, status=FileStatus.COMPLETED),
            FileItem(file_path="test2.txt", file_name="test2.txt", file_size=2048, status=FileStatus.FAILED),
            FileItem(file_path="test3.txt", file_name="test3.txt", file_size=512, status=FileStatus.PENDING)
        ]
        dialog.add_files(items)
        
        stats = dialog.get_statistics()
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1


class TestFileItem:
    """文件项测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.batch_dialog import FileItem, FileStatus
        
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        assert item.file_path == "test.txt"
        assert item.file_name == "test.txt"
        assert item.file_size == 1024
        assert item.status == FileStatus.PENDING
        assert item.error_message is None
    
    def test_status_update(self, qapp):
        """测试状态更新"""
        from widgets.batch_dialog import FileItem, FileStatus
        
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        
        item.status = FileStatus.PROCESSING
        assert item.status == FileStatus.PROCESSING
        
        item.status = FileStatus.COMPLETED
        assert item.status == FileStatus.COMPLETED
        
        item.error_message = "处理失败"
        assert item.error_message == "处理失败"


# ==================== 术语库管理测试 ====================

class TestTerminologyDialog:
    """术语库管理对话框测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry, TerminologyDatabase
        
        dialog = TerminologyDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "术语库管理"
        assert len(dialog.databases) >= 1  # 至少有默认数据库
    
    def test_add_entry(self, qapp):
        """测试添加术语条目"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        entry = TerminologyEntry(
            source="人工智能",
            target="Artificial Intelligence",
            category="技术",
            notes="AI的全称"
        )
        
        result = dialog.add_entry(entry)
        assert result == True
        
        # 验证添加成功
        entries = dialog.search_entries("人工智能")
        assert len(entries) >= 1
    
    def test_remove_entry(self, qapp):
        """测试移除术语条目"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        entry = TerminologyEntry(
            source="测试术语",
            target="Test Term",
            category="测试"
        )
        
        dialog.add_entry(entry)
        result = dialog.remove_entry(entry.source)
        assert result == True
    
    def test_search_entries(self, qapp):
        """测试搜索术语条目"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        # 添加测试数据
        entries = [
            TerminologyEntry(source="机器学习", target="Machine Learning", category="技术"),
            TerminologyEntry(source="深度学习", target="Deep Learning", category="技术"),
            TerminologyEntry(source="自然语言处理", target="Natural Language Processing", category="技术")
        ]
        
        for entry in entries:
            dialog.add_entry(entry)
        
        # 搜索
        results = dialog.search_entries("学习")
        assert len(results) >= 2
    
    def test_export_import(self, qapp, tmp_path):
        """测试导出导入"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        # 添加测试数据
        entry = TerminologyEntry(source="导出测试", target="Export Test", category="测试")
        dialog.add_entry(entry)
        
        # 导出
        export_path = str(tmp_path / "terms.json")
        result = dialog.export_to_json(export_path)
        assert result == True
        assert os.path.exists(export_path)
        
        # 清空后导入
        dialog.clear_entries()
        result = dialog.import_from_json(export_path)
        assert result == True
        
        # 验证导入成功
        entries = dialog.search_entries("导出测试")
        assert len(entries) >= 1


class TestTerminologyEntry:
    """术语条目测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.terminology_dialog import TerminologyEntry
        
        entry = TerminologyEntry(
            source="源语言",
            target="目标语言",
            category="分类",
            notes="备注"
        )
        
        assert entry.source == "源语言"
        assert entry.target == "目标语言"
        assert entry.category == "分类"
        assert entry.notes == "备注"
    
    def test_to_dict(self, qapp):
        """测试转换为字典"""
        from widgets.terminology_dialog import TerminologyEntry
        
        entry = TerminologyEntry(source="测试", target="Test", category="测试")
        data = entry.to_dict()
        
        assert data["source"] == "测试"
        assert data["target"] == "Test"
        assert data["category"] == "测试"
    
    def test_from_dict(self, qapp):
        """测试从字典创建"""
        from widgets.terminology_dialog import TerminologyEntry
        
        data = {
            "source": "字典",
            "target": "Dictionary",
            "category": "词汇",
            "notes": "测试备注"
        }
        
        entry = TerminologyEntry.from_dict(data)
        assert entry.source == "字典"
        assert entry.target == "Dictionary"
        assert entry.category == "词汇"
        assert entry.notes == "测试备注"


# ==================== 翻译记忆测试 ====================

class TestTranslationMemory:
    """翻译记忆系统测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        assert memory is not None
        assert len(memory.units) == 0
    
    def test_add_unit(self, qapp):
        """测试添加翻译单元"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        unit = TranslationUnit(
            source="Hello",
            target="你好",
            source_lang="en",
            target_lang="zh",
            context="greeting"
        )
        
        result = memory.add_unit(unit)
        assert result == True
        assert len(memory.units) == 1
    
    def test_search_exact(self, qapp):
        """测试精确搜索"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加测试数据
        units = [
            TranslationUnit(source="Hello", target="你好", source_lang="en", target_lang="zh"),
            TranslationUnit(source="World", target="世界", source_lang="en", target_lang="zh"),
            TranslationUnit(source="Goodbye", target="再见", source_lang="en", target_lang="zh")
        ]
        
        for unit in units:
            memory.add_unit(unit)
        
        # 精确搜索
        results = memory.search_exact("Hello", source_lang="en", target_lang="zh")
        assert len(results) == 1
        assert results[0].target == "你好"
    
    def test_search_fuzzy(self, qapp):
        """测试模糊搜索"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加测试数据
        units = [
            TranslationUnit(source="Hello World", target="你好世界", source_lang="en", target_lang="zh"),
            TranslationUnit(source="Hello Everyone", target="大家好", source_lang="en", target_lang="zh"),
            TranslationUnit(source="Good morning", target="早上好", source_lang="en", target_lang="zh")
        ]
        
        for unit in units:
            memory.add_unit(unit)
        
        # 模糊搜索
        results = memory.search_fuzzy("Hello", source_lang="en", target_lang="zh", threshold=0.5)
        assert len(results) >= 2
    
    def test_export_import_tmx(self, qapp, tmp_path):
        """测试TMX格式导出导入"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加测试数据
        unit = TranslationUnit(
            source="TMX Test",
            target="TMX测试",
            source_lang="en",
            target_lang="zh",
            context="test"
        )
        memory.add_unit(unit)
        
        # 导出TMX
        tmx_path = str(tmp_path / "memory.tmx")
        result = memory.export_to_tmx(tmx_path)
        assert result == True
        assert os.path.exists(tmx_path)
        
        # 清空后导入
        memory.clear()
        result = memory.import_from_tmx(tmx_path)
        assert result == True
        
        # 验证导入成功
        assert len(memory.units) >= 1
    
    def test_statistics(self, qapp):
        """测试统计信息"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加测试数据
        units = [
            TranslationUnit(source="Test1", target="测试1", source_lang="en", target_lang="zh"),
            TranslationUnit(source="Test2", target="测试2", source_lang="en", target_lang="zh"),
            TranslationUnit(source="Test3", target="测试3", source_lang="en", target_lang="zh")
        ]
        
        for unit in units:
            memory.add_unit(unit)
        
        stats = memory.get_statistics()
        assert stats["total_units"] == 3
        assert stats["language_pairs"] >= 1


class TestTranslationUnit:
    """翻译单元测试"""
    
    def test_init(self, qapp):
        """测试初始化"""
        from widgets.translation_memory import TranslationUnit
        
        unit = TranslationUnit(
            source="Source",
            target="目标",
            source_lang="en",
            target_lang="zh",
            context="test context"
        )
        
        assert unit.source == "Source"
        assert unit.target == "目标"
        assert unit.source_lang == "en"
        assert unit.target_lang == "zh"
        assert unit.context == "test context"
    
    def test_to_dict(self, qapp):
        """测试转换为字典"""
        from widgets.translation_memory import TranslationUnit
        
        unit = TranslationUnit(source="Test", target="测试", source_lang="en", target_lang="zh")
        data = unit.to_dict()
        
        assert data["source"] == "Test"
        assert data["target"] == "测试"
        assert data["source_lang"] == "en"
        assert data["target_lang"] == "zh"


# ==================== 集成测试 ====================

class TestPhase4Integration:
    """阶段4集成测试"""
    
    def test_batch_dialog_with_terminology(self, qapp):
        """测试批量处理对话框与术语库集成"""
        from widgets.batch_dialog import BatchDialog, FileItem
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        # 创建术语库
        term_dialog = TerminologyDialog()
        entry = TerminologyEntry(source="集成测试", target="Integration Test", category="测试")
        term_dialog.add_entry(entry)
        
        # 创建批量处理对话框
        batch_dialog = BatchDialog()
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        batch_dialog.add_file(item)
        
        # 验证两个组件都能正常工作
        assert len(batch_dialog.file_items) == 1
        assert len(term_dialog.search_entries("集成测试")) >= 1
    
    def test_translation_memory_with_batch(self, qapp):
        """测试翻译记忆与批量处理集成"""
        from widgets.batch_dialog import BatchDialog, FileItem
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        # 创建翻译记忆
        memory = TranslationMemory()
        unit = TranslationUnit(source="Batch Test", target="批量测试", source_lang="en", target_lang="zh")
        memory.add_unit(unit)
        
        # 创建批量处理对话框
        batch_dialog = BatchDialog()
        item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        batch_dialog.add_file(item)
        
        # 验证集成
        assert len(memory.units) == 1
        assert len(batch_dialog.file_items) == 1
    
    def test_full_workflow(self, qapp, tmp_path):
        """测试完整工作流"""
        from widgets.batch_dialog import BatchDialog, FileItem
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        # 1. 创建术语库并添加术语
        term_dialog = TerminologyDialog()
        term = TerminologyEntry(source="工作流", target="Workflow", category="技术")
        term_dialog.add_entry(term)
        
        # 2. 创建翻译记忆并添加翻译对
        memory = TranslationMemory()
        unit = TranslationUnit(source="Workflow Test", target="工作流测试", source_lang="en", target_lang="zh")
        memory.add_unit(unit)
        
        # 3. 创建批量处理并添加文件
        batch_dialog = BatchDialog()
        file_item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        batch_dialog.add_file(file_item)
        
        # 4. 导出术语库
        terms_path = str(tmp_path / "terms.json")
        term_dialog.export_to_json(terms_path)
        
        # 5. 导出翻译记忆
        tmx_path = str(tmp_path / "memory.tmx")
        memory.export_to_tmx(tmx_path)
        
        # 验证所有操作成功
        assert os.path.exists(terms_path)
        assert os.path.exists(tmx_path)
        assert len(batch_dialog.file_items) == 1


# ==================== 边界情况测试 ====================

class TestPhase4EdgeCases:
    """阶段4边界情况测试"""
    
    def test_empty_batch(self, qapp):
        """测试空批量处理"""
        from widgets.batch_dialog import BatchDialog
        
        dialog = BatchDialog()
        stats = dialog.get_statistics()
        
        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
    
    def test_duplicate_terminology(self, qapp):
        """测试重复术语"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        entry1 = TerminologyEntry(source="重复", target="Duplicate", category="测试")
        entry2 = TerminologyEntry(source="重复", target="Duplicate Again", category="测试")
        
        dialog.add_entry(entry1)
        result = dialog.add_entry(entry2)  # 应该更新而非重复添加
        
        entries = dialog.search_entries("重复")
        assert len(entries) == 1  # 只有一条记录
    
    def test_large_translation_memory(self, qapp):
        """测试大量翻译记忆"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加大量翻译单元
        for i in range(100):
            unit = TranslationUnit(
                source=f"Source {i}",
                target=f"目标 {i}",
                source_lang="en",
                target_lang="zh"
            )
            memory.add_unit(unit)
        
        assert len(memory.units) == 100
        
        # 搜索测试
        results = memory.search_exact("Source 50", source_lang="en", target_lang="zh")
        assert len(results) == 1
    
    def test_invalid_file_batch(self, qapp):
        """测试无效文件批量处理"""
        from widgets.batch_dialog import BatchDialog, FileItem, FileStatus
        
        dialog = BatchDialog()
        
        # 添加无效文件
        item = FileItem(file_path="", file_name="", file_size=0, status=FileStatus.FAILED)
        dialog.add_file(item)
        
        stats = dialog.get_statistics()
        assert stats["failed"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
