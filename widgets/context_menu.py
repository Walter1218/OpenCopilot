"""
右键菜单优化组件
支持动态菜单项、快捷键显示、上下文感知
"""
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import pyqtSignal


class ContextMenu(QMenu):
    """优化的右键菜单"""
    
    # 信号定义
    action_triggered = pyqtSignal(str, object)  # 动作触发信号 (action_id, data)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.actions_map = {}
        self.dynamic_actions = []
        self.context_type = "text"
        
        # 初始化默认菜单
        self._setup_default_menu()
    
    def _setup_default_menu(self):
        """设置默认菜单"""
        # 基础操作
        self.add_action("复制", "copy", "Ctrl+C")
        self.add_action("粘贴", "paste", "Ctrl+V")
        self.add_action("剪切", "cut", "Ctrl+X")
        self.addSeparator()
        
        # AI操作
        self.add_action("翻译", "translate", "Ctrl+T")
        self.add_action("润色", "polish", "Ctrl+P")
        self.add_action("修订", "revise", "Ctrl+R")
        self.addSeparator()
        
        # 格式操作
        self.add_action("加粗", "bold", "Ctrl+B")
        self.add_action("斜体", "italic", "Ctrl+I")
    
    def add_action(self, text, action_id, shortcut=None):
        """添加菜单项"""
        action = QAction(text, self)
        action.setData(action_id)
        
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        
        action.triggered.connect(lambda: self._on_action_triggered(action_id))
        self.addAction(action)
        self.actions_map[action_id] = action
        
        return action
    
    def add_dynamic_action(self, text, action_id, data=None):
        """添加动态菜单项"""
        action = QAction(text, self)
        action.setData(action_id)
        
        if data:
            action.setProperty("custom_data", data)
        
        action.triggered.connect(lambda: self._on_action_triggered(action_id, data))
        self.addAction(action)
        self.dynamic_actions.append(action)
        
        return action
    
    def clear_dynamic_actions(self):
        """清除动态菜单项"""
        for action in self.dynamic_actions:
            self.removeAction(action)
        self.dynamic_actions.clear()
    
    def set_context(self, context_type):
        """设置上下文类型"""
        self.context_type = context_type
        self._update_dynamic_items()
    
    def _update_dynamic_items(self):
        """更新动态菜单项"""
        self.clear_dynamic_actions()
        
        if self.context_type == "text":
            self.addSeparator()
            self.add_dynamic_action("解释选中文本", "explain_text")
            self.add_dynamic_action("总结选中文本", "summarize_text")
        
        elif self.context_type == "code":
            self.addSeparator()
            self.add_dynamic_action("解释代码", "explain_code")
            self.add_dynamic_action("优化代码", "optimize_code")
            self.add_dynamic_action("添加注释", "add_comment")
        
        elif self.context_type == "file":
            self.addSeparator()
            self.add_dynamic_action("打开文件", "open_file")
            self.add_dynamic_action("预览文件", "preview_file")
            self.add_dynamic_action("重命名文件", "rename_file")
    
    def _on_action_triggered(self, action_id, data=None):
        """动作触发回调"""
        self.action_triggered.emit(action_id, data)
    
    def get_action(self, action_id):
        """获取菜单项"""
        return self.actions_map.get(action_id)
    
    def set_action_enabled(self, action_id, enabled):
        """设置菜单项启用状态"""
        action = self.actions_map.get(action_id)
        if action:
            action.setEnabled(enabled)
    
    def set_action_visible(self, action_id, visible):
        """设置菜单项可见性"""
        action = self.actions_map.get(action_id)
        if action:
            action.setVisible(visible)
    
    def get_context_type(self):
        """获取上下文类型"""
        return self.context_type


class TextContextMenu(ContextMenu):
    """文本上下文菜单"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_text = ""
    
    def show_for_text(self, text, position):
        """为文本显示菜单"""
        self.selected_text = text
        self.set_context("text")
        
        # 根据选中文本启用/禁用菜单项
        has_selection = bool(text and text.strip())
        self.set_action_enabled("copy", has_selection)
        self.set_action_enabled("translate", has_selection)
        self.set_action_enabled("polish", has_selection)
        self.set_action_enabled("revise", has_selection)
        
        # 显示菜单
        self.exec(position)
    
    def get_selected_text(self):
        """获取选中文本"""
        return self.selected_text


class FileContextMenu(ContextMenu):
    """文件上下文菜单"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ""
    
    def show_for_file(self, file_path, position):
        """为文件显示菜单"""
        self.file_path = file_path
        self.set_context("file")
        
        # 根据文件类型启用/禁用菜单项
        is_supported = self._is_supported_file(file_path)
        self.set_action_enabled("open_file", is_supported)
        self.set_action_enabled("preview_file", is_supported)
        
        # 显示菜单
        self.exec(position)
    
    def _is_supported_file(self, file_path):
        """检查是否是支持的文件类型"""
        supported_extensions = ['.txt', '.md', '.docx', '.pdf', '.pptx']
        return any(file_path.endswith(ext) for ext in supported_extensions)
    
    def get_file_path(self):
        """获取文件路径"""
        return self.file_path


class CodeContextMenu(ContextMenu):
    """代码上下文菜单"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.code_text = ""
        self.language = ""
    
    def show_for_code(self, code_text, language, position):
        """为代码显示菜单"""
        self.code_text = code_text
        self.language = language
        self.set_context("code")
        
        # 根据代码长度启用/禁用菜单项
        has_code = bool(code_text and code_text.strip())
        self.set_action_enabled("explain_code", has_code)
        self.set_action_enabled("optimize_code", has_code)
        
        # 显示菜单
        self.exec(position)
    
    def get_code_text(self):
        """获取代码文本"""
        return self.code_text
    
    def get_language(self):
        """获取编程语言"""
        return self.language
