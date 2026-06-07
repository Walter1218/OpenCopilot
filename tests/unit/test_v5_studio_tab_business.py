"""V5 Studio Tab 业务模拟测试

覆盖:
- 初始化与 UI 结构验证
- 快速创建 PPT 流程（_on_quick_open）
- 共享文本接收（set_shared_text）
- 状态更新（update_status）
- PPT 内容解析（_parse_slides_from_text）
- 打开 Studio 窗口（_on_open_studio）
- Worker 取消与错误处理
- 埋点事件验证
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import json
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
    nav.is_studio_open.return_value = False
    nav.get_studio_slides_count.return_value = 0
    return nav


@pytest.fixture
def studio_tab(qapp, mock_nav):
    """创建 StudioTabV5 实例"""
    from gui.v5.studio_tab import StudioTabV5
    with patch("gui.v5.telemetry.V5Telemetry._get_obs", return_value=None):
        tab = StudioTabV5(mock_nav)
    yield tab
    tab.deleteLater()


# =============================================================================
# 1. 初始化验证
# =============================================================================

class TestStudioTabInit:
    """Studio Tab 初始化结构验证"""

    def test_creation(self, studio_tab):
        """StudioTabV5 应能正常创建"""
        assert studio_tab is not None

    def test_has_quick_input(self, studio_tab):
        """应有快速输入区"""
        assert studio_tab._quick_input is not None
        assert studio_tab._quick_input.placeholderText() != ""

    def test_has_open_button(self, studio_tab):
        """应有打开 Studio 按钮"""
        assert studio_tab._open_btn is not None
        assert "Studio" in studio_tab._open_btn.text()

    def test_has_status_label(self, studio_tab):
        """应有状态标签"""
        assert studio_tab._status_label is not None

    def test_quick_input_max_height(self, studio_tab):
        """快速输入区应有最大高度限制"""
        assert studio_tab._quick_input.maximumHeight() == 80

    def test_quick_input_no_rich_text(self, studio_tab):
        """快速输入区不应接受富文本"""
        assert studio_tab._quick_input.acceptRichText() is False


# =============================================================================
# 2. 快速创建 PPT 流程
# =============================================================================

class TestQuickOpen:
    """快速创建 PPT 流程测试"""

    def test_quick_open_empty_input_shows_warning(self, studio_tab):
        """空输入应显示警告"""
        studio_tab._quick_input.setPlainText("")
        studio_tab._on_quick_open()
        assert "请输入" in studio_tab._status_label.text()

    def test_quick_open_creates_agent_worker(self, studio_tab):
        """有输入时应创建 V5AgentWorker"""
        studio_tab._quick_input.setPlainText("AI 发展历史")
        with patch("gui.v5.studio_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            studio_tab._on_quick_open()

        mock_worker.assert_called_once()
        call_kwargs = mock_worker.call_args.kwargs
        assert call_kwargs["action_type"] == "ppt"
        assert call_kwargs["context_source"] == "studio"
        # prompt 是模板 + 输入文本
        prompt = call_kwargs["prompt"]
        assert "AI 发展历史" in prompt or "[T-" in prompt

    def test_quick_open_shows_processing_status(self, studio_tab):
        """开始处理时应显示处理中状态"""
        studio_tab._quick_input.setPlainText("Test topic")
        with patch("gui.v5.studio_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            studio_tab._on_quick_open()

        assert "AI 生成" in studio_tab._status_label.text()

    def test_quick_open_uses_clipboard_fallback(self, studio_tab):
        """短文本应尝试从剪贴板补充"""
        studio_tab._quick_input.setPlainText("Hi")
        with patch("gui.v5.bridge.get_clipboard_text") as mock_clip:
            mock_clip.return_value = {"text": "This is a much longer text from clipboard", "status": "ok"}
            with patch("gui.v5.studio_tab.V5AgentWorker") as mock_worker:
                mock_instance = MagicMock()
                mock_instance.isRunning.return_value = False
                mock_worker.return_value = mock_instance
                studio_tab._on_quick_open()

        mock_clip.assert_called_once()

    def test_quick_open_cancel_running_worker(self, studio_tab):
        """已有 Worker 运行时应取消"""
        studio_tab._quick_input.setPlainText("Test")
        mock_existing = MagicMock()
        mock_existing.isRunning.return_value = True
        studio_tab._agent_worker = mock_existing

        studio_tab._on_quick_open()
        mock_existing.stop.assert_called_once()


# =============================================================================
# 3. PPT 生成完成回调
# =============================================================================

class TestPPTGenerated:
    """PPT 生成完成回调测试"""

    def test_ppt_generated_with_slides(self, studio_tab):
        """解析到 slides 时应打开 Studio"""
        studio_tab._quick_input.setPlainText("Topic")
        with patch("gui.v5.studio_tab.V5AgentWorker") as mock_worker:
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            mock_worker.return_value = mock_instance
            studio_tab._on_quick_open()

        # 模拟生成完成
        json_output = json.dumps({
            "slides": [
                {"title": "Slide 1", "content": "Content 1"},
                {"title": "Slide 2", "content": "Content 2"},
            ]
        })
        studio_tab._on_ppt_generated(json_output)

        studio_tab.nav.open_studio.assert_called_once()
        assert "2 页" in studio_tab._status_label.text()

    def test_ppt_generated_without_slides(self, studio_tab):
        """未解析到 slides 时也应打开 Studio"""
        studio_tab._on_ppt_generated("Plain text without JSON")

        studio_tab.nav.open_studio.assert_called_once()
        assert "未解析" in studio_tab._status_label.text()

    def test_ppt_error_shows_error(self, studio_tab):
        """生成错误应显示错误信息"""
        studio_tab._on_ppt_error("LLM service timeout")
        assert "生成失败" in studio_tab._status_label.text()
        assert "LLM service timeout" in studio_tab._status_label.text()


# =============================================================================
# 4. 共享文本接收
# =============================================================================

class TestSetSharedText:
    """共享文本接收测试"""

    def test_set_shared_text_updates_input(self, studio_tab):
        """接收共享文本应更新输入区"""
        studio_tab.set_shared_text("Shared content from drag", "drag_drop")
        assert studio_tab._quick_input.toPlainText() == "Shared content from drag"

    def test_set_shared_text_updates_status(self, studio_tab):
        """接收共享文本应更新状态"""
        studio_tab.set_shared_text("Content", "drag_drop")
        assert "已接收" in studio_tab._status_label.text()
        assert "drag_drop" in studio_tab._status_label.text()

    def test_set_shared_text_empty_ignored(self, studio_tab):
        """空共享文本不应更新"""
        studio_tab._quick_input.setPlainText("")
        studio_tab.set_shared_text("", "drag_drop")
        assert studio_tab._quick_input.toPlainText() == ""


# =============================================================================
# 5. 状态更新
# =============================================================================

class TestUpdateStatus:
    """状态更新测试"""

    def test_status_studio_open(self, studio_tab):
        """Studio 打开状态"""
        studio_tab.update_status(studio_open=True, slides_count=0, has_text=False)
        assert "已打开" in studio_tab._status_label.text()

    def test_status_has_slides(self, studio_tab):
        """有幻灯片状态"""
        studio_tab.update_status(studio_open=False, slides_count=5, has_text=False)
        assert "5 页" in studio_tab._status_label.text()

    def test_status_has_text(self, studio_tab):
        """有文本状态"""
        studio_tab.update_status(studio_open=False, slides_count=0, has_text=True)
        assert "已导入" in studio_tab._status_label.text()

    def test_status_empty(self, studio_tab):
        """空状态"""
        studio_tab.update_status(studio_open=False, slides_count=0, has_text=False)
        assert "请先导入" in studio_tab._status_label.text()


# =============================================================================
# 6. PPT 内容解析
# =============================================================================

class TestParseSlides:
    """PPT 内容解析测试"""

    def test_parse_json_code_block(self, studio_tab):
        """应能解析 ```json 代码块"""
        text = '```json\n{"slides": [{"title": "T1"}]}\n```'
        slides = studio_tab._parse_slides_from_text(text)
        assert len(slides) == 1
        assert slides[0]["title"] == "T1"

    def test_parse_direct_json(self, studio_tab):
        """应能解析直接 JSON"""
        text = '{"slides": [{"title": "T1", "content": "C1"}]}'
        slides = studio_tab._parse_slides_from_text(text)
        assert len(slides) == 1

    def test_parse_json_array(self, studio_tab):
        """应能解析方括号数组"""
        text = '[{"title": "T1"}, {"title": "T2"}]'
        slides = studio_tab._parse_slides_from_text(text)
        assert len(slides) == 2

    def test_parse_invalid_json_returns_empty(self, studio_tab):
        """无效 JSON 应返回空列表"""
        text = "Not JSON at all"
        slides = studio_tab._parse_slides_from_text(text)
        assert slides == []

    def test_parse_no_slides_key_returns_empty(self, studio_tab):
        """无 slides 键且无数组时应返回空列表"""
        text = '{"data": "just a string"}'
        slides = studio_tab._parse_slides_from_text(text)
        assert slides == []

    def test_parse_mixed_text_with_json(self, studio_tab):
        """混合文本中的 JSON 应被提取"""
        text = 'Some intro text\n```json\n{"slides": [{"title": "T1"}]}\n```\nSome outro'
        slides = studio_tab._parse_slides_from_text(text)
        assert len(slides) == 1


# =============================================================================
# 7. 打开 Studio 窗口
# =============================================================================

class TestOpenStudio:
    """打开 Studio 窗口测试"""

    def test_open_studio_emits_telemetry(self, studio_tab):
        """打开 Studio 应发射埋点"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            studio_tab._on_open_studio()

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_OPEN_STUDIO"]
        assert len(calls) == 1

    def test_open_studio_calls_nav(self, studio_tab):
        """打开 Studio 应调用 nav.open_studio"""
        studio_tab._on_open_studio()
        studio_tab.nav.open_studio.assert_called_once()


# =============================================================================
# 8. Worker 生命周期
# =============================================================================

class TestWorkerLifecycle:
    """Worker 生命周期测试"""

    def test_safely_reset_worker(self, studio_tab):
        """安全重置 Worker 不应报错"""
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        studio_tab._agent_worker = mock_worker
        studio_tab._safely_reset_worker()
        assert studio_tab._agent_worker is None

    def test_reset_worker_sets_none(self, studio_tab):
        """重置 Worker 应置空引用"""
        studio_tab._agent_worker = MagicMock()
        studio_tab._reset_worker()
        assert studio_tab._agent_worker is None


# =============================================================================
# 9. 埋点事件验证
# =============================================================================

class TestTelemetryEvents:
    """Studio Tab 埋点事件验证"""

    def test_set_shared_text_emits_event(self, studio_tab):
        """接收共享文本应发射 V5_STAB_SHARED_TEXT"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            studio_tab.set_shared_text("Text", "drag_drop")

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_SHARED_TEXT"]
        assert len(calls) == 1
        assert calls[0][1].get("source") == "drag_drop"

    def test_update_status_emits_event(self, studio_tab):
        """更新状态应发射 V5_STAB_STATUS"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            studio_tab.update_status(studio_open=True, slides_count=0, has_text=False)

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_STATUS"]
        assert len(calls) == 1

    def test_quick_open_emits_event(self, studio_tab):
        """快速创建应发射 V5_STAB_QUICK_OPEN"""
        studio_tab._quick_input.setPlainText("Topic")
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            with patch("gui.v5.studio_tab.V5AgentWorker") as mock_worker:
                mock_instance = MagicMock()
                mock_instance.isRunning.return_value = False
                mock_worker.return_value = mock_instance
                studio_tab._on_quick_open()

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_QUICK_OPEN"]
        assert len(calls) == 1

    def test_ppt_done_emits_event(self, studio_tab):
        """PPT 完成应发射 V5_STAB_PPT_DONE"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            studio_tab._on_ppt_generated('{"slides": [{"title": "T1"}]}')

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_PPT_DONE"]
        assert len(calls) == 1
        assert calls[0][1].get("slide_count") == 1

    def test_ppt_error_emits_event(self, studio_tab):
        """PPT 错误应发射 V5_STAB_PPT_ERROR"""
        with patch("gui.v5.telemetry.V5Telemetry.emit") as mock_emit:
            studio_tab._on_ppt_error("Error msg")

        calls = [c for c in mock_emit.call_args_list if c[0][0] == "V5_STAB_PPT_ERROR"]
        assert len(calls) == 1
        assert calls[0][1].get("error") == "Error msg"
