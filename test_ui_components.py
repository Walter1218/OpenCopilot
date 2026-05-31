"""
PPT 共创 UI 组件集成测试

使用真实代码验证所有 UI 组件的：
1. 模块导入兼容性（PyQt5 vs PyQt6）
2. 类实例化（offscreen 模式）
3. 信号/槽连接
4. 与 API 的数据流对接
5. 组件间交互
"""

import os
import sys
import json

# 强制 offscreen 模式，避免需要真实显示器
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, os.path.dirname(__file__))

# 必须在任何 QWidget 创建之前初始化 QApplication
from PyQt6.QtWidgets import QApplication
_qapp = QApplication.instance() or QApplication(sys.argv)

PASS = 0
FAIL = 0
ERRORS = []


def report(name, passed, detail=""):
    global PASS, FAIL, ERRORS
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {name}")
    if detail:
        print(f"       {detail}")
    if passed:
        PASS += 1
    else:
        FAIL += 1
        ERRORS.append(f"{name}: {detail}")


def test_import_compatibility():
    """测试 1: PyQt 导入兼容性"""
    print("\n" + "=" * 60)
    print("  测试 1: PyQt 导入兼容性")
    print("=" * 60)
    
    # 检查 PyQt6 是否可用
    try:
        from PyQt6.QtWidgets import QApplication
        report("PyQt6 可用", True)
        pyqt_version = 6
    except ImportError:
        report("PyQt6 可用", False, "PyQt6 未安装")
        return False
    
    # 检查 SuggestionBubble 是否有真实的 UI 能力
    from ppt_cocreation.suggestion_bubble import SuggestionBubble as SB
    from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel as CAP
    
    has_signal = hasattr(SB, 'accepted') and hasattr(SB, 'dismissed')
    report("SuggestionBubble 有信号定义", has_signal,
           f"accepted={hasattr(SB, 'accepted')}, dismissed={hasattr(SB, 'dismissed')}")
    
    # 检查是否继承自 QWidget（而非 object 空壳）
    from PyQt6.QtWidgets import QWidget as QW
    is_real = issubclass(SB, QW)
    report("SuggestionBubble 是真实 QWidget 实现", is_real,
           f"基类: {SB.__bases__}")
    
    has_signal = hasattr(CAP, 'suggestion_clicked')
    report("ContentAnalysisPanel 有信号定义", has_signal,
           f"suggestion_clicked={has_signal}")
    
    is_real = issubclass(CAP, QW)
    report("ContentAnalysisPanel 是真实 QWidget 实现", is_real,
           f"基类: {CAP.__bases__}")
    
    return True


def test_qapp_creation():
    """测试 2: QApplication 创建"""
    print("\n" + "=" * 60)
    print("  测试 2: QApplication 创建")
    print("=" * 60)
    
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    report("QApplication 创建", app is not None)
    return app


def test_widget_creation(app):
    """测试 3: Widget 实例化"""
    print("\n" + "=" * 60)
    print("  测试 3: Widget 实例化")
    print("=" * 60)
    
    # 测试 ChatMessageWidget
    try:
        from ppt_cocreation.ai_chat_widget import ChatMessageWidget
        user_msg = ChatMessageWidget("测试用户消息", is_user=True)
        ai_msg = ChatMessageWidget("测试AI回复", is_user=False)
        report("ChatMessageWidget 创建", True)
    except Exception as e:
        report("ChatMessageWidget 创建", False, str(e))
    
    # 测试 SuggestionBubble (应该用 PyQt6)
    try:
        from ppt_cocreation.suggestion_bubble import SuggestionBubble
        test_suggestion = {
            "type": "data_to_chart",
            "title": "测试建议",
            "description": "测试描述",
            "confidence": 0.85
        }
        bubble = SuggestionBubble(test_suggestion)
        report("SuggestionBubble 创建", True)
        
        # 检查是否有真实属性
        has_style = hasattr(bubble, 'SUGGESTION_STYLES')
        report("SuggestionBubble 有样式配置", has_style,
               f"SUGGESTION_STYLES={has_style}")
    except Exception as e:
        report("SuggestionBubble 创建", False, str(e))
    
    # 测试 ContentAnalysisPanel
    try:
        from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel
        panel = ContentAnalysisPanel()
        report("ContentAnalysisPanel 创建", True)
        
        # 检查是否有真实属性
        has_types = hasattr(panel, 'CONTENT_TYPE_CONFIG')
        report("ContentAnalysisPanel 有类型配置", has_types,
               f"CONTENT_TYPE_CONFIG={has_types}")
    except Exception as e:
        report("ContentAnalysisPanel 创建", False, str(e))
    
    # 测试 AICopilotChatWidget
    try:
        from ppt_cocreation.ai_chat_widget import AICopilotChatWidget
        # 使用 PPT API 的端口
        chat_widget = AICopilotChatWidget(agent_url="http://127.0.0.1:8088")
        report("AICopilotChatWidget 创建", True)
        
        # 检查内部组件
        has_analysis = hasattr(chat_widget, 'analysis_panel')
        has_suggestion = hasattr(chat_widget, 'suggestion_manager')
        report("AICopilotChatWidget 集成了分析面板", has_analysis)
        report("AICopilotChatWidget 集成了建议管理器", has_suggestion)
    except Exception as e:
        report("AICopilotChatWidget 创建", False, str(e))
        chat_widget = None
    
    return chat_widget


