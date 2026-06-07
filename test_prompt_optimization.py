#!/usr/bin/env python3
"""
Prompt优化对比测试
对比优化前后的生成质量
"""
import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

def evaluate_content_quality(slides_data, prompt, test_name):
    """评估内容质量"""
    scores = {
        "结构有效性": 0,
        "目标准确性": 0,
        "内容相关性": 0,
        "内容质量": 0,
        "格式丰富度": 0
    }
    
    # 1. 结构有效性 (2分)
    structure_score = 0
    
    # 检查是否有title
    has_title = any(s.get('type') in ['title', 'title_slide'] for s in slides_data)
    if has_title:
        structure_score += 0.5
    
    # 检查是否有内容页
    content_slides = [s for s in slides_data if s.get('type') in ['content', 'content_slide']]
    if content_slides:
        structure_score += 0.5
    
    # 检查是否有结尾页
    has_ending = any(s.get('type') in ['ending', 'end_slide'] for s in slides_data)
    if has_ending:
        structure_score += 0.5
    
    # 检查幻灯片数量
    if len(slides_data) >= 3:
        structure_score += 0.5
    
    scores["结构有效性"] = structure_score
    
    # 2. 目标准确性 (2分)
    accuracy_score = 0
    
    # 检查是否包含预期关键词
    expected_keywords = []
    if "图片" in prompt:
        expected_keywords.extend(["image", "图片", "image_text", "full_image"])
    if "图表" in prompt:
        expected_keywords.extend(["chart", "图表", "bar", "line", "pie"])
    if "流程" in prompt:
        expected_keywords.extend(["flowchart", "流程", "process", "步骤"])
    if "表格" in prompt:
        expected_keywords.extend(["table", "表格", "headers", "rows"])
    
    response_str = json.dumps(slides_data, ensure_ascii=False)
    found_keywords = [k for k in expected_keywords if k in response_str]
    
    if expected_keywords:
        keyword_score = len(found_keywords) / len(expected_keywords)
        accuracy_score = keyword_score * 2
    
    scores["目标准确性"] = accuracy_score
    
    # 3. 内容相关性 (3分)
    relevance_score = 0
    
    # 检查标题是否相关
    titles = [s.get('title', '') for s in slides_data]
    title_content = ' '.join(titles)
    
    # 简单的相关性检查
    if len(title_content) > 10:
        relevance_score += 1.0
    
    # 检查是否有详细内容
    detailed_slides = [s for s in slides_data if s.get('items') and len(s.get('items', [])) > 1]
    if detailed_slides:
        relevance_score += 1.0
    
    # 检查内容是否与主题相关
    if any('发展' in t or '历史' in t or '历程' in t for t in titles):
        relevance_score += 1.0
    else:
        relevance_score += 0.5
    
    scores["内容相关性"] = relevance_score
    
    # 4. 内容质量 (3分)
    quality_score = 0
    
    # 检查每个幻灯片的内容质量
    for i, slide in enumerate(slides_data[:5]):  # 只检查前5个
        slide_quality = 0
        
        # 检查标题
        title = slide.get('title', '')
        if len(title) > 5:
            slide_quality += 0.3
        elif len(title) > 0:
            slide_quality += 0.1
        
        # 检查内容
        items = slide.get('items', [])
        if items:
            if isinstance(items[0], str):
                # 文本内容
                total_text = ' '.join(items)
                if len(total_text) > 20:
                    slide_quality += 0.3
                elif len(total_text) > 10:
                    slide_quality += 0.15
            elif isinstance(items[0], dict):
                # 结构化内容
                slide_quality += 0.3
        
        # 检查布局
        layout = slide.get('layout', '')
        if layout in ['image_text', 'two_column', 'chart', 'table']:
            slide_quality += 0.2
        elif layout in ['text_only', 'content']:
            slide_quality += 0.1
        
        quality_score += min(slide_quality, 0.6)  # 每页最多0.6分
    
    # 归一化到3分
    quality_score = min(quality_score / (len(slides_data[:5]) * 0.6) * 3, 3.0)
    scores["内容质量"] = quality_score
    
    # 5. 格式丰富度 (2分)
    format_score = 0
    
    # 检查布局多样性
    layouts = set(s.get('layout', '') for s in slides_data)
    if len(layouts) >= 3:
        format_score += 1.0
    elif len(layouts) >= 2:
        format_score += 0.5
    
    # 检查是否包含富格式
    has_rich_format = False
    for slide in slides_data:
        items = slide.get('items', [])
        if items and isinstance(items[0], dict):
            has_rich_format = True
            break
    
    if has_rich_format:
        format_score += 1.0
    
    scores["格式丰富度"] = format_score
    
    # 计算总分
    total_score = sum(scores.values())
    max_score = 12.0  # 2+2+3+3+2
    
    # 评级
    percentage = total_score / max_score
    if percentage >= 0.8:
        grade = "优秀"
    elif percentage >= 0.6:
        grade = "良好"
    elif percentage >= 0.4:
        grade = "及格"
    else:
        grade = "不及格"
    
    return scores, total_score, grade

