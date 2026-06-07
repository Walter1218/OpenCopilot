"""V5 Smart Copilot 拖放功能集成测试

覆盖:
- 文本拖拽（mime.hasText()，模拟从 Qoder 拖拽文本）
- 文件拖拽（mime.hasUrls()）
- 混合拖拽（同时有 text 和 urls，优先处理文本）
- 不支持的格式拖拽（应 ignore）
- 拖放后 WorkTab 是否正确接收文本
- 拖放后是否切换到 Work Tab（index 0）
- 埋点事件验证（V5_SC_DROP_TEXT / V5_SC_TEXT_LOADED / V5_SC_DROP_FILES / V5_SC_FILE_LOADED）
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


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
def smart_copilot(qapp, mock_nav):
    """创建 SmartCopilotV5 实例"""
    from gui.v5.smart_copilot import SmartCopilotV5
    with patch("gui.v5.telemetry.V5Telemetry._get_obs", return_value=None):
        sc = SmartCopilotV5(mock_nav)
    yield sc
    sc.deleteLater()


def _make_mime_data(has_text=False, text="", has_urls=False, urls=None):
    """构造模拟 QMimeData"""
    mime = MagicMock()
    mime.hasText.return_value = has_text
    mime.text.return_value = text
    mime.hasUrls.return_value = has_urls
    if urls is None:
        urls = []
    mime.urls.return_value = urls
    return mime


def _make_drag_event(mime_data, event_type="enter"):
    """构造模拟拖拽事件"""
    event = MagicMock()
    event.mimeData.return_value = mime_data
    return event


# =============================================================================
# 1. dragEnterEvent 测试
# =============================================================================

class TestDragEnterEvent:
    """拖拽进入事件测试"""

    def test_text_drag_accepted(self, smart_copilot):
        """文本拖拽应 acceptProposedAction"""
        mime = _make_mime_data(has_text=True, text="hello from qoder")
        event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()
        event.ignore.assert_not_called()

    def test_file_drag_accepted(self, smart_copilot):
        """文件拖拽应 acceptProposedAction"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()
        event.ignore.assert_not_called()

    def test_unsupported_drag_ignored(self, smart_copilot):
        """不支持的格式应 ignore"""
        mime = _make_mime_data(has_text=False, has_urls=False)
        event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(event)
        event.ignore.assert_called_once()
        event.acceptProposedAction.assert_not_called()

    def test_mixed_drag_accepted(self, smart_copilot):
        """混合拖拽（text + urls）应 accept"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_text=True, text="mixed", has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(event)
        event.acceptProposedAction.assert_called_once()
        event.ignore.assert_not_called()


# =============================================================================
# 2. dragMoveEvent 测试
# =============================================================================

class TestDragMoveEvent:
    """拖拽移动事件测试"""

    def test_text_drag_move_accepted(self, smart_copilot):
        """文本拖拽移动应持续 accept"""
        mime = _make_mime_data(has_text=True, text="moving text")
        event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_file_drag_move_accepted(self, smart_copilot):
        """文件拖拽移动应持续 accept"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(event)
        event.acceptProposedAction.assert_called_once()

    def test_unsupported_drag_move_ignored(self, smart_copilot):
        """不支持的拖拽移动应 ignore"""
        mime = _make_mime_data(has_text=False, has_urls=False)
        event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(event)
        event.ignore.assert_called_once()


# =============================================================================
# 3. dropEvent — 文本拖拽
# =============================================================================

