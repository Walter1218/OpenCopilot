"""V5 Work Tab 非AI事件链测试 (v5.2 精简版)

覆盖:
- Context Header Bar (发光圆点 + 来源 + 字数 + 宿主badge + 刷新/关闭)
- Toolbar Row 数据源按钮切换 + 操作按钮
- Action Bar Copy/Apply/Export 操作 (合并到 Result Area 底部)
- Streaming Result Area + Confidence Bar
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
    """Mock navigationManager"""
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

    def test_has_toolbar_source_buttons(self, work_tab):
        """应有 5 个 Toolbar 数据源按钮"""
        from gui.v5.tokens import CONTEXT_SOURCES
        assert len(work_tab._strip_buttons) == len(CONTEXT_SOURCES)
        for source_id, _, _, _ in CONTEXT_SOURCES:
            assert source_id in work_tab._strip_buttons

    def test_default_selection_is_selection(self, work_tab):
        """默认选中 selection 数据源按钮"""
        sel_btn = work_tab._strip_buttons["selection"]
        assert work_tab._current_source == "selection"
        # 验证 selection 按钮样式包含 active 态颜色 #4da6ff
        style = sel_btn.styleSheet()
        assert "#4da6ff" in style.lower() or "4da6ff" in style.lower()

    def test_selection_button_has_icon(self, work_tab):
        """默认 selection 按钮应有 icon letter"""
        sel_btn = work_tab._strip_buttons["selection"]
        # 按钮文本应包含对应 icon letter（非空）
        assert len(sel_btn.text().strip()) > 0

    def test_result_area_has_welcome_text(self, work_tab):
        """Result Area 应有欢迎文本"""
        text = work_tab._result_area.toPlainText()
        assert "双击右键" in text

    def test_has_action_cards(self, work_tab):
        """应有 3 个 Primary Action 按钮"""
        from gui.v5.tokens import PRIMARY_ACTION_CARDS
        assert len(work_tab._action_cards) == len(PRIMARY_ACTION_CARDS)
        for cd in PRIMARY_ACTION_CARDS:
            assert cd["id"] in work_tab._action_cards

    def test_confidence_bar_initial(self, work_tab):
        """Confidence Bar 初始应为空"""
        assert work_tab._conf_value.text() == ""

    def test_streaming_indicator_hidden(self, work_tab):
        """Streaming 指示器初始应隐藏"""
        assert not work_tab._stream_dot.isVisibleTo(work_tab)
        assert not work_tab._stream_label.isVisibleTo(work_tab)


# =============================================================================
# 2. Toolbar 数据源切换事件链
# =============================================================================

class TestToolbarSourceSwitch:
    """Toolbar 数据源按钮切换 → bridge.fetch_context → Header 更新"""

    def test_strip_switch_updates_source(self, work_tab):
        """切换数据源应更新 _current_source"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "clipboard data",
                "source": "clipboard",
                "status": "ok",
            }
            work_tab._on_strip_clicked("clipboard")

        assert work_tab._current_source == "clipboard"
        assert work_tab._selected_text == "clipboard data"

    def test_strip_switch_updates_header_with_content(self, work_tab):
        """有内容时 Header 应显示字符数"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "hello world",
                "source": "clipboard",
                "status": "ok",
                "app_name": "",
            }
            work_tab._on_strip_clicked("clipboard")

        assert work_tab._header_chars.text() == "11 chars"

    def test_strip_switch_updates_header_empty(self, work_tab):
        """无内容时 Header 应显示 'empty'"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {
                "text": "",
                "source": "selection",
                "status": "empty",
            }
            work_tab._on_strip_clicked("selection")

        assert work_tab._header_chars.text() == "empty"

    def test_strip_switch_updates_button_styles(self, work_tab):
        """切换后对应按钮应为 active 态，其他为 inactive"""
        with patch("gui.v5.bridge.fetch_context", return_value={
            "text": "", "status": "empty"
        }):
            work_tab._on_strip_clicked("browser")

        for sid, btn in work_tab._strip_buttons.items():
            style = btn.styleSheet()
            if sid == "browser":
                # active 态包含 #4da6ff 颜色
                assert "#4da6ff" in style.lower() or "4da6ff" in style.lower()
            else:
                # inactive 态使用 #666 或 #252526
                assert "#666" in style or "#252526" in style

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

        assert work_tab._header_app_name.text() == "VS Code"
        assert work_tab._header_app_badge.text() == "VS"

    def test_strip_all_sources_work(self, work_tab):
        """所有 5 个数据源切换都应正常工作"""
        from gui.v5.tokens import CONTEXT_SOURCES
        for source_id, _, _, _ in CONTEXT_SOURCES:
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
        assert work_tab._header_chars.text() == "5 chars"


# =============================================================================
# 4. Context Header Bar 操作
# =============================================================================

class TestHeaderBar:
    """Context Header Bar 刷新/清空按钮"""

    def test_header_refresh(self, work_tab):
        """刷新按钮应重新获取当前数据源"""
        with patch("gui.v5.bridge.fetch_context") as mock_fetch:
            mock_fetch.return_value = {"text": "refreshed", "status": "ok", "app_name": ""}
            work_tab._on_header_refresh()
        mock_fetch.assert_called_once()

    def test_header_clear(self, work_tab):
        """清空按钮应清空上下文"""
        work_tab._selected_text = "some text"
        work_tab.set_context_text("some text")
        work_tab._on_header_clear()
        assert work_tab._selected_text == ""


