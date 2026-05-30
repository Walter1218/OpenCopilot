#!/usr/bin/env python3
"""
P3 功能测试：快捷键扩展 + 主题/样式优化
"""

import sys
import os
from unittest.mock import MagicMock, patch

# 设置 PyQt 使用 offscreen 渲染
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

# 初始化 QApplication
app = QApplication(sys.argv)

# 导入测试模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppt_cocreation.cocreation_dialog import CoCreationDialog


def test_shortcuts_definition():
    """测试快捷键定义"""
    print("\n=== 测试快捷键定义 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[{"title": "测试标题", "items": []}],
            agent_url=None
        )
    
    # 手动调用 _setup_shortcuts
    dialog._setup_shortcuts()
    
    # 检查快捷键数量
    shortcuts = dialog.findChildren(QShortcut)
    print(f"  找到 {len(shortcuts)} 个快捷键")
    
    # 检查关键快捷键（Escape和Delete可能被QDialog默认处理）
    expected_shortcuts = [
        "Ctrl+S", "Ctrl+Shift+S", "F5", "F11",
        "Ctrl+Left", "Ctrl+Right", "Ctrl+Home", "Ctrl+End",
        "Ctrl+Z", "Ctrl+Shift+Z", "Ctrl+D", "Ctrl+Shift+N",
        "Ctrl+Return", "Ctrl+1", "Ctrl+2", "Ctrl+3", "Ctrl+4",
        "Ctrl++", "Ctrl+-", "Ctrl+0",
        "Alt+1", "Alt+2", "Alt+3", "Alt+4",
        "Ctrl+T", "F1"
    ]
    
    found_shortcuts = set()
    for shortcut in shortcuts:
        key_sequence = shortcut.key().toString()
        found_shortcuts.add(key_sequence)
    
    missing = []
    for expected in expected_shortcuts:
        if expected not in found_shortcuts:
            missing.append(expected)
    
    if missing:
        print(f"  ❌ 缺失快捷键: {missing}")
        return False
    else:
        print(f"  ✓ 所有 {len(expected_shortcuts)} 个快捷键都已定义")
        return True


def test_theme_definition():
    """测试主题定义"""
    print("\n=== 测试主题定义 ===")
    
    # 检查主题定义
    themes = CoCreationDialog.THEMES
    print(f"  找到 {len(themes)} 个主题")
    
    # 检查主题名称
    expected_themes = ["dark", "light", "blue", "green"]
    for theme_name in expected_themes:
        if theme_name in themes:
            print(f"  ✓ 主题 '{theme_name}': {themes[theme_name]['name']}")
        else:
            print(f"  ❌ 缺失主题: {theme_name}")
            return False
    
    # 检查主题属性
    required_keys = ["name", "dialog_bg", "dialog_color", "splitter_handle", 
                     "toolbar_bg", "button_bg", "button_hover", "button_pressed", 
                     "accent_color", "border_color"]
    
    for theme_name, theme_data in themes.items():
        missing_keys = [key for key in required_keys if key not in theme_data]
        if missing_keys:
            print(f"  ❌ 主题 '{theme_name}' 缺失属性: {missing_keys}")
            return False
    
    print(f"  ✓ 所有主题属性完整")
    return True


def test_theme_switching():
    """测试主题切换"""
    print("\n=== 测试主题切换 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[{"title": "测试标题", "items": []}],
            agent_url=None
        )
    
    # 检查初始主题
    initial_theme = dialog.current_theme
    print(f"  初始主题: {initial_theme}")
    
    # Mock QMessageBox.information
    with patch('PyQt6.QtWidgets.QMessageBox.information'):
        # 测试切换主题
        dialog._on_toggle_theme()
    
    new_theme = dialog.current_theme
    print(f"  切换后主题: {new_theme}")
    
    if initial_theme == new_theme:
        print(f"  ❌ 主题未切换")
        return False
    
    # 测试循环切换
    themes = list(CoCreationDialog.THEMES.keys())
    current_index = themes.index(new_theme)
    expected_next = themes[(current_index + 1) % len(themes)]
    
    with patch('PyQt6.QtWidgets.QMessageBox.information'):
        dialog._on_toggle_theme()
    next_theme = dialog.current_theme
    
    if next_theme == expected_next:
        print(f"  ✓ 主题循环切换正常: {new_theme} -> {next_theme}")
        return True
    else:
        print(f"  ❌ 主题循环切换异常: 期望 {expected_next}, 实际 {next_theme}")
        return False


