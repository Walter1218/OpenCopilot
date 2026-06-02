"""
MiniMax 模型对比测试脚本

对比 MiniMax-M2.7 和 MiniMax-M3 在多个维度的表现
"""

import os
import json
import time
import httpx
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

# 加载配置
def load_config():
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@dataclass
class TestResult:
    """测试结果数据类"""
    model: str
    test_name: str
    prompt: str
    response: str
    latency: float  # 秒
    token_count: int
    success: bool
    error: str = ""

class MiniMaxModelTester:
    """MiniMax 模型测试器"""
    
    def __init__(self):
        config = load_config()
        self.api_key = config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY")
        self.base_url = "https://api.minimax.chat/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("未找到 MINIMAX_API_KEY，请在 config.json 或环境变量中设置")
    
    def call_model(self, model: str, messages: List[Dict], max_tokens: int = 1000) -> Dict:
        """调用 MiniMax 模型"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        start_time = time.time()
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                latency = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    return {
                        "success": True,
                        "content": content,
                        "latency": latency,
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "latency": latency
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.time() - start_time
            }
    
    def run_test(self, model: str, test_name: str, prompt: str, system_prompt: str = "") -> TestResult:
        """运行单个测试"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        result = self.call_model(model, messages)
        
        return TestResult(
            model=model,
            test_name=test_name,
            prompt=prompt,
            response=result.get("content", ""),
            latency=result.get("latency", 0),
            token_count=result.get("total_tokens", 0),
            success=result.get("success", False),
            error=result.get("error", "")
        )

# 测试用例定义
TEST_CASES = [
    {
        "name": "代码生成",
        "prompt": "请用 Python 编写一个函数，实现快速排序算法，并添加详细的注释。",
        "system_prompt": "你是一个专业的 Python 开发者，请提供高质量的代码。"
    },
    {
        "name": "逻辑推理",
        "prompt": "小明有 5 个苹果，小红的苹果是小明的 2 倍，小华的苹果比小红少 3 个。请问小华有多少个苹果？请详细解释你的推理过程。",
        "system_prompt": ""
    },
    {
        "name": "创意写作",
        "prompt": "请写一首关于人工智能的现代诗，要求有科技感和人文关怀。",
        "system_prompt": ""
    },
    {
        "name": "技术解释",
        "prompt": "请用简单易懂的语言解释什么是 Transformer 架构，以及它为什么在自然语言处理中如此重要。",
        "system_prompt": "你是一个技术专家，请用通俗易懂的语言解释技术概念。"
    },
    {
        "name": "问题分析",
        "prompt": "一个 Web 应用的响应时间突然变慢了，请列出可能的原因和排查步骤。",
        "system_prompt": "你是一个有经验的后端工程师。"
    },
    {
        "name": "多轮对话理解",
        "prompt": "我有一个 Python 项目，使用了 FastAPI 框架。现在我想要添加用户认证功能，应该怎么做？",
        "system_prompt": "你是一个全栈开发专家。"
    },
    {
        "name": "错误处理",
        "prompt": "以下 Python 代码报错了，请帮我找出问题并修复：\n```python\ndef divide(a, b):\n    return a / b\n\nresult = divide(10, 0)\nprint(result)\n```",
        "system_prompt": ""
    },
    {
        "name": "数据处理",
        "prompt": "我有一个 CSV 文件，包含用户数据（name, age, email）。请帮我写一个 Python 脚本，读取文件并找出所有年龄大于 30 岁的用户。",
        "system_prompt": "你是一个数据处理专家。"
    }
]

def calculate_score(result: TestResult) -> Dict[str, float]:
    """计算测试得分（基于多个维度）"""
    scores = {}
    
    # 1. 成功率 (0-10)
    scores["success"] = 10.0 if result.success else 0.0
    
    if not result.success:
        return scores
    
    # 2. 响应长度（越长通常越详细，但有上限）
    response_len = len(result.response)
    if response_len < 50:
        scores["length"] = 2.0
    elif response_len < 200:
        scores["length"] = 5.0
    elif response_len < 500:
        scores["length"] = 7.0
    elif response_len < 1000:
        scores["length"] = 9.0
    else:
        scores["length"] = 10.0
    
    # 3. 响应速度（延迟越低越好）
    if result.latency < 2:
        scores["speed"] = 10.0
    elif result.latency < 5:
        scores["speed"] = 8.0
    elif result.latency < 10:
        scores["speed"] = 6.0
    elif result.latency < 20:
        scores["speed"] = 4.0
    else:
        scores["speed"] = 2.0
    
    # 4. Token 效率（每个 token 的价值）
    if result.token_count > 0:
        chars_per_token = response_len / result.token_count
        if chars_per_token > 3:
            scores["token_efficiency"] = 10.0
        elif chars_per_token > 2:
            scores["token_efficiency"] = 8.0
        elif chars_per_token > 1:
            scores["token_efficiency"] = 6.0
        else:
            scores["token_efficiency"] = 4.0
    else:
        scores["token_efficiency"] = 0.0
    
    # 5. 内容质量（基于关键词检测）
    quality_keywords = ["```", "def ", "class ", "import ", "return", "if ", "for ", "while ", 
                       "首先", "其次", "然后", "最后", "总结", "例如", "注意"]
    quality_score = 5.0  # 基础分
    for keyword in quality_keywords:
        if keyword in result.response:
            quality_score += 0.5
    scores["content_quality"] = min(quality_score, 10.0)
    
    return scores

