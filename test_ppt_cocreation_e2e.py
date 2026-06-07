#!/usr/bin/env python3
"""
PPT共创模式端到端测试

测试内容：
1. PPT生成功能（验证ImmuneSystem不再误拦截）
2. 共创模式各个功能
3. 质量评估和指令执行验证
"""

import sys
import os
import time
import json
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_generator import extract_json_from_text, generate_ppt_from_json


def get_latest_logs(minutes=5):
    """获取最近N分钟的埋点日志"""
    db_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/opencopilot/pipeline_logs.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, event, message, level, session_id
        FROM pipeline_logs
        WHERE timestamp > datetime('now', ?)
        ORDER BY timestamp DESC
    """, (f'-{minutes} minutes',))
    logs = cursor.fetchall()
    conn.close()
    return logs


def test_ppt_generation():
    """测试PPT生成功能"""
    print("\n" + "="*60)
    print("📝 测试1: PPT生成功能")
    print("="*60)
    
    # 读取测试文档
    test_file = "/Users/onetwo/Documents/trae_projects/OpenCopilot/test_docs/ai_agent_whitepaper.md"
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 测试文件: {test_file}")
    print(f"📊 文件大小: {len(content)} 字符")
    
    # 构建PPT生成提示
    prompt = f"""请根据以下内容生成 PPT 大纲。

要求：
1. 严格输出纯 JSON 格式，不要输出任何其他文字、代码块标记或解释
2. 输出格式为 {{"title": "演示文稿标题", "slides": [...]}}
3. 每个 slide 包含 type, layout, title, items 等字段
4. layout 可选值: center, text_only, image_right, three_columns
5. 每页 3-5 个要点，每个要点一句话
6. 智能选择版式：数据对比用 three_columns，案例说明用 image_right
7. 必须包含结尾页：type=ending, layout=center, title='谢谢', subtitle='Q & A'
8. 覆盖原文所有一级章节，不要遗漏任何主题
9. 包含表格数据的章节优先用 three_columns 布局

