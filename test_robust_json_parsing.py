#!/usr/bin/env python3
"""测试更robust的JSON解析逻辑"""
import json
import re

def clean_chinese_quotes(text):
    """清理中文引号"""
    text = text.replace('\u201c', '').replace('\u201d', '')  # 删除中文双引号
    text = text.replace('\u2018', '').replace('\u2019', '')  # 删除中文单引号
    text = text.replace('\u300c', '').replace('\u300d', '')  # 删除中文书名号
    text = text.replace('\u300e', '').replace('\u300f', '')  # 删除中文书名号
    return text

def extract_json_from_text_v2(text):
    """从大模型的混合输出中提取 JSON 数据，或降级解析 Markdown 为 PPT 大纲"""
    # 0. 清理中文引号（AI有时会返回中文引号，导致JSON解析失败）
    text = clean_chinese_quotes(text)
    
    # 1. 尝试匹配 ```json ... ``` 块（支持对象 {} 或数组 []）
    match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    json_str = match.group(1) if match else text

    # 2. 尝试直接解析 JSON
    try:
        start_obj = json_str.find('{')
        start_arr = json_str.find('[')
        start_idx = -1
        
        if start_obj != -1 and start_arr != -1:
            start_idx = min(start_obj, start_arr)
        else:
            start_idx = max(start_obj, start_arr)
            
        if start_idx != -1:
            end_idx = -1
            if json_str[start_idx] == '{':
                end_idx = json_str.rfind('}') + 1
            else:
                end_idx = json_str.rfind(']') + 1
                
            if end_idx > start_idx:
                clean_str = json_str[start_idx:end_idx]
                parsed = json.loads(clean_str)
                
                # 兼容两种格式：
                # 1. {"title": "...", "slides": [...]} - 完整格式，直接返回
                # 2. {"slides": [...]} - 部分格式，返回完整对象
                # 3. [...] - 数组格式，直接返回
                if isinstance(parsed, dict) and "slides" in parsed:
                    return parsed  # 返回完整字典，保留 title 等字段
                elif isinstance(parsed, list):
                    return parsed
    except Exception:
        pass
    
    # 2.1 尝试修复被截断的 JSON
    try:
        # 检查是否是被截断的 JSON（包含 slides 但不完整）
        if '"slides"' in json_str and '"slides":[' in json_str:
            # 找到 slides 数组的开始
            slides_start = json_str.find('"slides":[')
            if slides_start > 0:
                # 提取 slides 数组内容（跳过 "slides":[ 部分）
                slides_content = json_str[slides_start + 10:]  # 跳过 "slides":[
                
                # 找到最后一个完整的 slide 对象
                # 通过匹配花括号来找到完整的对象
                brace_count = 0
                last_complete_slide_end = -1
                in_slide = False
                
                for i, char in enumerate(slides_content):
                    if char == '{':
                        if not in_slide:
                            in_slide = True
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and in_slide:
                            last_complete_slide_end = i
                            in_slide = False
                
                if last_complete_slide_end > 0:
                    # 截取到最后一个完整的 slide
                    slides_content = slides_content[:last_complete_slide_end + 1]
                    
                    # 构建完整的 JSON
                    # 提取 title 字段
                    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', json_str[:slides_start])
                    if title_match:
                        fixed_json = '{"title":"' + title_match.group(1) + '","slides":[' + slides_content + ']}'
                    else:
                        fixed_json = '{"slides":[' + slides_content + ']}'
                    
                    try:
                        parsed = json.loads(fixed_json)
                        if isinstance(parsed, dict) and "slides" in parsed:
                            print(f"[ppt_generator] 修复被截断的 JSON，保留 {len(parsed['slides'])} 个 slides")
                            return parsed
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
        
    # 3. 如果 JSON 解析失败，但包含 Markdown 标题，则降级将 Markdown 转换为 JSON 结构
    if '# ' in text or '## ' in text:
        slides = []
        current_slide = None
        table_buffer = []       # 累积表格行
        in_table = False        # 是否在表格中
        in_code_block = False   # 是否在代码块中
        code_buffer = []        # 累积代码行
        code_lang = ""          # 代码语言

        def flush_table():
            """将累积的表格行写入当前 slide"""
            nonlocal table_buffer, in_table
            if current_slide and table_buffer:
                current_slide["layout"] = "table"
                current_slide["table_data"] = table_buffer.copy()
                current_slide["items"] = current_slide.get("items", [])
            table_buffer = []
            in_table = False

        def flush_code():
            """将累积的代码块写入当前 slide"""
            nonlocal code_buffer, code_lang, in_code_block
            if current_slide and code_buffer:
                current_slide["layout"] = "code"
                current_slide["code_lang"] = code_lang
                current_slide["code_text"] = "\n".join(code_buffer)
                current_slide["items"] = current_slide.get("items", [])
            code_buffer = []
            code_lang = ""
            in_code_block = False

        for line in text.split('\n'):
            stripped = line.strip()
            
            # 代码块检测
            if stripped.startswith('```'):
                if in_code_block:
                    flush_code()
                else:
                    flush_table()  # 先刷新可能的表格
                    code_lang = stripped[3:].strip()
                    in_code_block = True
                continue
            if in_code_block:
                code_buffer.append(line)
                continue
            
            # 表格检测（包含 | 且下一行是 |---| 分隔符）
            if '|' in stripped and stripped.strip('|').strip():
                if not in_table:
                    flush_code()  # 刷新可能的代码块
                    # 检查是否真的是表格（需要后续行也存在）
                    in_table = True
                table_buffer.append(stripped)
                continue
            elif in_table and stripped.strip():
                # 可能是表格的 continuation
                if '|' in stripped:
                    table_buffer.append(stripped)
                    continue
                else:
                    flush_table()
            
            # 空行处理
            if not stripped:
                flush_table()
                flush_code()
                continue
            
            flush_table()
            flush_code()
            
            if stripped.startswith('# '):
                if current_slide: slides.append(current_slide)
                current_slide = {"type": "title", "layout": "center", "title": stripped[2:].strip(), "subtitle": "", "items": []}
            elif stripped.startswith('## '):
                if current_slide: slides.append(current_slide)
                current_slide = {"type": "content", "layout": "text_only", "title": stripped[3:].strip(), "items": []}
            elif stripped.startswith('- ') or stripped.startswith('* '):
                if current_slide:
                    if "items" not in current_slide: current_slide["items"] = []
                    current_slide["items"].append({"level": 0, "text": stripped[2:].strip()})
            else:
                if current_slide and current_slide.get("type") == "content":
                    if "items" not in current_slide: current_slide["items"] = []
                    current_slide["items"].append({"level": 0, "text": stripped})

        # 刷新残留缓冲区
        flush_table()
        flush_code()
        if current_slide:
            slides.append(current_slide)
        if slides:
            return slides
            
    return None

