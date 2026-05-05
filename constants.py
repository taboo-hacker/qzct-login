"""
常量配置模块

集中管理项目中的硬编码配置值。
"""

import os

# ==========================================
# 校园网登录配置
# ==========================================
CAMPUS_LOGIN_CONFIG = {
    "login_url": "http://192.168.51.2:801/eportal/portal/login",
    "referer": "http://192.168.51.2/",
    "callback": "dr1004",
    "version": "7213",
    "js_version": "4.2.2",
    "timeout": 15,
}

CAMPUS_LOGIN_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Connection": "keep-alive",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    ),
}

# ==========================================
# WiFi 配置
# ==========================================
WIFI_CONFIG = {
    "connection_wait_seconds": 5,
    "profile_authentication": "WPA2PSK",
    "profile_encryption": "AES",
}

# ==========================================
# 关机配置
# ==========================================
SHUTDOWN_CONFIG = {
    "default_hour": 23,
    "default_minute": 0,
}

# ==========================================
# 重试配置
# ==========================================
RETRY_CONFIG = {
    "max_wifi_retry": 10,
    "retry_interval_seconds": 5,
}

# ==========================================
# 加密配置
# ==========================================
ENCRYPTION_CONFIG = {
    "pbkdf2_iterations": 600000,
    "salt_length": 16,
    "key_length": 32,
}

# ==========================================
# 线程池配置
# ==========================================
THREAD_POOL_CONFIG = {
    "max_threads_multiplier": 4,
    "max_threads_limit": 16,
    "stack_size_kb": 1024,
}

# ==========================================
# 日志配置
# ==========================================
LOG_CONFIG = {
    "default_level": 1,  # INFO
    "max_file_size_mb": 10,
    "backup_count": 5,
    "retention_days": 35,
}

# ==========================================
# GUI 配置
# ==========================================
GUI_CONFIG = {
    "window_width": 860,
    "window_height": 620,
    "corner_radius": 12,
    "shadow_margin": 6,
    "shadow_blur": 5,
    "shadow_opacity": 30,
}

# ==========================================
# 配置文件路径
# ==========================================
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".qzct")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
KEY_FILE = os.path.join(CONFIG_DIR, "encryption_key.key")
SALT_FILE = os.path.join(CONFIG_DIR, "encryption_salt.key")
