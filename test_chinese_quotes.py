#!/usr/bin/env python3
"""测试中文引号清理逻辑"""
import json

def clean_chinese_quotes(text):
    """清理中文引号"""
    text = text.replace('\u201c', '').replace('\u201d', '')  # 删除中文双引号
    text = text.replace('\u2018', '').replace('\u2019', '')  # 删除中文单引号
    text = text.replace('\u300c', '').replace('\u300d', '')  # 删除中文书名号
    text = text.replace('\u300e', '').replace('\u300f', '')  # 删除中文书名号
    return text

def test_chinese_quotes():
    """测试中文引号清理逻辑"""
    print("=" * 80)
    print("测试中文引号清理逻辑")
    print("=" * 80)
    
    # 测试用例1：包含中文双引号的JSON
    test1 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从"对话助手"到"能自己干活的数字员工""}]}'
    print(f"测试用例1 - 中文双引号:")
    print(f"原始: {test1}")
    
    cleaned1 = clean_chinese_quotes(test1)
    print(f"清理后: {cleaned1}")
    
    try:
        data1 = json.loads(cleaned1)
        print(f"✅ 解析成功: {data1}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
    print()
    
    # 测试用例2：包含中文单引号的JSON
    test2 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从"对话助手"到"能自己干活的数字员工""}]}'
    print(f"测试用例2 - 中文单引号:")
    print(f"原始: {test2}")
    
    cleaned2 = clean_chinese_quotes(test2)
    print(f"清理后: {cleaned2}")
    
    try:
        data2 = json.loads(cleaned2)
        print(f"✅ 解析成功: {data2}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
    print()
    
    # 测试用例3：包含中文书名号的JSON
    test3 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从「对话助手」到「能自己干活的数字员工」"}]}'
    print(f"测试用例3 - 中文书名号:")
    print(f"原始: {test3}")
    
    cleaned3 = clean_chinese_quotes(test3)
    print(f"清理后: {cleaned3}")
    
    try:
        data3 = json.loads(cleaned3)
        print(f"✅ 解析成功: {data3}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
    print()
    
    # 测试用例4：混合中文引号
    test4 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从"对话助手"到"能自己干活的数字员工""}]}'
    print(f"测试用例4 - 混合中文引号:")
    print(f"原始: {test4}")
    
    cleaned4 = clean_chinese_quotes(test4)
    print(f"清理后: {cleaned4}")
    
    try:
        data4 = json.loads(cleaned4)
        print(f"✅ 解析成功: {data4}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
    print()
    
    # 测试用例5：中文引号在JSON值内部
    test5 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从"对话助手"到"能自己干活的数字员工""}]}'
    print(f"测试用例5 - 中文引号在JSON值内部:")
    print(f"原始: {test5}")
    
    cleaned5 = clean_chinese_quotes(test5)
    print(f"清理后: {cleaned5}")
    
    try:
        data5 = json.loads(cleaned5)
        print(f"✅ 解析成功: {data5}")
    except json.JSONDecodeError as e:
        print(f"❌ 解析失败: {e}")
    print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_chinese_quotes()