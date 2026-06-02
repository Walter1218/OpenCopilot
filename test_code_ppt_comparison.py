"""
MiniMax 模型对比测试脚本 - 代码任务与PPT任务专项测试

对比 MiniMax-M2.7 和 MiniMax-M3 在代码生成、调试、重构等代码任务
以及PPT生成、优化等PPT任务上的表现差异
"""

import os
import json
import time
import httpx
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime

def load_config():
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

@dataclass
class TestResult:
    model: str
    test_name: str
    category: str
    prompt: str
    response: str
    latency: float
    token_count: int
    success: bool
    error: str = ""

class MiniMaxModelTester:
    def __init__(self):
        config = load_config()
        self.api_key = config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY")
        self.base_url = "https://api.minimax.chat/v1/chat/completions"
        if not self.api_key:
            raise ValueError("未找到 MINIMAX_API_KEY，请在 config.json 或环境变量中设置")

    def call_model(self, model: str, messages: List[Dict], max_tokens: int = 2000) -> Dict:
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
            with httpx.Client(timeout=120.0) as client:
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
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}", "latency": latency}
        except Exception as e:
            return {"success": False, "error": str(e), "latency": time.time() - start_time}

    def run_test(self, model: str, test_name: str, category: str, prompt: str, system_prompt: str = "") -> TestResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        result = self.call_model(model, messages)
        return TestResult(
            model=model, test_name=test_name, category=category, prompt=prompt,
            response=result.get("content", ""), latency=result.get("latency", 0),
            token_count=result.get("total_tokens", 0), success=result.get("success", False),
            error=result.get("error", "")
        )


