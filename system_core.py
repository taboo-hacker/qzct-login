import base64
import copy
import datetime
import json
import os
import threading

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from lunar_python import Solar
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from infrastructure import error, info

# ==========================================
# 农历工具类
# ==========================================
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
    (12, 30): "除夕",
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
    (10, 1): "国庆节",
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
    yi_options = [
        "嫁娶",
        "出行",
        "搬家",
        "开市",
        "安床",
        "祭祀",
        "祈福",
        "动土",
        "破土",
        "安葬",
        "开光",
    ]
    ji_options = [
        "嫁娶",
        "出行",
        "搬家",
        "开市",
        "安床",
        "祭祀",
        "祈福",
        "动土",
        "破土",
        "安葬",
        "开光",
    ]
    yi = yi_options[: hash_val % 5 + 1]
    ji = [item for item in ji_options if item not in yi][: hash_val % 5 + 1]
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
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()
            lunar_info = {
                "lunar_year": lunar.getYear(),
                "lunar_month": abs(lunar.getMonth()),
                "lunar_day": lunar.getDay(),
                "is_leap_month": lunar.getMonth() < 0,
                "full_str": lunar.toString(),
                "short_str": f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            }
            return lunar_info
        except Exception as e:
            error("system_core", f"公历转农历失败：{e}")
            return None

    @staticmethod
    def get_solar_term(date):
        """
        获取指定日期的节气

        使用 lunar-python 库计算节气，支持任意年份。

        Args:
            date (datetime.date): 公历日期

        Returns:
            str: 节气名称，如"立春"，如果不是节气则返回空字符串
        """
        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()
            jie_qi = lunar.getJieQi()
            return jie_qi if jie_qi else ""
        except Exception:
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
        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()
            yi = lunar.getDayYi()
            ji = lunar.getDayJi()
            return {"宜": yi, "忌": ji}
        except Exception as e:
            error("system_core", f"获取宜忌信息失败：{e}")
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

        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()
            lunar_info["year_ganzhi"] = lunar.getYearInGanZhi()
            lunar_info["month_ganzhi"] = lunar.getMonthInGanZhi()
            lunar_info["day_ganzhi"] = lunar.getDayInGanZhi()
            lunar_info["year_shengxiao"] = lunar.getYearShengXiao()
            lunar_info["jieqi"] = lunar.getJieQi()
        except Exception as e:
            error("system_core", f"获取干支生肖信息失败：{e}")

        return lunar_info


# ==========================================
# 安全加密模块
# ==========================================
_CONFIG_DIR = None


def _get_config_dir():
    """获取配置目录（确保目录存在），并迁移旧文件"""
    global _CONFIG_DIR
    if _CONFIG_DIR is not None:
        return _CONFIG_DIR
    _CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".qzct")
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    _migrate_old_files(_CONFIG_DIR)
    return _CONFIG_DIR


def _migrate_old_files(config_dir: str):
    """将旧工作目录中的加密密钥文件迁移到新位置"""
    import shutil

    old_files = ["encryption_key.key", "encryption_salt.key"]
    for filename in old_files:
        new_path = os.path.join(config_dir, filename)
        if os.path.exists(filename) and not os.path.exists(new_path):
            shutil.copy2(filename, new_path)


KEY_FILE = os.path.join(_get_config_dir(), "encryption_key.key")
SALT_FILE = os.path.join(_get_config_dir(), "encryption_salt.key")
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
        iterations=600000,
        backend=default_backend(),
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
            echo=QLineEdit.Password,
        )

        if not ok:
            info("system_core", "用户取消设置主密码，使用临时密码")
            return "temp_password"

        if not password:
            QMessageBox.warning(None, "提示", "主密码不能为空，请重新输入：")
            continue

        confirm_password, ok = QInputDialog.getText(
            None, "确认主密码", "请再次输入主密码以确认：", echo=QLineEdit.Password
        )

        if not ok:
            info("system_core", "用户取消确认主密码，使用临时密码")
            return "temp_password"

        if password != confirm_password:
            QMessageBox.warning(None, "提示", "两次输入的密码不一致，请重新输入：")
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
            None, "验证主密码", "请输入主密码以验证身份：", echo=QLineEdit.Password
        )

        if not ok:
            return None

        if not password:
            QMessageBox.warning(None, "提示", "主密码不能为空，请重新输入：")
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


def is_encrypted(data) -> bool:
    """
    判断数据是否已加密

    数据存储格式为 base64(Fernet_token)，其中 Fernet token 以 "gA" 开头。
    通过解一层 base64 后检查是否为有效 Fernet token 前缀来判断。

    Args:
        data (str): 要检查的数据

    Returns:
        bool: True 表示已加密，False 表示未加密
    """
    if not isinstance(data, str) or len(data) < 20:
        return False
    try:
        decoded = base64.b64decode(data.encode(), validate=True)
        return len(decoded) > 20 and decoded.startswith(b"gA")
    except Exception:
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
        return master_password, old_derived_key
    except Exception as e:
        error("system_core", f"解密主密码失败：{e}")
        reply = QMessageBox.question(
            None,
            "解密失败",
            "主密码解密失败，是否重置主密码？\n\n注意：重置后所有已加密信息将无法恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            return initialize_first_run(config)
        else:
            raise Exception("用户取消重置主密码")


# ==========================================
# 配置文件管理模块
# ==========================================
CONFIG_FILE = os.path.join(_get_config_dir(), "config.json")

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
        "2026-10-10",
    ],
    "DATE_RULES": {
        "ENABLE_CUSTOM_RULE": False,
        "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
        "CUSTOM_HOLIDAY_PERIODS": [],
        "CUSTOM_WORKDAY_PERIODS": [],
    },
    "_DECRYPT_FAILED_FIELDS": [],
}

