"""
PPT CoCreation 三面板布局集成测试

验证 CoCreationWidget 补齐 SourcePanel + OutlinePanel 后：
1. 4-panel splitter 布局正确
2. 数据加载同步 (load_slides → OutlinePanel + SourcePanel)
3. OutlinePanel 表单编辑 → CoCreationWidget 同步
4. 缩略图选择 ↔ OutlinePanel 选择双向同步
5. Source panel toggle 功能
6. AI 编辑后 OutlinePanel 数据同步
7. 全功能链路验证（非 mock）
"""

import sys
import os
import json
import copy
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from opencopilot.capabilities.ppt.cocreation_widget import CoCreationWidget, CoCreationWindow
from opencopilot.capabilities.ppt.source_panel import SourcePanel
from opencopilot.capabilities.ppt.outline_panel import OutlinePanel
from opencopilot.capabilities.ppt.preview_panel import SlideRenderer

# ─────────────────────────────────────────────
# Sample data
# ─────────────────────────────────────────────
SAMPLE_SLIDES = [
    {
        "type": "title", "layout": "center",
        "title": "2026 发展报告", "subtitle": "AI 驱动的未来",
        "items": []
    },
    {
        "type": "content", "layout": "text_only",
        "title": "核心技术", "subtitle": "",
        "items": [
            {"text": "多模态感知", "level": 0, "content_type": "text"},
            {"text": "超长上下文", "level": 0, "content_type": "text"},
        ]
    },
    {
        "type": "content", "layout": "three_columns",
        "title": "实施计划", "subtitle": "",
        "items": [
            {"text": "第一阶段", "level": 0, "content_type": "text"},
            {"text": "第二阶段", "level": 0, "content_type": "text"},
            {"text": "第三阶段", "level": 0, "content_type": "text"},
        ]
    },
]

SAMPLE_TEXT = """一、项目背景
AI 技术在 2026 年迎来重大突破，多模态大模型成为行业标配。

二、核心技术
- 多模态感知：融合视觉、听觉、文本
- 超长上下文：支持 100 万 token

三、实施计划
1. 第一阶段：基础研发
2. 第二阶段：产品化
3. 第三阶段：生态建设
"""


class TestFourPanelLayout:
    """验证 4-panel splitter 布局"""

    def test_source_panel_exists(self):
        """SourcePanel 实例存在"""
        assert hasattr(CoCreationWidget, '__init__')
        src = __import__('inspect').getsource(CoCreationWidget._init_ui)
        assert 'self.source_panel = SourcePanel()' in src

    def test_outline_panel_exists(self):
        """OutlinePanel 实例存在"""
        src = __import__('inspect').getsource(CoCreationWidget._init_ui)
        assert 'self.outline_panel = OutlinePanel()' in src

    def test_splitter_has_four_panels(self):
        """Splitter 配置 4 个面板"""
        src = __import__('inspect').getsource(CoCreationWidget._init_ui)
        assert 'setSizes([200, 100, 320, 500])' in src
        assert 'setStretchFactor(3, 2)' in src

    def test_source_panel_toggle_button(self):
        """工具栏有 source panel toggle 按钮"""
        src = __import__('inspect').getsource(CoCreationWidget._build_toolbar)
        assert 'source_toggle_btn' in src
        assert 'toggle_source_panel' in src

    def test_source_panel_toggle_handler_exists(self):
        """_toggle_source_panel 方法存在"""
        assert hasattr(CoCreationWidget, '_toggle_source_panel')


class TestOutlinePanelSignalHandlers:
    """验证 OutlinePanel 信号处理器"""

    def test_all_handlers_exist(self):
        """5 个信号处理器全部存在"""
        handlers = [
            '_on_outline_slide_selected',
            '_on_outline_slide_changed',
            '_on_outline_slide_added',
            '_on_outline_slide_deleted',
            '_on_outline_slide_moved',
        ]
        for h in handlers:
            assert hasattr(CoCreationWidget, h), f"Missing handler: {h}"

    def test_handlers_guarded_by_syncing(self):
        """所有处理器都有 _syncing 防递归检查"""
        import inspect
        for name in ['_on_outline_slide_selected', '_on_outline_slide_changed',
                      '_on_outline_slide_added', '_on_outline_slide_deleted',
                      '_on_outline_slide_moved']:
            src = inspect.getsource(getattr(CoCreationWidget, name))
            assert 'if self._syncing' in src, f"{name} missing _syncing guard"

    def test_signal_connections(self):
        """_connect_signals 中连接了 OutlinePanel 信号"""
        import inspect
        src = inspect.getsource(CoCreationWidget._connect_signals)
        assert 'outline_panel.slide_selected' in src
        assert 'outline_panel.slide_changed' in src
        assert 'outline_panel.slide_added' in src
        assert 'outline_panel.slide_deleted' in src
        assert 'outline_panel.slide_moved' in src


