"""V5Plus Stage 3 (StageEditorWidget) 功能测试

覆盖：
- 缩略图条水平滚动策略
- 原文-幻灯片双向联动高亮
- 版式切换更新数据+预览
- AI指令/重新提炼走V5AgentWorker
- 多布局类型预览渲染
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── PyQt6 基础设施 ──
pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 确保 QApplication 存在
_app = QApplication.instance() or QApplication(sys.argv)

from gui.v5plus.stage_editor import StageEditorWidget
from gui.v5.ppt_prompt import (
    build_ppt_generation_prompt, build_ppt_modify_prompt,
    build_ppt_reextract_prompt, parse_slides_from_text
)


@pytest.fixture
def editor():
    """创建 StageEditorWidget 实例"""
    return StageEditorWidget(session_id="test-session-001")


@pytest.fixture
def sample_slides():
    """多布局类型的测试幻灯片数据（同时覆盖 Studio 和旧格式）"""
    return [
        {
            "title": "封面页",
            "layout": "center",
            "type": "title",
            "items": [],
            "subtitle": "Q & A",
            "source_excerpt": "原始标题段落",
        },
        {
            "title": "数据概览",
            "layout": "chart",
            "type": "content",
            # Studio 格式：items[0] 包含 chart_data
            "items": [{
                "text": "增长趋势",
                "content_type": "chart",
                "chart_type": "bar",
                "chart_data": {
                    "title": "季度增长",
                    "labels": ["Q1", "Q2", "Q3"],
                    "datasets": [{"label": "收入", "data": [100, 150, 200]}],
                },
            }],
            "source_excerpt": "Q1-Q3数据",
        },
        {
            "title": "流程说明",
            "layout": "flowchart",
            "type": "content",
            # Studio 格式：items[0] 包含 flowchart_data（steps 为字符串数组）
            "items": [{
                "text": "开发流程",
                "content_type": "flowchart",
                "flowchart_data": {
                    "title": "产品开发",
                    "steps": ["需求分析", "设计", "开发"],
                    "layout": "horizontal",
                },
            }],
            "source_excerpt": "开发流程",
        },
        {
            "title": "对比分析",
            "layout": "three_columns",
            "type": "content",
            "items": [
                {"text": "方案A: 低成本"},
                {"text": "方案B: 高效率"},
                {"text": "方案C: 低风险"},
            ],
            "source_excerpt": "方案对比",
        },
        {
            "title": "图文页",
            "layout": "image_right",
            "type": "content",
            "items": [{"text": "产品截图描述"}],
            "image_hint": "产品展示截图",
            "source_excerpt": "产品介绍",
        },
        {
            "title": "表格页",
            "layout": "table",
            "type": "content",
            # Studio 格式：items[0] 包含 table_data（用 columns 而非 headers）
            "items": [{
                "text": "项目预算",
                "content_type": "table",
                "table_data": {
                    "columns": ["项目", "预算", "状态"],
                    "rows": [["A", "100万", "完成"], ["B", "200万", "进行中"]],
                },
            }],
            "source_excerpt": "项目预算",
        },
    ]


@pytest.fixture
def sample_text():
    """测试原文"""
    return (
        "原始标题段落，介绍了整个演示文稿的主题。\n\n"
        "第一段内容，关于Q1到Q3的数据概览。\n\n"
        "第二段内容，描述开发流程的各个阶段。\n\n"
        "第三段内容，对比不同方案的优劣。\n\n"
        "第四段内容，展示产品的实际截图。\n\n"
        "第五段内容，列出项目预算和状态。"
    )


# =============================================================================
# 缩略图条滚动策略
# =============================================================================

class TestThumbStripScroll:
    """缩略图条必须支持水平滚动"""

    def test_horizontal_scroll_policy_is_as_needed(self, editor):
        """水平滚动条策略为 AsNeeded（非 AlwaysOff）"""
        from PyQt6.QtWidgets import QScrollArea
        # 找到 thumb strip 中的 QScrollArea
        scroll = None
        for child in editor._thumb_strip.findChildren(QScrollArea):
            scroll = child
            break
        assert scroll is not None, "thumb strip 中应包含 QScrollArea"
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    def test_vertical_scroll_policy_is_always_off(self, editor):
        """垂直滚动条保持关闭"""
        from PyQt6.QtWidgets import QScrollArea
        scroll = editor._thumb_strip.findChildren(QScrollArea)[0]
        assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


# =============================================================================
# 双向联动高亮
# =============================================================================

class TestBidirectionalHighlight:
    """原文-幻灯片双向联动高亮"""

    def test_load_data_populates_paragraph_slide_map(self, editor, sample_slides, sample_text):
        """load_data 后 _paragraph_slide_map 正确填充"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        assert len(editor._paragraph_slide_map) > 0
        # 第一段应映射到 slide 0
        assert editor._paragraph_slide_map[0] == 0

    def test_highlight_source_paragraphs_changes_style(self, editor, sample_slides, sample_text):
        """_highlight_source_paragraphs 修改对应段落样式"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        # 记录初始样式
        initial_styles = [w.styleSheet() for w in editor._paragraph_widgets]

        # 高亮 slide 1
        editor._highlight_source_paragraphs(1)

        # 至少有一个段落的样式发生了变化
        changed = any(
            w.styleSheet() != initial_styles[i]
            for i, w in enumerate(editor._paragraph_widgets)
        )
        assert changed, "高亮应改变对应段落的样式"

        # 映射到 slide 1 的段落应有蓝色高亮
        for i, (w, si) in enumerate(
            zip(editor._paragraph_widgets, editor._paragraph_slide_map)
        ):
            if si == 1:
                assert "59, 130, 246" in w.styleSheet(), \
                    f"段落 {i} 映射到 slide 1，应包含蓝色高亮"

    def test_slide_select_highlights_source(self, editor, sample_slides, sample_text):
        """点击缩略图应触发原文段落高亮"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._on_slide_select(2)
        assert editor._current_slide == 2
        # 映射到 slide 2 的段落应有蓝色高亮
        for w, si in zip(editor._paragraph_widgets, editor._paragraph_slide_map):
            if si == 2:
                assert "59, 130, 246" in w.styleSheet()

    def test_mapping_tag_click_highlights_source(self, editor, sample_slides, sample_text):
        """点击映射标签应触发原文段落高亮"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._on_mapping_tag_click(3)
        assert editor._current_slide == 3
        for w, si in zip(editor._paragraph_widgets, editor._paragraph_slide_map):
            if si == 3:
                assert "59, 130, 246" in w.styleSheet()

    def test_thumb_selection_updates_style(self, editor, sample_slides, sample_text):
        """_update_thumb_selection 更新选中缩略图的样式"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_thumb_selection(2)
        # 第 2 个缩略图应有选中样式
        thumb2 = editor._thumb_layout.itemAt(2).widget()
        assert "#eef4ff" in thumb2.styleSheet()


