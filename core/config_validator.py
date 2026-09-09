"""
配置 Schema 验证模块

在 load_config() 后对配置字典进行结构和类型校验：
- 必需字段是否存在
- 字段类型是否正确（str/int/bool/list/dict）
- 字段值域是否合法（如 ISP_TYPE 必须是四个之一）
- 嵌套结构（DATE_RULES 子字段）校验

校验失败的字段回退到 DEFAULT_CONFIG 中的默认值，并记录警告日志。
"""

import copy
from typing import Any

from core.constants import ISP_MAPPING, TAB_NAMES
from infra.date_utils import parse_date_str
from infra.logging import warning

# WINDOW_GEOMETRY 合法长度上限（字符）：Qt 的 saveGeometry 实际输出约 100~200 字节，
# base64 后不超过 400 字符；超过说明字段被外部写入垃圾数据，回退默认尺寸
_WINDOW_GEOMETRY_MAX_LEN = 1024


def _default(field: str) -> Any:
    """从 DEFAULT_CONFIG 获取字段的深拷贝（防止污染默认配置）"""
    from core.config import DEFAULT_CONFIG

    return copy.deepcopy(DEFAULT_CONFIG.get(field))


def _is_valid_period_element(el: object) -> bool:
    """判断区间列表元素是否合法：dict 且 start/end 均为可解析的 "YYYY-MM-DD"。

    非法元素（字符串/数字/缺失日期/日期不可解析的 dict）会在
    is_date_in_period 的 period.get("start") 处抛 AttributeError，
    沿 should_work_today 传播到主窗口 __init__ 导致启动即崩，
    因此在 validate_config 的元素清洗段统一丢弃。
    """
    if not isinstance(el, dict):
        return False
    start, end = el.get("start"), el.get("end")
    # 先做 str 类型过滤：parse_date_str 内部的 lru_cache 收到
    # 不可哈希入参（list/dict 等）会直接抛 TypeError 而非返回 None
    if not isinstance(start, str) or not isinstance(end, str):
        return False
    return parse_date_str(start) is not None and parse_date_str(end) is not None


# Schema 定义: field_name -> (expected_type, validator_fn | None)
# validator_fn 接收值，返回 True 表示合法
_SCHEMA: dict[str, tuple[type, Any]] = {
    "WIFI_NAME": (str, None),
    "WIFI_PASSWORD": (str, None),
    "MAX_WIFI_RETRY": (int, lambda v: v >= 0),
    "RETRY_INTERVAL": (int, lambda v: v >= 0),
    "USERNAME": (str, None),
    "PASSWORD": (str, None),
    "ISP_TYPE": (str, lambda v: v in ISP_MAPPING),
    "WAN_IP": (str, None),
    "SHUTDOWN_HOUR": (int, lambda v: 0 <= v <= 23),
    "SHUTDOWN_MIN": (int, lambda v: 0 <= v <= 59),
    "AUTOSTART": (bool, None),
    "THEME": (str, lambda v: v in ("light", "dark")),
    "ACTIVE_TAB": (str, lambda v: v in TAB_NAMES),
    # 窗口几何是不透明的 base64 串，长度上限防御异常膨胀的配置文件
    "WINDOW_GEOMETRY": (str, lambda v: len(v) <= _WINDOW_GEOMETRY_MAX_LEN),
    "SHOW_LUNAR_CALENDAR": (bool, None),
    "LUNAR_DISPLAY_FORMAT": (int, lambda v: v in (0, 1)),
}

# DATE_RULES 子字段 schema
_DATE_RULES_SCHEMA: dict[str, tuple[type, Any]] = {
    "ENABLE_CUSTOM_RULE": (bool, None),
    "WEEKLY_EXECUTE_DAYS": (list, lambda v: all(isinstance(d, int) and 0 <= d <= 6 for d in v)),
    "CUSTOM_HOLIDAY_PERIODS": (list, None),
    "CUSTOM_WORKDAY_PERIODS": (list, None),
}