def test_robust_json_parsing():
    """测试更robust的JSON解析逻辑"""
    print("=" * 80)
    print("测试更robust的JSON解析逻辑")
    print("=" * 80)
    
    # 测试用例1：正常JSON
    test1 = '{"title": "测试标题", "slides": [{"type": "content", "title": "内容页"}]}'
    print(f"测试用例1 - 正常JSON:")
    print(f"原始: {test1}")
    
    result1 = extract_json_from_text_v2(test1)
    if result1:
        print(f"✅ 解析成功: {result1}")
    else:
        print(f"❌ 解析失败")
    print()
    
    # 测试用例2：包含中文引号的JSON
    test2 = '{"title": "测试标题", "slides": [{"type": "content", "title": "从\u201c对话助手\u201d到\u201c能自己干活的数字员工\u201d"}]}'
    print(f"测试用例2 - 包含中文引号的JSON:")
    print(f"原始: {test2}")
    
    result2 = extract_json_from_text_v2(test2)
    if result2:
        print(f"✅ 解析成功: {result2}")
    else:
        print(f"❌ 解析失败")
    print()
    
    # 测试用例3：被截断的JSON
    test3 = '{"title": "测试标题", "slides": [{"type": "content", "title": "内容页1"}, {"type": "content", "title": "内容页2"}'  # 缺少结尾
    print(f"测试用例3 - 被截断的JSON:")
    print(f"原始: {test3}")
    
    result3 = extract_json_from_text_v2(test3)
    if result3:
        print(f"✅ 解析成功（修复后）: {result3}")
    else:
        print(f"❌ 解析失败")
    print()
    
    # 测试用例4：包含markdown的JSON
    test4 = '''```json
{
  "title": "测试标题",
  "slides": [
    {
      "type": "content",
      "title": "内容页"
    }
  ]
}
```'''
    print(f"测试用例4 - 包含markdown的JSON:")
    print(f"原始: {test4[:100]}...")
    
    result4 = extract_json_from_text_v2(test4)
    if result4:
        print(f"✅ 解析成功: {result4}")
    else:
        print(f"❌ 解析失败")
    print()
    
    # 测试用例5：markdown格式的PPT大纲
    test5 = '''# 测试标题

## 内容页1
- 要点1
- 要点2

## 内容页2
- 要点3
- 要点4
'''
    print(f"测试用例5 - markdown格式的PPT大纲:")
    print(f"原始: {test5[:100]}...")
    
    result5 = extract_json_from_text_v2(test5)
    if result5:
        print(f"✅ 解析成功（降级处理）: {result5}")
    else:
        print(f"❌ 解析失败")
    print()
    
    print("=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_robust_json_parsing()