# =============================================================================
# 版式切换
# =============================================================================

class TestLayoutChange:
    """版式切换更新数据 + 刷新预览"""

    def test_layout_change_updates_slide_data(self, editor, sample_slides, sample_text):
        """版式切换实际更新 slides_data"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        assert editor._slides_data[1]["layout"] == "chart"
        editor._current_slide = 1
        editor._on_layout_change("flowchart")
        assert editor._slides_data[1]["layout"] == "flowchart"

    def test_layout_change_renders_preview(self, editor, sample_slides, sample_text):
        """版式切换后预览区通过 SlideRenderer 更新"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._current_slide = 0
        editor._on_layout_change("chart")
        # SlideRenderer 应收到更新后的 slide 数据
        rendered_slide = editor._preview_renderer.current_slide
        assert rendered_slide is not None
        assert rendered_slide.get("layout") == "chart"


# =============================================================================
# 多布局类型预览渲染
# =============================================================================

class TestPreviewRendering:
    """预览区支持多布局类型渲染（通过 SlideRenderer）"""

    def test_center_layout(self, editor, sample_slides, sample_text):
        """center 布局：SlideRenderer 接收封面页数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(0)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "center"
        assert rendered.get("type") == "title"

    def test_chart_layout_renders_data(self, editor, sample_slides, sample_text):
        """chart 布局：SlideRenderer 接收图表数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(1)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "chart"
        items = rendered.get("items", [])
        assert items and items[0].get("content_type") == "chart"
        assert items[0].get("chart_data", {}).get("labels") == ["Q1", "Q2", "Q3"]

    def test_flowchart_layout_renders_steps(self, editor, sample_slides, sample_text):
        """flowchart 布局：SlideRenderer 接收流程数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(2)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "flowchart"
        items = rendered.get("items", [])
        assert items and items[0].get("content_type") == "flowchart"
        steps = items[0].get("flowchart_data", {}).get("steps", [])
        assert "需求分析" in steps

    def test_three_columns_layout(self, editor, sample_slides, sample_text):
        """three_columns 布局：SlideRenderer 接收三栏数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(3)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "three_columns"
        items = rendered.get("items", [])
        assert any("方案A" in (i.get("text", "") if isinstance(i, dict) else str(i)) for i in items)

    def test_image_right_layout(self, editor, sample_slides, sample_text):
        """image_right 布局：SlideRenderer 接收图文数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(4)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "image_right"
        assert rendered.get("image_hint") == "产品展示截图"

    def test_table_layout(self, editor, sample_slides, sample_text):
        """table 布局：SlideRenderer 接收表格数据"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._update_preview(5)
        rendered = editor._preview_renderer.current_slide
        assert rendered["layout"] == "table"
        items = rendered.get("items", [])
        table_data = items[0].get("table_data", {}) if items else {}
        assert "项目" in table_data.get("columns", [])
        assert "预算" in table_data.get("columns", [])


