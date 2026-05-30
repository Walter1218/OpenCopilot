#!/usr/bin/env python3
"""
第一阶段功能测试：AI局部修改、快捷指令、界面简化

测试内容：
1. AI局部修改支持
2. 快捷指令功能
3. 大纲面板技术细节隐藏
4. 界面布局优化
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量，避免 GUI 阻塞
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

# 创建 QApplication（必须在创建任何 QWidget 之前）
app = QApplication(sys.argv)

def test_ai_partial_update():
    """测试 AI 局部修改支持"""
    print("\n=== 测试 AI 局部修改支持 ===")
    
    from ppt_cocreation.ai_chat_widget import AICopilotChatWidget
    
    # 创建组件
    widget = AICopilotChatWidget()
    
    # 设置测试数据
    widget.slides_data = [
        {
            "title": "原标题",
            "subtitle": "副标题",
            "type": "content",
            "layout": "text_only",
            "items": [
                {"text": "要点1", "level": 0, "content_type": "text"},
                {"text": "要点2", "level": 0, "content_type": "text"}
            ]
        },
        {
            "title": "第二页",
            "subtitle": "",
            "type": "content",
            "layout": "image_right",
            "items": []
        }
    ]
    
    # 测试1: 字段更新
    print("测试1: 字段更新")
    data1 = {"action": "update", "slide_index": 0, "field": "title", "value": "新标题"}
    msg1 = widget._apply_update(data1)
    assert widget.slides_data[0]["title"] == "新标题", f"标题更新失败: {widget.slides_data[0]['title']}"
    print(f"  ✓ {msg1}")
    
    # 测试2: 要点更新
    print("测试2: 要点更新")
    data2 = {"action": "update_item", "slide_index": 0, "item_index": 0, "field": "text", "value": "新要点1"}
    msg2 = widget._apply_update(data2)
    assert widget.slides_data[0]["items"][0]["text"] == "新要点1"
    print(f"  ✓ {msg2}")
    
    # 测试3: 添加要点
    print("测试3: 添加要点")
    data3 = {"action": "add_item", "slide_index": 0, "item": {"text": "新要点3", "level": 0, "content_type": "text"}}
    msg3 = widget._apply_update(data3)
    assert len(widget.slides_data[0]["items"]) == 3
    print(f"  ✓ {msg3}")
    
    # 测试4: 删除要点
    print("测试4: 删除要点")
    data4 = {"action": "remove_item", "slide_index": 0, "item_index": 2}
    msg4 = widget._apply_update(data4)
    assert len(widget.slides_data[0]["items"]) == 2
    print(f"  ✓ {msg4}")
    
    # 测试5: 添加幻灯片
    print("测试5: 添加幻灯片")
    data5 = {"action": "add_slide", "index": 1, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": []}}
    msg5 = widget._apply_update(data5)
    assert len(widget.slides_data) == 3
    assert widget.slides_data[1]["title"] == "新页面"
    print(f"  ✓ {msg5}")
    
    # 测试6: 删除幻灯片
    print("测试6: 删除幻灯片")
    data6 = {"action": "remove_slide", "index": 1}
    msg6 = widget._apply_update(data6)
    assert len(widget.slides_data) == 2
    print(f"  ✓ {msg6}")
    
    # 测试7: 全量更新（兼容旧模式）
    print("测试7: 全量更新（兼容旧模式）")
    data7 = {"slides": [{"title": "全量更新", "items": []}]}
    msg7 = widget._apply_update(data7)
    assert len(widget.slides_data) == 1
    assert widget.slides_data[0]["title"] == "全量更新"
    print(f"  ✓ {msg7}")
    
    print("✓ AI 局部修改支持测试通过！\n")


def test_json_extraction():
    """测试 JSON 提取功能"""
    print("=== 测试 JSON 提取功能 ===")
    
    from ppt_cocreation.ai_chat_widget import AICopilotChatWidget
    
    widget = AICopilotChatWidget()
    
    # 测试1: 从代码块提取
    print("测试1: 从代码块提取")
    text1 = '这是响应\n```json\n{"action": "update", "slide_index": 0}\n```\n结束'
    result1 = widget._extract_json(text1)
    assert result1 is not None
    data1 = json.loads(result1)
    assert data1["action"] == "update"
    print("  ✓ 代码块提取成功")
    
    # 测试2: 直接提取
    print("测试2: 直接提取")
    text2 = '响应: {"action": "add_item", "slide_index": 1}'
    result2 = widget._extract_json(text2)
    assert result2 is not None
    data2 = json.loads(result2)
    assert data2["action"] == "add_item"
    print("  ✓ 直接提取成功")
    
    # 测试3: 嵌套 JSON
    print("测试3: 嵌套 JSON")
    text3 = '{"action": "update", "item": {"text": "内容", "level": 0}}'
    result3 = widget._extract_json(text3)
    assert result3 is not None
    data3 = json.loads(result3)
    assert data3["item"]["text"] == "内容"
    print("  ✓ 嵌套 JSON 提取成功")
    
    print("✓ JSON 提取功能测试通过！\n")


def test_outline_panel_layout_mapping():
    """测试大纲面板版式映射"""
    print("=== 测试大纲面板版式映射 ===")
    
    from ppt_cocreation.outline_panel import OutlinePanel
    
    panel = OutlinePanel()
    
    # 测试版式选项
    print("测试版式选项")
    assert len(panel.LAYOUT_OPTIONS) == 7
    assert panel.LAYOUT_OPTIONS[0] == ("center", "🎯 居中封面")
    assert panel.LAYOUT_OPTIONS[1] == ("text_only", "📄 纯文本")
    assert panel.LAYOUT_OPTIONS[2] == ("image_right", "🖼️ 图右文左")
    print("  ✓ 版式选项映射正确")
    
    # 测试类型选项
    print("测试类型选项")
    assert panel.type_combo.count() == 2
    assert panel.type_combo.itemText(0) == "🎯 封面页"
    assert panel.type_combo.itemText(1) == "📄 内容页"
    print("  ✓ 类型选项映射正确")
    
    print("✓ 大纲面板版式映射测试通过！\n")


def test_system_prompt():
    """测试系统提示内容"""
    print("=== 测试系统提示内容 ===")
    
    from ppt_cocreation.ai_chat_widget import AIWorker
    
    worker = AIWorker()
    prompt = worker._build_system_prompt()
    
    # 检查是否包含局部修改指令
    assert "局部修改" in prompt, "系统提示应包含局部修改说明"
    assert '"action": "update"' in prompt, "系统提示应包含 update action 示例"
    assert '"action": "add_item"' in prompt, "系统提示应包含 add_item action 示例"
    assert '"action": "remove_item"' in prompt, "系统提示应包含 remove_item action 示例"
    print("  ✓ 系统提示包含局部修改指令")
    
    # 检查是否包含内容类型
    assert "text" in prompt, "系统提示应包含 text 类型"
    assert "image" in prompt, "系统提示应包含 image 类型"
    assert "flowchart" in prompt, "系统提示应包含 flowchart 类型"
    print("  ✓ 系统提示包含内容类型说明")
    
    print("✓ 系统提示测试通过！\n")


def test_user_message():
    """测试用户消息格式"""
    print("=== 测试用户消息格式 ===")
    
    from ppt_cocreation.ai_chat_widget import AIWorker
    
    worker = AIWorker()
    worker.slides_data = [{"title": "测试", "items": []}]
    worker.current_index = 0
    worker.instruction = "修改标题"
    
    message = worker._build_user_message()
    
    # 检查是否包含关键信息
    assert "当前幻灯片数据" in message, "用户消息应包含幻灯片数据"
    assert "修改标题" in message, "用户消息应包含用户指令"
    assert "局部修改模式" in message, "用户消息应提示使用局部修改模式"
    print("  ✓ 用户消息格式正确")
    
    print("✓ 用户消息格式测试通过！\n")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第一阶段功能测试：AI局部修改、快捷指令、界面简化")
    print("=" * 60)
    
    try:
        test_ai_partial_update()
        test_json_extraction()
        test_outline_panel_layout_mapping()
        test_system_prompt()
        test_user_message()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
