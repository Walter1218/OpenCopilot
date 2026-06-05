"""
PPT 人机共创编辑器模块

提供三面板布局的 PPT 共创工作台：
- 原文面板：显示 AI 原始输出，支持高亮标记和选中工具
- 编辑大纲面板：幻灯片导航和编辑表单
- PPT 预览面板：实时预览，与最终导出一致
- AI 对话框：交互式修改幻灯片内容
"""

from .cocreation_dialog import CoCreationDialog
from .source_panel import SourcePanel
from .outline_panel import OutlinePanel
from .preview_panel import PreviewPanel
from .ai_chat_widget import AICopilotChatWidget
from .source_matcher import SourceMatcher
from .suggestion_bubble import SuggestionBubble, SuggestionBubbleManager
from .content_analysis_panel import ContentAnalysisPanel, AnalysisPanelManager

__all__ = [
    'CoCreationDialog',
    'SourcePanel',
    'OutlinePanel',
    'PreviewPanel',
    'AICopilotChatWidget',
    'SourceMatcher',
    'SuggestionBubble',
    'SuggestionBubbleManager',
    'ContentAnalysisPanel',
    'AnalysisPanelManager',
]
