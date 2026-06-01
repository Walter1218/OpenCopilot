# agents_md_module/rule_engine.py

"""
规则引擎

负责解析、管理和执行 AGENTS.md 规则。
"""

import re
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

from .models import (
    AgentRule, RuleViolation, RuleContext, RuleCheckResult,
    RuleType, RuleSeverity, RuleScope, ViolationAction,
    AgentsMdConfig
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎
    
    负责解析、管理和执行 AGENTS.md 规则，支持：
    - 规则解析和加载
    - 规则匹配和执行
    - 违规检测和处理
    - 规则继承和覆盖
    """
    
    def __init__(self, config: Optional[AgentsMdConfig] = None):
        """
        初始化规则引擎
        
        Args:
            config: AGENTS.md 配置
        """
        self.config = config or AgentsMdConfig()
        
        # 规则存储: rule_id -> AgentRule
        self._rules: Dict[str, AgentRule] = {}
        
        # 规则名称索引: name -> rule_id
        self._rules_by_name: Dict[str, str] = {}
        
        # 违规记录
        self._violations: List[RuleViolation] = []
        
        # 规则缓存
        self._rules_cache: Dict[str, List[AgentRule]] = {}
        self._cache_timestamp: float = 0
        
        # 自定义检查函数
        self._custom_checkers: Dict[str, Callable] = {}
        
        # 加载默认规则
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        # 代码质量规则
        self.add_rule(AgentRule(
            rule_id="rule_no_print",
            name="no_print_statements",
            description="Avoid using print statements in production code",
            rule_type=RuleType.BEHAVIOR.value,
            severity=RuleSeverity.WARNING.value,
            pattern=r"print\s*\(",
            action=ViolationAction.WARN.value,
            message="Consider using logging instead of print statements",
            examples=["print('debug')", "print(variable)"],
            tags=["code_quality", "python"]
        ))
        
        self.add_rule(AgentRule(
            rule_id="rule_no_eval",
            name="no_eval_exec",
            description="Avoid using eval() and exec() for security reasons",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.CRITICAL.value,
            pattern=r"(eval|exec)\s*\(",
            action=ViolationAction.BLOCK.value,
            message="eval() and exec() are security risks and should be avoided",
            examples=["eval(user_input)", "exec(code_string)"],
            tags=["security", "python"]
        ))
        
        self.add_rule(AgentRule(
            rule_id="rule_no_hardcoded_secrets",
            name="no_hardcoded_secrets",
            description="Avoid hardcoding secrets and credentials",
            rule_type=RuleType.SECURITY.value,
            severity=RuleSeverity.CRITICAL.value,
            pattern=r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
            action=ViolationAction.BLOCK.value,
            message="Secrets should be stored in environment variables or secure vaults",
            examples=["password = 'my_password'", "api_key = '12345'"],
            tags=["security", "credentials"]
        ))
        
        # 工具使用规则
        self.add_rule(AgentRule(
            rule_id="rule_approval_required",
            name="approval_required_actions",
            description="Certain actions require user approval",
            rule_type=RuleType.CONSTRAINT.value,
            severity=RuleSeverity.WARNING.value,
            condition="action in ['delete_file', 'execute_command', 'modify_system']",
            action=ViolationAction.ASK_HUMAN.value,
            message="This action requires user approval",
            tags=["approval", "safety"]
        ))
        
        # 工作流规则
        self.add_rule(AgentRule(
            rule_id="rule_test_before_commit",
            name="test_before_commit",
            description="Run tests before committing code",
            rule_type=RuleType.WORKFLOW.value,
            severity=RuleSeverity.WARNING.value,
            condition="action == 'git_commit'",
            action=ViolationAction.WARN.value,
            message="Consider running tests before committing",
            tags=["workflow", "testing"]
        ))
        
        # 文档规则
        self.add_rule(AgentRule(
            rule_id="rule_update_docs",
            name="update_documentation",
            description="Update documentation when modifying code",
            rule_type=RuleType.WORKFLOW.value,
            severity=RuleSeverity.INFO.value,
            condition="action in ['modify_function', 'add_feature']",
            action=ViolationAction.LOG.value,
            message="Consider updating documentation for code changes",
            tags=["documentation", "workflow"]
        ))
    
    def add_rule(self, rule: AgentRule) -> bool:
        """添加规则
        
        Args:
            rule: 规则对象
            
        Returns:
            bool: 是否添加成功
        """
        if rule.rule_id in self._rules:
            logger.warning(f"Rule {rule.rule_id} already exists")
            return False
        
        self._rules[rule.rule_id] = rule
        self._rules_by_name[rule.name] = rule.rule_id
        
        # 清除缓存
        self._rules_cache.clear()
        
        logger.info(f"Added rule: {rule.name} ({rule.rule_id})")
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否移除成功
        """
        if rule_id not in self._rules:
            return False
        
        rule = self._rules[rule_id]
        del self._rules[rule_id]
        
        if rule.name in self._rules_by_name:
            del self._rules_by_name[rule.name]
        
        # 清除缓存
        self._rules_cache.clear()
        
        logger.info(f"Removed rule: {rule.name} ({rule_id})")
        return True
    
    def get_rule(self, rule_id: str) -> Optional[AgentRule]:
        """获取规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            Optional[AgentRule]: 规则对象
        """
        return self._rules.get(rule_id)
    
    def get_rule_by_name(self, name: str) -> Optional[AgentRule]:
        """根据名称获取规则
        
        Args:
            name: 规则名称
            
        Returns:
            Optional[AgentRule]: 规则对象
        """
        rule_id = self._rules_by_name.get(name)
        if rule_id:
            return self._rules.get(rule_id)
        return None
    
    def list_rules(
        self,
        rule_type: Optional[str] = None,
        scope: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[AgentRule]:
        """列出规则
        
        Args:
            rule_type: 规则类型过滤
            scope: 作用域过滤
            enabled_only: 是否只返回启用的规则
            
        Returns:
            List[AgentRule]: 规则列表
        """
        rules = list(self._rules.values())
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        if scope:
            rules = [r for r in rules if r.scope == scope]
        
        return rules
    
    def load_rules_from_file(self, file_path: str) -> int:
        """从文件加载规则
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 加载的规则数量
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Rules file not found: {file_path}")
                return 0
            
            content = path.read_text(encoding='utf-8')
            rules = self._parse_agents_md(content)
            
            for rule in rules:
                self.add_rule(rule)
            
            logger.info(f"Loaded {len(rules)} rules from {file_path}")
            return len(rules)
            
        except Exception as e:
            logger.error(f"Failed to load rules from {file_path}: {e}")
            return 0
    
    def _parse_agents_md(self, content: str) -> List[AgentRule]:
        """解析 AGENTS.md 内容
        
        Args:
            content: AGENTS.md 内容
            
        Returns:
            List[AgentRule]: 规则列表
        """
        rules = []
        
        # 简单的解析逻辑，实际应该更复杂
        lines = content.split('\n')
        current_section = None
        current_rule = None
        
        for line in lines:
            line = line.strip()
            
            # 检测章节标题
            if line.startswith('#'):
                if current_rule:
                    rules.append(current_rule)
                    current_rule = None
                
                section = line.lstrip('#').strip()
                if 'rule' in section.lower() or 'constraint' in section.lower():
                    current_section = section
                else:
                    current_section = None
            
            # 检测规则项
            elif line.startswith('- ') and current_section:
                rule_text = line[2:].strip()
                
                # 解析规则
                rule = self._parse_rule_line(rule_text, current_section)
                if rule:
                    if current_rule:
                        rules.append(current_rule)
                    current_rule = rule
            
            # 规则描述
            elif current_rule and line:
                current_rule.description += f" {line}"
        
        # 添加最后一个规则
        if current_rule:
            rules.append(current_rule)
        
        return rules
    
    def _parse_rule_line(self, line: str, section: str) -> Optional[AgentRule]:
        """解析规则行
        
        Args:
            line: 规则行
            section: 章节名称
            
        Returns:
            Optional[AgentRule]: 规则对象
        """
        # 简单的解析逻辑
        parts = line.split(':', 1)
        if len(parts) < 2:
            return None
        
        name = parts[0].strip()
        description = parts[1].strip()
        
        # 确定规则类型
        rule_type = RuleType.BEHAVIOR.value
        if 'security' in section.lower() or '安全' in section:
            rule_type = RuleType.SECURITY.value
        elif 'constraint' in section.lower() or '约束' in section:
            rule_type = RuleType.CONSTRAINT.value
        elif 'workflow' in section.lower() or '工作流' in section:
            rule_type = RuleType.WORKFLOW.value
        
        # 确定严重程度
        severity = RuleSeverity.WARNING.value
        if '必须' in description or 'must' in description.lower():
            severity = RuleSeverity.ERROR.value
        if '禁止' in description or 'never' in description.lower():
            severity = RuleSeverity.CRITICAL.value
        
        return AgentRule(
            rule_id="",
            name=name.lower().replace(' ', '_'),
            description=description,
            rule_type=rule_type,
            severity=severity,
            message=description
        )
    
    def check_rules(
        self,
        context: RuleContext,
        content: Optional[str] = None,
        action: Optional[str] = None
    ) -> RuleCheckResult:
        """检查规则
        
        Args:
            context: 规则上下文
            content: 要检查的内容
            action: 要执行的动作
            
        Returns:
            RuleCheckResult: 检查结果
        """
        violations = []
        warnings = []
        suggestions = []
        
        # 获取适用的规则
        rules = self._get_applicable_rules(context)
        
        for rule in rules:
            if not rule.enabled:
                continue
            
            # 检查规则
            violation = self._check_rule(rule, context, content, action)
            
            if violation:
                violations.append(violation)
                
                # 根据严重程度添加警告或建议
                if rule.severity in [RuleSeverity.ERROR.value, RuleSeverity.CRITICAL.value]:
                    warnings.append(f"[{rule.severity}] {rule.message}")
                else:
                    suggestions.append(rule.message)
        
        return RuleCheckResult(
            valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _get_applicable_rules(self, context: RuleContext) -> List[AgentRule]:
        """获取适用的规则
        
        Args:
            context: 规则上下文
            
        Returns:
            List[AgentRule]: 适用的规则列表
        """
        # 检查缓存
        cache_key = f"{context.project_path}:{context.current_action}"
        now = time.time()
        
        if cache_key in self._rules_cache:
            if now - self._cache_timestamp < self.config.rules_cache_ttl:
                return self._rules_cache[cache_key]
        
        # 获取所有启用的规则
        rules = self.list_rules(enabled_only=True)
        
        # 按作用域过滤
        applicable_rules = []
        for rule in rules:
            if self._is_rule_applicable(rule, context):
                applicable_rules.append(rule)
        
        # 更新缓存
        self._rules_cache[cache_key] = applicable_rules
        self._cache_timestamp = now
        
        return applicable_rules
    
    def _is_rule_applicable(self, rule: AgentRule, context: RuleContext) -> bool:
        """检查规则是否适用
        
        Args:
            rule: 规则对象
            context: 规则上下文
            
        Returns:
            bool: 是否适用
        """
        # 全局规则总是适用
        if rule.scope == RuleScope.GLOBAL.value:
            return True
        
        # 项目规则
        if rule.scope == RuleScope.PROJECT.value:
            # 检查是否有项目特定的规则
            if context.project_path:
                return True
        
        # 会话规则
        if rule.scope == RuleScope.SESSION.value:
            if context.session_id:
                return True
        
        # 用户规则
        if rule.scope == RuleScope.USER.value:
            if context.user_id:
                return True
        
        return True
    
    def _check_rule(
        self,
        rule: AgentRule,
        context: RuleContext,
        content: Optional[str] = None,
        action: Optional[str] = None
    ) -> Optional[RuleViolation]:
        """检查单个规则
        
        Args:
            rule: 规则对象
            context: 规则上下文
            content: 要检查的内容
            action: 要执行的动作
            
        Returns:
            Optional[RuleViolation]: 违规记录（如果有）
        """
        # 模式匹配检查
        if rule.pattern and content:
            if re.search(rule.pattern, content):
                return self._create_violation(rule, context, content)
        
        # 条件检查
        if rule.condition:
            if self._evaluate_condition(rule.condition, context, action):
                return self._create_violation(rule, context, action)
        
        # 自定义检查器
        if rule.rule_id in self._custom_checkers:
            checker = self._custom_checkers[rule.rule_id]
            if checker(rule, context, content, action):
                return self._create_violation(rule, context, content or action)
        
        return None
    
    def _evaluate_condition(
        self,
        condition: str,
        context: RuleContext,
        action: Optional[str] = None
    ) -> bool:
        """评估条件表达式
        
        Args:
            condition: 条件表达式
            context: 规则上下文
            action: 动作
            
        Returns:
            bool: 条件是否满足
        """
        try:
            # 简单的条件评估
            # 实际应该使用更安全的表达式解析器
            
            # 替换变量
            condition = condition.replace("action", f"'{action or context.current_action}'")
            condition = condition.replace("tool", f"'{context.tool_name}'")
            
            # 评估条件
            return eval(condition)
            
        except Exception as e:
            logger.warning(f"Failed to evaluate condition: {condition}, error: {e}")
            return False
    
    def _create_violation(
        self,
        rule: AgentRule,
        context: RuleContext,
        details: Any
    ) -> RuleViolation:
        """创建违规记录
        
        Args:
            rule: 规则对象
            context: 规则上下文
            details: 详细信息
            
        Returns:
            RuleViolation: 违规记录
        """
        violation = RuleViolation(
            violation_id="",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            timestamp=time.time(),
            context={
                "user_id": context.user_id,
                "session_id": context.session_id,
                "project_path": context.project_path,
                "current_file": context.current_file,
                "current_action": context.current_action,
                "tool_name": context.tool_name
            },
            details=str(details),
            severity=rule.severity,
            action_taken=rule.action
        )
        
        # 记录违规
        self._violations.append(violation)
        
        # 限制违规记录数量
        if len(self._violations) > self.config.max_violations:
            self._violations = self._violations[-self.config.max_violations:]
        
        logger.warning(
            f"Rule violation: {rule.name} - {rule.message} "
            f"(severity: {rule.severity}, action: {rule.action})"
        )
        
        return violation
    
    def register_custom_checker(
        self,
        rule_id: str,
        checker: Callable[[AgentRule, RuleContext, Optional[str], Optional[str]], bool]
    ):
        """注册自定义检查器
        
        Args:
            rule_id: 规则 ID
            checker: 检查函数
        """
        self._custom_checkers[rule_id] = checker
        logger.info(f"Registered custom checker for rule: {rule_id}")
    
    def get_violations(
        self,
        rule_id: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[RuleViolation]:
        """获取违规记录
        
        Args:
            rule_id: 规则 ID 过滤
            severity: 严重程度过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[RuleViolation]: 违规记录列表
        """
        violations = self._violations
        
        if rule_id:
            violations = [v for v in violations if v.rule_id == rule_id]
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        if start_time:
            violations = [v for v in violations if v.timestamp >= start_time]
        
        if end_time:
            violations = [v for v in violations if v.timestamp <= end_time]
        
        # 按时间倒序排列
        violations.sort(key=lambda v: v.timestamp, reverse=True)
        
        return violations[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_rules": len(self._rules),
            "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
            "total_violations": len(self._violations),
            "rules_by_type": self._count_by_type(),
            "rules_by_severity": self._count_by_severity(),
            "violations_by_severity": self._count_violations_by_severity()
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """按类型统计规则"""
        counts = {}
        for rule in self._rules.values():
            counts[rule.rule_type] = counts.get(rule.rule_type, 0) + 1
        return counts
    
    def _count_by_severity(self) -> Dict[str, int]:
        """按严重程度统计规则"""
        counts = {}
        for rule in self._rules.values():
            counts[rule.severity] = counts.get(rule.severity, 0) + 1
        return counts
    
    def _count_violations_by_severity(self) -> Dict[str, int]:
        """按严重程度统计违规"""
        counts = {}
        for violation in self._violations:
            counts[violation.severity] = counts.get(violation.severity, 0) + 1
        return counts
    
    def clear(self):
        """清空所有规则和违规记录"""
        self._rules.clear()
        self._rules_by_name.clear()
        self._violations.clear()
        self._rules_cache.clear()
        self._custom_checkers.clear()
        logger.info("Rule engine cleared")
