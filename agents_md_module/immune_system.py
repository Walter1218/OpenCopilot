# agents_md_module/immune_system.py

"""
免疫系统

负责协调规则引擎和其他模块，提供统一的免疫机制接口。
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable

from .models import (
    AgentsMdConfig, AgentRule, RuleViolation, RuleContext,
    RuleCheckResult, ImmuneResponse, ViolationAction
)
from .rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class ImmuneSystem:
    """免疫系统
    
    协调规则引擎和其他模块，提供统一的免疫机制接口，支持：
    - 行为检查
    - 违规处理
    - 自动修复
    - 人工介入
    """
    
    def __init__(self, config: Optional[AgentsMdConfig] = None):
        """
        初始化免疫系统
        
        Args:
            config: AGENTS.md 配置
        """
        self.config = config or AgentsMdConfig()
        
        # 初始化规则引擎
        self.rule_engine = RuleEngine(self.config)
        
        # 自动修复处理器
        self._auto_fix_handlers: Dict[str, Callable] = {}
        
        # 人工介入处理器
        self._human_intervention_handler: Optional[Callable] = None
        
        # 统计信息
        self._stats = {
            "total_checks": 0,
            "violations_detected": 0,
            "actions_blocked": 0,
            "auto_fixes_applied": 0,
            "human_interventions": 0
        }
    
    def set_human_intervention_handler(self, handler: Callable):
        """设置人工介入处理器
        
        Args:
            handler: 处理器函数
        """
        self._human_intervention_handler = handler
    
    def register_auto_fix_handler(
        self,
        rule_id: str,
        handler: Callable[[RuleViolation, Any], Any]
    ):
        """注册自动修复处理器
        
        Args:
            rule_id: 规则 ID
            handler: 处理器函数
        """
        self._auto_fix_handlers[rule_id] = handler
        logger.info(f"Registered auto-fix handler for rule: {rule_id}")
    
    async def check_action(
        self,
        context: RuleContext,
        action: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ImmuneResponse:
        """检查动作
        
        Args:
            context: 规则上下文
            action: 要执行的动作
            parameters: 动作参数
            
        Returns:
            ImmuneResponse: 免疫响应
        """
        # 更新统计
        self._stats["total_checks"] += 1
        
        # 更新上下文
        context.current_action = action
        if parameters:
            context.parameters = parameters
        
        # 检查规则
        result = self.rule_engine.check_rules(
            context=context,
            action=action
        )
        
        # 处理违规
        if result.has_violations:
            return await self._handle_violations(result, context)
        
        # 没有违规，允许执行
        return ImmuneResponse(
            allowed=True,
            message="Action allowed",
            suggestions=result.suggestions
        )
    
    async def check_content(
        self,
        context: RuleContext,
        content: str
    ) -> ImmuneResponse:
        """检查内容
        
        Args:
            context: 规则上下文
            content: 要检查的内容
            
        Returns:
            ImmuneResponse: 免疫响应
        """
        # 更新统计
        self._stats["total_checks"] += 1
        
        # 检查规则
        result = self.rule_engine.check_rules(
            context=context,
            content=content
        )
        
        # 处理违规
        if result.has_violations:
            return await self._handle_violations(result, context)
        
        # 没有违规，允许执行
        return ImmuneResponse(
            allowed=True,
            message="Content allowed",
            suggestions=result.suggestions
        )
    
    async def _handle_violations(
        self,
        result: RuleCheckResult,
        context: RuleContext
    ) -> ImmuneResponse:
        """处理违规
        
        Args:
            result: 检查结果
            context: 规则上下文
            
        Returns:
            ImmuneResponse: 免疫响应
        """
        # 更新统计
        self._stats["violations_detected"] += len(result.violations)
        
        # 按严重程度排序违规
        sorted_violations = sorted(
            result.violations,
            key=lambda v: self._get_severity_order(v.severity),
            reverse=True
        )
        
        # 处理最严重的违规
        most_severe = sorted_violations[0]
        
        # 根据违规动作处理
        if most_severe.action_taken == ViolationAction.BLOCK.value:
            # 阻止执行
            self._stats["actions_blocked"] += 1
            
            return ImmuneResponse(
                allowed=False,
                violations=sorted_violations,
                message=f"Action blocked: {most_severe.rule_name}",
                suggestions=result.suggestions
            )
        
        elif most_severe.action_taken == ViolationAction.ASK_HUMAN.value:
            # 询问人工
            self._stats["human_interventions"] += 1
            
            if self._human_intervention_handler:
                # 调用人工介入处理器
                approved = await self._request_human_approval(
                    most_severe, context
                )
                
                if approved:
                    return ImmuneResponse(
                        allowed=True,
                        violations=sorted_violations,
                        message="Action approved by human",
                        suggestions=result.suggestions
                    )
                else:
                    return ImmuneResponse(
                        allowed=False,
                        violations=sorted_violations,
                        message="Action rejected by human",
                        suggestions=result.suggestions
                    )
            else:
                # 没有人工处理器，记录警告
                logger.warning(
                    f"Human intervention required but no handler registered: "
                    f"{most_severe.rule_name}"
                )
                
                return ImmuneResponse(
                    allowed=True,  # 默认允许
                    violations=sorted_violations,
                    message="Action allowed (no human handler)",
                    suggestions=result.suggestions
                )
        
        elif most_severe.action_taken == ViolationAction.AUTO_FIX.value:
            # 自动修复
            if self.config.enable_auto_fix:
                fixed = await self._apply_auto_fix(most_severe, context)
                
                if fixed:
                    self._stats["auto_fixes_applied"] += 1
                    
                    return ImmuneResponse(
                        allowed=True,
                        violations=sorted_violations,
                        message="Action allowed after auto-fix",
                        auto_fix_applied=True,
                        suggestions=result.suggestions
                    )
        
        # 默认：记录警告但允许执行
        return ImmuneResponse(
            allowed=True,
            violations=sorted_violations,
            message="Action allowed with warnings",
            suggestions=result.suggestions
        )
    
    def _get_severity_order(self, severity: str) -> int:
        """获取严重程度排序
        
        Args:
            severity: 严重程度
            
        Returns:
            int: 排序值
        """
        order = {
            "info": 0,
            "warning": 1,
            "error": 2,
            "critical": 3
        }
        return order.get(severity, 0)
    
    async def _request_human_approval(
        self,
        violation: RuleViolation,
        context: RuleContext
    ) -> bool:
        """请求人工批准
        
        Args:
            violation: 违规记录
            context: 规则上下文
            
        Returns:
            bool: 是否批准
        """
        if not self._human_intervention_handler:
            return True
        
        try:
            if asyncio.iscoroutinefunction(self._human_intervention_handler):
                return await self._human_intervention_handler(violation, context)
            else:
                return self._human_intervention_handler(violation, context)
        except Exception as e:
            logger.error(f"Human intervention handler error: {e}")
            return True
    
    async def _apply_auto_fix(
        self,
        violation: RuleViolation,
        context: RuleContext
    ) -> bool:
        """应用自动修复
        
        Args:
            violation: 违规记录
            context: 规则上下文
            
        Returns:
            bool: 是否修复成功
        """
        handler = self._auto_fix_handlers.get(violation.rule_id)
        if not handler:
            logger.warning(
                f"No auto-fix handler for rule: {violation.rule_id}"
            )
            return False
        
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(violation, context)
            else:
                return handler(violation, context)
        except Exception as e:
            logger.error(f"Auto-fix handler error: {e}")
            return False
    
    def load_rules_from_file(self, file_path: str) -> int:
        """从文件加载规则
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 加载的规则数量
        """
        return self.rule_engine.load_rules_from_file(file_path)
    
    def add_rule(self, rule: AgentRule) -> bool:
        """添加规则
        
        Args:
            rule: 规则对象
            
        Returns:
            bool: 是否添加成功
        """
        return self.rule_engine.add_rule(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否移除成功
        """
        return self.rule_engine.remove_rule(rule_id)
    
    def get_rule(self, rule_id: str) -> Optional[AgentRule]:
        """获取规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            Optional[AgentRule]: 规则对象
        """
        return self.rule_engine.get_rule(rule_id)
    
    def list_rules(self, **kwargs) -> List[AgentRule]:
        """列出规则
        
        Returns:
            List[AgentRule]: 规则列表
        """
        return self.rule_engine.list_rules(**kwargs)
    
    def get_violations(self, **kwargs) -> List[RuleViolation]:
        """获取违规记录
        
        Returns:
            List[RuleViolation]: 违规记录列表
        """
        return self.rule_engine.get_violations(**kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = self._stats.copy()
        stats.update(self.rule_engine.get_stats())
        return stats
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "enabled": self.config.enabled,
            "stats": self.get_stats(),
            "config": {
                "default_action": self.config.default_action,
                "enable_auto_fix": self.config.enable_auto_fix,
                "enable_inheritance": self.config.enable_inheritance,
                "max_violations": self.config.max_violations,
                "rules_cache_ttl": self.config.rules_cache_ttl
            }
        }
    
    def clear(self):
        """清空所有数据"""
        self.rule_engine.clear()
        self._auto_fix_handlers.clear()
        self._stats = {
            "total_checks": 0,
            "violations_detected": 0,
            "actions_blocked": 0,
            "auto_fixes_applied": 0,
            "human_interventions": 0
        }
        logger.info("Immune system cleared")


# 导入 asyncio 用于异步函数检查
import asyncio
