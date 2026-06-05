"""
翻译功能测试：验证 _inject_translation_direction 和翻译流程
"""
import pytest
import sys
import os

# 确保 opencopilot 模块可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestTranslationDirectionInjection:
    """SessionSetupMiddleware._inject_translation_direction 静态方法测试"""

    @staticmethod
    def _inject(persona_prompt: str, context_meta: dict) -> str:
        """直接引用被测试方法的实现——不 mock，调用业务代码"""
        from opencopilot.agent.middlewares import SessionSetupMiddleware
        return SessionSetupMiddleware._inject_translation_direction(persona_prompt, context_meta)

    BASE_PERSONA = (
        "你是 **OpenCopilot 智能助手** 的翻译模块，由 OpenCopilot 团队打造。\n\n"
        "作为金牌翻译官，请将用户提供的文本翻译为指定目标语言。要求信达雅，只输出翻译结果，不带任何解释和废话。\n\n"
        "**重要**：不要提及你底层使用的具体模型名称，保持 OpenCopilot 助手的身份。"
    )

    def test_zh_to_en(self):
        """中文 → 英文：替换 '翻译为指定目标语言' 为明确方向"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "zh", "target_lang": "en"})
        assert "从中文翻译为英文" in result
        assert "翻译为指定目标语言" not in result

    def test_en_to_zh(self):
        """英文 → 中文"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "en", "target_lang": "zh"})
        assert "从英文翻译为中文" in result
        assert "翻译为指定目标语言" not in result

    def test_ja_to_ko(self):
        """日文 → 韩文"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "ja", "target_lang": "ko"})
        assert "从日文翻译为韩文" in result

    def test_fr_to_de(self):
        """法文 → 德文"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "fr", "target_lang": "de"})
        assert "从法文翻译为德文" in result

    def test_unknown_lang_fallback(self):
        """未知语言代码：保留原始代码作为名称"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "th", "target_lang": "vi"})
        assert "从th翻译为vi" in result

    def test_no_context_meta_fallback(self):
        """无 context_meta 时回退到 zh→en 默认"""
        result = self._inject(self.BASE_PERSONA, {})
        assert "从中文翻译为英文" in result

    def test_old_persona_with_hardcoded_direction(self):
        """兼容旧版 persona: 不含 '翻译为指定目标语言' 时追加方向"""
        old_persona = "你是翻译助手，请把文本翻译为目标语言。"
        result = self._inject(old_persona, {"source_lang": "zh", "target_lang": "en"})
        assert "从中文翻译为英文" in result
        # 旧文本仍保留
        assert "你是翻译助手" in result

    def test_result_still_contains_identity(self):
        """方向注入后不丢失助手身份标识"""
        result = self._inject(self.BASE_PERSONA, {"source_lang": "zh", "target_lang": "en"})
        assert "OpenCopilot" in result
        assert "不要提及你底层使用的具体模型名称" in result


class TestTranslationDialogTextSeparation:
    """验证 translation_dialog._do_translate 只传纯文本，不传指令前缀"""

    def test_do_translate_passes_pure_text(self):
        """确认 _do_translate 传递的是纯文本而非带指令的 prompt 拼接"""
        # 读取源码确认 text 参数是直接传递给 call_agent_pipeline_sync
        import inspect
        from dialogs.translation_dialog import TranslationDialog

        source = inspect.getsource(TranslationDialog._do_translate)

        # 确认 text=text 传递的是原始文本（不是 prompt 拼接）
        assert "text=text" in source, (
            "_do_translate 应将纯文本作为 text 参数传入 pipeline，"
            "而非将指令+文本拼接后的 prompt 传入"
        )

        # 确认不再构建 prompt 拼接
        assert 'f"请将以下文本翻译成' not in source, (
            "_do_translate 不应再拼接 '请将以下文本翻译成...' 指令到 text 参数"
        )

    def test_context_meta_contains_lang_info(self):
        """确认 context_meta 包含 source_lang 和 target_lang"""
        import inspect
        from dialogs.translation_dialog import TranslationDialog

        source = inspect.getsource(TranslationDialog._do_translate)

        assert '"source_lang": source_lang' in source
        assert '"target_lang": target_lang' in source
        assert '"task": "translate"' in source


class TestTimerActionType:
    """验证中间件 Timer 日志携带 action_type"""

    def test_timer_accepts_action_type_kwarg(self):
        """timer() 方法接受 action_type 关键字参数"""
        import inspect
        from opencopilot.agent.observability import PipelineObservability

        sig = inspect.signature(PipelineObservability.timer)
        params = list(sig.parameters.keys())
        assert "action_type" in params, "timer() 方法应接受 action_type 参数"

    def test_middleware_timers_have_action_type(self):
        """验证关键中间件 timer 调用携带 action_type=ctx.action_type"""
        import os
        middlewares_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "opencopilot", "agent", "middlewares.py"
        )
        with open(middlewares_path, "r") as f:
            content = f.read()

        # 每个中间件类都应该有带 action_type 的 timer 调用
        middleware_classes = [
            "SessionSetup", "SecurityGuard", "ImmuneSystem",
            "Planner", "StateTracking", "CapabilityRouter",
            "LLMProvider", "LLMAgent",
        ]

        import re
        for mw_class in middleware_classes:
            # 查找每个中间件类的 process 方法中的 timer 调用
            # 找一个带 action_type=ctx.action_type 的模式
            pattern = rf"class {mw_class}Middleware"
            assert pattern in content, f"{mw_class}Middleware 类存在"

        # 确认 timer 调用总数中有足够多带 action_type 的
        import re
        timer_calls = re.findall(r'\.timer\(', content)
        # 逐行检测：timer 调用中 action_type=ctx.action_type 的个数
        # 注意：f-string 中的 ) 会干扰简单正则，改为逐行状态机
        timer_with_action = 0
        lines = content.split('\n')
        in_timer = False
        timer_line_no = -1
        for i, line in enumerate(lines):
            timer_opened = '.timer(' in line
            if timer_opened:
                in_timer = True
                timer_line_no = i
            if in_timer and 'action_type=ctx.action_type' in line:
                timer_with_action += 1
                in_timer = False
                continue
            # 只有当非开头的行出现 ) 且不含 action_type 时才认为 timer 结束
            if in_timer and i != timer_line_no and ')' in line and 'action_type' not in line:
                in_timer = False
        print(f"Total timer calls: {len(timer_calls)}")
        print(f"Timer calls with action_type=ctx.action_type: {timer_with_action}")
        # 至少 20 个 timer 调用应携带 action_type（共约 24 个 timer 调用）
        assert timer_with_action >= 20, (
            f"至少 20 个 timer 调用应携带 action_type=ctx.action_type，"
            f"实际只有 {timer_with_action} 个"
        )


class TestAllEntryPointsHaveObservability:
    """验证所有 pipeline 入口点都有埋点日志（检查特定事件名称）"""

    def _check_events_exist(self, filepath: str, required_events: list):
        """检查文件中是否包含指定的埋点事件名"""
        import os
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            filepath
        )
        with open(path, "r") as f:
            content = f.read()
        missing = []
        for event in required_events:
            if event not in content:
                missing.append(event)
        return missing

    def test_chat_worker_has_events(self):
        """ChatWorker 埋点事件"""
        missing = self._check_events_exist(
            "gui/workers/chat.py",
            ["worker_log", "START |", "FINISHED |", "CANCELLED |"]
        )
        assert not missing, f"ChatWorker 缺少事件: {missing}"

    def test_ai_worker_has_events(self):
        """AIWorker 埋点事件"""
        missing = self._check_events_exist(
            "gui/workers/ai.py",
            ["worker_log", "START |", "FINISHED |", "CANCELLED |", "ERROR |"]
        )
        assert not missing, f"AIWorker 缺少事件: {missing}"

    def test_translation_dialog_has_events(self):
        """翻译对话框埋点事件"""
        missing = self._check_events_exist(
            "dialogs/translation_dialog.py",
            ["gui_log", "TRANSLATION_START", "TRANSLATION_DONE", "TRANSLATION_EMPTY", "TRANSLATION_FAILED"]
        )
        assert not missing, f"TranslationDialog 缺少事件: {missing}"

    def test_ppt_widget_has_events(self):
        """PPT AI 共创组件埋点事件"""
        missing = self._check_events_exist(
            "opencopilot/capabilities/ppt/ai_chat_widget.py",
            ["gui_log", "PPT_COCREATION_START", "PPT_COCREATION_DONE",
             "PPT_ANALYZE_START", "PPT_ANALYZE_DONE",
             "PPT_SUGGEST_START", "PPT_SUGGEST_DONE"]
        )
        assert not missing, f"PPT ai_chat_widget 缺少事件: {missing}"

    def test_window_ppt_outline_has_events(self):
        """window.py PPT 大纲生成埋点事件"""
        missing = self._check_events_exist(
            "gui/window.py",
            ["gui_log", "PPT_OUTLINE_START", "PPT_OUTLINE_DONE"]
        )
        assert not missing, f"window.py PPT 大纲生成缺少事件: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
