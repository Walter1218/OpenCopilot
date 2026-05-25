"""
P0 单元测试：ContextWindowManager + ContextEnvelope 兼容层
=======================================================

运行方式：
    python test_context_window_manager.py
"""

import time
import unittest

from asu_custom_agent import ContextWindowManager, normalize_context_envelope


class TestContextEnvelope(unittest.TestCase):
    def test_normalize_legacy_fields(self):
        req = {
            "text": "legacy text",
            "context_source": "ide",
            "context_meta": {"file_name": "a.py", "language": "python", "task": "fix bug"},
        }
        env = normalize_context_envelope(req, req["text"], req["context_source"], req["context_meta"])

        self.assertEqual(env["source"], "ide")
        self.assertEqual(env["content"], "legacy text")
        self.assertEqual(env["task"], "fix bug")
        self.assertEqual(env["meta"]["file_name"], "a.py")
        self.assertTrue(abs(env["timestamp"] - time.time()) < 5)

    def test_normalize_prefers_context_envelope(self):
        req = {
            "text": "legacy text",
            "context_source": "drag",
            "context_meta": {"app_name": "LegacyApp"},
            "context_envelope": {
                "source": "browser",
                "content": "new envelope content",
                "selection": "sel",
                "task": "research",
                "meta": {"app_name": "Safari", "url": "https://example.com"},
                "timestamp": 123.0,
            },
        }
        env = normalize_context_envelope(req, req["text"], req["context_source"], req["context_meta"])

        self.assertEqual(env["source"], "browser")
        self.assertEqual(env["content"], "new envelope content")
        self.assertEqual(env["selection"], "sel")
        self.assertEqual(env["task"], "research")
        self.assertEqual(env["meta"]["app_name"], "Safari")
        self.assertEqual(env["timestamp"], 123.0)


class TestContextWindowManager(unittest.TestCase):
    def setUp(self):
        self.manager = ContextWindowManager(
            max_input_chars=1400,
            reserve_output_chars=300,
            recent_turns=2,
            max_history_msg_chars=120,
        )

    def test_keep_recent_history_only(self):
        history = []
        for i in range(8):
            role = "user" if i % 2 == 0 else "assistant"
            history.append({"role": role, "content": f"msg_{i}"})

        envelope = {
            "source": "chat",
            "content": "current input",
            "selection": "",
            "task": "",
            "meta": {},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system", envelope, history)

        all_text = "\n".join(m["content"] for m in messages)
        self.assertIn("msg_7", all_text)
        self.assertIn("msg_6", all_text)
        self.assertIn("msg_5", all_text)
        self.assertIn("msg_4", all_text)
        self.assertNotIn("msg_0", all_text)
        self.assertNotIn("msg_1", all_text)

    def test_ide_content_is_clipped_with_marker(self):
        long_code = "def x():\n" + ("print('x')\n" * 1000)
        envelope = {
            "source": "ide",
            "content": long_code,
            "selection": "print('x')",
            "task": "review code",
            "meta": {"file_name": "main.py", "language": "python"},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system", envelope, [])
        user_payload = messages[-1]["content"]

        self.assertIn("[context_source] ide", user_payload)
        self.assertIn("[selection]", user_payload)
        self.assertIn("[content]", user_payload)
        self.assertIn("...[IDE内容已裁剪，保留头尾关键片段]...", user_payload)

    def test_final_payload_within_reasonable_budget(self):
        history = [{"role": "user", "content": "h" * 600} for _ in range(6)]
        envelope = {
            "source": "browser",
            "content": "web" * 2000,
            "selection": "",
            "task": "summarize",
            "meta": {"app_name": "Safari", "title": "Example", "url": "https://example.com"},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system" * 30, envelope, history)
        total_chars = sum(len(m["content"]) for m in messages)

        # 预算是近似控制（字符近似 token），允许一定结构性开销
        self.assertLessEqual(total_chars, self.manager.max_input_chars + 120)

    def test_empty_content_still_builds_valid_user_payload(self):
        envelope = {
            "source": "drag",
            "content": "",
            "selection": "",
            "task": "",
            "meta": {},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system", envelope, [])
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("[content]", messages[-1]["content"])

    def test_non_string_content_is_normalized_to_string(self):
        req = {
            "context_envelope": {
                "source": "chat",
                "content": 12345,
                "meta": {},
            }
        }
        env = normalize_context_envelope(req, "fallback", "drag", {})
        self.assertEqual(env["content"], "12345")

    def test_tiny_budget_does_not_crash(self):
        tiny = ContextWindowManager(
            max_input_chars=300,
            reserve_output_chars=250,
            recent_turns=1,
            max_history_msg_chars=40,
        )
        envelope = {
            "source": "browser",
            "content": "A" * 5000,
            "selection": "B" * 200,
            "task": "C" * 200,
            "meta": {"app_name": "Safari", "title": "T" * 120},
            "timestamp": time.time(),
        }
        messages = tiny.build_messages("sys" * 50, envelope, [{"role": "user", "content": "H" * 500}])
        self.assertGreaterEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["role"], "user")

    def test_history_message_is_capped(self):
        history = [
            {"role": "user", "content": "x" * 1000},
            {"role": "assistant", "content": "y" * 1000},
        ]
        envelope = {
            "source": "chat",
            "content": "hello",
            "selection": "",
            "task": "",
            "meta": {},
            "timestamp": time.time(),
        }
        messages = self.manager.build_messages("system", envelope, history)
        history_contents = [m["content"] for m in messages[1:-1]]
        self.assertTrue(all(len(c) <= self.manager.max_history_msg_chars + 30 for c in history_contents))


if __name__ == "__main__":
    unittest.main(verbosity=2)
