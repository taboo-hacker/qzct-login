"""
配置文件管理模块

提供线程安全的配置管理器、配置加载/保存、主密码更改等功能。
"""

import copy
import json
import os
import threading
from typing import Any

from core.config_validator import validate_config
from core.constants import CONFIG_DIR, CONFIG_FILE
from core.encryption import (
    MASTER_PASSWORD_KEY,
    decrypt_data,
    encrypt_data,
    generate_derived_key_from_master_password,
    is_encrypted,
    load_and_update_encryption,
    save_derived_key,
)
from core.holidays import COMPENSATORY_WORKDAYS, HOLIDAY_PERIODS
from infra.logging import error, info, warning

# ==========================================
# 配置目录迁移
# ==========================================


def _get_config_dir() -> str:
    """获取配置目录（确保目录存在），并迁移旧文件"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _migrate_old_files(CONFIG_DIR)
    return CONFIG_DIR


def _migrate_old_files(config_dir: str) -> None:
    """将旧工作目录中的加密密钥文件迁移到新位置"""
    import shutil

    old_files = ["encryption_key.key", "encryption_salt.key"]
    for filename in old_files:
        new_path = os.path.join(config_dir, filename)
        if os.path.exists(filename) and not os.path.exists(new_path):
            shutil.copy2(filename, new_path)


DEFAULT_CONFIG: dict[str, Any] = {
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
    "THEME": "light",
    "SHOW_LUNAR_CALENDAR": True,
    "LUNAR_DISPLAY_FORMAT": 0,
    "HOLIDAY_PERIODS": HOLIDAY_PERIODS,
    "COMPENSATORY_WORKDAYS": COMPENSATORY_WORKDAYS,
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


class ConfigManager(dict[str, Any]):
    """线程安全配置管理器，dict 子类 —— 现有代码无需改动即可获得线程安全。

    对可变值（list/dict）的 get/__getitem__ 自动返回浅拷贝，防止意外修改
    原始配置。简单值（str/int/bool）直接返回，零拷贝开销。

    snapshot() 返回浅拷贝的 dict，替代原来的 copy.deepcopy(global_config)，
    用于工作线程一次性读取多个配置项。
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._config_lock = threading.RLock()

    # ---- 读操作 ----

    def __getitem__(self, key: str) -> Any:
        with self._config_lock:
            val = super().__getitem__(key)
        return self._clone_if_mutable(val)

    def get(self, key: str, default: Any = None) -> Any:
        with self._config_lock:
            val = super().get(key, default)
        return self._clone_if_mutable(val)

    def snapshot(self) -> dict[str, Any]:
        """返回配置的深拷贝。工作线程应使用此方法批量读取配置，
        避免逐次 .get() 持锁多次。深拷贝确保嵌套可变对象不共享引用。"""
        with self._config_lock:
            return copy.deepcopy(dict(self))

    # ---- 写操作 ----

    def __setitem__(self, key: str, value: Any) -> None:
        with self._config_lock:
            super().__setitem__(key, value)

    def update(self, other: Any = None, **kwargs: Any) -> None:  # type: ignore[override]
        with self._config_lock:
            super().update(other, **kwargs)

    def clear(self) -> None:
        with self._config_lock:
            super().clear()

    def pop(self, key: str, *args: Any) -> Any:
        with self._config_lock:
            return super().pop(key, *args)

    def replace_all(self, new_config: dict[str, Any]) -> None:
        """原子性地替换整个配置（clear + update 在一次锁内完成）。"""
        with self._config_lock:
            super().clear()
            super().update(new_config)

    # ---- 内部 ----

    @staticmethod
    def _clone_if_mutable(val: Any) -> Any:
        """列表和字典返回浅拷贝，防止调用方意外修改原始配置。"""
        if isinstance(val, (dict, list)):
            return val.copy()  # 对 list 是浅拷贝，对 dict 也是浅拷贝
        return val


global_config = ConfigManager(copy.deepcopy(DEFAULT_CONFIG))
current_derived_key: bytes | None = None
_derived_key_lock = threading.RLock()


def get_config_snapshot() -> dict[str, Any]:
    """
    获取配置的线程安全快照（浅拷贝）

    ConfigManager 的 snapshot() 返回浅拷贝，比原 deepcopy 快一个数量级。
    工作线程在读取配置时应使用此函数。

    Returns:
        dict: 配置的浅拷贝
    """
    return global_config.snapshot()


