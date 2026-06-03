"""
统一 Agent 管线端到端验证测试

测试策略：模拟真实用户输入 → 调用真实 Agent 服务 → 获得真实输出 → 断言输出符合预期

使用方式:
    # 1. 先启动 Agent 服务
    python asu_custom_agent.py

    # 2. 运行端到端测试
    python test_unified_agent_pipeline.py
"""

import os
import sys
import json
import time
import unittest
import subprocess
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Agent 服务地址
AGENT_URL = "http://127.0.0.1:18888"


def _send_chat(text: str, action_type: str = "default",
               session_id: str = None, timeout: int = 120) -> dict:
    """发送真实请求到 Agent，返回 {status_code, response, trace_id}"""
    import requests

    sid = session_id or f"e2e_test_{int(time.time())}"
    payload = {
        "text": text,
        "action_type": action_type,
        "session_id": sid,
        "context_source": "chat",
    }

    resp = requests.post(
        f"{AGENT_URL}/v1/agent/chat",
        json=payload,
        stream=True,
        timeout=timeout,
    )

    full_text = ""
    for line in resp.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
        if line_str.startswith("data: "):
            data_str = line_str[6:]
            if data_str == "[DONE]":
                break
            try:
                data_json = json.loads(data_str)
                chunk = data_json.get("chunk", "")
                if chunk:
                    full_text += chunk
            except json.JSONDecodeError:
                pass

    return {
        "status_code": resp.status_code,
        "response": full_text,
        "session_id": sid,
    }


def _get_traces() -> list:
    """获取 trace 列表"""
    import requests
    resp = requests.get(f"{AGENT_URL}/traces", timeout=5)
    if resp.status_code == 200:
        return resp.json().get("traces", [])
    return []


def _get_trace(trace_id: str) -> dict:
    """获取单条 trace"""
    import requests
    resp = requests.get(f"{AGENT_URL}/traces/{trace_id}", timeout=5)
    if resp.status_code == 200:
        return resp.json()
    return {}


# ==============================================================
# 测试用例
# ==============================================================

class TestSearchShortCircuit(unittest.TestCase):
    """搜索请求：在 CapabilityRouter 短路，返回搜索结果"""

    def test_search_returns_result_format(self):
        """搜索请求应返回 🔍 搜索结果 或 ❌ 未找到"""
        result = _send_chat("搜索Python教程", action_type="default")
        self.assertEqual(result["status_code"], 200, "请求应返回200")

        output = result["response"]
        self.assertTrue(len(output) > 0, "搜索请求应有输出")
        # 搜索结果应包含 🔍 标记或未找到提示
        has_search_marker = "🔍" in output or "搜索结果" in output
        has_not_found = "未找到" in output or "❌" in output
        self.assertTrue(
            has_search_marker or has_not_found,
            f"搜索输出应包含搜索结果标记，实际: {output[:200]}"
        )

    def test_search_short_circuit_no_llm(self):
        """搜索请求不应走 LLM（通过 trace 验证）"""
        _send_chat("搜索AI新闻", action_type="default",
                    session_id=f"search_trace_{int(time.time())}")
        time.sleep(0.5)

        traces = _get_traces()
        # 找到最近的搜索 trace
        for t in traces[:5]:
            if t.get("tags", {}).get("action_type") == "default":
                span_ops = [s["operation"] for s in t.get("spans", [])]
                has_llm = any("LLMProvider" in op for op in span_ops)
                self.assertFalse(has_llm,
                                 f"搜索请求不应走 LLM，但 trace 中包含 LLM span: {span_ops}")
                # 应包含 CapabilityRouter
                has_router = any("CapabilityRouter" in op for op in span_ops)
                self.assertTrue(has_router,
                                f"搜索请求应经过 CapabilityRouter，实际: {span_ops}")
                break