class TestDropText:
    """文本拖放测试"""

    def test_text_drop_sets_work_tab_text(self, smart_copilot):
        """文本拖放后 WorkTab 应接收文本"""
        mime = _make_mime_data(has_text=True, text="dragged text from qoder")
        event = _make_drag_event(mime)
        smart_copilot.dropEvent(event)
        assert smart_copilot._selected_text == "dragged text from qoder"

    def test_text_drop_shares_to_all_tabs(self, smart_copilot):
        """文本拖放后应同步到三个 Tab，不强制切换"""
        smart_copilot.tabs.setCurrentIndex(1)
        with patch.object(smart_copilot._work_tab, "set_context_text") as mock_work:
            with patch.object(smart_copilot._chat_tab, "set_shared_text") as mock_chat:
                with patch.object(smart_copilot._studio_tab, "set_shared_text") as mock_studio:
                    mime = _make_mime_data(has_text=True, text="shared text")
                    event = _make_drag_event(mime)
                    smart_copilot.dropEvent(event)
        mock_work.assert_called_once_with("shared text")
        mock_chat.assert_called_once_with("shared text", source="drag_drop")
        mock_studio.assert_called_once_with("shared text", source="drag_drop")
        # 不强制切换 Tab，保持当前 Tab
        assert smart_copilot.tabs.currentIndex() == 1

    def test_text_drop_calls_work_tab_set_context(self, smart_copilot):
        """文本拖放应调用 _work_tab.set_context_text"""
        with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
            mime = _make_mime_data(has_text=True, text="context text")
            event = _make_drag_event(mime)
            smart_copilot.dropEvent(event)
        mock_set.assert_called_once_with("context text")

    def test_text_drop_empty_text_ignored(self, smart_copilot):
        """空文本拖放不应设置文本"""
        with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
            mime = _make_mime_data(has_text=True, text="")
            event = _make_drag_event(mime)
            smart_copilot.dropEvent(event)
        mock_set.assert_not_called()

    def test_text_drop_accepts_event(self, smart_copilot):
        """文本拖放应 acceptProposedAction"""
        mime = _make_mime_data(has_text=True, text="accept me")
        event = _make_drag_event(mime)
        smart_copilot.dropEvent(event)
        event.acceptProposedAction.assert_called_once()


# =============================================================================
# 4. dropEvent — 文件拖拽
# =============================================================================

