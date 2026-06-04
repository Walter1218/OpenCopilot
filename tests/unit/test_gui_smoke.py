"""GUI 冒烟测试 — 验证窗口创建/销毁/基本交互。

使用 QT_QPA_PLATFORM=offscreen 在无头环境中运行。
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt6.QtCore import Qt, QPoint, QMimeData, QUrl
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_provider():
    """创建 mock LLM provider"""
    provider = MagicMock()
    provider.stream_agent_task.return_value = iter([])
    return provider


# =========================================
# 1. AICardWindow 冒烟测试
# =========================================
class TestAICardWindowStructure:
    """悬浮卡片结构验证（不创建实例，避免 offscreen 模式崩溃）"""

    def test_module_importable(self, qapp, qtbot):
        """gui.window 模块应可正常导入"""
        from gui.window import AICardWindow
        assert AICardWindow is not None

    def test_class_has_required_signals(self, qapp, qtbot):
        """AICardWindow 应定义必要的信号"""
        from gui.window import AICardWindow
        # 类级别属性
        assert hasattr(AICardWindow, 'ide_probe_result')
        assert hasattr(AICardWindow, 'browser_probe_result')

    def test_class_has_required_methods(self, qapp, qtbot):
        """AICardWindow 应定义必要的方法"""
        from gui.window import AICardWindow
        required_methods = [
            'initUI', 'hide_card', 'hideEvent', 'closeEvent',
            'on_text_updated', 'trigger_ai', 'send_chat_message',
            'jump_to_chat', '_on_vision_analyze_clicked',
            'read_from_ide_extension', 'read_from_browser',
            'paste_from_clipboard', '_apply_to_ide',
            '_copy_result_to_clipboard', '_export_to_ppt',
        ]
        for method in required_methods:
            assert hasattr(AICardWindow, method), f"Missing method: {method}"

    def test_class_has_resize_support(self, qapp, qtbot):
        """AICardWindow 应支持拖拽缩放"""
        from gui.window import AICardWindow
        assert hasattr(AICardWindow, 'mousePressEvent')
        assert hasattr(AICardWindow, 'mouseMoveEvent')
        assert hasattr(AICardWindow, 'mouseReleaseEvent')
        assert hasattr(AICardWindow, '_get_resize_edge')
        assert hasattr(AICardWindow, '_EDGE_CURSORS')


# =========================================
# 2. AgentWorkspace 冒烟测试
# =========================================
class TestAgentWorkspaceSmoke:
    """任务工作台冒烟测试"""

    def test_workspace_creation(self, qapp, qtbot, mock_provider):
        """工作台应能正常创建"""
        from gui.workspace import AgentWorkspace

        workspace = AgentWorkspace(mock_provider)

        assert workspace is not None
        assert workspace.provider == mock_provider
        assert workspace.current_task == ""
        assert workspace.session_id  # 应有 UUID

    def test_workspace_save_task(self, qapp, qtbot, mock_provider):
        """保存任务应更新 current_task 并发射信号"""
        from gui.workspace import AgentWorkspace

        workspace = AgentWorkspace(mock_provider)

        signals = []
        workspace.task_changed.connect(lambda t: signals.append(t))

        workspace.task_input.setText("审查支付模块")
        workspace._save_task()

        assert workspace.current_task == "审查支付模块"
        assert len(signals) == 1
        assert signals[0] == "审查支付模块"

    def test_workspace_clear_task(self, qapp, qtbot, mock_provider):
        """空任务应清除并隐藏状态"""
        from gui.workspace import AgentWorkspace

        workspace = AgentWorkspace(mock_provider)

        # 先设置任务
        workspace.task_input.setText("某任务")
        workspace._save_task()
        assert workspace.current_task == "某任务"

        # 再清除
        workspace.task_input.setText("")
        signals = []
        workspace.task_changed.connect(lambda t: signals.append(t))
        workspace._save_task()

        assert workspace.current_task == ""
        assert "" in signals

    def test_workspace_default_size(self, qapp, qtbot, mock_provider):
        """工作台默认尺寸"""
        from gui.workspace import AgentWorkspace

        workspace = AgentWorkspace(mock_provider)

        assert workspace.width() == 520
        assert workspace.height() == 480


# =========================================
# 3. SettingsDialog 冒烟测试
# =========================================
class TestSettingsDialogSmoke:
    """设置对话框冒烟测试

    注意：settings.py 存在 Bug — setup_ui() 内使用 QWidget 但未导入。
    这些测试验证 Bug 的存在。
    """

    def test_settings_dialog_has_import_bug(self, qapp, qtbot):
        """settings.py 的 setup_ui 使用了 QWidget 但未导入（已知 Bug）"""
        from gui.dialogs.settings import SettingsDialog

        with patch("gui.dialogs.settings.load_config", return_value={
            "provider_type": "minimax",
            "minimax_api_key": "",
            "local_api_base": "http://localhost:11434/v1",
            "local_model": "llama3",
            "local_api_key": "",
        }):
            with pytest.raises(NameError, match="QWidget"):
                SettingsDialog()


class TestStaticReviewFindings:
    """验证静态审查发现的潜在问题"""

    def test_workspace_missing_imports(self, qapp, qtbot):
        """AgentWorkspace 的 _open_settings 引用 NewSettingsDialog 但未导入。

        这是一个已知 Bug：workspace.py 第297行使用 NewSettingsDialog，
        但该类只在 gui/shared.py 中有导入，workspace.py 没有引入它。
        调用 _open_settings 时会抛出 NameError。
        """
        # 验证 Bug 存在：NewSettingsDialog 未在 workspace 模块中导入
        import gui.workspace as ws_module
        assert not hasattr(ws_module, 'NewSettingsDialog'), \
            "Bug 已修复？NewSettingsDialog 现在在 workspace 模块中可用了"

    def test_browser_worker_missing_import(self, qapp, qtbot):
        """BrowserReaderWorker 使用 SystemProbeClient 但未导入。

        这是一个已知 Bug：browser.py 第12行使用 SystemProbeClient()，
        但文件顶部没有导入该模块。
        """
        import gui.workers.browser as browser_module
        # 检查 SystemProbeClient 是否在模块中定义或导入
        assert not hasattr(browser_module, 'SystemProbeClient'), \
            "Bug 已修复？SystemProbeClient 现在在 browser 模块中可用了"

    def test_workspace_missing_theme_manager(self, qapp, qtbot, mock_provider):
        """AgentWorkspace._open_settings 使用 self.theme_manager 但未初始化。

        workspace.py 第327行访问 self.theme_manager，但 __init__ 中没有初始化它。
        """
        from gui.workspace import AgentWorkspace

        workspace = AgentWorkspace(mock_provider)

        assert not hasattr(workspace, 'theme_manager'), \
            "Bug 已修复？theme_manager 现在在 AgentWorkspace.__init__ 中初始化了"