def test_prompt_comparison():
    """测试Prompt对比"""
    print("=" * 80)
    print("Prompt优化对比测试")
    print("=" * 80)
    
    from opencopilot.providers.llm_provider import MiMoProvider
    provider = MiMoProvider()
    
    # 定义优化前后的Prompt
    test_cases = [
        {
            "name": "内容转图片表示",
            "original_prompt": """请将以下内容转换为图片表示的幻灯片。

内容：
人工智能的发展历程
- 1956年：人工智能概念提出
- 1997年：深蓝击败国际象棋冠军
- 2016年：AlphaGo击败围棋世界冠军
- 2022年：ChatGPT发布

要求：
1. 使用图片布局（image_text或full_image）
2. 生成JSON格式的PPT大纲
3. 包含title和slides字段
4. slides中每个对象包含type、layout、title、items字段
5. type可选值：title、content、ending
6. layout可选值：center、text_only、image_text、full_image、two_column

请生成完整的PPT大纲JSON。""",
            "optimized_prompt": """请将以下内容转换为完整的PPT幻灯片，必须包含完整的结构：

内容：
人工智能的发展历程
- 1956年：人工智能概念提出
- 1997年：深蓝击败国际象棋冠军
- 2016年：AlphaGo击败围棋世界冠军
- 2022年：ChatGPT发布

【必须要求】
1. 必须包含标题页（type: "title"）
2. 必须包含至少3个内容页（type: "content"）
3. 必须包含结尾页（type: "ending"）
4. 每个内容页必须包含：
   - 标题（title）
   - 详细内容（items数组，至少3个项目）
   - 图片布局（layout: "image_text"或"full_image"）
5. 每个项目必须包含：
   - 类型（type: "text"或"image"）
   - 内容（content）
   - 描述（description）- 详细说明

【输出格式】
严格输出JSON格式，结构如下：
{
  "title": "PPT标题",
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "人工智能的发展历程",
      "items": [{"type": "text", "content": "从1956年到2022年的技术演进"}]
    },
    {
      "type": "content",
      "layout": "image_text",
      "title": "1956年：人工智能概念提出",
      "items": [
        {"type": "text", "content": "起源", "description": "人工智能作为计算机科学的一个分支正式诞生"},
        {"type": "image", "content": "ai_origin.jpg", "description": "早期AI研究者"},
        {"type": "text", "content": "意义", "description": "开创了智能机器的新纪元"}
      ]
    }
  ]
}

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "图表表示",
            "original_prompt": """请将以下数据转换为图表表示的幻灯片。

数据：
2023年各季度销售额
- Q1: 120万
- Q2: 150万
- Q3: 180万
- Q4: 200万

要求：
1. 使用图表布局（chart或data_comparison）
2. 生成JSON格式的PPT大纲
3. 包含title和slides字段
4. slides中每个对象包含type、layout、title、items字段
5. items中包含图表数据（chart_data或table_data）
6. 图表类型：bar、line、pie

请生成完整的PPT大纲JSON。""",
            "optimized_prompt": """请将以下数据转换为完整的图表PPT幻灯片，必须包含完整的结构：

数据：
2023年各季度销售额
- Q1: 120万
- Q2: 150万
- Q3: 180万
- Q4: 200万

【必须要求】
1. 必须包含标题页（type: "title"）
2. 必须包含至少2个图表页（type: "chart"）
3. 必须包含结尾页（type: "ending"）
4. 每个图表页必须包含：
   - 标题（title）
   - 图表类型（chart_type: "bar"/"line"/"pie"）
   - 图表数据（chart_data）
   - 图表选项（chart_options）

【图表数据结构】
每个图表必须包含：
- chart_type: 图表类型
- chart_data: {
    labels: ["标签1", "标签2", ...],
    datasets: [{
      label: "数据集名称",
      data: [数值1, 数值2, ...]
    }]
  }
- chart_options: {
    responsive: true,
    plugins: { legend: { position: "top" } }
  }

【输出格式】
严格输出JSON格式，结构如下：
{
  "title": "2023年销售额分析报告",
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "2023年各季度销售额分析",
      "items": [{"type": "text", "content": "数据驱动的业绩洞察"}]
    },
    {
      "type": "chart",
      "layout": "chart",
      "title": "销售额趋势图",
      "items": [{
        "chart_type": "line",
        "chart_data": {
          "labels": ["Q1", "Q2", "Q3", "Q4"],
          "datasets": [{
            "label": "销售额（万元）",
            "data": [120, 150, 180, 200]
          }]
        },
        "chart_options": {"responsive": true}
      }]
    },
    {
      "type": "ending",
      "layout": "center",
      "title": "谢谢观看",
      "items": [{"type": "text", "content": "数据驱动决策"}]
    }
  ]
}

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "流程图表示",
            "original_prompt": """请将以下流程转换为流程图表示的幻灯片。

流程：
用户登录流程
1. 用户输入用户名和密码
2. 系统验证用户信息
3. 验证通过，跳转到首页
4. 验证失败，显示错误信息

要求：
1. 使用流程图布局（flowchart或process）
2. 生成JSON格式的PPT大纲
3. 包含title和slides字段
4. slides中每个对象包含type、layout、title、items字段
5. items中包含流程图数据（flowchart_data或steps）
6. 流程图包含节点和连接

请生成完整的PPT大纲JSON。""",
            "optimized_prompt": """请将以下流程转换为完整的流程图PPT幻灯片，必须包含完整的结构：

流程：
用户登录流程
1. 用户输入用户名和密码
2. 系统验证用户信息
3. 验证通过，跳转到首页
4. 验证失败，显示错误信息

【必须要求】
1. 必须包含标题页（type: "title"）
2. 必须包含流程图页（type: "flowchart"）
3. 必须包含详细步骤页（type: "content"）
4. 必须包含结尾页（type: "ending"）
5. 流程图必须包含：
   - 节点（nodes）：每个步骤
   - 连接（edges）：步骤间的关系
   - 决策点（decision）：条件判断

【流程图数据结构】
flowchart_data必须包含：
- nodes: [
    { id: "node1", label: "节点名称", type: "start"/"process"/"decision"/"end" },
    ...
  ]
- edges: [
    { from: "node1", to: "node2", label: "连接标签" },
    ...
  ]

【输出格式】
严格输出JSON格式，结构如下：
{
  "title": "用户登录流程",
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "用户登录流程",
      "items": [{"type": "text", "content": "安全认证流程设计"}]
    },
    {
      "type": "flowchart",
      "layout": "process",
      "title": "登录流程图",
      "items": [{
        "flowchart_data": {
          "nodes": [
            {"id": "start", "label": "开始", "type": "start"},
            {"id": "input", "label": "输入用户名密码", "type": "process"},
            {"id": "verify", "label": "验证信息", "type": "decision"},
            {"id": "success", "label": "跳转首页", "type": "process"},
            {"id": "fail", "label": "显示错误", "type": "process"},
            {"id": "end", "label": "结束", "type": "end"}
          ],
          "edges": [
            {"from": "start", "to": "input"},
            {"from": "input", "to": "verify"},
            {"from": "verify", "to": "success", "label": "验证通过"},
            {"from": "verify", "to": "fail", "label": "验证失败"},
            {"from": "success", "to": "end"},
            {"from": "fail", "to": "end"}
          ]
        }
      }]
    },
    {
      "type": "content",
      "layout": "text_only",
      "title": "详细步骤说明",
      "items": [
        {"type": "text", "content": "步骤1：用户输入用户名和密码"},
        {"type": "text", "content": "步骤2：系统验证用户信息"},
        {"type": "text", "content": "步骤3：验证通过，跳转到首页"},
        {"type": "text", "content": "步骤4：验证失败，显示错误信息"}
      ]
    },
    {
      "type": "ending",
      "layout": "center",
      "title": "流程设计完成",
      "items": [{"type": "text", "content": "安全认证流程"}]
    }
  ]
}

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "表格表示",
            "original_prompt": """请将以下信息转换为表格表示的幻灯片。

