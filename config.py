import os
import json
import logging
from PyQt5.QtWidgets import QMessageBox

# 配置日志
def info(module_name, message):
    logging.info(message, extra={"logger_name": module_name})

def error(module_name, message):
    logging.error(message, extra={"logger_name": module_name})
from security import load_and_update_encryption, encrypt_data, decrypt_data, is_encrypted, MASTER_PASSWORD_KEY

# ==========================================
# 配置文件管理模块
# ==========================================
# 本模块负责管理应用程序的所有配置项，包括：
# - WiFi连接配置（网络名称、密码、重试策略）
# - 校园网登录配置（用户名、密码、运营商类型）
# - 自动关机配置（关机时间）
# - 节假日规则配置（基础节假日、调休上班日、自定义规则）
# - 应用程序设置（开机自启动）
#
# 配置存储：
#     所有配置保存在 config.json 文件中
#     首次运行时自动创建默认配置文件
#
# 配置优先级：
#     1. 配置文件中的值（用户自定义）
#     2. DEFAULT_CONFIG（默认值）
# ==========================================

CONFIG_FILE = "config.json"


# ==========================================
# 默认配置
# ==========================================
# 以下配置同步国务院2025/2026年节假日安排，并结合高校假期进行调整
#
# HOLIDAY_PERIODS: 节假日时间段（不执行任务）
#     - 国务院官方节假日
#     - 高校寒假/暑假
#
# COMPENSATORY_WORKDAYS: 调休上班日（强制执行任务，优先级最高）
#     - 即使是周末也强制执行
#
# DATE_RULES: 日期规则配置
#     - ENABLE_CUSTOM_RULE: 是否启用自定义规则
#     - WEEKLY_EXECUTE_DAYS: 每周默认执行日（0=周一 ~ 6=周日）
#     - CUSTOM_HOLIDAY_PERIODS: 自定义假期时间段
#     - CUSTOM_WORKDAY_PERIODS: 自定义工作日时间段
# ==========================================
DEFAULT_CONFIG = {
    "WIFI_NAME": "",
    "WIFI_PASSWORD": "",
    "MAX_WIFI_RETRY": 10,
    "RETRY_INTERVAL": 5,
    "USERNAME": "",
    "PASSWORD": "",
    "ISP_TYPE": "telecom",
    "WAN_IP": "",
    "SHUTDOWN_HOUR": 23,
    "SHUTDOWN_MIN": 0,
    "AUTOSTART": False,
    "SHOW_LUNAR_CALENDAR": True,
    "LUNAR_DISPLAY_FORMAT": 0,
    "HOLIDAY_PERIODS": [
        {"name": "2025元旦", "start": "2025-01-01", "end": "2025-01-01"},
        {"name": "2025春节", "start": "2025-01-28", "end": "2025-02-04"},
        {"name": "2025清明", "start": "2025-04-04", "end": "2025-04-06"},
        {"name": "2025劳动节", "start": "2025-05-01", "end": "2025-05-05"},
        {"name": "2025端午", "start": "2025-05-31", "end": "2025-06-02"},
        {"name": "2025国庆中秋", "start": "2025-10-01", "end": "2025-10-08"},
        {"name": "2026元旦", "start": "2026-01-01", "end": "2026-01-03"},
        {"name": "2026春节", "start": "2026-02-15", "end": "2026-02-23"},
        {"name": "2026清明", "start": "2026-04-04", "end": "2026-04-06"},
        {"name": "2026劳动节", "start": "2026-05-01", "end": "2026-05-05"},
        {"name": "2026端午", "start": "2026-06-19", "end": "2026-06-21"},
        {"name": "2026中秋", "start": "2026-09-25", "end": "2026-09-27"},
        {"name": "2026国庆", "start": "2026-10-01", "end": "2026-10-07"},
        {"name": "2025寒假", "start": "2025-01-10", "end": "2025-02-28"},
        {"name": "2025暑假", "start": "2025-07-01", "end": "2025-08-31"},
        {"name": "2026寒假", "start": "2026-01-15", "end": "2026-02-28"},
        {"name": "2026暑假", "start": "2026-07-01", "end": "2026-08-31"},
    ],
    "COMPENSATORY_WORKDAYS": [
        "2025-01-26",
        "2025-02-08",
        "2025-04-27",
        "2025-09-28",
        "2025-10-11",
        "2026-01-04",
        "2026-02-14",
        "2026-02-28",
        "2026-05-09",
        "2026-09-20",
        "2026-10-10"
    ],
    "DATE_RULES": {
        "ENABLE_CUSTOM_RULE": False,
        "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
        "CUSTOM_HOLIDAY_PERIODS": [],
        "CUSTOM_WORKDAY_PERIODS": []
    }
}


