"""
核心包

提供配置管理、日期判断、常量、异常等核心功能。
（v1.4.1 起已移除加密系统，密码以明文保存在配置文件中。）
"""

from core.config import (
    DEFAULT_CONFIG,
    ISP_MAPPING,
    WEEKDAY_MAPPING,
    ConfigManager,
    get_config_snapshot,
    global_config,
    load_config,
    save_config,
)
from core.date_rules import should_work_today
from core.holidays import COMPENSATORY_WORKDAYS, HOLIDAY_PERIODS

__all__ = [
    # 配置
    "DEFAULT_CONFIG",
    "ISP_MAPPING",
    "WEEKDAY_MAPPING",
    "ConfigManager",
    "get_config_snapshot",
    "global_config",
    "load_config",
    "save_config",
    # 假期数据
    "COMPENSATORY_WORKDAYS",
    "HOLIDAY_PERIODS",
    # 日期判断
    "should_work_today",
]
