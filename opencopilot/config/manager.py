"""
配置管理器桥接

统一入口：所有 ConfigManager 引用收敛至根 config_manager.py。
此文件保留向后兼容。
"""
from config_manager import *  # noqa: F401, F403
from config_manager import ConfigManager  # noqa: F401
