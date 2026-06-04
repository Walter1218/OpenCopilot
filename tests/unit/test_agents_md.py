"""
AGENTS.md 免疫系统模块测试
"""
import pytest
import os



class TestRuleEngine:
    """规则引擎"""

    def test_init(self):
        from opencopilot.safety.immune import RuleEngine
        engine = RuleEngine()
        assert engine is not None

    def test_add_and_get_rule(self):
        from opencopilot.safety.immune import RuleEngine
        from opencopilot.safety.immune.models import AgentRule, RuleType, RuleSeverity
        engine = RuleEngine()
        rule = AgentRule(
            rule_id="rule-1",
            name="test_rule",
            description="test",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.WARNING.value,
            pattern=r"test_pattern",
        )
        result = engine.add_rule(rule)
        assert result is True
        found = engine.get_rule_by_name("test_rule")
        assert found is not None

    def test_remove_rule(self):
        from opencopilot.safety.immune import RuleEngine
        from opencopilot.safety.immune.models import AgentRule, RuleType, RuleSeverity
        engine = RuleEngine()
        rule = AgentRule(
            rule_id="rule-rm",
            name="to_remove",
            description="to remove",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.INFO.value,
        )
        engine.add_rule(rule)
        result = engine.remove_rule("rule-rm")
        assert result is True
        assert engine.get_rule_by_name("to_remove") is None


class TestImmuneSystem:
    """免疫系统"""

    @pytest.fixture
    def immune(self):
        from opencopilot.safety.immune import ImmuneSystem
        return ImmuneSystem()

    def test_init(self, immune):
        assert immune is not None
        assert immune.rule_engine is not None

    def test_add_rule(self, immune):
        from opencopilot.safety.immune.models import AgentRule, RuleType, RuleSeverity
        rule = AgentRule(
            rule_id="immune-1",
            name="test_immune_rule",
            description="Test immune rule",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.CRITICAL.value,
            pattern=r"test_content",
        )
        result = immune.add_rule(rule)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_content_safe(self, immune):
        from opencopilot.safety.immune.models import RuleContext
        ctx = RuleContext(session_id="test", user_id="test_user")
        response = await immune.check_content(ctx, "safe content")
        assert response.allowed is True

    @pytest.mark.asyncio
    async def test_check_content_blocked(self, immune):
        from opencopilot.safety.immune.models import AgentRule, RuleContext, RuleType, RuleSeverity, ViolationAction
        rule = AgentRule(
            rule_id="block-1",
            name="block_test",
            description="Block test",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.CRITICAL.value,
            pattern=r"BLOCKED_PHRASE",
            action=ViolationAction.BLOCK.value,
        )
        immune.add_rule(rule)
        ctx = RuleContext(session_id="test", user_id="test_user")
        response = await immune.check_content(ctx, "This contains BLOCKED_PHRASE\nrest of content")
        assert not response.allowed
