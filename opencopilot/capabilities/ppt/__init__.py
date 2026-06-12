"""
PPT 人机共创编辑器模块

提供三面板布局的 PPT 共创工作台：
- 原文面板：显示 AI 原始输出，支持高亮标记和选中工具
- 编辑大纲面板：幻灯片导航和编辑表单
- PPT 预览面板：实时预览，与最终导出一致
- AI 对话框：交互式修改幻灯片内容
- 渲染指令系统：声明式渲染架构，支持 AI 指令驱动
"""

from .cocreation_dialog import CoCreationDialog
from .cocreation_widget import CoCreationWidget, CoCreationWindow
from .source_panel import SourcePanel
from .outline_panel import OutlinePanel
from .preview_panel import PreviewPanel
from .ai_chat_widget import AICopilotChatWidget
from .source_matcher import SourceMatcher
from .suggestion_bubble import SuggestionBubble, SuggestionBubbleManager
from .content_analysis_panel import ContentAnalysisPanel, AnalysisPanelManager
from .pipeline import (
    PPTGenerationPipeline, PipelineResult, Topic,
    ContentMapping, ContentItem, FormatResult,
)
from .intent_router import IntentRouter
from .storyline_view import StorylineView

# 渲染指令系统
from .render_command import (
    RenderCommand, RenderGroup, RenderResult,
    RenderCommandParser, QuickActionGenerator,
    BatchOperationParser,
    convert_render_command_to_slide_json,
    parse_batch_operation
)
from .render_executor import RenderExecutor, RenderDispatcher
from .render_prompt_generator import RenderPromptGenerator, generate_render_prompt

__all__ = [
    'CoCreationDialog',
    'CoCreationWidget',
    'CoCreationWindow',
    'SourcePanel',
    'OutlinePanel',
    'PreviewPanel',
    'AICopilotChatWidget',
    'SourceMatcher',
    'SuggestionBubble',
    'SuggestionBubbleManager',
    'ContentAnalysisPanel',
    'AnalysisPanelManager',
    'PPTGenerationPipeline',
    'PipelineResult',
    'Topic',
    'ContentMapping',
    'ContentItem',
    'FormatResult',
    'IntentRouter',
    'StorylineView',
    # 渲染指令系统
    'RenderCommand',
    'RenderGroup',
    'RenderResult',
    'RenderCommandParser',
    'QuickActionGenerator',
    'BatchOperationParser',
    'convert_render_command_to_slide_json',
    'parse_batch_operation',
    'RenderExecutor',
    'RenderDispatcher',
    'RenderPromptGenerator',
    'generate_render_prompt',
]
