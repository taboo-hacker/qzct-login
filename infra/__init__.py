"""
基础设施包

提供日志系统、日期工具、线程池并发调度（Qt Signal 回报）等基础设施。
并发框架绑定 PySide6（Signal 跨线程投递），与桌面应用共进退。
"""

from infra.concurrency import TaskChain, TaskContext, TaskExecutor, task
from infra.date_utils import is_date_in_period, parse_date_str
from infra.file_permissions import restrict_file_permissions
from infra.logging import (
    Logger,
    StreamRedirector,
    critical,
    debug,
    error,
    info,
    init_logger,
    warning,
)

__all__ = [
    # 并发
    "TaskChain",
    "TaskContext",
    "TaskExecutor",
    "task",
    # 日志
    "Logger",
    "StreamRedirector",
    "critical",
    "debug",
    "error",
    "info",
    "init_logger",
    "warning",
    # 文件权限
    "restrict_file_permissions",
    # 日期工具
    "is_date_in_period",
    "parse_date_str",
]
