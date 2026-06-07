#!/usr/bin/env python3
"""
内容质量评估测试
评估AI生成的PPT内容质量
"""
import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

def evaluate_content_quality(slides_data, prompt, test_name):
    """评估内容质量"""
    print(f"\n{'='*60}")
    print(f"质量评估: {test_name}")
    print(f"{'='*60}")
    
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
        print(f"  ✅ 包含标题页: +0.5")
    else:
        print(f"  ❌ 缺少标题页: +0")
    
    # 检查是否有内容页
    content_slides = [s for s in slides_data if s.get('type') in ['content', 'content_slide']]
    if content_slides:
        structure_score += 0.5
        print(f"  ✅ 包含内容页: +0.5 ({len(content_slides)}页)")
    else:
        print(f"  ❌ 缺少内容页: +0")
    
    # 检查是否有结尾页
    has_ending = any(s.get('type') in ['ending', 'end_slide'] for s in slides_data)
    if has_ending:
        structure_score += 0.5
        print(f"  ✅ 包含结尾页: +0.5")
    else:
        print(f"  ❌ 缺少结尾页: +0")
    
    # 检查幻灯片数量
    if len(slides_data) >= 3:
        structure_score += 0.5
        print(f"  ✅ 幻灯片数量充足: +0.5 ({len(slides_data)}页)")
    else:
        print(f"  ⚠️ 幻灯片数量较少: +0 ({len(slides_data)}页)")
    
    scores["结构有效性"] = structure_score
    print(f"  结构有效性得分: {structure_score}/2.0")
    
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
        print(f"  ✅ 关键词匹配: +{accuracy_score:.1f} ({len(found_keywords)}/{len(expected_keywords)})")
        print(f"     匹配: {found_keywords[:5]}")
    else:
        accuracy_score = 1.0
        print(f"  ✅ 无特定关键词要求: +1.0")
    
    scores["目标准确性"] = accuracy_score
    print(f"  目标准确性得分: {accuracy_score}/2.0")
    
    # 3. 内容相关性 (3分)
    relevance_score = 0
    
    # 检查标题是否相关
    titles = [s.get('title', '') for s in slides_data]
    title_content = ' '.join(titles)
    
    # 简单的相关性检查
    if len(title_content) > 10:
        relevance_score += 1.0
        print(f"  ✅ 标题内容丰富: +1.0")
    else:
        print(f"  ⚠️ 标题内容较少: +0")
    
    # 检查是否有详细内容
    detailed_slides = [s for s in slides_data if s.get('items') and len(s.get('items', [])) > 1]
    if detailed_slides:
        relevance_score += 1.0
        print(f"  ✅ 包含详细内容: +1.0 ({len(detailed_slides)}页)")
    else:
        print(f"  ⚠️ 缺少详细内容: +0")
    
    # 检查内容是否与主题相关
    if any('发展' in t or '历史' in t or '历程' in t for t in titles):
        relevance_score += 1.0
        print(f"  ✅ 内容与主题相关: +1.0")
    else:
        relevance_score += 0.5
        print(f"  ⚠️ 内容相关性一般: +0.5")
    
    scores["内容相关性"] = relevance_score
    print(f"  内容相关性得分: {relevance_score}/3.0")
    
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
    print(f"  内容质量得分: {quality_score:.2f}/3.0")
    
    # 5. 格式丰富度 (2分)
    format_score = 0
    
    # 检查布局多样性
    layouts = set(s.get('layout', '') for s in slides_data)
    if len(layouts) >= 3:
        format_score += 1.0
        print(f"  ✅ 布局多样性: +1.0 ({len(layouts)}种)")
    elif len(layouts) >= 2:
        format_score += 0.5
        print(f"  ⚠️ 布局较少: +0.5 ({len(layouts)}种)")
    else:
        print(f"  ❌ 布局单一: +0 ({len(layouts)}种)")
    
    # 检查是否包含富格式
    has_rich_format = False
    for slide in slides_data:
        items = slide.get('items', [])
        if items and isinstance(items[0], dict):
            has_rich_format = True
            break
    
    if has_rich_format:
        format_score += 1.0
        print(f"  ✅ 包含富格式内容: +1.0")
    else:
        print(f"  ⚠️ 缺少富格式内容: +0")
    
    scores["格式丰富度"] = format_score
    print(f"  格式丰富度得分: {format_score}/2.0")
    
    # 计算总分
    total_score = sum(scores.values())
    max_score = 12.0  # 2+2+3+3+2
    
    print(f"\n  总分: {total_score:.1f}/{max_score} ({total_score/max_score*100:.0f}%)")
    
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
    
    print(f"  评级: {grade}")
    
    return scores, total_score, grade

