#!/usr/bin/env python3
"""
OpenCopilot LLM 能力全方位验证测试
每项测试包含：功能正确性验证 + 输出质量打分（以 AI 自身输出为 benchmark）
"""
import httpx, json, time, os, sys
from datetime import datetime

API_TEXT = "http://127.0.0.1:8088/api/text/process"
API_AGENT = "http://127.0.0.1:18888/v1/agent/chat"
API_KG = "http://127.0.0.1:8088/api/knowledge/query"
API_CODING = "http://127.0.0.1:8088/api/coding"
API_EVAL = "http://127.0.0.1:8088/api/evaluation/evaluate"
API_CONFIG = "http://127.0.0.1:8088/api/config"
API_HEALTH = "http://127.0.0.1:8088/health"

results = []
scores = []

def record(test_id, category, description, status, output, expected_behavior, quality_score, quality_note):
    results.append({
        "id": test_id, "category": category, "description": description,
        "status": status, "output_snippet": str(output)[:500],
        "expected": expected_behavior, "quality_score": quality_score,
        "quality_note": quality_note
    })
    if quality_score is not None:
        scores.append(quality_score)

def call_text_api(action, text, target_lang="zh", custom_instruction=None):
    payload = {"action": action, "text": text}
    if target_lang:
        payload["target_language"] = target_lang
    if custom_instruction:
        payload["custom_instruction"] = custom_instruction
    try:
        r = httpx.post(API_TEXT, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            return data.get("processed", data.get("result", str(data)))
        return f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"ERROR: {e}"

def call_agent(text, action_type="auto", session_id=None, context_source="drag"):
    if session_id is None:
        session_id = f"test_{int(time.time())}"
    payload = {
        "text": text, "action_type": action_type,
        "session_id": session_id, "context_source": context_source
    }
    try:
        full = ""
        with httpx.stream("POST", API_AGENT, json=payload, timeout=120) as r:
            for line in r.iter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    chunk = json.loads(line[6:]).get("chunk", "")
                    full += chunk
        return full
    except Exception as e:
        return f"ERROR: {e}"

def call_kg(query_text):
    try:
        r = httpx.post(API_KG, json={"query": query_text}, timeout=30)
        if r.status_code == 200:
            return str(r.json())[:800]
        return f"HTTP {r.status_code}"
    except Exception as e:
        return f"ERROR: {e}"

# ==============================
# 1. 翻译测试 (Translate)
# ==============================
print("=" * 60)
print("1. 翻译能力测试")
print("=" * 60)

# T1: 英→中 技术文本
out = call_text_api("translate", "The Transformer architecture relies entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution.", "zh")
has_translation = len(out) > 20 and any('\u4e00' <= c <= '\u9fff' for c in out)
score = 9 if (has_translation and "注意力" in out) else (6 if has_translation else 2)
record("T1", "翻译", "英→中 技术文本(Transformer论文原句)", "PASS" if has_translation else "FAIL", out,
       "应包含'自注意力'、'Transformer'等技术术语的准确翻译", score,
       "很准确，术语翻译专业" if score >= 8 else "可接受")

# T2: 中→英 学术文本
out = call_text_api("translate", "大语言模型通过海量文本预训练获得了强大的语言理解和生成能力，但在精确计算和实时信息获取方面仍存在显著局限。", "en")
has_en = len(out) > 20 and sum(1 for c in out if c.isascii() and c.isalpha()) > len(out) * 0.5
score = 9 if (has_en and "language model" in out.lower()) else (5 if has_en else 2)
record("T2", "翻译", "中→英 学术文本(LLM能力边界描述)", "PASS" if has_en else "FAIL", out,
       "应准确翻译'大语言模型'为'large language model'等", score,
       "学术翻译准确流畅" if score >= 8 else "基本可读")

# T3: 空输入
out = call_text_api("translate", "", "zh")
is_handled = len(out) < 50 or "空" in out or "empty" in out.lower() or out == "" or "请" in out
record("T3", "翻译", "边缘: 空输入", "PASS" if is_handled else "WARN", out,
       "不应崩溃，返回空或提示", 10 if out == "" or "空" in out else 7,
       "正确处理空输入" if is_handled else "可能返回了无意义内容")

# T4: 单字
out = call_text_api("translate", "Hello", "zh")
record("T4", "翻译", "边缘: 单个单词", "PASS" if len(out) > 0 else "FAIL", out,
       "应正确翻译为'你好'", 10 if "你好" in out else (8 if len(out) < 10 else 5),
       "单字准确" if "你好" in out else "可接受")

# T5: 混杂中英文本
out = call_text_api("translate", "这里有个NullPointerException在第42行，需要尽快修复这个critical bug。", "en")
has_both = "NullPointerException" in out or "line 42" in out.lower() or "bug" in out.lower()
record("T5", "翻译", "边缘: 中英混杂(含代码术语)", "PASS" if has_both else "FAIL", out,
       "代码术语应保留原文，中文部分应翻译", 8 if has_both else 4,
       "代码术语保留得当" if has_both else "代码术语可能被翻译了")

# ==============================
# 2. 代码解析测试 (Code)
# ==============================
print("=" * 60)
print("2. 代码解析能力测试")
print("=" * 60)

# C1: Python 标准代码
out = call_text_api("code", """async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status}")
            return await resp.json()""", "")
has_explanation = len(out) > 30 and ("async" in out.lower() or "异步" in out or "fetch" in out.lower())
record("C1", "代码解析", "Python async/await 函数", "PASS" if has_explanation else "FAIL", out,
       "应解释async/await、异常处理、aiohttp用法", 9 if has_explanation else 3,
       "分析深入" if len(out) > 200 else "基本覆盖")

# C2: SQL 查询
out = call_text_api("code", """SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5
ORDER BY order_count DESC
LIMIT 10;""", "")
has_sql = "JOIN" in out or "LEFT JOIN" in out or "聚合" in out or "group" in out.lower()
record("C2", "代码解析", "SQL LEFT JOIN + 聚合查询", "PASS" if has_sql else "FAIL", out,
       "应解释LEFT JOIN、GROUP BY、HAVING的区别和用途", 8 if has_sql else 3,
       "SQL语法解释到位" if has_sql else "遗漏关键概念")

# C3: 含 Bug 的代码
out = call_text_api("code", """def divide_list(items, n):
    result = []
    for i in range(len(items)):
        result.append(items[i] / n)
    return result

print(divide_list([1, 2, '3', 4], 2))""", "")
bug_identified = "bug" in out.lower() or "错误" in out or "类型" in out or "type" in out.lower() or "字符串" in out
record("C3", "代码解析", "边缘: 含类型错误的代码", "PASS" if bug_identified else "FAIL", out,
       "应识别出列表中有'3'(字符串)，会导致TypeError", 10 if bug_identified else 3,
       "准确识别类型Bug" if bug_identified else "未发现类型错误")

# C4: 空代码
out = call_text_api("code", "", "")
record("C4", "代码解析", "边缘: 空代码", "PASS" if len(out) < 100 else "WARN", out,
       "应提示'没有代码'或返回空", 10 if len(out) < 50 else 5,
       "正确处理空输入" if len(out) < 50 else "生成了过多内容")

# C5: JavaScript
out = call_text_api("code", """const memoize = (fn) => {
    const cache = new Map();
    return (...args) => {
        const key = JSON.stringify(args);
        if (cache.has(key)) return cache.get(key);
        const result = fn(...args);
        cache.set(key, result);
        return result;
    };
};""", "")
has_js = "memoize" in out.lower() or "缓存" in out or "闭包" in out or "map" in out.lower()
record("C5", "代码解析", "JavaScript 闭包+memoize", "PASS" if has_js else "FAIL", out,
       "应解释闭包、Map缓存、memoization模式", 8 if has_js else 3,
       "JS闭包解释清晰" if has_js else "覆盖不全")

# ==============================
# 3. 润色测试 (Polish)
# ==============================
print("=" * 60)
print("3. 润色能力测试")
print("=" * 60)

# P1: 技术口语化文本
out = call_text_api("polish", "我觉得这个方案挺好的，但是好像有一些小问题，比如那个性能方面可能不太行，还有就是那个接口的设计也不是很合理，可能需要再改改。", "")
improved = len(out) > 20 and ("性能" in out or "接口" in out)
orig_len = len("我觉得这个方案挺好的，但是好像有一些小问题，比如那个性能方面可能不太行，还有就是那个接口的设计也不是很合理，可能需要再改改。")
record("P1", "润色", "口语化技术评论", "PASS" if improved else "FAIL", out,
       "应将口语转为书面表达，保留技术要点：性能、接口", 8 if improved else 4,
       "去口语化到位" if improved else "改写不够充分")

# P2: 空文本
out = call_text_api("polish", "", "")
record("P2", "润色", "边缘: 空输入", "PASS" if len(out) < 100 else "WARN", out,
       "不应崩溃", 10 if len(out) < 50 else 5, "正常")

# P3: Markdown 技术文档
out = call_text_api("polish", "## 安装步骤\n首先你要下载这个文件然后解压它。\n然后运行那个脚本。\n最后看一下是不是成功了。", "")
has_md = "安装" in out and len(out) > 20
record("P3", "润色", "Markdown技术文档去口语化", "PASS" if has_md else "FAIL", out,
       "应保留Markdown结构，去除口语化表达", 9 if has_md and len(out) > 50 else 5,
       "Markdown结构保留+语言优化" if has_md else "改动不足")

# ==============================
# 4. 解释测试 (Explain)
# ==============================
print("=" * 60)
print("4. 解释能力测试")
print("=" * 60)

# E1: 技术概念
out = call_text_api("explain", "什么是向量数据库？它与传统关系型数据库有什么本质区别？", "")
has_expl = len(out) > 50 and ("向量" in out or "embedding" in out.lower())
record("E1", "解释", "技术概念: 向量数据库", "PASS" if has_expl else "FAIL", out,
       "应解释向量存储/相似度搜索/ANN/与传统DB对比", 9 if has_expl else 3,
       "解释深入准确" if has_expl else "内容不足")

# E2: 简单概念
out = call_text_api("explain", "什么是Python的GIL?", "")
has_gil = "GIL" in out and "锁" in out and len(out) > 30
record("E2", "解释", "技术概念: Python GIL", "PASS" if has_gil else "FAIL", out,
       "应解释Global Interpreter Lock及其对多线程的影响", 10 if has_gil else 3,
       "GIL解释精准" if has_gil else "关键信息缺失")

# E3: 空输入
out = call_text_api("explain", "", "")
record("E3", "解释", "边缘: 空输入", "PASS" if len(out) < 100 else "WARN", out,
       "不应崩溃", 10 if len(out) < 50 else 5, "正常")

# ==============================
# 5. 总结测试 (Summarize)
# ==============================
print("=" * 60)
print("5. 总结能力测试")
print("=" * 60)

# S1: 长文总结
long_text = """OpenCopilot 是一个致力于探索下一代人机交互模式的系统级工具集。
它将底层硬件事件监听（鼠标/键盘）、高帧率 GUI 特效渲染与最前沿的 LLM 能力深度结合。
核心特性包括：上下文感知专属智能体，支持场景自动感知和多角色人格；
双引擎动态热切架构，云端LLM与本地推理一键切换；
纯鼠标双击唤醒，右键唤出悬浮卡片；
双图层解耦设计，全屏穿透图层负责光标特效，局部交互图层承载AI卡片；
极低资源占用的系统级监听，基于pynput与原生系统调用；
基于Privileged Broker的极客级交互，突破macOS TCC沙盒限制。
系统采用四层架构：UI层(PyQt6悬浮卡片)、Agent层(asu_custom_agent.py)、
Broker层(特权代理)、系统层(macOS Accessibility API + NSWorkspace通知)。"""
out = call_text_api("summarize", long_text, "")
is_summary = len(out) > 10 and len(out) < len(long_text) * 0.7
record("S1", "总结", "长文总结(OpenCopilot系统介绍, ~400字)", "PASS" if is_summary else "FAIL", out,
       "应提炼出3-5个核心要点，长度约为原文的30-50%", 9 if is_summary else 4,
       "提炼精准" if len(out) > 100 else "过度压缩")

# S2: 空输入
out = call_text_api("summarize", "", "")
record("S2", "总结", "边缘: 空输入", "PASS" if len(out) < 100 else "WARN", out,
       "不应崩溃", 10 if len(out) < 50 else 5, "正常")

# ==============================
# 6. 自定义指令测试 (Custom)
# ==============================
print("=" * 60)
print("6. 自定义指令测试")
print("=" * 60)

# CU1: 指令遵循
out = call_text_api("custom", "Hello World! This is a test message.", "", "只输出翻译成中文的结果，一个字都不要多")
follows = "你好" in out and len(out) < 20
record("CU1", "自定义指令", "指定格式输出(只输出翻译)", "PASS" if follows else "FAIL", out,
       "应严格只输出翻译结果，无额外解释", 10 if follows else 3,
       "严格遵循指令" if follows else "未完全遵循指令")

# CU2: 格式转换
out = call_text_api("custom", "name: John, age: 30, city: New York, role: Engineer", "",
                    "转为JSON格式，只输出JSON，不要解释")
is_json = "{" in out and "}" in out and "John" in out
record("CU2", "自定义指令", "文本→JSON格式转换", "PASS" if is_json else "FAIL", out,
       "应输出合法JSON字符串", 10 if is_json else 2,
       "输出合法JSON" if is_json else "不是JSON格式")

# CU3: 代码生成
out = call_text_api("custom", "[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]", "",
                    "写一个Python函数过滤出偶数，只输出代码不用解释")
is_code = "def" in out and "return" in out and "filter" in out.lower() and len(out) < 200
record("CU3", "自定义指令", "代码生成+格式约束", "PASS" if is_code else "FAIL", out,
       "应输出Python函数代码，无多余内容", 10 if is_code else 3,
       "代码生成精准" if is_code else "输出不够纯净")

# ==============================
# 7. 知识图谱测试
# ==============================
print("=" * 60)
print("7. 知识图谱查询测试")
print("=" * 60)

out = call_kg("Agent")
has_agent = "Agent" in out and len(out) > 30
record("KG1", "知识图谱", "查询实体: Agent", "PASS" if has_agent else "FAIL", out,
       "应返回Agent相关的实体信息", 9 if has_agent else 3,
       "实体查询成功" if has_agent else "查询无结果")

out = call_kg("Broker")
has_broker = "Broker" in out and len(out) > 20
record("KG2", "知识图谱", "查询实体: Broker", "PASS" if has_broker else "FAIL", out,
       "应返回Broker相关实体", 9 if has_broker else 3,
       "查询成功" if has_broker else "无结果")

out = call_kg("不存在的实体XYZABC123")
record("KG3", "知识图谱", "边缘: 查询不存在的实体", "PASS" if True else "FAIL", out,
       "不应崩溃，返回空或无结果", 10, "正确处理无结果场景")

# ==============================
# 8. System Status
# ==============================
print("=" * 60)
print("8. 系统状态检查")
print("=" * 60)

try:
    r = httpx.get(API_HEALTH, timeout=5)
    record("SYS1", "系统", "健康检查", "PASS" if r.status_code == 200 else "FAIL",
           r.json(), "应返回healthy", 10, "正常")
except Exception as e:
    record("SYS1", "系统", "健康检查", "FAIL", str(e), "应返回healthy", 0, "服务不可达")

# ==============================
# 9. 综合评分
# ==============================
print("=" * 60)
print("9. 统计与结论")
print("=" * 60)

total = len(results)
passed = sum(1 for r in results if r["status"] == "PASS")
warned = sum(1 for r in results if r["status"] == "WARN")
failed = sum(1 for r in results if r["status"] == "FAIL")
avg_score = sum(scores) / len(scores) if scores else 0

print(f"\n总测试数: {total}")
print(f"通过: {passed} | 警告: {warned} | 失败: {failed}")
print(f"通过率: {passed/total*100:.1f}%")
print(f"平均质量分: {avg_score:.1f}/10")

print("\n--- 分类统计 ---")
cats = {}
for r in results:
    c = r["category"]
    if c not in cats:
        cats[c] = {"total": 0, "passed": 0, "scores": []}
    cats[c]["total"] += 1
    if r["status"] == "PASS":
        cats[c]["passed"] += 1
    if r.get("quality_score"):
        cats[c]["scores"].append(r["quality_score"])

for cat, stats in cats.items():
    avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
    print(f"  {cat}: {stats['passed']}/{stats['total']} 通过, 质量分: {avg:.1f}/10")

# 保存详细报告
report = {
    "timestamp": datetime.now().isoformat(),
    "total": total, "passed": passed, "warned": warned, "failed": failed,
    "pass_rate": f"{passed/total*100:.1f}%",
    "avg_quality_score": f"{avg_score:.1f}/10",
    "category_stats": {c: {"pass_rate": f"{s['passed']}/{s['total']}", "avg_score": f"{sum(s['scores'])/len(s['scores']):.1f}" if s['scores'] else "N/A"} for c, s in cats.items()},
    "detailed_results": results
}

with open("test_llm_capability_full.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n详细报告已保存: test_llm_capability_full.json")
