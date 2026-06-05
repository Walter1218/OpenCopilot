"""
上下文管理核心模块

从 asu_custom_agent.py 抽取的 ContextWindowManager，增强为独立模块。
"""

import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContextBudget:
    """上下文预算配置"""
    max_input_chars: int = 120000
    reserve_output_chars: int = 30000
    recent_turns: int = 12
    max_history_msg_chars: int = 8000


# ConfigManager 统一使用根版本（已合并 get_context_budget/get_model_limits）
from config_manager import ConfigManager


class ContextWindowManager:
    """
    基于预算的上下文窗口管理器
    
    从 asu_custom_agent.py 抽取，保持向后兼容。
    
    使用示例：
        manager = ContextWindowManager(model_name="MiniMax-M3")
        
        # 构建用户 payload
        envelope = {
            "source": "ide",
            "content": "代码内容...",
            "task": "修复 bug"
        }
        payload = manager.build_user_payload(envelope)
    """
    
    def __init__(self, max_input_chars=120000, reserve_output_chars=30000,
                 recent_turns=12, max_history_msg_chars=8000,
                 model_name: str = None, config_path: str = None):
        self.max_input_chars = max_input_chars
        self.reserve_output_chars = reserve_output_chars
        self.recent_turns = recent_turns
        self.max_history_msg_chars = max_history_msg_chars
        self.model_name = model_name
        
        # 添加配置管理器（统一使用单例）
        self.config_manager = ConfigManager.get_instance()
        
        # 如果指定了模型，动态调整配置
        if model_name:
            self.adjust_for_model(model_name)
    
    def adjust_for_model(self, model_name: str):
        """根据模型能力动态调整配置"""
        # 使用配置管理器获取模型限制
        model_limits = self.config_manager.get_model_limits()
        model_limit = model_limits.get(model_name, 200000)
        
        # 将 token 限制转换为字符限制（中文约 1.5-2 token/字符）
        # 使用保守估计：1 token ≈ 1.5 字符
        max_chars = int(model_limit * 0.75)  # 75% 的 token 限制作为字符限制
        
        # 调整配置
        self.max_input_chars = max_chars
        self.reserve_output_chars = max_chars // 4  # 预留 25% 给输出
        self.max_history_msg_chars = min(8000, max_chars // 15)  # 单条消息不超过总预算的 1/15
        
        # 根据模型能力调整轮数
        if model_limit >= 100000:
            self.recent_turns = 12
        elif model_limit >= 32000:
            self.recent_turns = 8
        elif model_limit >= 8000:
            self.recent_turns = 4
        else:
            self.recent_turns = 2
        
        return self
    
    def _truncate_text(self, text, limit):
        """截断文本"""
        if not text or limit <= 0:
            return ""
        if len(text) <= limit:
            return text
        marker = "\n\n...[已截断]...\n\n"
        marker_len = len(marker)
        if limit <= marker_len + 20:
            return text[:limit]
        head = int((limit - marker_len) * 0.7)
        tail = limit - marker_len - head
        return text[:head] + marker + text[-tail:]
    
    def _clip_by_source(self, source, text, limit):
        """按来源做裁剪策略：IDE 保留头尾，Browser 偏头部，其他常规截断。"""
        if not text or limit <= 0:
            return ""
        if len(text) <= limit:
            return text
        
        if source == "ide":
            marker = "\n\n...[IDE内容已裁剪，保留头尾关键片段]...\n\n"
            marker_len = len(marker)
            if limit <= marker_len + 20:
                return text[:limit]
            head = int((limit - marker_len) * 0.55)
            tail = limit - marker_len - head
            return text[:head] + marker + text[-tail:]
        
        if source == "browser":
            marker = "\n\n...[网页正文已裁剪]...\n\n"
            marker_len = len(marker)
            if limit <= marker_len + 20:
                return text[:limit]
            head = limit - marker_len
            return text[:head] + marker
        
        return self._truncate_text(text, limit)
    
    def _build_user_payload(self, envelope, budget=None):
        """构建用户 payload"""
        if budget is None:
            budget = self.max_input_chars - self.reserve_output_chars
        
        source = envelope.get("source", "drag")
        content = envelope.get("content", "")
        selection = envelope.get("selection", "")
        task = envelope.get("task", "")
        custom_instruction = envelope.get("custom_instruction", "")
        meta = envelope.get("meta", {}) or {}
        
        # 元信息摘要
        meta_parts = []
        for k in ("file_name", "language", "app_name", "title", "url"):
            v = meta.get(k)
            if v:
                meta_parts.append(f"{k}={v}")
        # custom_instruction 优先从 envelope 顶层取，其次从 meta 取
        if not custom_instruction:
            custom_instruction = meta.get("custom_instruction", "")
        meta_text = "；".join(meta_parts)
        
        # 先构建骨架，再把正文按剩余预算裁剪
        payload_parts = [f"[context_source] {source}"]
        if task:
            payload_parts.append(f"[task] {task}")
        if meta_text:
            payload_parts.append(f"[meta] {meta_text}")
            
        # 注入高级 IDE 上下文
        diagnostics = meta.get("diagnostics")
        if diagnostics and isinstance(diagnostics, list):
            diag_lines = []
            for d in diagnostics:
                sev_idx = d.get("severity", 0)
                severity = ["Error", "Warning", "Information", "Hint"][sev_idx] if isinstance(sev_idx, int) and 0 <= sev_idx <= 3 else "Error"
                diag_lines.append(f"- Line {d.get('line')}: [{severity}] {d.get('message')}")
            if diag_lines:
                payload_parts.append("[diagnostics] (当前文件存在的诊断报错)\n" + "\n".join(diag_lines))
        
        git_diff = meta.get("git_diff")
        if git_diff and isinstance(git_diff, str) and git_diff.strip():
            payload_parts.append(f"[git_diff] (当前文件的未提交变更)\n{git_diff[:2000]}")
        
        if custom_instruction:
            payload_parts.append(
                f"[custom_instruction]\n{custom_instruction}\n\n"
                f"请严格按照上述指令对 [selection] 或当前代码块中的文本进行修改，只输出修改后的文本，不要输出任何解释或说明。"
            )
        if selection:
            payload_parts.append(f"[selection]\n{selection}")
        
        skeleton = "\n\n".join(payload_parts)
        skeleton_len = len(skeleton)
        
        # 计算内容可用预算
        content_budget = budget - skeleton_len - 20  # 20 字符余量
        
        if content and content_budget > 100:
            # 按来源裁剪内容
            clipped_content = self._clip_by_source(source, content, content_budget)
            payload_parts.append(f"[content]\n{clipped_content}")
        
        return "\n\n".join(payload_parts)
    
    def build_user_payload(self, envelope: Dict[str, Any]) -> str:
        """
        构建用户 payload（公共接口）
        
        Args:
            envelope: 上下文信封，包含 source, content, task 等字段
            
        Returns:
            构建好的 payload 字符串
        """
        return self._build_user_payload(envelope)
    
    def build_messages(self, system_prompt: str, context: Dict[str, Any], 
                      history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        构建完整的消息列表
        
        Args:
            system_prompt: 系统提示词
            context: 上下文信封
            history: 历史消息列表
            
        Returns:
            消息列表
        """
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史消息（限制轮数）
        if history:
            recent_history = history[-self.recent_turns:]
            for msg in recent_history:
                # 限制单条消息长度
                content = msg.get("content", "")
                if len(content) > self.max_history_msg_chars:
                    content = self._truncate_text(content, self.max_history_msg_chars)
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })
        
        # 添加当前上下文
        if context:
            user_payload = self._build_user_payload(context)
            messages.append({"role": "user", "content": user_payload})
        
        return messages
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "max_input_chars": self.max_input_chars,
            "reserve_output_chars": self.reserve_output_chars,
            "recent_turns": self.recent_turns,
            "max_history_msg_chars": self.max_history_msg_chars,
            "model_name": self.model_name
        }


class ContextManager:
    """
    上下文管理器 - 乐高积木模块
    
    整合 ContextWindowManager，提供统一的上下文管理接口。
    
    使用示例：
        manager = ContextManager(model_name="MiniMax-M3")
        
        # 获取上下文
        context = manager.get_context(session_id="session_123")
        
        # 构建消息
        messages = manager.build_messages(system_prompt, context, history)
    """
    
    def __init__(self, model_name: str = None, config_path: str = None):
        self.window_manager = ContextWindowManager(
            model_name=model_name,
            config_path=config_path
        )
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话上下文
        
        Args:
            session_id: 会话 ID
            
        Returns:
            上下文信封
        """
        return {
            "source": "session",
            "content": "",
            "session_id": session_id,
            "history": self._sessions.get(session_id, [])
        }
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        添加消息到会话历史
        
        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant)
            content: 消息内容
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        self._sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def clear_session(self, session_id: str):
        """清空会话历史"""
        self._sessions.pop(session_id, None)
    
    def build_messages(self, system_prompt: str, context: Dict[str, Any],
                      history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Args:
            system_prompt: 系统提示词
            context: 上下文信封
            history: 历史消息
            
        Returns:
            消息列表
        """
        return self.window_manager.build_messages(system_prompt, context, history)
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self.window_manager.get_config()
