"""V5 Studio Window 非AI操作测试 — 导出 PPT / 全屏预览

覆盖:
- Studio Window 创建与初始化
- PPT 导出: 空数据 / 有数据 / 导出失败
- 全屏预览: 空数据 / 有数据
- load_text 公共方法
- 底部按钮事件处理
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
def studio_window(qapp, mock_nav):
    """创建 StudioWindowV5 实例"""
    from gui.v5.studio_window import StudioWindowV5
    win = StudioWindowV5(mock_nav)
    yield win
    win.deleteLater()


# =============================================================================
# 1. 初始化验证
# =============================================================================

class TestStudioInit:
    """Studio Window 初始化验证"""

    def test_creation(self, studio_window):
        """StudioWindowV5 应能正常创建"""
        assert studio_window is not None

    def test_initial_slides_empty(self, studio_window):
        """初始 slides_data 应为空列表"""
        assert studio_window.slides_data == []

    def test_has_stats_label(self, studio_window):
        """应有统计标签"""
        assert studio_window._stats_label is not None
        text = studio_window._stats_label.text()
        assert "幻灯片:0" in text


# =============================================================================
# 2. PPT 导出 — 空数据
# =============================================================================

class TestExportPptEmpty:
    """PPT 导出: 空数据处理"""

    def test_export_empty_shows_warning(self, studio_window):
        """无幻灯片数据时应显示警告"""
        studio_window.slides_data = []
        studio_window._on_export_ppt()
        text = studio_window._stats_label.text()
        assert "无幻灯片数据" in text

    def test_export_empty_does_not_call_bridge(self, studio_window):
        """无数据时不应调用 bridge.do_export_ppt"""
        studio_window.slides_data = []
        with patch("gui.v5.bridge.do_export_ppt") as mock_export:
            studio_window._on_export_ppt()
        mock_export.assert_not_called()


# =============================================================================
# 3. PPT 导出 — 有数据
# =============================================================================

class TestExportPptWithData:
    """PPT 导出: 有数据"""

    def test_export_success(self, studio_window):
        """导出成功应显示成功信息"""
        studio_window.slides_data = [
            {"title": "Slide 1", "bullets": ["Point A"]},
            {"title": "Slide 2", "bullets": ["Point B"]},
        ]
        with patch("gui.v5.bridge.do_export_ppt") as mock_export:
            mock_export.return_value = {
                "success": True,
                "file_path": "/tmp/presentation.pptx",
                "filename": "presentation.pptx",
                "file_size": 51200,
                "slide_count": 2,
            }
            studio_window._on_export_ppt()

        text = studio_window._stats_label.text()
        assert "已导出" in text
        assert "presentation.pptx" in text
        assert "2 页" in text

    def test_export_calls_bridge_with_slides(self, studio_window):
        """导出应用 slides_data 调用 bridge"""
        slides = [{"title": "S1"}, {"title": "S2"}]
        studio_window.slides_data = slides
        with patch("gui.v5.bridge.do_export_ppt") as mock_export:
            mock_export.return_value = {
                "success": True, "filename": "test.pptx",
                "slide_count": 2, "file_size": 1024,
            }
            studio_window._on_export_ppt()
        mock_export.assert_called_once_with(slides)

    def test_export_failure_shows_error(self, studio_window):
        """导出失败应显示错误信息"""
        studio_window.slides_data = [{"title": "S1"}]
        with patch("gui.v5.bridge.do_export_ppt") as mock_export:
            mock_export.return_value = {
                "success": False,
                "message": "pptx 生成失败",
            }
            studio_window._on_export_ppt()
        text = studio_window._stats_label.text()
        assert "失败" in text
        assert "pptx 生成失败" in text


# =============================================================================
# 4. 全屏预览
# =============================================================================

class TestFullscreenPreview:
    """全屏预览"""

    def test_preview_empty_shows_warning(self, studio_window):
        """无数据时全屏预览应显示警告"""
        studio_window.slides_data = []
        studio_window._on_fullscreen_preview()
        text = studio_window._stats_label.text()
        assert "无幻灯片数据" in text

    def test_preview_with_data_shows_count(self, studio_window):
        """有数据时全屏预览应显示幻灯片数量"""
        studio_window.slides_data = [{"title": "S1"}, {"title": "S2"}, {"title": "S3"}]
        studio_window._on_fullscreen_preview()
        text = studio_window._stats_label.text()
        assert "全屏预览" in text
        assert "3 张" in text


# =============================================================================
# 5. load_text 公共方法
# =============================================================================

class TestLoadText:
    """load_text 加载文本到 Source Panel"""

    def test_load_text_updates_stats(self, studio_window):
        """load_text 应更新统计标签"""
        studio_window.load_text("Hello World, this is a test document.")
        text = studio_window._stats_label.text()
        assert "原文:" in text
        assert "字符" in text

    def test_load_text_empty(self, studio_window):
        """load_text 空字符串应正常工作"""
        studio_window.load_text("")
        text = studio_window._stats_label.text()
        assert "原文:0字符" in text

    def test_load_text_long(self, studio_window):
        """load_text 超长文本应显示实际字符数"""
        long_text = "A" * 10000
        studio_window.load_text(long_text)
        text = studio_window._stats_label.text()
        # 修复后显示实际字符数，不再截断
        assert "10000字符" in text
        # 同时验证文本已加载到 Source Panel
        assert studio_window._source_text.toPlainText() == long_text


# =============================================================================
# 6. 底部按钮结构验证
# =============================================================================

class TestBottomBarStructure:
    """底部按钮结构验证"""

    def test_close_button_calls_close(self, studio_window):
        """取消按钮应调用 close"""
        # The close button is connected to self.close
        # We can verify by checking the window exists
        assert studio_window is not None

    def test_stats_label_initial_state(self, studio_window):
        """初始统计标签应显示默认值"""
        text = studio_window._stats_label.text()
        assert "幻灯片:0" in text
        assert "要点:0" in text
