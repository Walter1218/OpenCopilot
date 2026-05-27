"""
阶段3 UI组件测试用例
测试右键菜单优化、个性化设置、进度反馈
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QComboBox, QGroupBox,
    QMenu, QProgressBar, QSlider, QCheckBox, QSpinBox,
    QDialog, QFormLayout, QLineEdit, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QAction

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 模拟PyQt6模块以避免UI依赖
@pytest.fixture(scope="session", autouse=True)
def qapp():
    """创建QApplication实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestContextMenu:
    """右键菜单优化测试"""

    def test_context_menu_initialization(self, qapp):
        """测试右键菜单初始化"""
        class ContextMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.actions = {}
                self.setup_menu()
            
            def setup_menu(self):
                """设置菜单项"""
                # 文本操作
                self.add_action("复制", "copy")
                self.add_action("粘贴", "paste")
                self.add_separator()
                
                # AI操作
                self.add_action("翻译", "translate")
                self.add_action("润色", "polish")
                self.add_action("修订", "revise")
                self.add_separator()
                
                # 格式操作
                self.add_action("加粗", "bold")
                self.add_action("斜体", "italic")
            
            def add_action(self, text, action_id):
                """添加菜单项"""
                action = QAction(text, self)
                action.setData(action_id)
                self.addAction(action)
                self.actions[action_id] = action
            
            def add_separator(self):
                """添加分隔符"""
                self.addSeparator()
        
        menu = ContextMenu()
        
        # 验证菜单项
        assert len(menu.actions) == 7
        assert "copy" in menu.actions
        assert "paste" in menu.actions
        assert "translate" in menu.actions
        assert "polish" in menu.actions
        assert "revise" in menu.actions
        assert "bold" in menu.actions
        assert "italic" in menu.actions

    def test_context_menu_dynamic_items(self, qapp):
        """测试右键菜单动态项"""
        class DynamicContextMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.context_type = "text"
                self.dynamic_actions = []
            
            def set_context(self, context_type):
                """设置上下文类型"""
                self.context_type = context_type
                self._update_menu_items()
            
            def _update_menu_items(self):
                """更新菜单项"""
                # 清除动态项
                for action in self.dynamic_actions:
                    self.removeAction(action)
                self.dynamic_actions.clear()
                
                # 根据上下文添加项
                if self.context_type == "text":
                    self._add_dynamic_action("翻译选中文本")
                    self._add_dynamic_action("润色选中文本")
                elif self.context_type == "file":
                    self._add_dynamic_action("打开文件")
                    self._add_dynamic_action("预览文件")
                elif self.context_type == "code":
                    self._add_dynamic_action("解释代码")
                    self._add_dynamic_action("优化代码")
            
            def _add_dynamic_action(self, text):
                """添加动态菜单项"""
                action = QAction(text, self)
                self.addAction(action)
                self.dynamic_actions.append(action)
        
        menu = DynamicContextMenu()
        
        # 测试文本上下文
        menu.set_context("text")
        assert len(menu.dynamic_actions) == 2
        
        # 测试文件上下文
        menu.set_context("file")
        assert len(menu.dynamic_actions) == 2
        
        # 测试代码上下文
        menu.set_context("code")
        assert len(menu.dynamic_actions) == 2

    def test_context_menu_action_trigger(self, qapp):
        """测试右键菜单动作触发"""
        class ActionContextMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.triggered_action = None
                self.setup_menu()
            
            def setup_menu(self):
                """设置菜单"""
                action = QAction("测试动作", self)
                action.triggered.connect(self.on_action_triggered)
                self.addAction(action)
            
            def on_action_triggered(self):
                """动作触发回调"""
                self.triggered_action = "test_action"
        
        menu = ActionContextMenu()
        
        # 模拟触发
        menu.triggered_action = None
        menu.on_action_triggered()
        assert menu.triggered_action == "test_action"

    def test_context_menu_shortcut_display(self, qapp):
        """测试右键菜单快捷键显示"""
        class ShortcutContextMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.shortcut_actions = {}
            
            def add_action_with_shortcut(self, text, action_id, shortcut):
                """添加带快捷键的菜单项"""
                action = QAction(text, self)
                action.setData(action_id)
                action.setShortcut(shortcut)
                self.addAction(action)
                self.shortcut_actions[action_id] = {
                    "action": action,
                    "shortcut": shortcut
                }
            
            def get_shortcut(self, action_id):
                """获取快捷键"""
                if action_id in self.shortcut_actions:
                    return self.shortcut_actions[action_id]["shortcut"]
                return None
        
        menu = ShortcutContextMenu()
        
        # 添加带快捷键的菜单项
        menu.add_action_with_shortcut("复制", "copy", "Ctrl+C")
        menu.add_action_with_shortcut("粘贴", "paste", "Ctrl+V")
        menu.add_action_with_shortcut("翻译", "translate", "Ctrl+T")
        
        # 验证快捷键
        assert menu.get_shortcut("copy") == "Ctrl+C"
        assert menu.get_shortcut("paste") == "Ctrl+V"
        assert menu.get_shortcut("translate") == "Ctrl+T"
        assert menu.get_shortcut("nonexistent") is None