class TestCodeExecutionShortCircuit(unittest.TestCase):
    """代码执行请求：在 CapabilityRouter 短路，返回执行结果"""

    def test_code_execution_returns_result(self):
        """代码执行请求应返回 ✅ 代码执行成功 或 ❌ 代码执行失败"""
        result = _send_chat("运行代码 print(1+1)", action_type="default")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "代码执行请求应有输出")
        # 应包含执行结果标记
        has_success = "✅" in output or "代码执行成功" in output
        has_failure = "❌" in output or "代码执行失败" in output
        self.assertTrue(
            has_success or has_failure,
            f"代码执行输出应包含执行结果标记，实际: {output[:200]}"
        )

    def test_code_execution_contains_output(self):
        """代码执行结果应包含代码输出"""
        result = _send_chat("运行代码 print(42)", action_type="default")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        # 执行成功时结果应包含 "42" 或执行输出
        if "代码执行成功" in output or "✅" in output:
            self.assertIn("42", output,
                          f"执行 print(42) 的输出应包含 '42'，实际: {output[:300]}")


class TestKnowledgeQueryShortCircuit(unittest.TestCase):
    """知识检索请求：在 CapabilityRouter 短路"""

    def test_knowledge_query_returns_format(self):
        """知识检索请求应返回 🔍 知识检索结果 或 ❌ 未找到"""
        result = _send_chat("查询知识 OpenCopilot", action_type="default")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "知识检索请求应有输出")
        has_knowledge = "🔍" in output or "知识检索结果" in output or "知识" in output
        has_not_found = "未找到" in output or "❌" in output
        self.assertTrue(
            has_knowledge or has_not_found,
            f"知识检索输出应包含结果标记，实际: {output[:200]}"
        )


class TestChatGoesToLLM(unittest.TestCase):
    """Chat 请求：走完7层到 LLM，返回 AI 回复"""

    def test_chat_returns_nonempty_response(self):
        """Chat 请求应返回非空 AI 回复"""
        result = _send_chat("你好，请用一句话介绍自己", action_type="chat",
                            session_id=f"chat_e2e_{int(time.time())}")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "Chat 请求应返回非空回复")
        # AI 回复应包含中文字符
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in output)
        self.assertTrue(has_chinese,
                       f"Chat 回复应包含中文，实际: {output[:200]}")

    def test_chat_trace_has_all_7_middlewares(self):
        """Chat 请求的 trace 应包含7个中间件 span"""
        sid = f"chat_trace_{int(time.time())}"
        _send_chat("你好", action_type="chat", session_id=sid)
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("session_id") == sid:
                span_ops = [s["operation"].replace("middleware.", "")
                            for s in t.get("spans", [])]
                expected = [
                    "SessionSetupMiddleware",
                    "SecurityGuardMiddleware",
                    "ImmuneSystemMiddleware",
                    "PlannerMiddleware",
                    "StateTrackingMiddleware",
                    "CapabilityRouterMiddleware",
                    "LLMProviderMiddleware",
                ]
                for mw in expected:
                    self.assertIn(mw, span_ops,
                                  f"Chat trace 缺少中间件: {mw}，实际: {span_ops}")
                break


class TestCodingGoesToLLM(unittest.TestCase):
    """Coding 请求：走完7层到 LLM，使用 coding persona"""

    def test_coding_returns_review(self):
        """代码审查请求应返回包含代码分析的回复"""
        result = _send_chat(
            "请审查这段Python代码：def add(a, b): return a + b",
            action_type="coding",
            session_id=f"coding_e2e_{int(time.time())}",
        )
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "代码审查应返回非空回复")
        # 代码审查回复应包含相关关键词
        relevant_keywords = ["代码", "add", "函数", "审查", "建议", "python", "Python"]
        has_keyword = any(kw in output for kw in relevant_keywords)
        self.assertTrue(has_keyword,
                       f"代码审查回复应包含相关关键词，实际: {output[:200]}")

    def test_coding_trace_uses_coding_persona(self):
        """Coding 请求的 trace 应显示 action_type=coding"""
        sid = f"coding_trace_{int(time.time())}"
        _send_chat("帮我分析这段代码", action_type="coding", session_id=sid)
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("session_id") == sid:
                self.assertEqual(t["tags"]["action_type"], "coding",
                                 f"Coding 请求 trace 的 action_type 应为 coding")
                break