def test_all_content_types():
    """测试所有内容类型"""
    print("=" * 80)
    print("内容质量评估测试")
    print("=" * 80)
    
    from opencopilot.providers.llm_provider import MiMoProvider
    provider = MiMoProvider()
    
    # 测试用例
    test_cases = [
        {
            "name": "内容转图片表示",
            "prompt": """请将以下内容转换为图片表示的幻灯片。

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

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "图表表示",
            "prompt": """请将以下数据转换为图表表示的幻灯片。

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

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "流程图表示",
            "prompt": """请将以下流程转换为流程图表示的幻灯片。

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

请生成完整的PPT大纲JSON。"""
        },
        {
            "name": "表格表示",
            "prompt": """请将以下信息转换为表格表示的幻灯片。

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

请生成完整的PPT大纲JSON。"""
        }
    ]
    
    all_results = []
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"测试场景: {test_case['name']}")
        print(f"{'='*80}")
        
        try:
            # 调用LLM
            start_time = time.time()
            response_chunks = []
            for chunk in provider.stream_chat(test_case['prompt']):
                response_chunks.append(chunk)
            
            end_time = time.time()
            duration = end_time - start_time
            full_response = ''.join(response_chunks)
            
            print(f"  响应时间: {duration:.3f}秒")
            print(f"  响应长度: {len(full_response)} 字符")
            
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
                        test_case['prompt'], 
                        test_case['name']
                    )
                    
                    all_results.append({
                        "name": test_case['name'],
                        "duration": duration,
                        "scores": scores,
                        "total_score": total_score,
                        "grade": grade,
                        "slides_count": len(slides_data)
                    })
                else:
                    print(f"  ❌ 未找到JSON结构")
                    all_results.append({
                        "name": test_case['name'],
                        "error": "JSON not found",
                        "total_score": 0,
                        "grade": "失败"
                    })
                    
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON解析失败: {e}")
                all_results.append({
                    "name": test_case['name'],
                    "error": str(e),
                    "total_score": 0,
                    "grade": "失败"
                })
                
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            all_results.append({
                "name": test_case['name'],
                "error": str(e),
                "total_score": 0,
                "grade": "失败"
            })
    
    # 3. 总结测试结果
    print("\n" + "=" * 80)
    print("质量评估总结")
    print("=" * 80)
    
    successful_tests = [r for r in all_results if r.get('total_score', 0) > 0]
    failed_tests = [r for r in all_results if r.get('total_score', 0) == 0]
    
    print(f"\n测试统计:")
    print(f"  总测试数: {len(all_results)}")
    print(f"  成功: {len(successful_tests)}")
    print(f"  失败: {len(failed_tests)}")
    print(f"  成功率: {len(successful_tests)/len(all_results)*100:.0f}%")
    
    print(f"\n详细结果:")
    for result in all_results:
        if 'error' in result:
            print(f"  ❌ {result['name']}: 失败 - {result['error']}")
        else:
            print(f"  ✅ {result['name']}: {result['total_score']:.1f}/12.0 ({result['grade']})")
            print(f"     幻灯片数: {result['slides_count']}, 响应时间: {result['duration']:.3f}秒")
    
    # 计算平均分数
    if successful_tests:
        avg_score = sum(r['total_score'] for r in successful_tests) / len(successful_tests)
        avg_duration = sum(r['duration'] for r in successful_tests) / len(successful_tests)
        
        print(f"\n平均指标:")
        print(f"  平均得分: {avg_score:.1f}/12.0 ({avg_score/12*100:.0f}%)")
        print(f"  平均响应时间: {avg_duration:.3f}秒")
        
        # 评估结果
        if avg_score >= 9.6:  # 80%
            grade = "优秀"
            print(f"\n🎉 内容质量评估: {grade}")
            print(f"   AI生成的内容质量优秀，可以直接使用。")
        elif avg_score >= 7.2:  # 60%
            grade = "良好"
            print(f"\n⚠️ 内容质量评估: {grade}")
            print(f"   AI生成的内容质量良好，可以使用但可能需要微调。")
        elif avg_score >= 4.8:  # 40%
            grade = "及格"
            print(f"\n⚠️ 内容质量评估: {grade}")
            print(f"   AI生成的内容质量及格，需要较多手动修改。")
        else:
            grade = "不及格"
            print(f"\n❌ 内容质量评估: {grade}")
            print(f"   AI生成的内容质量不佳，需要重新生成或大幅修改。")
    
    return len(successful_tests) > 0

if __name__ == "__main__":
    print("内容质量评估测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    success = test_all_content_types()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 内容质量评估测试完成！")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ 内容质量评估测试失败")
        print("=" * 80)