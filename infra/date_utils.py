"""
日期工具函数模块

提供日期字符串解析、期间判断等工具函数。
"""

import datetime
from functools import lru_cache
from typing import Any

PeriodDict = dict[str, Any]


@lru_cache(maxsize=512)
def _parse_date_str_cached(date_str: str) -> datetime.date | None:
    """解析 "YYYY-MM-DD" 字符串为 date；失败返回 None（缓存加速逐日重判）。"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError, AttributeError):
        return None


def parse_date_str(date_str: str | None) -> datetime.date | None:
    """
    解析日期字符串为 date 对象

    将 "YYYY-MM-DD" 格式的字符串转换为 Python datetime.date 对象。
    结果按输入字符串缓存（万年历逐日判定会反复解析同一批配置日期，
    缓存后每次调用只做字典查找）。

    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"
                  例如："2025-01-26"、"2026-02-14"

    Returns:
        解析后的日期对象，如果解析失败则返回 None

    Examples:
        >>> date = parse_date_str("2025-01-26")
        >>> if date:
        ...     print(date.year, date.month, date.day)
        2025 1 26
    """
    if date_str is None:
        return None
    return _parse_date_str_cached(date_str)


def validate_period(start_str: str, end_str: str) -> str | None:
    """
    校验时间段起止日期的先后关系

    设置面板各日期录入点（基础节假日表单、时间段编辑弹窗）共用的
    单一校验口径：两者均可解析且开始日期晚于结束日期时返回错误文案；
    其余情况（含任一日期不可解析）返回 None——不可解析的交由调用方
    既有逻辑处理，本函数不引入新行为。

    Args:
        start_str: 开始日期字符串，"YYYY-MM-DD" 格式
        end_str: 结束日期字符串，"YYYY-MM-DD" 格式

    Returns:
        校验未通过时返回错误文案；通过校验返回 None

    Examples:
        >>> validate_period("2026-01-10", "2026-01-05")
        '开始日期不能晚于结束日期'
        >>> validate_period("2026-01-01", "2026-01-05") is None
        True
    """
    start = parse_date_str(start_str)
    end = parse_date_str(end_str)
    if start is not None and end is not None and start > end:
        return "开始日期不能晚于结束日期"
    return None


def is_date_in_period(check_date: datetime.date, period: PeriodDict) -> bool:
    """
    判断日期是否在指定的时间段内

    检查给定的日期是否在时间段 [start, end] 范围内（闭区间）。

    Args:
        check_date: 要检查的日期
        period: 时间段字典，包含以下键：
            - start (str): 开始日期，"YYYY-MM-DD" 格式
            - end (str): 结束日期，"YYYY-MM-DD" 格式
            - name (str, optional): 时间段名称

    Returns:
        True 表示日期在时间段内，False 表示不在

    Examples:
        >>> today = datetime.date.today()
        >>> period = {"name": "寒假", "start": "2025-01-10", "end": "2025-02-28"}
        >>> if is_date_in_period(today, period):
        ...     print("今天在寒假期间")
    """
    if not isinstance(period, dict):
        # 纵深防御：来自配置的区间列表可能混入非 dict 元素（字符串/数字等），
        # 返回安全值 False，避免 period.get 抛 AttributeError 沿调用链导致崩溃
        return False
    start_date = parse_date_str(period.get("start"))
    end_date = parse_date_str(period.get("end"))
    if not start_date or not end_date:
        return False
    return start_date <= check_date <= end_date