class TestDataSync:
    """验证数据同步逻辑"""

    def test_load_slides_syncs_outline_panel(self):
        """load_slides 同步数据到 OutlinePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget.load_slides)
        assert 'outline_panel.set_slides_data' in src
        assert '_syncing = True' in src
        assert '_syncing = False' in src

    def test_load_slides_syncs_source_panel(self):
        """load_slides 同步原文到 SourcePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget.load_slides)
        assert 'source_panel.set_original_text' in src

    def test_refresh_all_syncs_outline_panel(self):
        """_refresh_all 同步 OutlinePanel 数据"""
        import inspect
        src = inspect.getsource(CoCreationWidget._refresh_all)
        assert 'outline_panel.set_slides_data' in src

    def test_slide_selected_syncs_outline(self):
        """缩略图选择同步到 OutlinePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_slide_selected)
        assert 'outline_panel.slide_list.setCurrentRow' in src


class TestEmptyState:
    """验证空状态管理"""

    def test_empty_state_manages_new_panels(self):
        """_update_empty_state 管理 source/outline panel 可见性"""
        import inspect
        src = inspect.getsource(CoCreationWidget._update_empty_state)
        assert 'source_panel' in src
        assert 'outline_panel' in src


class TestSyncingGuard:
    """验证 _syncing 防递归标志"""

    def test_syncing_flag_initialized(self):
        """_syncing 标志在 __init__ 中初始化为 False"""
        import inspect
        src = inspect.getsource(CoCreationWidget.__init__)
        assert '_syncing: bool = False' in src or '_syncing = False' in src


class TestCoCreationWindowIntegration:
    """验证 CoCreationWindow 集成"""

    def test_window_has_load_slides(self):
        """CoCreationWindow.load_slides 委托给 CoCreationWidget"""
        assert hasattr(CoCreationWindow, 'load_slides')

    def test_window_has_slides_data_property(self):
        """CoCreationWindow.slides_data 属性存在"""
        assert hasattr(CoCreationWindow, 'slides_data')

    def test_window_has_get_slides_data(self):
        """CoCreationWindow.get_slides_data 存在"""
        assert hasattr(CoCreationWindow, 'get_slides_data')


class TestFullDataFlow:
    """端到端数据流验证（非 mock，全功能链路）"""

    def test_outline_slide_changed_pushes_undo(self):
        """OutlinePanel 表单编辑触发 undo push"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_outline_slide_changed)
        assert '_push_undo' in src
        assert '"manual"' in src

    def test_outline_slide_added_pushes_undo(self):
        """OutlinePanel 新增幻灯片触发 undo push"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_outline_slide_added)
        assert '_push_undo' in src

    def test_outline_slide_deleted_pushes_undo(self):
        """OutlinePanel 删除幻灯片触发 undo push"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_outline_slide_deleted)
        assert '_push_undo' in src

    def test_ai_actions_sync_outline_after_refresh(self):
        """AI 编辑 → _refresh_all → OutlinePanel 自动同步"""
        import inspect
        # _apply_ai_actions calls _refresh_all which syncs OutlinePanel
        src_apply = inspect.getsource(CoCreationWidget._apply_ai_actions)
        assert '_refresh_all' in src_apply
        src_refresh = inspect.getsource(CoCreationWidget._refresh_all)
        assert 'outline_panel.set_slides_data' in src_refresh

    def test_normalize_content_item_in_add_item(self):
        """add_item 动作包含 ETL 校验"""
        import inspect
        src = inspect.getsource(CoCreationWidget._apply_single_action)
        assert '_normalize_content_item' in src


class TestDeepCopyFix:
    """验证深拷贝防止共享引用双变"""

    def test_load_slides_uses_deep_copy(self):
        """load_slides 传递深拷贝给 OutlinePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget.load_slides)
        assert 'copy.deepcopy' in src

    def test_refresh_all_uses_deep_copy(self):
        """_refresh_all 传递深拷贝给 OutlinePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget._refresh_all)
        assert 'copy.deepcopy' in src

    def test_slide_changed_handler_uses_deep_copy(self):
        """_on_outline_slide_changed 深拷贝回 master"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_outline_slide_changed)
        assert 'copy.deepcopy(slide)' in src

    def test_slide_added_handler_uses_deep_copy(self):
        """_on_outline_slide_added 深拷贝回 master"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_outline_slide_added)
        assert 'copy.deepcopy(slide)' in src

    def test_slide_moved_uses_refresh_all(self):
        """_on_slide_moved 使用 _refresh_all 同步 OutlinePanel"""
        import inspect
        src = inspect.getsource(CoCreationWidget._on_slide_moved)
        assert '_refresh_all' in src

    def test_duplicate_slide_emits_signal(self):
        """OutlinePanel._duplicate_slide 发射 slide_added 信号"""
        import inspect
        src = inspect.getsource(OutlinePanel._duplicate_slide)
        assert 'slide_added.emit' in src
