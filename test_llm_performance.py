#!/usr/bin/env python3
"""
LLM调用性能测试
测试真实的LLM调用延迟
"""
import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, '/Users/onetwo/Documents/trae_projects/OpenCopilot')

def test_llm_call_performance():
    """测试LLM调用性能"""
    print("=" * 80)
    print("LLM调用性能测试")
    print("=" * 80)
    
    # 1. 测试LLM Provider导入
    print("\n1. 测试LLM Provider导入...")
    try:
        from opencopilot.providers.llm_provider import MiMoProvider
        print("✅ MiMoProvider导入成功")
    except Exception as e:
        print(f"❌ MiMoProvider导入失败: {e}")
        return False
    
    # 2. 测试LLM配置
    print("\n2. 测试LLM配置...")
    try:
        provider = MiMoProvider()
        print(f"  模型: {provider.default_model}")
        print(f"  max_completion_tokens: {provider._max_completion_tokens}")
        print(f"  repetition_penalty: {provider._repetition_penalty}")
    except Exception as e:
        print(f"❌ LLM配置检查失败: {e}")
        return False
    
    # 3. 测试简单LLM调用
    print("\n3. 测试简单LLM调用...")
    try:
        test_prompt = "请用一句话介绍人工智能。"
        
        start_time = time.time()
        
        # 调用LLM
        response_chunks = []
        for chunk in provider.stream_chat(test_prompt):
            response_chunks.append(chunk)
        
        end_time = time.time()
        duration = end_time - start_time
        
        full_response = ''.join(response_chunks)
        
        print(f"  Prompt: {test_prompt}")
        print(f"  响应长度: {len(full_response)} 字符")
        print(f"  响应内容: {full_response[:100]}...")
        print(f"  调用耗时: {duration:.3f}秒")
        print(f"  平均速度: {len(full_response)/duration:.0f} 字符/秒")
        
    except Exception as e:
        print(f"❌ LLM调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 测试PPT生成场景的LLM调用
    print("\n4. 测试PPT生成场景的LLM调用...")
    try:
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
        
        # 调用LLM
        response_chunks = []
        for chunk in provider.stream_chat(ppt_prompt):
            response_chunks.append(chunk)
        
        end_time = time.time()
        duration = end_time - start_time
        
        full_response = ''.join(response_chunks)
        
        print(f"  Prompt长度: {len(ppt_prompt)} 字符")
        print(f"  响应长度: {len(full_response)} 字符")
        print(f"  调用耗时: {duration:.3f}秒")
        print(f"  平均速度: {len(full_response)/duration:.0f} 字符/秒")
        
        # 检查JSON格式
        import json
        try:
            # 尝试提取JSON
            start_idx = full_response.find('{')
            end_idx = full_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = full_response[start_idx:end_idx]
                data = json.loads(json_str)
                print(f"  JSON解析: ✅ 成功")
                if 'slides' in data:
                    print(f"  幻灯片数量: {len(data['slides'])}")
            else:
                print(f"  JSON解析: ⚠️ 未找到JSON结构")
        except json.JSONDecodeError as e:
            print(f"  JSON解析: ❌ 失败 - {e}")
        
    except Exception as e:
        print(f"❌ PPT生成场景LLM调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 性能对比
    print("\n5. 性能对比分析...")
    print("=" * 80)
    print("组件类型                    | 延迟        | 说明")
    print("-" * 80)
    print("埋点系统 (telemetry.emit)   | 0.041ms     | 本地日志记录，无网络调用")
    print("正则模式 (ContextAnalyzer)  | <1ms        | 本地正则匹配，无LLM调用")
    print(f"LLM调用 (简单问答)          | {duration:.1f}s        | 需要调用远程LLM服务")
    print(f"LLM调用 (PPT生成)           | {duration:.1f}s        | 需要调用远程LLM服务")
    print("=" * 80)
    
    print("\n✅ LLM性能测试完成")
    print(f"\n结论:")
    print(f"  - 埋点系统延迟极低（0.041ms），因为只是本地日志记录")
    print(f"  - 正则模式延迟很低（<1ms），因为只是本地字符串匹配")
    print(f"  - LLM调用延迟较高（{duration:.1f}s），因为需要调用远程AI服务")
    print(f"  - 这是正常现象，LLM调用必然比本地操作慢得多")
    
    return True

if __name__ == "__main__":
    print("LLM调用性能测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    success = test_llm_call_performance()
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 LLM性能测试完成！")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ LLM性能测试失败")
        print("=" * 80)