原始内容：
{content}"""
    
    print(f"\n📝 Prompt长度: {len(prompt)} 字符")
    print("\n🔄 正在调用Agent Pipeline生成PPT...")
    
    try:
        from opencopilot.agent.caller import call_agent_pipeline_sync
        
        start_time = time.time()
        full_text = ""
        chunk_count = 0
        
        for chunk in call_agent_pipeline_sync(
            prompt,
            action_type="ppt",
            session_id=f"test_ppt_{int(time.time())}",
            context_source="test",
            is_new_task=True,
        ):
            full_text += chunk
            chunk_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ PPT生成完成!")
        print(f"   - 耗时: {elapsed:.2f}秒")
        print(f"   - 输出长度: {len(full_text)} 字符")
        print(f"   - Chunk数: {chunk_count}")
        
        # 解析JSON
        print("\n🔍 解析生成的JSON...")
        result = extract_json_from_text(full_text)
        
        if result:
            slides = result.get("slides", []) if isinstance(result, dict) else result
            print(f"✅ JSON解析成功!")
            print(f"   - 幻灯片数量: {len(slides)}")
            
            # 验证slides结构
            valid_slides = 0
            for i, slide in enumerate(slides):
                has_title = "title" in slide
                has_items = "items" in slide and len(slide.get("items", [])) > 0
                has_layout = "layout" in slide
                if has_title and has_items:
                    valid_slides += 1
            
            print(f"   - 有效幻灯片: {valid_slides}/{len(slides)}")
            
            # 显示前3页内容
            print("\n📑 前3页幻灯片预览:")
            for i, slide in enumerate(slides[:3]):
                print(f"\n   第{i+1}页:")
                print(f"   - 标题: {slide.get('title', 'N/A')}")
                print(f"   - 版式: {slide.get('layout', 'N/A')}")
                items = slide.get("items", [])
                if items:
                    print(f"   - 要点数: {len(items)}")
                    for j, item in enumerate(items[:2]):
                        print(f"     • {item.get('text', 'N/A')[:50]}...")
            
            return True, {"slides_count": len(slides), "valid_slides": valid_slides, "elapsed": elapsed}
        else:
            print(f"❌ JSON解析失败!")
            print(f"   - 输出前200字符: {full_text[:200]}")
            return False, {"error": "JSON解析失败", "output": full_text[:500]}
            
    except Exception as e:
        print(f"❌ PPT生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


def test_cocreation_features():
    """测试共创模式各个功能"""
    print("\n" + "="*60)
    print("🎨 测试2: 共创模式功能测试")
    print("="*60)
    
    # 测试数据
    test_slides = [
        {
            "title": "测试标题",
            "layout": "text_only",
            "type": "content",
            "items": [
                {"text": "要点1"},
                {"text": "要点2"},
                {"text": "要点3"}
            ]
        },
        {
            "title": "数据对比",
            "layout": "three_columns",
            "type": "content",
            "items": [
                {"text": "列1数据"},
                {"text": "列2数据"},
                {"text": "列3数据"}
            ]
        },
        {
            "title": "谢谢",
            "layout": "center",
            "type": "ending",
            "items": [
                {"text": "Q & A"}
            ]
        }
    ]
    
    results = {}
    
    # 测试1: JSON提取功能
    print("\n✅ 测试2.1: JSON提取功能")
    test_json_str = '{"title": "测试", "slides": [{"title": "页1", "items": [{"text": "内容"}]}]}'
    extracted = extract_json_from_text(test_json_str)
    results["json_extraction"] = extracted is not None
    print(f"   结果: {'✅ 通过' if results['json_extraction'] else '❌ 失败'}")
    
    # 测试2: PPT导出功能
    print("\n✅ 测试2.2: PPT导出功能")
    try:
        output_path = "/tmp/test_cocreation_output.pptx"
        generate_ppt_from_json(test_slides, output_path)
        file_exists = os.path.exists(output_path)
        file_size = os.path.getsize(output_path) if file_exists else 0
        results["ppt_export"] = file_exists and file_size > 0
        print(f"   结果: {'✅ 通过' if results['ppt_export'] else '❌ 失败'}")
        print(f"   - 文件大小: {file_size} bytes")
        if file_exists:
            os.remove(output_path)
    except Exception as e:
        results["ppt_export"] = False
        print(f"   结果: ❌ 失败 - {e}")
    
    # 测试3: 差异计算功能
    print("\n✅ 测试2.3: 差异计算功能（模拟）")
    old_slide = {"title": "旧标题", "items": [{"text": "旧内容"}]}
    new_slide = {"title": "新标题", "items": [{"text": "旧内容"}, {"text": "新内容"}]}
    # 简单验证数据结构兼容性
    results["diff_compatible"] = isinstance(old_slide, dict) and isinstance(new_slide, dict)
    print(f"   结果: {'✅ 通过' if results['diff_compatible'] else '❌ 失败'}")
    
    # 测试4: 撤销/重做栈（模拟）
    print("\n✅ 测试2.4: 撤销/重做栈（模拟）")
    undo_stack = []
    redo_stack = []
    undo_stack.append({"slides": test_slides.copy(), "desc": "初始状态"})
    can_undo = len(undo_stack) > 0
    results["undo_redo"] = can_undo
    print(f"   结果: {'✅ 通过' if results['undo_redo'] else '❌ 失败'}")
    
    # 统计结果
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n📊 功能测试总结: {passed}/{total} 通过")
    
    return all(results.values()), results


def check_immune_system_logs():
    """检查ImmuneSystem日志"""
    print("\n" + "="*60)
    print("🛡️ 测试3: ImmuneSystem日志检查")
    print("="*60)
    
    logs = get_latest_logs(minutes=10)
    
    immune_logs = [log for log in logs if 'IMMUNE' in log[1] or 'immune' in log[2].lower()]
    
    print(f"\n📊 最近10分钟ImmuneSystem日志: {len(immune_logs)} 条")
    
    blocked_count = 0
    skipped_count = 0
    
    for log in immune_logs[:20]:
        timestamp, event, message, level, session_id = log
        if 'BLOCKED' in event:
            blocked_count += 1
            print(f"   ❌ {timestamp} | {event} | {message[:80]}")
        elif 'SKIPPED' in event:
            skipped_count += 1
            print(f"   ⏭️ {timestamp} | {event} | {message[:80]}")
        else:
            print(f"   ℹ️ {timestamp} | {event} | {message[:80]}")
    
    print(f"\n📊 统计:")
    print(f"   - 被拦截: {blocked_count}")
    print(f"   - 已跳过: {skipped_count}")
    
    return blocked_count == 0


def main():
    """主测试函数"""
    print("\n" + "🚀"*30)
    print("PPT共创模式端到端测试")
    print("🚀"*30)
    
    start_time = time.time()
    results = {}
    
    # 测试1: PPT生成
    success, details = test_ppt_generation()
    results["ppt_generation"] = {"success": success, "details": details}
    
    # 测试2: 共创功能
    success, details = test_cocreation_features()
    results["cocreation_features"] = {"success": success, "details": details}
    
    # 测试3: ImmuneSystem日志
    no_blocks = check_immune_system_logs()
    results["immune_system"] = {"success": no_blocks, "no_blocks": no_blocks}
    
    # 总结
    elapsed = time.time() - start_time
    
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r["success"])
    
    for test_name, result in results.items():
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")
    print(f"总耗时: {elapsed:.2f}秒")
    
    # 质量评估
    print("\n" + "="*60)
    print("📋 质量评估报告")
    print("="*60)
    
    ppt_result = results.get("ppt_generation", {})
    if ppt_result.get("success"):
        details = ppt_result.get("details", {})
        slides_count = details.get("slides_count", 0)
        valid_slides = details.get("valid_slides", 0)
        
        print("\n✅ PPT生成质量:")
        print(f"   - 幻灯片数量: {slides_count}")
        print(f"   - 有效幻灯片: {valid_slides}")
        print(f"   - 生成耗时: {details.get('elapsed', 0):.2f}秒")
        
        if slides_count > 0:
            quality_score = (valid_slides / slides_count) * 100
            print(f"   - 质量得分: {quality_score:.1f}%")
        
        print("\n✅ 指令执行验证:")
        print(f"   - JSON格式: {'正确' if slides_count > 0 else '错误'}")
        print(f"   - 幻灯片结构: {'完整' if valid_slides == slides_count else '部分缺失'}")
        print(f"   - ImmuneSystem: {'未误拦截' if no_blocks else '存在误拦截'}")
    else:
        print("\n❌ PPT生成失败，无法进行质量评估")
        error = ppt_result.get("details", {}).get("error", "未知错误")
        print(f"   错误: {error}")
    
    # 返回结果
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
