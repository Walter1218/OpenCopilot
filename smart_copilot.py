"""
Smart Copilot 桌面应用 - 兼容入口
====================================
v4.0 重构：3978行 → gui/ 13个模块文件（平均206行）
所有 v3.0 导入路径通过本文件 re-export 保持兼容。
使用方式: python smart_copilot.py
"""
import os, sys

from gui.shared import check_accessibility_permission, make_panel_persistent
from gui.workers.scanner import ModelScannerWorker
from gui.workers.ai import AIWorker
from gui.workers.chat import ChatWorker
from gui.workers.broker import BrokerEventsWorker
from gui.workers.browser import BrowserReaderWorker
from gui.workers.mouse import MouseListenerWorker
from gui.workers.health import AgentHealthWorker
from gui.dialogs.settings import SettingsDialog
from gui.dialogs.ppt_preview import PPTPreviewDialog
from gui.window import AICardWindow
from gui.workspace import AgentWorkspace
from gui.main import CopilotManager, main

__all__ = [
    "AICardWindow", "AgentWorkspace", "CopilotManager",
    "AIWorker", "ChatWorker", "BrokerEventsWorker",
    "BrowserReaderWorker", "MouseListenerWorker", "AgentHealthWorker",
    "ModelScannerWorker", "SettingsDialog", "PPTPreviewDialog",
    "check_accessibility_permission", "make_panel_persistent",
    "main",
]

if __name__ == "__main__":
    main()