def test_suggestion_styles():
    """测试 4: 建议类型配置完整性"""
    print("\n" + "=" * 60)
    print("  测试 4: 建议类型配置完整性")
    print("=" * 60)
    
    from ppt_cocreation.suggestion_bubble import SuggestionBubble
    
    expected_types = [
        "visual_enhance", "content_optimize", "structure_improve",
        "style_consistent", "data_to_chart", "text_to_table",
        "steps_to_flowchart", "content_too_long", "default"
    ]
    
    styles = getattr(SuggestionBubble, 'SUGGESTION_STYLES', {})
    if not styles:
        report("建议类型配置存在", False, "SUGGESTION_STYLES 为空或不存在")
        return
    
    report("建议类型配置存在", True, f"共 {len(styles)} 种类型")
    
    for t in expected_types:
        if t in styles:
            style = styles[t]
            has_icon = "icon" in style
            has_color = "color" in style
            has_title = "title" in style
            report(f"  类型 '{t}'", has_icon and has_color and has_title,
                   f"icon={style.get('icon','?')} color={style.get('color','?')}")
        else:
            report(f"  类型 '{t}'", False, "未配置")


def test_content_type_config():
    """测试 5: 内容类型配置完整性"""
    print("\n" + "=" * 60)
    print("  测试 5: 内容类型配置完整性")
    print("=" * 60)
    
    from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel
    
    expected_types = [
        "text", "data_comparison", "time_series",
        "process", "person_attributes", "list_items"
    ]
    
    config = getattr(ContentAnalysisPanel, 'CONTENT_TYPE_CONFIG', {})
    if not config:
        report("内容类型配置存在", False, "CONTENT_TYPE_CONFIG 为空或不存在")
        return
    
    report("内容类型配置存在", True, f"共 {len(config)} 种类型")
    
    for t in expected_types:
        if t in config:
            cfg = config[t]
            has_icon = "icon" in cfg
            has_label = "label" in cfg
            report(f"  类型 '{t}'", has_icon and has_label,
                   f"icon={cfg.get('icon','?')} label={cfg.get('label','?')}")
        else:
            report(f"  类型 '{t}'", False, "未配置")


def test_visualization_types():
    """测试 6: 可视化类型配置"""
    print("\n" + "=" * 60)
    print("  测试 6: 可视化类型配置")
    print("=" * 60)
    
    from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel
    
    expected_viz = [
        "bar_chart", "line_chart", "pie_chart",
        "table", "flowchart", "timeline", "list", "text"
    ]
    
    config = getattr(ContentAnalysisPanel, 'VISUAL_TYPE_CONFIG', {})
    if not config:
        report("可视化类型配置存在", False, "VISUAL_TYPE_CONFIG 为空或不存在")
        return
    
    report("可视化类型配置存在", True, f"共 {len(config)} 种类型")
    
    for v in expected_viz:
        if v in config:
            report(f"  可视化 '{v}'", True, f"label={config[v].get('label', '?')}")
        else:
            report(f"  可视化 '{v}'", False, "未配置")


