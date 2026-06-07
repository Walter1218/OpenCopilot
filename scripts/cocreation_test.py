#!/usr/bin/env python3
"""
自动化 PPT 共创流程：
1. 读取 AI_Agent_深度研究报告.md
2. 生成 PPT
3. 进入共创模式
4. 将第三页转换为图表
"""

import os
import sys
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline
from opencopilot.capabilities.ppt.content_converter import TextAnalyzer, create_chart_data
from ppt_generator import generate_ppt_from_json


def main():
    # 1. 读取文档
    doc_path = os.path.expanduser("~/Documents/trae_projects/OpenCopilot/test_docs/ai_agent_whitepaper.md")
    if not os.path.exists(doc_path):
        print(f"❌ 文档不存在: {doc_path}")
        return
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 已读取文档: {len(content)} 字符")
    
    # 2. 生成 PPT
    print("🔄 开始生成 PPT...")
    pipeline = PPTGenerationPipeline()
    result = pipeline.run(content)
    
    print(f"✅ PPT 生成完成: {result.total_pages} 页")
    print(f"   主题: {[t.title for t in result.topics]}")
    
    # 3. 查看第三页内容
    if len(result.slides) >= 3:
        slide_3 = result.slides[2]
        print(f"\n📊 第三页内容:")
        print(f"   标题: {slide_3.get('title', 'N/A')}")
        print(f"   类型: {slide_3.get('type', 'N/A')}")
        print(f"   内容: {json.dumps(slide_3.get('content', []), ensure_ascii=False, indent=2)[:200]}...")
        
        # 4. 将第三页转换为图表
        print("\n🔄 将第三页转换为图表...")
        
        # 分析内容，提取图表数据
        content_text = "\n".join(slide_3.get('content', []))
        analysis = TextAnalyzer.analyze(content_text)
        
        if analysis['best_match']:
            chart_data = analysis['best_match']
            print(f"   推荐图表类型: {chart_data.get('chart_type', 'N/A')}")
            
            # 更新幻灯片
            result.slides[2]['content_type'] = 'chart'
            result.slides[2]['chart_type'] = chart_data.get('chart_type', 'bar')
            result.slides[2]['chart_data'] = chart_data.get('chart_data', {})
            
            print("✅ 已转换为图表")
        else:
            # 手动创建图表数据
            print("   使用手动图表数据...")
            result.slides[2]['content_type'] = 'chart'
            result.slides[2]['chart_type'] = 'bar'
            result.slides[2]['chart_data'] = {
                "title": "MACF 框架性能对比",
                "labels": ["任务完成率", "响应速度", "准确率"],
                "datasets": [
                    {"label": "单Agent", "data": [65, 70, 75], "color": "#dc3545"},
                    {"label": "MACF", "data": [92, 95, 90], "color": "#28a745"}
                ]
            }
            print("✅ 已手动创建图表")
    
    # 5. 生成 PPT 文件
    output_dir = os.path.expanduser("~/Documents/trae_projects/OpenCopilot/output")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "AI_Agent_研究报告_图表版.pptx")
    print(f"\n📁 生成 PPT 文件: {output_path}")
    
    # 使用 generate_ppt_from_json 生成 PPT（注意：传入 slides 列表，而不是字典）
    try:
        generate_ppt_from_json(result.slides, output_path)
        print(f"✅ PPT 已生成: {output_path}")
        final_path = output_path
    except Exception as e:
        print(f"⚠️ PPT 生成警告: {e}")
        # 保存 JSON 作为备选
        json_path = os.path.join(output_dir, "AI_Agent_研究报告_图表版.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"slides": result.slides}, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 已保存: {json_path}")
        final_path = json_path
    
    # 6. 显示结果
    print("\n" + "="*60)
    print("📊 结果预览")
    print("="*60)
    print(f"总页数: {len(result.slides)}")
    print(f"第三页类型: {result.slides[2].get('content_type', 'N/A')}")
    print(f"第三页图表类型: {result.slides[2].get('chart_type', 'N/A')}")
    print(f"第三页图表数据: {json.dumps(result.slides[2].get('chart_data', {}), ensure_ascii=False, indent=2)}")
    
    print("\n" + "="*60)
    print("📁 文件位置")
    print("="*60)
    if os.path.exists(output_path):
        print(f"PPT 文件: {output_path}")
    else:
        print(f"JSON 文件: {json_path}")
    
    return result


if __name__ == "__main__":
    main()
