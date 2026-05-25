"""
真实场景 + 边界压力测试：ContextWindowManager
=============================================

运行方式：
    python test_context_window_realworld.py
"""

import time
import unittest

from asu_custom_agent import ContextWindowManager, normalize_context_envelope


def _make_history(rounds, user_size=600, assistant_size=700):
    history = []
    for i in range(rounds):
        history.append({"role": "user", "content": f"[u{i}] " + ("U" * user_size)})
        history.append({"role": "assistant", "content": f"[a{i}] " + ("A" * assistant_size)})
    return history


def _estimate_raw_chars(system_prompt, envelope, history):
    meta = envelope.get("meta", {}) or {}
    meta_text = "；".join(f"{k}={v}" for k, v in meta.items())
    raw = len(system_prompt)
    raw += sum(len(m.get("content", "")) for m in history)
    raw += len(str(envelope.get("content", "") or ""))
    raw += len(str(envelope.get("selection", "") or ""))
    raw += len(str(envelope.get("task", "") or ""))
    raw += len(meta_text)
    return raw


class TestContextWindowRealworld(unittest.TestCase):
    def setUp(self):
        self.manager = ContextWindowManager(
            max_input_chars=10000,
            reserve_output_chars=2500,
            recent_turns=4,
            max_history_msg_chars=1000,
        )

    def test_ide_review_realworld(self):
        history = _make_history(rounds=6, user_size=450, assistant_size=500)
        content = "# main.py\n" + ("def handler(x):\n    return x + 1\n" * 450)
        envelope = {
            "source": "ide",
            "content": content,
            "selection": "def handler(x):\n    return x + 1",
            "task": "审查性能瓶颈并给出重构建议",
            "meta": {"file_name": "main.py", "language": "python", "app_name": "Trae"},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system prompt", envelope, history)
        user_payload = messages[-1]["content"]

        self.assertIn("[context_source] ide", user_payload)
        self.assertIn("[selection]", user_payload)
        self.assertIn("...[IDE内容已裁剪，保留头尾关键片段]...", user_payload)
        self.assertLessEqual(len(messages) - 2, self.manager.recent_turns * 2)

    def test_browser_research_realworld(self):
        history = _make_history(rounds=8, user_size=320, assistant_size=420)
        article = "【长文】" + ("这是一段网页正文。" * 2500)
        envelope = {
            "source": "browser",
            "content": article,
            "selection": "",
            "task": "提炼三条结论并给出处",
            "meta": {"app_name": "Safari", "title": "AI 趋势报告", "url": "https://example.com/report"},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system prompt", envelope, history)
        user_payload = messages[-1]["content"]

        self.assertIn("[context_source] browser", user_payload)
        self.assertIn("...[网页正文已裁剪]...", user_payload)
        self.assertLessEqual(len(messages) - 2, self.manager.recent_turns * 2)

    def test_multiturn_growth_stability(self):
        history = []
        system_prompt = "system prompt for long session"

        for i in range(20):
            envelope = {
                "source": "chat",
                "content": f"第{i}轮问题：" + ("请继续深入分析。" * 120),
                "selection": "",
                "task": "持续推进同一任务",
                "meta": {},
                "timestamp": time.time(),
            }
            messages = self.manager.build_messages(system_prompt, envelope, history)
            total_chars = sum(len(m["content"]) for m in messages)
            self.assertLessEqual(total_chars, self.manager.max_input_chars + 500)
            self.assertLessEqual(len(messages) - 2, self.manager.recent_turns * 2)

            # 模拟一轮对话结束后写入历史
            history.append({"role": "user", "content": envelope["content"]})
            history.append({"role": "assistant", "content": "收到，以下是分析：" + ("建议。" * 140)})

    def test_source_switching_same_session(self):
        history = _make_history(rounds=3, user_size=200, assistant_size=240)

        ide_env = {
            "source": "ide",
            "content": "print('hello')\n" * 500,
            "selection": "print('hello')",
            "task": "修复 bug",
            "meta": {"file_name": "a.py", "language": "python"},
            "timestamp": time.time(),
        }
        browser_env = {
            "source": "browser",
            "content": "网页正文" * 1200,
            "selection": "",
            "task": "查证资料",
            "meta": {"app_name": "Chrome", "title": "Doc"},
            "timestamp": time.time(),
        }
        drag_env = {
            "source": "drag",
            "content": "用户手动拖拽的零散文本" * 260,
            "selection": "",
            "task": "合并分析",
            "meta": {},
            "timestamp": time.time(),
        }

        ide_msg = self.manager.build_messages("sys", ide_env, history)[-1]["content"]
        browser_msg = self.manager.build_messages("sys", browser_env, history)[-1]["content"]
        drag_msg = self.manager.build_messages("sys", drag_env, history)[-1]["content"]

        self.assertIn("[context_source] ide", ide_msg)
        self.assertIn("[context_source] browser", browser_msg)
        self.assertIn("[context_source] drag", drag_msg)

    def test_tiny_budget_extreme_inputs(self):
        tiny = ContextWindowManager(
            max_input_chars=500,
            reserve_output_chars=450,
            recent_turns=1,
            max_history_msg_chars=80,
        )
        history = _make_history(rounds=4, user_size=500, assistant_size=500)
        envelope = {
            "source": "browser",
            "content": "X" * 20000,
            "selection": "Y" * 1000,
            "task": "Z" * 1000,
            "meta": {"app_name": "Safari", "title": "T" * 300, "url": "https://example.com/" + ("a" * 300)},
            "timestamp": time.time(),
        }

        messages = tiny.build_messages("S" * 600, envelope, history)
        self.assertGreaterEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["role"], "user")

    def test_envelope_normalization_under_malformed_input(self):
        req = {
            "context_envelope": {
                "source": 123,
                "content": None,
                "selection": ["not", "string"],
                "task": {"bad": "type"},
                "meta": "not-dict",
            }
        }
        env = normalize_context_envelope(req, "fallback", "drag", {"task": "legacy"})

        # 当前实现保证 content 为字符串，其他字段允许透传但不能崩溃
        self.assertIsInstance(env["content"], str)
        messages = self.manager.build_messages("sys", env, [])
        self.assertEqual(messages[-1]["role"], "user")


def run_quant_report():
    manager = ContextWindowManager(
        max_input_chars=10000,
        reserve_output_chars=2500,
        recent_turns=4,
        max_history_msg_chars=1000,
    )

    scenarios = [
        {
            "name": "ide_large_file",
            "system": "system" * 80,
            "history": _make_history(6, 450, 500),
            "envelope": {
                "source": "ide",
                "content": "def x():\n    pass\n" * 1200,
                "selection": "def x():",
                "task": "代码评审",
                "meta": {"file_name": "main.py", "language": "python"},
                "timestamp": time.time(),
            },
        },
        {
            "name": "browser_long_article",
            "system": "system" * 40,
            "history": _make_history(8, 300, 450),
            "envelope": {
                "source": "browser",
                "content": "正文" * 9000,
                "selection": "",
                "task": "总结观点",
                "meta": {"app_name": "Safari", "title": "Long Read", "url": "https://example.com"},
                "timestamp": time.time(),
            },
        },
        {
            "name": "chat_long_session",
            "system": "system" * 60,
            "history": _make_history(16, 280, 360),
            "envelope": {
                "source": "chat",
                "content": "继续深挖" * 600,
                "selection": "",
                "task": "同一任务推进",
                "meta": {},
                "timestamp": time.time(),
            },
        },
        {
            "name": "drag_bulk_text",
            "system": "system" * 30,
            "history": _make_history(5, 220, 260),
            "envelope": {
                "source": "drag",
                "content": "用户粘贴资料" * 3500,
                "selection": "",
                "task": "提炼要点",
                "meta": {},
                "timestamp": time.time(),
            },
        },
    ]

    rows = []
    for s in scenarios:
        messages = manager.build_messages(s["system"], s["envelope"], s["history"])
        raw_chars = _estimate_raw_chars(s["system"], s["envelope"], s["history"])
        final_chars = sum(len(m["content"]) for m in messages)
        compression = 0.0 if raw_chars == 0 else (1 - final_chars / raw_chars)
        history_total = len(s["history"])
        history_kept = max(0, len(messages) - 2)
        history_keep_ratio = 0.0 if history_total == 0 else history_kept / history_total
        rows.append({
            "name": s["name"],
            "raw_chars": raw_chars,
            "final_chars": final_chars,
            "compression": compression,
            "history_kept": history_kept,
            "history_total": history_total,
            "history_keep_ratio": history_keep_ratio,
        })

    avg_compression = sum(r["compression"] for r in rows) / len(rows)
    avg_keep_ratio = sum(r["history_keep_ratio"] for r in rows) / len(rows)
    max_final_chars = max(r["final_chars"] for r in rows)

    print("\n=== Quant Report (Context Window) ===")
    for r in rows:
        print(
            f"- {r['name']}: raw={r['raw_chars']}, final={r['final_chars']}, "
            f"compress={r['compression'] * 100:.1f}%, "
            f"history={r['history_kept']}/{r['history_total']}({r['history_keep_ratio'] * 100:.1f}%)"
        )
    print(
        f"SUMMARY: scenarios={len(rows)}, avg_compress={avg_compression * 100:.1f}%, "
        f"avg_history_keep={avg_keep_ratio * 100:.1f}%, max_final_chars={max_final_chars}, "
        f"budget_limit={manager.max_input_chars}"
    )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestContextWindowRealworld)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    run_quant_report()
    raise SystemExit(0 if result.wasSuccessful() else 1)