# 代码任务测试用例
CODE_TEST_CASES = [
    {"name": "简单代码生成-冒泡排序", "category": "code",
     "prompt": "请用 Python 编写一个函数，实现冒泡排序算法，并添加详细的注释。",
     "system_prompt": "你是一个专业的 Python 开发者，请提供高质量的代码。"},
    {"name": "中等复杂度-装饰器", "category": "code",
     "prompt": "请用 Python 编写一个装饰器，实现函数执行时间统计功能。要求：1. 支持异步函数 2. 支持同步函数 3. 可配置输出格式 4. 添加详细注释。",
     "system_prompt": "你是一个高级 Python 开发者，请提供生产级别的代码实现。"},
    {"name": "复杂代码-ORM框架", "category": "code",
     "prompt": "请用 Python 实现一个简单的 ORM 框架，支持：1. 模型定义 2. CRUD 操作 3. 关系映射 4. 查询构建器 5. 事务支持。要求代码结构清晰，有完整的错误处理和注释。",
     "system_prompt": "你是一个架构师级别的 Python 开发者，请提供完整、可扩展的解决方案。"},
    {"name": "代码调试", "category": "code",
     "prompt": """以下 Python 代码有多个 bug，请找出并修复所有问题：
```python
import asyncio
import aiohttp

class AsyncCrawler:
    def __init__(self, urls):
        self.urls = urls
        self.results = []
    
    async def fetch(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    async def crawl_all(self):
        tasks = [self.fetch(url) for url in self.urls]
        results = await asyncio.gather(*tasks)
        self.results = results
        return results
    
    def get_results(self):
        return self.results

crawler = AsyncCrawler(['https://example.com', 'https://httpbin.org'])
results = crawler.crawl_all()
print(results)
```""",
     "system_prompt": "你是一个有经验的 Python 开发者，请仔细分析代码并修复所有问题。"},
    {"name": "代码重构", "category": "code",
     "prompt": """请重构以下代码，提高其可读性、可维护性和性能：
```python
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] is not None:
            if isinstance(data[i], dict):
                if 'value' in data[i]:
                    if data[i]['value'] > 0:
                        result.append(data[i]['value'] * 2)
                    else:
                        result.append(0)
                else:
                    result.append(-1)
            else:
                result.append(-2)
        else:
            result.append(-3)
    return result
```""",
     "system_prompt": "你是一个代码质量专家，请提供重构后的代码，使用更清晰的逻辑和更好的设计模式。"},
    {"name": "代码解释-设计模式", "category": "code",
     "prompt": """请详细解释以下 Python 代码的功能、设计模式和潜在问题：
```python
from functools import wraps
import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'open':
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'half-open'
                else:
                    raise Exception('Circuit breaker is open')
            try:
                result = func(*args, **kwargs)
                if self.state == 'half-open':
                    self.state = 'closed'
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = 'open'
                raise e
        return wrapper
```""",
     "system_prompt": "你是一个软件架构师，请详细解释代码的功能、设计模式和潜在问题。"},
    {"name": "单元测试生成", "category": "code",
     "prompt": """请为以下 Python 类编写完整的单元测试，使用 pytest 框架：
```python
class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance
        self._transactions = []
    
    def deposit(self, amount):
        if amount <= 0:
            return False
        self.balance += amount
        self._transactions.append(('deposit', amount))
        return True
    
    def withdraw(self, amount):
        if amount <= 0 or amount > self.balance:
            return False
        self.balance -= amount
        self._transactions.append(('withdraw', amount))
        return True
    
    def get_balance(self):
        return self.balance
    
    def get_transactions(self):
        return self._transactions.copy()
```""",
     "system_prompt": "你是一个测试专家，请编写全面、健壮的单元测试，覆盖正常情况、边界情况和异常情况。"},
    {"name": "代码审查-安全审计", "category": "code",
     "prompt": """请对以下 Python 代码进行代码审查，指出潜在问题、安全漏洞、性能问题和改进建议：
```python
import hashlib
import json
import os
from datetime import datetime

class UserManager:
    def __init__(self, db_path='users.json'):
        self.db_path = db_path
        self.users = self._load_users()
    
    def _load_users(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.users, f)
    
    def register(self, username, password):
        if username in self.users:
            return False, '用户已存在'
        password_hash = hashlib.md5(password.encode()).hexdigest()
        self.users[username] = {
            'password': password_hash,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        self._save_users()
        return True, '注册成功'
    
    def login(self, username, password):
        if username not in self.users:
            return False, '用户不存在'
        password_hash = hashlib.md5(password.encode()).hexdigest()
        if self.users[username]['password'] != password_hash:
            return False, '密码错误'
        self.users[username]['last_login'] = datetime.now().isoformat()
        self._save_users()
        return True, '登录成功'
```""",
     "system_prompt": "你是一个安全专家和代码质量专家，请进行全面的代码审查。"},
]

