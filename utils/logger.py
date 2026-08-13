"""
Loguru 日志系统配置

提供日志器初始化和配置。QtLogSink 已移至 gui/log_sink.py，
本模块通过延迟导入使用，使 utils/ 层不再在模块加载时耦合 PySide6。
"""

import os
import sys
from typing import Any

from loguru import logger


def _restrict_file_permissions(filepath: str) -> None:
    """限制文件权限，使其仅当前用户可读写（Windows: icacls，POSIX: chmod 600）。

    失败不阻断日志初始化。
    """
    try:
        if sys.platform == "win32":
            import getpass
            import subprocess

            subprocess.run(
                ["icacls", filepath, "/inheritance:r", "/grant:r", f"{getpass.getuser()}:F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        else:
            os.chmod(filepath, 0o600)
    except Exception:
        pass


def setup_logger(
    gui_widget: Any = None,
    log_file: str | None = None,
    level: str = "INFO",
    max_size: str = "10 MB",
    retention: str = "30 days",
) -> Any:
    """
    配置 Loguru 日志系统

    Args:
        gui_widget: PyQt QTextEdit 组件，用于显示日志
        log_file: 日志文件路径
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_size: 日志文件最大大小，默认 10 MB
        retention: 日志保留时间，默认 30 天

    Returns:
        Loguru logger 实例
    """
    logger.remove()

    # 纯文本格式（GUI + 文件）
    plain_format = "[{time:YYYY-MM-DD HH:mm:ss.SSS}] [{name}] [{level}] {message}"

    # 终端彩色格式
    terminal_format = (
        "<light-black>[{time:YYYY-MM-DD HH:mm:ss.SSS}]</light-black> "
        "<cyan>[{name}]</cyan> "
        "<level>[{level}]</level> "
        "{message}"
    )

    if gui_widget:
        from gui.log_sink import QtLogSink

        QtLogSink.set_gui_widget(gui_widget)
        logger.add(
            QtLogSink._instance.write,  # type: ignore[union-attr]
            level=level,
            format=plain_format + "\n",
            colorize=False,
        )

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # 预创建空日志文件并限制权限（防止敏感信息泄露）
        if not os.path.exists(log_file):
            with open(log_file, "a", encoding="utf-8"):
                pass
        _restrict_file_permissions(log_file)

        logger.add(
            log_file,
            level=level,
            format=plain_format,
            rotation=max_size,
            compression="zip",
            retention=retention,
            encoding="utf-8",
        )

    # 打包模式（PyInstaller console=False）下 sys.stderr 为 None，
    # 此时跳过终端 sink（loguru 不接受 None 流）
    if sys.stderr is not None:
        logger.add(sys.stderr, level=level, format=terminal_format, colorize=True)

    logger.info("日志系统初始化完成 [Loguru]")
    return logger


def set_gui_widget(widget: Any) -> None:
    """运行时更新 GUI 日志组件"""
    from gui.log_sink import QtLogSink

    QtLogSink.set_gui_widget(widget)
    if QtLogSink._instance and QtLogSink._pending_logs:
        QtLogSink.flush_pending_logs()


def get_logger() -> Any:
    """获取 Loguru logger 实例"""
    return logger