# ==========================================
# 运营商映射表
# ==========================================
ISP_MAPPING = {
    "中国电信": "@telecom",
    "中国移动": "@cmcc",
    "中国联通": "@unicom",
    "校内资源": "@local"
}


# ==========================================
# 星期映射（便于显示）
# ==========================================
WEEKDAY_MAPPING = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日"
}


# ==========================================
# 全局配置变量
# ==========================================
global_config = DEFAULT_CONFIG.copy()
current_derived_key = None


def load_config():
    """
    加载配置文件
    
    从 config.json 文件中加载用户配置，如果文件不存在则创建默认配置。
    加载时会合并默认配置和用户配置，确保所有配置项都存在。
    同时会自动处理加密解密逻辑。
    
    Returns:
        None（直接修改 global_config 全局变量）
    """
    global global_config, current_derived_key
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
            
            # 合并默认配置和用户配置
            for key, value in DEFAULT_CONFIG.items():
                global_config[key] = value
            for key, value in loaded_config.items():
                global_config[key] = value
            
            # 处理加密解密逻辑
            master_password, current_derived_key = load_and_update_encryption(global_config)
            
            # 解密敏感信息（WiFi密码和校园网密码）
            sensitive_fields = ["WIFI_PASSWORD", "PASSWORD"]
            for field in sensitive_fields:
                if field in global_config and is_encrypted(global_config[field]):
                    try:
                        global_config[field] = decrypt_data(global_config[field], current_derived_key)
                        info("config", f"解密配置项：{field}")
                    except Exception as e:
                        error("config", f"解密 {field} 失败：{e}")
                        if field in DEFAULT_CONFIG:
                            global_config[field] = DEFAULT_CONFIG[field]
            
            # 兼容性处理
            if "ISP_SUFFIX" in global_config and "ISP_TYPE" not in global_config:
                suffix = global_config["ISP_SUFFIX"]
                for type_key, type_suffix in ISP_MAPPING.items():
                    if type_suffix == suffix:
                        global_config["ISP_TYPE"] = type_key
                        del global_config["ISP_SUFFIX"]
                        break
            
            if "COMPENSATORY_WORKDAYS" not in global_config:
                global_config["COMPENSATORY_WORKDAYS"] = DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy()
            
            if "DATE_RULES" not in global_config:
                global_config["DATE_RULES"] = DEFAULT_CONFIG["DATE_RULES"].copy()
            else:
                for key in DEFAULT_CONFIG["DATE_RULES"]:
                    if key not in global_config["DATE_RULES"]:
                        global_config["DATE_RULES"][key] = DEFAULT_CONFIG["DATE_RULES"][key]
                if "CUSTOM_HOLIDAYS" in global_config["DATE_RULES"]:
                    global_config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] = []
                    del global_config["DATE_RULES"]["CUSTOM_HOLIDAYS"]
                if "CUSTOM_WORKDAYS" in global_config["DATE_RULES"]:
                    global_config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] = []
                    del global_config["DATE_RULES"]["CUSTOM_WORKDAYS"]
            
            # 保存配置（此时会用新的派生密钥加密敏感信息）
            save_config()
            info("config", f"从 {CONFIG_FILE} 加载配置成功")
        else:
            for key, value in DEFAULT_CONFIG.items():
                global_config[key] = value
            # 首次运行，初始化加密系统
            master_password, current_derived_key = load_and_update_encryption(global_config)
            save_config()
            info("config", f"未找到配置文件，创建默认配置 {CONFIG_FILE}")
    except Exception as e:
        error("config", f"加载配置失败，使用默认配置：{e}")
        for key, value in DEFAULT_CONFIG.items():
            global_config[key] = value


def save_config():
    """
    保存配置到文件
    
    将当前 global_config 中的配置保存到 config.json 文件。
    使用UTF-8编码，支持中文配置项。
    同时会自动加密敏感信息。
    
    Returns:
        bool: 保存是否成功
    """
    try:
        config_to_save = global_config.copy()
        
        # 加密敏感信息（WiFi密码和校园网密码）
        sensitive_fields = ["WIFI_PASSWORD", "PASSWORD"]
        for field in sensitive_fields:
            if field in config_to_save and config_to_save[field] and not is_encrypted(config_to_save[field]):
                try:
                    config_to_save[field] = encrypt_data(config_to_save[field], current_derived_key)
                    info("config", f"加密配置项：{field}")
                except Exception as e:
                    error("config", f"加密 {field} 失败：{e}")
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, ensure_ascii=False, indent=4)
        info("config", f"配置已保存到 {CONFIG_FILE}")
        return True
    except Exception as e:
        error("config", f"保存配置失败：{e}")
        QMessageBox.critical(None, "错误", f"保存配置失败：{e}")
        return False
