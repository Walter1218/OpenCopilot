"""
快捷键管理器 - 增加全局快捷键，提高办公操作效率
"""

import json
import os
from typing import Dict, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut


@dataclass
class Shortcut:
    """快捷键配置"""
    key: str
    name: str
    action: str
    description: str = ""
    enabled: bool = True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "key": self.key,
            "name": self.name,
            "action": self.action,
            "description": self.description,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Shortcut':
        """从字典创建"""
        return cls(
            key=data.get("key", ""),
            name=data.get("name", ""),
            action=data.get("action", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True)
        )


# 预定义快捷键
DEFAULT_SHORTCUTS = {
    "cmd+shift+space": Shortcut(
        key="cmd+shift+space",
        name="唤醒/隐藏卡片",
        action="toggle_visibility",
        description="显示或隐藏AI助手卡片"
    ),
    "cmd+shift+t": Shortcut(
        key="cmd+shift+t",
        name="翻译模式",
        action="open_translation",
        description="打开翻译功能"
    ),
    "cmd+shift+p": Shortcut(
        key="cmd+shift+p",
        name="润色模式",
        action="open_polish",
        description="打开文本润色功能"
    ),
    "cmd+shift+r": Shortcut(
        key="cmd+shift+r",
        name="文档修订模式",
        action="open_revision",
        description="打开文档修订功能"
    ),
    "cmd+shift+s": Shortcut(
        key="cmd+shift+s",
        name="打开设置",
        action="open_settings",
        description="打开设置界面"
    ),
    "cmd+shift+b": Shortcut(
        key="cmd+shift+b",
        name="批量处理模式",
        action="open_batch",
        description="打开批量处理功能"
    ),
    "cmd+enter": Shortcut(
        key="cmd+enter",
        name="发送消息",
        action="send_message",
        description="发送当前输入的消息"
    ),
    "escape": Shortcut(
        key="escape",
        name="关闭/取消",
        action="close_or_cancel",
        description="关闭当前对话框或取消操作"
    )
}

# 系统保留快捷键（不允许用户修改）
SYSTEM_SHORTCUTS = [
    "cmd+c",  # 复制
    "cmd+v",  # 粘贴
    "cmd+x",  # 剪切
    "cmd+z",  # 撤销
    "cmd+a",  # 全选
    "cmd+s",  # 保存
    "cmd+o",  # 打开
    "cmd+n",  # 新建
    "cmd+w",  # 关闭
    "cmd+q",  # 退出
    "cmd+tab",  # 切换应用
    "cmd+space",  # Spotlight
]


