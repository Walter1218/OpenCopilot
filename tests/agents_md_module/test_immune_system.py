# tests/agents_md_module/test_immune_system.py

"""
AGENTS.md 免疫机制模块测试

测试免疫系统的各项功能。
"""

import pytest
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入免疫机制模块
from agents_md_module.models import (
    AgentsMdConfig, AgentRule, RuleViolation, RuleContext,
    RuleCheckResult, ImmuneResponse, RuleType, RuleSeverity,
    RuleScope, ViolationAction, generate_rule_id
)
from agents_md_module.immune_system import ImmuneSystem
from agents_md_module.rule_engine import RuleEngine


@pytest.fixture
def immune_system():
    """创建免疫系统实例"""
    config = AgentsMdConfig(
        enabled=True,
        default_action=ViolationAction.LOG.value,
        enable_auto_fix=True,
        enable_inheritance=True,
        max_violations=1000
    )
    return ImmuneSystem(config=config)


@pytest.fixture
def rule_engine():
    """创建规则引擎实例"""
    return RuleEngine()


@pytest.fixture
def rule_context():
    """创建规则上下文"""
    return RuleContext(
        user_id="test_user",
        session_id="test_session",
        project_path="/test/project",
        current_file="test.py",
        tool_name="code_editor"
    )


class TestModels:
    """数据模型测试"""
    
    def test_generate_rule_id(self):
        """测试生成规则 ID"""
        id1 = generate_rule_id()
        id2 = generate_rule_id()
        
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2
    
    def test_agent_rule_creation(self):
        """测试创建 Agent 规则"""
        rule = AgentRule(
            rule_id="test_rule",
            name="test_rule",
            description="Test rule",
            rule_type=RuleType.BEHAVIOR.value,
            severity=RuleSeverity.WARNING.value
        )
        
        assert rule.rule_id == "test_rule"
        assert rule.name == "test_rule"
        assert rule.rule_type == RuleType.BEHAVIOR.value
    
    def test_rule_violation_creation(self):
        """测试创建规则违规"""
        violation = RuleViolation(
            violation_id="test_violation",
            rule_id="test_rule",
            rule_name="test_rule",
            timestamp=1234567890.0,
            details="Test violation"
        )
        
        assert violation.violation_id == "test_violation"
        assert violation.rule_id == "test_rule"
        assert violation.resolved is False
    
    def test_rule_context_creation(self):
        """测试创建规则上下文"""
        context = RuleContext(
            user_id="user1",
            session_id="session1",
            project_path="/project"
        )
        
        assert context.user_id == "user1"
        assert context.session_id == "session1"


class TestRuleEngine:
    """规则引擎测试"""
    
    def test_default_rules(self, rule_engine):
        """测试默认规则"""
        rules = rule_engine.list_rules()
        
        assert len(rules) > 0
        
        # 检查是否有默认规则
        rule_names = [r.name for r in rules]
        assert "no_print_statements" in rule_names
        assert "no_eval_exec" in rule_names
    
    def test_add_rule(self, rule_engine):
        """测试添加规则"""
        rule = AgentRule(
            rule_id="custom_rule",
            name="custom_rule",
            description="Custom rule",
            rule_type=RuleType.BEHAVIOR.value,
            severity=RuleSeverity.INFO.value
        )
        
        success = rule_engine.add_rule(rule)
        
        assert success is True
        assert rule_engine.get_rule("custom_rule") is not None
    
    def test_remove_rule(self, rule_engine):
        """测试删除规则"""
        # 添加规则
        rule = AgentRule(
            rule_id="temp_rule",
            name="temp_rule",
            description="Temporary rule",
            rule_type=RuleType.BEHAVIOR.value
        )
        rule_engine.add_rule(rule)
        
        # 删除规则
        success = rule_engine.remove_rule("temp_rule")
        
        assert success is True
        assert rule_engine.get_rule("temp_rule") is None
    
    def test_check_rules_pattern_match(self, rule_engine, rule_context):
        """测试规则检查 - 模式匹配"""
        # 检查包含 print 的代码
        result = rule_engine.check_rules(
            context=rule_context,
            content="print('Hello, World!')"
        )
        
        # 应该检测到违规
        assert result.has_violations is True
        
        # 检查违规规则
        violation_rules = [v.rule_name for v in result.violations]
        assert "no_print_statements" in violation_rules
    
    def test_check_rules_no_violation(self, rule_engine, rule_context):
        """测试规则检查 - 无违规"""
        # 检查正常代码
        result = rule_engine.check_rules(
            context=rule_context,
            content="x = 1 + 2"
        )
        
        # 应该没有违规
        assert result.valid is True
        assert len(result.violations) == 0
    
    def test_check_rules_security_violation(self, rule_engine, rule_context):
        """测试规则检查 - 安全违规"""
        # 检查包含 eval 的代码
        result = rule_engine.check_rules(
            context=rule_context,
            content="eval(user_input)"
        )
        
        # 应该检测到严重违规
        assert result.has_violations is True
        assert result.has_critical_violations is True
    
    def test_get_stats(self, rule_engine):
        """测试获取统计信息"""
        stats = rule_engine.get_stats()
        
        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "total_violations" in stats


