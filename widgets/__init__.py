"""
Widgets模块 - UI组件
"""

from .file_drop_zone import FileDropZone
from .context_menu import ContextMenu, TextContextMenu, FileContextMenu, CodeContextMenu
from .settings_dialog import SettingsDialog
from .progress_widget import ProgressWidget, MultiStepProgressWidget, ProgressManager
from .batch_dialog import BatchDialog, FileItem, FileStatus, BatchStatus
from .terminology_dialog import TerminologyDialog, TerminologyEntry, TerminologyDatabase, MatchType
from .translation_memory import TranslationMemory, TranslationUnit, TranslationMemoryDialog

__all__ = [
    'FileDropZone',
    'ContextMenu',
    'TextContextMenu',
    'FileContextMenu',
    'CodeContextMenu',
    'SettingsDialog',
    'ProgressWidget',
    'MultiStepProgressWidget',
    'ProgressManager',
    'BatchDialog',
    'FileItem',
    'FileStatus',
    'BatchStatus',
    'TerminologyDialog',
    'TerminologyEntry',
    'TerminologyDatabase',
    'MatchType',
    'TranslationMemory',
    'TranslationUnit',
    'TranslationMemoryDialog'
]