# security_module/approval_engine.py

"""
审批引擎

负责管理审批流程，包括创建审批请求、处理审批决定等。
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .models import (
    ApprovalRequest, ApprovalStatus, UrgencyLevel,
    HumanResponse, SecurityConfig
)

logger = logging.getLogger(__name__)


class ApprovalEngine:
    """审批引擎
    
    管理审批流程，支持：
    - 创建审批请求
    - 处理审批决定
    - 超时处理
    - 回调通知
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        初始化审批引擎
        
        Args:
            config: 安全配置
        """
        self.config = config or SecurityConfig()
        
        # 审批请求存储: request_id -> ApprovalRequest
        self._requests: Dict[str, ApprovalRequest] = {}
        
        # 等待审批的请求队列
        self._pending_queue: asyncio.Queue = asyncio.Queue()
        
        # 审批回调函数
        self._approval_callbacks: Dict[str, Callable] = {}
        
        # 审批处理器（用于 HITL）
        self._approval_handler: Optional[Callable] = None
        
        # 统计信息
        self._stats = {
            "total_requests": 0,
            "approved": 0,
            "rejected": 0,
            "expired": 0,
            "pending": 0
        }
    
    def set_approval_handler(self, handler: Callable):
        """设置审批处理器
        
        Args:
            handler: 审批处理器函数
        """
        self._approval_handler = handler
    
    async def create_request(
        self,
        requester_id: str,
        action: str,
        resource: str,
        parameters: Optional[Dict[str, Any]] = None,
        reason: str = "",
        urgency: str = UrgencyLevel.MEDIUM.value,
        timeout: Optional[float] = None
    ) -> ApprovalRequest:
        """创建审批请求
        
        Args:
            requester_id: 请求者 ID
            action: 请求的动作
            resource: 资源
            parameters: 参数
            reason: 原因
            urgency: 紧急程度
            timeout: 超时时间（秒）
            
        Returns:
            ApprovalRequest: 审批请求
        """
        # 计算过期时间
        actual_timeout = timeout or self.config.default_approval_timeout
        expires_at = time.time() + actual_timeout
        
        # 创建请求
        request = ApprovalRequest(
            request_id="",
            requester_id=requester_id,
            action=action,
            resource=resource,
            parameters=parameters or {},
            reason=reason,
            urgency=urgency,
            expires_at=expires_at
        )
        
        # 存储请求
        self._requests[request.request_id] = request
        
        # 添加到待处理队列
        await self._pending_queue.put(request.request_id)
        
        # 更新统计
        self._stats["total_requests"] += 1
        self._stats["pending"] += 1
        
        logger.info(
            f"Created approval request: {request.request_id}, "
            f"action={action}, resource={resource}, urgency={urgency}"
        )
        
        # 如果设置了审批处理器，自动触发
        if self._approval_handler:
            asyncio.create_task(self._auto_process_request(request))
        
        return request
    
    async def _auto_process_request(self, request: ApprovalRequest):
        """自动处理审批请求
        
        Args:
            request: 审批请求
        """
        try:
            # 调用审批处理器
            if asyncio.iscoroutinefunction(self._approval_handler):
                approved = await self._approval_handler(request)
            else:
                approved = self._approval_handler(request)
            
            # 处理结果
            if approved:
                await self.approve(request.request_id, "auto_approver")
            else:
                await self.reject(request.request_id, "auto_approver", "Auto-rejected")
                
        except Exception as e:
            logger.error(f"Error in auto-approval handler: {e}")
            await self.reject(request.request_id, "system", f"Error: {str(e)}")
    
    async def approve(
        self,
        request_id: str,
        approver_id: str
    ) -> bool:
        """批准请求
        
        Args:
            request_id: 请求 ID
            approver_id: 审批者 ID
            
        Returns:
            bool: 是否批准成功
        """
        request = self._requests.get(request_id)
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        # 检查是否已处理
        if request.status != ApprovalStatus.PENDING.value:
            logger.warning(f"Request already processed: {request_id}, status={request.status}")
            return False
        
        # 检查是否过期
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED.value
            self._stats["expired"] += 1
            self._stats["pending"] -= 1
            logger.warning(f"Request expired: {request_id}")
            return False
        
        # 批准请求
        request.approve(approver_id)
        
        # 更新统计
        self._stats["approved"] += 1
        self._stats["pending"] -= 1
        
        logger.info(f"Approved request: {request_id} by {approver_id}")
        
        # 触发回调
        await self._trigger_callback(request_id, True)
        
        return True
    
    async def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str = ""
    ) -> bool:
        """拒绝请求
        
        Args:
            request_id: 请求 ID
            approver_id: 审批者 ID
            reason: 拒绝原因
            
        Returns:
            bool: 是否拒绝成功
        """
        request = self._requests.get(request_id)
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        # 检查是否已处理
        if request.status != ApprovalStatus.PENDING.value:
            logger.warning(f"Request already processed: {request_id}, status={request.status}")
            return False
        
        # 检查是否过期
        if request.is_expired():
            request.status = ApprovalStatus.EXPIRED.value
            self._stats["expired"] += 1
            self._stats["pending"] -= 1
            logger.warning(f"Request expired: {request_id}")
            return False
        
        # 拒绝请求
        request.reject(approver_id, reason)
        
        # 更新统计
        self._stats["rejected"] += 1
        self._stats["pending"] -= 1
        
        logger.info(f"Rejected request: {request_id} by {approver_id}, reason: {reason}")
        
        # 触发回调
        await self._trigger_callback(request_id, False)
        
        return True
    
    async def wait_for_decision(
        self,
        request_id: str,
        timeout: Optional[float] = None
    ) -> Optional[ApprovalRequest]:
        """等待审批决定
        
        Args:
            request_id: 请求 ID
            timeout: 超时时间（秒）
            
        Returns:
            Optional[ApprovalRequest]: 审批请求（如果已决定）
        """
        request = self._requests.get(request_id)
        if not request:
            return None
        
        # 如果已决定，直接返回
        if request.status != ApprovalStatus.PENDING.value:
            return request
        
        # 等待决定
        actual_timeout = timeout or self.config.default_approval_timeout
        start_time = time.time()
        
        while time.time() - start_time < actual_timeout:
            # 检查是否过期
            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED.value
                self._stats["expired"] += 1
                self._stats["pending"] -= 1
                return request
            
            # 检查状态
            if request.status != ApprovalStatus.PENDING.value:
                return request
            
            # 等待一段时间
            await asyncio.sleep(0.1)
        
        # 超时处理
        if request.status == ApprovalStatus.PENDING.value:
            request.status = ApprovalStatus.EXPIRED.value
            self._stats["expired"] += 1
            self._stats["pending"] -= 1
            logger.warning(f"Request timed out: {request_id}")
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取审批请求
        
        Args:
            request_id: 请求 ID
            
        Returns:
            Optional[ApprovalRequest]: 审批请求
        """
        return self._requests.get(request_id)
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """获取待处理的请求
        
        Returns:
            List[ApprovalRequest]: 待处理请求列表
        """
        return [
            req for req in self._requests.values()
            if req.status == ApprovalStatus.PENDING.value and not req.is_expired()
        ]
    
    def get_requests_by_requester(self, requester_id: str) -> List[ApprovalRequest]:
        """获取指定请求者的请求
        
        Args:
            requester_id: 请求者 ID
            
        Returns:
            List[ApprovalRequest]: 请求列表
        """
        return [
            req for req in self._requests.values()
            if req.requester_id == requester_id
        ]
    
    def get_requests_by_approver(self, approver_id: str) -> List[ApprovalRequest]:
        """获取指定审批者的请求
        
        Args:
            approver_id: 审批者 ID
            
        Returns:
            List[ApprovalRequest]: 请求列表
        """
        return [
            req for req in self._requests.values()
            if req.approver_id == approver_id
        ]
    
    def register_callback(
        self,
        request_id: str,
        callback: Callable[[str, bool], Awaitable[None]]
    ):
        """注册审批回调
        
        Args:
            request_id: 请求 ID
            callback: 回调函数
        """
        self._approval_callbacks[request_id] = callback
    
    async def _trigger_callback(self, request_id: str, approved: bool):
        """触发审批回调
        
        Args:
            request_id: 请求 ID
            approved: 是否批准
        """
        callback = self._approval_callbacks.get(request_id)
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(request_id, approved)
                else:
                    callback(request_id, approved)
            except Exception as e:
                logger.error(f"Error in callback for {request_id}: {e}")
            finally:
                # 清理回调
                del self._approval_callbacks[request_id]
    
    def cleanup_expired(self):
        """清理过期的请求"""
        expired_ids = []
        
        for request_id, request in self._requests.items():
            if request.status == ApprovalStatus.PENDING.value and request.is_expired():
                request.status = ApprovalStatus.EXPIRED.value
                expired_ids.append(request_id)
                self._stats["expired"] += 1
                self._stats["pending"] -= 1
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired requests")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_requests": self._stats["total_requests"],
            "approved": self._stats["approved"],
            "rejected": self._stats["rejected"],
            "expired": self._stats["expired"],
            "pending": self._stats["pending"],
            "current_pending": len(self.get_pending_requests())
        }
    
    def clear(self):
        """清空所有请求"""
        self._requests.clear()
        self._approval_callbacks.clear()
        self._stats = {
            "total_requests": 0,
            "approved": 0,
            "rejected": 0,
            "expired": 0,
            "pending": 0
        }
        logger.info("Approval engine cleared")
