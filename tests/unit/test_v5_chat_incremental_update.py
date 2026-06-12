"""Chat Tab 增量更新测试 — _update_last_ai_message

验证多 chunk 流式输出时的增量更新逻辑（气泡 UI 版）。
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
def chat_tab(qapp, mock_nav):
    from gui.v5.chat_tab import ChatTabV5
    with patch("gui.v5.telemetry.V5Telemetry._get_obs", return_value=None):
        tab = ChatTabV5(mock_nav)
    yield tab
    tab.deleteLater()


# =============================================================================
# 1. 增量更新基础逻辑
# =============================================================================

class TestIncrementalUpdate:
    """_update_last_ai_message 增量更新测试"""

    def test_single_chunk_replaces_placeholder(self, chat_tab):
        """第一个 chunk 应替换 '思考中...' 占位"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._update_last_ai_message("Hello")
        assert chat_tab._last_bubble_label.text() == "Hello"

    def test_multiple_chunks_accumulate(self, chat_tab):
        """多个 chunk 应累积显示（最终文本覆盖）"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._update_last_ai_message("First")
        chat_tab._update_last_ai_message("First Second")
        chat_tab._update_last_ai_message("First Second Third")
        assert chat_tab._last_bubble_label.text() == "First Second Third"

    def test_empty_chunk(self, chat_tab):
        """空 chunk 不应导致异常"""
        chat_tab.append_message("AI", "placeholder")
        chat_tab._update_last_ai_message("")
        assert chat_tab._last_bubble_label.text() == ""

    def test_very_long_chunk(self, chat_tab):
        """超长 chunk 应正常处理"""
        chat_tab.append_message("AI", "placeholder")
        long_text = "A" * 5000
        chat_tab._update_last_ai_message(long_text)
        assert "A" * 100 in chat_tab._last_bubble_label.text()


# =============================================================================
# 2. 与 _on_ai_chunk 集成
# =============================================================================

class TestOnAIChunkIntegration:
    """_on_ai_chunk → _update_last_ai_message 集成测试"""

    def test_chunk_callback_updates_display(self, chat_tab):
        """_on_ai_chunk 应通过 _update_last_ai_message 更新显示"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_chunk("Response part 1")
        assert chat_tab._last_bubble_label.text() == "Response part 1"

    def test_multiple_chunks_via_callback(self, chat_tab):
        """多次 _on_ai_chunk 应累积更新"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_chunk("Step 1: ")
        chat_tab._on_ai_chunk("Step 1: Analysis ")
        chat_tab._on_ai_chunk("Step 1: Analysis complete")
        assert chat_tab._last_bubble_label.text() == "Step 1: Analysis complete"


# =============================================================================
# 3. 与 _on_ai_error 集成
# =============================================================================

class TestOnAIErrorIntegration:
    """错误回调应正确显示错误信息"""

    def test_error_shows_in_display(self, chat_tab):
        """错误应在显示区显示"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_error("Connection failed")
        # 错误消息作为新的系统/AI 气泡出现
        assert chat_tab._last_bubble_label is not None

    def test_error_resets_button(self, chat_tab):
        """错误后发送按钮应恢复"""
        chat_tab._on_ai_error("Error")
        assert chat_tab._send_btn.text() == "▶"


# =============================================================================
# 4. 完整流式输出模拟
# =============================================================================

class TestFullStreamSimulation:
    """模拟完整的多 chunk 流式输出"""

    def test_simulate_explain_stream(self, chat_tab):
        """模拟 explain 操作的流式输出"""
        chat_tab.append_message("AI", "🔄 思考中...")

        chunks = [
            "这段代码",
            "这段代码使用了递归",
            "这段代码使用了递归算法",
            "这段代码使用了递归算法来计算",
            "这段代码使用了递归算法来计算斐波那契数列",
        ]
        for chunk in chunks:
            chat_tab._update_last_ai_message(chunk)

        assert chat_tab._last_bubble_label.text() == "这段代码使用了递归算法来计算斐波那契数列"

    def test_simulate_code_block_stream(self, chat_tab):
        """模拟包含代码块的流式输出"""
        chat_tab.append_message("AI", "🔄 思考中...")

        chunks = [
            "```python",
            "```python\ndef hello():",
            "```python\ndef hello():\n    pass",
            "```python\ndef hello():\n    pass\n```",
        ]
        for chunk in chunks:
            chat_tab._update_last_ai_message(chunk)

        final = chat_tab._last_bubble_label.text()
        assert "def hello():" in final
        assert "pass" in final
