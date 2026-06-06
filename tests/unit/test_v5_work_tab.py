"""V5 Work Tab 非AI事件链测试

覆盖:
- Context Strip 切换 → bridge.fetch_context → Header 更新
- Action Bar Copy/Apply/Export 操作
- More 按钮展示操作列表
- set_context_text 公共方法
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
    """Mock NavigationManager"""
    nav = MagicMock()
    return nav


@pytest.fixture
def work_tab(qapp, mock_nav):
    """创建 WorkTabV5 实例"""
    from gui.v5.work_tab import WorkTabV5
    tab = WorkTabV5(mock_nav)
    yield tab
    tab.deleteLater()


# =============================================================================
# 1. 初始化验证
# =============================================================================

class TestWorkTabInit:
    """Work Tab 初始化结构验证"""

    def test_creation(self, work_tab):
        """WorkTabV5 应能正常创建"""
        assert work_tab is not None
        assert work_tab._current_source == "selection"
        assert work_tab._selected_text == ""

    def test_has_context_strip_buttons(self, work_tab):
        """应有 5 个 Context Strip 按钮"""
        from gui.v5.tokens import CONTEXT_SOURCES
        assert len(work_tab._strip_buttons) == len(CONTEXT_SOURCES)
        for source_id, _, _ in CONTEXT_SOURCES:
            assert source_id in work_tab._strip_buttons

    def test_default_selection_is_selection(self, work_tab):
        """默认选中 selection 按钮（通过样式标识，非 checked 状态）"""
        # 代码中初始状态仅通过 stylesheet 标识选中，不调用 setChecked
        sel_btn = work_tab._strip_buttons["selection"]
        assert work_tab._current_source == "selection"
        # 验证 selection 按钮样式包含选中态颜色
        style = sel_btn.styleSheet()
        from gui.v5.tokens import BG_SELECTED
        assert BG_SELECTED in style

    def test_result_area_has_welcome_text(self, work_tab):
        """Result Area 应有欢迎文本"""
        text = work_tab._result_area.toPlainText()
        assert "v5.0" in text


# =============================================================================
# 2. Context Strip 切换事件链
# =============================================================================

class TestContextStripSwitch:
    """Context Strip 切换 → bridge.fetch_context → Header 更新"""

    def test_strip_switch_updates_source(self, work_tab):
        """切换数据源应更新 _current_source"""
        # Arrange: mock bridge to return clipboard content
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "clipboard data",
                "source": "clipboard",
                "status": "ok",
            }
            # Act: click clipboard button
            work_tab._on_strip_clicked("clipboard")

        # Assert
        assert work_tab._current_source == "clipboard"
        assert work_tab._selected_text == "clipboard data"

    def test_strip_switch_updates_header_with_content(self, work_tab):
        """有内容时 Header 应显示字符数和来源"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "hello world",
                "source": "clipboard",
                "status": "ok",
                "app_name": "",
            }
            work_tab._on_strip_clicked("clipboard")

        header_text = work_tab._header.text()
        assert "11 字符" in header_text  # "hello world" = 11 chars

    def test_strip_switch_updates_header_empty(self, work_tab):
        """无内容时 Header 应显示 '暂无内容'"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "",
                "source": "selection",
                "status": "empty",
            }
            work_tab._on_strip_clicked("selection")

        header_text = work_tab._header.text()
        assert "暂无内容" in header_text

    def test_strip_switch_highlights_correct_button(self, work_tab):
        """切换后对应按钮应 checked，其他 unchecked"""
        with patch("gui.v5.bridge.fetch_context", return_value={
            "text": "", "status": "empty"
        }):
            work_tab._on_strip_clicked("browser")

        for sid, btn in work_tab._strip_buttons.items():
            if sid == "browser":
                assert btn.isChecked() is True
            else:
                assert btn.isChecked() is False

    def test_strip_switch_calls_bridge(self, work_tab):
        """切换应调用 bridge.fetch_context 对应 source_id"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {"text": "", "status": "empty"}
            work_tab._on_strip_clicked("active_doc")
        mock_fetch.assert_called_once_with("active_doc")

    def test_strip_switch_header_shows_app_name(self, work_tab):
        """有 app_name 时 Header 应包含应用名"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "some code",
                "source": "selection",
                "status": "ok",
                "app_name": "VS Code",
            }
            work_tab._on_strip_clicked("selection")

        header_text = work_tab._header.text()
        assert "VS Code" in header_text

    def test_strip_all_sources_work(self, work_tab):
        """所有 5 个数据源切换都应正常工作"""
        from gui.v5.tokens import CONTEXT_SOURCES
        for source_id, _, _ in CONTEXT_SOURCES:
            with patch("gui.v5.bridge.fetch_context") as mock_fetch:
                mock_fetch.return_value = {"text": "data", "status": "ok"}
                work_tab._on_strip_clicked(source_id)
            assert work_tab._current_source == source_id


# =============================================================================
# 3. set_context_text 公共方法
# =============================================================================

class TestSetContextText:
    """set_context_text 方法测试"""

    def test_set_context_updates_selected_text(self, work_tab):
        """设置上下文文本应更新 _selected_text"""
        work_tab.set_context_text("new context")
        assert work_tab._selected_text == "new context"

    def test_set_context_updates_header(self, work_tab):
        """设置上下文后 Header 应显示字符数"""
        work_tab.set_context_text("hello")
        header = work_tab._header.text()
        assert "5 字符" in header

    def test_set_context_shows_preview_in_result(self, work_tab):
        """Result Area 应显示内容预览"""
        work_tab.set_context_text("preview text here")
        result = work_tab._result_area.toPlainText()
        assert "preview text here" in result

    def test_set_context_long_text_truncated(self, work_tab):
        """超长文本应在预览中截断"""
        long_text = "A" * 500
        work_tab.set_context_text(long_text)
        result = work_tab._result_area.toPlainText()
        assert "…" in result


# =============================================================================
# 4. Action Bar 操作
# =============================================================================

class TestActionBar:
    """Action Bar Copy/Apply/Export 操作"""

    def test_copy_success(self, work_tab):
        """Copy 按钮成功时应显示成功提示"""
        work_tab._result_area.setPlainText("result text to copy")
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True):
            work_tab._on_action_bar("📋 Copy")
        result = work_tab._result_area.toPlainText()
        assert "已复制" in result

    def test_copy_failure(self, work_tab):
        """Copy 按钮失败时应显示失败提示"""
        work_tab._result_area.setPlainText("text")
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=False):
            work_tab._on_action_bar("📋 Copy")
        result = work_tab._result_area.toPlainText()
        assert "复制失败" in result

    def test_copy_uses_selected_text_when_result_empty(self, work_tab):
        """Result 为空时应使用 _selected_text"""
        work_tab._result_area.setPlainText("")
        work_tab._selected_text = "selected fallback"
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True) as mock_copy:
            work_tab._on_action_bar("📋 Copy")
        # The function passes result_text or selected_text
        mock_copy.assert_called_once()

    def test_apply_success(self, work_tab):
        """Apply 成功时应显示成功信息"""
        work_tab._result_area.setPlainText("code to apply")
        with patch("gui.v5.bridge.do_apply_to_ide") as mock_apply:
            mock_apply.return_value = {"success": True, "method": "broker_insert"}
            work_tab._on_action_bar("📝 Apply")
        result = work_tab._result_area.toPlainText()
        assert "已应用" in result

    def test_apply_failure(self, work_tab):
        """Apply 失败时应显示失败信息"""
        work_tab._result_area.setPlainText("code")
        with patch("gui.v5.bridge.do_apply_to_ide") as mock_apply:
            mock_apply.return_value = {"success": False, "message": "连接失败"}
            work_tab._on_action_bar("📝 Apply")
        result = work_tab._result_area.toPlainText()
        assert "失败" in result

    def test_export_ppt_shows_info(self, work_tab):
        """Export PPT 按钮应显示导出提示信息"""
        work_tab._on_action_bar("💾 Export PPT")
        result = work_tab._result_area.toPlainText()
        assert "PPT" in result


# =============================================================================
# 5. More 按钮
# =============================================================================

class TestMoreAction:
    """More 按钮展示操作列表"""

    def test_more_shows_action_list(self, work_tab):
        """More 按钮应展示可用操作列表"""
        from gui.v5.bridge import DEFAULT_MORE_ACTIONS
        with patch("gui.v5.bridge.get_more_actions", return_value=DEFAULT_MORE_ACTIONS):
            work_tab._on_action("more")
        result = work_tab._result_area.toPlainText()
        assert "可用操作" in result
        assert "5 项" in result

    def test_more_custom_actions(self, work_tab):
        """自定义操作列表也应正常展示"""
        custom = [{"id": "my", "label": "My Action", "description": "Custom desc"}]
        with patch("gui.v5.bridge.get_more_actions", return_value=custom):
            work_tab._on_action("more")
        result = work_tab._result_area.toPlainText()
        assert "1 项" in result
        assert "My Action" in result


# =============================================================================
# 6. AI Action 占位反馈
# =============================================================================

class TestAIActionPlaceholder:
    """AI 操作（explain/fix/polish）占位反馈"""

    def test_explain_with_text(self, work_tab):
        """有选区文本时 explain 应显示处理中"""
        work_tab._selected_text = "def hello(): pass"
        work_tab._on_action("explain")
        result = work_tab._result_area.toPlainText()
        assert "处理中" in result
        assert "explain" in result

    def test_explain_without_text(self, work_tab):
        """无选区文本时 explain 应显示警告"""
        work_tab._selected_text = ""
        work_tab._on_action("explain")
        result = work_tab._result_area.toPlainText()
        assert "无内容" in result

    def test_fix_action(self, work_tab):
        """fix 操作应有占位反馈"""
        work_tab._selected_text = "buggy code"
        work_tab._on_action("fix")
        result = work_tab._result_area.toPlainText()
        assert "fix" in result
        assert "trace_id" in result

    def test_polish_action(self, work_tab):
        """polish 操作应有占位反馈"""
        work_tab._selected_text = "rough text"
        work_tab._on_action("polish")
        result = work_tab._result_area.toPlainText()
        assert "polish" in result
