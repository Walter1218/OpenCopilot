"""AppEnv — 应用运行环境配置

通过 APP_ENV 环境变量区分开发(dev)和生产(prod)模式：
    export APP_ENV=dev   # 开发模式（默认）
    export APP_ENV=prod  # 生产模式

用法:
    from gui.v5.env import AppEnv
    if AppEnv.is_dev():
        print("调试信息")
    if AppEnv.is_prod():
        # 生产模式行为
        pass
"""
import os
import sys


class AppEnv:
    """应用环境配置类"""

    _env = None

    @classmethod
    def _get_env(cls) -> str:
        if cls._env is None:
            cls._env = os.environ.get("APP_ENV", "dev").lower()
        return cls._env

    @classmethod
    def is_dev(cls) -> bool:
        """是否为开发模式"""
        return cls._get_env() == "dev"

    @classmethod
    def is_prod(cls) -> bool:
        """是否为生产模式"""
        return cls._get_env() == "prod"

    @classmethod
    def log_level(cls) -> str:
        """返回日志级别"""
        return "DEBUG" if cls.is_dev() else "INFO"

    @classmethod
    def should_show_error_dialog(cls) -> bool:
        """错误时是否弹出对话框（开发模式弹窗，生产模式静默）"""
        return cls.is_dev()

    @classmethod
    def should_print_debug(cls) -> bool:
        """是否打印调试输出"""
        return cls.is_dev()

    @classmethod
    def mode_label(cls) -> str:
        """返回模式标签（用于日志/标题）"""
        return "DEV" if cls.is_dev() else "PROD"


# 全局便捷函数
def is_dev() -> bool:
    return AppEnv.is_dev()


def is_prod() -> bool:
    return AppEnv.is_prod()


def debug_print(*args, **kwargs):
    """开发模式下打印，生产模式下忽略"""
    if AppEnv.should_print_debug():
        print(*args, **kwargs)


def setup_logging():
    """根据环境配置日志级别"""
    import logging
    level = logging.DEBUG if AppEnv.is_dev() else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("opencopilot")
