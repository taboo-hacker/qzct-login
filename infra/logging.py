"""
日志系统模块（基于 Loguru）

提供日志器初始化、日志级别映射、输出流重定向等功能。
"""

import sys
from typing import Any, Optional

from utils.logger import setup_logger

# ==========================================
# 类型定义
# ==========================================
LogLevel = int

LOG_LEVEL_MAP: dict[int, str] = {
    0: "DEBUG",
    1: "INFO",
    2: "WARNING",
    3: "ERROR",
    4: "CRITICAL",
}

logger: Optional["Logger"] = None


class Logger:
    """
    向后兼容的日志包装类

    保持与原 Logger API 一致，内部使用 Loguru。
    """

    def __init__(
        self,
        gui_log_widget: Any | None = None,
        log_file_path: str | None = None,
        level: int = 1,
        max_log_size: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """
        初始化日志器

        Args:
            gui_log_widget: GUI 日志显示组件
            log_file_path: 日志文件路径
            level: 日志级别 (0-4)
            max_log_size: 最大日志文件大小（字节）
            backup_count: 备份文件数量
        """
        global logger
        logger = self

        max_size_mb = max_log_size / (1024 * 1024)
        rotation_str = f"{max_size_mb:.0f} MB"
        retention_days = backup_count * 7

        self._loguru_logger = setup_logger(
            gui_widget=gui_log_widget,
            log_file=log_file_path,
            level=LOG_LEVEL_MAP.get(level, "INFO"),
            max_size=rotation_str,
            retention=f"{retention_days} days",
        )

    def log(
        self,
        module_name: str,
        level: int,
        message: str,
        exc_info: bool = False,
        from_handler: bool = False,
    ) -> None:
        """
        记录日志

        Args:
            module_name: 模块名称
            level: 日志级别 (0-4)
            message: 日志消息
            exc_info: 是否包含异常信息
            from_handler: 是否来自处理器
        """
        std_level = LOG_LEVEL_MAP.get(level, "INFO")
        if exc_info and level >= 3:
            self._loguru_logger.opt(exception=True).log(
                std_level,
                "<magenta><{name}></magenta> {message}",
                name=module_name,
                message=message,
            )
        else:
            self._loguru_logger.log(
                std_level,
                "<magenta><{name}></magenta> {message}",
                name=module_name,
                message=message,
            )

    def debug(self, module_name: str, message: str, exc_info: bool = False) -> None:
        """记录 DEBUG 级别日志"""
        self.log(module_name, 0, message, exc_info)

    def info(self, module_name: str, message: str, exc_info: bool = False) -> None:
        """记录 INFO 级别日志"""
        self.log(module_name, 1, message, exc_info)

    def warning(self, module_name: str, message: str, exc_info: bool = False) -> None:
        """记录 WARNING 级别日志"""
        self.log(module_name, 2, message, exc_info)

    def error(self, module_name: str, message: str, exc_info: bool = False) -> None:
        """记录 ERROR 级别日志"""
        self.log(module_name, 3, message, exc_info)

    def critical(self, module_name: str, message: str, exc_info: bool = False) -> None:
        """记录 CRITICAL 级别日志"""
        self.log(module_name, 4, message, exc_info)


def init_logger(
    gui_log_widget: Any | None = None,
    log_file_path: str | None = None,
    level: int = 1,
) -> Logger:
    """
    初始化全局日志对象

    Args:
        gui_log_widget: GUI 日志显示组件
        log_file_path: 日志文件路径
        level: 日志级别 (0-4)

    Returns:
        初始化后的 Logger 实例
    """
    global logger
    logger = Logger(gui_log_widget=gui_log_widget, log_file_path=log_file_path, level=level)
    return logger


def debug(module_name: str, message: str, exc_info: bool = False) -> None:
    """记录 DEBUG 级别日志"""
    if logger:
        logger.debug(module_name, message, exc_info)


def info(module_name: str, message: str, exc_info: bool = False) -> None:
    """记录 INFO 级别日志"""
    if logger:
        logger.info(module_name, message, exc_info)


def warning(module_name: str, message: str, exc_info: bool = False) -> None:
    """记录 WARNING 级别日志"""
    if logger:
        logger.warning(module_name, message, exc_info)


def error(module_name: str, message: str, exc_info: bool = True) -> None:
    """记录 ERROR 级别日志

    exc_info 默认 True，但只有在 except 块内（sys.exc_info()[0] 不为 None）
    时才真正附加堆栈。在非异常上下文调用 error() 也不会触发 loguru 的
    "no active exception" 警告。
    """
    if not logger:
        return
    has_active_exception = sys.exc_info()[0] is not None
    logger.error(module_name, message, exc_info=exc_info and has_active_exception)


def critical(module_name: str, message: str, exc_info: bool = True) -> None:
    """记录 CRITICAL 级别日志"""
    if not logger:
        return
    has_active_exception = sys.exc_info()[0] is not None
    logger.critical(module_name, message, exc_info=exc_info and has_active_exception)


class StreamRedirector:
    """
    输出流重定向器

    将 Python 的标准输出和标准错误重定向到日志系统。
    """

    def __init__(self, module_name: str = "stdout", level: int = 1) -> None:
        """
        初始化输出流重定向器

        Args:
            module_name: 模块名称
            level: 日志级别
        """
        self.module_name = module_name
        self.level = level

    def write(self, text: str) -> None:
        """
        写入文本到日志系统

        Args:
            text: 要写入的文本
        """
        if text.strip() and logger:
            logger.log(self.module_name, self.level, text.strip())

    def flush(self) -> None:
        """刷新输出缓冲区（空实现，保持兼容）"""
        pass

    def isatty(self) -> bool:
        """
        判断是否为终端设备

        Returns:
            始终返回 False，因为这是重定向流
        """
        return False

    def fileno(self) -> int:
        """
        获取文件描述符

        返回标准错误流的文件描述符作为回退。

        Returns:
            文件描述符
        """
        if sys.__stderr__ is not None:
            return sys.__stderr__.fileno()
        return -1

    def readable(self) -> bool:
        """
        判断是否可读

        Returns:
            始终返回 False
        """
        return False

    def writable(self) -> bool:
        """
        判断是否可写

        Returns:
            始终返回 True
        """
        return True

    def seekable(self) -> bool:
        """
        判断是否可搜索

        Returns:
            始终返回 False
        """
        return False