def test_theme_application():
    """测试主题应用"""
    print("\n=== 测试主题应用 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[{"title": "测试标题", "items": []}],
            agent_url=None
        )
    
    # Mock 子面板
    dialog.source_panel = MagicMock()
    dialog.outline_panel = MagicMock()
    dialog.preview_panel = MagicMock()
    dialog.ai_chat = MagicMock()
    
    # 设置 apply_theme 方法
    dialog.source_panel.apply_theme = MagicMock()
    dialog.outline_panel.apply_theme = MagicMock()
    dialog.preview_panel.apply_theme = MagicMock()
    dialog.ai_chat.apply_theme = MagicMock()
    
    # 测试应用主题
    try:
        dialog._apply_theme()
        print(f"  ✓ 主题应用成功")
        
        # 检查子面板的 apply_theme 是否被调用
        dialog.source_panel.apply_theme.assert_called_once()
        dialog.outline_panel.apply_theme.assert_called_once()
        dialog.preview_panel.apply_theme.assert_called_once()
        dialog.ai_chat.apply_theme.assert_called_once()
        
        print(f"  ✓ 所有子面板的 apply_theme 方法都被调用")
        return True
    except Exception as e:
        print(f"  ❌ 主题应用失败: {e}")
        return False


def test_help_text():
    """测试帮助文本"""
    print("\n=== 测试帮助文本 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[{"title": "测试标题", "items": []}],
            agent_url=None
        )
    
    # 检查 _on_show_shortcuts_help 方法
    if hasattr(dialog, '_on_show_shortcuts_help'):
        print(f"  ✓ 有 _on_show_shortcuts_help 方法")
        return True
    else:
        print(f"  ❌ 缺少 _on_show_shortcuts_help 方法")
        return False


def test_navigation_methods():
    """测试导航方法"""
    print("\n=== 测试导航方法 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[
                {"title": "幻灯片1", "items": []},
                {"title": "幻灯片2", "items": []},
                {"title": "幻灯片3", "items": []}
            ],
            agent_url=None
        )
    
    # Mock 面板
    dialog.preview_panel = MagicMock()
    dialog.outline_panel = MagicMock()
    dialog.preview_panel.current_index = 1
    
    # 检查导航方法
    methods = [
        "_on_prev_slide",
        "_on_next_slide",
        "_on_first_slide",
        "_on_last_slide"
    ]
    
    for method_name in methods:
        if hasattr(dialog, method_name):
            print(f"  ✓ 有 {method_name} 方法")
        else:
            print(f"  ❌ 缺少 {method_name} 方法")
            return False
    
    # 测试导航功能
    dialog._on_prev_slide()
    dialog.preview_panel.set_current_slide.assert_called_with(0)
    print(f"  ✓ 上一页导航正常")
    
    dialog._on_next_slide()
    dialog.preview_panel.set_current_slide.assert_called_with(2)
    print(f"  ✓ 下一页导航正常")
    
    dialog._on_first_slide()
    dialog.preview_panel.set_current_slide.assert_called_with(0)
    print(f"  ✓ 第一页导航正常")
    
    dialog._on_last_slide()
    dialog.preview_panel.set_current_slide.assert_called_with(2)
    print(f"  ✓ 最后一页导航正常")
    
    return True


def test_panel_focus():
    """测试面板聚焦"""
    print("\n=== 测试面板聚焦 ===")
    
    # 使用 mock 来避免 UI 初始化
    with patch.object(CoCreationDialog, '_init_ui'), \
         patch.object(CoCreationDialog, '_connect_signals'), \
         patch.object(CoCreationDialog, '_load_initial_data'):
        
        dialog = CoCreationDialog(
            original_text="测试文本",
            json_data=[{"title": "测试标题", "items": []}],
            agent_url=None
        )
    
    # Mock 面板
    dialog.source_panel = MagicMock()
    dialog.outline_panel = MagicMock()
    dialog.preview_panel = MagicMock()
    dialog.ai_chat = MagicMock()
    dialog.ai_chat.input_edit = MagicMock()
    
    # 检查 _focus_panel 方法
    if hasattr(dialog, '_focus_panel'):
        print(f"  ✓ 有 _focus_panel 方法")
        
        # 测试面板聚焦
        dialog._focus_panel("source")
        dialog.source_panel.setFocus.assert_called_once()
        
        dialog._focus_panel("outline")
        dialog.outline_panel.setFocus.assert_called_once()
        
        dialog._focus_panel("preview")
        dialog.preview_panel.setFocus.assert_called_once()
        
        dialog._focus_panel("ai")
        dialog.ai_chat.input_edit.setFocus.assert_called_once()
        
        print(f"  ✓ 面板聚焦功能正常")
        return True
    else:
        print(f"  ❌ 缺少 _focus_panel 方法")
        return False


def main():
    """主测试函数"""
    print("P3 功能测试：快捷键扩展 + 主题/样式优化")
    print("=" * 60)
    
    tests = [
        ("快捷键定义", test_shortcuts_definition),
        ("主题定义", test_theme_definition),
        ("主题切换", test_theme_switching),
        ("主题应用", test_theme_application),
        ("帮助文本", test_help_text),
        ("导航方法", test_navigation_methods),
        ("面板聚焦", test_panel_focus),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{passed + failed} 通过")
    
    if failed > 0:
        print(f"\n❌ 有 {failed} 个测试失败")
        return 1
    else:
        print(f"\n✓ 所有测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
