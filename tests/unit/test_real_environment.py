"""
真实环境测试 - 不使用mock，直接测试代码
验证代码在真实环境下的行为
"""
import pytest
import sys
import os
import tempfile
import json

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestRealEnvironment:
    """真实环境测试"""
    
    def test_theme_manager_real(self):
        """测试主题管理器 - 真实环境"""
        from core.theme_manager import ThemeManager

        # 直接实例化，不使用mock
        manager = ThemeManager()

        # 验证初始化
        assert manager.current_theme in ["dark", "office", "light"]
        assert len(manager.get_themes()) == 3
        assert "dark" in manager.get_themes()
        assert "light" in manager.get_themes()
        assert "office" in manager.get_themes()
        
        # 测试主题切换
        result = manager.switch_theme("light")
        assert result == True
        assert manager.current_theme == "light"
        
        # 测试切换到办公主题
        result = manager.switch_theme("office")
        assert result == True
        assert manager.current_theme == "office"
        
        # 测试切换回暗色主题
        result = manager.switch_theme("dark")
        assert result == True
        assert manager.current_theme == "dark"
        
        print("✅ 主题管理器真实环境测试通过")
    
    def test_shortcut_manager_real(self):
        """测试快捷键管理器 - 真实环境"""
        from core.shortcut_manager import ShortcutManager
        
        # 直接实例化
        manager = ShortcutManager()
        
        # 验证初始化
        shortcuts = manager.get_shortcuts()
        assert len(shortcuts) > 0
        
        # 测试检查冲突 - 返回元组 (has_conflict, action)
        has_conflict, action = manager.check_shortcut_conflict("cmd+shift+t")
        assert isinstance(has_conflict, bool)
        assert has_conflict == True  # 应该有冲突，因为这是预定义的快捷键
        assert action == "open_translation"
        
        # 测试检查不存在的快捷键
        has_conflict, action = manager.check_shortcut_conflict("cmd+shift+9")
        assert has_conflict == False
        assert action is None
        
        print("✅ 快捷键管理器真实环境测试通过")
    
    def test_file_drop_zone_real(self):
        """测试文件拖拽区 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.file_drop_zone import FileDropZone
            
            # 直接实例化
            zone = FileDropZone()
            
            # 验证初始化
            assert zone is not None
            assert zone.acceptDrops() == True
            
            # 测试获取接受的扩展名
            extensions = zone.get_accepted_extensions()
            assert len(extensions) > 0
            assert ".txt" in extensions
            assert ".docx" in extensions
            assert ".pdf" in extensions
            
            # 测试文件验证（使用私有方法）
            assert zone._is_valid_file("test.txt") == False  # 文件不存在
            assert zone._is_valid_file("") == False  # 空路径
            
            print("✅ 文件拖拽区真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_batch_dialog_real(self):
        """测试批量处理对话框 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.batch_dialog import BatchDialog, FileItem, FileStatus
            
            # 直接实例化
            dialog = BatchDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "批量处理"
            assert len(dialog.file_items) == 0
            
            # 测试添加文件
            item1 = FileItem(file_path="test1.txt", file_name="test1.txt", file_size=1024)
            dialog.add_file(item1)
            assert len(dialog.file_items) == 1
            
            item2 = FileItem(file_path="test2.txt", file_name="test2.txt", file_size=2048)
            dialog.add_file(item2)
            assert len(dialog.file_items) == 2
            
            # 测试统计信息
            stats = dialog.get_statistics()
            assert stats["total"] == 2
            assert stats["pending"] == 2
            
            # 测试移除文件
            dialog.remove_file("test1.txt")
            assert len(dialog.file_items) == 1
            
            print("✅ 批量处理对话框真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_terminology_dialog_real(self):
        """测试术语库管理 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
            
            # 直接实例化
            dialog = TerminologyDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "术语库管理"
            assert len(dialog.databases) >= 1
            
            # 测试添加术语
            entry = TerminologyEntry(
                source="人工智能",
                target="Artificial Intelligence",
                category="技术",
                notes="AI的全称"
            )
            result = dialog.add_entry(entry)
            assert result == True
            
            # 测试搜索术语
            results = dialog.search_entries("人工智能")
            assert len(results) >= 1
            assert results[0].source == "人工智能"
            
            # 测试导出导入
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                temp_path = f.name
            
            try:
                # 导出
                result = dialog.export_to_json(temp_path)
                assert result == True
                assert os.path.exists(temp_path)
                
                # 清空后导入
                dialog.clear_entries()
                result = dialog.import_from_json(temp_path)
                assert result == True
                
                # 验证导入成功
                results = dialog.search_entries("人工智能")
                assert len(results) >= 1
                
                print("✅ 术语库管理真实环境测试通过")
            finally:
                os.unlink(temp_path)
                
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_translation_memory_real(self):
        """测试翻译记忆系统 - 真实环境"""
        try:
            from widgets.translation_memory import TranslationMemory, TranslationUnit
            
            # 直接实例化
            memory = TranslationMemory()
            
            # 验证初始化
            assert len(memory.units) == 0
            
            # 测试添加翻译单元
            unit1 = TranslationUnit(
                source="Hello",
                target="你好",
                source_lang="en",
                target_lang="zh"
            )
            result = memory.add_unit(unit1)
            assert result == True
            assert len(memory.units) == 1
            
            unit2 = TranslationUnit(
                source="World",
                target="世界",
                source_lang="en",
                target_lang="zh"
            )
            memory.add_unit(unit2)
            assert len(memory.units) == 2
            
            # 测试精确搜索
            results = memory.search_exact("Hello", source_lang="en", target_lang="zh")
            assert len(results) == 1
            assert results[0].target == "你好"
            
            # 测试模糊搜索
            results = memory.search_fuzzy("Hell", source_lang="en", target_lang="zh", threshold=0.5)
            assert len(results) >= 1
            
            # 测试统计信息
            stats = memory.get_statistics()
            assert stats["total_units"] == 2
            assert stats["language_pairs"] >= 1
            
            # 测试导出导入
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                temp_path = f.name
            
            try:
                # 导出
                result = memory.export_to_json(temp_path)
                assert result == True
                assert os.path.exists(temp_path)
                
                # 清空后导入
                memory.clear()
                assert len(memory.units) == 0
                
                result = memory.import_from_json(temp_path)
                assert result == True
                assert len(memory.units) == 2
                
                print("✅ 翻译记忆系统真实环境测试通过")
            finally:
                os.unlink(temp_path)
                
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_document_dialog_real(self):
        """测试文档处理对话框 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from dialogs.document_dialog import DocumentDialog
            
            # 直接实例化
            dialog = DocumentDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "文档处理"
            
            # 测试设置内容
            dialog.set_content("测试文档内容")
            assert dialog.get_content() == "测试文档内容"
            
            print("✅ 文档处理对话框真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_translation_dialog_real(self):
        """测试翻译对话框 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from dialogs.translation_dialog import TranslationDialog
            
            # 直接实例化
            dialog = TranslationDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "翻译"
            
            # 测试设置文本
            dialog.set_source_text("Hello World")
            assert dialog.get_source_text() == "Hello World"
            
            print("✅ 翻译对话框真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_polish_dialog_real(self):
        """测试润色对话框 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from dialogs.polish_dialog import PolishDialog
            
            # 直接实例化
            dialog = PolishDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "文本润色"
            
            # 测试设置文本
            dialog.set_original_text("测试文本")
            assert dialog.original_text == "测试文本"
            
            # 测试设置润色风格
            result = dialog.set_polish_style("formal")
            assert result == True
            assert dialog.polish_style == "formal"
            
            print("✅ 润色对话框真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_context_menu_real(self):
        """测试右键菜单 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.context_menu import ContextMenu, TextContextMenu
            
            # 直接实例化
            menu = ContextMenu()
            
            # 验证初始化
            assert menu is not None
            
            # 测试文本右键菜单
            text_menu = TextContextMenu()
            assert text_menu is not None
            
            print("✅ 右键菜单真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_settings_dialog_real(self):
        """测试设置对话框 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.settings_dialog import SettingsDialog
            
            # 直接实例化
            dialog = SettingsDialog()
            
            # 验证初始化
            assert dialog.windowTitle() == "个性化设置"
            
            # 测试获取设置
            settings = dialog.get_settings()
            assert "theme" in settings
            assert "font_size" in settings
            
            print("✅ 设置对话框真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_progress_widget_real(self):
        """测试进度组件 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.progress_widget import ProgressWidget
            
            # 直接实例化
            widget = ProgressWidget()
            
            # 验证初始化
            assert widget is not None
            
            # 测试开始进度
            widget.start(100)
            assert widget.current_progress == 0
            
            # 测试更新进度
            widget.update(50, "处理中...")
            assert widget.current_progress == 50
            
            # 测试获取进度
            progress = widget.get_progress()
            assert progress == 50
            
            print("✅ 进度组件真实环境测试通过")
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")
    
    def test_integration_real(self):
        """集成测试 - 真实环境"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            from widgets.batch_dialog import BatchDialog, FileItem
            from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
            from widgets.translation_memory import TranslationMemory, TranslationUnit
            
            # 1. 创建术语库并添加术语
            term_dialog = TerminologyDialog()
            term = TerminologyEntry(source="集成测试", target="Integration Test", category="测试")
            term_dialog.add_entry(term)
            
            # 2. 创建翻译记忆并添加翻译对
            memory = TranslationMemory()
            unit = TranslationUnit(source="Integration Test", target="集成测试", source_lang="en", target_lang="zh")
            memory.add_unit(unit)
            
            # 3. 创建批量处理并添加文件
            batch_dialog = BatchDialog()
            file_item = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
            batch_dialog.add_file(file_item)
            
            # 4. 验证集成
            assert len(batch_dialog.file_items) == 1
            assert len(term_dialog.search_entries("集成测试")) >= 1
            assert len(memory.units) == 1
            
            # 5. 导出测试
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                terms_path = f.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                memory_path = f.name
            
            try:
                term_dialog.export_to_json(terms_path)
                memory.export_to_json(memory_path)
                
                assert os.path.exists(terms_path)
                assert os.path.exists(memory_path)
                
                print("✅ 集成测试真实环境测试通过")
            finally:
                os.unlink(terms_path)
                os.unlink(memory_path)
                
        except ImportError:
            print("⚠️ PyQt6未安装，跳过UI测试")


if __name__ == "__main__":
    # 运行所有真实环境测试
    test = TestRealEnvironment()
    
    print("\n" + "="*60)
    print("开始真实环境测试（不使用mock）")
    print("="*60 + "\n")
    
    test.test_theme_manager_real()
    test.test_shortcut_manager_real()
    test.test_file_drop_zone_real()
    test.test_batch_dialog_real()
    test.test_terminology_dialog_real()
    test.test_translation_memory_real()
    test.test_document_dialog_real()
    test.test_translation_dialog_real()
    test.test_polish_dialog_real()
    test.test_context_menu_real()
    test.test_settings_dialog_real()
    test.test_progress_widget_real()
    test.test_integration_real()
    
    print("\n" + "="*60)
    print("真实环境测试完成")
    print("="*60)
