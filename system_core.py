import os
import json
import base64
import logging
import datetime
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QApplication, QLineEdit
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from zhdate import ZhDate

# 配置日志
def info(module_name, message):
    logging.info(message, extra={"logger_name": module_name})

def error(module_name, message, exc_info=False):
    logging.error(message, extra={"logger_name": module_name}, exc_info=exc_info)

def debug(module_name, message):
    logging.debug(message, extra={"logger_name": module_name})

def warning(module_name, message):
    logging.warning(message, extra={"logger_name": module_name})


# ==========================================
# 农历工具类
# ==========================================
SOLAR_TERMS_2020_2030 = {
    2024: {
        1: {6: "小寒", 20: "大寒"},
        2: {4: "立春", 19: "雨水"},
        3: {5: "惊蛰", 20: "春分"},
        4: {4: "清明", 20: "谷雨"},
        5: {5: "立夏", 21: "小满"},
        6: {5: "芒种", 21: "夏至"},
        7: {6: "小暑", 22: "大暑"},
        8: {7: "立秋", 23: "处暑"},
        9: {7: "白露", 23: "秋分"},
        10: {8: "寒露", 23: "霜降"},
        11: {7: "立冬", 22: "小雪"},
        12: {6: "大雪", 21: "冬至"}
    },
    2025: {
        1: {5: "小寒", 20: "大寒"},
        2: {3: "立春", 18: "雨水"},
        3: {5: "惊蛰", 20: "春分"},
        4: {4: "清明", 20: "谷雨"},
        5: {5: "立夏", 21: "小满"},
        6: {5: "芒种", 21: "夏至"},
        7: {6: "小暑", 22: "大暑"},
        8: {7: "立秋", 23: "处暑"},
        9: {7: "白露", 23: "秋分"},
        10: {8: "寒露", 23: "霜降"},
        11: {7: "立冬", 22: "小雪"},
        12: {6: "大雪", 21: "冬至"}
    }
}

TRADITIONAL_FESTIVALS = {
    (1, 1): "春节",
    (1, 15): "元宵节",
    (2, 2): "龙抬头",
    (5, 5): "端午节",
    (7, 7): "七夕节",
    (7, 15): "中元节",
    (8, 15): "中秋节",
    (9, 9): "重阳节",
    (12, 8): "腊八节",
    (12, 23): "小年",
    (12, 30): "除夕"
}

SOLAR_FESTIVALS = {
    (1, 1): "元旦",
    (3, 8): "妇女节",
    (3, 12): "植树节",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (10, 1): "国庆节"
}


def get_simplified_yi_ji(date):
    """
    获取简化版宜忌信息
    
    Args:
        date (datetime.date): 公历日期
        
    Returns:
        dict: 包含宜和忌的字典
    """
    year, month, day = date.year, date.month, date.day
    hash_val = year * 10000 + month * 100 + day
    yi_options = ["嫁娶", "出行", "搬家", "开市", "安床", "祭祀", "祈福", "动土", "破土", "安葬", "开光"]
    ji_options = ["嫁娶", "出行", "搬家", "开市", "安床", "祭祀", "祈福", "动土", "破土", "安葬", "开光"]
    yi = yi_options[:hash_val % 5 + 1]
    ji = [item for item in ji_options if item not in yi][:hash_val % 5 + 1]
    return {"宜": yi, "忌": ji}


