"""
阶段1 UI组件测试 - 主题系统、快捷键系统、文件拖拽区
测试真实代码实现（使用mock避免UI依赖）
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestThemeManager:
    """主题系统测试 - 测试真实的ThemeManager类"""
    
    @pytest.fixture
    def theme_manager(self):
        """创建ThemeManager实例"""
        from core.theme_manager import ThemeManager
        
        # 创建临时配置目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock配置文件路径
            with patch.object(ThemeManager, 'CONFIG_DIR', tmpdir), \
                 patch.object(ThemeManager, 'CONFIG_FILE', os.path.join(tmpdir, 'theme_config.json')):
                manager = ThemeManager()
                yield manager
    
    def test_theme_manager_initialization(self, theme_manager):
        """测试主题管理器初始化"""
        assert theme_manager.current_theme == "dark"
        assert len(theme_manager.get_themes()) == 3
        assert "dark" in theme_manager.get_themes()
        assert "light" in theme_manager.get_themes()
        assert "office" in theme_manager.get_themes()
    
    def test_switch_theme_success(self, theme_manager):
        """测试主题切换成功"""
        # 切换到亮色主题
        result = theme_manager.switch_theme("light")
        
        assert result == True
        assert theme_manager.current_theme == "light"
        assert theme_manager.current_theme_config.name == "亮色主题"
    
    def test_switch_theme_invalid(self, theme_manager):
        """测试切换无效主题"""
        # 尝试切换到不存在的主题
        result = theme_manager.switch_theme("invalid_theme")
        
        assert result == False
        assert theme_manager.current_theme == "dark"  # 保持原主题
    
    def test_switch_theme_same_theme(self, theme_manager):
        """测试切换相同主题"""
        # 切换到当前主题
        result = theme_manager.switch_theme("dark")
        
        assert result == True
        assert theme_manager.current_theme == "dark"
    
    def test_get_current_theme(self, theme_manager):
        """测试获取当前主题"""
        assert theme_manager.current_theme == "dark"
        
        # 切换主题后测试
        theme_manager.switch_theme("light")
        assert theme_manager.current_theme == "light"
    
    def test_get_theme_config(self, theme_manager):
        """测试获取主题配置"""
        # 获取当前主题配置
        config = theme_manager.get_theme_config()
        assert config.name == "暗色主题"
        assert config.background == "#2b2b2b"
        
        # 获取指定主题配置
        light_config = theme_manager.get_theme_config("light")
        assert light_config.name == "亮色主题"
        assert light_config.background == "#f5f5f5"
    
    def test_get_theme_config_invalid(self, theme_manager):
        """测试获取无效主题配置"""
        config = theme_manager.get_theme_config("invalid_theme")
        assert config is None
    
    def test_save_theme_preference(self, theme_manager):
        """测试保存主题偏好"""
        result = theme_manager.save_theme_preference("light")
        assert result == True
        
        # 验证配置文件已创建
        assert os.path.exists(theme_manager.CONFIG_FILE)
        
        # 验证配置内容
        with open(theme_manager.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        assert config["current_theme"] == "light"
    
    def test_load_theme_preference(self, theme_manager):
        """测试加载主题偏好"""
        # 先保存一个主题
        theme_manager.save_theme_preference("office")
        
        # 创建新的管理器实例来测试加载
        from core.theme_manager import ThemeManager
        with patch.object(ThemeManager, 'CONFIG_DIR', theme_manager.CONFIG_DIR), \
             patch.object(ThemeManager, 'CONFIG_FILE', theme_manager.CONFIG_FILE):
            new_manager = ThemeManager()
            
            # 验证加载的主题
            assert new_manager.current_theme == "office"
    
    def test_theme_persistence(self, theme_manager):
        """测试主题持久化"""
        # 保存主题
        theme_manager.save_theme_preference("light")
        
        # 创建新的管理器实例
        from core.theme_manager import ThemeManager
        with patch.object(ThemeManager, 'CONFIG_DIR', theme_manager.CONFIG_DIR), \
             patch.object(ThemeManager, 'CONFIG_FILE', theme_manager.CONFIG_FILE):
            new_manager = ThemeManager()
            
            # 验证主题是否正确加载
            assert new_manager.current_theme == "light"
    
    def test_register_custom_theme(self, theme_manager):
        """测试注册自定义主题"""
        from core.theme_manager import Theme
        
        # 创建自定义主题
        custom_theme = Theme(
            name="自定义主题",
            background="#123456",
            text="#ffffff"
        )
        
        # 注册主题
        result = theme_manager.register_theme("custom", custom_theme)
        assert result == True
        assert "custom" in theme_manager.get_themes()
    
    def test_unregister_theme(self, theme_manager):
        """测试注销主题"""
        # 先注册一个主题
        from core.theme_manager import Theme
        custom_theme = Theme(name="test", background="#000", text="#fff")
        theme_manager.register_theme("custom", custom_theme)
        
        # 注销主题
        result = theme_manager.unregister_theme("custom")
        assert result == True
        assert "custom" not in theme_manager.get_themes()
    
    def test_unregister_builtin_theme(self, theme_manager):
        """测试注销内置主题（应该失败）"""
        result = theme_manager.unregister_theme("dark")
        assert result == False
        assert "dark" in theme_manager.get_themes()
    
    def test_get_stylesheet(self, theme_manager):
        """测试获取样式表"""
        stylesheet = theme_manager.get_stylesheet()
        
        # 验证样式表包含关键样式
        assert "background-color" in stylesheet
        assert "color" in stylesheet
        assert "border" in stylesheet


class TestShortcutManager:
    """快捷键系统测试 - 测试真实的ShortcutManager类"""
    
    @pytest.fixture
    def shortcut_manager(self):
        """创建ShortcutManager实例"""
        from core.shortcut_manager import ShortcutManager
        
        # 创建临时配置目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock配置文件路径
            with patch.object(ShortcutManager, 'CONFIG_DIR', tmpdir), \
                 patch.object(ShortcutManager, 'CONFIG_FILE', os.path.join(tmpdir, 'shortcut_config.json')):
                manager = ShortcutManager()
                yield manager
    
    def test_shortcut_manager_initialization(self, shortcut_manager):
        """测试快捷键管理器初始化"""
        assert len(shortcut_manager.get_shortcuts()) == 8
        assert shortcut_manager.is_registered == False
        assert "cmd+shift+space" in shortcut_manager.get_shortcuts()
    
    def test_check_shortcut_conflict_no_conflict(self, shortcut_manager):
        """测试检查快捷键冲突 - 无冲突"""
        # 检查无冲突的快捷键
        has_conflict, _ = shortcut_manager.check_shortcut_conflict("cmd+shift+z")
        assert has_conflict == False
    
    def test_check_shortcut_conflict_with_conflict(self, shortcut_manager):
        """测试检查快捷键冲突 - 有冲突"""
        # 检查系统快捷键
        has_conflict, action = shortcut_manager.check_shortcut_conflict("cmd+c")
        assert has_conflict == True
        assert action == "system"
    
    def test_add_shortcut_new(self, shortcut_manager):
        """测试添加新快捷键"""
        from core.shortcut_manager import Shortcut
        
        new_shortcut = Shortcut(
            key="cmd+shift+x",
            name="测试快捷键",
            action="test_action"
        )
        
        result = shortcut_manager.add_shortcut(new_shortcut)
        
        assert result == True
        assert "cmd+shift+x" in shortcut_manager.get_shortcuts()
    
    def test_add_shortcut_existing(self, shortcut_manager):
        """测试添加已存在的快捷键"""
        from core.shortcut_manager import Shortcut
        
        # 尝试添加已存在的快捷键
        existing_shortcut = Shortcut(
            key="cmd+shift+space",
            name="测试",
            action="test"
        )
        
        result = shortcut_manager.add_shortcut(existing_shortcut)
        assert result == False
    
    def test_remove_shortcut_existing(self, shortcut_manager):
        """测试移除存在的快捷键"""
        result = shortcut_manager.remove_shortcut("cmd+shift+space")
        
        assert result == True
        assert "cmd+shift+space" not in shortcut_manager.get_shortcuts()
    
    def test_remove_shortcut_nonexistent(self, shortcut_manager):
        """测试移除不存在的快捷键"""
        result = shortcut_manager.remove_shortcut("cmd+shift+nonexistent")
        
        assert result == False
    
    def test_remove_system_shortcut(self, shortcut_manager):
        """测试移除系统快捷键（应该失败）"""
        result = shortcut_manager.remove_shortcut("cmd+c")
        assert result == False
    
    def test_get_shortcut_list(self, shortcut_manager):
        """测试获取快捷键列表"""
        shortcuts = shortcut_manager.get_shortcut_list()
        
        assert len(shortcuts) == 8
        assert any(s.key == "cmd+shift+space" for s in shortcuts)
    
    def test_trigger_shortcut_existing(self, shortcut_manager):
        """测试触发存在的快捷键"""
        # 注册回调
        callback_called = False
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        shortcut_manager.register_action_callback("toggle_visibility", test_callback)
        
        # 触发快捷键
        result = shortcut_manager.trigger_shortcut("cmd+shift+space")
        
        assert result == True
        assert callback_called == True
    
    def test_trigger_shortcut_nonexistent(self, shortcut_manager):
        """测试触发不存在的快捷键"""
        result = shortcut_manager.trigger_shortcut("cmd+shift+nonexistent")
        
        assert result == False
    
    def test_save_and_load_preference(self, shortcut_manager):
        """测试保存和加载偏好设置"""
        # 添加自定义快捷键
        from core.shortcut_manager import Shortcut
        custom_shortcut = Shortcut(
            key="cmd+shift+y",
            name="自定义",
            action="custom"
        )
        shortcut_manager.add_shortcut(custom_shortcut)
        
        # 保存偏好
        result = shortcut_manager.save_shortcut_preference()
        assert result == True
        
        # 创建新的管理器实例来测试加载
        from core.shortcut_manager import ShortcutManager
        with patch.object(ShortcutManager, 'CONFIG_DIR', shortcut_manager.CONFIG_DIR), \
             patch.object(ShortcutManager, 'CONFIG_FILE', shortcut_manager.CONFIG_FILE):
            new_manager = ShortcutManager()
            
            # 验证加载的快捷键
            assert "cmd+shift+y" in new_manager.get_shortcuts()


class TestFileDropZone:
    """文件拖拽区测试 - 测试真实的FileDropZone类（避免UI依赖）"""
    
    @pytest.fixture
    def sample_files(self):
        """创建示例文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            files = {}
            
            # Word文档
            docx_path = os.path.join(tmpdir, "test.docx")
            with open(docx_path, 'w') as f:
                f.write("test content")
            files["docx"] = docx_path
            
            # PPT文档
            pptx_path = os.path.join(tmpdir, "test.pptx")
            with open(pptx_path, 'w') as f:
                f.write("test content")
            files["pptx"] = pptx_path
            
            # PDF文档
            pdf_path = os.path.join(tmpdir, "test.pdf")
            with open(pdf_path, 'w') as f:
                f.write("test content")
            files["pdf"] = pdf_path
            
            # 文本文件
            txt_path = os.path.join(tmpdir, "test.txt")
            with open(txt_path, 'w') as f:
                f.write("test content")
            files["txt"] = txt_path
            
            # Markdown文件
            md_path = os.path.join(tmpdir, "test.md")
            with open(md_path, 'w') as f:
                f.write("test content")
            files["md"] = md_path
            
            # 不支持的文件
            exe_path = os.path.join(tmpdir, "test.exe")
            with open(exe_path, 'w') as f:
                f.write("test content")
            files["exe"] = exe_path
            
            yield files
    
    @pytest.fixture
    def file_drop_zone(self):
        """创建FileDropZone实例（使用mock避免UI依赖）"""
        from widgets.file_drop_zone import FileDropZone
        
        # 使用mock避免QApplication依赖
        with patch('widgets.file_drop_zone.QFrame.__init__', return_value=None), \
             patch('widgets.file_drop_zone.QFrame.setAcceptDrops'), \
             patch('widgets.file_drop_zone.QFrame.setObjectName'), \
             patch('widgets.file_drop_zone.QFrame.setStyleSheet'):
            zone = FileDropZone.__new__(FileDropZone)
            
            # 手动初始化必要的属性
            zone._accepted_extensions = [
                ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
                ".pdf", ".txt", ".md", ".markdown", ".csv", ".json"
            ]
            zone._current_file_info = None
            zone._is_hovering = False
            zone._on_drag_enter_callback = None
            zone._on_drag_leave_callback = None
            zone._on_drop_callback = None
            
            yield zone
    
    def test_file_drop_zone_initialization(self, file_drop_zone):
        """测试文件拖拽区初始化"""
        assert len(file_drop_zone.get_accepted_extensions()) == 12
        assert ".docx" in file_drop_zone.get_accepted_extensions()
        assert ".pptx" in file_drop_zone.get_accepted_extensions()
        assert ".pdf" in file_drop_zone.get_accepted_extensions()
        assert file_drop_zone._is_hovering == False
    
    def test_is_valid_file_docx(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - docx文件"""
        result = file_drop_zone._is_valid_file(sample_files["docx"])
        assert result == True
    
    def test_is_valid_file_pptx(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - pptx文件"""
        result = file_drop_zone._is_valid_file(sample_files["pptx"])
        assert result == True
    
    def test_is_valid_file_pdf(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - pdf文件"""
        result = file_drop_zone._is_valid_file(sample_files["pdf"])
        assert result == True
    
    def test_is_valid_file_txt(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - txt文件"""
        result = file_drop_zone._is_valid_file(sample_files["txt"])
        assert result == True
    
    def test_is_valid_file_md(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - md文件"""
        result = file_drop_zone._is_valid_file(sample_files["md"])
        assert result == True
    
    def test_is_valid_file_unsupported(self, file_drop_zone, sample_files):
        """测试文件有效性检查 - 不支持的文件"""
        result = file_drop_zone._is_valid_file(sample_files["exe"])
        assert result == False
    
    def test_is_valid_file_nonexistent(self, file_drop_zone):
        """测试文件有效性检查 - 不存在的文件"""
        result = file_drop_zone._is_valid_file("/nonexistent/path/file.docx")
        assert result == False
    
    def test_is_valid_file_empty_path(self, file_drop_zone):
        """测试文件有效性检查 - 空路径"""
        result = file_drop_zone._is_valid_file("")
        assert result == False
    
    def test_get_file_info(self, file_drop_zone, sample_files):
        """测试获取文件信息"""
        file_info = file_drop_zone._get_file_info(sample_files["docx"])
        
        assert file_info is not None
        assert file_info.name == "test.docx"
        assert file_info.path == sample_files["docx"]
        assert file_info.size > 0
        assert file_info.file_type == "Word文档"
        assert file_info.extension == ".docx"
    
    def test_get_file_info_unsupported(self, file_drop_zone, sample_files):
        """测试获取不支持文件的信息"""
        file_info = file_drop_zone._get_file_info(sample_files["exe"])
        assert file_info is None
    
    def test_get_accepted_extensions(self, file_drop_zone):
        """测试获取接受的文件扩展名"""
        extensions = file_drop_zone.get_accepted_extensions()
        
        assert len(extensions) == 12
        assert ".docx" in extensions
        assert ".pptx" in extensions
    
    def test_set_accepted_extensions(self, file_drop_zone):
        """测试设置接受的文件扩展名"""
        new_extensions = [".docx", ".pdf"]
        file_drop_zone.set_accepted_extensions(new_extensions)
        
        assert len(file_drop_zone.get_accepted_extensions()) == 2
        assert ".docx" in file_drop_zone.get_accepted_extensions()
        assert ".pptx" not in file_drop_zone.get_accepted_extensions()


class TestIntegration:
    """集成测试 - 测试组件间交互"""
    
    @pytest.fixture
    def sample_files(self):
        """创建示例文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {}
            
            # Word文档
            docx_path = os.path.join(tmpdir, "test.docx")
            with open(docx_path, 'w') as f:
                f.write("test content")
            files["docx"] = docx_path
            
            # PPT文档
            pptx_path = os.path.join(tmpdir, "test.pptx")
            with open(pptx_path, 'w') as f:
                f.write("test content")
            files["pptx"] = pptx_path
            
            yield files
    
    @pytest.fixture
    def ui_system(self):
        """创建UI系统"""
        from core.theme_manager import ThemeManager
        from core.shortcut_manager import ShortcutManager
        from widgets.file_drop_zone import FileDropZone
        
        # 创建临时配置目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock配置文件路径
            with patch('core.theme_manager.ThemeManager.CONFIG_DIR', tmpdir), \
                 patch('core.theme_manager.ThemeManager.CONFIG_FILE', os.path.join(tmpdir, 'theme_config.json')), \
                 patch('core.shortcut_manager.ShortcutManager.CONFIG_DIR', tmpdir), \
                 patch('core.shortcut_manager.ShortcutManager.CONFIG_FILE', os.path.join(tmpdir, 'shortcut_config.json')):
                
                class UISystem:
                    def __init__(self):
                        self.theme_manager = ThemeManager()
                        self.shortcut_manager = ShortcutManager()
                        self.current_mode = "normal"
                        
                        # 使用mock避免FileDropZone的UI依赖
                        with patch('widgets.file_drop_zone.QFrame.__init__', return_value=None), \
                             patch('widgets.file_drop_zone.QFrame.setAcceptDrops'), \
                             patch('widgets.file_drop_zone.QFrame.setObjectName'), \
                             patch('widgets.file_drop_zone.QFrame.setStyleSheet'):
                            self.file_drop_zone = FileDropZone.__new__(FileDropZone)
                            
                            # 手动初始化必要的属性
                            self.file_drop_zone._accepted_extensions = [
                                ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
                                ".pdf", ".txt", ".md", ".markdown", ".csv", ".json"
                            ]
                            self.file_drop_zone._current_file_info = None
                            self.file_drop_zone._is_hovering = False
                    
                    def initialize(self):
                        """初始化UI系统"""
                        # 不注册快捷键，避免UI依赖
                        return True
                    
                    def switch_to_office_mode(self):
                        """切换到办公模式"""
                        self.theme_manager.switch_theme("office")
                        self.current_mode = "office"
                        return True
                    
                    def handle_file_drop(self, file_path):
                        """处理文件拖拽"""
                        if self.file_drop_zone._is_valid_file(file_path):
                            file_info = self.file_drop_zone._get_file_info(file_path)
                            file_type = file_info.file_type
                            
                            # 根据文件类型切换模式
                            if "Word" in file_type:
                                self.current_mode = "document"
                            elif "PPT" in file_type:
                                self.current_mode = "presentation"
                            elif "PDF" in file_type:
                                self.current_mode = "pdf"
                            else:
                                self.current_mode = "text"
                            
                            return True
                        return False
                
                system = UISystem()
                yield system
    
    def test_ui_system_initialization(self, ui_system):
        """测试UI系统初始化"""
        result = ui_system.initialize()
        
        assert result == True
        assert ui_system.theme_manager.current_theme == "dark"
        assert ui_system.current_mode == "normal"
    
    def test_switch_to_office_mode(self, ui_system):
        """测试切换到办公模式"""
        # 先初始化
        ui_system.initialize()
        
        # 切换到办公模式
        result = ui_system.switch_to_office_mode()
        
        assert result == True
        assert ui_system.theme_manager.current_theme == "office"
        assert ui_system.current_mode == "office"
    
    def test_handle_file_drop_word(self, ui_system, sample_files):
        """测试处理Word文档拖拽"""
        # 先初始化
        ui_system.initialize()
        
        # 处理Word文档
        result = ui_system.handle_file_drop(sample_files["docx"])
        
        assert result == True
        assert ui_system.current_mode == "document"
    
    def test_handle_file_drop_pptx(self, ui_system, sample_files):
        """测试处理PPT文档拖拽"""
        # 先初始化
        ui_system.initialize()
        
        # 处理PPT文档
        result = ui_system.handle_file_drop(sample_files["pptx"])
        
        assert result == True
        assert ui_system.current_mode == "presentation"
    
    def test_handle_file_drop_invalid(self, ui_system):
        """测试处理无效文件拖拽"""
        # 先初始化
        ui_system.initialize()
        
        # 处理无效文件
        result = ui_system.handle_file_drop("/path/to/test.exe")
        
        assert result == False
        assert ui_system.current_mode == "normal"
    
    def test_complete_workflow(self, ui_system, sample_files):
        """测试完整工作流程"""
        # 1. 初始化UI系统
        ui_system.initialize()
        
        # 2. 切换到办公模式
        ui_system.switch_to_office_mode()
        
        # 3. 拖拽Word文档
        ui_system.handle_file_drop(sample_files["docx"])
        
        # 验证最终状态
        assert ui_system.theme_manager.current_theme == "office"
        assert ui_system.current_mode == "document"


class TestEdgeCases:
    """边界情况测试"""
    
    def test_theme_manager_none_theme(self):
        """测试主题管理器空主题"""
        from core.theme_manager import ThemeManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ThemeManager, 'CONFIG_DIR', tmpdir), \
                 patch.object(ThemeManager, 'CONFIG_FILE', os.path.join(tmpdir, 'theme_config.json')):
                manager = ThemeManager()
                result = manager.switch_theme(None)
                assert result == False
    
    def test_shortcut_manager_empty_shortcut(self):
        """测试快捷键管理器空快捷键"""
        from core.shortcut_manager import ShortcutManager, Shortcut
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ShortcutManager, 'CONFIG_DIR', tmpdir), \
                 patch.object(ShortcutManager, 'CONFIG_FILE', os.path.join(tmpdir, 'shortcut_config.json')):
                manager = ShortcutManager()
                empty_shortcut = Shortcut(key="", name="test", action="test")
                result = manager.add_shortcut(empty_shortcut)
                assert result == False
    
    def test_file_drop_zone_no_extension(self):
        """测试文件拖拽区无扩展名文件"""
        from widgets.file_drop_zone import FileDropZone
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建无扩展名文件
            file_path = os.path.join(tmpdir, "file")
            with open(file_path, 'w') as f:
                f.write("test")
            
            # 使用mock避免UI依赖
            with patch('widgets.file_drop_zone.QFrame.__init__', return_value=None), \
                 patch('widgets.file_drop_zone.QFrame.setAcceptDrops'), \
                 patch('widgets.file_drop_zone.QFrame.setObjectName'), \
                 patch('widgets.file_drop_zone.QFrame.setStyleSheet'):
                zone = FileDropZone.__new__(FileDropZone)
                
                # 手动初始化必要的属性
                zone._accepted_extensions = [
                    ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
                    ".pdf", ".txt", ".md", ".markdown", ".csv", ".json"
                ]
                
                result = zone._is_valid_file(file_path)
                assert result == False
    
    def test_file_drop_zone_empty_path(self):
        """测试文件拖拽区空路径"""
        from widgets.file_drop_zone import FileDropZone
        
        # 使用mock避免UI依赖
        with patch('widgets.file_drop_zone.QFrame.__init__', return_value=None), \
             patch('widgets.file_drop_zone.QFrame.setAcceptDrops'), \
             patch('widgets.file_drop_zone.QFrame.setObjectName'), \
             patch('widgets.file_drop_zone.QFrame.setStyleSheet'):
            zone = FileDropZone.__new__(FileDropZone)
            
            # 手动初始化必要的属性
            zone._accepted_extensions = [
                ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
                ".pdf", ".txt", ".md", ".markdown", ".csv", ".json"
            ]
            
            result = zone._is_valid_file("")
            assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])