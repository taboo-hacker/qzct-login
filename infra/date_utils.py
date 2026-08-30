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
    start_date = parse_date_str(period.get("start"))
    end_date = parse_date_str(period.get("end"))
    if not start_date or not end_date:
        return False
    return start_date <= check_date <= end_date
