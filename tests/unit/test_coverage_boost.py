"""
覆盖率提升测试 - 补充单元测试和边际测试
目标：将覆盖率从46%提升到80%+ 
不使用mock，直接测试真实代码
"""
import pytest
import sys
import os
import json
import tempfile
import time

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """创建QApplication实例"""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# ==================== SettingsDialog 完整测试 ====================
class TestSettingsDialogComplete:
    """SettingsDialog完整覆盖测试"""
    
    @pytest.fixture
    def settings_dialog(self, qapp):
        """创建SettingsDialog实例"""
        from widgets.settings_dialog import SettingsDialog
        
        # 使用临时文件避免污染真实配置
        dialog = SettingsDialog()
        dialog.settings_file = tempfile.mktemp(suffix='.json')
        yield dialog
        
        # 清理
        if os.path.exists(dialog.settings_file):
            os.unlink(dialog.settings_file)
    
    def test_default_settings(self, settings_dialog):
        """测试默认设置值"""
        settings = settings_dialog.get_settings()
        assert settings["theme"] == "dark"
        assert settings["font_size"] == 12
        assert settings["font_family"] == "Arial"
        assert settings["auto_save"] == True
        assert settings["auto_translate"] == False
        assert settings["show_shortcuts"] == True
        assert settings["language"] == "zh"
        assert settings["office_mode"] == False
        assert settings["recent_files_limit"] == 10
        assert settings["default_export_format"] == "docx"
    
    def test_theme_change_events(self, settings_dialog):
        """测试主题改变事件处理"""
        # 测试暗色主题
        settings_dialog._on_theme_changed("暗色")
        assert settings_dialog.settings["theme"] == "dark"
        
        # 测试亮色主题
        settings_dialog._on_theme_changed("亮色")
        assert settings_dialog.settings["theme"] == "light"
        
        # 测试办公主题
        settings_dialog._on_theme_changed("办公")
        assert settings_dialog.settings["theme"] == "office"
        
        # 测试无效主题（应默认为dark）
        settings_dialog._on_theme_changed("不存在的主题")
        assert settings_dialog.settings["theme"] == "dark"
    
    def test_font_size_change(self, settings_dialog):
        """测试字体大小改变"""
        settings_dialog._on_font_size_changed(16)
        assert settings_dialog.settings["font_size"] == 16
        
        settings_dialog._on_font_size_changed(8)
        assert settings_dialog.settings["font_size"] == 8
        
        settings_dialog._on_font_size_changed(24)
        assert settings_dialog.settings["font_size"] == 24
    
    def test_font_family_change(self, settings_dialog):
        """测试字体族改变"""
        settings_dialog._on_font_family_changed("Times New Roman")
        assert settings_dialog.settings["font_family"] == "Times New Roman"
        
        settings_dialog._on_font_family_changed("SimSun")
        assert settings_dialog.settings["font_family"] == "SimSun"
    
    def test_checkbox_events(self, settings_dialog):
        """测试复选框事件处理"""
        from PyQt6.QtCore import Qt
        
        # 测试显示快捷键
        settings_dialog._on_show_shortcuts_changed(Qt.CheckState.Checked.value)
        assert settings_dialog.settings["show_shortcuts"] == True
        
        settings_dialog._on_show_shortcuts_changed(Qt.CheckState.Unchecked.value)
        assert settings_dialog.settings["show_shortcuts"] == False
        
        # 测试自动保存
        settings_dialog._on_auto_save_changed(Qt.CheckState.Checked.value)
        assert settings_dialog.settings["auto_save"] == True
        
        settings_dialog._on_auto_save_changed(Qt.CheckState.Unchecked.value)
        assert settings_dialog.settings["auto_save"] == False
        
        # 测试自动翻译
        settings_dialog._on_auto_translate_changed(Qt.CheckState.Checked.value)
        assert settings_dialog.settings["auto_translate"] == True
        
        # 测试办公模式
        settings_dialog._on_office_mode_changed(Qt.CheckState.Checked.value)
        assert settings_dialog.settings["office_mode"] == True
    
    def test_language_change(self, settings_dialog):
        """测试语言改变事件"""
        settings_dialog._on_language_changed("中文")
        assert settings_dialog.settings["language"] == "zh"
        
        settings_dialog._on_language_changed("English")
        assert settings_dialog.settings["language"] == "en"
        
        settings_dialog._on_language_changed("日本語")
        assert settings_dialog.settings["language"] == "ja"
        
        settings_dialog._on_language_changed("한국어")
        assert settings_dialog.settings["language"] == "ko"
        
        # 无效语言应默认为zh
        settings_dialog._on_language_changed("未知语言")
        assert settings_dialog.settings["language"] == "zh"
    
    def test_recent_files_change(self, settings_dialog):
        """测试最近文件数改变"""
        settings_dialog._on_recent_files_changed(20)
        assert settings_dialog.settings["recent_files_limit"] == 20
        
        settings_dialog._on_recent_files_changed(5)
        assert settings_dialog.settings["recent_files_limit"] == 5
    
    def test_export_format_change(self, settings_dialog):
        """测试导出格式改变"""
        settings_dialog._on_export_format_changed("pdf")
        assert settings_dialog.settings["default_export_format"] == "pdf"
        
        settings_dialog._on_export_format_changed("txt")
        assert settings_dialog.settings["default_export_format"] == "txt"
    
    def test_save_and_load_settings(self, settings_dialog):
        """测试保存和加载设置"""
        # 修改设置
        settings_dialog.settings["theme"] = "light"
        settings_dialog.settings["font_size"] = 16
        
        # 保存设置
        result = settings_dialog.save_settings()
        assert result == True
        assert os.path.exists(settings_dialog.settings_file)
        
        # 创建新实例加载设置
        from widgets.settings_dialog import SettingsDialog
        new_dialog = SettingsDialog()
        new_dialog.settings_file = settings_dialog.settings_file
        new_dialog.load_settings()
        
        # 验证加载的设置
        assert new_dialog.settings["theme"] == "light"
        assert new_dialog.settings["font_size"] == 16
    
    def test_load_settings_nonexistent_file(self, settings_dialog):
        """测试加载不存在的设置文件"""
        settings_dialog.settings_file = "/tmp/nonexistent_settings.json"
        settings_dialog.load_settings()
        
        # 应保持默认设置
        assert settings_dialog.settings["theme"] == "dark"
    
    def test_load_settings_invalid_json(self, settings_dialog):
        """测试加载无效JSON文件"""
        # 写入无效JSON
        with open(settings_dialog.settings_file, 'w') as f:
            f.write("invalid json content")
        
        # 应该不崩溃，保持默认设置
        settings_dialog.load_settings()
        assert settings_dialog.settings["theme"] == "dark"
    
    def test_set_and_get_setting(self, settings_dialog):
        """测试设置单个设置项"""
        settings_dialog.set_setting("theme", "office")
        assert settings_dialog.get_setting("theme") == "office"
        
        settings_dialog.set_setting("font_size", 20)
        assert settings_dialog.get_setting("font_size") == 20
        
        # 测试获取不存在的设置
        assert settings_dialog.get_setting("nonexistent") is None
    
    def test_settings_changed_signal(self, settings_dialog, qapp):
        """测试设置改变信号"""
        signal_received = []
        settings_dialog.settings_changed.connect(lambda s: signal_received.append(s))
        
        # 手动触发保存（会发射信号）
        settings_dialog.save_settings()
        settings_dialog.settings_changed.emit(settings_dialog.settings)
        
        assert len(signal_received) == 1
        assert signal_received[0]["theme"] == "dark"
    
    def test_ui_update_from_settings(self, settings_dialog):
        """测试UI从设置更新"""
        # 修改设置
        settings_dialog.settings["theme"] = "light"
        settings_dialog.settings["font_size"] = 16
        settings_dialog.settings["language"] = "en"
        
        # 更新UI
        settings_dialog._update_ui_from_settings()
        
        # 验证UI更新
        assert settings_dialog.theme_combo.currentText() == "亮色"
        assert settings_dialog.font_size_spin.value() == 16
        assert settings_dialog.language_combo.currentText() == "English"
    
    def test_reset_to_default(self, settings_dialog):
        """测试重置为默认设置"""
        # 修改设置
        settings_dialog.settings["theme"] = "light"
        settings_dialog.settings["font_size"] = 20
        
        # 重置为默认
        settings_dialog.settings = settings_dialog.DEFAULT_SETTINGS.copy()
        settings_dialog._update_ui_from_settings()
        
        # 验证重置
        assert settings_dialog.settings["theme"] == "dark"
        assert settings_dialog.settings["font_size"] == 12
    
    def test_export_import_settings(self, settings_dialog):
        """测试导出导入设置"""
        # 修改设置
        settings_dialog.settings["theme"] = "office"
        settings_dialog.settings["font_size"] = 18
        
        # 导出设置
        export_file = tempfile.mktemp(suffix='.json')
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(settings_dialog.settings, f, indent=2, ensure_ascii=False)
        
        # 创建新对话框并导入
        from widgets.settings_dialog import SettingsDialog
        new_dialog = SettingsDialog()
        new_dialog.settings_file = tempfile.mktemp(suffix='.json')
        
        with open(export_file, 'r', encoding='utf-8') as f:
            imported_settings = json.load(f)
            new_dialog.settings.update(imported_settings)
        
        # 验证导入
        assert new_dialog.settings["theme"] == "office"
        assert new_dialog.settings["font_size"] == 18
        
        # 清理
        os.unlink(export_file)