# PPT任务测试用例
PPT_TEST_CASES = [
    {"name": "PPT内容生成-医疗AI", "category": "ppt",
     "prompt": "请为一个关于'人工智能在医疗领域的应用'的PPT生成完整的内容大纲，包括：1. 标题页 2. 目录 3. 引言 4. 主要应用领域（至少4个） 5. 案例分析 6. 挑战与机遇 7. 未来展望 8. 结论 9. 参考文献。每个部分都要有具体的要点和关键信息。",
     "system_prompt": "你是一个专业的PPT内容策划师，请提供专业、有深度的内容。"},
    {"name": "PPT结构设计-创业路演", "category": "ppt",
     "prompt": "我需要为一个创业项目路演设计PPT结构，项目是'基于AI的智能教育平台'。请设计一个10-12页的PPT结构，每页都要有明确的标题、要点和视觉元素建议。",
     "system_prompt": "你是一个专业的PPT设计师和商业策划师，请提供专业的结构设计。"},
    {"name": "PPT内容优化", "category": "ppt",
     "prompt": "请优化以下PPT内容，使其更加专业、有说服力：\n\n原标题：公司业绩报告\n要点：\n- 今年销售额增长\n- 成本有所下降\n- 利润提高\n- 员工数量增加\n- 新开了几个办事处\n\n请提供优化后的标题、要点，并建议添加哪些数据和图表来增强说服力。",
     "system_prompt": "你是一个专业的商业文案和PPT专家，请提供优化建议。"},
    {"name": "PPT风格建议-科技发布会", "category": "ppt",
     "prompt": "我需要为一个科技公司的产品发布会设计PPT，请提供：1. 推荐的配色方案 2. 字体搭配建议 3. 布局风格 4. 动画效果建议 5. 视觉元素建议 6. 整体设计原则。要求现代、科技感强、专业。",
     "system_prompt": "你是一个专业的UI/UX设计师和PPT设计专家，请提供详细的设计建议。"},
    {"name": "PPT图表设计-数据可视化", "category": "ppt",
     "prompt": "请为以下数据设计合适的图表类型，并说明如何在PPT中呈现：\n\n数据：\n- 2023年Q1-Q4销售额：120万、150万、180万、210万\n- 各产品线占比：产品A 35%、产品B 25%、产品C 20%、其他 20%\n- 月度用户增长：1月5000、2月6500、3月8200、4月10000、5月12000、6月15000\n- 地区分布：华东40%、华南25%、华北20%、其他15%",
     "system_prompt": "你是一个数据可视化专家和PPT设计师，请提供专业的图表设计建议。"},
    {"name": "PPT演讲备注生成", "category": "ppt",
     "prompt": "请为以下PPT页面生成演讲备注：\n\n页面标题：AI技术架构\n要点：\n- 微服务架构设计\n- 实时数据处理流程\n- 模型训练与部署\n- 系统监控与告警\n\n要求：每个要点2-3句话，语言口语化，包含过渡语，时长控制在2分钟内。",
     "system_prompt": "你是一个专业的演讲教练和PPT专家，请提供自然、有感染力的演讲备注。"},
    {"name": "PPT模板设计-技术分享", "category": "ppt",
     "prompt": "请设计一个适用于技术分享会的PPT模板方案，包括：1. 封面设计 2. 目录页 3. 内容页 4. 图表页 5. 代码展示页 6. 结论页 7. Q&A页。要求现代、简洁、技术感强。",
     "system_prompt": "你是一个专业的PPT模板设计师，请提供详细的设计方案。"},
    {"name": "PPT动画设计-产品发布", "category": "ppt",
     "prompt": "我需要为一个产品发布PPT设计动画效果，请提供：1. 页面切换动画建议 2. 元素入场动画 3. 数据展示动画 4. 流程图动画 5. 重点强调动画。要求：专业、不花哨、增强表达力。",
     "system_prompt": "你是一个PPT动画设计专家，请提供专业、有效的动画设计建议。"},
]


def calculate_score(result: TestResult, category: str) -> Dict[str, float]:
    """计算测试得分"""
    scores = {}
    scores["success"] = 10.0 if result.success else 0.0
    if not result.success:
        return scores

    response = result.response

    # 响应速度
    if result.latency < 5:
        scores["speed"] = 10.0
    elif result.latency < 10:
        scores["speed"] = 8.0
    elif result.latency < 20:
        scores["speed"] = 6.0
    elif result.latency < 30:
        scores["speed"] = 4.0
    else:
        scores["speed"] = 2.0

    # Token效率
    if result.token_count > 0:
        chars_per_token = len(response) / result.token_count
        scores["token_efficiency"] = min(10.0, max(2.0, chars_per_token * 3))
    else:
        scores["token_efficiency"] = 0.0

    if category == "code":
        # 代码质量
        code_quality = 4.0
        for feat in ["def ", "class ", "import ", "return", "if ", "for ", "try:", "except:", "with ", "async ", "# "]:
            if feat in response:
                code_quality += 0.5
        scores["code_quality"] = min(code_quality, 10.0)
        # 注释质量
        comment_quality = 4.0
        for ind in ["# ", '"""', "'''", "注释", "说明", "参数", "返回值"]:
            if ind in response:
                comment_quality += 0.7
        scores["comment_quality"] = min(comment_quality, 10.0)
        # 完整性
        completeness = 4.0
        if len(response) > 500: completeness += 1.5
        if len(response) > 1500: completeness += 1.5
        if "```" in response: completeness += 1.5
        if "示例" in response or "example" in response.lower(): completeness += 1.0
        scores["completeness"] = min(completeness, 10.0)
    else:
        # 专业性
        professionalism = 4.0
        for term in ["设计", "布局", "配色", "字体", "视觉", "动画", "图表", "数据", "结构", "要点", "案例", "策略", "方案"]:
            if term in response:
                professionalism += 0.4
        scores["professionalism"] = min(professionalism, 10.0)
        # 创意性
        creativity = 4.0
        for ind in ["创新", "独特", "创意", "新颖", "现代", "科技感", "互动", "沉浸", "用户体验"]:
            if ind in response:
                creativity += 0.6
        scores["creativity"] = min(creativity, 10.0)
        # 实用性
        practicality = 4.0
        for ind in ["具体", "详细", "步骤", "方法", "技巧", "工具", "示例", "建议", "推荐"]:
            if ind in response:
                practicality += 0.5
        scores["practicality"] = min(practicality, 10.0)
        # 完整性
        completeness = 4.0
        if len(response) > 300: completeness += 1.0
        if len(response) > 800: completeness += 1.5
        if len(response) > 1500: completeness += 1.5
        if "1." in response and "2." in response: completeness += 1.0
        scores["completeness"] = min(completeness, 10.0)

    return scores


