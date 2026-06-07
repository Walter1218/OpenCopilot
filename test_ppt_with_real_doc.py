#!/usr/bin/env python3
"""用实际文档测试PPT生成"""
import sys
import os
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

from opencopilot.providers.llm_provider import MiMoProvider
from ppt_generator import extract_json_from_text

def test_ppt_with_real_doc():
    """用实际文档测试PPT生成"""
    print("=" * 80)
    print("测试PPT生成 - 使用实际文档")
    print("=" * 80)
    
    # 读取文档内容
    doc_path = "/Users/onetwo/Documents/trae_projects/OpenCopilot/test_docs/ai_agent_whitepaper.md"
    if not os.path.exists(doc_path):
        print(f"❌ 文档不存在: {doc_path}")
        return False
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        doc_content = f.read()
    
    print(f"文档长度: {len(doc_content)} 字符")
    print(f"文档前500字符:\n{doc_content[:500]}...")
    print()
    
    # 构建prompt
    prompt = f"""请根据以下内容生成 PPT 大纲。

要求：
1. 严格输出纯 JSON 格式，不要包含任何其他文字
2. JSON 格式必须包含 "title" 和 "slides" 字段
3. slides 数组中每个对象必须包含 "type", "layout", "title" 字段
4. type 可选值: "title", "content", "ending"
5. layout 可选值: "center", "text_only", "two_column", "image_text"

内容：
{doc_content[:5000]}  # 限制内容长度，避免prompt过长

请生成完整的PPT大纲JSON。"""
    
    print(f"Prompt 长度: {len(prompt)} 字符")
    print()
    
    # 调用LLM
    provider = MiMoProvider()
    print(f"MiMoProvider 配置:")
    print(f"  max_completion_tokens: {provider._max_completion_tokens}")
    print(f"  model: {provider.default_model}")
    print()
    
    try:
        response_chunks = []
        for chunk in provider.stream_chat(prompt):
            response_chunks.append(chunk)
        
        full_response = ''.join(response_chunks)
        print(f"AI 返回长度: {len(full_response)} 字符")
        print(f"AI 返回前300字符:\n{full_response[:300]}...")
        print()
        
        # 检查是否被截断
        if full_response.endswith('}'):
            print("✅ JSON 输出完整（以 } 结尾）")
        else:
            print("⚠️  JSON 输出可能被截断（不以 } 结尾）")
            print(f"最后100字符:\n{full_response[-100:]}")
        print()
        
        # 尝试解析JSON
        result = extract_json_from_text(full_response)
        if result:
            print(f"✅ extract_json_from_text 解析成功")
            print(f"   返回类型: {type(result)}")
            if isinstance(result, dict) and 'slides' in result:
                print(f"   slides 数量: {len(result['slides'])}")
                print(f"   title: {result.get('title', 'N/A')}")
                return True
            elif isinstance(result, list):
                print(f"   数组长度: {len(result)}")
                return True
        else:
            print("❌ extract_json_from_text 解析失败")
            
            # 尝试手动解析
            import json
            start_idx = full_response.find('{')
            end_idx = full_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = full_response[start_idx:end_idx]
                try:
                    data = json.loads(json_str)
                    print(f"✅ 手动 JSON 解析成功")
                    if 'slides' in data:
                        print(f"   slides 数量: {len(data['slides'])}")
                        return True
                except json.JSONDecodeError as e:
                    print(f"❌ 手动 JSON 解析失败: {e}")
                    print(f"   JSON 字符串长度: {len(json_str)}")
                    print(f"   JSON 前200字符: {json_str[:200]}")
            
            return False
            
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试PPT生成...")
    print()
    
    success = test_ppt_with_real_doc()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 测试通过！PPT生成配置已生效。")
    else:
        print("❌ 测试失败！需要进一步调查。")
    print("=" * 80)