信息：
团队成员信息
- 张三：25岁，北京，月薪15000
- 李四：30岁，上海，月薪20000
- 王五：28岁，广州，月薪18000

要求：
1. 使用表格布局（table或data_comparison）
2. 生成JSON格式的PPT大纲
3. 包含title和slides字段
4. slides中每个对象包含type、layout、title、items字段
5. items中包含表格数据（table_data）
6. 表格包含表头和数据行

请生成完整的PPT大纲JSON。""",
            "optimized_prompt": """请将以下信息转换为完整的表格PPT幻灯片，必须包含完整的结构：

信息：
团队成员信息
- 张三：25岁，北京，月薪15000
- 李四：30岁，上海，月薪20000
- 王五：28岁，广州，月薪18000

【必须要求】
1. 必须包含标题页（type: "title"）
2. 必须包含表格页（type: "table"）
3. 必须包含总结页（type: "content"）
4. 必须包含结尾页（type: "ending"）
5. 表格必须包含：
   - 表头（headers）
   - 数据行（rows）
   - 表格说明（description）

【表格数据结构】
table_data必须包含：
- headers: ["列1", "列2", ...]
- rows: [
    ["行1列1", "行1列2", ...],
    ["行2列1", "行2列2", ...],
    ...
  ]
- description: "表格说明文字"

