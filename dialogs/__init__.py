"""
对话框模块
包含办公场景专用界面
"""

from .document_dialog import DocumentDialog
from .translation_dialog import TranslationDialog
from .polish_dialog import PolishDialog

__all__ = [
    'DocumentDialog',
    'TranslationDialog',
    'PolishDialog'
]
