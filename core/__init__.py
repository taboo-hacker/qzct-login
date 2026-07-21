"""
核心包

提供配置管理、加密系统、农历工具、日期判断、常量、异常等核心功能。
"""

from core.config import (
    DEFAULT_CONFIG,
    ISP_MAPPING,
    WEEKDAY_MAPPING,
    ConfigManager,
    change_master_password,
    current_derived_key,
    get_config_snapshot,
    global_config,
    load_config,
    save_config,
)
from core.date_rules import should_work_today
from core.encryption import (
    MASTER_PASSWORD_KEY,
    decrypt_data,
    encrypt_data,
    generate_derived_key_from_master_password,
    is_encrypted,
)
from core.holidays import COMPENSATORY_WORKDAYS, HOLIDAY_PERIODS
from core.lunar import LunarUtils

__all__ = [
    # 配置
    "DEFAULT_CONFIG",
    "ISP_MAPPING",
    "WEEKDAY_MAPPING",
    "ConfigManager",
    "change_master_password",
    "current_derived_key",
    "get_config_snapshot",
    "global_config",
    "load_config",
    "save_config",
    # 加密
    "MASTER_PASSWORD_KEY",
    "decrypt_data",
    "encrypt_data",
    "generate_derived_key_from_master_password",
    "is_encrypted",
    # 假期数据
    "COMPENSATORY_WORKDAYS",
    "HOLIDAY_PERIODS",
    # 农历
    "LunarUtils",
    # 日期判断
    "should_work_today",
]