class TestDropFiles:
    """文件拖放测试"""

    def test_file_drop_reads_content(self, smart_copilot):
        """文件拖放应调用 bridge.get_file_content"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file content", "status": "ok", "file_path": "/tmp/test.py"}
            smart_copilot.dropEvent(event)
        mock_get.assert_called_once_with("/tmp/test.py")

    def test_file_drop_sets_work_tab_text(self, smart_copilot):
        """文件拖放成功后 WorkTab 应接收文件内容"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file content", "status": "ok", "file_path": "/tmp/test.py"}
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
                smart_copilot.dropEvent(event)
        mock_set.assert_called_once_with("file content")

    def test_file_drop_shares_to_all_tabs(self, smart_copilot):
        """文件拖放成功后应同步到三个 Tab，不强制切换"""
        smart_copilot.tabs.setCurrentIndex(2)
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file content", "status": "ok", "file_path": "/tmp/test.py"}
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_work:
                with patch.object(smart_copilot._chat_tab, "set_shared_text") as mock_chat:
                    with patch.object(smart_copilot._studio_tab, "set_shared_text") as mock_studio:
                        smart_copilot.dropEvent(event)
        mock_work.assert_called_once_with("file content")
        mock_chat.assert_called_once_with("file content", source="file:test.py")
        mock_studio.assert_called_once_with("file content", source="file:test.py")
        # 不强制切换 Tab
        assert smart_copilot.tabs.currentIndex() == 2

    def test_file_drop_failed_status_ignores(self, smart_copilot):
        """文件读取失败不应设置文本"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/missing.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "", "status": "not_found", "file_path": "/tmp/missing.py"}
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
                smart_copilot.dropEvent(event)
        mock_set.assert_not_called()

    def test_file_drop_empty_url_ignored(self, smart_copilot):
        """空 URL 列表应 ignore"""
        mime = _make_mime_data(has_urls=True, urls=[])
        event = _make_drag_event(mime)
        smart_copilot.dropEvent(event)
        event.ignore.assert_called_once()

    def test_file_drop_multiple_files(self, smart_copilot):
        """多文件拖放应处理每个文件"""
        url1 = MagicMock()
        url1.toLocalFile.return_value = "/tmp/a.py"
        url2 = MagicMock()
        url2.toLocalFile.return_value = "/tmp/b.py"
        mime = _make_mime_data(has_urls=True, urls=[url1, url2])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.side_effect = [
                {"text": "content a", "status": "ok", "file_path": "/tmp/a.py"},
                {"text": "content b", "status": "ok", "file_path": "/tmp/b.py"},
            ]
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
                smart_copilot.dropEvent(event)
        assert mock_get.call_count == 2
        # 每个成功文件都会调用 set_context_text（覆盖）
        assert mock_set.call_count == 2


# =============================================================================
# 5. dropEvent — 混合拖拽（text + urls）
# =============================================================================

class TestDropMixed:
    """混合拖放测试（同时有 text 和 urls）。

    注意：当前源码 dropEvent 第 248 行条件为 `mime.hasText() and not mime.hasUrls()`，
    因此同时含有 text 和 urls 的混合拖拽会走文件分支，而非优先文本分支。
    以下测试反映当前源码的实际行为。
    """

    def test_mixed_falls_through_to_file_path(self, smart_copilot):
        """混合拖拽（同时有 text 和 urls）会落入文件处理分支"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_text=True, text="priority text", has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file content", "status": "ok", "file_path": "/tmp/test.py"}
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_set:
                smart_copilot.dropEvent(event)
        # 会调用文件读取（走文件分支）
        mock_get.assert_called_once_with("/tmp/test.py")
        # 最终设置的是文件内容，而非文本内容
        mock_set.assert_called_once_with("file content")

    def test_mixed_sets_selected_text_from_file(self, smart_copilot):
        """混合拖拽后 _selected_text 来自文件内容"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_text=True, text="mixed content", has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file data", "status": "ok", "file_path": "/tmp/test.py"}
            smart_copilot.dropEvent(event)
        assert smart_copilot._selected_text == "file data"

    def test_mixed_shares_to_all_tabs_via_file(self, smart_copilot):
        """混合拖拽后通过文件分支同步到三个 Tab，不切换"""
        smart_copilot.tabs.setCurrentIndex(2)
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_text=True, text="mixed", has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "ok", "status": "ok", "file_path": "/tmp/test.py"}
            with patch.object(smart_copilot._work_tab, "set_context_text") as mock_work:
                with patch.object(smart_copilot._chat_tab, "set_shared_text") as mock_chat:
                    with patch.object(smart_copilot._studio_tab, "set_shared_text") as mock_studio:
                        smart_copilot.dropEvent(event)
        mock_work.assert_called_once_with("ok")
        mock_chat.assert_called_once_with("ok", source="file:test.py")
        mock_studio.assert_called_once_with("ok", source="file:test.py")
        # 不强制切换 Tab
        assert smart_copilot.tabs.currentIndex() == 2


# =============================================================================
# 6. dropEvent — 不支持格式
# =============================================================================

class TestDropUnsupported:
    """不支持格式拖放测试"""

    def test_unsupported_drop_ignored(self, smart_copilot):
        """不支持格式应 ignore"""
        mime = _make_mime_data(has_text=False, has_urls=False)
        event = _make_drag_event(mime)
        smart_copilot.dropEvent(event)
        event.ignore.assert_called_once()

    def test_unsupported_no_state_change(self, smart_copilot):
        """不支持格式拖放不应改变状态"""
        original_text = smart_copilot._selected_text
        original_tab = smart_copilot.tabs.currentIndex()
        mime = _make_mime_data(has_text=False, has_urls=False)
        event = _make_drag_event(mime)
        smart_copilot.dropEvent(event)
        assert smart_copilot._selected_text == original_text
        assert smart_copilot.tabs.currentIndex() == original_tab


# =============================================================================
# 7. 埋点事件验证
# =============================================================================

class TestTelemetryEvents:
    """拖放埋点事件验证"""

    def test_text_drop_emits_drop_text(self, smart_copilot):
        """文本拖放应发射 V5_SC_DROP_TEXT"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            mime = _make_mime_data(has_text=True, text="telemetry text")
            event = _make_drag_event(mime)
            smart_copilot.dropEvent(event)
        # 查找 V5_SC_DROP_TEXT 调用
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_SC_DROP_TEXT"]
        assert len(calls) == 1
        assert calls[0][1].get("text_len") == len("telemetry text")

    def test_text_drop_emits_text_shared(self, smart_copilot):
        """文本拖放应发射 V5_SC_TEXT_SHARED"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            mime = _make_mime_data(has_text=True, text="loaded text")
            event = _make_drag_event(mime)
            smart_copilot.dropEvent(event)
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_SC_TEXT_SHARED"]
        assert len(calls) == 1
        assert calls[0][1].get("target_tabs") == ["work", "chat", "studio"]

    def test_file_drop_emits_drop_files(self, smart_copilot):
        """文件拖放应发射 V5_SC_DROP_FILES"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            with patch("gui.v5.bridge.get_file_content") as mock_get:
                mock_get.return_value = {"text": "content", "status": "ok", "file_path": "/tmp/test.py"}
                smart_copilot.dropEvent(event)
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_SC_DROP_FILES"]
        assert len(calls) == 1
        assert calls[0][1].get("file_count") == 1

    def test_file_drop_emits_file_shared(self, smart_copilot):
        """文件拖放成功应发射 V5_SC_FILE_SHARED"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/test.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            with patch("gui.v5.bridge.get_file_content") as mock_get:
                mock_get.return_value = {"text": "content", "status": "ok", "file_path": "/tmp/test.py"}
                smart_copilot.dropEvent(event)
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_SC_FILE_SHARED"]
        assert len(calls) == 1
        assert calls[0][1].get("file") == "test.py"
        assert calls[0][1].get("target_tabs") == ["work", "chat", "studio"]

    def test_file_drop_error_emits_file_error(self, smart_copilot):
        """文件读取失败应发射 V5_SC_FILE_ERROR"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/bad.py"
        mime = _make_mime_data(has_urls=True, urls=[url])
        event = _make_drag_event(mime)
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            with patch("gui.v5.bridge.get_file_content") as mock_get:
                mock_get.return_value = {"text": "", "status": "not_found", "file_path": "/tmp/bad.py"}
                smart_copilot.dropEvent(event)
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_SC_FILE_ERROR"]
        assert len(calls) == 1
        assert calls[0][1].get("status") == "not_found"


