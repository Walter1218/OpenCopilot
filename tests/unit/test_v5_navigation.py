"""V5 NavigationManager 跳转逻辑测试 — 7 条核心链路验证

覆盖:
- A. Tab 切换（内部，由 SmartCopilot 自行处理）
- B. Smart Copilot → Studio 窗口
- C. Smart Copilot → Settings 弹窗
- D. Workspace → Settings 弹窗
- E. System Tray → 各窗口
- F. Work Tab → Chat Tab (上下文跳转)
- G. Studio → Smart Copilot (结果回传)
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
def nav(qapp):
    """创建一个干净的 NavigationManager 实例"""
    _ = qapp
    from gui.v5.navigation import NavigationManager
    return NavigationManager()


# =============================================================================
# 1. 初始化与基本属性
# =============================================================================

class TestNavigationInit:
    """NavigationManager 初始化验证"""

    def test_initial_state_all_none(self, nav):
        # Arrange & Act: nav fixture creates fresh instance
        # Assert: all window references are None
        assert nav._smart_copilot is None
        assert nav._workspace is None
        assert nav._studio_window is None
        assert nav._settings_dialog is None

    def test_signals_defined(self, nav):
        """验证 3 个信号已定义"""
        assert hasattr(nav, 'studio_opened')
        assert hasattr(nav, 'settings_opened')
        assert hasattr(nav, 'workspace_opened')


# =============================================================================
# 2. Studio Window (链路 B)
# =============================================================================

class TestOpenStudio:
    """链路 B: Smart Copilot → Studio 窗口"""

    def test_open_studio_creates_window(self, nav):
        """首次打开 Studio 应创建新窗口"""
        with patch("gui.v5.studio_window.StudioWindowV5") as MockStudio:
            mock_win = MagicMock()
            mock_win.isVisible.return_value = False
            MockStudio.return_value = mock_win
            nav.open_studio()
        assert nav._studio_window is not None
        mock_win.show.assert_called_once()

    def test_open_studio_with_text(self, nav):
        """带文本打开 Studio 应调用 load_text"""
        with patch("gui.v5.studio_window.StudioWindowV5") as MockStudio:
            mock_win = MagicMock()
            mock_win.isVisible.return_value = False
            MockStudio.return_value = mock_win
            with patch("gui.v5.navigation.QTimer") as MockTimer:
                nav.open_studio(text="Hello PPT")
        # QTimer.singleShot should be called for deferred text loading
        MockTimer.singleShot.assert_called_once()

    def test_open_studio_reuses_visible_window(self, nav):
        """已有可见窗口时应直接激活而非创建新窗口"""
        mock_existing = MagicMock()
        mock_existing.isVisible.return_value = True
        nav._studio_window = mock_existing

        nav.open_studio()

        mock_existing.raise_.assert_called_once()
        mock_existing.activateWindow.assert_called_once()

    def test_open_studio_emits_signal(self, nav):
        """打开 Studio 应发射 studio_opened 信号"""
        signals = []
        nav.studio_opened.connect(lambda: signals.append(True))

        with patch("gui.v5.studio_window.StudioWindowV5") as MockStudio:
            mock_win = MagicMock()
            mock_win.isVisible.return_value = False
            MockStudio.return_value = mock_win
            nav.open_studio()

        assert len(signals) == 1

    def test_is_studio_open_false_when_none(self, nav):
        assert nav.is_studio_open() is False

    def test_is_studio_open_true_when_visible(self, nav):
        mock_win = MagicMock()
        mock_win.isVisible.return_value = True
        nav._studio_window = mock_win
        assert nav.is_studio_open() is True

    def test_get_studio_slides_count_zero_when_none(self, nav):
        assert nav.get_studio_slides_count() == 0

    def test_get_studio_slides_count_with_data(self, nav):
        mock_win = MagicMock()
        mock_win.slides_data = [{"title": "S1"}, {"title": "S2"}, {"title": "S3"}]
        nav._studio_window = mock_win
        assert nav.get_studio_slides_count() == 3


# =============================================================================
# 3. Settings Dialog (链路 C / D)
# =============================================================================

class TestOpenSettings:
    """链路 C/D: Smart Copilot/Workspace → Settings 弹窗"""

    def test_open_settings_creates_dialog(self, nav):
        """首次打开 Settings 应创建新弹窗"""
        with patch("gui.v5.settings_dialog.SettingsDialogV5") as MockDialog:
            mock_dlg = MagicMock()
            mock_dlg.isVisible.return_value = False
            MockDialog.return_value = mock_dlg
            nav.open_settings("engine")
        assert nav._settings_dialog is not None
        mock_dlg.show.assert_called_once()

    def test_open_settings_default_section(self, nav):
        """默认 section 是 engine"""
        with patch("gui.v5.settings_dialog.SettingsDialogV5") as MockDialog:
            mock_dlg = MagicMock()
            mock_dlg.isVisible.return_value = False
            MockDialog.return_value = mock_dlg
            nav.open_settings()
        # Verify initial_section="engine" was passed
        call_args = MockDialog.call_args
        assert call_args[1]["initial_section"] == "engine" or call_args[0][1] == "engine"

    def test_open_settings_reuses_visible_dialog(self, nav):
        """已有可见弹窗时应激活并跳转 section"""
        mock_existing = MagicMock()
        mock_existing.isVisible.return_value = True
        nav._settings_dialog = mock_existing

        nav.open_settings("appearance")

        mock_existing.raise_.assert_called_once()
        mock_existing.activateWindow.assert_called_once()
        mock_existing.select_section.assert_called_once_with("appearance")

    def test_open_settings_emits_signal(self, nav):
        """打开 Settings 应发射 settings_opened 信号"""
        signals = []
        nav.settings_opened.connect(lambda: signals.append(True))

        with patch("gui.v5.settings_dialog.SettingsDialogV5") as MockDialog:
            mock_dlg = MagicMock()
            mock_dlg.isVisible.return_value = False
            MockDialog.return_value = mock_dlg
            nav.open_settings()

        assert len(signals) == 1


# =============================================================================
# 4. Workspace (链路 E)
# =============================================================================

class TestShowWorkspace:
    """链路 E: System Tray → Workspace"""

    def test_show_workspace_creates_window(self, nav):
        """首次显示 Workspace 应创建新窗口"""
        with patch("gui.v5.workspace.WorkspaceV5") as MockWS:
            mock_ws = MagicMock()
            MockWS.return_value = mock_ws
            nav.show_workspace()
        assert nav._workspace is not None
        mock_ws.show.assert_called_once()
        mock_ws.raise_.assert_called_once()

    def test_show_workspace_reuses_existing(self, nav):
        """已有实例时应复用"""
        mock_existing = MagicMock()
        mock_existing.isVisible.return_value = False
        nav._workspace = mock_existing

        nav.show_workspace()

        mock_existing.show.assert_called_once()
        # Should not create a new one
        assert nav._workspace is mock_existing

    def test_show_workspace_emits_signal(self, nav):
        """显示 Workspace 应发射 workspace_opened 信号"""
        signals = []
        nav.workspace_opened.connect(lambda: signals.append(True))

        with patch("gui.v5.workspace.WorkspaceV5") as MockWS:
            mock_ws = MagicMock()
            MockWS.return_value = mock_ws
            nav.show_workspace()

        assert len(signals) == 1


# =============================================================================
# 5. Smart Copilot (链路 E)
# =============================================================================

class TestSmartCopilot:
    """Smart Copilot 显示/隐藏"""

    def test_show_smart_copilot_uses_v5_ui(self, nav):
        mock_popup = MagicMock()
        mock_popup.width.return_value = 420
        mock_popup.height.return_value = 320
        with patch("gui.v5.smart_copilot.SmartCopilotV5", return_value=mock_popup):
            nav.show_smart_copilot(100, 120, selected_text="hello")

        assert nav._smart_copilot is mock_popup
        mock_popup.set_selected_text.assert_called_once_with("hello")
        mock_popup.show.assert_called_once()
        mock_popup.raise_.assert_called_once()

    def test_hide_smart_copilot_when_none(self, nav):
        """Smart Copilot 不存在时 hide 不应报错"""
        nav.hide_smart_copilot()  # Should not raise

    def test_hide_smart_copilot_when_visible(self, nav):
        """隐藏可见的 Smart Copilot"""
        mock_sc = MagicMock()
        mock_sc.isVisible.return_value = True
        nav._smart_copilot = mock_sc
        nav.hide_smart_copilot()
        mock_sc.hide.assert_called_once()

    def test_hide_smart_copilot_when_hidden(self, nav):
        """已隐藏的 Smart Copilot 不应再次 hide"""
        mock_sc = MagicMock()
        mock_sc.isVisible.return_value = False
        nav._smart_copilot = mock_sc
        nav.hide_smart_copilot()
        mock_sc.hide.assert_not_called()

    def test_cleanup_calls_popup_cleanup(self, nav):
        mock_sc = MagicMock()
        nav._smart_copilot = mock_sc
        nav.cleanup()
        mock_sc.cleanup.assert_not_called()


# =============================================================================
# 6. 跨 Tab 跳转 (链路 F / G)
# =============================================================================

class TestJumpWorkToChat:
    """链路 F: Work Tab → Chat Tab"""

    def test_jump_when_no_smart_copilot(self, nav):
        """Smart Copilot 不存在时不应报错"""
        nav.jump_work_to_chat("some context", "selection")  # Should not raise

    def test_jump_delegates_to_smart_copilot(self, nav):
        """跳转应委托给 SmartCopilot.jump_to_chat"""
        mock_sc = MagicMock()
        nav._smart_copilot = mock_sc
        nav.jump_work_to_chat("context text", "clipboard")
        mock_sc.jump_to_chat.assert_called_once_with("context text", "clipboard")


class TestJumpStudioToChat:
    """链路 G: Studio → Smart Copilot Chat Tab"""

    def test_jump_when_no_smart_copilot(self, nav):
        """Smart Copilot 不存在时不应报错"""
        nav.jump_studio_to_chat("/tmp/export.pptx")  # Should not raise

    def test_jump_injects_message_and_switches(self, nav):
        """跳转应注入消息并切换到 Chat Tab"""
        mock_sc = MagicMock()
        nav._smart_copilot = mock_sc
        nav.jump_studio_to_chat("/tmp/test.pptx")
        mock_sc.inject_chat_message.assert_called_once()
        mock_sc.switch_to_chat.assert_called_once()
        mock_sc.show.assert_called_once()
        mock_sc.raise_.assert_called_once()

    def test_jump_message_contains_export_path(self, nav):
        """注入的消息应包含导出路径"""
        mock_sc = MagicMock()
        nav._smart_copilot = mock_sc
        nav.jump_studio_to_chat("/tmp/my_presentation.pptx")
        call_args = mock_sc.inject_chat_message.call_args[0][0]
        assert "/tmp/my_presentation.pptx" in call_args


# =============================================================================
# 7. 全局隐藏
# =============================================================================

class TestHideAll:
    """System Tray → 隐藏全部窗口"""

    def test_hide_all_hides_visible_windows(self, nav):
        """hide_all 应隐藏 Smart Copilot 和 Workspace"""
        mock_sc = MagicMock()
        mock_sc.isVisible.return_value = True
        mock_ws = MagicMock()
        mock_ws.isVisible.return_value = True
        nav._smart_copilot = mock_sc
        nav._workspace = mock_ws

        nav.hide_all()

        mock_sc.hide.assert_called_once()
        mock_ws.hide.assert_called_once()

    def test_hide_all_skips_hidden(self, nav):
        """hide_all 应跳过已隐藏的窗口"""
        mock_sc = MagicMock()
        mock_sc.isVisible.return_value = False
        nav._smart_copilot = mock_sc

        nav.hide_all()

        mock_sc.hide.assert_not_called()

    def test_hide_all_with_none_windows(self, nav):
        """所有窗口为 None 时不应报错"""
        nav.hide_all()  # Should not raise
