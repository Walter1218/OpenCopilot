"""
PPT 人机共创编辑器自动化测试

所有测试使用 offscreen 模式，无需 GUI 交互。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置 offscreen 模式（必须在 QApplication 创建前设置）
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 创建全局 QApplication（PyQt6 要求每个进程只有一个）
_app = QApplication.instance() or QApplication(sys.argv)

from ppt_cocreation.source_matcher import SourceMatcher, TextRange
from ppt_cocreation.source_panel import SourcePanel, SourceTextEdit
from ppt_cocreation.outline_panel import OutlinePanel
from ppt_cocreation.preview_panel import PreviewPanel, SlideRenderer
from ppt_cocreation.ai_chat_widget import AICopilotChatWidget
from ppt_cocreation.cocreation_dialog import CoCreationDialog


# 测试数据
SAMPLE_TEXT = """
OpenCopilot 是一个系统级 AI 助手，具有以下特点：

1. 上下文感知：能够自动识别用户当前的工作环境
2. 多模态支持：支持文本、图片、代码等多种内容类型
3. 人机协作：提供直观的交互界面，让用户与 AI 无缝协作

技术架构采用四层设计：
- 交互层：负责用户界面和交互逻辑
- 智能体层：负责 AI 推理和决策
- 上下文层：负责获取和管理上下文信息
- 模型层：负责底层模型调用
"""

SAMPLE_SLIDES = [
    {
        "type": "title",
        "layout": "center",
        "title": "OpenCopilot 介绍",
        "subtitle": "系统级 AI 助手"
    },
    {
        "type": "content",
        "layout": "text_only",
        "title": "核心特点",
        "items": [
            {"text": "上下文感知：能够自动识别用户当前的工作环境", "level": 0, "content_type": "text"},
            {"text": "多模态支持：支持文本、图片、代码等多种内容类型", "level": 0, "content_type": "text"},
            {"text": "人机协作：提供直观的交互界面", "level": 0, "content_type": "text"}
        ]
    },
    {
        "type": "content",
        "layout": "image_right",
        "title": "技术架构",
        "items": [
            {"text": "交互层", "level": 0, "content_type": "text"},
            {"text": "智能体层", "level": 0, "content_type": "text"},
            {"text": "上下文层", "level": 0, "content_type": "text"},
            {"text": "模型层", "level": 0, "content_type": "text"}
        ]
    },
    {
        "type": "content",
        "layout": "three_columns",
        "title": "三栏对比",
        "items": [
            {"text": "方案 A", "level": 0, "content_type": "text"},
            {"text": "方案 B", "level": 0, "content_type": "text"},
            {"text": "方案 C", "level": 0, "content_type": "text"}
        ]
    }
]


def test_source_matcher():
    """测试原文匹配器"""
    print("  [1/6] 测试原文匹配器...")
    
    matcher = SourceMatcher()
    matcher.build_mappings(SAMPLE_TEXT, SAMPLE_SLIDES)
    
    # 验证已提炼范围
    extracted = matcher.get_extracted_ranges()
    assert len(extracted) > 0, "应有已提炼范围"
    print(f"        已提炼范围: {len(extracted)} 个")
    
    # 验证位置查找
    for r in extracted:
        result = matcher.find_slide_for_position(r.start)
        # result 可能为 None（如果范围跨越多个幻灯片）
        if result:
            slide_idx, item_idx = result
            assert 0 <= slide_idx < len(SAMPLE_SLIDES), f"幻灯片索引越界: {slide_idx}"
    
    # 验证选中范围
    tr = TextRange(start=0, end=10, text="OpenCopilot")
    matcher.add_selected_range(tr)
    selected = matcher.get_selected_ranges()
    assert len(selected) == 1, "应有 1 个选中范围"
    
    matcher.clear_selected_ranges()
    assert len(matcher.get_selected_ranges()) == 0, "清除后应为空"
    
    print("        ✓ 原文匹配器测试通过")


def test_source_panel():
    """测试原文面板"""
    print("  [2/6] 测试原文面板...")
    
    panel = SourcePanel()
    
    # 设置原文
    panel.set_original_text(SAMPLE_TEXT)
    text = panel.text_edit.toPlainText()
    assert len(text) > 0, "原文不应为空"
    assert "OpenCopilot" in text, "原文应包含关键词"
    
    # 设置匹配器
    matcher = SourceMatcher()
    matcher.build_mappings(SAMPLE_TEXT, SAMPLE_SLIDES)
    panel.set_source_matcher(matcher)
    
    # 测试选中模式切换
    panel.select_btn.setChecked(True)
    assert panel.text_edit.select_mode == True, "选中模式应开启"
    
    panel.select_btn.setChecked(False)
    assert panel.text_edit.select_mode == False, "选中模式应关闭"
    
    print("        ✓ 原文面板测试通过")


def test_outline_panel():
    """测试编辑大纲面板"""
    print("  [3/6] 测试编辑大纲面板...")
    
    panel = OutlinePanel()
    
    # 加载幻灯片
    panel.set_slides_data(SAMPLE_SLIDES)
    slides = panel.get_slides_data()
    assert len(slides) == len(SAMPLE_SLIDES), f"幻灯片数量不匹配: {len(slides)} vs {len(SAMPLE_SLIDES)}"
    
    # 验证列表
    assert panel.slide_list.count() == len(SAMPLE_SLIDES), "列表项数量不匹配"
    
    # 选择幻灯片
    panel.slide_list.setCurrentRow(1)
    assert panel.current_index == 1, "当前索引应为 1"
    
    # 验证刷新
    panel._refresh_items()
    
    # 验证添加幻灯片（直接操作数据）
    original_count = len(panel.slides_data)
    new_slide = {
        "type": "content",
        "layout": "text_only",
        "title": "新幻灯片",
        "items": []
    }
    panel.slides_data.append(new_slide)
    panel._refresh_list()
    slides_after = panel.get_slides_data()
    assert len(slides_after) == original_count + 1, f"应多一张幻灯片: {len(slides_after)} vs {original_count + 1}"
    
    print("        ✓ 编辑大纲面板测试通过")


def test_preview_panel():
    """测试 PPT 预览面板"""
    print("  [4/6] 测试 PPT 预览面板...")
    
    panel = PreviewPanel()
    
    # 设置幻灯片
    panel.set_slides_data(SAMPLE_SLIDES)
    assert len(panel.slides_data) == len(SAMPLE_SLIDES), "幻灯片数据不匹配"
    assert panel.current_index == 0, "初始索引应为 0"
    
    # 测试导航
    panel.set_current_slide(1)
    assert panel.current_index == 1, "导航后索引应为 1"
    
    panel.set_current_slide(3)
    assert panel.current_index == 3, "导航后索引应为 3"
    
    # 测试边界
    panel.set_current_slide(999)
    assert panel.current_index == 3, "越界索引不应改变"
    
    panel.set_current_slide(-1)
    assert panel.current_index == 3, "负索引不应改变"
    
    # 测试渲染（不崩溃即通过）
    renderer = SlideRenderer()
    for slide in SAMPLE_SLIDES:
        renderer.set_slide(slide)
        # 触发 paintEvent
        renderer.repaint()
    
    renderer.set_slide(None)
    renderer.repaint()
    
    print("        ✓ PPT 预览面板测试通过")


def test_ai_chat_widget():
    """测试 AI 对话组件"""
    print("  [5/6] 测试 AI 对话组件...")
    
    widget = AICopilotChatWidget()
    
    # 设置幻灯片数据
    widget.set_slides_data(SAMPLE_SLIDES)
    assert widget.slides_data is not None, "幻灯片数据不应为空"
    assert len(widget.slides_data) == len(SAMPLE_SLIDES), "幻灯片数量不匹配"
    
    # 测试消息添加
    widget._add_message("测试消息", is_user=True)
    widget._add_message("AI 回复", is_user=False)
    
    # 验证 JSON 提取逻辑（模拟 AI 响应）
    import json
    test_json = '{"slides": [{"type": "title", "title": "test"}]}'
    # 测试嵌套花括号的 JSON 提取
    test_response = f"好的，这是修改后的结果：\n```json\n{test_json}\n```"
    
    # 手动验证正则匹配
    import re
    code_block = re.search(r'```(?:json)?\s*(.*?)\s*```', test_response, re.DOTALL)
    assert code_block is not None, "应匹配到代码块"
    block_content = code_block.group(1).strip()
    assert block_content.startswith('{'), "应以 { 开头"
    
    # 用括号计数提取
    depth = 0
    json_str = None
    for idx in range(len(block_content)):
        if block_content[idx] == '{':
            depth += 1
        elif block_content[idx] == '}':
            depth -= 1
            if depth == 0:
                json_str = block_content[:idx + 1]
                break
    assert json_str is not None, "应提取到 JSON"
    parsed = json.loads(json_str)
    assert 'slides' in parsed, "应包含 slides 字段"
    
    print("        ✓ AI 对话组件测试通过")


def test_cocreation_dialog():
    """测试共创对话框（不弹出窗口）"""
    print("  [6/6] 测试共创对话框...")
    
    dialog = CoCreationDialog(
        original_text=SAMPLE_TEXT,
        json_data=SAMPLE_SLIDES,
        agent_url="http://127.0.0.1:18888"
    )
    
    # 验证数据初始化
    assert len(dialog.json_data) == len(SAMPLE_SLIDES), "幻灯片数据不匹配"
    assert dialog.original_text == SAMPLE_TEXT, "原文不匹配"
    
    # 验证面板已创建
    assert dialog.source_panel is not None, "原文面板应已创建"
    assert dialog.outline_panel is not None, "大纲面板应已创建"
    assert dialog.preview_panel is not None, "预览面板应已创建"
    assert dialog.ai_chat is not None, "AI 对话组件应已创建"
    
    # 验证数据加载
    source_text = dialog.source_panel.text_edit.toPlainText()
    assert len(source_text) > 0, "原文面板应有内容"
    
    outline_slides = dialog.outline_panel.get_slides_data()
    assert len(outline_slides) == len(SAMPLE_SLIDES), "大纲面板幻灯片数量不匹配"
    
    # 验证双向联动
    dialog.outline_panel.slide_list.setCurrentRow(2)
    assert dialog.preview_panel.current_index == 2, "预览面板应联动到第 3 页"
    
    # 验证 get_final_slides
    final = dialog.get_final_slides()
    assert len(final) == len(SAMPLE_SLIDES), "最终幻灯片数量不匹配"
    
    # 验证 get_output_path
    assert dialog.get_output_path() is None, "未导出前路径应为 None"
    
    print("        ✓ 共创对话框测试通过")


def main():
    """主测试函数"""
    print("=" * 55)
    print("PPT 人机共创编辑器 - 自动化测试")
    print("=" * 55)
    print()
    
    tests = [
        test_source_matcher,
        test_source_panel,
        test_outline_panel,
        test_preview_panel,
        test_ai_chat_widget,
        test_cocreation_dialog,
    ]
    
    passed = 0
    failed = 0
    
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"        ✗ {test_fn.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 55)
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 个")
    print("=" * 55)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
