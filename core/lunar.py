"""
农历工具模块

提供公历转农历、节气查询、节日查询、宜忌查询等农历相关功能。
"""

from datetime import date
from typing import Any

from lunar_python import Solar

from infra.logging import error

# ==========================================
# 农历常量
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


class LunarUtils:
    """
    农历工具类，提供完整的农历功能
    """

    @staticmethod
    def solar_to_lunar(date: date) -> dict[str, Any] | None:
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
        获取指定日期的节日

        Args:
            date (datetime.date): 公历日期

        Returns:
            dict: 包含传统节日和公历节日的字典
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
            # lunar-python 失败时返回空字典，不再伪造哈希随机数据
            return {"宜": [], "忌": []}

    @staticmethod
    def get_lunar_info(date: date) -> dict[str, Any] | None:
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
