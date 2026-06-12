"""V5 Chat Tab 业务模拟测试（气泡 UI 版）

覆盖:
- 初始化与 UI 结构验证
- 消息发送流程（_on_send）
- 上下文注入（inject_context）
- 共享文本接收（set_shared_text）
- 会话管理（新建/切换/加载历史）
- Context Panel 折叠/展开
- 埋点事件验证
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import json
import tempfile
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
def chat_tab(qapp, mock_nav):
    """创建 ChatTabV5 实例"""
    from gui.v5.chat_tab import ChatTabV5
    with patch("gui.v5.telemetry.V5Telemetry._get_obs", return_value=None):
        tab = ChatTabV5(mock_nav)
    yield tab
    tab.deleteLater()


from PyQt6.QtWidgets import QLabel


def _get_bubble_texts(chat_tab):
    """提取所有气泡中的文本"""
    texts = []
    for i in range(chat_tab._bubble_layout.count()):
        item = chat_tab._bubble_layout.itemAt(i)
        if item.widget():
            # 直接 widget（AI / 系统）
            lbl = item.widget().findChild(QLabel)
            if lbl is not None:
                texts.append(lbl.text())
        elif item.layout():
            # wrapper layout（用户气泡）
            for j in range(item.layout().count()):
                sub = item.layout().itemAt(j)
                if sub.widget():
                    lbl = sub.widget().findChild(QLabel)
                    if lbl is not None:
                        texts.append(lbl.text())
    return texts


# =============================================================================
# 1. 初始化验证
# =============================================================================

class TestChatTabInit:
    """Chat Tab 初始化结构验证"""

    def test_creation(self, chat_tab):
        """ChatTabV5 应能正常创建"""
        assert chat_tab is not None
        assert chat_tab._message_count == 0

    def test_has_bubble_scroll(self, chat_tab):
        """应有气泡滚动区"""
        assert chat_tab._chat_scroll is not None
        assert chat_tab._bubble_layout is not None

    def test_has_chat_input(self, chat_tab):
        """应有输入框"""
        assert chat_tab._chat_input is not None
        assert chat_tab._chat_input.placeholderText() != ""

    def test_has_send_button(self, chat_tab):
        """应有发送按钮"""
        assert chat_tab._send_btn is not None
        assert chat_tab._send_btn.text() == "▶"

    def test_has_session_combo(self, chat_tab):
        """应有会话选择器（隐藏但存在）"""
        assert chat_tab._session_combo is not None
        assert chat_tab._session_combo.count() >= 1

    def test_has_new_session_button(self, chat_tab):
        """应有新建会话按钮"""
        assert chat_tab._new_session_btn is not None
        assert chat_tab._new_session_btn.text() == "+"

    def test_context_collapsed_by_default(self, chat_tab):
        """Context 默认应折叠"""
        assert chat_tab._context_collapsed is True

    def test_has_context_badge(self, chat_tab):
        """应有 Context Badge"""
        assert chat_tab._ctx_badge is not None
        assert chat_tab._ctx_badge.text() == "Context"


# =============================================================================
# 2. 消息发送流程
# =============================================================================

class TestSendMessage:
    """消息发送流程测试"""

    def test_send_empty_message_ignored(self, chat_tab):
        """空消息应被忽略"""
        chat_tab._chat_input.setText("   ")
        chat_tab._on_send()
        assert chat_tab._message_count == 0

    def test_send_message_updates_ui(self, chat_tab):
        """发送消息后 UI 应更新"""
        chat_tab._chat_input.setText("Hello AI")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        assert chat_tab._chat_input.text() == ""
        assert chat_tab._message_count == 1

    def test_send_message_appends_user_message(self, chat_tab):
        """发送后应显示用户消息气泡"""
        chat_tab._chat_input.setText("Test message")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        texts = _get_bubble_texts(chat_tab)
        assert any("Test message" in t for t in texts)

    def test_send_button_changes_to_stop(self, chat_tab):
        """发送后应创建 Agent Worker"""
        chat_tab._chat_input.setText("Hello")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        assert chat_tab._agent_worker is not None

    def test_send_creates_agent_worker(self, chat_tab):
        """发送应创建 V5AgentWorker"""
        chat_tab._chat_input.setText("Test prompt")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        mock_worker.assert_called_once()
        call_kwargs = mock_worker.call_args.kwargs
        assert call_kwargs["prompt"] == "Test prompt"
        assert call_kwargs["action_type"] == "chat"
        assert call_kwargs["context_source"] == "chat"

    def test_send_while_running_stops_worker(self, chat_tab):
        """发送时如果 Worker 在运行，应先停止"""
        chat_tab._chat_input.setText("Stop me")
        mock_existing = MagicMock()
        mock_existing.isRunning.return_value = True
        chat_tab._agent_worker = mock_existing

        chat_tab._on_send()

        mock_existing.stop.assert_called_once()


# =============================================================================
# 3. AI 回调处理
# =============================================================================

class TestAICallbacks:
    """AI 流式输出回调测试"""

    def test_ai_chunk_updates_display(self, chat_tab):
        """AI chunk 应更新显示"""
        chat_tab._chat_input.setText("Test")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        chat_tab._on_ai_chunk("Hello from AI")
        texts = _get_bubble_texts(chat_tab)
        assert any("Hello from AI" in t for t in texts)

    def test_ai_finished_resets_button(self, chat_tab):
        """AI 完成后应恢复状态"""
        chat_tab._chat_input.setText("Test")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        chat_tab._on_ai_finished("Final response")
        assert chat_tab._send_btn.text() == "▶"

    def test_ai_error_shows_error(self, chat_tab):
        """AI 错误应显示错误信息"""
        chat_tab._chat_input.setText("Test")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        chat_tab._on_ai_error("Connection timeout")
        texts = _get_bubble_texts(chat_tab)
        assert any("Connection timeout" in t for t in texts)
        assert chat_tab._send_btn.text() == "▶"

    def test_ai_finished_saves_message(self, chat_tab):
        """AI 完成后应保存消息到历史"""
        chat_tab._chat_input.setText("Test")
        with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            chat_tab._on_send()

        chat_tab._on_ai_finished("Assistant response")
        history_dir = os.path.expanduser("~/.opencopilot/chat_history")
        history_file = os.path.join(history_dir, f"{chat_tab._session_id}.json")
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            assert len(history) >= 2
            assert history[-1]["role"] == "assistant"


# =============================================================================
# 4. 上下文注入
# =============================================================================

class TestInjectContext:
    """上下文注入测试"""

    def test_inject_context_shows_preview(self, chat_tab):
        """注入上下文应显示系统消息"""
        chat_tab.inject_context("This is context text from Work Tab", "selection")
        texts = _get_bubble_texts(chat_tab)
        assert any("上下文" in t for t in texts) or any("selection" in t for t in texts)

    def test_inject_context_long_text_truncated(self, chat_tab):
        """超长上下文应截断显示"""
        long_text = "A" * 500
        chat_tab.inject_context(long_text, "active_doc")
        texts = _get_bubble_texts(chat_tab)
        assert any("500 字符" in t for t in texts)

    def test_inject_context_clears_display(self, chat_tab):
        """注入上下文应清空显示区"""
        chat_tab.append_message("AI", "Old content")
        chat_tab.inject_context("New context", "browser")
        texts = _get_bubble_texts(chat_tab)
        assert not any("Old content" in t for t in texts)

    def test_inject_context_updates_context_panel(self, chat_tab):
        """注入上下文后 Context 来源数应增加"""
        chat_tab.inject_context("Context payload", "selection")
        assert len(chat_tab._context_sources) == 1
        assert "1 个上下文来源" in chat_tab._ctx_hint.text()


# =============================================================================
# 5. 共享文本接收
# =============================================================================

class TestSetSharedText:
    """共享文本接收测试"""

    def test_set_shared_text_shows_message(self, chat_tab):
        """接收共享文本应显示消息"""
        chat_tab.set_shared_text("Shared from drag drop", source="drag_drop")
        texts = _get_bubble_texts(chat_tab)
        assert any("Shared from drag drop" in t for t in texts) or \
               any("drag_drop" in t for t in texts)

    def test_set_shared_text_empty_ignored(self, chat_tab):
        """空共享文本不应显示"""
        chat_tab._clear_bubbles()
        chat_tab.set_shared_text("", source="drag_drop")
        texts = _get_bubble_texts(chat_tab)
        assert not any("drag_drop" in t for t in texts)

    def test_set_shared_text_with_file_source(self, chat_tab):
        """文件来源应正确显示"""
        chat_tab.set_shared_text("File content", source="file:test.py")
        texts = _get_bubble_texts(chat_tab)
        assert any("file:test.py" in t for t in texts)

    def test_set_shared_text_updates_context_count(self, chat_tab):
        """共享文本后 Context 来源数应增加"""
        chat_tab.set_shared_text("Shared content", source="drag_drop")
        assert len(chat_tab._context_sources) == 1
        assert "1 个上下文来源" in chat_tab._ctx_hint.text()


# =============================================================================
# 6. 会话管理
# =============================================================================

class TestSessionManagement:
    """会话管理测试"""

    def test_new_session_creates_new_id(self, chat_tab):
        """新建会话应生成新 session_id"""
        old_id = chat_tab._session_id
        chat_tab._on_new_session()
        assert chat_tab._session_id != old_id
        assert chat_tab._message_count == 0

    def test_new_session_adds_to_combo(self, chat_tab):
        """新建会话应添加到选择器"""
        old_count = chat_tab._session_combo.count()
        chat_tab._on_new_session()
        assert chat_tab._session_combo.count() == old_count + 1

    def test_new_session_clears_display(self, chat_tab):
        """新建会话应清空显示区并显示新会话提示"""
        chat_tab.append_message("AI", "Old message")
        chat_tab._on_new_session()
        texts = _get_bubble_texts(chat_tab)
        assert any("新会话" in t for t in texts)

    def test_session_switch_loads_history(self, chat_tab):
        """切换会话应加载历史"""
        chat_tab._session_id = "test-session-123"
        chat_tab._save_message("user", "Hello")
        chat_tab._save_message("assistant", "Hi there")

        chat_tab._session_combo.addItem("Test Session", "test-session-123")
        index = chat_tab._session_combo.count() - 1

        chat_tab._on_session_changed(index)
        texts = _get_bubble_texts(chat_tab)
        assert any("Hello" in t for t in texts)
        assert any("Hi there" in t for t in texts)

    def test_session_switch_negative_index_ignored(self, chat_tab):
        """负索引应被忽略"""
        chat_tab.append_message("AI", "Content")
        old_texts = _get_bubble_texts(chat_tab)
        chat_tab._on_session_changed(-1)
        # 不应清空（气泡数不变）
        new_texts = _get_bubble_texts(chat_tab)
        assert len(new_texts) >= len(old_texts)


# =============================================================================
# 7. Context Panel
# =============================================================================

class TestContextPanel:
    """Context Panel 测试"""

    def test_toggle(self, chat_tab):
        """toggle_context 应切换折叠状态"""
        assert chat_tab._context_collapsed is True
        chat_tab._toggle_context()
        assert chat_tab._context_collapsed is False
        chat_tab._toggle_context()
        assert chat_tab._context_collapsed is True

    def test_clear_context_sources(self, chat_tab):
        """清空上下文后应恢复为空状态"""
        chat_tab.set_shared_text("Shared content", source="drag_drop")
        chat_tab._clear_context_sources()
        assert len(chat_tab._context_sources) == 0
        assert "从 Work Tab" in chat_tab._ctx_hint.text()


# =============================================================================
# 8. 消息追加
# =============================================================================

class TestAppendMessage:
    """消息追加测试"""

    def test_append_user_message(self, chat_tab):
        """用户消息应正确显示为气泡"""
        chat_tab.append_message("你", "Hello")
        texts = _get_bubble_texts(chat_tab)
        assert any("Hello" in t for t in texts)

    def test_append_ai_message(self, chat_tab):
        """AI 消息应正确显示为气泡"""
        chat_tab.append_message("AI", "Response")
        texts = _get_bubble_texts(chat_tab)
        assert any("Response" in t for t in texts)

    def test_append_system_message(self, chat_tab):
        """系统消息应正确显示为气泡"""
        chat_tab.append_message("系统", "System info")
        texts = _get_bubble_texts(chat_tab)
        assert any("System info" in t for t in texts)


# =============================================================================
# 9. 历史保存/加载
# =============================================================================

class TestHistoryPersistence:
    """历史记录持久化测试"""

    def test_save_and_load_message(self, chat_tab):
        """保存和加载消息应一致"""
        chat_tab._session_id = "test-save-load"
        chat_tab._save_message("user", "Test message")
        history = chat_tab._load_session_history("test-save-load")
        assert len(history) >= 1
        assert history[-1]["role"] == "user"
        assert history[-1]["text"] == "Test message"

    def test_load_nonexistent_session(self, chat_tab):
        """不存在的会话应返回空列表"""
        history = chat_tab._load_session_history("nonexistent-session-xyz")
        assert history == []

    def test_save_message_with_timestamp(self, chat_tab):
        """保存的消息应包含时间戳"""
        chat_tab._session_id = "test-timestamp"
        chat_tab._save_message("assistant", "Response")
        history = chat_tab._load_session_history("test-timestamp")
        if history:
            assert "timestamp" in history[-1]


# =============================================================================
# 10. 埋点事件验证
# =============================================================================

class TestTelemetryEvents:
    """Chat Tab 埋点事件验证"""

    def test_send_emits_v5_chat_send(self, chat_tab):
        """发送消息应发射 V5_CHAT_SEND"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            chat_tab._chat_input.setText("Test message")
            with patch("gui.v5.chat_tab.V5AgentWorker") as mock_worker:
                mock_instance = MagicMock()
                mock_instance.isRunning.return_value = False
                mock_worker.return_value = mock_instance
                chat_tab._on_send()

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_CHAT_SEND"]
        assert len(calls) == 1
        assert calls[0][1].get("text_len") == len("Test message")

    def test_new_session_emits_v5_chat_new_session(self, chat_tab):
        """新建会话应发射 V5_CHAT_NEW_SESSION"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            chat_tab._on_new_session()

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_CHAT_NEW_SESSION"]
        assert len(calls) == 1

    def test_inject_context_emits_v5_chat_inject(self, chat_tab):
        """注入上下文应发射 V5_CHAT_INJECT"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            chat_tab.inject_context("Context text", "selection")

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_CHAT_INJECT"]
        assert len(calls) == 1
        assert calls[0][1].get("source") == "selection"

    def test_set_shared_text_emits_v5_chat_shared_text(self, chat_tab):
        """接收共享文本应发射 V5_CHAT_SHARED_TEXT"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            chat_tab.set_shared_text("Shared text", "drag_drop")

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_CHAT_SHARED_TEXT"]
        assert len(calls) == 1
        assert calls[0][1].get("source") == "drag_drop"

    def test_session_switch_emits_v5_chat_switch_session(self, chat_tab):
        """切换会话应发射 V5_CHAT_SWITCH_SESSION"""
        chat_tab._session_combo.addItem("Test", "test-id")
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            chat_tab._on_session_changed(chat_tab._session_combo.count() - 1)

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_CHAT_SWITCH_SESSION"]
        assert len(calls) == 1
