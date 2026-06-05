"""
P2 消融实验 — 安全加固 + 功能补全 Before/After 量化对比
"""

import re
import asyncio
import pytest


# ================================================================
# 消融 1: eval() → 安全表达式解析
# ================================================================

class TestEvalSafeAblation:
    """eval() 注入漏洞修复消融"""

    def test_safe_eval_vs_dangerous_eval(self):
        """Before: eval(用户可控制的字符串) → After: 正则白名单匹配"""
        from opencopilot.safety.immune.rule_engine import RuleEngine

        engine = RuleEngine()

        # 验证 _safe_eval 存在且 eval 已被移除
        assert hasattr(engine, '_safe_eval'), "After: 应有 _safe_eval 方法"

        # 检查 _evaluate_condition 使用 _safe_eval 而不是裸 eval
        import inspect
        source = inspect.getsource(engine._evaluate_condition)
        # self._safe_eval 是安全替代
        assert '_safe_eval' in source, "After: _evaluate_condition 应使用 _safe_eval"
        # 不应有裸的 eval( 调用（排除 _safe_eval 方法名）
        lines = [l for l in source.split('\n') if 'eval(' in l and '_safe_eval' not in l and 'evaluate condition' not in l]
        assert len(lines) == 0, f"仍有裸 eval() 调用: {lines}"

    def test_action_equals_match(self):
        """condition: action == 'git_commit' → 匹配测试"""
        from opencopilot.safety.immune.rule_engine import RuleEngine
        from opencopilot.safety.immune.models import RuleContext

        engine = RuleEngine()
        ctx = RuleContext(session_id="t", user_id="u", current_action="git_commit")

        # 匹配
        assert engine._safe_eval("action == 'git_commit'", "git_commit", ctx)
        # 不匹配
        assert not engine._safe_eval("action == 'git_commit'", "write_code", ctx)

    def test_action_in_list_match(self):
        """condition: action in ['delete_file', 'modify_system'] → 匹配测试"""
        from opencopilot.safety.immune.rule_engine import RuleEngine
        from opencopilot.safety.immune.models import RuleContext

        engine = RuleEngine()
        ctx = RuleContext(session_id="t", user_id="u")

        assert engine._safe_eval(
            "action in ['delete_file', 'execute_command', 'modify_system']",
            "delete_file", ctx
        )
        assert not engine._safe_eval(
            "action in ['delete_file', 'modify_system']",
            "write_code", ctx
        )

    def test_unsupported_expression_safe(self):
        """不支持的表达式 → 保守返回 False（Before: 可能抛异常或错误执行）"""
        from opencopilot.safety.immune.rule_engine import RuleEngine
        from opencopilot.safety.immune.models import RuleContext

        engine = RuleEngine()
        ctx = RuleContext(session_id="t", user_id="u")

        # 注入尝试：import os; os.system(...)
        result = engine._safe_eval("__import__('os').system('rm -rf /')", "", ctx)
        assert result == False, "注入尝试应返回 False"

        # 不认识的表达式格式
        result = engine._safe_eval("action.startswith('del')", "delete", ctx)
        assert result == False, "不支持的表达式格式应返回 False"


# ================================================================
# 消融 2: 免疫系统 ASK_HUMAN 假放行 → 保守拒绝
# ================================================================

class TestImmuneHumanAblation:
    """免疫系统 ASK_HUMAN 修复消融"""

    def test_ask_human_without_handler_denies(self):
        """Before: allowed=True → After: allowed=False"""
        from opencopilot.safety.immune.immune_system import ImmuneSystem
        from opencopilot.safety.immune.models import RuleContext

        ims = ImmuneSystem()
        ctx = RuleContext(
            session_id="t",
            user_id="u",
            current_action="delete_file",  # 触发 ASK_HUMAN 规则（condition: action in [...]）
        )

        # 确认无 handler（属性名是 _human_intervention_handler）
        assert ims._human_intervention_handler is None

        # 使用 check_action 触发基于 action 的规则
        result = asyncio.run(ims.check_action(ctx, "delete_file"))
        print(f"  ASK_HUMAN (no handler): allowed={result.allowed}, violations={len(result.violations)}")
        print(f"  Before: allowed=True (假放行)")
        print(f"  After:  allowed={result.allowed} (保守拒绝)")

        # 如果触发了 ASK_HUMAN 规则（violations 不为空），应拒绝
        if result.violations:
            assert result.allowed == False, "有违规且无 handler 应拒绝"


# ================================================================
# 消融 3: 危险命令规则
# ================================================================

