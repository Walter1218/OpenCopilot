"""
第三阶段测试：交互体验优化

测试内容：
1. 预览面板点击检测（_hit_test）
2. 预览面板右键菜单
3. 内联编辑器
4. 原文面板拖拽支持
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QColor

# 初始化 QApplication（如果还没有）
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from ppt_cocreation.preview_panel import SlideRenderer, InlineEditor, PreviewPanel
from ppt_cocreation.source_panel import SourceTextEdit


def test_hit_test_title_slide():
    """测试封面幻灯片的点击检测"""
    print_header("测试1: 封面幻灯片点击检测")
    
    renderer = SlideRenderer()
    renderer.resize(800, 450)
    
    # 设置封面幻灯片数据
    slide_data = {
        "type": "title",
        "title": "测试标题",
        "subtitle": "测试副标题"
    }
    renderer.set_slide(slide_data)
    
    # 测试标题区域点击
    # 标题区域大约在 (100, 250) 到 (900, 350)
    title_pos = QPointF(400, 300)  # 标题中心
    element_type, element_index = renderer._hit_test(title_pos)
    assert element_type == "title", f"应该检测到标题，实际: {element_type}"
    print_result("标题区域点击", element_type == "title")
    
    # 测试副标题区域点击
    subtitle_pos = QPointF(400, 410)  # 副标题中心
    element_type, element_index = renderer._hit_test(subtitle_pos)
    assert element_type == "subtitle", f"应该检测到副标题，实际: {element_type}"
    print_result("副标题区域点击", element_type == "subtitle")
    
    # 测试空白区域点击
    empty_pos = QPointF(10, 10)  # 左上角空白
    element_type, element_index = renderer._hit_test(empty_pos)
    assert element_type is None, f"应该检测到空白，实际: {element_type}"
    print_result("空白区域点击", element_type is None)
    
    return True


def test_hit_test_content_slide():
    """测试内容幻灯片的点击检测"""
    print_header("测试2: 内容幻灯片点击检测")
    
    renderer = SlideRenderer()
    renderer.resize(800, 450)
    
    # 设置内容幻灯片数据
    slide_data = {
        "type": "content",
        "title": "内容标题",
        "layout": "text_only",
        "items": [
            {"text": "第一个要点", "level": 0, "content_type": "text"},
            {"text": "第二个要点", "level": 0, "content_type": "text"},
            {"text": "第三个要点", "level": 1, "content_type": "text"}
        ]
    }
    renderer.set_slide(slide_data)
    
    # 测试标题区域点击
    title_pos = QPointF(600, 110)  # 标题中心
    element_type, element_index = renderer._hit_test(title_pos)
    assert element_type == "title", f"应该检测到标题，实际: {element_type}"
    print_result("标题区域点击", element_type == "title")
    
    # 测试第一个要点点击
    item1_pos = QPointF(600, 200)  # 第一个要点位置
    element_type, element_index = renderer._hit_test(item1_pos)
    assert element_type == "item", f"应该检测到要点，实际: {element_type}"
    assert element_index == 0, f"应该是第一个要点，实际: {element_index}"
    print_result("第一个要点点击", element_type == "item" and element_index == 0)
    
    return True


def test_hit_test_chart_slide():
    """测试图表幻灯片的点击检测"""
    print_header("测试3: 图表幻灯片点击检测")
    
    renderer = SlideRenderer()
    renderer.resize(800, 450)
    
    # 设置图表幻灯片数据
    slide_data = {
        "type": "content",
        "title": "图表标题",
        "layout": "text_only",
        "items": [
            {
                "content_type": "chart",
                "chart_type": "bar",
                "chart_data": {
                    "title": "销售数据",
                    "labels": ["Q1", "Q2", "Q3", "Q4"],
                    "datasets": [{"label": "产品A", "data": [100, 120, 150, 180]}]
                }
            }
        ]
    }
    renderer.set_slide(slide_data)
    
    # 测试图表区域点击
    chart_pos = QPointF(600, 400)  # 图表中心
    element_type, element_index = renderer._hit_test(chart_pos)
    assert element_type == "chart", f"应该检测到图表，实际: {element_type}"
    print_result("图表区域点击", element_type == "chart")
    
    return True


def test_element_text_retrieval():
    """测试获取元素文本"""
    print_header("测试4: 获取元素文本")
    
    renderer = SlideRenderer()
    
    # 设置幻灯片数据
    slide_data = {
        "type": "content",
        "title": "测试标题",
        "subtitle": "测试副标题",
        "items": [
            {"text": "第一个要点内容", "level": 0},
            {"text": "第二个要点内容", "level": 0}
        ]
    }
    renderer.set_slide(slide_data)
    
    # 测试获取标题
    title = renderer._get_element_text("title", -1)
    assert title == "测试标题", f"标题应该为'测试标题'，实际: {title}"
    print_result("获取标题", title == "测试标题")
    
    # 测试获取副标题
    subtitle = renderer._get_element_text("subtitle", -1)
    assert subtitle == "测试副标题", f"副标题应该为'测试副标题'，实际: {subtitle}"
    print_result("获取副标题", subtitle == "测试副标题")
    
    # 测试获取要点
    item_text = renderer._get_element_text("item", 0)
    assert item_text == "第一个要点内容", f"要点应该为'第一个要点内容'，实际: {item_text}"
    print_result("获取要点", item_text == "第一个要点内容")
    
    return True


def test_inline_editor():
    """测试内联编辑器"""
    print_header("测试5: 内联编辑器")
    
    editor = InlineEditor()
    
    # 测试初始化
    assert editor.element_type == "", f"初始元素类型应该为空，实际: {editor.element_type}"
    assert editor.element_index == -1, f"初始元素索引应该为-1，实际: {editor.element_index}"
    print_result("初始化状态", editor.element_type == "" and editor.element_index == -1)
    
    # 测试开始编辑
    editor.start_editing("title", -1, "测试文本", QRectF(100, 100, 200, 30))
    assert editor.element_type == "title", f"元素类型应该为'title'，实际: {editor.element_type}"
    assert editor.text() == "测试文本", f"文本应该为'测试文本'，实际: {editor.text()}"
    print_result("开始编辑", editor.element_type == "title" and editor.text() == "测试文本")
    
    return True


def test_source_text_edit_drag():
    """测试原文编辑器拖拽功能"""
    print_header("测试6: 原文编辑器拖拽功能")
    
    text_edit = SourceTextEdit()
    
    # 测试拖拽信号
    drag_text = None
    def on_drag_started(text):
        nonlocal drag_text
        drag_text = text
    
    text_edit.drag_started.connect(on_drag_started)
    
    # 设置文本
    text_edit.setPlainText("这是测试文本，用于测试拖拽功能。")
    
    # 检查拖拽相关属性
    assert hasattr(text_edit, '_drag_start_pos'), "应该有拖拽起始位置属性"
    assert hasattr(text_edit, '_drag_text'), "应该有拖拽文本属性"
    print_result("拖拽属性", hasattr(text_edit, '_drag_start_pos') and hasattr(text_edit, '_drag_text'))
    
    # 检查信号定义
    assert hasattr(text_edit, 'drag_started'), "应该有拖拽开始信号"
    print_result("拖拽信号", hasattr(text_edit, 'drag_started'))
    
    return True


def test_preview_panel_signals():
    """测试预览面板信号"""
    print_header("测试7: 预览面板信号")
    
    panel = PreviewPanel()
    
    # 测试信号定义
    assert hasattr(panel.renderer, 'element_clicked'), "应该有元素点击信号"
    assert hasattr(panel.renderer, 'title_double_clicked'), "应该有标题双击信号"
    assert hasattr(panel.renderer, 'edit_requested'), "应该有编辑请求信号"
    assert hasattr(panel.renderer, 'text_dropped'), "应该有文本拖放信号"
    print_result("信号定义", True)
    
    # 测试内联编辑器
    assert hasattr(panel, 'inline_editor'), "应该有内联编辑器"
    print_result("内联编辑器", hasattr(panel, 'inline_editor'))
    
    return True


def test_drop_handling():
    """测试拖放处理"""
    print_header("测试8: 拖放处理")
    
    renderer = SlideRenderer()
    
    # 设置幻灯片数据
    slide_data = {
        "type": "content",
        "title": "原始标题",
        "items": [
            {"text": "原始要点", "level": 0}
        ]
    }
    renderer.set_slide(slide_data)
    
    # 测试拖放到标题
    renderer._handle_drop("拖放文本", "title", -1)
    assert "拖放文本" in renderer.current_slide['title'], f"标题应该包含拖放文本，实际: {renderer.current_slide['title']}"
    print_result("拖放到标题", "拖放文本" in renderer.current_slide['title'])
    
    # 测试拖放到要点
    renderer._handle_drop("新内容", "item", 0)
    assert "新内容" in renderer.current_slide['items'][0]['text'], f"要点应该包含新内容，实际: {renderer.current_slide['items'][0]['text']}"
    print_result("拖放到要点", "新内容" in renderer.current_slide['items'][0]['text'])
    
    return True


# 辅助函数
def print_header(title: str):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name: str, passed: bool, detail: str = ""):
    """打印测试结果"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {test_name}")
    if detail:
        print(f"         {detail}")


def main():
    """运行所有测试"""
    print_header("第三阶段测试：交互体验优化")
    
    tests = [
        test_hit_test_title_slide,
        test_hit_test_content_slide,
        test_hit_test_chart_slide,
        test_element_text_retrieval,
        test_inline_editor,
        test_source_text_edit_drag,
        test_preview_panel_signals,
        test_drop_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {test_func.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"  测试结果: {passed}/{passed + failed} 通过")
    print(f"{'='*60}")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
