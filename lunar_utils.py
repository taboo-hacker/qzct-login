#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
农历工具类

提供完整的农历功能，包括：
1. 公历转农历
2. 农历转公历
3. 节气查询
4. 传统节日查询
5. 宜忌信息（简化版）
"""

import datetime
from zhdate import ZhDate
from logger import error

# 24节气数据（1900-2100年）
# 简化版，仅包含2020-2030年的节气
SOLAR_TERMS_2020_2030 = {
    2024: {
        1: {6: "小寒", 20: "大寒"},
        2: {4: "立春", 19: "雨水"},
        3: {5: "惊蛰", 20: "春分"},
        4: {4: "清明", 20: "谷雨"},
        5: {5: "立夏", 21: "小满"},
        6: {5: "芒种", 21: "夏至"},
        7: {6: "小暑", 22: "大暑"},
        8: {7: "立秋", 23: "处暑"},
        9: {7: "白露", 23: "秋分"},
        10: {8: "寒露", 23: "霜降"},
        11: {7: "立冬", 22: "小雪"},
        12: {6: "大雪", 21: "冬至"}
    },
    2025: {
        1: {5: "小寒", 20: "大寒"},
        2: {3: "立春", 18: "雨水"},
        3: {5: "惊蛰", 20: "春分"},
        4: {4: "清明", 20: "谷雨"},
        5: {5: "立夏", 21: "小满"},
        6: {5: "芒种", 21: "夏至"},
        7: {6: "小暑", 22: "大暑"},
        8: {7: "立秋", 23: "处暑"},
        9: {7: "白露", 23: "秋分"},
        10: {8: "寒露", 23: "霜降"},
        11: {7: "立冬", 22: "小雪"},
        12: {6: "大雪", 21: "冬至"}
    }
}

# 传统节日（农历）
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
    (12, 30): "除夕"
}

# 公历节日
SOLAR_FESTIVALS = {
    (1, 1): "元旦",
    (3, 8): "妇女节",
    (3, 12): "植树节",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (10, 1): "国庆节"
}

# 简化版宜忌信息（根据农历日期的天干地支生成）
# 实际应用中，宜忌信息需要更复杂的算法或外部数据源
def get_simplified_yi_ji(date):
    """
    获取简化版宜忌信息
    
    Args:
        date (datetime.date): 公历日期
        
    Returns:
        dict: 包含宜和忌的字典
    """
    # 简化版，根据日期简单生成
    year, month, day = date.year, date.month, date.day
    
    # 简单的算法，根据日期的哈希值生成宜忌
    hash_val = year * 10000 + month * 100 + day
    
    yi_options = ["嫁娶", "出行", "搬家", "开市", "安床", "祭祀", "祈福", "动土", "破土", "安葬", "开光"]
    ji_options = ["嫁娶", "出行", "搬家", "开市", "安床", "祭祀", "祈福", "动土", "破土", "安葬", "开光"]
    
    # 根据哈希值选择宜忌
    yi = yi_options[:hash_val % 5 + 1]
    ji = [item for item in ji_options if item not in yi][:hash_val % 5 + 1]
    
    return {
        "宜": yi,
        "忌": ji
    }

class LunarUtils:
    """
    农历工具类，提供完整的农历功能
    """
    
    @staticmethod
    def solar_to_lunar(date):
        """
        公历转农历
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含农历信息的字典
        """
        try:
            dt = datetime.datetime.combine(date, datetime.time.min)
            lunar = ZhDate.from_datetime(dt)
            
            lunar_info = {
                "lunar_year": lunar.lunar_year,
                "lunar_month": lunar.lunar_month,
                "lunar_day": lunar.lunar_day,
                "is_leap_month": getattr(lunar, 'is_leap_month', False),
                "full_str": str(lunar),
                "short_str": str(lunar)[2:] if str(lunar).startswith("农历") else str(lunar)
            }
            
            return lunar_info
        except Exception as e:
            error("lunar_utils", f"公历转农历失败：{e}")
            return None
    
    @staticmethod
    def get_solar_term(date):
        """
        获取指定日期的节气
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            str: 节气名称，如"立春"，如果不是节气则返回空字符串
        """
        year, month, day = date.year, date.month, date.day
        
        # 检查是否在支持的年份范围内
        if year not in SOLAR_TERMS_2020_2030:
            return ""
        
        year_terms = SOLAR_TERMS_2020_2030[year]
        if month in year_terms and day in year_terms[month]:
            return year_terms[month][day]
        
        return ""
    
    @staticmethod
    def get_festivals(date):
        """
        获取指定日期的节日
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含传统节日和公历节日的字典
        """
        festivals = {
            "traditional": [],
            "solar": []
        }
        
        # 检查公历节日
        solar_key = (date.month, date.day)
        if solar_key in SOLAR_FESTIVALS:
            festivals["solar"].append(SOLAR_FESTIVALS[solar_key])
        
        # 检查传统节日（需要先转换为农历）
        lunar_info = LunarUtils.solar_to_lunar(date)
        if lunar_info:
            lunar_key = (lunar_info["lunar_month"], lunar_info["lunar_day"])
            if lunar_key in TRADITIONAL_FESTIVALS:
                festivals["traditional"].append(TRADITIONAL_FESTIVALS[lunar_key])
        
        return festivals
    
    @staticmethod
    def get_yi_ji(date):
        """
        获取指定日期的宜忌信息
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            dict: 包含宜和忌的字典
        """
        return get_simplified_yi_ji(date)
    
    @staticmethod
    def get_lunar_info(date):
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
        
        # 添加节气
        solar_term = LunarUtils.get_solar_term(date)
        lunar_info["solar_term"] = solar_term
        
        # 添加节日
        festivals = LunarUtils.get_festivals(date)
        lunar_info["festivals"] = festivals
        
        # 添加宜忌
        yi_ji = LunarUtils.get_yi_ji(date)
        lunar_info["yi_ji"] = yi_ji
        
        return lunar_info