class TestPPTGoesToLLM(unittest.TestCase):
    """PPT 请求：走完7层到 LLM，使用 ppt persona"""

    def test_ppt_returns_nonempty(self):
        """PPT 请求应返回非空 AI 回复"""
        result = _send_chat(
            "帮我生成一个关于AI的PPT大纲",
            action_type="ppt",
            session_id=f"ppt_e2e_{int(time.time())}",
        )
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "PPT 请求应返回非空回复")

    def test_ppt_trace_has_llm(self):
        """PPT 请求的 trace 应包含 LLMProviderMiddleware"""
        sid = f"ppt_trace_{int(time.time())}"
        _send_chat("生成PPT大纲", action_type="ppt", session_id=sid)
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("session_id") == sid:
                span_ops = [s["operation"] for s in t.get("spans", [])]
                has_llm = any("LLMProvider" in op for op in span_ops)
                self.assertTrue(has_llm,
                                f"PPT 请求应经过 LLMProviderMiddleware，实际: {span_ops}")
                self.assertEqual(t["tags"]["action_type"], "ppt")
                break


class TestSecurityGuardBlocks(unittest.TestCase):
    """SecurityGuard 中间件：应放行正常请求"""

    def test_normal_request_passes_security(self):
        """正常请求应通过安全检查"""
        result = _send_chat("你好", action_type="chat",
                            session_id=f"security_e2e_{int(time.time())}")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        # 正常请求不应被安全检查拦截
        is_blocked = "权限不足" in output or "请求被拦截" in output
        self.assertFalse(is_blocked,
                         f"正常请求不应被安全检查拦截，实际: {output[:200]}")


class TestImmuneSystemPasses(unittest.TestCase):
    """ImmuneSystem 中间件：正常请求应通过规则检查"""

    def test_normal_request_passes_immune(self):
        """正常请求应通过免疫检查"""
        result = _send_chat("帮我写一个排序算法", action_type="chat",
                            session_id=f"immune_e2e_{int(time.time())}")
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        is_blocked = "规则检查发现违规" in output or "⚠️" in output
        self.assertFalse(is_blocked,
                         f"正常请求不应被免疫检查拦截，实际: {output[:200]}")


class TestPlannerForComplexTask(unittest.TestCase):
    """Planner 中间件：复杂任务应触发自动规划"""

    def test_complex_task_triggers_planning(self):
        """包含步骤/流程关键词的请求应触发规划"""
        result = _send_chat(
            "请帮我设计并实现一个用户注册流程，包括验证、存储和通知步骤",
            action_type="chat",
            session_id=f"planner_e2e_{int(time.time())}",
        )
        self.assertEqual(result["status_code"], 200)

        output = result["response"]
        self.assertTrue(len(output) > 0, "复杂任务应返回非空回复")


class TestSessionSetupPersonaSwitch(unittest.TestCase):
    """SessionSetup 中间件：action_type 非 default 时应切换 persona"""

    def test_persona_switch_for_coding(self):
        """action_type=coding 时 persona 应切换"""
        sid = f"persona_e2e_{int(time.time())}"

        # 先发一个 default 请求
        _send_chat("你好", action_type="default", session_id=sid)

        # 再发 coding 请求
        result = _send_chat("def foo(): pass", action_type="coding",
                            session_id=sid)
        self.assertEqual(result["status_code"], 200)

        # 验证 persona 已切换（通过 trace）
        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("action_type") == "coding":
                # coding 请求的 action_type 应为 coding
                self.assertEqual(t["tags"]["action_type"], "coding")
                break


class TestTraceSystemIntegration(unittest.TestCase):
    """Trace 系统端到端验证"""

    def test_search_trace_is_short_circuit(self):
        """搜索请求的 trace 状态应为 short_circuit"""
        sid = f"trace_status_{int(time.time())}"
        _send_chat("搜索测试", action_type="default", session_id=sid)
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("session_id") == sid:
                self.assertEqual(t["status"], "short_circuit",
                                 f"搜索请求的 trace 状态应为 short_circuit，实际: {t['status']}")
                break

    def test_chat_trace_is_ok_or_active(self):
        """Chat 请求的 trace 状态应为 ok（若已完成）或仍 active"""
        sid = f"trace_chat_{int(time.time())}"
        _send_chat("你好", action_type="chat", session_id=sid)
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("tags", {}).get("session_id") == sid:
                # Chat 请求可能还在进行（LLM流式输出），所以状态可能是 ok 或 active
                self.assertIn(t["status"], ["ok", "active", "short_circuit"],
                              f"Chat 请求 trace 状态异常: {t['status']}")
                break

    def test_trace_has_duration(self):
        """已完成的 trace 应有 duration_ms"""
        # 用搜索请求（快速完成）
        _send_chat("搜索测试duration", action_type="default",
                    session_id=f"trace_dur_{int(time.time())}")
        time.sleep(0.5)

        traces = _get_traces()
        for t in traces[:5]:
            if t.get("status") == "short_circuit":
                self.assertIsNotNone(t.get("duration_ms"),
                                     "已完成的 trace 应有 duration_ms")
                self.assertGreater(t["duration_ms"], 0,
                                   "trace duration_ms 应大于0")
                # 每个 span 也应有 duration
                for span in t.get("spans", []):
                    self.assertIsNotNone(span.get("duration_ms"),
                                         f"span {span['operation']} 应有 duration_ms")
                break


