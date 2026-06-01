# security_module/rate_limiter.py

"""
速率限制器

负责限制用户或系统的请求频率，防止滥用。
"""

import time
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import RateLimitRule, RateLimitState

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器
    
    限制用户或系统的请求频率，支持：
    - 基于用户的速率限制
    - 基于资源的速率限制
    - 滑动窗口算法
    - 自定义规则
    """
    
    def __init__(self):
        """初始化速率限制器"""
        # 速率限制规则: rule_id -> RateLimitRule
        self._rules: Dict[str, RateLimitRule] = {}
        
        # 速率限制状态: (user_id, resource, action) -> RateLimitState
        self._states: Dict[tuple, RateLimitState] = defaultdict(
            lambda: RateLimitState(resource="", action="")
        )
        
        # 默认规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认规则"""
        # API 调用限制
        self.add_rule(RateLimitRule(
            rule_id="rule_api_calls",
            resource="api",
            action="call",
            max_requests=100,
            time_window=60.0,
            description="API call rate limit"
        ))
        
        # 工具执行限制
        self.add_rule(RateLimitRule(
            rule_id="rule_tool_execute",
            resource="tool",
            action="execute",
            max_requests=50,
            time_window=60.0,
            description="Tool execution rate limit"
        ))
        
        # 代码执行限制
        self.add_rule(RateLimitRule(
            rule_id="rule_code_execute",
            resource="code",
            action="execute",
            max_requests=20,
            time_window=60.0,
            description="Code execution rate limit"
        ))
        
        # 文件操作限制
        self.add_rule(RateLimitRule(
            rule_id="rule_file_operations",
            resource="file",
            action="write",
            max_requests=30,
            time_window=60.0,
            description="File write rate limit"
        ))
        
        # 审批请求限制
        self.add_rule(RateLimitRule(
            rule_id="rule_approval_requests",
            resource="approval",
            action="request",
            max_requests=10,
            time_window=60.0,
            description="Approval request rate limit"
        ))
    
    def add_rule(self, rule: RateLimitRule) -> bool:
        """添加速率限制规则
        
        Args:
            rule: 规则对象
            
        Returns:
            bool: 是否添加成功
        """
        if rule.rule_id in self._rules:
            logger.warning(f"Rule {rule.rule_id} already exists")
            return False
        
        self._rules[rule.rule_id] = rule
        logger.info(f"Added rate limit rule: {rule.rule_id}")
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除速率限制规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            bool: 是否移除成功
        """
        if rule_id not in self._rules:
            return False
        
        del self._rules[rule_id]
        logger.info(f"Removed rate limit rule: {rule_id}")
        return True
    
    def get_rule(self, rule_id: str) -> Optional[RateLimitRule]:
        """获取规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            Optional[RateLimitRule]: 规则对象
        """
        return self._rules.get(rule_id)
    
    def list_rules(self) -> List[RateLimitRule]:
        """列出所有规则
        
        Returns:
            List[RateLimitRule]: 规则列表
        """
        return list(self._rules.values())
    
    def check_rate_limit(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> tuple[bool, Dict[str, Any]]:
        """检查速率限制
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            
        Returns:
            tuple: (是否允许, 详细信息)
        """
        # 查找匹配的规则
        rule = self._find_rule(resource, action)
        if not rule:
            # 没有匹配的规则，允许请求
            return True, {"rule": None, "allowed": True}
        
        # 获取状态
        state_key = (user_id, resource, action)
        state = self._states[state_key]
        state.resource = resource
        state.action = action
        
        # 清理过期请求
        state.cleanup(rule.time_window)
        
        # 检查是否超过限制
        current_count = state.get_request_count()
        allowed = current_count < rule.max_requests
        
        # 构建详细信息
        info = {
            "rule": rule.rule_id,
            "resource": resource,
            "action": action,
            "current_count": current_count,
            "max_requests": rule.max_requests,
            "time_window": rule.time_window,
            "allowed": allowed,
            "remaining": max(0, rule.max_requests - current_count)
        }
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{resource}.{action} ({current_count}/{rule.max_requests})"
            )
        
        return allowed, info
    
    def record_request(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> bool:
        """记录请求
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            
        Returns:
            bool: 是否记录成功
        """
        # 查找匹配的规则
        rule = self._find_rule(resource, action)
        if not rule:
            # 没有匹配的规则，不记录
            return True
        
        # 获取状态
        state_key = (user_id, resource, action)
        state = self._states[state_key]
        state.resource = resource
        state.action = action
        
        # 清理过期请求
        state.cleanup(rule.time_window)
        
        # 检查是否超过限制
        if state.get_request_count() >= rule.max_requests:
            return False
        
        # 记录请求
        state.add_request()
        
        return True
    
    def _find_rule(self, resource: str, action: str) -> Optional[RateLimitRule]:
        """查找匹配的规则
        
        Args:
            resource: 资源
            action: 动作
            
        Returns:
            Optional[RateLimitRule]: 匹配的规则
        """
        # 精确匹配
        for rule in self._rules.values():
            if rule.resource == resource and rule.action == action:
                return rule
        
        # 通配符匹配
        for rule in self._rules.values():
            if rule.resource == "*" and rule.action == action:
                return rule
            if rule.resource == resource and rule.action == "*":
                return rule
            if rule.resource == "*" and rule.action == "*":
                return rule
        
        return None
    
    def get_user_state(
        self,
        user_id: str,
        resource: str,
        action: str
    ) -> Dict[str, Any]:
        """获取用户速率限制状态
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            
        Returns:
            Dict[str, Any]: 状态信息
        """
        state_key = (user_id, resource, action)
        state = self._states.get(state_key)
        
        if not state:
            return {
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "request_count": 0
            }
        
        # 查找规则
        rule = self._find_rule(resource, action)
        
        # 清理过期请求
        if rule:
            state.cleanup(rule.time_window)
        
        return {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "request_count": state.get_request_count(),
            "rule": rule.rule_id if rule else None,
            "max_requests": rule.max_requests if rule else None,
            "time_window": rule.time_window if rule else None
        }
    
    def get_all_user_states(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有速率限制状态
        
        Args:
            user_id: 用户 ID
            
        Returns:
            List[Dict[str, Any]]: 状态列表
        """
        states = []
        
        for (uid, resource, action), state in self._states.items():
            if uid == user_id:
                # 查找规则
                rule = self._find_rule(resource, action)
                
                # 清理过期请求
                if rule:
                    state.cleanup(rule.time_window)
                
                states.append({
                    "user_id": uid,
                    "resource": resource,
                    "action": action,
                    "request_count": state.get_request_count(),
                    "rule": rule.rule_id if rule else None,
                    "max_requests": rule.max_requests if rule else None,
                    "time_window": rule.time_window if rule else None
                })
        
        return states
    
    def reset_user_state(
        self,
        user_id: str,
        resource: Optional[str] = None,
        action: Optional[str] = None
    ) -> int:
        """重置用户速率限制状态
        
        Args:
            user_id: 用户 ID
            resource: 资源（可选）
            action: 动作（可选）
            
        Returns:
            int: 重置的状态数量
        """
        reset_count = 0
        
        keys_to_remove = []
        
        for (uid, res, act) in self._states.keys():
            if uid == user_id:
                if resource is None or res == resource:
                    if action is None or act == action:
                        keys_to_remove.append((uid, res, act))
                        reset_count += 1
        
        for key in keys_to_remove:
            del self._states[key]
        
        if reset_count > 0:
            logger.info(f"Reset {reset_count} rate limit states for user {user_id}")
        
        return reset_count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        total_rules = len(self._rules)
        total_states = len(self._states)
        
        # 统计活跃用户
        active_users = set()
        for (uid, _, _) in self._states.keys():
            active_users.add(uid)
        
        return {
            "total_rules": total_rules,
            "total_states": total_states,
            "active_users": len(active_users)
        }
    
    def clear(self):
        """清空所有状态"""
        self._states.clear()
        logger.info("Rate limiter states cleared")
