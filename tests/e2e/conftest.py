"""E2E 测试配置"""
import pytest
import sys
from pathlib import Path

# 确保项目根目录在 sys.path（pytest 运行目录已包含）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
