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
# 配置文件路径
# ==========================================
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".qzct")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
KEY_FILE = os.path.join(CONFIG_DIR, "encryption_key.key")
SALT_FILE = os.path.join(CONFIG_DIR, "encryption_salt.key")
LOG_FILE = os.path.join(CONFIG_DIR, "qzct.log")