class LunarUtils:
    """
    农历工具类，提供完整的农历功能
    """
    
    @staticmethod
    def solar_to_lunar(date):
        """
        公历转农历
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含农历信息的字典
        """
        try:
            dt = datetime.datetime.combine(date, datetime.time.min)
            lunar = ZhDate.from_datetime(dt)
            lunar_info = {
                "lunar_year": lunar.lunar_year,
                "lunar_month": lunar.lunar_month,
                "lunar_day": lunar.lunar_day,
                "is_leap_month": getattr(lunar, 'is_leap_month', False),
                "full_str": str(lunar),
                "short_str": str(lunar)[2:] if str(lunar).startswith("农历") else str(lunar)
            }
            return lunar_info
        except Exception as e:
            error("system_core", f"公历转农历失败：{e}")
            return None
    
    @staticmethod
    def get_solar_term(date):
        """
        获取指定日期的节气
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            str: 节气名称，如"立春"，如果不是节气则返回空字符串
        """
        year, month, day = date.year, date.month, date.day
        if year not in SOLAR_TERMS_2020_2030:
            return ""
        year_terms = SOLAR_TERMS_2020_2030[year]
        if month in year_terms and day in year_terms[month]:
            return year_terms[month][day]
        return ""
    
    @staticmethod
    def get_festivals(date):
        """
        获取指定日期的节日
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含传统节日和公历节日的字典
        """
        festivals = {"traditional": [], "solar": []}
        solar_key = (date.month, date.day)
        if solar_key in SOLAR_FESTIVALS:
            festivals["solar"].append(SOLAR_FESTIVALS[solar_key])
        lunar_info = LunarUtils.solar_to_lunar(date)
        if lunar_info:
            lunar_key = (lunar_info["lunar_month"], lunar_info["lunar_day"])
            if lunar_key in TRADITIONAL_FESTIVALS:
                festivals["traditional"].append(TRADITIONAL_FESTIVALS[lunar_key])
        return festivals
    
    @staticmethod
    def get_yi_ji(date):
        """
        获取指定日期的宜忌信息
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含宜和忌的字典
        """
        return get_simplified_yi_ji(date)
    
    @staticmethod
    def get_lunar_info(date):
        """
        获取完整的农历信息
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含所有农历信息的字典
        """
        lunar_info = LunarUtils.solar_to_lunar(date)
        if not lunar_info:
            return None
        solar_term = LunarUtils.get_solar_term(date)
        lunar_info["solar_term"] = solar_term
        festivals = LunarUtils.get_festivals(date)
        lunar_info["festivals"] = festivals
        yi_ji = LunarUtils.get_yi_ji(date)
        lunar_info["yi_ji"] = yi_ji
        return lunar_info


# ==========================================
# 安全加密模块
# ==========================================
KEY_FILE = "encryption_key.key"
SALT_FILE = "encryption_salt.key"
MASTER_PASSWORD_KEY = "MASTER_PASSWORD"


def load_salt():
    """
    加载盐值
    
    Returns:
        bytes: 盐值
    """
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            return f.read()
    else:
        salt = os.urandom(16)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        info("system_core", "生成新的盐值文件")
        return salt


def generate_derived_key_from_master_password(master_password, salt=None):
    """
    从主密码生成派生密钥
    
    Args:
        master_password (str): 主密码
        salt (bytes, optional): 盐值
        
    Returns:
        tuple: (key, salt) 生成的派生密钥和使用的盐值
    """
    if salt is None:
        salt = load_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    return key, salt


def save_derived_key(key):
    """
    保存派生密钥
    
    Args:
        key (bytes): 派生密钥
    """
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    info("system_core", "派生密钥已保存")


