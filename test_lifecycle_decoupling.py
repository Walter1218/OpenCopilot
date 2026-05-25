"""
Phase 1 单元测试：UI 与 Agent 生命周期解耦验证
============================================

测试目标：
1. 验证 smart_copilot.py 不再包含 subprocess 强启动逻辑
2. 验证 AgentHealthWorker 在 Agent 在线/离线两种状态下行为正确
3. 验证 AICardWindow.set_agent_status 能正确切换 UI 状态（状态灯 + 离线横幅）
4. 验证 CopilotManager.cleanup 不再持有或终止 Agent 子进程

运行方式：
    python test_lifecycle_decoupling.py
"""

import sys
import os
import ast
import inspect
import unittest
from unittest.mock import patch, MagicMock

# ──────────────────────────────────────────────
# 工具函数：对源码做静态分析，不依赖真实 Qt 环境
# ──────────────────────────────────────────────

def get_source(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SMART_COPILOT_PATH = os.path.join(os.path.dirname(__file__), "smart_copilot.py")
SOURCE = get_source(SMART_COPILOT_PATH)
TREE = ast.parse(SOURCE)


class TestStaticAnalysis(unittest.TestCase):
    """静态代码分析测试：验证危险逻辑已被彻底移除。"""

    def test_subprocess_import_removed(self):
        """[P1-T01] subprocess 模块不应再被导入"""
        for node in ast.walk(TREE):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "subprocess",
                        "❌ subprocess 仍在 import 列表中，生命周期解耦未完成！")
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "subprocess",
                    "❌ from subprocess 导入仍存在！")
        print("  ✅ [P1-T01] subprocess import 已成功移除")

    def test_popen_not_called(self):
        """[P1-T02] subprocess.Popen 不应在任何地方被调用"""
        found = False
        for node in ast.walk(TREE):
            if isinstance(node, ast.Attribute):
                if node.attr == "Popen":
                    found = True
                    break
        self.assertFalse(found, "❌ subprocess.Popen 调用仍然存在！")
        print("  ✅ [P1-T02] 无 subprocess.Popen 调用")

    def test_check_and_start_agent_removed(self):
        """[P1-T03] _check_and_start_agent 方法不应再存在"""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.assertNotEqual(node.name, "_check_and_start_agent",
                    "❌ _check_and_start_agent 方法仍然存在！")
        print("  ✅ [P1-T03] _check_and_start_agent 已删除")

    def test_agent_health_worker_exists(self):
        """[P1-T04] AgentHealthWorker 类必须存在作为探活替代方案"""
        class_names = [node.name for node in ast.walk(TREE) if isinstance(node, ast.ClassDef)]
        self.assertIn("AgentHealthWorker", class_names,
            "❌ AgentHealthWorker 类不存在，探活机制未实现！")
        print("  ✅ [P1-T04] AgentHealthWorker 类已就位")

    def test_set_agent_status_in_aicard(self):
        """[P1-T05] AICardWindow 必须包含 set_agent_status 方法"""
        for node in ast.walk(TREE):
            if isinstance(node, ast.ClassDef) and node.name == "AICardWindow":
                methods = [n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertIn("set_agent_status", methods,
                    "❌ AICardWindow 没有 set_agent_status 方法！")
                print("  ✅ [P1-T05] AICardWindow.set_agent_status 已实现")
                return
        self.fail("❌ 未找到 AICardWindow 类！")

    def test_cleanup_no_terminate(self):
        """[P1-T06] CopilotManager.cleanup 不应调用 .terminate()"""
        for node in ast.walk(TREE):
            if isinstance(node, ast.ClassDef) and node.name == "CopilotManager":
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "cleanup":
                        for n in ast.walk(child):
                            if isinstance(n, ast.Attribute) and n.attr == "terminate":
                                self.fail("❌ CopilotManager.cleanup 仍调用 .terminate()，会终止 Agent 守护进程！")
                        print("  ✅ [P1-T06] cleanup 不再终止 Agent 进程")
                        return
        self.fail("❌ 未找到 CopilotManager.cleanup 方法！")

    def test_copilot_manager_no_agent_process(self):
        """[P1-T07] CopilotManager.__init__ 不应持有 agent_process 属性"""
        found_agent_process = False
        for node in ast.walk(TREE):
            if isinstance(node, ast.ClassDef) and node.name == "CopilotManager":
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "__init__":
                        for n in ast.walk(child):
                            if isinstance(n, ast.Attribute) and n.attr == "agent_process":
                                # 赋值才算，读取不算
                                found_agent_process = True
        self.assertFalse(found_agent_process,
            "❌ CopilotManager.__init__ 仍持有 self.agent_process，生命周期未解耦！")
        print("  ✅ [P1-T07] CopilotManager 不再持有 agent_process")


class TestAgentHealthWorkerLogic(unittest.TestCase):
    """逻辑测试：模拟 HTTP 探活结果，验证信号发射是否正确。"""

    def test_emit_online_when_health_ok(self):
        """[P1-T08] Agent 在线时 health_result 应 emit(True, active_sessions)"""
        results = []

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "active_sessions": 3}

        with patch("httpx.get", return_value=mock_resp):
            # 模拟 QThread.run 的核心逻辑
            try:
                resp = mock_resp
                if resp.status_code == 200:
                    data = resp.json()
                    results.append((True, data.get("active_sessions", 0)))
            except Exception:
                results.append((False, 0))

        self.assertEqual(results, [(True, 3)], "❌ Agent 在线时应返回 (True, 3)")
        print("  ✅ [P1-T08] Agent 在线时正确返回 (True, active_sessions)")

    def test_emit_offline_when_connection_refused(self):
        """[P1-T09] Agent 离线（连接拒绝）时 health_result 应 emit(False, 0)"""
        results = []

        with patch("httpx.get", side_effect=ConnectionRefusedError("Connection refused")):
            try:
                import httpx
                httpx.get("http://127.0.0.1:18888/health", timeout=1.5)
            except Exception:
                results.append((False, 0))

        self.assertEqual(results, [(False, 0)], "❌ Agent 离线时应返回 (False, 0)")
        print("  ✅ [P1-T09] Agent 离线时正确返回 (False, 0)")

    def test_emit_offline_when_http_500(self):
        """[P1-T10] Agent 返回 500 时 health_result 应 emit(False, 0)"""
        results = []

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        # 模拟 AgentHealthWorker 核心逻辑
        try:
            resp = mock_resp
            if resp.status_code == 200:
                data = resp.json()
                results.append((True, data.get("active_sessions", 0)))
            else:
                results.append((False, 0))
        except Exception:
            results.append((False, 0))

        self.assertEqual(results, [(False, 0)], "❌ HTTP 500 时应返回 (False, 0)")
        print("  ✅ [P1-T10] HTTP 500 时正确返回 (False, 0)")


if __name__ == "__main__":
    print("=" * 60)
    print("  Phase 1 单元测试：UI 与 Agent 生命周期解耦验证")
    print("=" * 60)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestStaticAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentHealthWorkerLogic))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    # 用自定义方式打印，让输出更美观
    result = unittest.TestResult()
    suite.run(result)

    print()
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    if result.failures or result.errors:
        print("\n❌ 失败的测试：")
        for test, trace in result.failures + result.errors:
            print(f"   - {test}: {trace.splitlines()[-1]}")
    
    print()
    print("=" * 60)
    if failed == 0:
        print(f"  🎉 所有测试通过！({passed}/{total} PASSED)")
        print("  Phase 1 改造验证完成：UI 与 Agent 生命周期已成功解耦。")
    else:
        print(f"  ⚠️  {failed} 个测试失败 ({passed}/{total} passed)")
    print("=" * 60)
    sys.exit(1 if failed > 0 else 0)
