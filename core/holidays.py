"""
假期与调休数据模块

集中管理法定假日和调休工作日数据，与配置默认值分离。
数据可能随年度更新，独立模块便于维护。
"""

import datetime

HOLIDAY_PERIODS: list[dict[str, str]] = [
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
]

COMPENSATORY_WORKDAYS: list[str] = [
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
]


def check_holiday_data_freshness() -> str | None:
    """检查假期数据是否覆盖当前年份。

    Returns:
        如果当前年份的假期数据缺失，返回警告消息；否则返回 None。
    """
    current_year = datetime.date.today().year
    latest_year = 0
    for period in HOLIDAY_PERIODS:
        try:
            year = int(period["start"][:4])
            if year > latest_year:
                latest_year = year
        except (ValueError, KeyError):
            continue

    if current_year > latest_year:
        return (
            f"假期数据仅覆盖到 {latest_year} 年，当前年份 {current_year} 的数据缺失。"
            "请更新 core/holidays.py 中的假期数据。"
        )
    return None
