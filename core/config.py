"""
配置文件管理模块

提供线程安全的配置管理器、配置加载/保存等功能。

说明：自 v1.4.1 起移除了主密码加密体系。原实现将派生密钥明文落盘，
主密码可随时重置、形同虚设，且反复出现"密码识别错误"误报。
WIFI_PASSWORD / PASSWORD 现在以明文形式保存在 config.json 中。
旧版加密数据（ENC: 前缀）加载时会自动清空，需在设置中重新填写。
"""

import contextlib
import copy
import json
import os
import tempfile
import threading
from typing import Any

from core.config_validator import validate_config
from core.constants import CONFIG_DIR, CONFIG_FILE, ISP_MAPPING
from core.holidays import COMPENSATORY_WORKDAYS, HOLIDAY_PERIODS
from infra.file_permissions import restrict_file_permissions
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


# 默认配置：字段含义 ——
#   WIFI_NAME/WIFI_PASSWORD   目标 WiFi 的 SSID 与密码
#   MAX_WIFI_RETRY            WiFi 连接最大重试次数
#   RETRY_INTERVAL            基础重试间隔秒数（实际按指数退避放大，封顶 60s）
#   USERNAME/PASSWORD         校园网认证账号密码（明文存储）
#   ISP_TYPE                  运营商类型（cmcc/telecom/unicom/local，见 ISP_MAPPING）
#   WAN_IP                    认证参数中的 wlan_user_ip（一般留空即可）
#   SHUTDOWN_HOUR/MIN         定时关机时间（24 小时制）
#   AUTOSTART                 开机自启开关（当前版本未实现写注册表，保留字段）
#   THEME                     界面主题（light/dark）
#   SHOW_LUNAR_CALENDAR       万年历是否显示农历/宜忌等详情
#   LUNAR_DISPLAY_FORMAT      农历显示格式（0=简化 / 1=完整）
#   HOLIDAY_PERIODS           节假日区间（含寒暑假），来源 core/holidays.py
#   COMPENSATORY_WORKDAYS     调休上班日列表，来源 core/holidays.py
#   DATE_RULES                自定义日期规则（启用开关/每周执行日/自定义区间）
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

# 运营商类型 → (登录账号后缀, 显示名) 的单一数据源在 core/constants.py 的
# ISP_MAPPING，此处与 core/__init__.py 仅再导出，供旧调用方稳定引用。

# Python weekday() 数字（0=周一）→ 中文名（UI 显示用）
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


def load_config() -> str | None:
    """
    加载配置文件（原地更新 global_config，不改变对象引用）。

    Returns:
        str | None: 失败原因（此时已回退默认配置）；None 表示加载成功。
        面向用户的错误提示由调用方（GUI 层）负责展示，core 层不依赖 Qt。
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
                for type_key, (type_suffix, _) in ISP_MAPPING.items():
                    if type_suffix == suffix:
                        new_config["ISP_TYPE"] = type_key
                        migrated = True
                        break
                new_config.pop("ISP_SUFFIX", None)
                if migrated:
                    info("system_core", f"已迁移 ISP_SUFFIX {suffix} -> ISP_TYPE")
                else:
                    warning("system_core", f"未知 ISP_SUFFIX {suffix}，已丢弃")

            # DATE_RULES 若被写成 list/str/null 等畸形结构，下方补键循环的
            # 下标赋值会抛 TypeError，导致整份配置被回退默认值（用户数据丢失）；
            # 此处先行重置为默认结构，将损失限定在该字段内
            loaded_rules = new_config.get("DATE_RULES")
            if not isinstance(loaded_rules, dict):
                warning(
                    "system_core",
                    f"配置校验: DATE_RULES 类型错误(收到{type(loaded_rules).__name__})，已重置为默认值",
                )
                new_config["DATE_RULES"] = copy.deepcopy(DEFAULT_CONFIG["DATE_RULES"])

            # new_config 由 DEFAULT_CONFIG 深拷贝起步，COMPENSATORY_WORKDAYS/
            # DATE_RULES 键必然存在，只需为旧配置的 DATE_RULES 补齐缺失子键
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
        return str(e)
    return None


def save_config() -> bool:
    """
    保存配置到文件（使用原子写入，防止写入中断导致文件损坏）

    Returns:
        bool: 保存是否成功。失败详情已记入日志；面向用户的错误提示
        由调用方（GUI 层）负责展示，core 层不依赖 Qt。
    """
    try:
        # snapshot() 已返回深拷贝，直接落盘（无需再套一层 deepcopy）
        config_to_save: dict[str, Any] = global_config.snapshot()

        # 原子写入：先写临时文件，再重命名，防止写入中断导致配置损坏。
        # mkstemp 以 0600 权限（POSIX）创建不可预测路径的临时文件，避免
        # 明文密码经 0644 中间文件暴露；与目标同目录保证 rename 不跨卷
        fd, tmp_file = tempfile.mkstemp(prefix=".config.", suffix=".tmp", dir=CONFIG_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, CONFIG_FILE)
        except BaseException:
            # 写入/替换失败时清理残留临时文件（含明文密码，不可遗留）；
            # 清理本身失败只记忽略——原始异常优先向上传递
            with contextlib.suppress(OSError):
                os.unlink(tmp_file)
            raise
        # config.json 含账号/WiFi 密码明文，落盘后立即收紧到仅当前用户可读写
        restrict_file_permissions(CONFIG_FILE)
        info("system_core", f"配置已保存到 {CONFIG_FILE}")
        return True
    except Exception as e:
        error("system_core", f"保存配置失败：{e}")
        return False
