"""GUI shared"""
import os
import re
import sys
import subprocess
import traceback
import time
import uuid
import threading
import tempfile
import asyncio
import websockets
import httpx
from pynput import mouse

from PyQt6.QtWidgets import *
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QDialog,
    QRadioButton, QLineEdit, QMessageBox, QTabWidget, QComboBox,
    QFileDialog, QSystemTrayIcon, QMenu, QStyle, QGroupBox,
    QSplitter, QListWidget, QListWidgetItem, QFormLayout
)
from ppt_generator import generate_ppt_from_json, extract_json_from_text
from opencopilot.capabilities.ppt import CoCreationDialog
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QCursor, QColor, QAction, QIcon

from cursor_effects import Ripple, CursorOverlay
from llm_provider import ProviderFactory, load_config, save_config
from markdown_renderer import render as md_render
from system_probe_client import SystemProbeClient

# 新增：导入办公场景UI组件
from core.theme_manager import ThemeManager
from core.shortcut_manager import ShortcutManager
from widgets.file_drop_zone import FileDropZone
from widgets.progress_widget import ProgressWidget, MultiStepProgressWidget
from widgets.context_menu import TextContextMenu, FileContextMenu, CodeContextMenu
from widgets.settings_dialog import SettingsDialog as NewSettingsDialog
from widgets.batch_dialog import BatchDialog
from widgets.terminology_dialog import TerminologyDialog
from widgets.translation_memory import TranslationMemory

# 新增：导入技能面板组件
from widgets.skill_panel import SkillPanel, SkillSearchWidget, SkillCommandParser
from widgets.skill_context_menu import SkillContextMenu, SkillCommandWidget
from widgets.skill_search_dialog import SkillSearchDialog, SkillQuickAccessWidget

# 导入 Skill 架构
from opencopilot.capabilities.skill import SkillRegistry, SkillContext, IntentRouter, SkillExecutor
from opencopilot.capabilities.skill.coding_skill import CodingSkill
from opencopilot.capabilities.skill.knowledge_skill import KnowledgeSkill
from opencopilot.capabilities.skill.ppt_skill import PPTSkill
from opencopilot.capabilities.skill.evaluation_skill import EvaluationSkill
from opencopilot.capabilities.skill.file_skill import FileSkill
from opencopilot.capabilities.skill.format_skill import FormatSkill
from opencopilot.capabilities.skill.persona_skill import PersonaSkill


def check_accessibility_permission():
    """检测 macOS 辅助功能权限，未授权则弹出提示并尝试打开系统设置。"""
    if sys.platform != "darwin":
        return True
    try:
        from ApplicationServices import AXIsProcessTrusted
        if AXIsProcessTrusted():
            return True
    except ImportError:
        # PyObjC 未安装，用 AppleScript 间接检测
        try:
            r = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first process'],
                capture_output=True, timeout=3, text=True,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass

    # 权限未授予 → 弹窗提示
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("⚠️ 辅助功能权限未授予")
    msg.setText(
        "Smart Copilot 无法监听鼠标事件！\n\n"
        "请按以下步骤授权：\n"
        "1. 打开 系统设置 → 隐私与安全性 → 辅助功能\n"
        "2. 将当前终端（Terminal / Trae / iTerm2）添加到列表并勾选\n"
        "3. 完全退出后重新运行 Smart Copilot\n\n"
        "点击「打开系统设置」可直达权限页面。"
    )
    btn_open = msg.addButton("打开系统设置", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton("稍后手动设置", QMessageBox.ButtonRole.RejectRole)
    msg.exec()

    if msg.clickedButton() == btn_open:
        subprocess.Popen([
            "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        ])
    return False


def make_panel_persistent(widget):
    """macOS: 设置 NSPanel.hidesOnDeactivate = False，防止失焦自动隐藏。
    
    Qt.Tool 标志在 macOS 上创建 NSPanel，默认 hidesOnDeactivate=True，
    导致应用失焦时窗口被系统自动隐藏。通过 PyObjC 直接修改该属性实现常驻。
    """
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApp, NSPanel

        # 保存原标题，设置唯一临时标题用于在 NSApp.windows() 中定位
        orig_title = widget.windowTitle()
        tag = f"_asu_persistent_{id(widget)}"
        widget.setWindowTitle(tag)

        found = False
        for ns_win in NSApp.windows():
            if ns_win.title() == tag:
                if isinstance(ns_win, NSPanel):
                    ns_win.setHidesOnDeactivate_(False)
                found = True
                break

        # 恢复原标题
        widget.setWindowTitle(orig_title)
        
        if not found:
            # 备选：遍历所有 NSPanel 直接设置
            for ns_win in NSApp.windows():
                if isinstance(ns_win, NSPanel):
                    ns_win.setHidesOnDeactivate_(False)
    except Exception:
        pass

