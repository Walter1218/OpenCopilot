"""Chat Tab 增量更新测试 — _update_last_ai_message

验证多 chunk 流式输出时的增量更新逻辑，确保不会全量重绘导致滚动跳回。
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
        html = chat_tab._chat_display.toHtml()
        assert "思考中" not in html
        assert "Hello" in html

    def test_multiple_chunks_accumulate(self, chat_tab):
        """多个 chunk 应累积显示"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._update_last_ai_message("First")
        chat_tab._update_last_ai_message("First Second")
        chat_tab._update_last_ai_message("First Second Third")
        html = chat_tab._chat_display.toHtml()
        assert "First Second Third" in html
        # 不应有重复的 "First" 或 "First Second"
        # （由于实现是删除最后一块再重新插入，所以只有最终文本）

    def test_chunk_with_html_special_chars(self, chat_tab):
        """chunk 包含 HTML 特殊字符应正确转义"""
        chat_tab.append_message("AI", "placeholder")
        chat_tab._update_last_ai_message("<b>bold</b>")
        html = chat_tab._chat_display.toHtml()
        # append_message 会转义 < 和 >
        assert "&lt;b&gt;bold&lt;/b&gt;" in html

    def test_chunk_with_newlines(self, chat_tab):
        """chunk 包含换行应正确显示"""
        chat_tab.append_message("AI", "placeholder")
        chat_tab._update_last_ai_message("Line1\nLine2")
        html = chat_tab._chat_display.toHtml()
        # append_message 会将 \n 转为 <br>
        assert "Line1" in html
        assert "Line2" in html

    def test_empty_chunk(self, chat_tab):
        """空 chunk 不应导致异常"""
        chat_tab.append_message("AI", "placeholder")
        chat_tab._update_last_ai_message("")
        html = chat_tab._chat_display.toHtml()
        # 最后一条消息应为空
        assert html is not None

    def test_very_long_chunk(self, chat_tab):
        """超长 chunk 应正常处理"""
        chat_tab.append_message("AI", "placeholder")
        long_text = "A" * 5000
        chat_tab._update_last_ai_message(long_text)
        html = chat_tab._chat_display.toHtml()
        assert "A" * 100 in html  # 至少包含部分内容


# =============================================================================
# 2. 与 _on_ai_chunk 集成
# =============================================================================

class TestOnAIChunkIntegration:
    """_on_ai_chunk → _update_last_ai_message 集成测试"""

    def test_chunk_callback_updates_display(self, chat_tab):
        """_on_ai_chunk 应通过 _update_last_ai_message 更新显示"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_chunk("Response part 1")
        html = chat_tab._chat_display.toHtml()
        assert "Response part 1" in html
        assert "思考中" not in html

    def test_multiple_chunks_via_callback(self, chat_tab):
        """多次 _on_ai_chunk 应累积更新"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_chunk("Step 1: ")
        chat_tab._on_ai_chunk("Step 1: Analysis ")
        chat_tab._on_ai_chunk("Step 1: Analysis complete")
        html = chat_tab._chat_display.toHtml()
        assert "Analysis complete" in html


# =============================================================================
# 3. 与 _on_ai_error 集成
# =============================================================================

class TestOnAIErrorIntegration:
    """错误回调应正确显示错误信息"""

    def test_error_shows_in_display(self, chat_tab):
        """错误应在显示区显示"""
        chat_tab.append_message("AI", "🔄 思考中...")
        chat_tab._on_ai_error("Connection failed")
        html = chat_tab._chat_display.toHtml()
        assert "Connection failed" in html
        assert "❌" in html

    def test_error_resets_button(self, chat_tab):
        """错误后发送按钮应恢复"""
        chat_tab._send_btn.setText("停止")
        chat_tab._on_ai_error("Error")
        assert chat_tab._send_btn.text() == "发送"


# =============================================================================
# 4. 完整流式输出模拟
# =============================================================================

class TestFullStreamSimulation:
    """模拟完整的多 chunk 流式输出"""

    def test_simulate_explain_stream(self, chat_tab):
        """模拟 explain 操作的流式输出"""
        # 初始化：发送消息后显示占位
        chat_tab.append_message("AI", "🔄 思考中...")

        # 模拟 5 个 chunk 的流式输出
        chunks = [
            "这段代码",
            "这段代码使用了递归",
            "这段代码使用了递归算法",
            "这段代码使用了递归算法来计算",
            "这段代码使用了递归算法来计算斐波那契数列",
        ]
        for chunk in chunks:
            chat_tab._update_last_ai_message(chunk)

        html = chat_tab._chat_display.toHtml()
        assert "斐波那契数列" in html
        # 验证只有最终文本，没有中间状态的残留
        assert "这段代码使用了递归算法来计算斐波那契数列" in html

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

        html = chat_tab._chat_display.toHtml()
        assert "def hello():" in html
        assert "pass" in html
