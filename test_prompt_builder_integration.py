"""
统一 Prompt 构建服务 - 集成功能验证测试

测试内容：
1. 原子功能（纯逻辑验证）
2. 复合功能（通过 Agent API 真实 LLM 验证）
3. 多领域覆盖：代码、翻译、PPT、内容分析、对话
"""

import sys
import os
import json
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompt_builder import (
    CONTEXT_DESCRIPTIONS,
    CONTEXT_SOURCE_PRIORITY,
    PERSONA_CONFLICT_PATTERNS,
    build_context_prefix,
    sanitize_persona_for_context,
    load_persona,
    build_full_prompt,
    build_system_messages,
)

AGENT_URL = "http://127.0.0.1:18888"
TEST_SESSION_PREFIX = "test_pb_integration"

# ==========================================
# 测试结果收集
# ==========================================

results = {"atomic": [], "composite": [], "summary": {}}


def log_test(category, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results[category].append({"name": name, "passed": passed, "detail": detail})
    icon = "✓" if passed else "✗"
    print(f"  [{status}] {icon} {name}" + (f" — {detail}" if detail else ""))


# ==========================================
# Part 1: 原子功能测试
# ==========================================

def test_atomic_functions():
    print("\n" + "=" * 60)
    print("Part 1: 原子功能测试（纯逻辑验证）")
    print("=" * 60)

    # 1.1 load_persona 测试
    print("\n--- 1.1 load_persona ---")

    for name in ["default", "code", "translate", "polish", "revision"]:
        content = load_persona(name)
        passed = isinstance(content, str) and len(content) > 10
        log_test("atomic", f"load_persona('{name}')", passed,
                 f"长度={len(content)}, 前30字={content[:30]}...")

    # 回退测试：不存在的 persona 应回退到 default
    fallback = load_persona("nonexistent_xyz")
    passed = isinstance(fallback, str) and len(fallback) > 10
    log_test("atomic", "load_persona('nonexistent_xyz') 回退到 default", passed,
             f"长度={len(fallback)}")

    # 1.2 build_context_prefix 测试
    print("\n--- 1.2 build_context_prefix ---")

    for source in CONTEXT_DESCRIPTIONS:
        prefix = build_context_prefix(source)
        passed = isinstance(prefix, str) and len(prefix) > 20
        log_test("atomic", f"build_context_prefix('{source}')", passed,
                 f"长度={len(prefix)}")

    # 带 meta 的测试
    meta = {"file_name": "test.py", "language": "python"}
    prefix = build_context_prefix("ide", meta)
    passed = "test.py" in prefix and "python" in prefix
    log_test("atomic", "build_context_prefix('ide', meta) 含文件信息", passed)

    # 浏览器带 app_name
    meta2 = {"app_name": "Google Chrome"}
    prefix2 = build_context_prefix("browser", meta2)
    passed = "Google Chrome" in prefix2
    log_test("atomic", "build_context_prefix('browser', app_name) 含浏览器名", passed)

    # 1.3 sanitize_persona_for_context 测试
    print("\n--- 1.3 sanitize_persona_for_context ---")

    # 低优先级 context_source 不应修改 persona
    persona_with_translate = "你是一个翻译助手，擅长翻译为中文，深度解析文本。"
    sanitized_low = sanitize_persona_for_context(persona_with_translate, "chat")
    passed = sanitized_low == persona_with_translate
    log_test("atomic", "低优先级('chat')不修改 persona", passed)

    # 高优先级 context_source 应添加优先级说明
    sanitized_high = sanitize_persona_for_context(persona_with_translate, "ide")
    passed = "【重要】" in sanitized_high and "ide" in sanitized_high
    log_test("atomic", "高优先级('ide')添加冲突说明", passed,
             f"末尾内容: ...{sanitized_high[-50:]}")

    # 无冲突模式时不添加说明
    clean_persona = "你是一个通用助手。"
    sanitized_clean = sanitize_persona_for_context(clean_persona, "ide")
    passed = "【重要】" not in sanitized_clean
    log_test("atomic", "无冲突模式时不做修改", passed)

    # 1.4 build_full_prompt 测试
    print("\n--- 1.4 build_full_prompt ---")

    prompt = build_full_prompt(
        action_type="chat",
        context_source="ide",
        context_content="请解释这段代码",
        context_meta={"file_name": "main.py", "language": "python"},
    )
    passed = all(k in prompt for k in ["main.py", "python", "请解释这段代码"])
    log_test("atomic", "build_full_prompt 包含所有关键元素", passed)

    # 验证 build_system_messages
    messages = build_system_messages(
        action_type="chat",
        context_source="ppt_editor",
        context_content="修改标题",
    )
    passed = isinstance(messages, list) and len(messages) == 1 and messages[0]["role"] == "system"
    log_test("atomic", "build_system_messages 返回格式正确", passed)

    # 1.5 CONTEXT_SOURCE_PRIORITY 测试
    print("\n--- 1.5 优先级配置完整性 ---")

    expected_high = {"ide", "revision", "ppt_generator", "ppt_editor"}
    actual_high = {k for k, v in CONTEXT_SOURCE_PRIORITY.items() if v == "high"}
    passed = expected_high == actual_high
    log_test("atomic", "高优先级 source 完整", passed,
             f"期望={expected_high}, 实际={actual_high}")

    # 1.6 冲突模式覆盖性测试
    print("\n--- 1.6 PERSONA_CONFLICT_PATTERNS ---")

    for source in ["ide", "revision", "ppt_generator", "ppt_editor"]:
        patterns = PERSONA_CONFLICT_PATTERNS.get(source, [])
        passed = len(patterns) > 0
        log_test("atomic", f"PERSONA_CONFLICT_PATTERNS['{source}'] 非空", passed,
                 f"模式数={len(patterns)}")


# ==========================================
# Part 2: 复合功能测试（真实 LLM 调用）
# ==========================================

def call_agent_api(payload, timeout=120):
    """调用 Agent API 并返回完整响应"""
    import urllib.request
    import urllib.error

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{AGENT_URL}/v1/agent/chat",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)

        full_text = ""
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data_json = json.loads(data_str)
                    chunk = data_json.get("chunk", "")
                    full_text += chunk
                except json.JSONDecodeError:
                    pass
        return full_text, None
    except urllib.error.URLError as e:
        return None, f"连接失败: {e.reason}"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)}"