def test_api_data_flow(chat_widget):
    """测试 7: API 数据流对接"""
    print("\n" + "=" * 60)
    print("  测试 7: API 数据流对接（真实 API 调用）")
    print("=" * 60)
    
    import httpx
    
    BASE_URL = "http://localhost:8088"
    
    # 测试内容分析 → 分析面板数据流
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/analyze",
                       json={"content": "产品A销量100万，产品B销量200万，产品C销量150万"},
                       timeout=10.0)
        data = r.json()
        
        content_type = data.get("content_type")
        report("API 返回内容类型", content_type is not None, f"content_type={content_type}")
        
        # 尝试用返回数据更新分析面板
        if chat_widget and hasattr(chat_widget, 'analysis_panel'):
            try:
                panel = chat_widget.analysis_panel
                # ContentAnalysisPanel.update_analysis 应该接受 dict
                if hasattr(panel, 'update_analysis'):
                    panel.update_analysis(data)
                    report("分析面板接收 API 数据", True)
                else:
                    report("分析面板接收 API 数据", False, "无 update_analysis 方法")
            except Exception as e:
                report("分析面板接收 API 数据", False, str(e))
    except Exception as e:
        report("API 内容分析", False, str(e))
    
    # 测试建议生成 → 建议气泡数据流
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/suggest",
                       json={
                           "context": {
                               "title": "测试PPT",
                               "current_slide": 0,
                               "slides": [{
                                   "index": 0,
                                   "title": "销售数据",
                                   "content": "产品A销量100万，产品B销量200万",
                                   "layout": "center",
                                   "items": []
                               }]
                           },
                           "max_suggestions": 2
                       },
                       timeout=10.0)
        data = r.json()
        
        suggestions = data.get("suggestions", [])
        report("API 返回建议", len(suggestions) > 0, f"建议数: {len(suggestions)}")
        
        if suggestions:
            s = suggestions[0]
            has_type = "type" in s
            has_title = "title" in s
            report("建议数据结构完整", has_type and has_title,
                   f"type={s.get('type')}, title={s.get('title', '')[:30]}")
            
            # 尝试用建议数据创建气泡
            try:
                from ppt_cocreation.suggestion_bubble import SuggestionBubble
                bubble = SuggestionBubble(s)
                report("建议气泡接收 API 数据", True,
                       f"类型: {s.get('type')}, 标题: {s.get('title', '')[:20]}")
            except Exception as e:
                report("建议气泡接收 API 数据", False, str(e))
    except Exception as e:
        report("API 建议生成", False, str(e))


def test_slides_data_update(chat_widget):
    """测试 8: 幻灯片数据更新流程"""
    print("\n" + "=" * 60)
    print("  测试 8: 幻灯片数据更新流程")
    print("=" * 60)
    
    if not chat_widget:
        report("幻灯片更新测试", False, "chat_widget 未创建")
        return
    
    test_slides = [
        {
            "index": 0,
            "title": "公司简介",
            "content": "我们是一家AI创业公司",
            "layout": "center",
            "items": [
                {"text": "创立于2020年", "level": 0, "content_type": "text"},
                {"text": "团队50人", "level": 0, "content_type": "text"}
            ]
        },
        {
            "index": 1,
            "title": "产品数据",
            "content": "核心产品A日活100万",
            "layout": "text_only",
            "items": []
        }
    ]
    
    # 测试 set_slides_data
    received_update = []
    def on_slides_updated(slides):
        received_update.append(slides)
    
    chat_widget.slides_updated.connect(on_slides_updated)
    chat_widget.set_slides_data(test_slides, current_index=0)
    
    report("set_slides_data 执行成功", True)
    report("slides_data 已更新", len(chat_widget.slides_data) == 2,
           f"slides_count={len(chat_widget.slides_data)}")
    report("current_index 已设置", chat_widget.current_index == 0,
           f"current_index={chat_widget.current_index}")
    
    # 测试 JSON 提取
    test_cases = [
        (
            '```json\n{"action": "update", "slide_index": 0, "field": "title", "value": "新标题"}\n```',
            "update"
        ),
        (
            '好的，我来修改标题。\n\n```json\n{"action": "add_item", "slide_index": 0, "item": {"text": "新要点", "level": 0}}\n```',
            "add_item"
        ),
        (
            '{"action": "remove_item", "slide_index": 0, "item_index": 0}',
            "remove_item"
        ),
    ]
    
    for text, expected_action in test_cases:
        json_str = chat_widget._extract_json(text)
        if json_str:
            data = json.loads(json_str)
            actual_action = data.get("action")
            report(f"JSON 提取 ({expected_action})",
                   actual_action == expected_action,
                   f"提取到: {actual_action}")
        else:
            report(f"JSON 提取 ({expected_action})", False, "未提取到 JSON")