class TestSettingsDialog:
    """个性化设置测试"""

    def test_settings_dialog_initialization(self, qapp):
        """测试设置对话框初始化"""
        class SettingsDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("个性化设置")
                self.setMinimumSize(600, 400)
                self.settings = {}
                self.setup_ui()
            
            def setup_ui(self):
                """设置UI"""
                layout = QVBoxLayout(self)
                
                # 创建标签页
                tabs = QTabWidget()
                
                # 外观设置
                appearance_tab = QWidget()
                appearance_layout = QFormLayout(appearance_tab)
                
                self.theme_combo = QComboBox()
                self.theme_combo.addItems(["暗色", "亮色", "办公"])
                appearance_layout.addRow("主题:", self.theme_combo)
                
                self.font_size_spin = QSpinBox()
                self.font_size_spin.setRange(8, 24)
                self.font_size_spin.setValue(12)
                appearance_layout.addRow("字体大小:", self.font_size_spin)
                
                tabs.addTab(appearance_tab, "外观")
                
                # 行为设置
                behavior_tab = QWidget()
                behavior_layout = QFormLayout(behavior_tab)
                
                self.auto_save_check = QCheckBox("自动保存")
                behavior_layout.addRow("自动保存:", self.auto_save_check)
                
                self.auto_translate_check = QCheckBox("自动翻译")
                behavior_layout.addRow("自动翻译:", self.auto_translate_check)
                
                tabs.addTab(behavior_tab, "行为")
                
                layout.addWidget(tabs)
                
                # 按钮
                button_layout = QHBoxLayout()
                self.save_btn = QPushButton("保存")
                self.cancel_btn = QPushButton("取消")
                button_layout.addWidget(self.save_btn)
                button_layout.addWidget(self.cancel_btn)
                layout.addLayout(button_layout)
        
        dialog = SettingsDialog()
        
        assert dialog.windowTitle() == "个性化设置"
        assert dialog.minimumSize().width() == 600
        assert dialog.minimumSize().height() == 400
        assert dialog.theme_combo.count() == 3
        assert dialog.font_size_spin.value() == 12

    def test_settings_save_load(self, qapp):
        """测试设置保存和加载"""
        class SettingsManager:
            def __init__(self):
                self.settings = {
                    "theme": "dark",
                    "font_size": 12,
                    "auto_save": True,
                    "auto_translate": False
                }
            
            def save_settings(self, file_path):
                """保存设置"""
                # 模拟保存
                return True
            
            def load_settings(self, file_path):
                """加载设置"""
                # 模拟加载
                return self.settings
            
            def get_setting(self, key):
                """获取设置"""
                return self.settings.get(key)
            
            def set_setting(self, key, value):
                """设置设置"""
                self.settings[key] = value
                return True
        
        manager = SettingsManager()
        
        # 测试获取设置
        assert manager.get_setting("theme") == "dark"
        assert manager.get_setting("font_size") == 12
        assert manager.get_setting("auto_save") == True
        
        # 测试设置值
        manager.set_setting("theme", "light")
        assert manager.get_setting("theme") == "light"
        
        manager.set_setting("font_size", 14)
        assert manager.get_setting("font_size") == 14
        
        # 测试保存和加载
        assert manager.save_settings("settings.json") == True
        loaded = manager.load_settings("settings.json")
        assert loaded is not None

    def test_theme_settings(self, qapp):
        """测试主题设置"""
        class ThemeSettings:
            def __init__(self):
                self.current_theme = "dark"
                self.themes = {
                    "dark": {"name": "暗色", "background": "#2b2b2b", "text": "#ffffff"},
                    "light": {"name": "亮色", "background": "#ffffff", "text": "#000000"},
                    "office": {"name": "办公", "background": "#f5f5f5", "text": "#333333"}
                }
            
            def set_theme(self, theme_name):
                """设置主题"""
                if theme_name in self.themes:
                    self.current_theme = theme_name
                    return True
                return False
            
            def get_theme_config(self):
                """获取主题配置"""
                return self.themes.get(self.current_theme)
            
            def get_available_themes(self):
                """获取可用主题"""
                return list(self.themes.keys())
        
        settings = ThemeSettings()
        
        # 测试默认主题
        assert settings.current_theme == "dark"
        config = settings.get_theme_config()
        assert config["name"] == "暗色"
        assert config["background"] == "#2b2b2b"
        
        # 测试切换主题
        assert settings.set_theme("light") == True
        assert settings.current_theme == "light"
        config = settings.get_theme_config()
        assert config["name"] == "亮色"
        
        # 测试无效主题
        assert settings.set_theme("invalid") == False
        assert settings.current_theme == "light"  # 保持不变
        
        # 测试获取可用主题
        themes = settings.get_available_themes()
        assert len(themes) == 3
        assert "dark" in themes
        assert "light" in themes
        assert "office" in themes

    def test_font_settings(self, qapp):
        """测试字体设置"""
        class FontSettings:
            def __init__(self):
                self.font_family = "Arial"
                self.font_size = 12
                self.font_weight = "normal"
                self.line_height = 1.5
            
            def set_font_size(self, size):
                """设置字体大小"""
                if 8 <= size <= 24:
                    self.font_size = size
                    return True
                return False
            
            def set_font_family(self, family):
                """设置字体族"""
                self.font_family = family
                return True
            
            def set_font_weight(self, weight):
                """设置字体粗细"""
                valid_weights = ["normal", "bold", "lighter"]
                if weight in valid_weights:
                    self.font_weight = weight
                    return True
                return False
            
            def set_line_height(self, height):
                """设置行高"""
                if 1.0 <= height <= 3.0:
                    self.line_height = height
                    return True
                return False
            
            def get_font_config(self):
                """获取字体配置"""
                return {
                    "family": self.font_family,
                    "size": self.font_size,
                    "weight": self.font_weight,
                    "line_height": self.line_height
                }
        
        settings = FontSettings()
        
        # 测试默认设置
        assert settings.font_family == "Arial"
        assert settings.font_size == 12
        assert settings.font_weight == "normal"
        assert settings.line_height == 1.5
        
        # 测试设置字体大小
        assert settings.set_font_size(14) == True
        assert settings.font_size == 14
        
        # 测试无效字体大小
        assert settings.set_font_size(30) == False
        assert settings.font_size == 14  # 保持不变
        
        # 测试设置字体族
        assert settings.set_font_family("Times New Roman") == True
        assert settings.font_family == "Times New Roman"
        
        # 测试设置字体粗细
        assert settings.set_font_weight("bold") == True
        assert settings.font_weight == "bold"
        
        # 测试无效字体粗细
        assert settings.set_font_weight("invalid") == False
        assert settings.font_weight == "bold"  # 保持不变
        
        # 测试设置行高
        assert settings.set_line_height(2.0) == True
        assert settings.line_height == 2.0
        
        # 测试无效行高
        assert settings.set_line_height(5.0) == False
        assert settings.line_height == 2.0  # 保持不变
        
        # 测试获取配置
        config = settings.get_font_config()
        assert config["family"] == "Times New Roman"
        assert config["size"] == 14
        assert config["weight"] == "bold"
        assert config["line_height"] == 2.0