def test_composite_functions():
    print("\n" + "=" * 60)
    print("Part 2: 复合功能测试（真实 LLM 验证）")
    print("=" * 60)

    # 2.1 代码编辑上下文（IDE）
    print("\n--- 2.1 IDE 代码编辑场景 ---")

    code_snippet = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

    payload = {
        "text": f"[selection]\n{code_snippet}\n\n请优化这段代码的性能",
        "context_source": "ide",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_ide_code",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 50
    log_test("composite", "IDE 代码优化请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        # 验证响应包含代码相关内容
        has_code = any(kw in resp.lower() for kw in ["fibonacci", "递归", "动态", "memo", "cache", "优化"])
        log_test("composite", "IDE 响应包含代码相关内容", has_code)

    # 2.2 PPT 编辑上下文
    print("\n--- 2.2 PPT 编辑场景 ---")

    slides_data = [
        {"type": "title", "title": "OpenCopilot", "subtitle": "AI 助手平台"},
        {"type": "content", "title": "核心功能", "layout": "text_only",
         "items": [{"level": 0, "text": "智能对话"}, {"level": 0, "text": "代码辅助"}]}
    ]

    payload = {
        "text": json.dumps({"slides": slides_data}, ensure_ascii=False) + "\n\n请把第2页的标题改为'核心优势'",
        "context_source": "ppt_editor",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_ppt_edit",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 20
    log_test("composite", "PPT 编辑修改标题请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        has_json = "action" in resp or "update" in resp or "核心优势" in resp
        log_test("composite", "PPT 响应包含修改指令或相关内容", has_json)

    # 2.3 翻译上下文（带 persona 冲突清理）
    print("\n--- 2.3 翻译场景（persona 冲突清理）---")

    payload = {
        "text": "The unified prompt building service ensures consistency across all modules.",
        "context_source": "chat",
        "action_type": "translate",
        "session_id": f"{TEST_SESSION_PREFIX}_translate",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 10
    log_test("composite", "翻译请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in resp)
        log_test("composite", "翻译响应包含中文", has_chinese)

    # 2.4 浏览器上下文（网页内容分析）
    print("\n--- 2.4 浏览器场景 ---")

    payload = {
        "text": "Python is a high-level programming language known for its readability and versatility.",
        "context_source": "browser",
        "action_type": "chat",
        "context_meta": {"app_name": "Google Chrome"},
        "session_id": f"{TEST_SESSION_PREFIX}_browser",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 30
    log_test("composite", "浏览器网页内容分析请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")

    # 2.5 代码审查场景
    print("\n--- 2.5 代码审查场景 ---")

    buggy_code = """import json

def load_config(path):
    with open(path) as f:
        config = json.load(f)
    return config["database"]["host"]

result = load_config("config.json")
print(result)"""

    payload = {
        "text": f"[selection]\n{buggy_code}\n\n请审查这段代码的安全性和健壮性",
        "context_source": "ide",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_code_review",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 80
    log_test("composite", "IDE 代码审查请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        review_keywords = ["异常", "try", "except", "error", "安全", "文件", "存在", "健壮"]
        has_review = any(kw in resp for kw in review_keywords)
        log_test("composite", "代码审查响应包含审查相关内容", has_review)

    # 2.6 多轮对话连续性
    print("\n--- 2.6 多轮对话连续性 ---")

    session_id = f"{TEST_SESSION_PREFIX}_multi_turn"

    # 第一轮
    payload1 = {
        "text": "我正在开发一个Python项目，需要实现一个缓存系统",
        "context_source": "chat",
        "action_type": "chat",
        "session_id": session_id,
    }
    resp1, err1 = call_agent_api(payload1)
    passed1 = resp1 is not None and len(resp1) > 30
    log_test("composite", "多轮对话-第1轮", passed1, f"响应长度={len(resp1) if resp1 else 0}")

    # 第二轮（应该有上下文连续性）
    payload2 = {
        "text": "请用 LRU 策略实现这个缓存",
        "context_source": "chat",
        "action_type": "chat",
        "session_id": session_id,
    }
    resp2, err2 = call_agent_api(payload2)
    passed2 = resp2 is not None and len(resp2) > 50
    log_test("composite", "多轮对话-第2轮(LRU缓存)", passed2,
             f"响应长度={len(resp2) if resp2 else 0}")
    if resp2:
        has_lru = any(kw in resp2.lower() for kw in ["lru", "cache", "缓存", "淘汰", "dict"])
        log_test("composite", "第2轮响应包含LRU相关实现", has_lru)

    # 2.7 PPT 生成场景
    print("\n--- 2.7 PPT 生成场景 ---")

    payload = {
        "text": "请根据以下内容生成PPT大纲：\n\n人工智能正在改变各行各业。从医疗诊断到自动驾驶，从金融风控到智能制造，AI技术已经渗透到生活的方方面面。本次演示将介绍AI的核心技术、应用场景和未来发展趋势。",
        "context_source": "ppt_generator",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_ppt_gen",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 50
    log_test("composite", "PPT 生成请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        has_json_structure = "[" in resp and ("title" in resp or "type" in resp)
        log_test("composite", "PPT 生成响应包含 JSON 结构", has_json_structure)

    # 2.8 通用对话
    print("\n--- 2.8 通用对话场景 ---")

    payload = {
        "text": "什么是微服务架构？请用简洁的语言解释",
        "context_source": "chat",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_general",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 50
    log_test("composite", "通用对话请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")
    if resp:
        has_arch_keywords = any(kw in resp for kw in ["微服务", "服务", "独立", "部署", "架构"])
        log_test("composite", "通用对话响应包含相关内容", has_arch_keywords)

    # 2.9 修订模式
    print("\n--- 2.9 修订模式场景 ---")

    payload = {
        "text": "[selection]\n我们的产品非常好用\n\n[content]\n这是一份产品介绍文档。我们的产品非常好用，它具有强大的功能。用户反馈表明我们的产品非常好用。",
        "context_source": "revision",
        "action_type": "chat",
        "session_id": f"{TEST_SESSION_PREFIX}_revision",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 20
    log_test("composite", "修订模式请求", passed,
             f"响应长度={len(resp) if resp else 0}, 错误={err}")

    # 2.10 Python 代码解释（跨领域）
    print("\n--- 2.10 Python 代码解释 ---")

    code = """class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance"""

    payload = {
        "text": f"[selection]\n{code}\n\n请解释这个设计模式",
        "context_source": "ide",
        "action_type": "chat",
        "context_meta": {"file_name": "singleton.py", "language": "python"},
        "session_id": f"{TEST_SESSION_PREFIX}_explain_pattern",
    }
    resp, err = call_agent_api(payload)
    passed = resp is not None and len(resp) > 50
    log_test("composite", "设计模式解释请求", passed,
             f"响应长度={len(resp) if resp else 0}")
    if resp:
        has_pattern = any(kw in resp for kw in ["单例", "singleton", "模式", "唯一", "实例"])
        log_test("composite", "响应包含设计模式相关内容", has_pattern)


# ==========================================
# Part 3: 边界条件与健壮性测试
# ==========================================

def test_edge_cases():
    print("\n" + "=" * 60)
    print("Part 3: 边界条件测试")
    print("=" * 60)

    # 3.1 空内容处理
    print("\n--- 3.1 空内容处理 ---")

    prefix = build_context_prefix("ide", {})
    passed = isinstance(prefix, str)
    log_test("atomic", "空 meta 不报错", passed)

    prefix_none = build_context_prefix("unknown_source")
    passed = isinstance(prefix_none, str)
    log_test("atomic", "未知 context_source 不报错", passed)

    # 3.2 长文本截断
    print("\n--- 3.2 长文本处理 ---")

    long_text = "这是一段很长的文本。" * 5000
    prompt = build_full_prompt(
        action_type="chat",
        context_source="ide",
        context_content=long_text,
    )
    passed = isinstance(prompt, str) and len(prompt) > 1000
    log_test("atomic", "长文本构建 prompt 不报错", passed,
             f"prompt 总长度={len(prompt)}")

    # 3.3 特殊字符处理
    print("\n--- 3.3 特殊字符处理 ---")

    special_text = '代码包含 "引号"、<标签>、{花括号}、[方括号]、\\n换行\\t制表符'
    prompt = build_full_prompt(
        action_type="chat",
        context_source="ide",
        context_content=special_text,
    )
    passed = isinstance(prompt, str) and "引号" in prompt
    log_test("atomic", "特殊字符不破坏 prompt 构建", passed)

    # 3.4 Agent API 健康检查
    print("\n--- 3.4 Agent API 健康检查 ---")

    try:
        resp = requests.get(f"{AGENT_URL}/health", timeout=5)
        passed = resp.status_code == 200
        data = resp.json() if passed else {}
        log_test("composite", "Agent 健康检查", passed,
                 f"状态={data.get('status')}, 会话数={data.get('active_sessions')}")
    except Exception as e:
        log_test("composite", "Agent 健康检查", False, str(e))


# ==========================================
# 主函数
# ==========================================

def print_summary():
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_tests = results["atomic"] + results["composite"]
    total = len(all_tests)
    passed = sum(1 for t in all_tests if t["passed"])
    failed = total - passed

    atomic_total = len(results["atomic"])
    atomic_passed = sum(1 for t in results["atomic"] if t["passed"])
    composite_total = len(results["composite"])
    composite_passed = sum(1 for t in results["composite"] if t["passed"])

    print(f"\n总计: {total} 项测试")
    print(f"  通过: {passed} / {total} ({passed/total*100:.1f}%)")
    print(f"  失败: {failed} / {total}")
    print(f"\n  原子功能: {atomic_passed}/{atomic_total} 通过")
    print(f"  复合功能: {composite_passed}/{composite_total} 通过")

    if failed > 0:
        print(f"\n失败项:")
        for t in all_tests:
            if not t["passed"]:
                print(f"  - {t['name']}: {t['detail']}")

    results["summary"] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "atomic": {"total": atomic_total, "passed": atomic_passed},
        "composite": {"total": composite_total, "passed": composite_passed},
    }

    # 保存结果到文件
    with open("prompt_builder_test_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存到: prompt_builder_test_report.json")


if __name__ == "__main__":
    print("=" * 60)
    print("统一 Prompt 构建服务 - 集成功能验证")
    print("=" * 60)

    test_atomic_functions()
    test_composite_functions()
    test_edge_cases()
    print_summary()
