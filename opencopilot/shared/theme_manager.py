"""
主题管理器 - 支持明暗主题切换，提升办公场景视觉舒适度
"""

import json
import os
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class Theme:
    """主题配置"""
    name: str
    background: str
    text: str
    accent: str = "#007AFF"
    border: str = "#3a3a3a"
    hover: str = "#404040"
    card_bg: str = "#2d2d2d"
    input_bg: str = "#363636"
    button_bg: str = "#007AFF"
    button_text: str = "#ffffff"
    shadow: str = "rgba(0,0,0,0.3)"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "background": self.background,
            "text": self.text,
            "accent": self.accent,
            "border": self.border,
            "hover": self.hover,
            "card_bg": self.card_bg,
            "input_bg": self.input_bg,
            "button_bg": self.button_bg,
            "button_text": self.button_text,
            "shadow": self.shadow
        }
    
    def get_stylesheet(self) -> str:
        """获取QSS样式表"""
        return f"""
        QWidget {{
            background-color: {self.background};
            color: {self.text};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        
        QFrame#card {{
            background-color: {self.card_bg};
            border: 1px solid {self.border};
            border-radius: 12px;
        }}
        
        QLineEdit, QTextEdit {{
            background-color: {self.input_bg};
            border: 1px solid {self.border};
            border-radius: 6px;
            padding: 8px;
            color: {self.text};
        }}
        
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {self.accent};
        }}
        
        QPushButton {{
            background-color: {self.button_bg};
            color: {self.button_text};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            opacity: 0.9;
        }}
        
        QPushButton:pressed {{
            opacity: 0.8;
        }}
        
        QPushButton#secondary {{
            background-color: {self.hover};
            color: {self.text};
        }}
        
        QLabel {{
            color: {self.text};
        }}
        
        QRadioButton {{
            color: {self.text};
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid {self.border};
            background-color: {self.input_bg};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {self.accent};
            border-color: {self.accent};
        }}
        """


# 预定义主题
DARK_THEME = Theme(
    name="暗色主题",
    background="#2b2b2b",
    text="#ffffff",
    accent="#007AFF",
    border="#3a3a3a",
    hover="#404040",
    card_bg="#2d2d2d",
    input_bg="#363636",
    button_bg="#007AFF",
    button_text="#ffffff",
    shadow="rgba(0,0,0,0.3)"
)

LIGHT_THEME = Theme(
    name="亮色主题",
    background="#f5f5f5",
    text="#333333",
    accent="#007AFF",
    border="#e0e0e0",
    hover="#e8e8e8",
    card_bg="#ffffff",
    input_bg="#f0f0f0",
    button_bg="#007AFF",
    button_text="#ffffff",
    shadow="rgba(0,0,0,0.1)"
)

OFFICE_THEME = Theme(
    name="办公主题",
    background="#f8f9fa",
    text="#2c3e50",
    accent="#2980b9",
    border="#dee2e6",
    hover="#e9ecef",
    card_bg="#ffffff",
    input_bg="#f1f3f5",
    button_bg="#2980b9",
    button_text="#ffffff",
    shadow="rgba(0,0,0,0.08)"
)


class ThemeManager(QObject):
    """主题管理器"""
    
    # 主题切换信号
    theme_changed = pyqtSignal(str)
    
    # 配置文件路径
    CONFIG_DIR = os.path.expanduser("~/.opencopilot")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "theme_config.json")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 注册内置主题
        self._themes: Dict[str, Theme] = {
            "dark": DARK_THEME,
            "light": LIGHT_THEME,
            "office": OFFICE_THEME
        }
        
        # 当前主题
        self._current_theme_name: str = "dark"
        
        # 加载用户偏好
        self._load_theme_preference()
    
    @property
    def current_theme(self) -> str:
        """获取当前主题名称"""
        return self._current_theme_name
    
    @property
    def current_theme_config(self) -> Theme:
        """获取当前主题配置"""
        return self._themes.get(self._current_theme_name, DARK_THEME)
    
    def get_themes(self) -> Dict[str, Theme]:
        """获取所有主题"""
        return self._themes.copy()
    
    def get_theme(self, theme_name: str) -> Optional[Theme]:
        """获取指定主题"""
        return self._themes.get(theme_name)
    
    def get_theme_config(self, theme_name: str = None) -> Optional[Theme]:
        """获取主题配置"""
        if theme_name is None:
            theme_name = self._current_theme_name
        return self._themes.get(theme_name)
    
    def switch_theme(self, theme_name: str) -> bool:
        """
        切换主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            bool: 切换是否成功
        """
        if theme_name not in self._themes:
            return False
        
        # 如果是相同主题，不做任何操作
        if theme_name == self._current_theme_name:
            return True
        
        # 切换主题
        self._current_theme_name = theme_name
        
        # 保存用户偏好
        self._save_theme_preference()
        
        # 发送信号
        self.theme_changed.emit(theme_name)
        
        return True
    
    def register_theme(self, theme_name: str, theme: Theme) -> bool:
        """
        注册自定义主题
        
        Args:
            theme_name: 主题名称
            theme: 主题配置
            
        Returns:
            bool: 注册是否成功
        """
        if not theme_name or not theme:
            return False
        
        self._themes[theme_name] = theme
        return True
    
    def unregister_theme(self, theme_name: str) -> bool:
        """
        注销主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            bool: 注销是否成功
        """
        # 不允许注销内置主题
        if theme_name in ["dark", "light", "office"]:
            return False
        
        if theme_name not in self._themes:
            return False
        
        # 如果是当前主题，切换到默认主题
        if theme_name == self._current_theme_name:
            self.switch_theme("dark")
        
        del self._themes[theme_name]
        return True
    
    def get_stylesheet(self) -> str:
        """获取当前主题的样式表"""
        return self.current_theme_config.get_stylesheet()
    
    def _save_theme_preference(self) -> bool:
        """
        保存主题偏好设置
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保配置目录存在
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            
            # 保存配置
            config = {
                "current_theme": self._current_theme_name
            }
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存主题偏好失败: {e}")
            return False
    
    def _load_theme_preference(self) -> bool:
        """
        加载主题偏好设置
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(self.CONFIG_FILE):
                return False
            
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证并应用主题
            theme_name = config.get("current_theme", "dark")
            if theme_name in self._themes:
                self._current_theme_name = theme_name
                return True
            
            return False
        except Exception as e:
            print(f"加载主题偏好失败: {e}")
            return False
    
    def save_theme_preference(self, theme_name: str) -> bool:
        """
        保存指定主题的偏好设置
        
        Args:
            theme_name: 主题名称
            
        Returns:
            bool: 保存是否成功
        """
        if theme_name not in self._themes:
            return False
        
        self._current_theme_name = theme_name
        return self._save_theme_preference()
    
    def load_theme_preference(self) -> str:
        """
        加载主题偏好设置
        
        Returns:
            str: 加载的主题名称
        """
        self._load_theme_preference()
        return self._current_theme_name