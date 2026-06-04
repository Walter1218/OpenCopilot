"""
多轮对话管理器

管理对话上下文，支持追问、澄清、提供选项。
"""

import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationTurn:
    """对话轮次"""
    id: str
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class ConversationState:
    """对话状态"""
    session_id: str
    turn_count: int = 0
    last_action: Optional[str] = None
    pending_confirm: Optional[Dict[str, Any]] = None
    history: List[ConversationTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "last_action": self.last_action,
            "pending_confirm": self.pending_confirm,
            "history": [t.to_dict() for t in self.history],
            "context": self.context,
            "created_at": self.created_at
        }


@dataclass
class ChatResponse:
    """聊天响应"""
    session_id: str
    response: str
    options: Optional[List[Dict[str, Any]]] = None
    context_update: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "session_id": self.session_id,
            "response": self.response,
            "requires_confirmation": self.requires_confirmation
        }
        
        if self.options:
            result["options"] = self.options
        
        if self.context_update:
            result["context_update"] = self.context_update
        
        return result


class ConversationManager:
    """对话管理器
    
    管理对话上下文，支持追问、澄清、提供选项。
    """
    
    def __init__(self):
        """初始化对话管理器"""
        # 活跃会话
        self.sessions: Dict[str, ConversationState] = {}
        
        # 意图识别模式
        self.intent_patterns = {
            "convert": ["转换", "做成", "变成", "转为", "convert", "make"],
            "chart": ["图表", "柱状图", "折线图", "饼图", "chart", "bar", "line", "pie"],
            "table": ["表格", "table", "spreadsheet"],
            "flowchart": ["流程图", "flowchart", "流程"],
            "optimize": ["优化", "改进", "提升", "optimize", "improve"],
            "simplify": ["精简", "简化", "减少", "simplify", "reduce"],
            "add": ["添加", "增加", "加入", "add"],
            "remove": ["删除", "移除", "去掉", "remove", "delete"],
        }
        
        # 响应模板
        self.response_templates = {
            "chart_type_selection": "我检测到这是{data_type}数据，适合用{chart_type}展示。请问：",
            "confirmation": "你想要{action}吗？",
            "clarification": "我不太确定你的意思，你是想{option_a}还是{option_b}？",
            "success": "已完成{action}。",
            "error": "抱歉，{action}时出现问题：{error}",
        }
    
    def create_session(
        self,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建会话
        
        Args:
            session_id: 会话 ID（可选）
            context: 初始上下文（可选）
            
        Returns:
            str: 会话 ID
        """
        session_id = session_id or str(uuid.uuid4())
        
        self.sessions[session_id] = ConversationState(
            session_id=session_id,
            context=context or {}
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """获取会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[ConversationState]: 会话状态
        """
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功删除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def process_message(
        self,
        session_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """处理消息
        
        Args:
            session_id: 会话 ID
            message: 用户消息
            context: 上下文（可选）
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 获取或创建会话
        session = self.get_session(session_id)
        if not session:
            session_id = self.create_session(session_id, context)
            session = self.get_session(session_id)
        
        # 更新上下文
        if context:
            session.context.update(context)
        
        # 记录用户消息
        user_turn = ConversationTurn(
            id=str(uuid.uuid4()),
            role="user",
            content=message,
            timestamp=datetime.now().isoformat()
        )
        session.history.append(user_turn)
        session.turn_count += 1
        
        # 分析意图
        intent = self._analyze_intent(message)
        
        # 生成响应
        response = self._generate_response(session, message, intent)
        
        # 记录助手响应
        assistant_turn = ConversationTurn(
            id=str(uuid.uuid4()),
            role="assistant",
            content=response.response,
            timestamp=datetime.now().isoformat(),
            metadata={
                "options": response.options,
                "requires_confirmation": response.requires_confirmation
            }
        )
        session.history.append(assistant_turn)
        
        return response
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """分析意图
        
        Args:
            message: 用户消息
            
        Returns:
            Dict[str, Any]: 意图分析结果
        """
        message_lower = message.lower()
        
        intent = {
            "action": None,
            "target": None,
            "confidence": 0.0
        }
        
        # 检测动作
        for action, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    intent["action"] = action
                    intent["confidence"] = 0.8
                    break
            if intent["action"]:
                break
        
        # 检测目标
        if intent["action"] in ["chart", "table", "flowchart"]:
            intent["target"] = intent["action"]
        elif intent["action"] == "convert":
            # 尝试检测转换目标
            for target, patterns in self.intent_patterns.items():
                if target in ["chart", "table", "flowchart"]:
                    for pattern in patterns:
                        if pattern in message_lower:
                            intent["target"] = target
                            break
                    if intent["target"]:
                        break
            
            # 如果是转换请求但没有明确目标，设置为需要询问
            if not intent["target"]:
                intent["needs_clarification"] = True
        
        return intent
    
    def _generate_response(
        self,
        session: ConversationState,
        message: str,
        intent: Dict[str, Any]
    ) -> ChatResponse:
        """生成响应
        
        Args:
            session: 会话状态
            message: 用户消息
            intent: 意图分析结果
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 检查是否有待确认项
        if session.pending_confirm:
            return self._handle_confirmation(session, message)
        
        # 基于意图生成响应
        if intent["action"] == "convert":
            return self._handle_convert(session, message, intent)
        
        elif intent["action"] in ["chart", "table", "flowchart"]:
            return self._handle_visualization(session, message, intent)
        
        elif intent["action"] == "optimize":
            return self._handle_optimize(session, message, intent)
        
        elif intent["action"] == "simplify":
            return self._handle_simplify(session, message, intent)
        
        else:
            return self._handle_general(session, message)
    
    def _handle_convert(
        self,
        session: ConversationState,
        message: str,
        intent: Dict[str, Any]
    ) -> ChatResponse:
        """处理转换请求
        
        Args:
            session: 会话状态
            message: 用户消息
            intent: 意图分析结果
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 获取当前内容
        current_slide = session.context.get("current_slide", {})
        content = current_slide.get("content", "")
        
        if not content:
            return ChatResponse(
                session_id=session.session_id,
                response="请先选择要转换的内容。"
            )
        
        # 如果需要澄清或没有明确的目标，询问用户
        if intent.get("needs_clarification") or not intent["target"]:
            # 分析内容类型
            from .context_analyzer import ContextAnalyzer
            analyzer = ContextAnalyzer()
            analysis = analyzer.analyze_content(content)
            
            # 生成选项
            options = []
            
            if analysis.content_type in ["data_comparison", "time_series"]:
                options.append({
                    "id": "opt_bar",
                    "text": "柱状图（对比数值）",
                    "action": {"type": "convert_to_chart", "chart_type": "bar"}
                })
                options.append({
                    "id": "opt_line",
                    "text": "折线图（展示趋势）",
                    "action": {"type": "convert_to_chart", "chart_type": "line"}
                })
                options.append({
                    "id": "opt_pie",
                    "text": "饼图（展示占比）",
                    "action": {"type": "convert_to_chart", "chart_type": "pie"}
                })
            
            if analysis.content_type == "person_attributes":
                options.append({
                    "id": "opt_table",
                    "text": "表格（结构化展示）",
                    "action": {"type": "convert_to_table"}
                })
            
            if analysis.content_type == "process":
                options.append({
                    "id": "opt_flowchart",
                    "text": "流程图（步骤展示）",
                    "action": {"type": "convert_to_flowchart"}
                })
            
            if not options:
                options.append({
                    "id": "opt_table",
                    "text": "表格",
                    "action": {"type": "convert_to_table"}
                })
                options.append({
                    "id": "opt_chart",
                    "text": "图表",
                    "action": {"type": "convert_to_chart", "chart_type": "bar"}
                })
            
            # 设置待确认项
            session.pending_confirm = {
                "type": "conversion_selection",
                "content": content,
                "options": options
            }
            
            # 生成提示
            data_type = analysis.content_type.value if analysis.content_type else "文本"
            response_text = self.response_templates["chart_type_selection"].format(
                data_type=data_type,
                chart_type="图表"
            )
            
            return ChatResponse(
                session_id=session.session_id,
                response=response_text,
                options=options,
                requires_confirmation=True
            )
        
        # 有明确目标，直接执行
        action = {
            "type": f"convert_to_{intent['target']}",
            "params": {"content": content}
        }
        
        session.last_action = action["type"]
        
        return ChatResponse(
            session_id=session.session_id,
            response=self.response_templates["success"].format(
                action=f"转换为{intent['target']}"
            ),
            context_update={"action": action}
        )
    
    def _handle_visualization(
        self,
        session: ConversationState,
        message: str,
        intent: Dict[str, Any]
    ) -> ChatResponse:
        """处理可视化请求
        
        Args:
            session: 会话状态
            message: 用户消息
            intent: 意图分析结果
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 获取当前内容
        current_slide = session.context.get("current_slide", {})
        content = current_slide.get("content", "")
        
        if not content:
            return ChatResponse(
                session_id=session.session_id,
                response="请先选择要可视化的数据。"
            )
        
        # 分析内容
        from .context_analyzer import ContextAnalyzer
        analyzer = ContextAnalyzer()
        analysis = analyzer.analyze_content(content)
        
        # 生成选项
        options = []
        
        if intent["action"] == "chart":
            options.append({
                "id": "opt_bar",
                "text": "柱状图",
                "action": {"type": "convert_to_chart", "chart_type": "bar"}
            })
            options.append({
                "id": "opt_line",
                "text": "折线图",
                "action": {"type": "convert_to_chart", "chart_type": "line"}
            })
            options.append({
                "id": "opt_pie",
                "text": "饼图",
                "action": {"type": "convert_to_chart", "chart_type": "pie"}
            })
        
        elif intent["action"] == "table":
            options.append({
                "id": "opt_table",
                "text": "表格",
                "action": {"type": "convert_to_table"}
            })
        
        elif intent["action"] == "flowchart":
            options.append({
                "id": "opt_flowchart",
                "text": "流程图",
                "action": {"type": "convert_to_flowchart"}
            })
        
        # 设置待确认项
        session.pending_confirm = {
            "type": "visualization_selection",
            "content": content,
            "options": options
        }
        
        return ChatResponse(
            session_id=session.session_id,
            response=f"你想用哪种{intent['action']}类型？",
            options=options,
            requires_confirmation=True
        )
    
    def _handle_optimize(
        self,
        session: ConversationState,
        message: str,
        intent: Dict[str, Any]
    ) -> ChatResponse:
        """处理优化请求
        
        Args:
            session: 会话状态
            message: 用户消息
            intent: 意图分析结果
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 获取当前内容
        current_slide = session.context.get("current_slide", {})
        content = current_slide.get("content", "")
        
        if not content:
            return ChatResponse(
                session_id=session.session_id,
                response="请先选择要优化的内容。"
            )
        
        # 分析内容
        from .context_analyzer import ContextAnalyzer
        analyzer = ContextAnalyzer()
        analysis = analyzer.analyze_content(content)
        
        # 生成优化建议
        suggestions = []
        
        if analysis.quality_score < 0.6:
            suggestions.append("添加更多关键点和数据支撑")
        
        if len(analysis.key_points) > 7:
            suggestions.append(f"精简内容，当前有{len(analysis.key_points)}个要点，建议减少到5个以内")
        
        if not suggestions:
            suggestions.append("优化语言表达，使其更专业")
            suggestions.append("添加数据支撑")
        
        # 生成选项
        options = [
            {
                "id": f"opt_{i}",
                "text": suggestion,
                "action": {"type": "optimize", "params": {"suggestion": suggestion}}
            }
            for i, suggestion in enumerate(suggestions)
        ]
        
        # 设置待确认项
        session.pending_confirm = {
            "type": "optimize_selection",
            "content": content,
            "options": options
        }
        
        return ChatResponse(
            session_id=session.session_id,
            response="我可以从以下几个方面优化内容：",
            options=options,
            requires_confirmation=True
        )
    
    def _handle_simplify(
        self,
        session: ConversationState,
        message: str,
        intent: Dict[str, Any]
    ) -> ChatResponse:
        """处理精简请求
        
        Args:
            session: 会话状态
            message: 用户消息
            intent: 意图分析结果
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 获取当前内容
        current_slide = session.context.get("current_slide", {})
        content = current_slide.get("content", "")
        
        if not content:
            return ChatResponse(
                session_id=session.session_id,
                response="请先选择要精简的内容。"
            )
        
        # 分析内容
        from .context_analyzer import ContextAnalyzer
        analyzer = ContextAnalyzer()
        analysis = analyzer.analyze_content(content)
        
        # 生成精简建议
        current_points = len(analysis.key_points)
        recommended_points = 5
        
        if current_points <= recommended_points:
            return ChatResponse(
                session_id=session.session_id,
                response=f"当前内容已经有{current_points}个要点，不需要进一步精简。"
            )
        
        # 生成选项
        options = [
            {
                "id": "opt_auto",
                "text": f"自动精简到{recommended_points}个要点",
                "action": {
                    "type": "simplify",
                    "params": {
                        "current_points": current_points,
                        "recommended_points": recommended_points
                    }
                }
            },
            {
                "id": "opt_manual",
                "text": "手动选择要保留的要点",
                "action": {
                    "type": "simplify_manual",
                    "params": {
                        "points": analysis.key_points
                    }
                }
            }
        ]
        
        # 设置待确认项
        session.pending_confirm = {
            "type": "simplify_selection",
            "content": content,
            "options": options
        }
        
        return ChatResponse(
            session_id=session.session_id,
            response=f"当前有{current_points}个要点，建议精简到{recommended_points}个以内。你想怎么处理？",
            options=options,
            requires_confirmation=True
        )
    
    def _handle_general(
        self,
        session: ConversationState,
        message: str
    ) -> ChatResponse:
        """处理通用消息
        
        Args:
            session: 会话状态
            message: 用户消息
            
        Returns:
            ChatResponse: 聊天响应
        """
        # 检查是否是问候
        greetings = ["你好", "hi", "hello", "hey", "嗨"]
        if any(g in message.lower() for g in greetings):
            return ChatResponse(
                session_id=session.session_id,
                response="你好！我是 PPT 助手，可以帮你创建和优化 PPT。有什么可以帮你的吗？"
            )
        
        # 检查是否是帮助请求
        help_keywords = ["帮助", "help", "怎么用", "功能"]
        if any(k in message.lower() for k in help_keywords):
            return ChatResponse(
                session_id=session.session_id,
                response="我可以帮你：\n1. 将文本转换为图表、表格或流程图\n2. 优化 PPT 内容\n3. 精简冗长的内容\n4. 检查风格一致性\n\n请告诉我你想做什么。"
            )
        
        # 默认响应
        return ChatResponse(
            session_id=session.session_id,
            response="我理解你的意思。你可以告诉我具体想做什么，比如：\n- \"把这个做成图表\"\n- \"优化这段内容\"\n- \"精简这些要点\""
        )
    
    def _handle_confirmation(
        self,
        session: ConversationState,
        message: str
    ) -> ChatResponse:
        """处理确认
        
        Args:
            session: 会话状态
            message: 用户消息
            
        Returns:
            ChatResponse: 聊天响应
        """
        pending = session.pending_confirm
        options = pending.get("options", [])
        
        # 尝试匹配用户选择
        selected_option = None
        
        # 检查数字选择
        for i, option in enumerate(options):
            if str(i + 1) in message or option["text"] in message:
                selected_option = option
                break
        
        # 检查关键词匹配
        if not selected_option:
            for option in options:
                if any(word in message for word in option["text"].split()):
                    selected_option = option
                    break
        
        if selected_option:
            # 清除待确认项
            session.pending_confirm = None
            
            # 执行动作
            action = selected_option["action"]
            session.last_action = action["type"]
            
            return ChatResponse(
                session_id=session.session_id,
                response=self.response_templates["success"].format(
                    action=selected_option["text"]
                ),
                context_update={"action": action}
            )
        
        # 无法匹配，重新提示
        options_text = "\n".join([
            f"{i + 1}. {opt['text']}"
            for i, opt in enumerate(options)
        ])
        
        return ChatResponse(
            session_id=session.session_id,
            response=f"请选择一个选项：\n{options_text}",
            options=options,
            requires_confirmation=True
        )
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取对话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            List[Dict[str, Any]]: 对话历史
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        return [t.to_dict() for t in session.history]
    
    def clear_history(self, session_id: str) -> bool:
        """清除对话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功清除
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.history = []
        session.turn_count = 0
        session.last_action = None
        session.pending_confirm = None
        
        return True


# 便捷函数
def create_conversation_manager() -> ConversationManager:
    """创建对话管理器（便捷函数）"""
    return ConversationManager()