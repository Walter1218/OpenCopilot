# security_module/audit_logger.py

"""
审计日志器

负责记录安全相关的操作日志，用于安全审计和问题追踪。
"""

import time
import logging
import json
from typing import Dict, List, Optional, Any
from collections import deque

from .models import AuditEntry, AuditAction

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志器
    
    记录安全相关的操作日志，支持：
    - 日志记录
    - 日志查询
    - 日志过滤
    - 日志导出
    """
    
    def __init__(self, max_entries: int = 10000):
        """
        初始化审计日志器
        
        Args:
            max_entries: 最大日志条目数
        """
        self._entries: deque = deque(maxlen=max_entries)
        self._max_entries = max_entries
        
        # 统计信息
        self._stats = {
            "total_entries": 0,
            "entries_by_action": {},
            "entries_by_user": {},
            "entries_by_resource": {}
        }
    
    def log(
        self,
        user_id: str,
        action: str,
        resource: str,
        parameters: Optional[Dict[str, Any]] = None,
        result: str = "",
        ip_address: str = "",
        user_agent: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """记录审计日志
        
        Args:
            user_id: 用户 ID
            action: 操作类型
            resource: 资源
            parameters: 操作参数
            result: 操作结果
            ip_address: IP 地址
            user_agent: 用户代理
            metadata: 元数据
            
        Returns:
            AuditEntry: 审计条目
        """
        entry = AuditEntry(
            entry_id="",
            timestamp=time.time(),
            user_id=user_id,
            action=action,
            resource=resource,
            parameters=parameters or {},
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        self._entries.append(entry)
        self._update_stats(entry)
        
        logger.info(
            f"Audit log: user={user_id}, action={action}, "
            f"resource={resource}, result={result}"
        )
        
        return entry
    
    def log_permission_check(
        self,
        user_id: str,
        resource: str,
        action: str,
        granted: bool,
        ip_address: str = ""
    ) -> AuditEntry:
        """记录权限检查日志
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            granted: 是否授权
            ip_address: IP 地址
            
        Returns:
            AuditEntry: 审计条目
        """
        return self.log(
            user_id=user_id,
            action=AuditAction.PERMISSION_CHECK.value,
            resource=resource,
            parameters={"action": action},
            result="granted" if granted else "denied",
            ip_address=ip_address
        )
    
    def log_approval_request(
        self,
        requester_id: str,
        action: str,
        resource: str,
        request_id: str,
        urgency: str = "medium"
    ) -> AuditEntry:
        """记录审批请求日志
        
        Args:
            requester_id: 请求者 ID
            action: 动作
            resource: 资源
            request_id: 请求 ID
            urgency: 紧急程度
            
        Returns:
            AuditEntry: 审计条目
        """
        return self.log(
            user_id=requester_id,
            action=AuditAction.APPROVAL_REQUEST.value,
            resource=resource,
            parameters={
                "request_id": request_id,
                "requested_action": action,
                "urgency": urgency
            }
        )
    
    def log_approval_decision(
        self,
        approver_id: str,
        request_id: str,
        approved: bool,
        reason: str = ""
    ) -> AuditEntry:
        """记录审批决定日志
        
        Args:
            approver_id: 审批者 ID
            request_id: 请求 ID
            approved: 是否批准
            reason: 原因
            
        Returns:
            AuditEntry: 审计条目
        """
        action = AuditAction.APPROVAL_APPROVE if approved else AuditAction.APPROVAL_REJECT
        
        return self.log(
            user_id=approver_id,
            action=action.value,
            resource="approval",
            parameters={
                "request_id": request_id,
                "approved": approved,
                "reason": reason
            }
        )
    
    def log_rate_limit_check(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        current_count: int,
        max_count: int
    ) -> AuditEntry:
        """记录速率限制检查日志
        
        Args:
            user_id: 用户 ID
            resource: 资源
            action: 动作
            allowed: 是否允许
            current_count: 当前请求数
            max_count: 最大请求数
            
        Returns:
            AuditEntry: 审计条目
        """
        return self.log(
            user_id=user_id,
            action=AuditAction.RATE_LIMIT_CHECK.value,
            resource=resource,
            parameters={
                "action": action,
                "current_count": current_count,
                "max_count": max_count
            },
            result="allowed" if allowed else "blocked"
        )
    
    def log_security_violation(
        self,
        user_id: str,
        violation_type: str,
        details: Dict[str, Any],
        ip_address: str = ""
    ) -> AuditEntry:
        """记录安全违规日志
        
        Args:
            user_id: 用户 ID
            violation_type: 违规类型
            details: 详细信息
            ip_address: IP 地址
            
        Returns:
            AuditEntry: 审计条目
        """
        return self.log(
            user_id=user_id,
            action=AuditAction.SECURITY_VIOLATION.value,
            resource="security",
            parameters={
                "violation_type": violation_type,
                "details": details
            },
            ip_address=ip_address,
            metadata={"severity": "high"}
        )
    
    def get_entries(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """获取审计日志
        
        Args:
            user_id: 用户 ID 过滤
            action: 操作类型过滤
            resource: 资源过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[AuditEntry]: 审计条目列表
        """
        entries = list(self._entries)
        
        # 应用过滤器
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        
        if action:
            entries = [e for e in entries if e.action == action]
        
        if resource:
            entries = [e for e in entries if e.resource == resource]
        
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        # 按时间倒序排列
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries[:limit]
    
    def get_entry_by_id(self, entry_id: str) -> Optional[AuditEntry]:
        """根据 ID 获取审计条目
        
        Args:
            entry_id: 条目 ID
            
        Returns:
            Optional[AuditEntry]: 审计条目
        """
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_entries": self._stats["total_entries"],
            "entries_by_action": dict(self._stats["entries_by_action"]),
            "entries_by_user": dict(self._stats["entries_by_user"]),
            "entries_by_resource": dict(self._stats["entries_by_resource"]),
            "current_entries": len(self._entries)
        }
    
    def _update_stats(self, entry: AuditEntry):
        """更新统计信息
        
        Args:
            entry: 审计条目
        """
        self._stats["total_entries"] += 1
        
        # 按操作类型统计
        action = entry.action
        self._stats["entries_by_action"][action] = \
            self._stats["entries_by_action"].get(action, 0) + 1
        
        # 按用户统计
        user = entry.user_id
        self._stats["entries_by_user"][user] = \
            self._stats["entries_by_user"].get(user, 0) + 1
        
        # 按资源统计
        resource = entry.resource
        self._stats["entries_by_resource"][resource] = \
            self._stats["entries_by_resource"].get(resource, 0) + 1
    
    def clear(self):
        """清空审计日志"""
        self._entries.clear()
        self._stats = {
            "total_entries": 0,
            "entries_by_action": {},
            "entries_by_user": {},
            "entries_by_resource": {}
        }
        logger.info("Audit log cleared")
    
    def export_json(self, limit: Optional[int] = None) -> str:
        """导出审计日志为 JSON
        
        Args:
            limit: 导出数量限制
            
        Returns:
            str: JSON 字符串
        """
        entries = list(self._entries)
        
        if limit:
            entries = entries[-limit:]
        
        data = [
            {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp,
                "user_id": e.user_id,
                "action": e.action,
                "resource": e.resource,
                "parameters": e.parameters,
                "result": e.result,
                "ip_address": e.ip_address,
                "user_agent": e.user_agent,
                "metadata": e.metadata
            }
            for e in entries
        ]
        
        return json.dumps(data, indent=2, default=str)