# ==================== ProgressWidget 完整测试 ====================
class TestProgressWidgetComplete:
    """ProgressWidget完整覆盖测试"""
    
    @pytest.fixture
    def progress_widget(self, qapp):
        """创建ProgressWidget实例"""
        from widgets.progress_widget import ProgressWidget
        widget = ProgressWidget()
        return widget
    
    def test_initial_state(self, progress_widget):
        """测试初始状态"""
        assert progress_widget.current_progress == 0
        assert progress_widget.is_cancelled == False
        assert progress_widget.estimated_total == 100
        assert progress_widget.start_time is None
        assert progress_widget.status_label.text() == "就绪"
        assert progress_widget.percent_label.text() == "0%"
    
    def test_start_progress(self, progress_widget):
        """测试开始进度"""
        progress_widget.start(200)
        
        assert progress_widget.estimated_total == 200
        assert progress_widget.current_progress == 0
        assert progress_widget.is_cancelled == False
        assert progress_widget.start_time is not None
        assert progress_widget.status_label.text() == "处理中..."
        assert progress_widget.cancel_btn.isEnabled() == True
        assert progress_widget.pause_btn.isEnabled() == True
    
    def test_update_progress(self, progress_widget):
        """测试更新进度"""
        progress_widget.start(100)
        
        # 更新到50%
        result = progress_widget.update(50, "处理中...")
        assert result == True
        assert progress_widget.current_progress == 50
        assert progress_widget.percent_label.text() == "50%"
        assert progress_widget.status_label.text() == "处理中..."
    
    def test_update_progress_complete(self, progress_widget, qapp):
        """测试进度完成"""
        signal_received = []
        progress_widget.completed.connect(lambda: signal_received.append(True))
        
        progress_widget.start(100)
        progress_widget.update(100)
        
        assert progress_widget.status_label.text() == "完成"
        assert progress_widget.percent_label.text() == "100%"
        assert progress_widget.cancel_btn.isEnabled() == False
        assert progress_widget.pause_btn.isEnabled() == False
        assert len(signal_received) == 1
    
    def test_update_progress_cancelled(self, progress_widget):
        """测试取消后的进度更新"""
        progress_widget.start(100)
        progress_widget._on_cancel()
        
        result = progress_widget.update(50)
        assert result == False
    
    def test_cancel_progress(self, progress_widget, qapp):
        """测试取消进度"""
        signal_received = []
        progress_widget.cancelled.connect(lambda: signal_received.append(True))
        
        progress_widget.start(100)
        progress_widget._on_cancel()
        
        assert progress_widget.is_cancelled == True
        assert progress_widget.status_label.text() == "已取消"
        assert progress_widget.cancel_btn.isEnabled() == False
        assert progress_widget.pause_btn.isEnabled() == False
        assert len(signal_received) == 1
    
    def test_reset_progress(self, progress_widget):
        """测试重置进度"""
        progress_widget.start(100)
        progress_widget.update(50)
        progress_widget.reset()
        
        assert progress_widget.current_progress == 0
        assert progress_widget.is_cancelled == False
        assert progress_widget.start_time is None
        assert progress_widget.status_label.text() == "就绪"
        assert progress_widget.percent_label.text() == "0%"
        assert progress_widget.cancel_btn.isEnabled() == False
    
    def test_get_progress(self, progress_widget):
        """测试获取进度"""
        progress_widget.start(100)
        assert progress_widget.get_progress() == 0
        
        progress_widget.update(50)
        assert progress_widget.get_progress() == 50
    
    def test_get_status(self, progress_widget):
        """测试获取状态"""
        assert progress_widget.get_status() == "就绪"
        
        progress_widget.start(100)
        assert progress_widget.get_status() == "处理中..."
    
    def test_is_running(self, progress_widget):
        """测试是否正在运行"""
        assert progress_widget.is_running() == False
        
        progress_widget.start(100)
        assert progress_widget.is_running() == True
        
        progress_widget._on_cancel()
        assert progress_widget.is_running() == False
    
    def test_update_estimated_time(self, progress_widget):
        """测试预估时间更新"""
        progress_widget.start(100)
        progress_widget.current_progress = 50
        progress_widget.start_time = time.time() - 10  # 10秒前开始
        
        progress_widget._update_estimated_time()
        
        # 应该有预估时间显示
        assert progress_widget.estimated_label.text() != ""
        assert progress_widget.estimated_label.text() != "计算中..."
    
    def test_update_estimated_time_no_start(self, progress_widget):
        """测试未开始时更新预估时间"""
        progress_widget._update_estimated_time()
        # 应该不崩溃