def test_apply_update_logic(chat_widget):
    """测试 9: 更新应用逻辑"""
    print("\n" + "=" * 60)
    print("  测试 9: 更新应用逻辑")
    print("=" * 60)
    
    if not chat_widget:
        report("更新逻辑测试", False, "chat_widget 未创建")
        return
    
    # 先设置初始数据
    slides = [
        {
            "title": "原始标题",
            "content": "原始内容",
            "layout": "center",
            "items": [
                {"text": "要点1", "level": 0, "content_type": "text"},
                {"text": "要点2", "level": 0, "content_type": "text"}
            ]
        }
    ]
    chat_widget.set_slides_data(slides, current_index=0)
    
    # 测试 update 操作
    try:
        msg = chat_widget._apply_update({
            "action": "update",
            "slide_index": 0,
            "field": "title",
            "value": "新标题"
        })
        report("update 操作",
               chat_widget.slides_data[0]["title"] == "新标题",
               f"标题: {chat_widget.slides_data[0]['title']}")
    except Exception as e:
        report("update 操作", False, str(e))
    
    # 测试 add_item 操作
    try:
        msg = chat_widget._apply_update({
            "action": "add_item",
            "slide_index": 0,
            "item": {"text": "新要点", "level": 0, "content_type": "text"}
        })
        items = chat_widget.slides_data[0].get("items", [])
        report("add_item 操作",
               len(items) == 3,
               f"要点数: {len(items)}")
    except Exception as e:
        report("add_item 操作", False, str(e))
    
    # 测试 remove_item 操作
    try:
        msg = chat_widget._apply_update({
            "action": "remove_item",
            "slide_index": 0,
            "item_index": 0
        })
        items = chat_widget.slides_data[0].get("items", [])
        report("remove_item 操作",
               len(items) == 2,
               f"要点数: {len(items)}")
    except Exception as e:
        report("remove_item 操作", False, str(e))
    
    # 测试 add_slide 操作
    try:
        msg = chat_widget._apply_update({
            "action": "add_slide",
            "index": 1,
            "slide": {"title": "新页面", "content": "", "layout": "text_only", "items": []}
        })
        report("add_slide 操作",
               len(chat_widget.slides_data) == 2,
               f"幻灯片数: {len(chat_widget.slides_data)}")
    except Exception as e:
        report("add_slide 操作", False, str(e))
    
    # 测试 remove_slide 操作
    try:
        msg = chat_widget._apply_update({
            "action": "remove_slide",
            "index": 1
        })
        report("remove_slide 操作",
               len(chat_widget.slides_data) == 1,
               f"幻灯片数: {len(chat_widget.slides_data)}")
    except Exception as e:
        report("remove_slide 操作", False, str(e))
    
    # 测试边界：越界索引
    try:
        chat_widget._apply_update({
            "action": "update",
            "slide_index": 99,
            "field": "title",
            "value": "越界"
        })
        report("越界索引处理", False, "应该抛出异常但没有")
    except ValueError:
        report("越界索引处理", True, "正确抛出 ValueError")
    except Exception as e:
        report("越界索引处理", True, f"抛出了异常: {type(e).__name__}")


