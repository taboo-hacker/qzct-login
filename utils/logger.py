"""
Loguru 日志系统配置

提供日志器初始化和配置。本模块不依赖 PySide6：GUI 日志投递由调用方
（gui 层）传入可写回调（gui/log_sink.py 的 QtLogSink.write），
依赖方向保持 utils ← gui，不形成包级循环。

三个 sink（按配置启用）：
    GUI   → gui_sink 回调（QtLogSink，跨线程 Signal 投递到主线程）
    文件  → log_file 参数指定的路径（轮转 + zip 压缩 + 保留期清理）
    终端  → sys.stderr 彩色输出（打包 console=False 模式下自动跳过）
"""

import os
import sys
from collections.abc import Callable
from typing import Any

from loguru import logger

from infra.file_permissions import restrict_file_permissions


def setup_logger(
    gui_sink: Callable[[str], None] | None = None,
    log_file: str | None = None,
    level: str = "INFO",
    max_size: str = "10 MB",
    retention: str = "30 days",
) -> Any:
    """
    配置 Loguru 日志系统

    Args:
        gui_sink: GUI 日志写入回调（接收格式化后的整行消息），
            由调用方绑定具体控件实现，None 表示不启用 GUI sink
        log_file: 日志文件路径
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_size: 日志文件最大大小，默认 10 MB（超过后轮转）
        retention: 日志保留时间，默认 30 天（过期归档自动删除）

    Returns:
        Loguru logger 实例
    """
    # 先移除 loguru 默认的 stderr sink，避免与下面自定义的终端 sink 重复
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

    if gui_sink is not None:
        logger.add(
            gui_sink,
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
        restrict_file_permissions(log_file)

        # 轮转后新文件的权限由 main() 设置的进程 umask(0o077) 覆盖（POSIX）；
        # 初始文件的显式收权见上方 restrict_file_permissions；Windows 下继承用户目录 ACL
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
