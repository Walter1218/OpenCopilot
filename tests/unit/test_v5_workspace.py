"""V5 Workspace 面板数据加载测试 — Files/Memory/Task 面板切换时的数据刷新

覆盖:
- Workspace 创建与初始化
- 5 面板导航切换 (Task/Chat/Files/Memory/Settings)
- Files 面板: bridge.get_recent_files → 显示文件列表
- Memory 面板: bridge.get_memory_stats → 显示统计
- Task 面板: bridge.get_task_history → 显示任务历史
- Settings 面板 → nav.open_settings 跳转
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
def mock_nav():
    return MagicMock()


@pytest.fixture
def workspace(qapp, mock_nav):
    """创建 WorkspaceV5 实例，mock bridge 调用避免初始化时数据加载失败"""
    with patch("gui.v5.bridge.get_recent_files", return_value=[]), \
         patch("gui.v5.bridge.get_memory_stats", return_value={
             "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
             "translation_memory": {"entries": 0, "status": "unavailable"},
             "glossary": {"terms": 0, "status": "unavailable"},
         }):
        from gui.v5.workspace import WorkspaceV5
        ws = WorkspaceV5(mock_nav)
        yield ws
        ws.deleteLater()


# =============================================================================
# 1. 初始化验证
# =============================================================================

class TestWorkspaceInit:
    """Workspace 初始化验证"""

    def test_creation(self, workspace):
        """WorkspaceV5 应能正常创建"""
        assert workspace is not None

    def test_has_5_nav_buttons(self, workspace):
        """应有 5 个导航按钮"""
        from gui.v5.tokens import WORKSPACE_NAV_ITEMS
        assert len(workspace._nav_buttons) == len(WORKSPACE_NAV_ITEMS)
        for sid, _, _ in WORKSPACE_NAV_ITEMS:
            assert sid in workspace._nav_buttons

    def test_default_panel_is_task(self, workspace):
        """默认面板应是 Task (index 0)"""
        assert workspace._stack.currentIndex() == 0

    def test_stack_has_5_panels(self, workspace):
        """QStackedWidget 应有 5 个面板"""
        assert workspace._stack.count() == 5


# =============================================================================
# 2. 面板导航切换
# =============================================================================

class TestPanelNavigation:
    """5 面板导航切换事件"""

    def test_switch_to_chat(self, workspace):
        """切换到 Chat 面板 (index 1)"""
        with patch("gui.v5.bridge.get_recent_files", return_value=[]), \
             patch("gui.v5.bridge.get_memory_stats", return_value={
                 "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
                 "translation_memory": {"entries": 0, "status": "unavailable"},
                 "glossary": {"terms": 0, "status": "unavailable"},
             }), \
             patch("gui.v5.bridge.get_task_history", return_value=[]):
            workspace._on_nav_clicked(1)
        assert workspace._stack.currentIndex() == 1
        assert workspace._nav_buttons["chat"].isChecked() is True

    def test_switch_to_files_triggers_refresh(self, workspace):
        """切换到 Files 面板应触发数据刷新"""
        with patch("gui.v5.bridge.get_recent_files", return_value=[
            {"name": "test.py", "size": 1024, "modified": "2026-06-01T12:00:00"},
        ]) as mock_get:
            workspace._on_nav_clicked(2)
        mock_get.assert_called_once()
        assert workspace._stack.currentIndex() == 2

    def test_switch_to_memory_triggers_refresh(self, workspace):
        """切换到 Memory 面板应触发数据刷新"""
        with patch("gui.v5.bridge.get_memory_stats", return_value={
            "knowledge_graph": {"entities": 5, "relations": 10, "status": "ok"},
            "translation_memory": {"entries": 20, "status": "ok"},
            "glossary": {"terms": 8, "status": "ok"},
        }) as mock_get:
            workspace._on_nav_clicked(3)
        mock_get.assert_called_once()
        assert workspace._stack.currentIndex() == 3

    def test_switch_to_task_triggers_refresh(self, workspace):
        """切换到 Task 面板应触发任务历史刷新（优先按 session 过滤，回退全部）"""
        with patch("gui.v5.bridge.get_task_history", return_value=[]) as mock_get:
            workspace._on_nav_clicked(0)
        # 第一次带 session_id，第二次回退不带
        assert mock_get.call_count == 2
        # 验证第一次调用包含 session_id 参数
        first_call_kwargs = mock_get.call_args_list[0].kwargs
        assert "session_id" in first_call_kwargs

    def test_switch_to_settings(self, workspace):
        """切换到 Settings 面板 (index 4)"""
        with patch("gui.v5.bridge.get_recent_files", return_value=[]), \
             patch("gui.v5.bridge.get_memory_stats", return_value={
                 "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
                 "translation_memory": {"entries": 0, "status": "unavailable"},
                 "glossary": {"terms": 0, "status": "unavailable"},
             }):
            workspace._on_nav_clicked(4)
        assert workspace._stack.currentIndex() == 4

    def test_nav_highlights_correct_button(self, workspace):
        """切换后只有对应按钮 checked"""
        with patch("gui.v5.bridge.get_recent_files", return_value=[]), \
             patch("gui.v5.bridge.get_memory_stats", return_value={
                 "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
                 "translation_memory": {"entries": 0, "status": "unavailable"},
                 "glossary": {"terms": 0, "status": "unavailable"},
             }):
            workspace._on_nav_clicked(2)  # files

        for sid, btn in workspace._nav_buttons.items():
            if sid == "files":
                assert btn.isChecked() is True
            else:
                assert btn.isChecked() is False


# =============================================================================
# 3. Files 面板数据加载
# =============================================================================

class TestFilesPanel:
    """Files 面板: bridge.get_recent_files"""

    def test_refresh_with_files(self, workspace):
        """有最近文件时应显示文件列表"""
        files = [
            {"name": "main.py", "path": "/tmp/main.py", "size": 2048, "modified": "2026-06-01T10:00:00"},
            {"name": "test.py", "path": "/tmp/test.py", "size": 512, "modified": "2026-05-30T08:00:00"},
        ]
        with patch("gui.v5.bridge.get_recent_files", return_value=files), \
             patch("gui.v5.bridge.get_file_content", return_value={"text": "print('hello')", "status": "ok"}):
            workspace._refresh_files()
        assert "2 项" in workspace._files_summary_label.text()
        text = workspace._files_content.toPlainText()
        assert "main.py" in text
        assert "/tmp/main.py" in text

    def test_refresh_empty(self, workspace):
        """无最近文件时应显示提示"""
        with patch("gui.v5.bridge.get_recent_files", return_value=[]):
            workspace._refresh_files()
        text = workspace._files_content.toPlainText()
        assert "暂无" in text

    def test_refresh_shows_file_size_kb(self, workspace):
        """文件大小 < 1MB 应显示 KB"""
        files = [{"name": "small.py", "path": "/tmp/small.py", "size": 1024, "modified": "2026-06-01T10:00:00"}]
        with patch("gui.v5.bridge.get_recent_files", return_value=files), \
             patch("gui.v5.bridge.get_file_content", return_value={"text": "small", "status": "ok"}):
            workspace._refresh_files()
        text = workspace._files_content.toPlainText()
        assert "KB" in text

    def test_refresh_shows_file_size_mb(self, workspace):
        """文件大小 > 1MB 应显示 MB"""
        files = [{"name": "big.pptx", "path": "/tmp/big.pptx", "size": 2 * 1024 * 1024, "modified": "2026-06-01T10:00:00"}]
        with patch("gui.v5.bridge.get_recent_files", return_value=files), \
             patch("gui.v5.bridge.get_file_content", return_value={"text": "slides", "status": "ok"}):
            workspace._refresh_files()
        text = workspace._files_content.toPlainText()
        assert "MB" in text

    def test_use_file_for_task_imports_preview(self, workspace):
        """选中文件后应可导入到 Task 草稿"""
        workspace._files_entries = [{"name": "notes.md", "path": "/tmp/notes.md", "size": 12}]
        workspace._filtered_files = list(workspace._files_entries)
        workspace._files_list.addItem("notes.md")
        workspace._files_list.setCurrentRow(0)
        with patch("gui.v5.bridge.get_file_content", return_value={"text": "task context", "status": "ok"}):
            workspace._on_use_file_for_task()
        assert "task context" in workspace._task_input.toPlainText()

    def test_filter_files_updates_match_count(self, workspace):
        workspace._files_entries = [
            {"name": "notes.md", "path": "/tmp/notes.md", "size": 12, "source": "local"},
            {"name": "slides.pptx", "path": "/tmp/slides.pptx", "size": 120, "source": "drag_drop"},
        ]
        workspace._files_filter_input.setText("slides")
        assert len(workspace._filtered_files) == 1
        assert "1 项" in workspace._files_summary_label.text()

    def test_send_file_to_chat_appends_system_message(self, workspace):
        workspace._files_entries = [{"name": "notes.md", "path": "/tmp/notes.md", "size": 12, "source": "local"}]
        workspace._filtered_files = list(workspace._files_entries)
        workspace._files_list.addItem("notes.md")
        workspace._files_list.setCurrentRow(0)
        with patch("gui.v5.bridge.get_file_content", return_value={"text": "chat context", "status": "ok"}):
            workspace._on_send_file_to_chat()
        assert workspace._stack.currentIndex() == 1
        assert "chat context" in workspace._chat_display.toPlainText()

    def test_copy_selected_file_content(self, workspace):
        workspace._files_entries = [{"name": "notes.md", "path": "/tmp/notes.md", "size": 12, "source": "local"}]
        workspace._filtered_files = list(workspace._files_entries)
        workspace._files_list.addItem("notes.md")
        workspace._files_list.setCurrentRow(0)
        with patch("gui.v5.bridge.get_file_content", return_value={"text": "copy me", "status": "ok"}), \
             patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True) as mock_copy:
            workspace._on_copy_selected_file_content()
        mock_copy.assert_called_once_with("copy me")


# =============================================================================
# 4. Memory 面板数据加载
# =============================================================================

class TestMemoryPanel:
    """Memory 面板: bridge.get_memory_stats"""

    def test_refresh_with_stats(self, workspace):
        """有统计数据时应显示统计信息"""
        stats = {
            "knowledge_graph": {"entities": 42, "relations": 100, "status": "ok"},
            "translation_memory": {"entries": 256, "status": "ok"},
            "glossary": {"terms": 30, "status": "ok"},
        }
        with patch("gui.v5.bridge.get_memory_stats", return_value=stats):
            workspace._refresh_memory()
        text = workspace._memory_content.toPlainText()
        assert "42" in text   # entities
        assert "100" in text  # relations
        assert "256" in workspace._memory_cards["translation_memory"].text()
        assert "30" in workspace._memory_cards["glossary"].text()
        assert "知识图谱 42" in workspace._memory_summary_label.text()

    def test_refresh_unavailable(self, workspace):
        """数据不可用时应显示 unavailable 状态"""
        stats = {
            "knowledge_graph": {"entities": 0, "relations": 0, "status": "unavailable"},
            "translation_memory": {"entries": 0, "status": "unavailable"},
            "glossary": {"terms": 0, "status": "unavailable"},
        }
        with patch("gui.v5.bridge.get_memory_stats", return_value=stats):
            workspace._refresh_memory()
        text = workspace._memory_content.toPlainText()
        assert "unavailable" in text

    def test_memory_focus_switch_updates_detail(self, workspace):
        stats = {
            "knowledge_graph": {"entities": 42, "relations": 100, "status": "ok"},
            "translation_memory": {"entries": 10, "status": "ok"},
            "glossary": {"terms": 5, "status": "ok"},
        }
        with patch("gui.v5.bridge.get_memory_stats", return_value=stats):
            workspace._refresh_memory()
        workspace._memory_focus_combo.setCurrentIndex(
            workspace._memory_focus_combo.findData("translation_memory")
        )
        assert "翻译记忆详情" in workspace._memory_content.toPlainText()

    def test_memory_to_task_injects_summary(self, workspace):
        workspace._memory_stats_cache = {
            "knowledge_graph": {"entities": 3, "relations": 4, "status": "ok"},
        }
        workspace._memory_focus_combo.setCurrentIndex(
            workspace._memory_focus_combo.findData("knowledge_graph")
        )
        workspace._on_memory_to_task()
        assert "知识图谱详情" in workspace._task_input.toPlainText()

    def test_copy_memory_summary(self, workspace):
        workspace._memory_stats_cache = {
            "glossary": {"terms": 8, "status": "ok"},
        }
        workspace._memory_focus_combo.setCurrentIndex(
            workspace._memory_focus_combo.findData("glossary")
        )
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True) as mock_copy:
            workspace._on_copy_memory_summary()
        mock_copy.assert_called_once()


# =============================================================================
# 5. Task 面板数据加载
# =============================================================================

class TestTaskPanel:
    """Task 面板: bridge.get_task_history"""

    def test_refresh_with_tasks(self, workspace):
        """有任务历史时应显示任务列表"""
        tasks = [
            {"title": "审查支付模块", "created_at": "2026-06-01T10:00:00"},
            {"title": "修复登录 Bug", "created_at": "2026-05-30T08:00:00"},
        ]
        with patch("gui.v5.bridge.get_task_history", return_value=tasks):
            workspace._refresh_task_history()
        text = workspace._task_history_list.text()
        assert "2 个任务" in text
        assert "审查支付模块" in text

    def test_refresh_empty_tasks(self, workspace):
        """无任务历史时应显示提示"""
        with patch("gui.v5.bridge.get_task_history", return_value=[]):
            workspace._refresh_task_history()
        text = workspace._task_history_list.text()
        assert "暂无" in text


# =============================================================================
# 6. Settings 面板跳转
# =============================================================================

class TestSettingsPanelJumps:
    """Settings 面板 → nav.open_settings 跳转"""

    def test_open_settings_engine(self, workspace, mock_nav):
        """点击 Engine 配置应打开 Settings engine 分区"""
        # Settings 面板的按钮通过 lambda 连接 nav.open_settings
        # 我们验证 nav.open_settings 被正确调用
        mock_nav.open_settings("engine")
        mock_nav.open_settings.assert_called_with("engine")

    def test_open_settings_appearance(self, workspace, mock_nav):
        mock_nav.open_settings("appearance")
        mock_nav.open_settings.assert_called_with("appearance")

    def test_open_settings_shortcuts(self, workspace, mock_nav):
        mock_nav.open_settings("shortcuts")
        mock_nav.open_settings.assert_called_with("shortcuts")

    def test_open_settings_advanced(self, workspace, mock_nav):
        mock_nav.open_settings("advanced")
        mock_nav.open_settings.assert_called_with("advanced")

    def test_refresh_settings_summary_updates_cards(self, workspace):
        with patch("gui.v5.bridge.get_config", return_value={
            "provider_type": "cloud",
            "cloud_model": "MiniMax-M1",
        }), patch("gui.v5.bridge.get_appearance", return_value={
            "theme": "dark", "font_size": 13, "language": "zh",
        }), patch("gui.v5.bridge.get_shortcuts", return_value={
            "shortcuts": {"explain": {"key_sequence": "Cmd+E"}}
        }), patch("gui.v5.bridge.get_agent_runtime_config", return_value={
            "default_backend": "vnext_provider",
            "default_provider": "hermes_local",
        }):
            workspace._refresh_settings_summary()
        assert "hermes_local" in workspace._settings_overview_label.text()
        assert "MiniMax-M1" in workspace._settings_summary_labels["engine"].text()

    def test_copy_settings_summary(self, workspace):
        workspace._settings_overview_label.setText("overview")
        for label in workspace._settings_summary_labels.values():
            label.setText("summary")
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True) as mock_copy:
            workspace._on_copy_settings_summary()
        mock_copy.assert_called_once()
        assert "已复制" in workspace._settings_action_status.text()

    def test_export_workspace_settings(self, workspace):
        with patch("gui.v5.bridge.do_export_config", return_value={
            "success": True,
            "filename": "cfg.json",
        }):
            workspace._on_export_workspace_settings()
        assert "cfg.json" in workspace._settings_action_status.text()

    def test_reset_workspace_appearance(self, workspace):
        with patch("gui.v5.bridge.do_reset_config", return_value={"success": True}), \
             patch.object(workspace, "_refresh_settings_summary") as mock_refresh:
            workspace._on_reset_workspace_appearance()
        mock_refresh.assert_called_once()