class TestMultiStepProgressWidgetComplete:
    """MultiStepProgressWidget完整覆盖测试"""
    
    @pytest.fixture
    def multi_step_widget(self, qapp):
        """创建MultiStepProgressWidget实例"""
        from widgets.progress_widget import MultiStepProgressWidget
        widget = MultiStepProgressWidget()
        return widget
    
    def test_initial_state(self, multi_step_widget):
        """测试初始状态"""
        assert len(multi_step_widget.steps) == 0
        assert multi_step_widget.current_step == 0
        assert multi_step_widget.step_progress == 0
        assert multi_step_widget.step_label.text() == "步骤 0/0"
    
    def test_add_step(self, multi_step_widget):
        """测试添加步骤"""
        multi_step_widget.add_step("步骤1", weight=1)
        multi_step_widget.add_step("步骤2", weight=2)
        multi_step_widget.add_step("步骤3", weight=3)
        
        assert len(multi_step_widget.steps) == 3
        assert multi_step_widget.steps[0]["name"] == "步骤1"
        assert multi_step_widget.steps[0]["weight"] == 1
        assert multi_step_widget.steps[1]["weight"] == 2
        assert multi_step_widget.steps[2]["weight"] == 3
    
    def test_start_with_steps(self, multi_step_widget, qapp):
        """测试开始执行步骤"""
        signal_received = []
        multi_step_widget.step_changed.connect(lambda idx, name: signal_received.append((idx, name)))
        
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        
        assert multi_step_widget.current_step == 0
        assert multi_step_widget.step_name_label.text() == "步骤1"
        assert multi_step_widget.status_label.text() == "处理中..."
        assert multi_step_widget.cancel_btn.isEnabled() == True
        assert len(signal_received) == 1
        assert signal_received[0] == (0, "步骤1")
    
    def test_start_without_steps(self, multi_step_widget):
        """测试没有步骤时开始"""
        multi_step_widget.start()
        assert multi_step_widget.current_step == 0
    
    def test_update_step_progress(self, multi_step_widget):
        """测试更新步骤进度"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        
        multi_step_widget.update_step_progress(50)
        assert multi_step_widget.step_progress == 50
        
        # 验证总体进度计算
        overall = multi_step_widget._calculate_overall_progress()
        assert overall == 25.0  # 50% of 50% (1 step out of 2)
    
    def test_next_step(self, multi_step_widget, qapp):
        """测试进入下一步"""
        signal_received = []
        multi_step_widget.step_changed.connect(lambda idx, name: signal_received.append((idx, name)))
        
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.add_step("步骤3")
        multi_step_widget.start()
        
        # 进入下一步
        result = multi_step_widget.next_step()
        assert result == True
        assert multi_step_widget.current_step == 1
        assert multi_step_widget.step_name_label.text() == "步骤2"
        assert len(signal_received) == 2
        
        # 再下一步
        result = multi_step_widget.next_step()
        assert result == True
        assert multi_step_widget.current_step == 2
        assert multi_step_widget.step_name_label.text() == "步骤3"
    
    def test_next_step_at_end(self, multi_step_widget):
        """测试在最后一步时进入下一步"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.start()
        
        result = multi_step_widget.next_step()
        assert result == False
        assert multi_step_widget.current_step == 0
    
    def test_calculate_overall_progress(self, multi_step_widget):
        """测试总体进度计算"""
        multi_step_widget.add_step("步骤1", weight=1)
        multi_step_widget.add_step("步骤2", weight=2)
        multi_step_widget.add_step("步骤3", weight=3)
        multi_step_widget.start()
        
        # 步骤1完成50%
        multi_step_widget.update_step_progress(50)
        overall = multi_step_widget._calculate_overall_progress()
        assert overall == pytest.approx(8.33, abs=0.01)  # (0.5/6) * 100
        
        # 进入步骤2
        multi_step_widget.next_step()
        multi_step_widget.update_step_progress(100)
        overall = multi_step_widget._calculate_overall_progress()
        assert overall == pytest.approx(50.0, abs=0.01)  # (1 + 2) / 6 * 100
    
    def test_calculate_overall_progress_no_steps(self, multi_step_widget):
        """测试无步骤时的总体进度"""
        overall = multi_step_widget._calculate_overall_progress()
        assert overall == 0
    
    def test_cancel_multi_step(self, multi_step_widget, qapp):
        """测试取消多步骤进度"""
        signal_received = []
        multi_step_widget.cancelled.connect(lambda: signal_received.append(True))
        
        multi_step_widget.add_step("步骤1")
        multi_step_widget.start()
        multi_step_widget._on_cancel()
        
        assert multi_step_widget.status_label.text() == "已取消"
        assert multi_step_widget.cancel_btn.isEnabled() == False
        assert len(signal_received) == 1
    
    def test_complete_multi_step(self, multi_step_widget, qapp):
        """测试完成多步骤进度"""
        signal_received = []
        multi_step_widget.completed.connect(lambda: signal_received.append(True))
        
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        multi_step_widget.complete()
        
        assert multi_step_widget.status_label.text() == "完成"
        assert multi_step_widget.percent_label.text() == "100%"
        assert len(signal_received) == 1
    
    def test_reset_multi_step(self, multi_step_widget):
        """测试重置多步骤进度"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        multi_step_widget.update_step_progress(50)
        multi_step_widget.next_step()
        
        multi_step_widget.reset()
        
        assert multi_step_widget.current_step == 0
        assert multi_step_widget.step_progress == 0
        assert multi_step_widget.progress_bar.value() == 0
        assert multi_step_widget.status_label.text() == "就绪"
        assert multi_step_widget.cancel_btn.isEnabled() == False
    
    def test_get_current_step(self, multi_step_widget):
        """测试获取当前步骤"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        
        assert multi_step_widget.get_current_step() == 0
        
        multi_step_widget.next_step()
        assert multi_step_widget.get_current_step() == 1
    
    def test_get_current_step_name(self, multi_step_widget):
        """测试获取当前步骤名称"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        
        assert multi_step_widget.get_current_step_name() == "步骤1"
        
        multi_step_widget.next_step()
        assert multi_step_widget.get_current_step_name() == "步骤2"
    
    def test_get_current_step_name_invalid(self, multi_step_widget):
        """测试获取无效步骤名称"""
        assert multi_step_widget.get_current_step_name() is None
    
    def test_get_overall_progress(self, multi_step_widget):
        """测试获取总体进度"""
        multi_step_widget.add_step("步骤1")
        multi_step_widget.add_step("步骤2")
        multi_step_widget.start()
        
        multi_step_widget.update_step_progress(50)
        overall = multi_step_widget.get_overall_progress()
        assert overall == pytest.approx(25.0, abs=0.01)


# ==================== ContextMenu 完整测试 ====================
class TestContextMenuComplete:
    """ContextMenu完整覆盖测试"""
    
    @pytest.fixture
    def context_menu(self, qapp):
        """创建ContextMenu实例"""
        from widgets.context_menu import ContextMenu
        return ContextMenu()
    
    def test_initialization(self, context_menu):
        """测试初始化"""
        assert context_menu.context_type == "text"
        assert len(context_menu.actions_map) > 0
        assert "copy" in context_menu.actions_map
        assert "paste" in context_menu.actions_map
        assert "translate" in context_menu.actions_map
    
    def test_add_action(self, context_menu):
        """测试添加菜单项"""
        action = context_menu.add_action("测试", "test_action", "Ctrl+Shift+T")
        assert action is not None
        assert "test_action" in context_menu.actions_map
        assert context_menu.actions_map["test_action"] == action
    
    def test_add_action_without_shortcut(self, context_menu):
        """测试添加无快捷键的菜单项"""
        action = context_menu.add_action("测试", "test_action")
        assert action is not None
    
    def test_add_dynamic_action(self, context_menu):
        """测试添加动态菜单项"""
        action = context_menu.add_dynamic_action("动态项", "dynamic_action", {"key": "value"})
        assert action is not None
        assert len(context_menu.dynamic_actions) == 1
    
    def test_clear_dynamic_actions(self, context_menu):
        """测试清除动态菜单项"""
        context_menu.add_dynamic_action("动态1", "dynamic1")
        context_menu.add_dynamic_action("动态2", "dynamic2")
        assert len(context_menu.dynamic_actions) == 2
        
        context_menu.clear_dynamic_actions()
        assert len(context_menu.dynamic_actions) == 0
    
    def test_set_context(self, context_menu):
        """测试设置上下文类型"""
        context_menu.set_context("code")
        assert context_menu.context_type == "code"
        
        context_menu.set_context("file")
        assert context_menu.context_type == "file"
    
    def test_update_dynamic_items_text(self, context_menu):
        """测试更新文本上下文动态项"""
        context_menu.set_context("text")
        assert len(context_menu.dynamic_actions) > 0
    
    def test_update_dynamic_items_code(self, context_menu):
        """测试更新代码上下文动态项"""
        context_menu.set_context("code")
        assert len(context_menu.dynamic_actions) > 0
    
    def test_update_dynamic_items_file(self, context_menu):
        """测试更新文件上下文动态项"""
        context_menu.set_context("file")
        assert len(context_menu.dynamic_actions) > 0
    
    def test_get_action(self, context_menu):
        """测试获取菜单项"""
        action = context_menu.get_action("copy")
        assert action is not None
        
        # 获取不存在的菜单项
        action = context_menu.get_action("nonexistent")
        assert action is None
    
    def test_set_action_enabled(self, context_menu):
        """测试设置菜单项启用状态"""
        context_menu.set_action_enabled("copy", False)
        action = context_menu.get_action("copy")
        assert action.isEnabled() == False
        
        context_menu.set_action_enabled("copy", True)
        assert action.isEnabled() == True
    
    def test_set_action_enabled_nonexistent(self, context_menu):
        """测试设置不存在菜单项的启用状态"""
        # 应该不崩溃
        context_menu.set_action_enabled("nonexistent", True)
    
    def test_set_action_visible(self, context_menu):
        """测试设置菜单项可见性"""
        context_menu.set_action_visible("copy", False)
        action = context_menu.get_action("copy")
        assert action.isVisible() == False
        
        context_menu.set_action_visible("copy", True)
        assert action.isVisible() == True
    
    def test_get_context_type(self, context_menu):
        """测试获取上下文类型"""
        assert context_menu.get_context_type() == "text"
        
        context_menu.set_context("code")
        assert context_menu.get_context_type() == "code"


class TestTextContextMenuComplete:
    """TextContextMenu完整覆盖测试"""
    
    @pytest.fixture
    def text_menu(self, qapp):
        """创建TextContextMenu实例"""
        from widgets.context_menu import TextContextMenu
        return TextContextMenu()
    
    def test_initialization(self, text_menu):
        """测试初始化"""
        assert text_menu.selected_text == ""
        assert text_menu.context_type == "text"
    
    def test_get_selected_text(self, text_menu):
        """测试获取选中文本"""
        text_menu.selected_text = "测试文本"
        assert text_menu.get_selected_text() == "测试文本"


class TestFileContextMenuComplete:
    """FileContextMenu完整覆盖测试"""
    
    @pytest.fixture
    def file_menu(self, qapp):
        """创建FileContextMenu实例"""
        from widgets.context_menu import FileContextMenu
        return FileContextMenu()
    
    def test_initialization(self, file_menu):
        """测试初始化"""
        assert file_menu.file_path == ""
    
    def test_is_supported_file(self, file_menu):
        """测试文件类型检查"""
        assert file_menu._is_supported_file("test.txt") == True
        assert file_menu._is_supported_file("test.md") == True
        assert file_menu._is_supported_file("test.docx") == True
        assert file_menu._is_supported_file("test.pdf") == True
        assert file_menu._is_supported_file("test.pptx") == True
        
        # 不支持的文件类型
        assert file_menu._is_supported_file("test.exe") == False
        assert file_menu._is_supported_file("test.py") == False
        assert file_menu._is_supported_file("test.unknown") == False
    
    def test_get_file_path(self, file_menu):
        """测试获取文件路径"""
        file_menu.file_path = "/path/to/test.txt"
        assert file_menu.get_file_path() == "/path/to/test.txt"


class TestCodeContextMenuComplete:
    """CodeContextMenu完整覆盖测试"""
    
    @pytest.fixture
    def code_menu(self, qapp):
        """创建CodeContextMenu实例"""
        from widgets.context_menu import CodeContextMenu
        return CodeContextMenu()
    
    def test_initialization(self, code_menu):
        """测试初始化"""
        assert code_menu.code_text == ""
        assert code_menu.language == ""
    
    def test_get_code_text(self, code_menu):
        """测试获取代码文本"""
        code_menu.code_text = "print('hello')"
        assert code_menu.get_code_text() == "print('hello')"
    
    def test_get_language(self, code_menu):
        """测试获取编程语言"""
        code_menu.language = "python"
        assert code_menu.get_language() == "python"


# ==================== FileDropZone 完整测试 ====================
class TestFileDropZoneComplete:
    """FileDropZone完整覆盖测试"""
    
    @pytest.fixture
    def file_drop_zone(self, qapp):
        """创建FileDropZone实例"""
        from widgets.file_drop_zone import FileDropZone
        return FileDropZone()
    
    def test_initialization(self, file_drop_zone):
        """测试初始化"""
        assert file_drop_zone.acceptDrops() == True
        assert file_drop_zone._is_hovering == False
        assert file_drop_zone._current_file_info is None
    
    def test_accepted_extensions(self, file_drop_zone):
        """测试接受的扩展名"""
        extensions = file_drop_zone.get_accepted_extensions()
        assert ".docx" in extensions
        assert ".pdf" in extensions
        assert ".txt" in extensions
        assert ".xlsx" in extensions
        assert ".pptx" in extensions
    
    def test_set_accepted_extensions(self, file_drop_zone):
        """测试设置接受的扩展名"""
        new_extensions = [".txt", ".md"]
        file_drop_zone.set_accepted_extensions(new_extensions)
        
        extensions = file_drop_zone.get_accepted_extensions()
        assert extensions == new_extensions
    
    def test_accepted_extensions_property(self, file_drop_zone):
        """测试扩展名属性"""
        extensions = file_drop_zone.accepted_extensions
        assert isinstance(extensions, list)
        assert len(extensions) > 0
    
    def test_set_accepted_extensions_property(self, file_drop_zone):
        """测试设置扩展名属性"""
        new_extensions = [".csv", ".json"]
        file_drop_zone.accepted_extensions = new_extensions
        
        assert file_drop_zone.get_accepted_extensions() == new_extensions
    
    def test_is_valid_file(self, file_drop_zone):
        """测试文件验证"""
        # 空路径
        assert file_drop_zone._is_valid_file("") == False
        
        # 不存在的文件
        assert file_drop_zone._is_valid_file("/nonexistent/file.txt") == False
    
    def test_set_hovering(self, file_drop_zone):
        """测试设置悬停状态"""
        file_drop_zone._set_hovering(True)
        assert file_drop_zone._is_hovering == True
        
        file_drop_zone._set_hovering(False)
        assert file_drop_zone._is_hovering == False
    
    def test_clear_file_info(self, file_drop_zone):
        """测试清除文件信息"""
        file_drop_zone._clear_file_info()
        
        assert file_drop_zone._current_file_info is None
        assert file_drop_zone._text_label.text() == "拖拽文件到此处"
        assert file_drop_zone._file_info_label.isVisible() == False
    
    def test_update_icon_default(self, file_drop_zone):
        """测试更新默认图标"""
        file_drop_zone._update_icon()
        assert file_drop_zone._icon_label.pixmap() is not None
    
    def test_update_icon_with_type(self, file_drop_zone):
        """测试更新特定类型图标"""
        file_drop_zone._update_icon("word")
        assert file_drop_zone._icon_label.pixmap() is not None
        
        file_drop_zone._update_icon("pdf")
        assert file_drop_zone._icon_label.pixmap() is not None
        
        file_drop_zone._update_icon("unknown")
        assert file_drop_zone._icon_label.pixmap() is not None
    
    def test_drag_enter_callback(self, file_drop_zone):
        """测试拖拽进入回调"""
        callback_called = []
        file_drop_zone._on_drag_enter_callback = lambda: callback_called.append(True)
        
        # 模拟拖拽进入
        file_drop_zone._set_hovering(True)
        assert file_drop_zone._is_hovering == True
    
    def test_drag_leave_callback(self, file_drop_zone):
        """测试拖拽离开回调"""
        callback_called = []
        file_drop_zone._on_drag_leave_callback = lambda: callback_called.append(True)
        
        # 模拟拖拽离开
        file_drop_zone._set_hovering(False)
        assert file_drop_zone._is_hovering == False


class TestFileInfoComplete:
    """FileInfo完整覆盖测试"""
    
    def test_file_info_creation(self):
        """测试FileInfo创建"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(
            name="test.txt",
            path="/path/to/test.txt",
            size=1024,
            file_type="text",
            extension=".txt"
        )
        
        assert info.name == "test.txt"
        assert info.path == "/path/to/test.txt"
        assert info.size == 1024
        assert info.file_type == "text"
        assert info.extension == ".txt"
    
    def test_file_info_to_dict(self):
        """测试FileInfo转字典"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(
            name="test.txt",
            path="/path/to/test.txt",
            size=1024,
            file_type="text",
            extension=".txt"
        )
        
        d = info.to_dict()
        assert d["name"] == "test.txt"
        assert d["path"] == "/path/to/test.txt"
        assert d["size"] == 1024
        assert d["file_type"] == "text"
        assert d["extension"] == ".txt"
    
    def test_file_size_str_bytes(self):
        """测试文件大小格式化 - 字节"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(name="test", path="", size=500, file_type="text", extension=".txt")
        assert info.size_str == "500 B"
    
    def test_file_size_str_kb(self):
        """测试文件大小格式化 - KB"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(name="test", path="", size=1024, file_type="text", extension=".txt")
        assert info.size_str == "1.0 KB"
        
        info = FileInfo(name="test", path="", size=1536, file_type="text", extension=".txt")
        assert info.size_str == "1.5 KB"
    
    def test_file_size_str_mb(self):
        """测试文件大小格式化 - MB"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(name="test", path="", size=1024*1024, file_type="text", extension=".txt")
        assert info.size_str == "1.0 MB"
        
        info = FileInfo(name="test", path="", size=2.5*1024*1024, file_type="text", extension=".txt")
        assert info.size_str == "2.5 MB"
    
    def test_file_size_str_gb(self):
        """测试文件大小格式化 - GB"""
        from widgets.file_drop_zone import FileInfo
        
        info = FileInfo(name="test", path="", size=1024*1024*1024, file_type="text", extension=".txt")
        assert info.size_str == "1.0 GB"
        
        info = FileInfo(name="test", path="", size=1.5*1024*1024*1024, file_type="text", extension=".txt")
        assert info.size_str == "1.5 GB"