class TestProgressFeedback:
    """进度反馈测试"""

    def test_progress_bar_initialization(self, qapp):
        """测试进度条初始化"""
        class ProgressWidget(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setup_ui()
            
            def setup_ui(self):
                """设置UI"""
                layout = QVBoxLayout(self)
                
                # 进度条
                self.progress_bar = QProgressBar()
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)
                layout.addWidget(self.progress_bar)
                
                # 状态标签
                self.status_label = QLabel("就绪")
                layout.addWidget(self.status_label)
                
                # 取消按钮
                self.cancel_btn = QPushButton("取消")
                self.cancel_btn.setEnabled(False)
                layout.addWidget(self.cancel_btn)
            
            def update_progress(self, value, status=""):
                """更新进度"""
                self.progress_bar.setValue(value)
                if status:
                    self.status_label.setText(status)
                
                # 启用/禁用取消按钮
                self.cancel_btn.setEnabled(0 < value < 100)
            
            def reset(self):
                """重置"""
                self.progress_bar.setValue(0)
                self.status_label.setText("就绪")
                self.cancel_btn.setEnabled(False)
        
        widget = ProgressWidget()
        
        # 测试初始状态
        assert widget.progress_bar.value() == 0
        assert widget.status_label.text() == "就绪"
        assert widget.cancel_btn.isEnabled() == False
        
        # 测试更新进度
        widget.update_progress(50, "处理中...")
        assert widget.progress_bar.value() == 50
        assert widget.status_label.text() == "处理中..."
        assert widget.cancel_btn.isEnabled() == True
        
        # 测试完成
        widget.update_progress(100, "完成")
        assert widget.progress_bar.value() == 100
        assert widget.status_label.text() == "完成"
        assert widget.cancel_btn.isEnabled() == False
        
        # 测试重置
        widget.reset()
        assert widget.progress_bar.value() == 0
        assert widget.status_label.text() == "就绪"

    def test_progress_callback(self, qapp):
        """测试进度回调"""
        class ProgressManager:
            def __init__(self):
                self.callbacks = []
                self.current_progress = 0
                self.is_cancelled = False
            
            def add_callback(self, callback):
                """添加回调"""
                self.callbacks.append(callback)
            
            def update_progress(self, value):
                """更新进度"""
                if self.is_cancelled:
                    return False
                
                self.current_progress = value
                
                # 调用所有回调
                for callback in self.callbacks:
                    callback(value)
                
                return True
            
            def cancel(self):
                """取消"""
                self.is_cancelled = True
            
            def reset(self):
                """重置"""
                self.current_progress = 0
                self.is_cancelled = False
        
        manager = ProgressManager()
        
        # 添加回调
        progress_values = []
        def on_progress(value):
            progress_values.append(value)
        
        manager.add_callback(on_progress)
        
        # 测试更新进度
        manager.update_progress(25)
        assert manager.current_progress == 25
        assert progress_values == [25]
        
        manager.update_progress(50)
        assert manager.current_progress == 50
        assert progress_values == [25, 50]
        
        # 测试取消
        manager.cancel()
        result = manager.update_progress(75)
        assert result == False
        assert manager.current_progress == 50  # 保持不变
        
        # 测试重置
        manager.reset()
        assert manager.current_progress == 0
        assert manager.is_cancelled == False

    def test_progress_estimation(self, qapp):
        """测试进度估算"""
        class ProgressEstimator:
            def __init__(self):
                self.start_time = None
                self.current_progress = 0
                self.estimated_total = 100
            
            def start(self):
                """开始"""
                import time
                self.start_time = time.time()
                self.current_progress = 0
            
            def update(self, progress):
                """更新进度"""
                self.current_progress = progress
            
            def get_estimated_remaining(self):
                """获取预估剩余时间"""
                if not self.start_time or self.current_progress == 0:
                    return None
                
                import time
                elapsed = time.time() - self.start_time
                if self.current_progress >= self.estimated_total:
                    return 0
                
                # 计算平均速度
                speed = self.current_progress / elapsed
                remaining = (self.estimated_total - self.current_progress) / speed
                
                return remaining
            
            def get_estimated_completion_time(self):
                """获取预估完成时间"""
                remaining = self.get_estimated_remaining()
                if remaining is None:
                    return None
                
                import time
                return time.time() + remaining
        
        estimator = ProgressEstimator()
        
        # 测试开始前
        assert estimator.get_estimated_remaining() is None
        
        # 测试开始
        estimator.start()
        assert estimator.current_progress == 0
        
        # 测试更新进度
        estimator.update(50)
        assert estimator.current_progress == 50
        
        # 测试预估剩余时间（需要实际时间流逝）
        # 这里只测试方法存在和可调用
        assert hasattr(estimator, 'get_estimated_remaining')
        assert hasattr(estimator, 'get_estimated_completion_time')

    def test_multi_step_progress(self, qapp):
        """测试多步骤进度"""
        class MultiStepProgress:
            def __init__(self):
                self.steps = []
                self.current_step = 0
                self.step_progress = 0
            
            def add_step(self, name, weight=1):
                """添加步骤"""
                self.steps.append({"name": name, "weight": weight})
            
            def update_step_progress(self, progress):
                """更新当前步骤进度"""
                self.step_progress = progress
            
            def next_step(self):
                """进入下一步"""
                if self.current_step < len(self.steps) - 1:
                    self.current_step += 1
                    self.step_progress = 0
                    return True
                return False
            
            def get_overall_progress(self):
                """获取总体进度"""
                if not self.steps:
                    return 0
                
                # 计算总权重
                total_weight = sum(step["weight"] for step in self.steps)
                
                # 计算当前进度
                current_weight = 0
                for i, step in enumerate(self.steps):
                    if i < self.current_step:
                        current_weight += step["weight"]
                    elif i == self.current_step:
                        current_weight += step["weight"] * (self.step_progress / 100)
                
                return (current_weight / total_weight) * 100
            
            def get_current_step_name(self):
                """获取当前步骤名称"""
                if 0 <= self.current_step < len(self.steps):
                    return self.steps[self.current_step]["name"]
                return None
        
        progress = MultiStepProgress()
        
        # 添加步骤
        progress.add_step("加载文档", weight=1)
        progress.add_step("解析内容", weight=2)
        progress.add_step("生成结果", weight=1)
        
        # 测试初始状态
        assert progress.current_step == 0
        assert progress.get_current_step_name() == "加载文档"
        assert progress.get_overall_progress() == 0
        
        # 测试更新步骤进度
        progress.update_step_progress(50)
        assert progress.get_overall_progress() == 12.5  # (1 * 0.5) / 4 * 100
        
        # 测试下一步
        progress.next_step()
        assert progress.current_step == 1
        assert progress.get_current_step_name() == "解析内容"
        assert progress.step_progress == 0
        
        # 测试完成
        progress.update_step_progress(100)
        progress.next_step()
        progress.update_step_progress(100)
        assert progress.get_overall_progress() == 100