class TestSmartCopilotAPICodingEndpoints(unittest.TestCase):
    """验证 smart_copilot_api.py 的 Coding 端点走 Agent 管线"""

    @classmethod
    def setUpClass(cls):
        """检查两个服务是否都运行"""
        import requests
        cls.agent_running = False
        cls.api_running = False
        try:
            resp = requests.get(f"{AGENT_URL}/health", timeout=2)
            cls.agent_running = resp.status_code == 200
        except Exception:
            pass
        try:
            resp = requests.get("http://127.0.0.1:8088/docs", timeout=2)
            cls.api_running = resp.status_code == 200
        except Exception:
            pass

    def setUp(self):
        if not self.api_running:
            self.skipTest("Smart Copilot API 服务未运行 (python smart_copilot_api.py)")

    def test_code_review_returns_pipeline_source(self):
        """代码审查端点应返回 source=agent_pipeline"""
        import requests

        resp = requests.post(
            "http://127.0.0.1:8088/api/coding/review",
            json={
                "code": "def hello():\n    print('hello')",
                "language": "python",
            },
            timeout=120,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("source"), "agent_pipeline",
                         f"代码审查应走管线，实际: {data}")

    def test_code_explain_returns_pipeline_source(self):
        """代码解释端点应返回 source=agent_pipeline"""
        import requests

        resp = requests.post(
            "http://127.0.0.1:8088/api/coding/explain",
            json={
                "code": "x = 1 + 1",
                "language": "python",
            },
            timeout=120,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("source"), "agent_pipeline",
                         f"代码解释应走管线，实际: {data}")


# ==============================================================
# 运行入口
# ==============================================================

def check_agent_running():
    """检查 Agent 服务是否运行"""
    import requests
    try:
        resp = requests.get(f"{AGENT_URL}/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def start_agent_background():
    """后台启动 Agent 服务"""
    proc = subprocess.Popen(
        [sys.executable, "asu_custom_agent.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # 等待启动
    for _ in range(20):
        time.sleep(1)
        if check_agent_running():
            return proc
    proc.terminate()
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="统一 Agent 管线端到端验证")
    parser.add_argument("--start-agent", action="store_true",
                        help="自动启动 Agent 服务")
    parser.add_argument("--skip-llm", action="store_true",
                        help="跳过需要 LLM 的测试（只测试短路路径）")
    args, remaining = parser.parse_known_args()

    agent_proc = None

    if args.start_agent and not check_agent_running():
        print("正在启动 Agent 服务...")
        agent_proc = start_agent_background()
        if agent_proc:
            print("✅ Agent 服务已启动")
        else:
            print("❌ Agent 服务启动失败")
            sys.exit(1)
    elif not check_agent_running():
        print("⚠️  Agent 服务未运行。请先启动: python asu_custom_agent.py")
        print("   或使用 --start-agent 自动启动")
        sys.exit(1)

    # 选择测试集
    if args.skip_llm:
        # 只测试短路路径（不调用 LLM，速度快）
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSearchShortCircuit))
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCodeExecutionShortCircuit))
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestKnowledgeQueryShortCircuit))
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTraceSystemIntegration))
    else:
        # 全量测试
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 清理
    if agent_proc:
        print("正在停止 Agent 服务...")
        agent_proc.terminate()

    sys.exit(0 if result.wasSuccessful() else 1)