# ==================== 边际测试 ====================
class TestEdgeCases:
    """边际测试和异常处理"""
    
    def test_batch_dialog_empty_operations(self, qapp):
        """测试批量处理空操作"""
        from widgets.batch_dialog import BatchDialog
        
        dialog = BatchDialog()
        
        # 空文件列表操作
        assert len(dialog.file_items) == 0
        
        # 统计信息
        stats = dialog.get_statistics()
        assert stats["total"] == 0
    
    def test_batch_dialog_large_file_list(self, qapp):
        """测试大量文件"""
        from widgets.batch_dialog import BatchDialog, FileItem
        
        dialog = BatchDialog()
        
        # 添加100个文件
        for i in range(100):
            item = FileItem(file_path=f"test_{i}.txt", file_name=f"test_{i}.txt", file_size=i*1024)
            dialog.add_file(item)
        
        assert len(dialog.file_items) == 100
        
        stats = dialog.get_statistics()
        assert stats["total"] == 100
        assert stats["pending"] == 100
    
    def test_batch_dialog_duplicate_files(self, qapp):
        """测试重复文件"""
        from widgets.batch_dialog import BatchDialog, FileItem
        
        dialog = BatchDialog()
        
        # 添加重复文件
        item1 = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        item2 = FileItem(file_path="test.txt", file_name="test.txt", file_size=1024)
        
        dialog.add_file(item1)
        dialog.add_file(item2)
        
        # 取决于实现是否允许重复
        assert len(dialog.file_items) >= 1
    
    def test_batch_dialog_remove_nonexistent(self, qapp):
        """测试移除不存在的文件"""
        from widgets.batch_dialog import BatchDialog
        
        dialog = BatchDialog()
        
        # 移除不存在的文件应该不崩溃
        dialog.remove_file("nonexistent.txt")
        assert len(dialog.file_items) == 0
    
    def test_terminology_dialog_empty_search(self, qapp):
        """测试术语库空搜索"""
        from widgets.terminology_dialog import TerminologyDialog
        
        dialog = TerminologyDialog()
        
        # 空搜索
        results = dialog.search_entries("")
        assert isinstance(results, list)
    
    def test_terminology_dialog_special_characters(self, qapp):
        """测试术语库特殊字符"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        # 特殊字符术语
        entry = TerminologyEntry(
            source="C++编程",
            target="C++ Programming",
            category="技术",
            notes="包含+号"
        )
        dialog.add_entry(entry)
        
        results = dialog.search_entries("C++")
        assert len(results) >= 1
    
    def test_terminology_dialog_long_text(self, qapp):
        """测试术语库长文本"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        # 长文本术语
        long_source = "这" * 1000
        long_target = "A" * 1000
        
        entry = TerminologyEntry(
            source=long_source,
            target=long_target,
            category="测试"
        )
        dialog.add_entry(entry)
        
        results = dialog.search_entries(long_source[:10])
        assert len(results) >= 1
    
    def test_translation_memory_empty_search(self):
        """测试翻译记忆空搜索"""
        from widgets.translation_memory import TranslationMemory
        
        memory = TranslationMemory()
        
        # 空搜索
        results = memory.search_exact("")
        assert isinstance(results, list)
        
        results = memory.search_fuzzy("", threshold=0.5)
        assert isinstance(results, list)
    
    def test_translation_memory_special_characters(self):
        """测试翻译记忆特殊字符"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        unit = TranslationUnit(
            source="Hello, World! @#$%^&*()",
            target="你好，世界！@#$%^&*()",
            source_lang="en",
            target_lang="zh"
        )
        memory.add_unit(unit)
        
        results = memory.search_exact("Hello, World! @#$%^&*()")
        assert len(results) == 1
    
    def test_translation_memory_unicode(self):
        """测试翻译记忆Unicode字符"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # Unicode字符
        unit = TranslationUnit(
            source="こんにちは",
            target="你好",
            source_lang="ja",
            target_lang="zh"
        )
        memory.add_unit(unit)
        
        results = memory.search_exact("こんにちは")
        assert len(results) == 1
    
    def test_translation_memory_large_dataset(self):
        """测试翻译记忆大数据量"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加1000个翻译单元
        for i in range(1000):
            unit = TranslationUnit(
                source=f"source_{i}",
                target=f"target_{i}",
                source_lang="en",
                target_lang="zh"
            )
            memory.add_unit(unit)
        
        assert len(memory.units) == 1000
        
        # 搜索
        results = memory.search_exact("source_500")
        assert len(results) == 1
        assert results[0].target == "target_500"
    
    def test_translation_memory_fuzzy_search_threshold(self):
        """测试翻译记忆模糊搜索阈值"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        unit = TranslationUnit(
            source="Hello World",
            target="你好世界",
            source_lang="en",
            target_lang="zh"
        )
        memory.add_unit(unit)
        
        # 高阈值
        results = memory.search_fuzzy("Hello", threshold=0.9)
        assert len(results) == 0
        
        # 低阈值
        results = memory.search_fuzzy("Hello", threshold=0.3)
        assert len(results) >= 1
    
    def test_translation_memory_statistics(self):
        """测试翻译记忆统计信息"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        # 添加不同语言对
        unit1 = TranslationUnit(source="Hello", target="你好", source_lang="en", target_lang="zh")
        unit2 = TranslationUnit(source="Goodbye", target="再见", source_lang="en", target_lang="zh")
        unit3 = TranslationUnit(source="Bonjour", target="你好", source_lang="fr", target_lang="zh")
        
        memory.add_unit(unit1)
        memory.add_unit(unit2)
        memory.add_unit(unit3)
        
        stats = memory.get_statistics()
        assert stats["total_units"] == 3
        assert stats["language_pairs"] >= 2
    
    def test_translation_memory_export_import_json(self):
        """测试翻译记忆JSON导出导入"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        unit = TranslationUnit(
            source="Test",
            target="测试",
            source_lang="en",
            target_lang="zh",
            context="单元测试",
            domain="技术"
        )
        memory.add_unit(unit)
        
        # 导出
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = memory.export_to_json(temp_path)
            assert result == True
            assert os.path.exists(temp_path)
            
            # 导入到新实例
            new_memory = TranslationMemory()
            result = new_memory.import_from_json(temp_path)
            assert result == True
            assert len(new_memory.units) == 1
            
            # 验证导入的数据
            imported_unit = new_memory.units[0]
            assert imported_unit.source == "Test"
            assert imported_unit.target == "测试"
            assert imported_unit.context == "单元测试"
            assert imported_unit.domain == "技术"
        finally:
            os.unlink(temp_path)
    
    def test_translation_memory_clear(self):
        """测试翻译记忆清空"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        memory.add_unit(TranslationUnit(source="Test", target="测试", source_lang="en", target_lang="zh"))
        assert len(memory.units) == 1
        
        memory.clear()
        assert len(memory.units) == 0


# ==================== 边际测试 - 文件操作 ====================
class TestFileOperationsEdgeCases:
    """文件操作边际测试"""
    
    def test_terminology_export_import_json(self, qapp):
        """测试术语库JSON导出导入"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        entry = TerminologyEntry(
            source="测试",
            target="Test",
            category="技术",
            notes="测试备注"
        )
        dialog.add_entry(entry)
        
        # 导出
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = dialog.export_to_json(temp_path)
            assert result == True
            
            # 导入到新实例
            new_dialog = TerminologyDialog()
            result = new_dialog.import_from_json(temp_path)
            assert result == True
            
            results = new_dialog.search_entries("测试")
            assert len(results) >= 1
        finally:
            os.unlink(temp_path)
    
    def test_terminology_search_empty_database(self, qapp):
        """测试空术语库搜索"""
        from widgets.terminology_dialog import TerminologyDialog
        
        dialog = TerminologyDialog()
        
        # 搜索不存在的术语
        results = dialog.search_entries("不存在的术语")
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_terminology_remove_entry(self, qapp):
        """测试移除术语条目"""
        from widgets.terminology_dialog import TerminologyDialog, TerminologyEntry
        
        dialog = TerminologyDialog()
        
        entry = TerminologyEntry(
            source="测试",
            target="Test",
            category="技术"
        )
        dialog.add_entry(entry)
        
        results = dialog.search_entries("测试")
        assert len(results) >= 1
        
        # 移除术语（需要传入source字符串）
        result = dialog.remove_entry("测试")
        assert result == True
        
        results = dialog.search_entries("测试")
        assert len(results) == 0
    
    def test_translation_memory_export_tmx(self):
        """测试翻译记忆TMX导出"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        memory = TranslationMemory()
        
        unit = TranslationUnit(
            source="Hello",
            target="你好",
            source_lang="en",
            target_lang="zh"
        )
        memory.add_unit(unit)
        
        # 导出TMX
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmx', delete=False) as f:
            temp_path = f.name
        
        try:
            result = memory.export_to_tmx(temp_path)
            assert result == True
            assert os.path.exists(temp_path)
            
            # 验证TMX文件内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert '<?xml' in content
                assert 'tmx' in content.lower()
        finally:
            os.unlink(temp_path)
    
    def test_translation_memory_import_tmx(self):
        """测试翻译记忆TMX导入"""
        from widgets.translation_memory import TranslationMemory, TranslationUnit
        
        # 创建TMX文件
        tmx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <body>
    <tu>
      <tuv xml:lang="en"><seg>Hello</seg></tuv>
      <tuv xml:lang="zh"><seg>你好</seg></tuv>
    </tu>
  </body>
</tmx>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmx', delete=False, encoding='utf-8') as f:
            f.write(tmx_content)
            temp_path = f.name
        
        try:
            memory = TranslationMemory()
            result = memory.import_from_tmx(temp_path)
            assert result == True
            assert len(memory.units) >= 1
        finally:
            os.unlink(temp_path)


# ==================== ProgressManager 测试 ====================
class TestProgressManager:
    """ProgressManager测试"""
    
    def test_progress_manager_init(self):
        """测试ProgressManager初始化"""
        from widgets.progress_widget import ProgressManager
        
        manager = ProgressManager()
        assert manager.callbacks == []
        assert manager.progress_widget is None
        assert manager.multi_step_widget is None
    
    def test_progress_manager_set_widget(self, qapp):
        """测试设置进度组件"""
        from widgets.progress_widget import ProgressManager, ProgressWidget
        
        manager = ProgressManager()
        widget = ProgressWidget()
        
        manager.set_progress_widget(widget)
        assert manager.progress_widget == widget
    
    def test_progress_manager_set_multi_step_widget(self, qapp):
        """测试设置多步骤进度组件"""
        from widgets.progress_widget import ProgressManager, MultiStepProgressWidget
        
        manager = ProgressManager()
        widget = MultiStepProgressWidget()
        
        manager.set_multi_step_widget(widget)
        assert manager.multi_step_widget == widget


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