def run_comparison_test():
    tester = MiniMaxModelTester()
    models = ["MiniMax-M2.7", "MiniMax-M3"]
    all_results = {m: {"code": [], "ppt": []} for m in models}

    print("=" * 80)
    print("MiniMax 模型对比测试 - 代码任务与PPT任务专项测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试模型: {', '.join(models)}")
    print(f"代码任务: {len(CODE_TEST_CASES)} 个用例 | PPT任务: {len(PPT_TEST_CASES)} 个用例")
    print("=" * 80)

    for category, test_cases, label in [("code", CODE_TEST_CASES, "代码任务"), ("ppt", PPT_TEST_CASES, "PPT任务")]:
        print(f"\n{'=' * 80}")
        print(f"{label}测试")
        print("=" * 80)
        for tc in test_cases:
            print(f"\n测试: {tc['name']}")
            print("-" * 40)
            for model in models:
                print(f"  {model}...", end=" ")
                result = tester.run_test(model=model, test_name=tc["name"], category=category,
                                        prompt=tc["prompt"], system_prompt=tc.get("system_prompt", ""))
                all_results[model][category].append(result)
                if result.success:
                    print(f"OK ({result.latency:.1f}s, {result.token_count}t)")
                else:
                    print(f"FAIL ({result.error[:80]})")

    # 得分计算
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    model_scores = {m: {"code": [], "ppt": []} for m in models}

    for category, label in [("code", "代码任务"), ("ppt", "PPT任务")]:
        print(f"\n{label}:")
        print("-" * 40)
        for model in models:
            total = 0
            for r in all_results[model][category]:
                scores = calculate_score(r, category)
                avg = sum(scores.values()) / len(scores) if scores else 0
                model_scores[model][category].append({"test_name": r.test_name, "scores": scores, "avg_score": avg})
                total += avg
                print(f"  {model} | {r.test_name}: {avg:.1f}/10")
            avg_total = total / len(all_results[model][category])
            print(f"  {model} 平均分: {avg_total:.1f}/10")

    # 维度对比
    print("\n" + "=" * 80)
    print("维度对比")
    print("=" * 80)

    code_dims = ["success", "speed", "token_efficiency", "code_quality", "comment_quality", "completeness"]
    code_dim_names = {"success": "成功率", "speed": "响应速度", "token_efficiency": "Token效率",
                      "code_quality": "代码质量", "comment_quality": "注释质量", "completeness": "完整性"}

    ppt_dims = ["success", "speed", "token_efficiency", "professionalism", "creativity", "practicality", "completeness"]
    ppt_dim_names = {"success": "成功率", "speed": "响应速度", "token_efficiency": "Token效率",
                     "professionalism": "专业性", "creativity": "创意性", "practicality": "实用性", "completeness": "完整性"}

    for category, dims, dim_names, label in [
        ("code", code_dims, code_dim_names, "代码任务"),
        ("ppt", ppt_dims, ppt_dim_names, "PPT任务")
    ]:
        print(f"\n{label}维度:")
        for dim in dims:
            print(f"  {dim_names[dim]}:")
            for model in models:
                dim_scores = [s["scores"].get(dim, 0) for s in model_scores[model][category]]
                avg = sum(dim_scores) / len(dim_scores) if dim_scores else 0
                print(f"    {model}: {avg:.1f}/10")

    # 生成报告
    report = {
        "test_time": datetime.now().isoformat(),
        "models": models,
        "test_cases": {"code": len(CODE_TEST_CASES), "ppt": len(PPT_TEST_CASES)},
        "results": {}
    }
    for model in models:
        report["results"][model] = {}
        for category in ["code", "ppt"]:
            rs = all_results[model][category]
            report["results"][model][category] = {
                "total_tests": len(rs),
                "successful_tests": sum(1 for r in rs if r.success),
                "avg_latency": sum(r.latency for r in rs) / len(rs),
                "avg_tokens": sum(r.token_count for r in rs) / len(rs),
                "avg_score": sum(s["avg_score"] for s in model_scores[model][category]) / len(model_scores[model][category]),
                "test_details": []
            }
            for r in rs:
                scores = calculate_score(r, category)
                report["results"][model][category]["test_details"].append({
                    "test_name": r.test_name, "success": r.success, "latency": r.latency,
                    "token_count": r.token_count, "response_length": len(r.response),
                    "scores": scores, "avg_score": sum(scores.values()) / len(scores) if scores else 0,
                    "response_preview": r.response[:300] + "..." if len(r.response) > 300 else r.response
                })

    with open("code_ppt_comparison_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: code_ppt_comparison_report.json")

    # 最终结论
    print("\n" + "=" * 80)
    print("最终结论")
    print("=" * 80)
    for category, label in [("code", "代码任务"), ("ppt", "PPT任务")]:
        print(f"\n{label}:")
        scores_dict = {}
        for model in models:
            avg = sum(s["avg_score"] for s in model_scores[model][category]) / len(model_scores[model][category])
            scores_dict[model] = avg
            print(f"  {model}: {avg:.1f}/10")
        if scores_dict["MiniMax-M3"] > scores_dict["MiniMax-M2.7"]:
            imp = ((scores_dict["MiniMax-M3"] - scores_dict["MiniMax-M2.7"]) / scores_dict["MiniMax-M2.7"]) * 100
            print(f"  => MiniMax-M3 表现更好，提升 {imp:.1f}%")
        elif scores_dict["MiniMax-M2.7"] > scores_dict["MiniMax-M3"]:
            dec = ((scores_dict["MiniMax-M2.7"] - scores_dict["MiniMax-M3"]) / scores_dict["MiniMax-M2.7"]) * 100
            print(f"  => MiniMax-M2.7 表现更好，M3 下降 {dec:.1f}%")
        else:
            print(f"  => 两个模型表现相当")

    print(f"\n综合结论:")
    m27_all = sum(sum(s["avg_score"] for s in model_scores["MiniMax-M2.7"][c]) / len(model_scores["MiniMax-M2.7"][c]) for c in ["code", "ppt"]) / 2
    m3_all = sum(sum(s["avg_score"] for s in model_scores["MiniMax-M3"][c]) / len(model_scores["MiniMax-M3"][c]) for c in ["code", "ppt"]) / 2
    print(f"  MiniMax-M2.7: {m27_all:.1f}/10")
    print(f"  MiniMax-M3:   {m3_all:.1f}/10")
    if m3_all > m27_all:
        print(f"  => M3 综合更优，提升 {((m3_all-m27_all)/m27_all)*100:.1f}%")
    elif m27_all > m3_all:
        print(f"  => M2.7 综合更优，M3 下降 {((m27_all-m3_all)/m27_all)*100:.1f}%")
    else:
        print(f"  => 综合表现相当")

    return report


if __name__ == "__main__":
    try:
        run_comparison_test()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