def validate_config(config: dict[str, Any]) -> list[str]:
    """校验配置字典，返回修复的字段名列表。

    对每个 schema 中定义的字段：
    - 如果缺失，从 DEFAULT_CONFIG 补充
    - 如果类型不匹配或值域校验失败，回退到默认值
    - 记录警告日志

    Args:
        config: 待校验的配置字典（原地修改）

    Returns:
        被修复的字段名列表
    """
    fixed: list[str] = []

    for field, (expected_type, validator) in _SCHEMA.items():
        if field not in config:
            config[field] = _default(field)
            fixed.append(field)
            warning("system_core", f"配置校验: 缺失字段 {field}，已补充默认值")
            continue

        val = config[field]
        # bool 是 int 的子类，需在 isinstance 之前判断
        if expected_type is int and isinstance(val, bool):
            config[field] = _default(field)
            fixed.append(field)
            warning("system_core", f"配置校验: {field} 类型错误(收到bool)，已重置为默认值")
            continue
        if expected_type is bool and isinstance(val, int) and not isinstance(val, bool):
            config[field] = bool(val)
            fixed.append(field)
            warning("system_core", f"配置校验: {field} 类型不匹配(收到int)，已转换为bool")
            continue
        if not isinstance(val, expected_type):
            config[field] = _default(field)
            fixed.append(field)
            warning(
                "system_core",
                f"配置校验: {field} 类型错误(期望{expected_type.__name__})，已重置为默认值",
            )
            continue

        if validator is not None:
            try:
                if not validator(val):
                    config[field] = _default(field)
                    fixed.append(field)
                    warning("system_core", f"配置校验: {field} 值域不合法({val})，已重置为默认值")
            except Exception:
                config[field] = _default(field)
                fixed.append(field)
                warning("system_core", f"配置校验: {field} 值域校验异常，已重置为默认值")

    # DATE_RULES 嵌套校验
    if "DATE_RULES" not in config or not isinstance(config["DATE_RULES"], dict):
        config["DATE_RULES"] = _default("DATE_RULES")
        fixed.append("DATE_RULES")
        warning("system_core", "配置校验: DATE_RULES 缺失或类型错误，已重置为默认值")
    else:
        date_rules = config["DATE_RULES"]
        default_date_rules = _default("DATE_RULES")
        for field, (expected_type, validator) in _DATE_RULES_SCHEMA.items():
            if field not in date_rules:
                date_rules[field] = copy.deepcopy(default_date_rules.get(field))
                fixed.append(f"DATE_RULES.{field}")
                warning("system_core", f"配置校验: DATE_RULES.{field} 缺失，已补充默认值")
                continue

            val = date_rules[field]
            if not isinstance(val, expected_type):
                date_rules[field] = copy.deepcopy(default_date_rules.get(field))
                fixed.append(f"DATE_RULES.{field}")
                warning("system_core", f"配置校验: DATE_RULES.{field} 类型错误，已重置为默认值")
                continue

            if validator is not None:
                try:
                    if not validator(val):
                        date_rules[field] = copy.deepcopy(default_date_rules.get(field))
                        fixed.append(f"DATE_RULES.{field}")
                        warning(
                            "system_core",
                            f"配置校验: DATE_RULES.{field} 值域不合法，已重置为默认值",
                        )
                except Exception:
                    date_rules[field] = copy.deepcopy(default_date_rules.get(field))
                    fixed.append(f"DATE_RULES.{field}")
                    warning("system_core", f"配置校验: DATE_RULES.{field} 校验异常，已重置为默认值")

    # HOLIDAY_PERIODS 和 COMPENSATORY_WORKDAYS 类型校验
    for field in ("HOLIDAY_PERIODS", "COMPENSATORY_WORKDAYS"):
        if field not in config or not isinstance(config[field], list):
            config[field] = _default(field)
            fixed.append(field)
            warning("system_core", f"配置校验: {field} 缺失或类型错误，已重置为默认值")

    # 区间列表元素级清洗：列表内的畸形元素（字符串/数字/缺失或不可解析日期的 dict）
    # 能通过上面的 list 类型校验，却会让 is_date_in_period 抛 AttributeError，
    # 沿 should_work_today 传播到主窗口构造期导致启动即崩，这里统一丢弃。
    period_targets: list[tuple[str, list[Any]]] = []
    if isinstance(config.get("HOLIDAY_PERIODS"), list):
        period_targets.append(("HOLIDAY_PERIODS", config["HOLIDAY_PERIODS"]))
    if isinstance(config.get("DATE_RULES"), dict):
        date_rules_conf = config["DATE_RULES"]
        for field in ("CUSTOM_HOLIDAY_PERIODS", "CUSTOM_WORKDAY_PERIODS"):
            if isinstance(date_rules_conf.get(field), list):
                period_targets.append((f"DATE_RULES.{field}", date_rules_conf[field]))
    for field_name, elements in period_targets:
        kept = [el for el in elements if _is_valid_period_element(el)]
        dropped = len(elements) - len(kept)
        if dropped:
            elements[:] = kept  # elements 是 config 中对应列表的引用，原地更新
            fixed.append(field_name)
            warning(
                "system_core",
                f"配置校验: {field_name} 含 {dropped} 条非法条目"
                "(需为 start/end 均可解析的 dict)，已丢弃",
            )

    # COMPENSATORY_WORKDAYS 元素应为可解析的 "YYYY-MM-DD" 字符串，
    # 过滤不可解析的脏数据（date_rules 判定时本就会静默跳过它们，此处不致崩溃）
    compensatory = config.get("COMPENSATORY_WORKDAYS")
    if isinstance(compensatory, list):
        kept_days = [
            d for d in compensatory if isinstance(d, str) and parse_date_str(d) is not None
        ]
        dropped_days = len(compensatory) - len(kept_days)
        if dropped_days:
            compensatory[:] = kept_days
            fixed.append("COMPENSATORY_WORKDAYS")
            warning(
                "system_core",
                f"配置校验: COMPENSATORY_WORKDAYS 含 {dropped_days} 条不可解析的日期条目，已丢弃",
            )

    return fixed