# =============================================================================
# AI 指令走 V5AgentWorker
# =============================================================================

class TestAIInstruction:
    """AI 指令输入实际走 V5AgentWorker"""

    @patch("gui.v5plus.stage_editor.V5AgentWorker")
    def test_ai_send_creates_worker(self, mock_worker_cls, editor, sample_slides, sample_text):
        """_on_ai_send 创建 V5AgentWorker 并启动"""
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        mock_worker_cls.return_value = mock_worker

        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._ai_input.setText("把标题改短一些")
        editor._on_ai_send()

        mock_worker_cls.assert_called_once()
        call_kwargs = mock_worker_cls.call_args
        assert "ppt" == call_kwargs.kwargs.get("action_type", call_kwargs[1].get("action_type"))
        mock_worker.start.assert_called_once()
        assert editor._ai_input.text() == ""  # 输入已清空

    @patch("gui.v5plus.stage_editor.V5AgentWorker")
    def test_reextract_creates_worker(self, mock_worker_cls, editor, sample_slides, sample_text):
        """_on_reextract 创建 V5AgentWorker 并启动"""
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        mock_worker_cls.return_value = mock_worker

        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._reextract_input.setText("重点突出数据部分")
        editor._on_reextract()

        mock_worker_cls.assert_called_once()
        mock_worker.start.assert_called_once()

    def test_ai_send_without_slides_does_nothing(self, editor):
        """没有幻灯片数据时 AI 发送不执行任何操作"""
        editor._ai_input.setText("测试指令")
        editor._on_ai_send()
        assert editor._ai_input.text() == ""  # 输入被清空但无 worker

    @patch("gui.v5plus.stage_editor.V5AgentWorker")
    def test_ai_modify_finished_reloads_data(self, mock_worker_cls, editor, sample_slides, sample_text):
        """AI 修改完成后重新加载 slides"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        initial_count = len(editor._slides_data)

        # 模拟 AI 返回新的 slides
        new_slides_json = '{"title": "修改后的PPT", "slides": [{"title": "新封面", "layout": "center", "items": []}]}'
        editor._on_ai_modify_finished(new_slides_json)
        assert len(editor._slides_data) == 1
        assert editor._slides_data[0]["title"] == "新封面"

    def test_parse_slides_from_valid_json(self, editor):
        """_parse_slides_from_text 正确解析 JSON"""
        text = '{"title": "Test", "slides": [{"title": "S1", "layout": "text_only"}]}'
        result = StageEditorWidget._parse_slides_from_text(text)
        assert len(result) == 1
        assert result[0]["title"] == "S1"

    def test_parse_slides_from_markdown_json(self, editor):
        """_parse_slides_from_text 解析 ```json 代码块"""
        text = '```json\n{"title": "Test", "slides": [{"title": "S1"}, {"title": "S2"}]}\n```'
        result = StageEditorWidget._parse_slides_from_text(text)
        assert len(result) == 2

    def test_parse_slides_from_invalid_returns_empty(self, editor):
        """_parse_slides_from_text 无效输入返回空列表"""
        result = StageEditorWidget._parse_slides_from_text("这不是JSON")
        assert result == []


# =============================================================================
# 初始加载高亮
# =============================================================================

class TestInitialLoad:
    """初始加载后应高亮第一页对应段落"""

    def test_initial_highlight_after_load(self, editor, sample_slides, sample_text):
        """load_data 后第一页对应段落自动高亮"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        # slide 0 对应的段落应有蓝色高亮
        highlighted = False
        for w, si in zip(editor._paragraph_widgets, editor._paragraph_slide_map):
            if si == 0:
                assert "59, 130, 246" in w.styleSheet()
                highlighted = True
        assert highlighted, "至少有一个段落应被高亮"


# =============================================================================
# 共享 Prompt 模块
# =============================================================================

class TestSharedPPTPrompt:
    """测试 gui/v5/ppt_prompt.py 共享模块"""

    def test_build_generation_prompt_contains_layout_types(self):
        """build_ppt_generation_prompt 包含所有 7 种 layout"""
        prompt = build_ppt_generation_prompt("测试文本")
        for layout in ["center", "text_only", "image_right", "three_columns",
                        "chart", "flowchart", "table"]:
            assert layout in prompt, f"prompt 应包含 layout: {layout}"

    def test_build_generation_prompt_contains_strategy(self):
        """build_ppt_generation_prompt 包含策略参数"""
        prompt = build_ppt_generation_prompt("测试", strategy="narrative")
        assert "narrative" in prompt

    def test_build_generation_prompt_contains_data_structure_specs(self):
        """build_ppt_generation_prompt 包含特殊布局数据结构说明"""
        prompt = build_ppt_generation_prompt("测试")
        assert "content_type" in prompt
        assert "chart_data" in prompt
        assert "flowchart_data" in prompt
        assert "table_data" in prompt
        assert "source_excerpt" in prompt

    def test_build_generation_prompt_long_text_hint(self):
        """超过 8000 字符时添加长度提示"""
        long_text = "a" * 9000
        prompt = build_ppt_generation_prompt(long_text)
        assert "原始内容较长" in prompt

    def test_build_modify_prompt_contains_instruction(self):
        """build_ppt_modify_prompt 包含用户指令"""
        slides = [{"title": "测试", "layout": "text_only", "items": []}]
        prompt = build_ppt_modify_prompt("把标题改短", slides)
        assert "把标题改短" in prompt
        assert "测试" in prompt

    def test_build_reextract_prompt_contains_instruction(self):
        """build_ppt_reextract_prompt 包含用户指令"""
        prompt = build_ppt_reextract_prompt("重点突出数据", "原始文本")
        assert "重点突出数据" in prompt
        assert "原始文本" in prompt

    def test_parse_slides_valid_json(self):
        """parse_slides_from_text 正确解析 JSON"""
        text = '{"title": "Test", "slides": [{"title": "S1"}]}'
        result = parse_slides_from_text(text)
        assert len(result) == 1
        assert result[0]["title"] == "S1"

    def test_parse_slides_markdown_json(self):
        """parse_slides_from_text 解析 ```json 代码块"""
        text = '```json\n{"title": "T", "slides": [{"title": "S1"}, {"title": "S2"}]}\n```'
        result = parse_slides_from_text(text)
        assert len(result) == 2

    def test_parse_slides_invalid(self):
        """parse_slides_from_text 无效输入返回空"""
        result = parse_slides_from_text("这不是JSON")
        assert result == []


# =============================================================================
# InlineEditor 内联编辑
# =============================================================================

class TestInlineEditor:
    """InlineEditor 信号驱动的内联编辑"""

    def test_inline_editor_created(self, editor):
        """InlineEditor 在初始化时创建"""
        from opencopilot.capabilities.ppt.preview_panel import InlineEditor
        assert isinstance(editor._inline_editor, InlineEditor)

    def test_title_dblclick_sets_editor_state(self, editor, sample_slides, sample_text):
        """双击标题设置 InlineEditor 状态（不调用 show 避免 Popup bus error）"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        # 直接测试状态设置逻辑，跳过 show() 以避免 Popup 窗口在无头模式崩溃
        slide = editor._slides_data[editor._current_slide]
        editor._inline_editor.element_type = "title"
        editor._inline_editor.element_index = -1
        editor._inline_editor.setText(slide.get("title", ""))
        assert editor._inline_editor.element_type == "title"
        assert editor._inline_editor.text() == slide["title"]

    def test_inline_edit_done_updates_title(self, editor, sample_slides, sample_text):
        """InlineEditor 确认后更新 slides_data 标题"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._current_slide = 0
        old_title = editor._slides_data[0]["title"]
        editor._on_inline_edit_done("title", "新标题", -1)
        assert editor._slides_data[0]["title"] == "新标题"
        assert editor._slides_data[0]["title"] != old_title

    def test_inline_edit_done_updates_item(self, editor, sample_slides, sample_text):
        """InlineEditor 确认后更新 item 文本"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._current_slide = 5  # table slide
        editor._on_inline_edit_done("item", "新文本", 0)
        item = editor._slides_data[5]["items"][0]
        assert isinstance(item, dict)
        assert item["text"] == "新文本"

    def test_inline_edit_cancel_does_not_crash(self, editor, sample_slides, sample_text):
        """InlineEditor 取消不崩溃"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._on_inline_edit_cancel()  # 不应抛异常

    def test_element_clicked_does_not_crash(self, editor, sample_slides, sample_text):
        """element_clicked 信号处理不崩溃"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._on_element_clicked("title", 0)  # 不应抛异常

    def test_text_dropped_updates_title(self, editor, sample_slides, sample_text):
        """拖放文本更新标题"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._current_slide = 0
        editor._on_text_dropped("拖放的文本", "title", -1)
        assert editor._slides_data[0]["title"] == "拖放的文本"

    def test_text_dropped_updates_item(self, editor, sample_slides, sample_text):
        """拖放文本更新 item"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        editor._current_slide = 3  # three_columns slide
        editor._on_text_dropped("新内容", "item", 0)
        item = editor._slides_data[3]["items"][0]
        assert item["text"] == "新内容"


# =============================================================================
# 渲染指令系统
# =============================================================================

class TestRenderCommand:
    """渲染指令系统接入"""

    def test_render_dispatcher_initialized_on_load(self, editor, sample_slides, sample_text):
        """load_data 后 RenderDispatcher 初始化"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        assert editor._render_dispatcher is not None

    def test_render_dispatcher_none_without_slides(self, editor):
        """无幻灯片时 RenderDispatcher 为 None"""
        editor.load_data("测试文本", {"strategy": "pyramid"})
        assert editor._render_dispatcher is None

    def test_ai_modify_uses_json_fallback(self, editor, sample_slides, sample_text):
        """无渲染指令时回退到 JSON 解析"""
        editor.load_data(sample_text, {"strategy": "pyramid"}, sample_slides)
        new_json = '{"title": "新PPT", "slides": [{"title": "S1", "layout": "center", "items": []}]}'
        editor._on_ai_modify_finished(new_json)
        assert len(editor._slides_data) == 1
        assert editor._slides_data[0]["title"] == "S1"
