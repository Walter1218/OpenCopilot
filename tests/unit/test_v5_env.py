"""AppEnv 环境配置测试

验证开发/生产模式区分、日志级别、路径配置等。
"""
import os
import pytest
from unittest.mock import patch


# =============================================================================
# 1. 环境模式检测
# =============================================================================

class TestAppEnvMode:
    """AppEnv 模式检测测试"""

    def test_default_is_dev(self):
        """默认应为开发模式"""
        from gui.v5.env import AppEnv
        # 清除缓存
        AppEnv._env = None
        with patch.dict(os.environ, {}, clear=True):
            assert AppEnv.is_dev() is True
            assert AppEnv.is_prod() is False

    def test_dev_mode(self):
        """APP_ENV=dev 应为开发模式"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            assert AppEnv.is_dev() is True
            assert AppEnv.is_prod() is False

    def test_prod_mode(self):
        """APP_ENV=prod 应为生产模式"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert AppEnv.is_dev() is False
            assert AppEnv.is_prod() is True

    def test_case_insensitive(self):
        """环境变量应大小写不敏感"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "PROD"}):
            assert AppEnv.is_prod() is True

        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "Dev"}):
            assert AppEnv.is_dev() is True

    def test_invalid_mode_treats_as_dev(self):
        """无效值被当作非 prod 处理（log_level 返回 INFO，因为 is_dev 为 False）"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "invalid"}, clear=True):
            # 当前实现：is_dev 检查 == "dev"，is_prod 检查 == "prod"
            # 无效值 "invalid" 既不是 dev 也不是 prod
            assert AppEnv.is_dev() is False
            assert AppEnv.is_prod() is False
            # log_level 在 is_dev 为 False 时返回 INFO
            assert AppEnv.log_level() == "INFO"


# =============================================================================
# 2. 日志级别
# =============================================================================

class TestAppEnvLogLevel:
    """日志级别测试"""

    def test_dev_log_level(self):
        """开发模式日志级别为 DEBUG"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            assert AppEnv.log_level() == "DEBUG"

    def test_prod_log_level(self):
        """生产模式日志级别为 INFO"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert AppEnv.log_level() == "INFO"


# =============================================================================
# 3. 错误对话框配置
# =============================================================================

class TestAppEnvErrorDialog:
    """错误对话框配置测试"""

    def test_dev_shows_error_dialog(self):
        """开发模式应显示错误对话框"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            assert AppEnv.should_show_error_dialog() is True

    def test_prod_hides_error_dialog(self):
        """生产模式应隐藏错误对话框"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert AppEnv.should_show_error_dialog() is False


# =============================================================================
# 4. 调试输出配置
# =============================================================================

class TestAppEnvDebugPrint:
    """调试输出配置测试"""

    def test_dev_allows_debug_print(self):
        """开发模式应允许调试输出"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            assert AppEnv.should_print_debug() is True

    def test_prod_suppresses_debug_print(self):
        """生产模式应抑制调试输出"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert AppEnv.should_print_debug() is False


# =============================================================================
# 5. 模式标签
# =============================================================================

class TestAppEnvModeLabel:
    """模式标签测试"""

    def test_dev_label(self):
        """开发模式标签应为 DEV"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}):
            assert AppEnv.mode_label() == "DEV"

    def test_prod_label(self):
        """生产模式标签应为 PROD"""
        from gui.v5.env import AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}):
            assert AppEnv.mode_label() == "PROD"


# =============================================================================
# 6. 便捷函数
# =============================================================================

class TestAppEnvConvenienceFunctions:
    """便捷函数测试"""

    def test_is_dev_function(self):
        """is_dev() 便捷函数"""
        from gui.v5.env import is_dev, AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
            assert is_dev() is True

    def test_is_prod_function(self):
        """is_prod() 便捷函数"""
        from gui.v5.env import is_prod, AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}, clear=True):
            assert is_prod() is True

    def test_debug_print_in_dev(self, capsys):
        """开发模式下 debug_print 应输出"""
        from gui.v5.env import debug_print, AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
            debug_print("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_debug_print_in_prod(self, capsys):
        """生产模式下 debug_print 应忽略"""
        from gui.v5.env import debug_print, AppEnv
        AppEnv._env = None
        with patch.dict(os.environ, {"APP_ENV": "prod"}, clear=True):
            debug_print("should not appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.out


# =============================================================================
# 7. setup_logging
# =============================================================================

class TestAppEnvSetupLogging:
    """日志配置测试"""

    def test_setup_logging_returns_logger(self):
        """setup_logging 应返回 logger"""
        from gui.v5.env import setup_logging
        import logging

        with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
            logger = setup_logging()
            assert isinstance(logger, logging.Logger)
            assert logger.name == "opencopilot"

    def test_setup_logging_dev_level(self):
        """开发模式日志级别应为 DEBUG"""
        from gui.v5.env import setup_logging, AppEnv
        import logging

        AppEnv._env = None
        # 先清除可能存在的 logging 配置
        root = logging.getLogger()
        root.handlers = []
        with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
            logger = setup_logging()
            # basicConfig 设置的是 root logger 级别，子 logger 继承
            assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_prod_level(self):
        """生产模式日志级别应为 INFO"""
        from gui.v5.env import setup_logging, AppEnv
        import logging

        AppEnv._env = None
        root = logging.getLogger()
        root.handlers = []
        with patch.dict(os.environ, {"APP_ENV": "prod"}, clear=True):
            logger = setup_logging()
            assert logging.getLogger().level == logging.INFO
