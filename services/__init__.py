"""
业务服务包

提供 WiFi 连接、校园网登录、关机操作、任务链编排等业务功能。
"""

from services.campus_login import campus_login, parse_jsonp
from services.shutdown import cancel_shutdown, set_shutdown_timer
from services.tasks import (
    task_campus_login,
    task_check_condition,
    task_connect_wifi,
    task_set_shutdown,
)
from services.wifi import (
    auto_connect_wifi,
    connect_wifi,
    create_windows_wifi_profile,
    is_wifi_connected,
)

__all__ = [
    # 关机
    "cancel_shutdown",
    "set_shutdown_timer",
    # WiFi
    "auto_connect_wifi",
    "connect_wifi",
    "create_windows_wifi_profile",
    "is_wifi_connected",
    # 校园网登录
    "campus_login",
    "parse_jsonp",
    # 任务
    "task_campus_login",
    "task_check_condition",
    "task_connect_wifi",
    "task_set_shutdown",
]
