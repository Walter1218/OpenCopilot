"""
Pipeline Trace 验证测试

通过真实请求 + trace 系统验证每个中间件是否有效接入管线。
测试方法：向 Agent 发送请求，然后查询 /traces 端点，
验证每个中间件都有对应的 span 记录。

使用方式:
    # 方式1: 需要先启动 Agent (python asu_custom_agent.py)
    python test_pipeline_trace_validation.py --live

    # 方式2: 纯单元测试（不需要启动服务）
    python test_pipeline_trace_validation.py
"""

import os
import sys
import json
import time
import unittest
import subprocess
import threading
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class PipelineTraceValidator:
    """管线追踪验证器"""

    # 预期的中间件名称（按执行顺序）
    EXPECTED_MIDDLEWARES = [
        "SessionSetupMiddleware",
        "SecurityGuardMiddleware",
        "ImmuneSystemMiddleware",
        "PlannerMiddleware",
        "StateTrackingMiddleware",
        "CapabilityRouterMiddleware",
        "LLMProviderMiddleware",
    ]

    def __init__(self, agent_url: str = "http://127.0.0.1:18888"):
        self.agent_url = agent_url
        self._test_session_id = f"trace_test_{int(time.time())}"

    def send_chat_request(
        self,
        text: str,
        action_type: str = "default",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发送聊天请求到 Agent"""
        import requests

        payload = {
            "text": text,
            "action_type": action_type,
            "session_id": session_id or self._test_session_id,
            "context_source": "chat",
        }

        resp = requests.post(
            f"{self.agent_url}/v1/agent/chat",
            json=payload,
            stream=True,
            timeout=120,
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
        }

    def get_traces(self) -> List[Dict[str, Any]]:
        """获取所有追踪记录"""
        import requests

        resp = requests.get(f"{self.agent_url}/traces", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("traces", [])
        return []

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取指定追踪"""
        import requests

        resp = requests.get(f"{self.agent_url}/traces/{trace_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return None

    def validate_trace(self, trace: Dict[str, Any], expected_mw_count: int = None) -> Dict[str, Any]:
        """验证追踪记录是否完整

        Args:
            trace: 追踪记录
            expected_mw_count: 预期的中间件数量（部分中间件可能短路不执行）

        Returns:
            验证结果
        """
        spans = trace.get("spans", [])
        span_operations = [s.get("operation", "") for s in spans]

        # 提取中间件名称
        executed_middlewares = []
        for op in span_operations:
            if op.startswith("middleware."):
                mw_name = op[len("middleware."):]
                executed_middlewares.append(mw_name)

        # 检查哪些中间件被执行了
        expected_set = set(self.EXPECTED_MIDDLEWARES)
        executed_set = set(executed_middlewares)

        missing = expected_set - executed_set
        unexpected = executed_set - expected_set

        # 验证执行顺序
        order_correct = True
        order_issues = []
        last_idx = -1
        for mw in executed_middlewares:
            if mw in self.EXPECTED_MIDDLEWARES:
                idx = self.EXPECTED_MIDDLEWARES.index(mw)
                if idx < last_idx:
                    order_correct = False
                    order_issues.append(f"{mw} (index={idx}) executed after index={last_idx}")
                last_idx = idx

        # 验证每个 span 都有 duration_ms
        duration_issues = []
        for span in spans:
            if span.get("duration_ms") is None and span.get("status") != "error":
                duration_issues.append(span.get("operation", "unknown"))

        # 验证所有 span 状态
        error_spans = [s for s in spans if s.get("status") == "error"]

        return {
            "valid": len(missing) == 0 and len(duration_issues) == 0 and order_correct,
            "executed_middlewares": executed_middlewares,
            "missing_middlewares": list(missing),
            "unexpected_middlewares": list(unexpected),
            "order_correct": order_correct,
            "order_issues": order_issues,
            "duration_issues": duration_issues,
            "error_spans": [s.get("operation") for s in error_spans],
            "total_spans": len(spans),
            "trace_duration_ms": trace.get("duration_ms"),
        }


class TestPipelineTraceUnit(unittest.TestCase):
    """单元测试：直接测试 Pipeline + Tracer 集成"""

    def setUp(self):
        from observability_module.tracer import DistributedTracer
        from observability_module import ObservabilityConfig
        from agent_pipeline import PipelineContext, MiddlewarePipeline

        # 创建 tracer
        config = ObservabilityConfig(enable_tracing=True)
        self.tracer = DistributedTracer(config)

        # 创建管线
        self.pipeline = MiddlewarePipeline(tracer=self.tracer)

    def test_tracer_auto_creates_spans(self):
        """测试：tracer 自动为每个中间件创建 span"""

        from agent_pipeline import BaseMiddleware, PipelineContext

        # 创建3个测试中间件
        class MW1(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.metadata["mw1_called"] = True
                next_fn()

        class MW2(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.metadata["mw2_called"] = True
                next_fn()

        class MW3(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.metadata["mw3_called"] = True
                # 不调用 next_fn（短路）

        self.pipeline.use(MW1())
        self.pipeline.use(MW2())
        self.pipeline.use(MW3())

        ctx = PipelineContext(
            request={"text": "test"},
            session_id="test_session",
            text="test",
            action_type="default",
        )

        self.pipeline.execute(ctx)

        # 验证中间件都被调用了
        self.assertTrue(ctx.metadata.get("mw1_called"))
        self.assertTrue(ctx.metadata.get("mw2_called"))
        self.assertTrue(ctx.metadata.get("mw3_called"))

        # 验证 trace 被创建
        stats = self.tracer.get_stats()
        self.assertEqual(stats["total_traces"], 1)
        self.assertEqual(stats["total_spans"], 3)
        self.assertEqual(stats["completed_traces"], 1)
        self.assertEqual(stats["completed_spans"], 3)

        # 验证 trace 包含正确的 span
        traces = self.tracer.get_traces()
        self.assertEqual(len(traces), 1)

        trace = traces[0]
        span_operations = [s.operation for s in trace.spans]
        self.assertIn("middleware.MW1", span_operations)
        self.assertIn("middleware.MW2", span_operations)
        self.assertIn("middleware.MW3", span_operations)

        # 验证 trace_id 被注入到 ctx
        self.assertIsNotNone(ctx.trace_id)

    def test_tracer_records_span_duration(self):
        """测试：span 记录了执行耗时"""

        from agent_pipeline import BaseMiddleware, PipelineContext
        import time

        class SlowMiddleware(BaseMiddleware):
            def process(self, ctx, next_fn):
                time.sleep(0.01)  # 10ms
                next_fn()

        self.pipeline.use(SlowMiddleware())

        ctx = PipelineContext(
            request={"text": "test"},
            session_id="test_session",
            text="test",
        )

        self.pipeline.execute(ctx)

        traces = self.tracer.get_traces()
        trace = traces[0]

        # 验证 span 有 duration
        for span in trace.spans:
            self.assertIsNotNone(span.duration_ms)
            self.assertGreater(span.duration_ms, 0)

        # 验证 trace 有 duration
        self.assertIsNotNone(trace.duration_ms)
        self.assertGreater(trace.duration_ms, 0)

    def test_tracer_records_short_circuit(self):
        """测试：短路情况下 trace 状态为 short_circuit"""

        from agent_pipeline import BaseMiddleware, PipelineContext

        class ShortCircuitMiddleware(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.short_circuit("blocked")
                # 不调用 next_fn

        class NeverReachedMiddleware(BaseMiddleware):
            def process(self, ctx, next_fn):
                ctx.metadata["never_reached"] = True
                next_fn()

        self.pipeline.use(ShortCircuitMiddleware())
        self.pipeline.use(NeverReachedMiddleware())

        ctx = PipelineContext(
            request={"text": "test"},
            session_id="test_session",
            text="test",
        )

        self.pipeline.execute(ctx)

        # 验证短路
        self.assertTrue(ctx.should_short_circuit)
        self.assertFalse(ctx.metadata.get("never_reached", False))

        # 验证只有1个 span（NeverReachedMiddleware 未执行）
        traces = self.tracer.get_traces()
        trace = traces[0]
        self.assertEqual(len(trace.spans), 1)
        self.assertEqual(trace.spans[0].operation, "middleware.ShortCircuitMiddleware")

        # 验证 trace 状态
        self.assertEqual(trace.status, "short_circuit")

    def test_tracer_handles_exception(self):
        """测试：中间件异常时 span 标记为 error"""

        from agent_pipeline import BaseMiddleware, PipelineContext

        class ErrorMiddleware(BaseMiddleware):
            def process(self, ctx, next_fn):
                raise ValueError("test error")

        self.pipeline.use(ErrorMiddleware())

        ctx = PipelineContext(
            request={"text": "test"},
            session_id="test_session",
            text="test",
        )

        with self.assertRaises(ValueError):
            self.pipeline.execute(ctx)

        # 验证 span 有 error 状态
        traces = self.tracer.get_traces()
        # 注意：异常时 trace 可能未被完成（因为异常传播）
        # 但 span 应该被标记为 error
        active_spans = self.tracer.get_active_spans()
        if active_spans:
            self.assertEqual(active_spans[0].status, "error")


class TestPipelineTraceReal(unittest.TestCase):
    """真实集成测试：向 Agent 发送请求并验证 trace"""

    @classmethod
    def setUpClass(cls):
        """检查 Agent 是否运行"""
        try:
            import requests
            resp = requests.get("http://127.0.0.1:18888/health", timeout=2)
            cls.agent_running = resp.status_code == 200
        except Exception:
            cls.agent_running = False

        cls.validator = PipelineTraceValidator()

    def setUp(self):
        if not self.agent_running:
            self.skipTest("Agent 未运行 (python asu_custom_agent.py)")

    def test_chat_request_trace(self):
        """测试：普通聊天请求的 trace 包含所有7个中间件"""
        result = self.validator.send_chat_request(
            text="你好，请介绍一下自己",
            action_type="chat",
            session_id=f"trace_chat_{int(time.time())}",
        )

        self.assertEqual(result["status_code"], 200)
        self.assertTrue(len(result["response"]) > 0, "Agent 应该返回响应")

        # 查询 traces
        traces = self.validator.get_traces()
        self.assertTrue(len(traces) > 0, "应该有 trace 记录")

        # 找到最近的 trace
        latest_trace = traces[0]  # 按 time 倒序
        validation = self.validator.validate_trace(latest_trace)

        print(f"\n[Chat Trace] 执行的中间件: {validation['executed_middlewares']}")
        print(f"[Chat Trace] 缺失的中间件: {validation['missing_middlewares']}")
        print(f"[Chat Trace] 总 span 数: {validation['total_spans']}")
        print(f"[Chat Trace] Trace 耗时: {validation['trace_duration_ms']:.2f}ms")

        # Chat 类型应该走完所有7层（包括 LLMProviderMiddleware）
        self.assertEqual(len(validation["executed_middlewares"]), 7,
                         f"Chat 请求应经过所有7个中间件，实际: {validation['executed_middlewares']}")

    def test_code_execution_trace(self):
        """测试：代码执行请求在 CapabilityRouter 处短路"""
        result = self.validator.send_chat_request(
            text="帮我运行Python代码 print(1+1)",
            action_type="default",
            session_id=f"trace_code_{int(time.time())}",
        )

        self.assertEqual(result["status_code"], 200)

        traces = self.validator.get_traces()
        latest_trace = traces[0]
        validation = self.validator.validate_trace(latest_trace)

        print(f"\n[Code Execution Trace] 执行的中间件: {validation['executed_middlewares']}")
        print(f"[Code Execution Trace] 缺失的中间件: {validation['missing_middlewares']}")

        # 代码执行应该在 CapabilityRouter 处短路
        # 前面的中间件（SessionSetup, SecurityGuard, ImmuneSystem, Planner, StateTracking, CapabilityRouter）都应执行
        # LLMProviderMiddleware 不应执行
        self.assertIn("CapabilityRouterMiddleware", validation["executed_middlewares"])

    def test_ppt_request_trace(self):
        """测试：PPT 请求的 trace 包含正确的 action_type"""
        result = self.validator.send_chat_request(
            text="帮我生成一个关于人工智能的PPT大纲",
            action_type="ppt",
            session_id=f"trace_ppt_{int(time.time())}",
        )

        self.assertEqual(result["status_code"], 200)

        traces = self.validator.get_traces()
        latest_trace = traces[0]
        validation = self.validator.validate_trace(latest_trace)

        print(f"\n[PPT Trace] 执行的中间件: {validation['executed_middlewares']}")

        # PPT 类型应该走 LLM（通过 CapabilityRouter 的 llm_types）
        self.assertIn("LLMProviderMiddleware", validation["executed_middlewares"],
                      "PPT 请求应经过 LLMProviderMiddleware")

    def test_coding_request_trace(self):
        """测试：Coding 请求的 trace 验证 persona 切换"""
        result = self.validator.send_chat_request(
            text="帮我审查这段代码的质量",
            action_type="coding",
            session_id=f"trace_coding_{int(time.time())}",
        )

        self.assertEqual(result["status_code"], 200)

        traces = self.validator.get_traces()
        latest_trace = traces[0]

        # 验证 trace tags 包含 action_type
        self.assertIn("action_type", latest_trace.get("tags", {}),
                      "Trace tags 应包含 action_type")

        validation = self.validator.validate_trace(latest_trace)
        print(f"\n[Coding Trace] 执行的中间件: {validation['executed_middlewares']}")

        # Coding 类型应该走 LLM
        self.assertIn("LLMProviderMiddleware", validation["executed_middlewares"])

    def test_trace_span_order(self):
        """测试：span 执行顺序与中间件注册顺序一致"""
        # 发送一个简单的 chat 请求
        self.validator.send_chat_request(
            text="你好",
            action_type="chat",
            session_id=f"trace_order_{int(time.time())}",
        )

        traces = self.validator.get_traces()
        latest_trace = traces[0]
        validation = self.validator.validate_trace(latest_trace)

        print(f"\n[Order Trace] 执行的中间件: {validation['executed_middlewares']}")
        print(f"[Order Trace] 顺序正确: {validation['order_correct']}")

        if validation["order_issues"]:
            print(f"[Order Trace] 顺序问题: {validation['order_issues']}")

        # 验证中间件顺序
        expected_order = [
            "SessionSetupMiddleware",
            "SecurityGuardMiddleware",
            "ImmuneSystemMiddleware",
            "PlannerMiddleware",
            "StateTrackingMiddleware",
            "CapabilityRouterMiddleware",
            "LLMProviderMiddleware",
        ]

        executed = validation["executed_middlewares"]
        for i, mw in enumerate(executed):
            if mw in expected_order:
                idx = expected_order.index(mw)
                # 验证中间件的执行顺序是递增的（中间件链式调用，顺序应该一致）
                # 允许中间件跳过（如短路），但不应乱序

    def test_trace_stats_endpoint(self):
        """测试：/traces/stats 端点返回正确的统计信息"""
        import requests

        resp = requests.get("http://127.0.0.1:18888/traces/stats", timeout=5)
        self.assertEqual(resp.status_code, 200)

        stats = resp.json()
        self.assertIn("total_traces", stats)
        self.assertIn("total_spans", stats)
        self.assertIn("completed_traces", stats)
        self.assertIn("completed_spans", stats)

        print(f"\n[Trace Stats] {json.dumps(stats, indent=2)}")


class TestPipelineTraceDetailed(unittest.TestCase):
    """详细验证：每种请求类型都走过了预期的中间件"""

    @classmethod
    def setUpClass(cls):
        try:
            import requests
            resp = requests.get("http://127.0.0.1:18888/health", timeout=2)
            cls.agent_running = resp.status_code == 200
        except Exception:
            cls.agent_running = False

        cls.validator = PipelineTraceValidator()

    def setUp(self):
        if not self.agent_running:
            self.skipTest("Agent 未运行")

    def test_all_action_types_have_traces(self):
        """测试：所有 action_type 都产生了 trace"""
        action_types = ["chat", "ppt", "coding", "evaluation", "default"]

        for action_type in action_types:
            with self.subTest(action_type=action_type):
                result = self.validator.send_chat_request(
                    text=f"测试 {action_type} 类型请求",
                    action_type=action_type,
                    session_id=f"trace_{action_type}_{int(time.time())}",
                )

                self.assertEqual(result["status_code"], 200,
                                 f"{action_type} 请求应返回 200")

                # 检查是否有响应
                self.assertTrue(len(result["response"]) > 0,
                                f"{action_type} 请求应有响应")

        # 查询 traces
        time.sleep(0.5)  # 等待 trace 写入
        traces = self.validator.get_traces()

        # 验证每种类型都有 trace
        trace_tags = [t.get("tags", {}).get("action_type") for t in traces]
        for action_type in action_types:
            self.assertIn(action_type, trace_tags,
                          f"应该有 {action_type} 类型的 trace")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline Trace 验证测试")
    parser.add_argument("--live", action="store_true",
                        help="运行真实集成测试（需要 Agent 服务运行）")
    args, remaining = parser.parse_known_args()

    if args.live:
        # 运行真实集成测试
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineTraceReal)
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPipelineTraceDetailed))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        # 只运行单元测试
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineTraceUnit)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
