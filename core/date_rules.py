"""
日期判断模块

提供基于节假日、调休日、自定义规则和 chinesecalendar 的工作日判断功能。

判定阶梯只实现一次（rule_source），should_work_today 的布尔结果与
GUI 状态文案（calendar_view）均由它派生，避免两处各自维护优先级导致漂移。
"""

import datetime
from typing import Any

from core.config import DEFAULT_CONFIG, global_config
from infra.date_utils import is_date_in_period, parse_date_str

# 判定为"需要执行任务"的来源集合（rule_source 返回值的前一项属于此集合即需执行）
_WORK_SOURCES = frozenset(
    {"custom_workday", "custom_weekly_work", "compensatory", "legal_workday", "weekday"}
)


def _chinese_calendar_is_holiday(date: datetime.date) -> bool:
    """chinesecalendar 是否为法定假日。数据不可用时返回 False。

    函数内延迟导入：该库按年份打包数据，新年份未发布时会抛
    NotImplementedError —— 捕获后回退到硬编码数据/周末规则，程序照常运行。
    """
    try:
        import chinese_calendar as chinesecalendar

        return bool(chinesecalendar.is_holiday(date))
    except (ImportError, NotImplementedError):
        return False


def _chinese_calendar_is_workday(date: datetime.date) -> bool:
    """chinesecalendar 是否为工作日（含调休上班日）。数据不可用时返回 False。"""
    try:
        import chinese_calendar as chinesecalendar

        return bool(chinesecalendar.is_workday(date))
    except (ImportError, NotImplementedError):
        # 库未安装或该年份数据未发布：视为"无法判定"，交给后续周末规则
        return False


def rule_source(check_date: datetime.date | None = None) -> tuple[str, dict[str, Any] | None]:
    """
    判定指定日期实际生效的规则来源（唯一的优先级阶梯实现）。

    判断优先级：
    1. 自定义规则（用户明确启用时完全遵守用户配置，最高优先级）
    2. 硬编码调休上班日 > 硬编码节假日 > chinesecalendar > 周末规则
       （硬编码数据覆盖学校特有假期（寒暑假），chinesecalendar 作为
       未来的法定假日兜底）

    Args:
        check_date: 要检查的日期，默认为今天

    Returns:
        tuple[str, dict | None]: (来源标识, 命中的区间数据或 None)。来源标识取值：
        custom_workday / custom_holiday / custom_weekly_work / custom_weekly_rest /
        compensatory / builtin_holiday / legal_holiday / legal_workday / weekday / weekend
    """
    today = check_date if check_date is not None else datetime.date.today()
    date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"])

    # 1. 自定义规则分支：用户明确启用了自定义规则，完全遵守用户配置，
    #    硬编码调休/节假日与 chinesecalendar 兜底均不覆盖用户意图。
    if date_rules.get("ENABLE_CUSTOM_RULE", False):
        for period in date_rules.get("CUSTOM_WORKDAY_PERIODS", []):
            if is_date_in_period(today, period):
                return "custom_workday", period
        for period in date_rules.get("CUSTOM_HOLIDAY_PERIODS", []):
            if is_date_in_period(today, period):
                return "custom_holiday", period

        weekday = today.weekday()
        weekly_execute_days = date_rules.get("WEEKLY_EXECUTE_DAYS", [0, 1, 2, 3, 4])
        return (
            "custom_weekly_work" if weekday in weekly_execute_days else "custom_weekly_rest"
        ), None

    # 2. 硬编码调休上班日
    compensatory_days = [
        parsed
        for d in global_config.get("COMPENSATORY_WORKDAYS", [])
        if (parsed := parse_date_str(d)) is not None
    ]
    if today in compensatory_days:
        return "compensatory", None

    # 3. 基础规则分支（使用硬编码节假日 + chinesecalendar 兜底）
    base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
    for period in base_holiday_periods:
        if is_date_in_period(today, period):
            return "builtin_holiday", period

    # chinesecalendar 法定假日兜底（覆盖硬编码未包含的年份）
    if _chinese_calendar_is_holiday(today):
        return "legal_holiday", None
    # chinesecalendar 调休上班日兜底
    if _chinese_calendar_is_workday(today):
        return "legal_workday", None

    weekday = today.weekday()
    return ("weekday" if weekday in [0, 1, 2, 3, 4] else "weekend"), None


def should_work_today(check_date: datetime.date | None = None) -> bool:
    """
    判断指定日期是否需要执行自动化任务（阶梯实现见 rule_source）

    Args:
        check_date (datetime.date, optional): 要检查的日期，默认为今天

    Returns:
        bool: True表示需要执行任务，False表示不需要执行
    """
    return rule_source(check_date)[0] in _WORK_SOURCES
