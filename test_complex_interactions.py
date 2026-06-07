#!/usr/bin/env python3
"""
复杂共创交互测试
测试内容转图片、图表、流程图等复杂指令
"""
import sys
import os
import time
import json

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

def test_complex_interactions():
    """测试复杂共创交互"""
    print("=" * 80)
    print("复杂共创交互测试")
    print("=" * 80)
    
    # 1. 测试LLM Provider
    print("\n1. 测试LLM Provider...")
    try:
        from opencopilot.providers.llm_provider import MiMoProvider
        provider = MiMoProvider()
        print(f"  ✅ LLM配置: model={provider.default_model}, max_tokens={provider._max_completion_tokens}")
    except Exception as e:
        print(f"  ❌ LLM Provider导入失败: {e}")
        return False
    
    # 2. 测试复杂指令
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

请生成完整的PPT大纲JSON。""",
            "expected_keywords": ["title", "slides", "image", "layout"],
            "expected_layouts": ["image_text", "full_image"]
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

请生成完整的PPT大纲JSON。""",
            "expected_keywords": ["title", "slides", "chart", "data"],
            "expected_data_structures": ["chart_data", "table_data"]
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

请生成完整的PPT大纲JSON。""",
            "expected_keywords": ["title", "slides", "flowchart", "process"],
            "expected_data_structures": ["flowchart_data", "steps"]
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

请生成完整的PPT大纲JSON。""",
            "expected_keywords": ["title", "slides", "table", "data"],
            "expected_data_structures": ["table_data", "headers", "rows"]
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"测试场景: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            # 调用LLM
            start_time = time.time()
            response_chunks = []
            for chunk in provider.stream_chat(test_case['prompt']):
                response_chunks.append(chunk)
            
            end_time = time.time()
            duration = end_time - start_time
            full_response = ''.join(response_chunks)
            
            print(f"  响应长度: {len(full_response)} 字符")
            print(f"  响应时间: {duration:.3f}秒")
            
            # 检查关键词
            found_keywords = []
            for keyword in test_case['expected_keywords']:
                if keyword in full_response:
                    found_keywords.append(keyword)
            
            keyword_score = len(found_keywords) / len(test_case['expected_keywords'])
            print(f"  关键词匹配: {len(found_keywords)}/{len(test_case['expected_keywords'])} ({keyword_score*100:.0f}%)")
            print(f"  匹配关键词: {found_keywords}")
            
            # 解析JSON
            json_valid = False
            json_data = None
            try:
                start_idx = full_response.find('{')
                end_idx = full_response.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = full_response[start_idx:end_idx]
                    json_data = json.loads(json_str)
                    json_valid = True
                    print(f"  JSON格式: ✅ 有效")
                    
                    # 检查JSON结构
                    has_title = 'title' in json_data
                    has_slides = 'slides' in json_data
                    slides_valid = isinstance(json_data.get('slides'), list)
                    
                    print(f"    包含title: {has_title}")
                    print(f"    包含slides: {has_slides}")
                    print(f"    slides是数组: {slides_valid}")
                    
                    if slides_valid:
                        slides = json_data['slides']
                        print(f"    幻灯片数量: {len(slides)}")
                        
                        # 检查每个幻灯片的结构
                        for i, slide in enumerate(slides[:3]):
                            print(f"    幻灯片 {i+1}:")
                            print(f"      type: {slide.get('type', 'N/A')}")
                            print(f"      layout: {slide.get('layout', 'N/A')}")
                            print(f"      title: {slide.get('title', 'N/A')[:50]}...")
                            
                            # 检查items结构
                            items = slide.get('items', [])
                            if items:
                                print(f"      items数量: {len(items)}")
                                for j, item in enumerate(items[:2]):
                                    if isinstance(item, dict):
                                        print(f"        item {j+1}: {list(item.keys())[:5]}")
                                    else:
                                        print(f"        item {j+1}: {type(item).__name__}")
                else:
                    print(f"  JSON格式: ⚠️ 未找到JSON结构")
                    
            except json.JSONDecodeError as e:
                print(f"  JSON格式: ❌ 解析失败 - {e}")
            
            # 检查数据结构
            if json_data and 'expected_data_structures' in test_case:
                found_structures = []
                response_str = json.dumps(json_data, ensure_ascii=False)
                
                for structure in test_case['expected_data_structures']:
                    if structure in response_str:
                        found_structures.append(structure)
                
                structure_score = len(found_structures) / len(test_case['expected_data_structures'])
                print(f"  数据结构匹配: {len(found_structures)}/{len(test_case['expected_data_structures'])} ({structure_score*100:.0f}%)")
                print(f"  匹配结构: {found_structures}")
            else:
                structure_score = 1.0
            
            # 检查布局类型
            if json_data and 'expected_layouts' in test_case:
                found_layouts = []
                if json_data.get('slides'):
                    for slide in json_data['slides']:
                        layout = slide.get('layout', '')
                        if layout in test_case['expected_layouts']:
                            found_layouts.append(layout)
                
                if found_layouts:
                    print(f"  布局匹配: ✅ 找到预期布局 {found_layouts}")
                else:
                    print(f"  布局匹配: ⚠️ 未找到预期布局")
            
            # 计算总体分数
            total_score = keyword_score * 0.4 + (1.0 if json_valid else 0.0) * 0.3 + structure_score * 0.3
            
            results.append({
                "name": test_case['name'],
                "response_length": len(full_response),
                "duration": duration,
                "keyword_score": keyword_score,
                "json_valid": json_valid,
                "structure_score": structure_score,
                "total_score": total_score,
                "found_keywords": found_keywords
            })
            
            print(f"  总体评分: {total_score*100:.0f}%")
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "name": test_case['name'],
                "error": str(e),
                "total_score": 0.0
            })
    
    # 3. 总结测试结果
    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)
    
    successful_tests = [r for r in results if r.get('total_score', 0) > 0.5]
    failed_tests = [r for r in results if r.get('total_score', 0) <= 0.5]
    
    print(f"\n测试统计:")
    print(f"  总测试数: {len(results)}")
    print(f"  成功: {len(successful_tests)}")
    print(f"  失败: {len(failed_tests)}")
    print(f"  成功率: {len(successful_tests)/len(results)*100:.0f}%")
    
    print(f"\n详细结果:")
    for result in results:
        status = "✅" if result.get('total_score', 0) > 0.5 else "❌"
        score = result.get('total_score', 0) * 100
        name = result.get('name', 'Unknown')
        print(f"  {status} {name}: {score:.0f}%")
    
    # 计算平均分数
    avg_score = sum(r.get('total_score', 0) for r in results) / len(results)
    avg_duration = sum(r.get('duration', 0) for r in results) / len(results)
    
    print(f"\n平均指标:")
    print(f"  平均评分: {avg_score*100:.0f}%")
    print(f"  平均响应时间: {avg_duration:.3f}秒")
    
    # 评估结果
    if avg_score >= 0.8:
        print(f"\n🎉 复杂共创交互测试通过！")
        print(f"   AI能够正确理解和处理复杂指令。")
    elif avg_score >= 0.6:
        print(f"\n⚠️ 复杂共创交互测试基本通过")
        print(f"   AI能够处理大部分复杂指令，但仍有改进空间。")
    else:
        print(f"\n❌ 复杂共创交互测试失败")
        print(f"   AI处理复杂指令的能力需要提升。")
    
    return avg_score >= 0.6

if __name__ == "__main__":
    print("复杂共创交互测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    success = test_complex_interactions()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 复杂共创交互测试完成！")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ 复杂共创交互测试失败")
        print("=" * 80)