def run_comparison_test():
    """运行对比测试"""
    tester = MiniMaxModelTester()
    
    models = ["MiniMax-M2.7", "MiniMax-M3"]
    all_results = {model: [] for model in models}
    
    print("=" * 80)
    print("MiniMax 模型对比测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试模型: {', '.join(models)}")
    print(f"测试用例数: {len(TEST_CASES)}")
    print("=" * 80)
    
    for test_case in TEST_CASES:
        print(f"\n测试: {test_case['name']}")
        print("-" * 40)
        
        for model in models:
            print(f"  测试 {model}...", end=" ")
            result = tester.run_test(
                model=model,
                test_name=test_case["name"],
                prompt=test_case["prompt"],
                system_prompt=test_case.get("system_prompt", "")
            )
            all_results[model].append(result)
            
            if result.success:
                print(f"✓ ({result.latency:.2f}s, {result.token_count} tokens)")
            else:
                print(f"✗ ({result.error})")
    
    # 计算得分
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    model_scores = {model: [] for model in models}
    
    for model in models:
        print(f"\n{model}:")
        print("-" * 40)
        
        total_score = 0
        for result in all_results[model]:
            scores = calculate_score(result)
            avg_score = sum(scores.values()) / len(scores) if scores else 0
            model_scores[model].append({
                "test_name": result.test_name,
                "scores": scores,
                "avg_score": avg_score
            })
            total_score += avg_score
            
            print(f"  {result.test_name}: {avg_score:.1f}/10")
        
        avg_total = total_score / len(all_results[model])
        print(f"  平均分: {avg_total:.1f}/10")
    
    # 详细对比
    print("\n" + "=" * 80)
    print("详细维度对比")
    print("=" * 80)
    
    dimensions = ["success", "length", "speed", "token_efficiency", "content_quality"]
    dimension_names = {
        "success": "成功率",
        "length": "响应长度",
        "speed": "响应速度",
        "token_efficiency": "Token效率",
        "content_quality": "内容质量"
    }
    
    for dim in dimensions:
        print(f"\n{dimension_names[dim]}:")
        print("-" * 40)
        
        for model in models:
            dim_scores = [s["scores"].get(dim, 0) for s in model_scores[model]]
            avg_score = sum(dim_scores) / len(dim_scores) if dim_scores else 0
            print(f"  {model}: {avg_score:.1f}/10")
    
    # 生成详细报告
    report = {
        "test_time": datetime.now().isoformat(),
        "models": models,
        "test_cases": len(TEST_CASES),
        "results": {}
    }
    
    for model in models:
        report["results"][model] = {
            "total_tests": len(all_results[model]),
            "successful_tests": sum(1 for r in all_results[model] if r.success),
            "avg_latency": sum(r.latency for r in all_results[model]) / len(all_results[model]),
            "avg_tokens": sum(r.token_count for r in all_results[model]) / len(all_results[model]),
            "test_details": []
        }
        
        for result in all_results[model]:
            scores = calculate_score(result)
            report["results"][model]["test_details"].append({
                "test_name": result.test_name,
                "success": result.success,
                "latency": result.latency,
                "token_count": result.token_count,
                "response_length": len(result.response),
                "scores": scores,
                "avg_score": sum(scores.values()) / len(scores) if scores else 0,
                "response_preview": result.response[:200] + "..." if len(result.response) > 200 else result.response
            })
    
    # 保存报告
    report_file = "model_comparison_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: {report_file}")
    
    # 最终结论
    print("\n" + "=" * 80)
    print("最终结论")
    print("=" * 80)
    
    m27_avg = sum(s["avg_score"] for s in model_scores["MiniMax-M2.7"]) / len(model_scores["MiniMax-M2.7"])
    m3_avg = sum(s["avg_score"] for s in model_scores["MiniMax-M3"]) / len(model_scores["MiniMax-M3"])
    
    print(f"MiniMax-M2.7 平均分: {m27_avg:.1f}/10")
    print(f"MiniMax-M3 平均分: {m3_avg:.1f}/10")
    
    if m3_avg > m27_avg:
        improvement = ((m3_avg - m27_avg) / m27_avg) * 100
        print(f"\n✓ MiniMax-M3 表现更好，提升了 {improvement:.1f}%")
    elif m27_avg > m3_avg:
        decline = ((m27_avg - m3_avg) / m27_avg) * 100
        print(f"\n✗ MiniMax-M2.7 表现更好，M3 下降了 {decline:.1f}%")
    else:
        print("\n- 两个模型表现相当")
    
    return report

if __name__ == "__main__":
    try:
        report = run_comparison_test()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
