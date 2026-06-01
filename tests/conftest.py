# tests/conftest.py

"""
测试目录的 pytest 配置文件

设置 Python 路径，确保模块可以正确导入。
"""

import sys
import os

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