def load_config() -> None:
    """
    加载配置文件（原地更新 global_config，不改变对象引用）

    注意：load_and_update_encryption 可能触发 GUI 弹窗和文件 IO，
    这些在锁外执行以避免长时间持锁。锁内只做内存赋值。
    """
    global global_config, current_derived_key
    _get_config_dir()
    try:
        new_config: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as f:
                loaded_config = json.load(f)

            for key, value in loaded_config.items():
                if isinstance(value, (list, dict)):
                    new_config[key] = copy.deepcopy(value)
                else:
                    new_config[key] = value

            # load_and_update_encryption 可能弹 GUI 窗 + IO，在锁外执行
            _, derived_key = load_and_update_encryption(new_config)

            new_config["_DECRYPT_FAILED_FIELDS"] = []
            for field in ["WIFI_PASSWORD", "PASSWORD"]:
                if field in new_config and is_encrypted(new_config[field]):
                    try:
                        new_config[field] = decrypt_data(new_config[field], derived_key)
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
                else:
                    del new_config["ISP_SUFFIX"]

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

            # Schema 验证：校验字段类型和值域，非法字段回退默认值
            fixed_fields = validate_config(new_config)
            if fixed_fields:
                warning(
                    "system_core",
                    f"配置校验修复了 {len(fixed_fields)} 个字段: {', '.join(fixed_fields)}",
                )

            info("system_core", f"从 {CONFIG_FILE} 加载配置成功")
        else:
            # load_and_update_encryption 可能弹 GUI 窗 + IO，在锁外执行
            _, derived_key = load_and_update_encryption(new_config)

        # 假期数据过期检查（锁外执行，无副作用）
        from core.holidays import check_holiday_data_freshness

        freshness_warning = check_holiday_data_freshness()
        if freshness_warning:
            warning("system_core", freshness_warning)

        # 锁内只做内存赋值，保证 global_config 和 current_derived_key 一致
        with _derived_key_lock:
            current_derived_key = derived_key
            global_config.replace_all(new_config)

    except Exception as e:
        error("system_core", f"加载配置失败，使用默认配置：{e}")
        with _derived_key_lock:
            global_config.replace_all(copy.deepcopy(DEFAULT_CONFIG))
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.warning(
            None,
            "配置加载失败",
            f"配置文件加载失败，已恢复为默认设置：\n{e}\n\n请检查 {CONFIG_FILE} 文件是否损坏。",
        )


def save_config() -> bool:
    """
    保存配置到文件（使用原子写入，防止写入中断导致文件损坏）

    Returns:
        bool: 保存是否成功
    """
    try:
        # 在锁内获取密钥和配置快照，保证两者一致
        with _derived_key_lock:
            config_to_save: dict[str, Any] = copy.deepcopy(global_config.snapshot())
            key_for_encryption = current_derived_key

        decrypt_failed: list[str] = config_to_save.pop("_DECRYPT_FAILED_FIELDS", [])

        for field in ["WIFI_PASSWORD", "PASSWORD"]:
            val = config_to_save.get(field)
            if val:
                if field in decrypt_failed:
                    config_to_save[field] = ""
                    continue
                if key_for_encryption is None:
                    error("system_core", "保存配置失败：派生密钥未初始化")
                    return False
                config_to_save[field] = encrypt_data(val, key_for_encryption)

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
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.critical(None, "错误", f"保存配置失败：{e}")
        return False


def change_master_password(old_password: str, new_password: str) -> bool:
    """
    更改主密码

    用旧密码派生密钥解密 config 中存储的主密码来验证旧密码是否正确。
    校验失败时立即返回 False，不做任何重加密操作。

    重加密过程在临时副本上完成，验证解密通路后原子切换。
    如果 save_config 失败，回滚密钥文件到旧密钥。

    Args:
        old_password (str): 旧主密码
        new_password (str): 新主密码

    Returns:
        bool: 是否成功
    """
    global current_derived_key
    with _derived_key_lock:
        try:
            # 用旧密码派生密钥，尝试解密存储的主密码来验证旧密码正确性
            old_derived_key, _ = generate_derived_key_from_master_password(old_password)

            if MASTER_PASSWORD_KEY not in global_config:
                error("system_core", "主密码配置项不存在，无法更改")
                return False

            encrypted_master = global_config[MASTER_PASSWORD_KEY]
            if not is_encrypted(encrypted_master):
                error("system_core", "存储的主密码未加密，数据异常")
                return False

            try:
                decrypt_data(encrypted_master, old_derived_key)
            except Exception:
                error("system_core", "旧密码验证失败：解密主密码错误")
                return False

            # 旧密码验证通过，在临时副本上重加密
            new_derived_key, _ = generate_derived_key_from_master_password(new_password)
            temp_config = global_config.snapshot()

            sensitive_fields = ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]
            for field in sensitive_fields:
                if field in temp_config and temp_config[field]:
                    val = temp_config[field]
                    if is_encrypted(val):
                        try:
                            decrypted = decrypt_data(val, old_derived_key)
                        except Exception:
                            # 旧密钥无法解密此字段，跳过
                            continue
                    else:
                        decrypted = val
                    temp_config[field] = encrypt_data(decrypted, new_derived_key)

            temp_config[MASTER_PASSWORD_KEY] = encrypt_data(new_password, new_derived_key)

            # 验证解密通路：确保新密钥能解密所有重加密的字段
            for field in sensitive_fields:
                if field in temp_config and temp_config[field] and is_encrypted(temp_config[field]):
                    try:
                        decrypt_data(temp_config[field], new_derived_key)
                    except Exception as e:
                        error("system_core", f"重加密验证失败({field}): {e}")
                        return False

            # 保存旧配置快照，用于 save_config 失败时回滚
            old_config_snapshot = global_config.snapshot()

            # 保存新密钥文件（在 save_config 之前，因为 save_config 需要新密钥）
            save_derived_key(new_derived_key)

            # 原子切换：更新内存密钥和配置
            current_derived_key = new_derived_key
            global_config.replace_all(temp_config)

            # 保存配置到磁盘
            if not save_config():
                # 配置保存失败，回滚密钥文件、内存密钥和内存配置
                save_derived_key(old_derived_key)
                current_derived_key = old_derived_key
                global_config.replace_all(old_config_snapshot)
                error("system_core", "主密码更改失败：配置保存失败，已回滚密钥和配置")
                return False

            info("system_core", "主密码更改成功")
            return True
        except Exception as e:
            error("system_core", f"主密码更改失败：{e}")
            return False
