#!/usr/bin/env python3
"""测试PPT生成配置是否生效"""
import sys
import os
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

from config_manager import ConfigManager
from opencopilot.providers.llm_provider import MiMoProvider

def test_config():
    """测试配置是否正确读取"""
    print("=" * 60)
    print("测试配置读取")
    print("=" * 60)
    
    # 测试ConfigManager
    cfg = ConfigManager.get_instance()
    llm_cfg = cfg.get_llm()
    print(f"ConfigManager.get_llm() 返回:")
    print(f"  max_completion_tokens: {llm_cfg.get('max_completion_tokens')}")
    print(f"  temperature: {llm_cfg.get('temperature')}")
    print(f"  repetition_penalty: {llm_cfg.get('repetition_penalty')}")
    print()
    
    # 测试MiMoProvider
    provider = MiMoProvider()
    print(f"MiMoProvider 初始化:")
    print(f"  _max_completion_tokens: {provider._max_completion_tokens}")
    print(f"  _temperature: {provider._temperature}")
    print(f"  _repetition_penalty: {provider._repetition_penalty}")
    print()
    
    # 验证配置
    assert llm_cfg.get('max_completion_tokens') == 32768, \
        f"ConfigManager max_completion_tokens 应该是 32768，实际是 {llm_cfg.get('max_completion_tokens')}"
    assert provider._max_completion_tokens == 32768, \
        f"MiMoProvider max_completion_tokens 应该是 32768，实际是 {provider._max_completion_tokens}"
    
    print("✅ 配置验证通过！")
    return True

def test_ppt_generation():
    """测试PPT生成是否会截断"""
    print("\n" + "=" * 60)
    print("测试PPT生成")
    print("=" * 60)
    
    provider = MiMoProvider()
    
    # 测试prompt
    test_prompt = """请根据以下内容生成 PPT 大纲。

要求：
1. 严格输出纯 JSON 格式，不要包含任何其他文字
2. JSON 格式必须包含 "title" 和 "slides" 字段
3. slides 数组中每个对象必须包含 "type", "layout", "title" 字段
4. type 可选值: "title", "content", "ending"
5. layout 可选值: "center", "text_only", "two_column", "image_text"

内容：
人工智能（AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

请生成完整的PPT大纲JSON。"""
    
    print(f"Prompt 长度: {len(test_prompt)} 字符")
    print(f"预期输出: 2000-5000 字符")
    print()
    
    # 调用LLM
    try:
        response_chunks = []
        for chunk in provider.stream_chat(test_prompt):
            response_chunks.append(chunk)
        
        full_response = ''.join(response_chunks)
        print(f"实际输出长度: {len(full_response)} 字符")
        print(f"输出前200字符: {full_response[:200]}...")
        print()
        
        # 检查是否被截断
        if full_response.endswith('}'):
            print("✅ JSON 输出完整（以 } 结尾）")
        else:
            print("⚠️  JSON 输出可能被截断（不以 } 结尾）")
            print(f"最后50字符: {full_response[-50:]}")
        
        # 尝试解析JSON
        import json
        try:
            # 提取JSON
            start_idx = full_response.find('{')
            end_idx = full_response.rfind('}') + 1
            json_str = full_response[start_idx:end_idx]
            data = json.loads(json_str)
            
            if 'slides' in data:
                print(f"✅ JSON 解析成功，包含 {len(data['slides'])} 个 slides")
                return True
            else:
                print("⚠️  JSON 解析成功但缺少 slides 字段")
                return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试PPT生成配置...")
    print()
    
    # 测试配置
    config_ok = test_config()
    
    if config_ok:
        # 测试PPT生成
        ppt_ok = test_ppt_generation()
        
        if ppt_ok:
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！PPT生成配置已生效。")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  PPT生成测试未通过，可能需要进一步调整。")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 配置测试未通过，请检查config.json。")
        print("=" * 60)