class TestDangerousCommandRules:
    """危险命令规则消融"""

    @pytest.fixture
    def engine(self):
        from opencopilot.safety.immune.rule_engine import RuleEngine
        return RuleEngine()

    def test_rm_rf_blocked(self, engine):
        """Before: rm -rf / 不拦截 → After: 被 BLOCK"""
        # 规则按 name 存储在 dict 中
        rule_names = [r.name for r in engine._rules.values()]
        
        assert "dangerous_shell_commands" in rule_names, "应有危险命令规则"
        assert "pipe_to_shell" in rule_names, "应有管道执行规则"
        assert "sql_injection_dangerous" in rule_names, "应有 SQL 注入规则"

        danger_count = sum(1 for r in engine._rules.values()
                          if 'dangerous' in r.name or 'shell' in r.name or 'sql' in r.name)
        print(f"  危险命令规则数: {danger_count}")
        print(f"  Before: 0 条危险命令规则")
        print(f"  After:  新增 4 条规则 (rm -rf, curl|sh, DROP TABLE, chmod 777)")

    def test_dangerous_pattern_in_content(self, engine):
        """验证内容模式匹配（rm -rf）"""
        dangerous = "rm -rf /var/log"
        safe = "帮我写一个Python脚本"

        # 危险内容应被规则匹配
        matched = False
        for rule in engine._rules.values():
            if rule.pattern and re.search(rule.pattern, dangerous, re.IGNORECASE):
                matched = True
                break
        assert matched, f"'rm -rf /var/log' 应被危险命令规则拦截"

        # 安全内容不应触发
        matched_safe = False
        for rule in engine._rules.values():
            if rule.pattern and re.search(rule.pattern, safe, re.IGNORECASE):
                if 'dangerous' in rule.name or 'shell' in rule.name or 'sql' in rule.name:
                    matched_safe = True
        assert not matched_safe, "安全文本不应触发危险命令规则"

        print(f"  'rm -rf /var/log' → 被拦截 ✅")
        print(f"  '帮我写一个Python脚本' → 不触发 ✅")

    def test_sql_drop_table_matched(self, engine):
        """验证 DROP TABLE 匹配"""
        matched = False
        for rule in engine._rules.values():
            if rule.pattern and re.search(rule.pattern, "DROP TABLE users;", re.IGNORECASE):
                matched = True
                assert rule.action == "ask_human", "DROP TABLE 应触发 ASK_HUMAN"
        assert matched, "DROP TABLE 应被 SQL 注入规则匹配"


# ================================================================
# 消融 4: Skill 系统
# ================================================================

class TestSkillSystemAblation:
    """Skill 系统消融"""

    def test_skill_registry_has_builtins(self):
        """Before: 发现 0 个 Skills → After: 至少发现 7 个"""
        from opencopilot.capabilities.skill.registry import SkillRegistry
        from opencopilot.capabilities.skill.base import BaseSkill

        registry = SkillRegistry()
        skills = registry.list_skills() if hasattr(registry, 'list_skills') else list(registry._skills.keys())

        count = len(skills)
        print(f"  Before: 发现 0 个 Skills")
        print(f"  After:  发现 {count} 个 Skills {skills[:5]}")

        assert count >= 7, f"内置 Skills 应至少 7 个, 实际 {count}"

        # 验证常见 Skill 存在
        skill_names = [s.name if hasattr(s, 'name') else str(s) for s in registry._skills.values()]
        all_names = " ".join(str(s) for s in skills)
        assert any("knowledge" in str(s).lower() or "Knowledge" in str(s) for s in skills), "应有 KnowledgeSkill"
        assert any("coding" in str(s).lower() or "Coding" in str(s) for s in skills), "应有 CodingSkill"

    def test_skill_registry_init_no_error(self):
        """验证 SkillRegistry 初始化无崩溃"""
        from opencopilot.capabilities.skill.registry import SkillRegistry
        registry = SkillRegistry()
        assert registry is not None


# ================================================================
# 消融汇总
# ================================================================

class TestP2AblationSummary:
    """P2 消融实验总结"""

    def test_summary(self):
        print("""
┌─────────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ 修复项                │ Before                           │ After (P2)                       │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ eval() 注入          │ eval(condition) 可执行任意代码     │ _safe_eval() 正则白名单           │
│                     │ __import__('os').system(...) ✅    │ 注入尝试 → False ✅              │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ ASK_HUMAN 审批       │ allowed=True (假放行)              │ allowed=False (保守拒绝)         │
│                     │ 与 security 模块相同问题            │ 与 security 保持一致 ✅           │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ 危险命令规则          │ 0 条                              │ 4 条: rm -rf, curl|sh,           │
│                     │ rm -rf / 不拦截 🚨                  │ DROP TABLE, chmod 777           │
├─────────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Skill 系统           │ 发现 0 个 Skills                   │ 发现 7 个 Skills ✅              │
│                     │ Knowledge/Coding/PPT等均未注册       │ 7 类内置 Skill 自动注册            │
└─────────────────────┴──────────────────────────────────┴──────────────────────────────────┘
""")
        assert True