ISP_MAPPING = {"cmcc": "@cmcc", "telecom": "@telecom", "unicom": "@unicom", "local": "@local"}

WEEKDAY_MAPPING = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}

global_config = copy.deepcopy(DEFAULT_CONFIG)
current_derived_key = None
_config_lock = threading.Lock()


def get_config_snapshot():
    """
    获取配置的线程安全快照（深拷贝）

    工作线程在读取配置时应使用此函数而非直接访问 global_config，
    避免与主线程（UI）发生竞态条件。

    Returns:
        dict: 配置的深拷贝
    """
    with _config_lock:
        return copy.deepcopy(global_config)


def load_config():
    """
    加载配置文件（原地更新 global_config，不改变对象引用）

    Returns:
        None
    """
    global global_config, current_derived_key
    try:
        new_config = copy.deepcopy(DEFAULT_CONFIG)

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as f:
                loaded_config = json.load(f)

            for key, value in loaded_config.items():
                if isinstance(value, (list, dict)):
                    new_config[key] = copy.deepcopy(value)
                else:
                    new_config[key] = value

            master_password, current_derived_key = load_and_update_encryption(new_config)

            new_config["_DECRYPT_FAILED_FIELDS"] = []
            for field in ["WIFI_PASSWORD", "PASSWORD"]:
                if field in new_config and is_encrypted(new_config[field]):
                    try:
                        new_config[field] = decrypt_data(new_config[field], current_derived_key)
                        info("system_core", f"解密配置项：{field}")
                    except Exception as e:
                        error("system_core", f"解密 {field} 失败：{e}")
                        new_config["_DECRYPT_FAILED_FIELDS"].append(field)

            if "ISP_SUFFIX" in new_config and "ISP_TYPE" not in new_config:
                suffix = new_config["ISP_SUFFIX"]
                for type_key, type_suffix in ISP_MAPPING.items():
                    if type_suffix == suffix:
                        new_config["ISP_TYPE"] = type_key
                        del new_config["ISP_SUFFIX"]
                        break

            if "COMPENSATORY_WORKDAYS" not in new_config:
                new_config["COMPENSATORY_WORKDAYS"] = DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy()

            if "DATE_RULES" not in new_config:
                new_config["DATE_RULES"] = DEFAULT_CONFIG["DATE_RULES"].copy()
            else:
                for key in DEFAULT_CONFIG["DATE_RULES"]:
                    if key not in new_config["DATE_RULES"]:
                        new_config["DATE_RULES"][key] = DEFAULT_CONFIG["DATE_RULES"][key]
                if "CUSTOM_HOLIDAYS" in new_config["DATE_RULES"]:
                    new_config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] = []
                    del new_config["DATE_RULES"]["CUSTOM_HOLIDAYS"]
                if "CUSTOM_WORKDAYS" in new_config["DATE_RULES"]:
                    new_config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] = []
                    del new_config["DATE_RULES"]["CUSTOM_WORKDAYS"]

            info("system_core", f"从 {CONFIG_FILE} 加载配置成功")
        else:
            master_password, current_derived_key = load_and_update_encryption(new_config)
            save_config()
            info("system_core", f"未找到配置文件，创建默认配置 {CONFIG_FILE}")

        with _config_lock:
            global_config.clear()
            global_config.update(new_config)

    except Exception as e:
        error("system_core", f"加载配置失败，使用默认配置：{e}")
        with _config_lock:
            global_config.clear()
            global_config.update(copy.deepcopy(DEFAULT_CONFIG))
        QMessageBox.warning(
            None,
            "配置加载失败",
            f"配置文件加载失败，已恢复为默认设置：\n{e}\n\n" f"请检查 {CONFIG_FILE} 文件是否损坏。",
        )


def save_config():
    """
    保存配置到文件（使用原子写入，防止写入中断导致文件损坏）

    Returns:
        bool: 保存是否成功
    """
    try:
        with _config_lock:
            config_to_save = copy.deepcopy(global_config)

        decrypt_failed = config_to_save.pop("_DECRYPT_FAILED_FIELDS", [])

        for field in ["WIFI_PASSWORD", "PASSWORD"]:
            val = config_to_save.get(field)
            if val:
                if field in decrypt_failed:
                    continue
                config_to_save[field] = encrypt_data(val, current_derived_key)

        # 原子写入：先写临时文件，再重命名，防止写入中断导致配置损坏
        tmp_file = CONFIG_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, CONFIG_FILE)
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
                    try:
                        decrypted = decrypt_data(global_config[field], old_derived_key)
                    except Exception:
                        continue
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
    from infrastructure import is_date_in_period, parse_date_str

    today = check_date if check_date is not None else datetime.date.today()
    date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"])

    compensatory_days = [
        parse_date_str(d)
        for d in global_config.get("COMPENSATORY_WORKDAYS", [])
        if parse_date_str(d)
    ]
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
