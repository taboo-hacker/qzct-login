"""
配置文件管理模块

提供线程安全的配置管理器、配置加载/保存等功能。

说明：自 v1.4.1 起移除了主密码加密体系。原实现将派生密钥明文落盘，
主密码可随时重置、形同虚设，且反复出现"密码识别错误"误报。
WIFI_PASSWORD / PASSWORD 现在以明文形式保存在 config.json 中。
旧版加密数据（ENC: 前缀）加载时会自动清空，需在设置中重新填写。
"""

import copy
import json
import os
import threading
from typing import Any

from core.config_validator import validate_config
from core.constants import CONFIG_DIR, CONFIG_FILE
from core.holidays import COMPENSATORY_WORKDAYS, HOLIDAY_PERIODS
from infra.logging import error, info, warning

# ==========================================
# 配置目录与旧版文件清理
# ==========================================

# 历史遗留的加密密钥文件名（已废弃，启动时清理）
_LEGACY_KEY_FILES = ("encryption_key.key", "encryption_salt.key")


def _get_config_dir() -> str:
    """获取配置目录（确保目录存在），并清理旧版加密遗留文件。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _cleanup_legacy_files()
    return CONFIG_DIR


def _cleanup_legacy_files() -> None:
    """清理旧版加密体系的遗留密钥文件（配置目录与当前工作目录）。"""
    for filename in _LEGACY_KEY_FILES:
        for location in (CONFIG_DIR, os.getcwd()):
            path = os.path.join(location, filename)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    info("system_core", f"已清理旧版密钥文件：{path}")
            except OSError:
                pass


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
}

ISP_MAPPING = {"cmcc": "@cmcc", "telecom": "@telecom", "unicom": "@unicom", "local": "@local"}

WEEKDAY_MAPPING = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}


class ConfigManager(dict[str, Any]):
    """线程安全配置管理器，dict 子类 —— 现有代码无需改动即可获得线程安全。

    对可变值（list/dict）的 get/__getitem__ 自动返回浅拷贝，防止意外修改
    原始配置。简单值（str/int/bool）直接返回，零拷贝开销。
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
            return val.copy()
        return val


global_config = ConfigManager(copy.deepcopy(DEFAULT_CONFIG))


def get_config_snapshot() -> dict[str, Any]:
    """
    获取配置的线程安全快照（深拷贝）

    工作线程在读取配置时应使用此函数。

    Returns:
        dict: 配置的快照
    """
    return global_config.snapshot()


def load_config() -> None:
    """
    加载配置文件（原地更新 global_config，不改变对象引用）。
    """
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

            # 旧版加密数据迁移：无密钥可解密，清空让用户重新填写
            for field in ("WIFI_PASSWORD", "PASSWORD"):
                if isinstance(new_config.get(field), str) and new_config[field].startswith("ENC:"):
                    new_config[field] = ""
                    warning(
                        "system_core",
                        f"旧版加密的 {field} 无法解密，已清空，请在设置中重新填写",
                    )
            # 旧版主密码配置项已废弃
            new_config.pop("MASTER_PASSWORD", None)

            # 旧版 ISP_SUFFIX 迁移：仅在配置文件确实提供该字段时生效
            # （不能判断 ISP_TYPE 是否存在——DEFAULT_CONFIG 自带默认值，
            #   旧条件恒为 False 导致迁移从未生效）
            if "ISP_SUFFIX" in loaded_config:
                suffix = loaded_config["ISP_SUFFIX"]
                migrated = False
                for type_key, type_suffix in ISP_MAPPING.items():
                    if type_suffix == suffix:
                        new_config["ISP_TYPE"] = type_key
                        migrated = True
                        break
                new_config.pop("ISP_SUFFIX", None)
                if migrated:
                    info("system_core", f"已迁移 ISP_SUFFIX {suffix} -> ISP_TYPE")
                else:
                    warning("system_core", f"未知 ISP_SUFFIX {suffix}，已丢弃")

            if "COMPENSATORY_WORKDAYS" not in new_config:
                new_config["COMPENSATORY_WORKDAYS"] = DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy()

            if "DATE_RULES" not in new_config:
                new_config["DATE_RULES"] = copy.deepcopy(DEFAULT_CONFIG["DATE_RULES"])
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

        # 假期数据过期检查
        from core.holidays import check_holiday_data_freshness

        freshness_warning = check_holiday_data_freshness()
        if freshness_warning:
            warning("system_core", freshness_warning)

        global_config.replace_all(new_config)

    except Exception as e:
        error("system_core", f"加载配置失败，使用默认配置：{e}")
        global_config.replace_all(copy.deepcopy(DEFAULT_CONFIG))
        from PySide6.QtWidgets import QMessageBox

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
        config_to_save: dict[str, Any] = copy.deepcopy(global_config.snapshot())

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
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "错误", f"保存配置失败：{e}")
        return False