【输出格式】
严格输出JSON格式，结构如下：
{
  "title": "团队成员信息",
  "slides": [
    {
      "type": "title",
      "layout": "center",
      "title": "团队成员信息",
      "items": [{"type": "text", "content": "人员配置与薪资结构"}]
    },
    {
      "type": "table",
      "layout": "table",
      "title": "成员信息表",
      "items": [{
        "table_data": {
          "headers": ["姓名", "年龄", "城市", "月薪"],
          "rows": [
            ["张三", "25", "北京", "15000"],
            ["李四", "30", "上海", "20000"],
            ["王五", "28", "广州", "18000"]
          ],
          "description": "团队共3名成员，平均年龄27.7岁，平均月薪17667元"
        }
      }]
    },
    {
      "type": "content",
      "layout": "text_only",
      "title": "数据洞察",
      "items": [
        {"type": "text", "content": "平均年龄：27.7岁"},
        {"type": "text", "content": "平均月薪：17667元"},
        {"type": "text", "content": "城市分布：北京、上海、广州"}
      ]
    },
    {
      "type": "ending",
      "layout": "center",
      "title": "谢谢观看",
      "items": [{"type": "text", "content": "数据驱动团队管理"}]
    }
  ]
}

请生成完整的PPT大纲JSON。"""
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"测试场景: {test_case['name']}")
        print(f"{'='*80}")
        
        scenario_results = {}
        
        for prompt_type, prompt in [("原始Prompt", test_case['original_prompt']), 
                                     ("优化Prompt", test_case['optimized_prompt'])]:
            print(f"\n{'='*60}")
            print(f"  {prompt_type}")
            print(f"{'='*60}")
            
            try:
                # 调用LLM
                start_time = time.time()
                response_chunks = []
                for chunk in provider.stream_chat(prompt):
                    response_chunks.append(chunk)
                
                end_time = time.time()
                duration = end_time - start_time
                full_response = ''.join(response_chunks)
                
                print(f"    响应时间: {duration:.3f}秒")
                print(f"    响应长度: {len(full_response)} 字符")
                
                # 解析JSON
                try:
                    start_idx = full_response.find('{')
                    end_idx = full_response.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = full_response[start_idx:end_idx]
                        json_data = json.loads(json_str)
                        slides_data = json_data.get('slides', [])
                        
                        # 评估质量
                        scores, total_score, grade = evaluate_content_quality(
                            slides_data, 
                            prompt, 
                            test_case['name']
                        )
                        
                        print(f"    幻灯片数量: {len(slides_data)}")
                        print(f"    总分: {total_score:.1f}/12.0 ({total_score/12*100:.0f}%)")
                        print(f"    评级: {grade}")
                        print(f"    各维度得分:")
                        for dim, score in scores.items():
                            print(f"      {dim}: {score:.1f}")
                        
                        scenario_results[prompt_type] = {
                            "duration": duration,
                            "response_length": len(full_response),
                            "slides_count": len(slides_data),
                            "scores": scores,
                            "total_score": total_score,
                            "grade": grade,
                            "json_valid": True
                        }
                    else:
                        print(f"    ❌ 未找到JSON结构")
                        scenario_results[prompt_type] = {
                            "json_valid": False,
                            "error": "JSON not found"
                        }
                        
                except json.JSONDecodeError as e:
                    print(f"    ❌ JSON解析失败: {e}")
                    scenario_results[prompt_type] = {
                        "json_valid": False,
                        "error": str(e)
                    }
                    
            except Exception as e:
                print(f"    ❌ 测试失败: {e}")
                scenario_results[prompt_type] = {
                    "error": str(e)
                }
        
        # 对比结果
        if "原始Prompt" in scenario_results and "优化Prompt" in scenario_results:
            orig = scenario_results["原始Prompt"]
            opt = scenario_results["优化Prompt"]
            
            if orig.get("json_valid") and opt.get("json_valid"):
                score_diff = opt["total_score"] - orig["total_score"]
                duration_diff = opt["duration"] - orig["duration"]
                slides_diff = opt["slides_count"] - orig["slides_count"]
                
                print(f"\n  {'='*60}")
                print(f"  对比结果")
                print(f"  {'='*60}")
                print(f"    得分变化: {orig['total_score']:.1f} → {opt['total_score']:.1f} ({score_diff:+.1f})")
                print(f"    评级变化: {orig['grade']} → {opt['grade']}")
                print(f"    幻灯片数变化: {orig['slides_count']} → {opt['slides_count']} ({slides_diff:+})")
                print(f"    响应时间变化: {orig['duration']:.3f}s → {opt['duration']:.3f}s ({duration_diff:+.3f}s)")
                print(f"    响应长度变化: {orig['response_length']} → {opt['response_length']} ({opt['response_length']-orig['response_length']:+})")
                
                # 各维度对比
                print(f"    各维度对比:")
                for dim in ["结构有效性", "目标准确性", "内容相关性", "内容质量", "格式丰富度"]:
                    orig_score = orig["scores"][dim]
                    opt_score = opt["scores"][dim]
                    print(f"      {dim}: {orig_score:.1f} → {opt_score:.1f} ({opt_score-orig_score:+.1f})")
        
        results.append({
            "name": test_case['name'],
            "results": scenario_results
        })
    
    # 4. 总结测试结果
    print("\n" + "=" * 80)
    print("优化效果总结")
    print("=" * 80)
    
    total_orig_score = 0
    total_opt_score = 0
    valid_scenarios = 0
    
    for result in results:
        if "原始Prompt" in result["results"] and "优化Prompt" in result["results"]:
            orig = result["results"]["原始Prompt"]
            opt = result["results"]["优化Prompt"]
            
            if orig.get("json_valid") and opt.get("json_valid"):
                total_orig_score += orig["total_score"]
                total_opt_score += opt["total_score"]
                valid_scenarios += 1
    
    if valid_scenarios > 0:
        avg_orig_score = total_orig_score / valid_scenarios
        avg_opt_score = total_opt_score / valid_scenarios
        score_improvement = avg_opt_score - avg_orig_score
        improvement_percentage = (score_improvement / avg_orig_score) * 100 if avg_orig_score > 0 else 0
        
        print(f"\n平均得分对比:")
        print(f"  原始Prompt平均得分: {avg_orig_score:.1f}/12.0 ({avg_orig_score/12*100:.0f}%)")
        print(f"  优化Prompt平均得分: {avg_opt_score:.1f}/12.0 ({avg_opt_score/12*100:.0f}%)")
        print(f"  得分提升: {score_improvement:+.1f} ({improvement_percentage:+.0f}%)")
        
        # 评级分布
        print(f"\n评级分布:")
        for result in results:
            if "原始Prompt" in result["results"] and "优化Prompt" in result["results"]:
                orig = result["results"]["原始Prompt"]
                opt = result["results"]["优化Prompt"]
                if orig.get("json_valid") and opt.get("json_valid"):
                    print(f"  {result['name']}: {orig['grade']} → {opt['grade']}")
        
        # 评估结果
        if improvement_percentage >= 20:
            print(f"\n🎉 Prompt优化效果显著！")
            print(f"   平均得分提升{improvement_percentage:.0f}%，生成质量明显改善。")
        elif improvement_percentage >= 10:
            print(f"\n⚠️ Prompt优化效果良好")
            print(f"   平均得分提升{improvement_percentage:.0f}%，生成质量有所改善。")
        elif improvement_percentage > 0:
            print(f"\n⚠️ Prompt优化效果一般")
            print(f"   平均得分提升{improvement_percentage:.0f}%，生成质量略有改善。")
        else:
            print(f"\n❌ Prompt优化效果不佳")
            print(f"   生成质量没有明显改善。")
    
    return len(results) > 0

if __name__ == "__main__":
    print("Prompt优化对比测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    success = test_prompt_comparison()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 Prompt优化对比测试完成！")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Prompt优化对比测试失败")
        print("=" * 80)