# =============================================================================
# 5. Action Bar 操作
# =============================================================================

class TestActionBar:
    """Action Bar Copy/Apply/Export 操作"""

    def test_copy_success(self, work_tab):
        """Copy 按钮成功时应显示成功提示"""
        work_tab._result_area.setPlainText("result text to copy")
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True):
            work_tab._on_action_bar("Copy")
        result = work_tab._result_area.toPlainText()
        assert "已复制" in result

    def test_copy_failure(self, work_tab):
        """Copy 按钮失败时应显示失败提示"""
        work_tab._result_area.setPlainText("text")
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=False):
            work_tab._on_action_bar("Copy")
        result = work_tab._result_area.toPlainText()
        assert "复制失败" in result

    def test_copy_uses_selected_text_when_result_empty(self, work_tab):
        """Result 为空时应使用 _selected_text"""
        work_tab._result_area.setPlainText("")
        work_tab._selected_text = "selected fallback"
        with patch("gui.v5.bridge.do_copy_to_clipboard", return_value=True) as mock_copy:
            work_tab._on_action_bar("Copy")
        mock_copy.assert_called_once()

    def test_apply_success(self, work_tab):
        """Apply 成功时应显示成功信息"""
        work_tab._result_area.setPlainText("code to apply")
        with patch("gui.v5.bridge.do_apply_to_ide") as mock_apply:
            mock_apply.return_value = {"success": True, "method": "broker_insert"}
            work_tab._on_action_bar("Apply")
        result = work_tab._result_area.toPlainText()
        assert "已应用" in result

    def test_apply_failure(self, work_tab):
        """Apply 失败时应显示失败信息"""
        work_tab._result_area.setPlainText("code")
        with patch("gui.v5.bridge.do_apply_to_ide") as mock_apply:
            mock_apply.return_value = {"success": False, "message": "连接失败"}
            work_tab._on_action_bar("Apply")
        result = work_tab._result_area.toPlainText()
        assert "失败" in result

    def test_export_opens_studio(self, work_tab):
        """Export 按钮应把当前内容发送到 Studio"""
        work_tab._result_area.setPlainText("weekly report content")
        work_tab.nav.open_studio = MagicMock()
        work_tab._on_action_bar("Export")
        result = work_tab._result_area.toPlainText()
        assert "Studio" in result
        work_tab.nav.open_studio.assert_called_once_with(text="weekly report content")

    def test_export_without_content_warns(self, work_tab):
        """没有内容时导出应给出警告"""
        work_tab._result_area.setPlainText("")
        work_tab._selected_text = ""
        work_tab._on_action_bar("Export")
        result = work_tab._result_area.toPlainText()
        assert "没有可发送到 Studio 的内容" in result


# =============================================================================
# 6. More 按钮
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
# 7. AI Action — streaming 状态 + confidence
# =============================================================================

class TestAIActionStreaming:
    """AI 操作 streaming 状态 + confidence bar"""

    def test_explain_without_text(self, work_tab):
        """无选区文本时 explain 应显示警告"""
        work_tab._selected_text = ""
        work_tab._on_action("explain")
        result = work_tab._result_area.toPlainText()
        assert "无内容" in result

    def test_explain_starts_streaming(self, work_tab):
        """有选区文本时 explain 应进入 streaming 状态"""
        work_tab._selected_text = "def hello(): pass"
        # 直接调用 _update_streaming_state 验证 UI
        work_tab._update_streaming_state("explain", True)

        assert work_tab._stream_dot.isVisibleTo(work_tab)
        assert work_tab._stream_label.text() == "Streaming..."
        assert "Explain" in work_tab._result_title.text()

    def test_streaming_done_hides_indicator(self, work_tab):
        """streaming 完成后指示器应隐藏"""
        work_tab._update_streaming_state("fix", True)
        work_tab._update_streaming_state("fix", False)
        assert not work_tab._stream_dot.isVisibleTo(work_tab)
        assert not work_tab._stream_label.isVisibleTo(work_tab)

    def test_confidence_high(self, work_tab):
        """高 confidence 应显示绿色"""
        work_tab._update_confidence(87)
        from gui.v5.tokens import CONFIDENCE_HIGH
        assert work_tab._conf_value.text() == "87%"
        assert CONFIDENCE_HIGH in work_tab._conf_value.styleSheet()

    def test_confidence_mid(self, work_tab):
        """中等 confidence 应显示黄色"""
        work_tab._update_confidence(60)
        from gui.v5.tokens import CONFIDENCE_MID
        assert work_tab._conf_value.text() == "60%"
        assert CONFIDENCE_MID in work_tab._conf_value.styleSheet()

    def test_confidence_low(self, work_tab):
        """低 confidence 应显示红色"""
        work_tab._update_confidence(30)
        from gui.v5.tokens import CONFIDENCE_LOW
        assert work_tab._conf_value.text() == "30%"
        assert CONFIDENCE_LOW in work_tab._conf_value.styleSheet()
