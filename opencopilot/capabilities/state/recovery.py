"""
恢复管理模块

提供任务恢复策略和恢复管理功能。
支持多种恢复策略：
- 从最新检查点恢复
- 从指定检查点恢复
- 自动重试
- 降级处理
"""

import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    FROM_LATEST = "from_latest"           # 从最新检查点恢复
    FROM_SPECIFIC = "from_specific"       # 从指定检查点恢复
    AUTO_RETRY = "auto_retry"             # 自动重试
    FALLBACK = "fallback"                 # 降级处理
    MANUAL = "manual"                     # 手动恢复


@dataclass
class RecoveryConfig:
    """恢复配置"""
    strategy: RecoveryStrategy = RecoveryStrategy.FROM_LATEST
    max_retries: int = 3
    retry_delay: float = 1.0  # 秒
    retry_backoff: float = 2.0  # 退避系数
    checkpoint_id: Optional[str] = None  # 用于 FROM_SPECIFIC 策略
    fallback_handler: Optional[Callable] = None  # 用于 FALLBACK 策略
    on_recovery_start: Optional[Callable] = None
    on_recovery_success: Optional[Callable] = None
    on_recovery_failure: Optional[Callable] = None


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    strategy_used: RecoveryStrategy
    checkpoint_id: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    recovery_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecoveryManager:
    """
    恢复管理器
    
    功能：
    1. 根据策略恢复任务状态
    2. 自动重试机制
    3. 恢复历史记录
    4. 恢复统计
    """
    
    def __init__(self, checkpoint_manager=None, state_manager=None):
        """
        初始化恢复管理器
        
        Args:
            checkpoint_manager: 检查点管理器
            state_manager: 状态管理器
        """
        self.checkpoint_manager = checkpoint_manager
        self.state_manager = state_manager
        self._lock = threading.RLock()
        self._recovery_history: List[Dict[str, Any]] = []
        self._retry_counts: Dict[str, int] = {}
    
    def recover_task(
        self,
        task_id: str,
        config: Optional[RecoveryConfig] = None
    ) -> RecoveryResult:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            config: 恢复配置
            
        Returns:
            恢复结果
        """
        if config is None:
            config = RecoveryConfig()
        
        start_time = time.time()
        
        # 调用恢复开始回调
        if config.on_recovery_start:
            config.on_recovery_start(task_id, config)
        
        result = RecoveryResult(
            success=False,
            strategy_used=config.strategy
        )
        
        try:
            if config.strategy == RecoveryStrategy.FROM_LATEST:
                result = self._recover_from_latest(task_id, config)
            elif config.strategy == RecoveryStrategy.FROM_SPECIFIC:
                result = self._recover_from_specific(task_id, config)
            elif config.strategy == RecoveryStrategy.AUTO_RETRY:
                result = self._recover_with_retry(task_id, config)
            elif config.strategy == RecoveryStrategy.FALLBACK:
                result = self._recover_with_fallback(task_id, config)
            elif config.strategy == RecoveryStrategy.MANUAL:
                result = RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.MANUAL,
                    error="手动恢复需要用户干预"
                )
            else:
                result = RecoveryResult(
                    success=False,
                    strategy_used=config.strategy,
                    error=f"未知的恢复策略: {config.strategy}"
                )
        except Exception as e:
            result = RecoveryResult(
                success=False,
                strategy_used=config.strategy,
                error=str(e)
            )
        
        result.recovery_time = time.time() - start_time
        
        # 记录恢复历史
        self._record_recovery(task_id, result)
        
        # 调用恢复完成回调
        if result.success and config.on_recovery_success:
            config.on_recovery_success(task_id, result)
        elif not result.success and config.on_recovery_failure:
            config.on_recovery_failure(task_id, result)
        
        return result
    
    def _recover_from_latest(self, task_id: str, config: RecoveryConfig) -> RecoveryResult:
        """从最新检查点恢复"""
        if not self.checkpoint_manager:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_LATEST,
                error="检查点管理器未初始化"
            )
        
        checkpoint = self.checkpoint_manager.get_latest_checkpoint(task_id)
        
        if not checkpoint:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_LATEST,
                error="没有可用的检查点"
            )
        
        state_snapshot = checkpoint.state_snapshot
        
        # 恢复状态
        if self.state_manager:
            self._restore_state(task_id, state_snapshot)
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.FROM_LATEST,
            checkpoint_id=checkpoint.checkpoint_id,
            state_snapshot=state_snapshot
        )
    
    def _recover_from_specific(self, task_id: str, config: RecoveryConfig) -> RecoveryResult:
        """从指定检查点恢复"""
        if not self.checkpoint_manager:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_SPECIFIC,
                error="检查点管理器未初始化"
            )
        
        if not config.checkpoint_id:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_SPECIFIC,
                error="未指定检查点ID"
            )
        
        checkpoint = self.checkpoint_manager.get_checkpoint(config.checkpoint_id)
        
        if not checkpoint:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_SPECIFIC,
                error=f"检查点不存在: {config.checkpoint_id}"
            )
        
        if checkpoint.task_id != task_id:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FROM_SPECIFIC,
                error="检查点不属于指定任务"
            )
        
        state_snapshot = checkpoint.state_snapshot
        
        # 恢复状态
        if self.state_manager:
            self._restore_state(task_id, state_snapshot)
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.FROM_SPECIFIC,
            checkpoint_id=checkpoint.checkpoint_id,
            state_snapshot=state_snapshot
        )
    
    def _recover_with_retry(self, task_id: str, config: RecoveryConfig) -> RecoveryResult:
        """带重试的恢复"""
        retry_count = self._retry_counts.get(task_id, 0)
        
        if retry_count >= config.max_retries:
            # 重试次数用尽，尝试从最新检查点恢复
            return self._recover_from_latest(task_id, config)
        
        # 增加重试计数
        self._retry_counts[task_id] = retry_count + 1
        
        # 计算延迟
        delay = config.retry_delay * (config.retry_backoff ** retry_count)
        
        # 等待
        time.sleep(delay)
        
        # 尝试恢复
        result = self._recover_from_latest(task_id, config)
        result.retry_count = retry_count + 1
        
        if result.success:
            # 恢复成功，重置重试计数
            self._retry_counts.pop(task_id, None)
        
        return result
    
    def _recover_with_fallback(self, task_id: str, config: RecoveryConfig) -> RecoveryResult:
        """降级恢复"""
        if not config.fallback_handler:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK,
                error="未配置降级处理器"
            )
        
        try:
            # 调用降级处理器
            fallback_result = config.fallback_handler(task_id)
            
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.FALLBACK,
                state_snapshot=fallback_result,
                metadata={"fallback": True}
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK,
                error=f"降级处理失败: {str(e)}"
            )
    
    def _restore_state(self, task_id: str, state_snapshot: Dict[str, Any]):
        """恢复状态到状态管理器"""
        if not self.state_manager:
            return
        
        # 恢复任务状态
        if "task" in state_snapshot:
            task_data = state_snapshot["task"]
            self.state_manager.update_task(
                task_id,
                status=task_data.get("status"),
                progress=task_data.get("progress"),
                result=task_data.get("result"),
                metadata=task_data.get("metadata")
            )
        
        # 恢复会话状态
        if "session" in state_snapshot:
            session_data = state_snapshot["session"]
            session_id = session_data.get("session_id")
            if session_id:
                self.state_manager.update_session_state(
                    session_id,
                    persona=session_data.get("persona"),
                    metadata=session_data.get("metadata")
                )
    
    def _record_recovery(self, task_id: str, result: RecoveryResult):
        """记录恢复历史"""
        record = {
            "task_id": task_id,
            "timestamp": time.time(),
            "success": result.success,
            "strategy": result.strategy_used.value,
            "checkpoint_id": result.checkpoint_id,
            "retry_count": result.retry_count,
            "recovery_time": result.recovery_time,
            "error": result.error
        }
        
        with self._lock:
            self._recovery_history.append(record)
            # 只保留最近 100 条记录
            if len(self._recovery_history) > 100:
                self._recovery_history = self._recovery_history[-100:]
    
    def get_recovery_history(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取恢复历史
        
        Args:
            task_id: 任务ID，为 None 返回所有历史
            
        Returns:
            恢复历史列表
        """
        with self._lock:
            if task_id:
                return [r for r in self._recovery_history if r["task_id"] == task_id]
            return self._recovery_history.copy()
    
    def get_retry_count(self, task_id: str) -> int:
        """
        获取任务的重试次数
        
        Args:
            task_id: 任务ID
            
        Returns:
            重试次数
        """
        return self._retry_counts.get(task_id, 0)
    
    def reset_retry_count(self, task_id: str):
        """
        重置任务的重试次数
        
        Args:
            task_id: 任务ID
        """
        self._retry_counts.pop(task_id, None)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取恢复统计信息
        
        Returns:
            统计信息
        """
        with self._lock:
            history = self._recovery_history
            
            if not history:
                return {
                    "total_recoveries": 0,
                    "successful_recoveries": 0,
                    "failed_recoveries": 0,
                    "success_rate": 0.0,
                    "avg_recovery_time": 0.0,
                    "strategies_used": {}
                }
            
            successful = [r for r in history if r["success"]]
            failed = [r for r in history if not r["success"]]
            
            # 统计各策略使用次数
            strategies_used = {}
            for record in history:
                strategy = record["strategy"]
                strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
            
            # 计算平均恢复时间
            recovery_times = [r["recovery_time"] for r in history if r["recovery_time"] > 0]
            avg_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0
            
            return {
                "total_recoveries": len(history),
                "successful_recoveries": len(successful),
                "failed_recoveries": len(failed),
                "success_rate": len(successful) / len(history) if history else 0,
                "avg_recovery_time": avg_recovery_time,
                "strategies_used": strategies_used
            }
    
    def clear_history(self):
        """清空恢复历史"""
        with self._lock:
            self._recovery_history.clear()
            self._retry_counts.clear()


# 预定义的降级处理器
def default_fallback_handler(task_id: str) -> Dict[str, Any]:
    """
    默认降级处理器
    
    返回一个最小化的状态，让任务可以重新开始
    """
    return {
        "task": {
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "metadata": {"recovered": True, "recovery_type": "fallback"}
        },
        "session": {
            "persona": "default"
        }
    }


def create_recovery_config(
    strategy: RecoveryStrategy = RecoveryStrategy.FROM_LATEST,
    max_retries: int = 3,
    checkpoint_id: Optional[str] = None
) -> RecoveryConfig:
    """
    创建恢复配置的便捷函数
    
    Args:
        strategy: 恢复策略
        max_retries: 最大重试次数
        checkpoint_id: 检查点ID（用于 FROM_SPECIFIC 策略）
        
    Returns:
        恢复配置
    """
    config = RecoveryConfig(
        strategy=strategy,
        max_retries=max_retries,
        checkpoint_id=checkpoint_id
    )
    
    if strategy == RecoveryStrategy.FALLBACK:
        config.fallback_handler = default_fallback_handler
    
    return config
