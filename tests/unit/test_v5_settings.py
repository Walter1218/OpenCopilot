"""V5 Settings Dialog 非AI事件链测试 — 4 分区保存/加载/切换/重置

覆盖:
- Engine 分区: Save / TestConnection
- Appearance 分区: Theme 切换 / FontSize 滑动
- Shortcuts 分区: Load / Save
- Advanced 分区: Export / Import / Reset
- 导航切换
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_nav():
    return MagicMock()


@pytest.fixture
def settings_dialog(qapp, mock_nav):
    """创建 SettingsDialogV5 实例，mock 所有 bridge 调用"""
    with patch("gui.v5.bridge.get_config", return_value={
        "provider_type": "cloud",
        "cloud_api_key": "sk-test",
        "cloud_model": "MiniMax-M1",
        "cloud_api_base": "https://api.minimax.chat/v1",
    }), patch("gui.v5.bridge.get_appearance", return_value={
        "theme": "dark", "font_size": 12, "language": "zh",
    }), patch("gui.v5.bridge.get_shortcuts", return_value={
        "shortcuts": {
            "explain": {"key_sequence": "Cmd+E"},
            "fix": {"key_sequence": "Cmd+F"},
        }
    }):
        from gui.v5.settings_dialog import SettingsDialogV5
        dlg = SettingsDialogV5(mock_nav, initial_section="engine")
        yield dlg
        dlg.deleteLater()


# =============================================================================
# 1. 初始化与结构验证
# =============================================================================

class TestSettingsInit:
    """Settings 弹窗初始化验证"""

    def test_creation(self, settings_dialog):
        """SettingsDialogV5 应能正常创建"""
        assert settings_dialog is not None
        assert settings_dialog.windowTitle() == "Settings"

    def test_has_4_nav_buttons(self, settings_dialog):
        """应有 4 个导航按钮"""
        from gui.v5.tokens import SETTINGS_SECTIONS
        assert len(settings_dialog._nav_buttons) == len(SETTINGS_SECTIONS)
        for sid, _, _ in SETTINGS_SECTIONS:
            assert sid in settings_dialog._nav_buttons

    def test_initial_section_is_engine(self, settings_dialog):
        """初始分区应是 engine"""
        assert settings_dialog._stack.currentIndex() == 0

    def test_select_section_appearance(self, settings_dialog):
        """select_section 应跳转到对应分区"""
        settings_dialog.select_section("appearance")
        assert settings_dialog._stack.currentIndex() == 1

    def test_select_section_shortcuts(self, settings_dialog):
        settings_dialog.select_section("shortcuts")
        assert settings_dialog._stack.currentIndex() == 2

    def test_select_section_advanced(self, settings_dialog):
        settings_dialog.select_section("advanced")
        assert settings_dialog._stack.currentIndex() == 3


# =============================================================================
# 2. 导航切换
# =============================================================================

class TestNavSwitch:
    """导航按钮切换事件"""

    def test_nav_click_switches_panel(self, settings_dialog):
        """点击导航按钮应切换面板"""
        # Click index 1 (appearance)
        settings_dialog._on_nav_clicked(1)
        assert settings_dialog._stack.currentIndex() == 1

    def test_nav_click_highlights_button(self, settings_dialog):
        """切换后对应按钮应 checked"""
        settings_dialog._on_nav_clicked(1)
        appearance_btn = settings_dialog._nav_buttons["appearance"]
        assert appearance_btn.isChecked() is True
        engine_btn = settings_dialog._nav_buttons["engine"]
        assert engine_btn.isChecked() is False

    def test_nav_click_all_sections(self, settings_dialog):
        """所有 4 个分区切换都应正常工作"""
        from gui.v5.tokens import SETTINGS_SECTIONS
        for idx, (sid, _, _) in enumerate(SETTINGS_SECTIONS):
            settings_dialog._on_nav_clicked(idx)
            assert settings_dialog._stack.currentIndex() == idx
            assert settings_dialog._nav_buttons[sid].isChecked() is True


# =============================================================================
# 3. Engine 分区
# =============================================================================

class TestEngineSection:
    """Engine 分区: Save / TestConnection"""

    def test_save_engine_success(self, settings_dialog):
        """保存引擎配置成功应显示 Saved"""
        with patch("gui.v5.bridge.save_engine_config", return_value=True):
            settings_dialog._on_save_engine()
        status = settings_dialog._engine_status.text()
        assert "Saved" in status

    def test_save_engine_failure(self, settings_dialog):
        """保存引擎配置失败应显示 Save Failed"""
        with patch("gui.v5.bridge.save_engine_config", return_value=False):
            settings_dialog._on_save_engine()
        status = settings_dialog._engine_status.text()
        assert "Failed" in status

    def test_save_engine_provider_detection_cloud(self, settings_dialog):
        """Backend index=0 应识别为 cloud"""
        settings_dialog._engine_backend.setCurrentIndex(0)
        with patch("gui.v5.bridge.save_engine_config", return_value=True) as mock_save:
            settings_dialog._on_save_engine()
        call_args = mock_save.call_args
        assert call_args[0][0] == "cloud"

    def test_save_engine_provider_detection_local(self, settings_dialog):
        """Backend index=1 应识别为 local"""
        settings_dialog._engine_backend.setCurrentIndex(1)
        with patch("gui.v5.bridge.save_engine_config", return_value=True) as mock_save:
            settings_dialog._on_save_engine()
        call_args = mock_save.call_args
        assert call_args[0][0] == "local"

    def test_test_connection_starts_worker(self, settings_dialog):
        """Test Connection 应启动异步 worker"""
        settings_dialog._engine_backend.setCurrentIndex(0)
        settings_dialog._engine_api_base.setText("https://api.test.com/v1")
        settings_dialog._engine_api_key.setText("sk-test")
        settings_dialog._engine_model.setText("test-model")

        with patch("gui.v5.settings_dialog._TestConnectionWorker") as MockWorker:
            mock_worker = MagicMock()
            MockWorker.return_value = mock_worker
            settings_dialog._on_test_connection()

        assert settings_dialog._engine_status.text() == "● Testing..."
        mock_worker.start.assert_called_once()


# =============================================================================
# 4. Appearance 分区
# =============================================================================

class TestAppearanceSection:
    """Appearance 分区: Theme / FontSize"""

    def test_theme_switch_to_light(self, settings_dialog):
        """切换到 Light 主题"""
        with patch("gui.v5.bridge.save_appearance", return_value=True):
            settings_dialog._on_theme_clicked("Light")
        assert settings_dialog._theme_buttons["light"].isChecked() is True
        assert settings_dialog._theme_buttons["dark"].isChecked() is False

    def test_theme_switch_to_system(self, settings_dialog):
        """切换到 System 主题"""
        with patch("gui.v5.bridge.save_appearance", return_value=True):
            settings_dialog._on_theme_clicked("System")
        assert settings_dialog._theme_buttons["system"].isChecked() is True

    def test_theme_switch_saves(self, settings_dialog):
        """切换主题应调用 bridge.save_appearance"""
        with patch("gui.v5.bridge.save_appearance", return_value=True) as mock_save:
            settings_dialog._on_theme_clicked("Dark")
        mock_save.assert_called_once_with(theme="dark")

    def test_font_size_change(self, settings_dialog):
        """字体大小变更应更新标签"""
        with patch("gui.v5.bridge.save_appearance", return_value=True):
            settings_dialog._on_font_size_changed(16)
        assert "16" in settings_dialog._font_size_label.text()

    def test_font_size_saves(self, settings_dialog):
        """字体大小变更应调用 bridge.save_appearance"""
        with patch("gui.v5.bridge.save_appearance", return_value=True) as mock_save:
            settings_dialog._on_font_size_changed(14)
        mock_save.assert_called_once_with(font_size=14)

    def test_font_slider_range(self, settings_dialog):
        """字体滑块范围应为 8-24"""
        assert settings_dialog._font_slider.minimum() == 8
        assert settings_dialog._font_slider.maximum() == 24


# =============================================================================
# 5. Shortcuts 分区
# =============================================================================

class TestShortcutsSection:
    """Shortcuts 分区: Load / Save"""

    def test_shortcuts_data_loaded(self, settings_dialog):
        """快捷键数据应在初始化时加载"""
        assert "explain" in settings_dialog._shortcuts_data
        assert settings_dialog._shortcuts_data["explain"]["key_sequence"] == "Cmd+E"

    def test_shortcut_edit_updates_data(self, settings_dialog):
        """编辑快捷键应更新内部数据"""
        settings_dialog._on_shortcut_edited("explain", "Cmd+Shift+E")
        assert settings_dialog._shortcuts_data["explain"]["key_sequence"] == "Cmd+Shift+E"

    def test_save_shortcuts_calls_bridge(self, settings_dialog):
        """保存快捷键应调用 bridge.save_shortcuts"""
        with patch("gui.v5.bridge.save_shortcuts", return_value=True) as mock_save:
            settings_dialog._on_save_shortcuts()
        mock_save.assert_called_once()

    def test_edit_nonexistent_shortcut_ignored(self, settings_dialog):
        """编辑不存在的快捷键应被忽略"""
        original = dict(settings_dialog._shortcuts_data)
        settings_dialog._on_shortcut_edited("nonexistent", "Cmd+X")
        assert settings_dialog._shortcuts_data == original


# =============================================================================
# 6. Advanced 分区
# =============================================================================

class TestAdvancedSection:
    """Advanced 分区: Export / Import / Reset"""

    def test_export_config_success(self, settings_dialog):
        """导出配置成功"""
        with patch("gui.v5.bridge.do_export_config") as mock_export:
            mock_export.return_value = {
                "success": True,
                "file_path": "/tmp/opencopilot_config_test.json",
            }
            settings_dialog._on_export_config()
        mock_export.assert_called_once()

    def test_export_config_failure(self, settings_dialog):
        """导出配置失败不应崩溃"""
        with patch("gui.v5.bridge.do_export_config") as mock_export:
            mock_export.return_value = {"success": False, "message": "config not found"}
            settings_dialog._on_export_config()  # Should not raise
        mock_export.assert_called_once()

    def test_reset_all_success(self, settings_dialog):
        """重置所有配置成功"""
        with patch("gui.v5.bridge.do_reset_config") as mock_reset:
            mock_reset.return_value = {
                "success": True,
                "reset_sections": ["agent", "llm", "concurrency", "web_search", "appearance"],
            }
            settings_dialog._on_reset_all()
        mock_reset.assert_called_once_with("")

    def test_reset_all_failure(self, settings_dialog):
        """重置失败不应崩溃"""
        with patch("gui.v5.bridge.do_reset_config") as mock_reset:
            mock_reset.return_value = {"success": False, "message": "error"}
            settings_dialog._on_reset_all()  # Should not raise