def test_analysis_panel_update():
    """测试 10: 分析面板更新"""
    print("\n" + "=" * 60)
    print("  测试 10: 分析面板更新")
    print("=" * 60)
    
    try:
        from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel
        panel = ContentAnalysisPanel()
        
        test_analysis = {
            "content_type": "data_comparison",
            "quality_score": 0.85,
            "confidence": 0.92,
            "key_points": ["产品A销量100万", "产品B销量200万"],
            "entities": [
                {"type": "number", "text": "100万"},
                {"type": "number", "text": "200万"}
            ],
            "suggestions": [
                {"type": "data_to_chart", "title": "数据可视化建议", "description": "建议转换为柱状图对比"}
            ],
            "recommended_visual": "bar_chart"
        }
        
        if hasattr(panel, 'update_analysis'):
            panel.update_analysis(test_analysis)
            report("分析面板 update_analysis 调用", True)
            
            # 检查内部状态
            if hasattr(panel, '_current_data'):
                report("分析面板数据已更新",
                       panel._current_data is not None,
                       f"content_type={panel._current_data.get('content_type') if panel._current_data else 'N/A'}")
        else:
            report("分析面板 update_analysis 方法", False, "方法不存在")
    except Exception as e:
        report("分析面板更新", False, str(e))


def test_manager_classes():
    """测试 11: Manager 类"""
    print("\n" + "=" * 60)
    print("  测试 11: Manager 类")
    print("=" * 60)
    
    # SuggestionBubbleManager
    try:
        from ppt_cocreation.suggestion_bubble import SuggestionBubbleManager
        from PyQt6.QtWidgets import QWidget as QW
        parent = QW()
        manager = SuggestionBubbleManager(parent)
        report("SuggestionBubbleManager 创建", True)
        
        has_show = hasattr(manager, 'show_suggestion')
        report("SuggestionBubbleManager.show_suggestion", has_show)
    except Exception as e:
        report("SuggestionBubbleManager 创建", False, str(e))
    
    # AnalysisPanelManager
    try:
        from ppt_cocreation.content_analysis_panel import ContentAnalysisPanel, AnalysisPanelManager
        panel = ContentAnalysisPanel()
        manager = AnalysisPanelManager(panel)
        report("AnalysisPanelManager 创建", True)
        
        has_update = hasattr(manager, 'update_analysis_debounced')
        report("AnalysisPanelManager.update_analysis_debounced", has_update)
    except Exception as e:
        report("AnalysisPanelManager 创建", False, str(e))


def test_module_exports():
    """测试 12: 模块导出"""
    print("\n" + "=" * 60)
    print("  测试 12: 模块导出 (__init__.py)")
    print("=" * 60)
    
    from ppt_cocreation import (
        SuggestionBubble, SuggestionBubbleManager,
        ContentAnalysisPanel, AnalysisPanelManager
    )
    
    report("SuggestionBubble 导出", SuggestionBubble is not None)
    report("SuggestionBubbleManager 导出", SuggestionBubbleManager is not None)
    report("ContentAnalysisPanel 导出", ContentAnalysisPanel is not None)
    report("AnalysisPanelManager 导出", AnalysisPanelManager is not None)


def main():
    print("\n" + "=" * 60)
    print("  PPT 共创 UI 组件集成测试")
    print("=" * 60)
    print("  验证 UI 组件与真实 API 的对接能力")
    print("=" * 60)
    
    # 1. 导入兼容性
    if not test_import_compatibility():
        print("\n❌ PyQt6 不可用，无法继续测试")
        return
    
    # 2. QApplication
    app = test_qapp_creation()
    
    # 3. Widget 实例化
    chat_widget = test_widget_creation(app)
    
    # 4. 建议类型配置
    test_suggestion_styles()
    
    # 5. 内容类型配置
    test_content_type_config()
    
    # 6. 可视化类型
    test_visualization_types()
    
    # 7. API 数据流
    test_api_data_flow(chat_widget)
    
    # 8. 幻灯片数据更新
    test_slides_data_update(chat_widget)
    
    # 9. 更新应用逻辑
    test_apply_update_logic(chat_widget)
    
    # 10. 分析面板更新
    test_analysis_panel_update()
    
    # 11. Manager 类
    test_manager_classes()
    
    # 12. 模块导出
    test_module_exports()
    
    # 汇总
    total = PASS + FAIL
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)
    print(f"\n  总计: {total} 项测试")
    print(f"  通过: {PASS} ✅")
    print(f"  失败: {FAIL} ❌")
    print(f"  通过率: {PASS / total * 100:.1f}%" if total > 0 else "  无测试项")
    
    if ERRORS:
        print(f"\n  失败项详情:")
        for err in ERRORS:
            print(f"    ❌ {err}")
    
    print("\n" + "=" * 60)
    
    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