class ShortcutManager(QObject):
    """快捷键管理器"""
    
    # 快捷键触发信号
    shortcut_triggered = pyqtSignal(str)
    
    # 快捷键冲突信号
    shortcut_conflict = pyqtSignal(str, str)  # (new_key, existing_action)
    
    # 配置文件路径
    CONFIG_DIR = os.path.expanduser("~/.opencopilot")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "shortcut_config.json")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 快捷键配置
        self._shortcuts: Dict[str, Shortcut] = {}
        
        # 动作回调
        self._action_callbacks: Dict[str, Callable] = {}
        
        # Qt快捷键对象
        self._qt_shortcuts: Dict[str, QShortcut] = {}
        
        # 是否已注册
        self._is_registered = False
        
        # 父窗口
        self._parent_widget = parent
        
        # 加载默认快捷键
        self._load_default_shortcuts()
        
        # 加载用户配置
        self._load_shortcut_preference()
    
    @property
    def is_registered(self) -> bool:
        """是否已注册快捷键"""
        return self._is_registered
    
    def get_shortcuts(self) -> Dict[str, Shortcut]:
        """获取所有快捷键"""
        return self._shortcuts.copy()
    
    def get_shortcut(self, key: str) -> Optional[Shortcut]:
        """获取指定快捷键"""
        return self._shortcuts.get(key)
    
    def get_shortcut_list(self) -> List[Shortcut]:
        """获取快捷键列表"""
        return list(self._shortcuts.values())
    
    def get_enabled_shortcuts(self) -> List[Shortcut]:
        """获取启用的快捷键列表"""
        return [s for s in self._shortcuts.values() if s.enabled]
    
    def register_shortcuts(self) -> bool:
        """
        注册所有快捷键到Qt
        
        Returns:
            bool: 注册是否成功
        """
        if not self._parent_widget:
            return False
        
        try:
            # 清除现有快捷键
            self.unregister_shortcuts()
            
            # 注册启用的快捷键
            for key, shortcut in self._shortcuts.items():
                if shortcut.enabled:
                    self._register_single_shortcut(key, shortcut)
            
            self._is_registered = True
            return True
        except Exception as e:
            print(f"注册快捷键失败: {e}")
            return False
    
    def unregister_shortcuts(self) -> bool:
        """
        注销所有快捷键
        
        Returns:
            bool: 注销是否成功
        """
        try:
            # 清除Qt快捷键对象
            for key, qt_shortcut in self._qt_shortcuts.items():
                qt_shortcut.setEnabled(False)
                qt_shortcut.deleteLater()
            
            self._qt_shortcuts.clear()
            self._is_registered = False
            return True
        except Exception as e:
            print(f"注销快捷键失败: {e}")
            return False
    
    def _register_single_shortcut(self, key: str, shortcut: Shortcut):
        """注册单个快捷键"""
        if not self._parent_widget:
            return
        
        # 创建Qt快捷键
        qt_shortcut = QShortcut(QKeySequence(key), self._parent_widget)
        qt_shortcut.activated.connect(lambda k=key: self._on_shortcut_activated(k))
        
        self._qt_shortcuts[key] = qt_shortcut
    
    def _on_shortcut_activated(self, key: str):
        """快捷键被激活时的处理"""
        shortcut = self._shortcuts.get(key)
        if shortcut and shortcut.enabled:
            # 发送信号
            self.shortcut_triggered.emit(key)
            
            # 调用回调
            callback = self._action_callbacks.get(shortcut.action)
            if callback:
                callback()
    
    def check_shortcut_conflict(self, key: str) -> Tuple[bool, Optional[str]]:
        """
        检查快捷键冲突
        
        Args:
            key: 快捷键
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有冲突, 冲突的动作)
        """
        # 检查系统快捷键
        if key.lower() in SYSTEM_SHORTCUTS:
            return True, "system"
        
        # 检查已注册的快捷键
        existing = self._shortcuts.get(key)
        if existing:
            return True, existing.action
        
        return False, None
    
    def add_shortcut(self, shortcut: Shortcut) -> bool:
        """
        添加快捷键
        
        Args:
            shortcut: 快捷键配置
            
        Returns:
            bool: 添加是否成功
        """
        if not shortcut.key or not shortcut.action:
            return False
        
        # 检查冲突
        has_conflict, _ = self.check_shortcut_conflict(shortcut.key)
        if has_conflict:
            return False
        
        # 添加快捷键
        self._shortcuts[shortcut.key] = shortcut
        
        # 如果已注册，注册新快捷键
        if self._is_registered and shortcut.enabled:
            self._register_single_shortcut(shortcut.key, shortcut)
        
        # 保存配置
        self._save_shortcut_preference()
        
        return True
    
    def remove_shortcut(self, key: str) -> bool:
        """
        移除快捷键
        
        Args:
            key: 快捷键
            
        Returns:
            bool: 移除是否成功
        """
        if key not in self._shortcuts:
            return False
        
        # 不允许移除系统快捷键
        if key.lower() in SYSTEM_SHORTCUTS:
            return False
        
        # 移除Qt快捷键
        qt_shortcut = self._qt_shortcuts.pop(key, None)
        if qt_shortcut:
            qt_shortcut.setEnabled(False)
            qt_shortcut.deleteLater()
        
        # 移除配置
        del self._shortcuts[key]
        
        # 保存配置
        self._save_shortcut_preference()
        
        return True
    
    def update_shortcut(self, key: str, shortcut: Shortcut) -> bool:
        """
        更新快捷键
        
        Args:
            key: 原快捷键
            shortcut: 新配置
            
        Returns:
            bool: 更新是否成功
        """
        # 如果键发生变化
        if key != shortcut.key:
            # 检查新键的冲突
            has_conflict, _ = self.check_shortcut_conflict(shortcut.key)
            if has_conflict:
                return False
            
            # 移除旧键
            self.remove_shortcut(key)
            
            # 添加新键
            return self.add_shortcut(shortcut)
        else:
            # 键未变化，直接更新配置
            if key in self._shortcuts:
                self._shortcuts[key] = shortcut
                self._save_shortcut_preference()
                return True
            return False
    
    def enable_shortcut(self, key: str) -> bool:
        """
        启用快捷键
        
        Args:
            key: 快捷键
            
        Returns:
            bool: 启用是否成功
        """
        shortcut = self._shortcuts.get(key)
        if not shortcut:
            return False
        
        shortcut.enabled = True
        
        # 如果已注册，注册快捷键
        if self._is_registered:
            self._register_single_shortcut(key, shortcut)
        
        self._save_shortcut_preference()
        return True
    
    def disable_shortcut(self, key: str) -> bool:
        """
        禁用快捷键
        
        Args:
            key: 快捷键
            
        Returns:
            bool: 禁用是否成功
        """
        shortcut = self._shortcuts.get(key)
        if not shortcut:
            return False
        
        shortcut.enabled = False
        
        # 移除Qt快捷键
        qt_shortcut = self._qt_shortcuts.pop(key, None)
        if qt_shortcut:
            qt_shortcut.setEnabled(False)
            qt_shortcut.deleteLater()
        
        self._save_shortcut_preference()
        return True
    
    def register_action_callback(self, action: str, callback: Callable):
        """
        注册动作回调
        
        Args:
            action: 动作名称
            callback: 回调函数
        """
        self._action_callbacks[action] = callback
    
    def unregister_action_callback(self, action: str):
        """
        注销动作回调
        
        Args:
            action: 动作名称
        """
        self._action_callbacks.pop(action, None)
    
    def trigger_shortcut(self, key: str) -> bool:
        """
        手动触发快捷键
        
        Args:
            key: 快捷键
            
        Returns:
            bool: 触发是否成功
        """
        shortcut = self._shortcuts.get(key)
        if not shortcut or not shortcut.enabled:
            return False
        
        # 调用回调
        callback = self._action_callbacks.get(shortcut.action)
        if callback:
            callback()
            return True
        
        return False
    
    def _load_default_shortcuts(self):
        """加载默认快捷键"""
        self._shortcuts = DEFAULT_SHORTCUTS.copy()
    
    def _save_shortcut_preference(self) -> bool:
        """
        保存快捷键偏好设置
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保配置目录存在
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            
            # 保存配置
            config = {
                "shortcuts": {key: s.to_dict() for key, s in self._shortcuts.items()}
            }
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存快捷键偏好失败: {e}")
            return False
    
    def _load_shortcut_preference(self) -> bool:
        """
        加载快捷键偏好设置
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(self.CONFIG_FILE):
                return False
            
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载快捷键配置
            shortcuts_data = config.get("shortcuts", {})
            for key, data in shortcuts_data.items():
                self._shortcuts[key] = Shortcut.from_dict(data)
            
            return True
        except Exception as e:
            print(f"加载快捷键偏好失败: {e}")
            return False
    
    def save_shortcut_preference(self) -> bool:
        """保存快捷键偏好设置"""
        return self._save_shortcut_preference()
    
    def load_shortcut_preference(self) -> bool:
        """加载快捷键偏好设置"""
        return self._load_shortcut_preference()
    
    def reset_to_default(self) -> bool:
        """
        重置为默认快捷键
        
        Returns:
            bool: 重置是否成功
        """
        # 注销现有快捷键
        self.unregister_shortcuts()
        
        # 加载默认快捷键
        self._load_default_shortcuts()
        
        # 保存配置
        self._save_shortcut_preference()
        
        # 重新注册
        if self._is_registered:
            self.register_shortcuts()
        
        return True