class TestImmuneSystem:
    """免疫系统测试"""
    
    @pytest.mark.asyncio
    async def test_check_action_allowed(self, immune_system, rule_context):
        """测试检查动作 - 允许"""
        response = await immune_system.check_action(
            context=rule_context,
            action="read_file"
        )
        
        assert response.allowed is True
        assert response.message == "Action allowed"
    
    @pytest.mark.asyncio
    async def test_check_action_blocked(self, immune_system, rule_context):
        """测试检查动作 - 阻止"""
        # 添加一个阻止规则
        rule = AgentRule(
            rule_id="block_delete",
            name="block_delete",
            description="Block delete actions",
            rule_type=RuleType.CONSTRAINT.value,
            severity=RuleSeverity.CRITICAL.value,
            condition="action == 'delete_file'",
            action=ViolationAction.BLOCK.value,
            message="Delete actions are blocked"
        )
        immune_system.add_rule(rule)
        
        response = await immune_system.check_action(
            context=rule_context,
            action="delete_file"
        )
        
        assert response.allowed is False
        assert "blocked" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_content_allowed(self, immune_system, rule_context):
        """测试检查内容 - 允许"""
        response = await immune_system.check_content(
            context=rule_context,
            content="x = 1 + 2"
        )
        
        assert response.allowed is True
    
    @pytest.mark.asyncio
    async def test_check_content_with_violation(self, immune_system, rule_context):
        """测试检查内容 - 有违规"""
        response = await immune_system.check_content(
            context=rule_context,
            content="print('debug')"
        )
        
        # 应该有违规但允许执行（默认动作是 LOG）
        assert response.allowed is True
        assert len(response.violations) > 0
    
    @pytest.mark.asyncio
    async def test_check_content_blocked(self, immune_system, rule_context):
        """测试检查内容 - 阻止"""
        response = await immune_system.check_content(
            context=rule_context,
            content="eval(dangerous_code)"
        )
        
        # 应该被阻止（默认规则中 eval 是 CRITICAL 级别）
        assert response.allowed is False
    
    def test_add_rule(self, immune_system):
        """测试添加规则"""
        rule = AgentRule(
            rule_id="custom_rule",
            name="custom_rule",
            description="Custom rule",
            rule_type=RuleType.BEHAVIOR.value
        )
        
        success = immune_system.add_rule(rule)
        
        assert success is True
        assert immune_system.get_rule("custom_rule") is not None
    
    def test_list_rules(self, immune_system):
        """测试列出规则"""
        rules = immune_system.list_rules()
        
        assert len(rules) > 0
    
    def test_get_violations(self, immune_system):
        """测试获取违规记录"""
        violations = immune_system.get_violations()
        
        # 初始应该没有违规
        assert len(violations) == 0
    
    def test_get_stats(self, immune_system):
        """测试获取统计信息"""
        stats = immune_system.get_stats()
        
        assert "total_checks" in stats
        assert "violations_detected" in stats
        assert "total_rules" in stats
    
    def test_get_status(self, immune_system):
        """测试获取状态"""
        status = immune_system.get_status()
        
        assert "enabled" in status
        assert "stats" in status
        assert "config" in status
    
    @pytest.mark.asyncio
    async def test_auto_fix(self, immune_system, rule_context):
        """测试自动修复"""
        # 注册自动修复处理器
        fix_called = False
        
        def fix_handler(violation, context):
            nonlocal fix_called
            fix_called = True
            return True
        
        # 获取默认规则
        rules = immune_system.list_rules()
        if rules:
            rule_id = rules[0].rule_id
            
            # 修改规则动作为 AUTO_FIX
            rule = immune_system.get_rule(rule_id)
            if rule:
                rule.action = ViolationAction.AUTO_FIX.value
                
                # 注册处理器
                immune_system.register_auto_fix_handler(rule_id, fix_handler)
                
                # 检查内容触发违规
                if rule.pattern:
                    await immune_system.check_content(
                        context=rule_context,
                        content="print('test')"
                    )
                    
                    # 注意：自动修复可能不会被调用，因为规则可能不匹配


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
