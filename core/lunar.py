"""
农历工具模块

提供公历转农历、节气查询、节日查询、宜忌查询等农历相关功能，
底层基于 lunar-python 库（支持任意年份，无需内置数据表）。

使用场景：主窗口"任务日历"标签页（gui/widgets/calendar_view.py）
显示农历日期、干支、宜忌、节气、节日等万年历信息。
"""

from datetime import date
from typing import Any

from lunar_python import Solar

from infra.logging import error

# ==========================================
# 农历常量
# ==========================================
# 传统节日：键为（农历月, 农历日），如 (8, 15) = 八月十五中秋节
# 注意腊月三十（除夕）在某些小年三十缺失的年份不会命中，属已知取舍
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

# 公历节日：键为（公历月, 公历日）
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


class LunarUtils:
    """
    农历工具类，提供完整的农历功能

    全部为静态方法，无状态，直接调用：LunarUtils.solar_to_lunar(date.today())
    """

    @staticmethod
    def solar_to_lunar(date: date) -> dict[str, Any] | None:
        """
        公历转农历

        Args:
            date (datetime.date): 公历日期

        Returns:
            dict | None: 农历信息字典，转换失败返回 None。键如下：
                - lunar_year (int): 农历年份数字
                - lunar_month (int): 农历月（取绝对值）
                - lunar_day (int): 农历日
                - is_leap_month (bool): 是否闰月（lunar-python 用负数表示闰月）
                - full_str (str): 完整描述字符串
                - short_str (str): 简短格式，如"正月初一"
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
    def get_solar_term(date: date) -> str:
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
    def get_festivals(date: date) -> dict[str, list[str]]:
        """
        获取指定日期的节日（传统农历节日 + 公历节日）

        Args:
            date (datetime.date): 公历日期

        Returns:
            dict: {"traditional": [农历节日名...], "solar": [公历节日名...]}，
                  无节日时两个列表均为空
        """
        festivals: dict[str, list[str]] = {"traditional": [], "solar": []}
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
    def get_yi_ji(date: date) -> dict[str, Any]:
        """
        获取指定日期的宜忌信息（黄历）

        Args:
            date (datetime.date): 公历日期

        Returns:
            dict: {"宜": [条目...], "忌": [条目...]}；
                  lunar-python 失败时两个列表为空（不伪造数据）
        """
        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()
            yi = lunar.getDayYi()
            ji = lunar.getDayJi()
            return {"宜": yi, "忌": ji}
        except Exception as e:
            error("system_core", f"获取宜忌信息失败：{e}")
            # lunar-python 失败时返回空字典，不再伪造哈希随机数据
            return {"宜": [], "忌": []}

    @staticmethod
    def get_lunar_info(date: date) -> dict[str, Any] | None:
        """
        获取完整的农历信息（一站式聚合，万年历详情页使用）

        在 solar_to_lunar 基础上追加：节气（solar_term）、节日（festivals）、
        宜忌（yi_ji）、干支（year/month/day_ganzhi）、生肖（year_shengxiao）。
        干支部分失败时仅记录日志，不中断其余字段。

        Args:
            date (datetime.date): 公历日期

        Returns:
            dict | None: 完整农历信息；基础转换失败返回 None
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