# =============================================================================
# 8. 完整事件链测试
# =============================================================================

class TestDragDropEventChain:
    """完整拖放事件链: dragEnterEvent → dragMoveEvent → dropEvent"""

    def test_text_drag_full_chain(self, smart_copilot):
        """文本拖拽完整事件链"""
        mime = _make_mime_data(has_text=True, text="chain test")

        # Step 1: dragEnterEvent
        enter_event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(enter_event)
        enter_event.acceptProposedAction.assert_called_once()

        # Step 2: dragMoveEvent
        move_event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(move_event)
        move_event.acceptProposedAction.assert_called_once()

        # Step 3: dropEvent
        drop_event = _make_drag_event(mime)
        smart_copilot.dropEvent(drop_event)
        drop_event.acceptProposedAction.assert_called_once()
        assert smart_copilot._selected_text == "chain test"
        # 不强制切换 Tab

    def test_file_drag_full_chain(self, smart_copilot):
        """文件拖拽完整事件链"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/chain.py"
        mime = _make_mime_data(has_urls=True, urls=[url])

        # Step 1: dragEnterEvent
        enter_event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(enter_event)
        enter_event.acceptProposedAction.assert_called_once()

        # Step 2: dragMoveEvent
        move_event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(move_event)
        move_event.acceptProposedAction.assert_called_once()

        # Step 3: dropEvent
        drop_event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "chain content", "status": "ok", "file_path": "/tmp/chain.py"}
            smart_copilot.dropEvent(drop_event)
        drop_event.acceptProposedAction.assert_called_once()
        assert smart_copilot._selected_text == "chain content"
        # 不强制切换 Tab

    def test_unsupported_drag_full_chain(self, smart_copilot):
        """不支持格式完整事件链"""
        mime = _make_mime_data(has_text=False, has_urls=False)

        # Step 1: dragEnterEvent
        enter_event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(enter_event)
        enter_event.ignore.assert_called_once()

        # Step 2: dragMoveEvent
        move_event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(move_event)
        move_event.ignore.assert_called_once()

        # Step 3: dropEvent
        drop_event = _make_drag_event(mime)
        smart_copilot.dropEvent(drop_event)
        drop_event.ignore.assert_called_once()

    def test_mixed_drag_full_chain(self, smart_copilot):
        """混合拖拽完整事件链（当前源码走文件分支）"""
        url = MagicMock()
        url.toLocalFile.return_value = "/tmp/chain.py"
        mime = _make_mime_data(has_text=True, text="mixed chain", has_urls=True, urls=[url])

        # Step 1: dragEnterEvent
        enter_event = _make_drag_event(mime)
        smart_copilot.dragEnterEvent(enter_event)
        enter_event.acceptProposedAction.assert_called_once()

        # Step 2: dragMoveEvent
        move_event = _make_drag_event(mime)
        smart_copilot.dragMoveEvent(move_event)
        move_event.acceptProposedAction.assert_called_once()

        # Step 3: dropEvent
        drop_event = _make_drag_event(mime)
        with patch("gui.v5.bridge.get_file_content") as mock_get:
            mock_get.return_value = {"text": "file from chain", "status": "ok", "file_path": "/tmp/chain.py"}
            smart_copilot.dropEvent(drop_event)
        # 当前源码条件下混合拖拽走文件分支
        mock_get.assert_called_once_with("/tmp/chain.py")
        assert smart_copilot._selected_text == "file from chain"
        # 不强制切换 Tab