def load_derived_key():
    """
    加载派生密钥
    
    Returns:
        bytes: 派生密钥，如果文件不存在则返回None
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    return None


def prompt_for_master_password():
    """
    提示用户输入主密码
    
    Returns:
        str: 主密码
    """
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    while True:
        password, ok = QInputDialog.getText(
            None, 
            "设置主密码", 
            "请设置加密主密码（用于保护您的敏感信息）：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            info("system_core", "用户取消设置主密码，使用临时密码")
            return "temp_password"
        
        if not password:
            QInputDialog.getText(
                None, 
                "提示", 
                "主密码不能为空，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        confirm_password, ok = QInputDialog.getText(
            None, 
            "确认主密码", 
            "请再次输入主密码以确认：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            info("system_core", "用户取消确认主密码，使用临时密码")
            return "temp_password"
        
        if password != confirm_password:
            QInputDialog.getText(
                None, 
                "提示", 
                "两次输入的密码不一致，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        info("system_core", "主密码设置成功")
        return password


def prompt_for_verify_master_password():
    """
    提示用户输入主密码进行验证
    
    Returns:
        str: 主密码
    """
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    while True:
        password, ok = QInputDialog.getText(
            None, 
            "验证主密码", 
            "请输入主密码以验证身份：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            return None
        
        if not password:
            QInputDialog.getText(
                None, 
                "提示", 
                "主密码不能为空，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        return password


def encrypt_data(data, derived_key):
    """
    加密数据
    
    Args:
        data (str): 要加密的数据
        derived_key (bytes): 派生密钥
    
    Returns:
        str: 加密后的数据（base64编码）
    """
    if not data:
        return data
    f = Fernet(derived_key)
    encrypted = f.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data, derived_key):
    """
    解密数据
    
    Args:
        encrypted_data (str): 加密的数据（base64编码）
        derived_key (bytes): 派生密钥
    
    Returns:
        str: 解密后的数据
    """
    if not encrypted_data:
        return encrypted_data
    f = Fernet(derived_key)
    try:
        encrypted = base64.b64decode(encrypted_data.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        error("system_core", f"解密失败：{e}")
        raise


def is_encrypted(data):
    """
    判断数据是否已加密
    
    Args:
        data (str): 要检查的数据
    
    Returns:
        bool: True表示已加密，False表示未加密
    """
    if not data:
        return False
    try:
        decoded = base64.b64decode(data.encode())
        return len(decoded) >= 44
    except:
        return False


def initialize_first_run(config):
    """
    首次运行初始化
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, derived_key) 主密码和派生密钥
    """
    info("system_core", "首次运行，初始化加密系统")
    master_password = prompt_for_master_password()
    derived_key, _ = generate_derived_key_from_master_password(master_password)
    save_derived_key(derived_key)
    encrypted_master_password = encrypt_data(master_password, derived_key)
    config[MASTER_PASSWORD_KEY] = encrypted_master_password
    return master_password, derived_key


def load_and_decrypt_master_password(config):
    """
    加载并解密主密码
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, old_derived_key) 主密码和旧的派生密钥
    """
    old_derived_key = load_derived_key()
    if old_derived_key is None:
        raise Exception("派生密钥文件不存在")
    
    if MASTER_PASSWORD_KEY not in config:
        raise Exception("主密码配置项不存在")
    
    encrypted_master_password = config[MASTER_PASSWORD_KEY]
    master_password = decrypt_data(encrypted_master_password, old_derived_key)
    return master_password, old_derived_key


def regenerate_derived_key(master_password):
    """
    重新生成派生密钥
    
    Args:
        master_password (str): 主密码
    
    Returns:
        bytes: 新的派生密钥
    """
    new_derived_key, _ = generate_derived_key_from_master_password(master_password)
    save_derived_key(new_derived_key)
    info("system_core", "派生密钥已重新生成")
    return new_derived_key


def reencrypt_sensitive_data(config, old_derived_key, new_derived_key):
    """
    重新加密敏感数据
    
    Args:
        config (dict): 配置字典
        old_derived_key (bytes): 旧的派生密钥
        new_derived_key (bytes): 新的派生密钥
    """
    sensitive_fields = ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]
    
    for field in sensitive_fields:
        if field in config and config[field]:
            if is_encrypted(config[field]):
                decrypted_data = decrypt_data(config[field], old_derived_key)
            else:
                decrypted_data = config[field]
            config[field] = encrypt_data(decrypted_data, new_derived_key)
    
    info("system_core", "敏感数据已重新加密")


def load_and_update_encryption(config):
    """
    加载并更新加密系统
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, new_derived_key) 主密码和新的派生密钥
    """
    old_derived_key = load_derived_key()
    if old_derived_key is None or MASTER_PASSWORD_KEY not in config:
        return initialize_first_run(config)
    
    try:
        master_password, old_derived_key = load_and_decrypt_master_password(config)
    except Exception as e:
        error("system_core", f"解密主密码失败：{e}")
        reply = QMessageBox.question(
            None, 
            "解密失败", 
            "主密码解密失败，是否重置主密码？\n\n注意：重置后所有已加密信息将无法恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            return initialize_first_run(config)
        else:
            raise Exception("用户取消重置主密码")
    
    new_derived_key = regenerate_derived_key(master_password)
    reencrypt_sensitive_data(config, old_derived_key, new_derived_key)
    
    return master_password, new_derived_key


# ==========================================
# 配置文件管理模块
# ==========================================
CONFIG_FILE = "config.json"

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

ISP_MAPPING = {
    "中国电信": "@telecom",
    "中国移动": "@cmcc",
    "中国联通": "@unicom",
    "校内资源": "@local"
}

WEEKDAY_MAPPING = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日"
}

global_config = DEFAULT_CONFIG.copy()
current_derived_key = None


def load_config():
    """
    加载配置文件
    
    Returns:
        None（直接修改 global_config 全局变量）
    """
    global global_config, current_derived_key
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
            
            for key, value in DEFAULT_CONFIG.items():
                global_config[key] = value
            for key, value in loaded_config.items():
                global_config[key] = value
            
            master_password, current_derived_key = load_and_update_encryption(global_config)
            
            sensitive_fields = ["WIFI_PASSWORD", "PASSWORD"]
            for field in sensitive_fields:
                if field in global_config and is_encrypted(global_config[field]):
                    try:
                        global_config[field] = decrypt_data(global_config[field], current_derived_key)
                        info("system_core", f"解密配置项：{field}")
                    except Exception as e:
                        error("system_core", f"解密 {field} 失败：{e}")
                        if field in DEFAULT_CONFIG:
                            global_config[field] = DEFAULT_CONFIG[field]
            
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
            
            save_config()
            info("system_core", f"从 {CONFIG_FILE} 加载配置成功")
        else:
            for key, value in DEFAULT_CONFIG.items():
                global_config[key] = value
            master_password, current_derived_key = load_and_update_encryption(global_config)
            save_config()
            info("system_core", f"未找到配置文件，创建默认配置 {CONFIG_FILE}")
    except Exception as e:
        error("system_core", f"加载配置失败，使用默认配置：{e}")
        for key, value in DEFAULT_CONFIG.items():
            global_config[key] = value


def save_config():
    """
    保存配置到文件
    
    Returns:
        bool: 保存是否成功
    """
    try:
        config_to_save = global_config.copy()
        
        sensitive_fields = ["WIFI_PASSWORD", "PASSWORD"]
        for field in sensitive_fields:
            if field in config_to_save and config_to_save[field] and not is_encrypted(config_to_save[field]):
                try:
                    config_to_save[field] = encrypt_data(config_to_save[field], current_derived_key)
                    info("system_core", f"加密配置项：{field}")
                except Exception as e:
                    error("system_core", f"加密 {field} 失败：{e}")
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, ensure_ascii=False, indent=4)
        info("system_core", f"配置已保存到 {CONFIG_FILE}")
        return True
    except Exception as e:
        error("system_core", f"保存配置失败：{e}")
        QMessageBox.critical(None, "错误", f"保存配置失败：{e}")
        return False


def change_master_password(old_password, new_password):
    """
    更改主密码
    
    Args:
        old_password (str): 旧主密码
        new_password (str): 新主密码
    
    Returns:
        bool: 是否成功
    """
    global current_derived_key
    try:
        old_derived_key, _ = generate_derived_key_from_master_password(old_password)
        test_encrypted = encrypt_data("test", old_derived_key)
        if test_encrypted:
            decrypt_data(test_encrypted, old_derived_key)
        
        new_derived_key, _ = generate_derived_key_from_master_password(new_password)
        
        sensitive_fields = ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]
        for field in sensitive_fields:
            if field in global_config and global_config[field]:
                if is_encrypted(global_config[field]):
                    decrypted = decrypt_data(global_config[field], old_derived_key)
                else:
                    decrypted = global_config[field]
                global_config[field] = encrypt_data(decrypted, new_derived_key)
        
        global_config[MASTER_PASSWORD_KEY] = encrypt_data(new_password, new_derived_key)
        save_derived_key(new_derived_key)
        current_derived_key = new_derived_key
        save_config()
        info("system_core", "主密码更改成功")
        return True
    except Exception as e:
        error("system_core", f"主密码更改失败：{e}")
        return False


# ==========================================
# 日期判断模块
# ==========================================
def should_work_today(check_date=None):
    """
    判断指定日期是否需要执行自动化任务
    
    Args:
        check_date (datetime.date, optional): 要检查的日期，默认为今天
    
    Returns:
        bool: True表示需要执行任务，False表示不需要执行
    """
    from infrastructure import parse_date_str, is_date_in_period
    
    today = check_date if check_date is not None else datetime.date.today()
    date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"])

    compensatory_days = [parse_date_str(d) for d in global_config.get("COMPENSATORY_WORKDAYS", []) if parse_date_str(d)]
    if today in compensatory_days:
        return True

    if date_rules.get("ENABLE_CUSTOM_RULE", False):
        custom_work_periods = date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
        for period in custom_work_periods:
            if is_date_in_period(today, period):
                return True

        custom_holiday_periods = date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
        for period in custom_holiday_periods:
            if is_date_in_period(today, period):
                return False

        weekday = today.weekday()
        weekly_execute_days = date_rules.get("WEEKLY_EXECUTE_DAYS", [0, 1, 2, 3, 4])
        if weekday in weekly_execute_days:
            return True
        else:
            return False

    else:
        base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
        for period in base_holiday_periods:
            if is_date_in_period(today, period):
                return False

        weekday = today.weekday()
        weekly_execute_days = [0, 1, 2, 3, 4]
        if weekday in weekly_execute_days:
            return True
        else:
            return False
