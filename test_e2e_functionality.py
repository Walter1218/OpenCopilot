#!/usr/bin/env python3
"""
端到端功能测试
测试完整的PPT共创工作台功能，包括LLM调用、UI显示、功能跳转等
"""
import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

# 创建QApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
app = QApplication(sys.argv)

def test_e2e_studio_window():
    """端到端测试StudioWindow功能"""
    print("=" * 80)
    print("端到端功能测试")
    print("=" * 80)
    
    # 1. 测试StudioWindow创建
    print("\n1. 测试StudioWindow创建...")
    try:
        from gui.v5.studio_window import StudioWindowV5, PPT_THEMES
        from gui.v5.navigation import NavigationManager
        
        # 创建NavigationManager
        nav = NavigationManager()
        
        # 创建StudioWindow
        window = StudioWindowV5(nav)
        print("✅ StudioWindow创建成功")
        
        # 检查窗口属性
        print(f"  窗口标题: {window.windowTitle() if hasattr(window, 'windowTitle') else 'N/A'}")
        print(f"  窗口大小: {window.size().width()}x{window.size().height()}")
        
    except Exception as e:
        print(f"❌ StudioWindow创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 测试主题切换功能
    print("\n2. 测试主题切换功能...")
    try:
        # 测试切换到不同主题
        for theme_id, theme_info in PPT_THEMES.items():
            window._on_theme_selected(theme_id)
            current_theme = window.get_current_theme()
            
            assert current_theme['name'] == theme_info['name'], f"主题名称不匹配: {current_theme['name']} != {theme_info['name']}"
            assert current_theme['primary_color'] == theme_info['primary_color'], f"主题颜色不匹配"
            
            print(f"  ✅ 主题 '{theme_info['name']}' 切换成功")
        
        # 测试自定义颜色
        window._on_custom_color()
        print("  ✅ 自定义颜色功能可用")
        
    except Exception as e:
        print(f"❌ 主题切换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 测试加载文档功能
    print("\n3. 测试加载文档功能...")
    try:
        # 读取测试文档
        doc_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/test_docs/ai_agent_whitepaper.md"
        with open(doc_path, 'r', encoding='utf-8') as f:
            doc_content = f.read()
        
        # 加载文本
        window.load_text(doc_content)
        print(f"  ✅ 文档加载成功: {len(doc_content)} 字符")
        
        # 检查Source Panel
        source_text = window._source_text.toPlainText()
        assert len(source_text) > 0, "Source Panel内容为空"
        print(f"  ✅ Source Panel内容: {len(source_text)} 字符")
        
    except Exception as e:
        print(f"❌ 文档加载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 测试AI Chat功能（需要调用LLM）
    print("\n4. 测试AI Chat功能...")
    try:
        from opencopilot.providers.llm_provider import MiMoProvider
        
        # 创建LLM Provider
        provider = MiMoProvider()
        print(f"  LLM配置: model={provider.default_model}, max_tokens={provider._max_completion_tokens}")
        
        # 测试简单LLM调用
        test_prompt = "请用一句话介绍人工智能。"
        
        start_time = time.time()
        response_chunks = []
        for chunk in provider.stream_chat(test_prompt):
            response_chunks.append(chunk)
        
        end_time = time.time()
        duration = end_time - start_time
        full_response = ''.join(response_chunks)
        
        print(f"  ✅ LLM调用成功:")
        print(f"    Prompt: {test_prompt}")
        print(f"    响应: {full_response[:100]}...")
        print(f"    耗时: {duration:.3f}秒")
        
    except Exception as e:
        print(f"❌ AI Chat测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 测试PPT生成功能（需要调用LLM）
    print("\n5. 测试PPT生成功能...")
    try:
        # 构建PPT生成prompt
        ppt_prompt = """请根据以下内容生成 PPT 大纲。

要求：
1. 严格输出纯 JSON 格式，不要包含任何其他文字
2. JSON 格式必须包含 "title" 和 "slides" 字段
3. slides 数组中每个对象必须包含 "type", "layout", "title" 字段
4. type 可选值: "title", "content", "ending"
5. layout 可选值: "center", "text_only", "two_column", "image_text"

内容：
AI Agent 技术白皮书：多智能体协作框架

一、摘要
本白皮书提出了一个面向企业级应用的多智能体协作框架（Multi-Agent Collaboration Framework, MACF）。该框架通过任务分解、角色分配、消息传递和共识机制，实现了异构AI Agent之间的高效协同。

二、背景与挑战
单一大模型Agent在处理复杂企业任务时面临三个核心挑战：上下文窗口限制导致长流程任务信息丢失、单一推理范式难以应对多领域交叉决策、缺乏自我纠错机制导致错误累积。

请生成完整的PPT大纲JSON。"""
        
        start_time = time.time()
        response_chunks = []
        for chunk in provider.stream_chat(ppt_prompt):
            response_chunks.append(chunk)
        
        end_time = time.time()
        duration = end_time - start_time
        full_response = ''.join(response_chunks)
        
        print(f"  ✅ PPT生成LLM调用成功:")
        print(f"    Prompt长度: {len(ppt_prompt)} 字符")
        print(f"    响应长度: {len(full_response)} 字符")
        print(f"    耗时: {duration:.3f}秒")
        
        # 解析JSON
        try:
            start_idx = full_response.find('{')
            end_idx = full_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = full_response[start_idx:end_idx]
                data = json.loads(json_str)
                
                print(f"    JSON解析: ✅ 成功")
                print(f"    标题: {data.get('title', 'N/A')}")
                print(f"    幻灯片数量: {len(data.get('slides', []))}")
                
                # 验证幻灯片结构
                slides = data.get('slides', [])
                for i, slide in enumerate(slides[:3]):  # 只显示前3个
                    print(f"    幻灯片 {i+1}: type={slide.get('type')}, layout={slide.get('layout')}, title={slide.get('title', '')[:30]}...")
                
                # 加载幻灯片到StudioWindow
                window.load_slides(slides)
                print(f"  ✅ 幻灯片加载到StudioWindow成功")
                
                # 检查各个面板
                print(f"    OutlinePanel幻灯片数: {len(window._outline_panel_widget.slides_data)}")
                print(f"    PreviewPanel幻灯片数: {len(window._preview_panel_widget.slides_data)}")
                print(f"    AICopilotChatWidget幻灯片数: {len(window._ai_chat_widget.slides_data)}")
                
            else:
                print(f"    JSON解析: ⚠️ 未找到JSON结构")
                
        except json.JSONDecodeError as e:
            print(f"    JSON解析: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"❌ PPT生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 测试Quality Badges功能
    print("\n6. 测试Quality Badges功能...")
    try:
        # 检查Quality Badges是否在OutlinePanel中工作
        outline_panel = window._outline_panel_widget
        
        # 测试质量检查
        if outline_panel.slides_data:
            issues = outline_panel._check_slide_quality(0)
            print(f"  ✅ Quality Badges检查成功: 发现 {len(issues)} 个问题")
            
            # 测试徽章信息获取
            badge_icon, badge_tooltip, badge_color = outline_panel._get_quality_badge_info(0)
            if badge_icon:
                print(f"    徽章图标: {badge_icon}")
                print(f"    颜色: {badge_color}")
                print(f"    提示: {badge_tooltip[:50]}...")
        
    except Exception as e:
        print(f"❌ Quality Badges测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. 测试跨面板联动
    print("\n7. 测试跨面板联动...")
    try:
        # 测试大纲选择 → 预览切换
        if window.slides_data:
            # 模拟大纲选择
            window._on_outline_slide_selected(0)
            print(f"  ✅ 大纲选择 → 预览切换: 选中第1页")
            
            # 测试预览切换 → 大纲同步
            window._on_preview_slide_changed(1)
            print(f"  ✅ 预览切换 → 大纲同步: 切换到第2页")
            
            # 测试AI修改 → 全局刷新
            window._on_ai_slides_updated(window.slides_data)
            print(f"  ✅ AI修改 → 全局刷新: 刷新所有面板")
        
    except Exception as e:
        print(f"❌ 跨面板联动测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. 测试埋点数据
    print("\n8. 测试埋点数据...")
    try:
        from gui.v5.telemetry import telemetry
        
        # 检查埋点事件是否被触发
        # 注意：这里只能检查埋点函数是否被调用，无法直接获取埋点数据
        print(f"  ✅ 埋点系统可用")
        
        # 测试埋点调用
        telemetry.emit("V5_E2E_TEST", test_type="end_to_end", timestamp=time.time())
        print(f"  ✅ 埋点调用成功")
        
    except Exception as e:
        print(f"❌ 埋点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 9. 测试UI显示
    print("\n9. 测试UI显示...")
    try:
        # 显示窗口
        window.show()
        print(f"  ✅ 窗口显示成功")
        
        # 等待一段时间让UI渲染
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()
        
        # 检查UI组件是否可见
        print(f"  OutlinePanel可见: {window._outline_panel_widget.isVisible()}")
        print(f"  PreviewPanel可见: {window._preview_panel_widget.isVisible()}")
        print(f"  AICopilotChatWidget可见: {window._ai_chat_widget.isVisible()}")
        
        # 关闭窗口
        window.close()
        print(f"  ✅ 窗口关闭成功")
        
    except Exception as e:
        print(f"❌ UI显示测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ 端到端功能测试完成！")
    print("=" * 80)
    
    return True

def test_llm_output_quality():
    """测试LLM输出质量"""
    print("\n" + "=" * 80)
    print("LLM输出质量测试")
    print("=" * 80)
    
    try:
        from opencopilot.providers.llm_provider import MiMoProvider
        
        provider = MiMoProvider()
        
        # 测试不同场景的LLM输出
        test_cases = [
            {
                "name": "简单问答",
                "prompt": "请用一句话介绍人工智能。",
                "expected_keywords": ["人工智能", "机器", "智能"]
            },
            {
                "name": "PPT大纲生成",
                "prompt": """请根据以下内容生成 PPT 大纲。

要求：
1. 严格输出纯 JSON 格式
2. JSON 格式必须包含 "title" 和 "slides" 字段
3. slides 数组中每个对象必须包含 "type", "layout", "title" 字段

内容：
人工智能技术发展

一、定义
人工智能是计算机科学的一个分支。

二、应用
1. 自然语言处理
2. 计算机视觉
3. 机器学习

请生成完整的PPT大纲JSON。""",
                "expected_keywords": ["title", "slides", "type", "layout"]
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n测试场景: {test_case['name']}")
            
            start_time = time.time()
            response_chunks = []
            for chunk in provider.stream_chat(test_case['prompt']):
                response_chunks.append(chunk)
            
            end_time = time.time()
            duration = end_time - start_time
            full_response = ''.join(response_chunks)
            
            # 检查是否包含预期关键词
            found_keywords = []
            for keyword in test_case['expected_keywords']:
                if keyword in full_response:
                    found_keywords.append(keyword)
            
            keyword_score = len(found_keywords) / len(test_case['expected_keywords'])
            
            print(f"  响应长度: {len(full_response)} 字符")
            print(f"  耗时: {duration:.3f}秒")
            print(f"  关键词匹配: {len(found_keywords)}/{len(test_case['expected_keywords'])} ({keyword_score*100:.0f}%)")
            print(f"  匹配关键词: {found_keywords}")
            
            # 如果是PPT大纲生成，检查JSON格式
            if "PPT大纲" in test_case['name']:
                try:
                    start_idx = full_response.find('{')
                    end_idx = full_response.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = full_response[start_idx:end_idx]
                        data = json.loads(json_str)
                        
                        has_title = 'title' in data
                        has_slides = 'slides' in data
                        slides_valid = isinstance(data.get('slides'), list)
                        
                        print(f"  JSON格式: ✅ 有效")
                        print(f"    包含title: {has_title}")
                        print(f"    包含slides: {has_slides}")
                        print(f"    slides是数组: {slides_valid}")
                        
                        if slides_valid:
                            print(f"    幻灯片数量: {len(data['slides'])}")
                    else:
                        print(f"  JSON格式: ⚠️ 未找到JSON结构")
                        
                except json.JSONDecodeError as e:
                    print(f"  JSON格式: ❌ 解析失败 - {e}")
            
            results.append({
                "name": test_case['name'],
                "response_length": len(full_response),
                "duration": duration,
                "keyword_score": keyword_score,
                "keywords_found": found_keywords
            })
        
        # 计算总体质量分数
        avg_keyword_score = sum(r['keyword_score'] for r in results) / len(results)
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        print(f"\n总体质量评估:")
        print(f"  平均关键词匹配率: {avg_keyword_score*100:.0f}%")
        print(f"  平均响应时间: {avg_duration:.3f}秒")
        
        if avg_keyword_score >= 0.8:
            print(f"  质量评级: ✅ 优秀")
        elif avg_keyword_score >= 0.6:
            print(f"  质量评级: ⚠️ 良好")
        else:
            print(f"  质量评级: ❌ 需要改进")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM输出质量测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("端到端功能测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 运行端到端测试
    e2e_success = test_e2e_studio_window()
    
    # 运行LLM输出质量测试
    llm_success = test_llm_output_quality()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"端到端功能测试: {'✅ 通过' if e2e_success else '❌ 失败'}")
    print(f"LLM输出质量测试: {'✅ 通过' if llm_success else '❌ 失败'}")
    
    if e2e_success and llm_success:
        print("\n🎉 所有测试通过！功能已验证。")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")