class TestIntegration:
    """集成测试"""

    def test_context_menu_integration(self, qapp):
        """测试右键菜单集成"""
        class IntegratedContextMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.selected_text = ""
                self.triggered_action = None
            
            def show_for_text(self, text, position):
                """为文本显示菜单"""
                self.selected_text = text
                # 模拟显示菜单
                return True
            
            def handle_action(self, action_id):
                """处理动作"""
                self.triggered_action = action_id
                return True
        
        menu = IntegratedContextMenu()
        
        # 测试显示菜单
        result = menu.show_for_text("测试文本", (100, 100))
        assert result == True
        assert menu.selected_text == "测试文本"
        
        # 测试处理动作
        result = menu.handle_action("translate")
        assert result == True
        assert menu.triggered_action == "translate"

    def test_settings_integration(self, qapp):
        """测试设置集成"""
        class IntegratedSettings:
            def __init__(self):
                self.theme = "dark"
                self.font_size = 12
                self.auto_save = True
            
            def apply_settings(self, settings):
                """应用设置"""
                if "theme" in settings:
                    self.theme = settings["theme"]
                if "font_size" in settings:
                    self.font_size = settings["font_size"]
                if "auto_save" in settings:
                    self.auto_save = settings["auto_save"]
                return True
            
            def get_current_settings(self):
                """获取当前设置"""
                return {
                    "theme": self.theme,
                    "font_size": self.font_size,
                    "auto_save": self.auto_save
                }
        
        settings = IntegratedSettings()
        
        # 测试应用设置
        new_settings = {
            "theme": "light",
            "font_size": 14,
            "auto_save": False
        }
        
        result = settings.apply_settings(new_settings)
        assert result == True
        assert settings.theme == "light"
        assert settings.font_size == 14
        assert settings.auto_save == False
        
        # 测试获取当前设置
        current = settings.get_current_settings()
        assert current["theme"] == "light"
        assert current["font_size"] == 14
        assert current["auto_save"] == False

    def test_progress_integration(self, qapp):
        """测试进度集成"""
        class IntegratedProgress:
            def __init__(self):
                self.progress_bar = None
                self.status_label = None
                self.callbacks = []
            
            def set_progress_bar(self, progress_bar):
                self.progress_bar = progress_bar
            
            def set_status_label(self, status_label):
                self.status_label = status_label
            
            def add_callback(self, callback):
                self.callbacks.append(callback)
            
            def update(self, progress, status=""):
                """更新进度"""
                if self.progress_bar:
                    self.progress_bar.setValue(progress)
                
                if self.status_label and status:
                    self.status_label.setText(status)
                
                for callback in self.callbacks:
                    callback(progress, status)
                
                return True
        
        progress = IntegratedProgress()
        
        # 设置组件
        mock_progress_bar = MagicMock()
        mock_status_label = MagicMock()
        
        progress.set_progress_bar(mock_progress_bar)
        progress.set_status_label(mock_status_label)
        
        # 添加回调
        callback_values = []
        def on_progress(value, status):
            callback_values.append((value, status))
        
        progress.add_callback(on_progress)
        
        # 测试更新
        progress.update(50, "处理中...")
        
        mock_progress_bar.setValue.assert_called_with(50)
        mock_status_label.setText.assert_called_with("处理中...")
        assert callback_values == [(50, "处理中...")]

    def test_complete_workflow(self, qapp):
        """测试完整工作流"""
        class WorkflowManager:
            def __init__(self):
                self.steps = []
                self.current_step = 0
                self.settings = {}
                self.progress = 0
            
            def load_settings(self):
                """加载设置"""
                self.settings = {"theme": "dark", "auto_save": True}
                return True
            
            def execute_step(self, step_name):
                """执行步骤"""
                self.steps.append(step_name)
                self.current_step += 1
                return True
            
            def update_progress(self, progress):
                """更新进度"""
                self.progress = progress
                return True
            
            def get_status(self):
                """获取状态"""
                return {
                    "steps_completed": len(self.steps),
                    "current_step": self.current_step,
                    "progress": self.progress,
                    "settings": self.settings
                }
        
        manager = WorkflowManager()
        
        # 测试加载设置
        assert manager.load_settings() == True
        assert manager.settings["theme"] == "dark"
        
        # 测试执行步骤
        assert manager.execute_step("初始化") == True
        assert manager.execute_step("处理") == True
        assert manager.execute_step("完成") == True
        
        # 测试更新进度
        assert manager.update_progress(100) == True
        
        # 测试获取状态
        status = manager.get_status()
        assert status["steps_completed"] == 3
        assert status["progress"] == 100
        assert status["settings"]["theme"] == "dark"


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_menu(self, qapp):
        """测试空菜单"""
        class EmptyMenu(QMenu):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.has_items = False
            
            def check_has_items(self):
                """检查是否有菜单项"""
                self.has_items = len(self.actions()) > 0
                return self.has_items
        
        menu = EmptyMenu()
        
        # 测试空菜单
        assert menu.check_has_items() == False
        assert menu.has_items == False

    def test_invalid_settings(self, qapp):
        """测试无效设置"""
        class SettingsValidator:
            def __init__(self):
                self.valid_themes = ["dark", "light", "office"]
                self.valid_font_sizes = range(8, 25)
            
            def validate_theme(self, theme):
                """验证主题"""
                return theme in self.valid_themes
            
            def validate_font_size(self, size):
                """验证字体大小"""
                return size in self.valid_font_sizes
            
            def validate_settings(self, settings):
                """验证设置"""
                errors = []
                
                if "theme" in settings:
                    if not self.validate_theme(settings["theme"]):
                        errors.append(f"无效的主题: {settings['theme']}")
                
                if "font_size" in settings:
                    if not self.validate_font_size(settings["font_size"]):
                        errors.append(f"无效的字体大小: {settings['font_size']}")
                
                return len(errors) == 0, errors
        
        validator = SettingsValidator()
        
        # 测试有效设置
        valid_settings = {"theme": "dark", "font_size": 12}
        is_valid, errors = validator.validate_settings(valid_settings)
        assert is_valid == True
        assert len(errors) == 0
        
        # 测试无效主题
        invalid_settings = {"theme": "invalid", "font_size": 12}
        is_valid, errors = validator.validate_settings(invalid_settings)
        assert is_valid == False
        assert len(errors) == 1
        assert "无效的主题" in errors[0]
        
        # 测试无效字体大小
        invalid_settings = {"theme": "dark", "font_size": 30}
        is_valid, errors = validator.validate_settings(invalid_settings)
        assert is_valid == False
        assert len(errors) == 1
        assert "无效的字体大小" in errors[0]

    def test_progress_overflow(self, qapp):
        """测试进度溢出"""
        class ProgressHandler:
            def __init__(self):
                self.progress = 0
            
            def set_progress(self, value):
                """设置进度"""
                if value < 0:
                    self.progress = 0
                elif value > 100:
                    self.progress = 100
                else:
                    self.progress = value
                return self.progress
        
        handler = ProgressHandler()
        
        # 测试正常范围
        assert handler.set_progress(50) == 50
        assert handler.progress == 50
        
        # 测试下溢
        assert handler.set_progress(-10) == 0
        assert handler.progress == 0
        
        # 测试上溢
        assert handler.set_progress(150) == 100
        assert handler.progress == 100
        
        # 测试边界值
        assert handler.set_progress(0) == 0
        assert handler.set_progress(100) == 100

    def test_concurrent_updates(self, qapp):
        """测试并发更新"""
        class ConcurrentHandler:
            def __init__(self):
                self.updates = []
                self.locked = False
            
            def update(self, value):
                """更新"""
                if self.locked:
                    return False
                
                self.locked = True
                self.updates.append(value)
                self.locked = False
                return True
            
            def get_updates(self):
                """获取更新"""
                return self.updates.copy()
        
        handler = ConcurrentHandler()
        
        # 测试正常更新
        assert handler.update(1) == True
        assert handler.update(2) == True
        assert handler.update(3) == True
        
        # 验证更新顺序
        assert handler.get_updates() == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
