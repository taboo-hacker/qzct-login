"""
core 包模块测试

测试配置管理、日期判断、农历等功能。
"""

import datetime

from core.config import ISP_MAPPING, get_config_snapshot, global_config
from core.date_rules import should_work_today
from core.lunar import LunarUtils


class TestLunarUtils:
    """农历工具类测试"""

    def test_solar_to_lunar(self):
        """测试公历转农历"""
        date = datetime.date(2026, 1, 1)
        result = LunarUtils.solar_to_lunar(date)

        assert result is not None
        assert "lunar_year" in result
        assert "lunar_month" in result
        assert "lunar_day" in result
        assert result["lunar_year"] == 2025
        assert result["lunar_month"] == 11
        # lunar-python 在 2026-01-01 公历对应农历乙巳年冬月十三
        assert result["lunar_day"] == 13

    def test_get_solar_term(self):
        """测试获取节气"""
        li_chun = datetime.date(2026, 2, 4)
        result = LunarUtils.get_solar_term(li_chun)
        assert result == "立春"

    def test_get_solar_term_not_solar_term(self):
        """测试非节气日期"""
        normal_day = datetime.date(2026, 1, 15)
        result = LunarUtils.get_solar_term(normal_day)
        assert result == ""

    def test_get_festivals_solar(self):
        """测试获取公历节日"""
        new_year = datetime.date(2026, 1, 1)
        result = LunarUtils.get_festivals(new_year)
        assert "元旦" in result["solar"]

    def test_get_festivals_traditional(self):
        """测试获取传统节日"""
        spring_festival = datetime.date(2026, 2, 17)
        result = LunarUtils.get_festivals(spring_festival)
        assert len(result["traditional"]) > 0 or len(result["solar"]) > 0

    def test_get_lunar_info(self):
        """测试获取完整农历信息"""
        date = datetime.date(2026, 1, 1)
        result = LunarUtils.get_lunar_info(date)

        assert result is not None
        assert "lunar_year" in result
        assert "solar_term" in result
        assert "festivals" in result
        assert "yi_ji" in result


class TestConfigManagement:
    """配置管理测试"""

    def test_get_config_snapshot(self, sample_config):
        """测试获取配置快照"""

        global_config.clear()
        global_config.update(sample_config)

        snapshot = get_config_snapshot()

        assert snapshot == sample_config
        assert snapshot is not global_config

    def test_get_config_snapshot_is_deep_copy(self, sample_config):
        """测试配置快照是深拷贝"""

        global_config.clear()
        global_config.update(sample_config)

        snapshot = get_config_snapshot()
        snapshot["WIFI_NAME"] = "ModifiedWiFi"

        assert global_config["WIFI_NAME"] == "TestWiFi"


class TestDateRules:
    """日期规则测试"""

    def test_should_work_today_weekday(self, sample_config):
        """测试普通工作日"""

        global_config.clear()
        global_config.update(sample_config)

        monday = datetime.date(2026, 1, 5)
        result = should_work_today(monday)
        assert result is True

    def test_should_work_today_weekend(self, sample_config):
        """测试周末"""

        # sample_config 把 2026-01-04 设为调休工作日，与"周末休息"用例冲突；
        # 这里清空调休列表，让测试单独检验周末规则。
        config = sample_config.copy()
        config["COMPENSATORY_WORKDAYS"] = []
        global_config.clear()
        global_config.update(config)

        # 用 2026-01-10/11 周末（chinesecalendar 也判作假日，不存在调休）
        saturday = datetime.date(2026, 1, 10)
        sunday = datetime.date(2026, 1, 11)

        assert should_work_today(saturday) is False
        assert should_work_today(sunday) is False

    def test_should_work_today_holiday(self, sample_config):
        """测试节假日"""

        config = sample_config.copy()
        config["HOLIDAY_PERIODS"] = [
            {"name": "测试假期", "start": "2026-01-05", "end": "2026-01-07"}
        ]
        global_config.clear()
        global_config.update(config)

        holiday = datetime.date(2026, 1, 6)
        result = should_work_today(holiday)
        assert result is False

    def test_should_work_today_compensatory_workday(self, sample_config):
        """测试调休上班日"""

        config = sample_config.copy()
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04"]
        global_config.clear()
        global_config.update(config)

        compensatory_day = datetime.date(2026, 1, 4)
        result = should_work_today(compensatory_day)
        assert result is True

    def test_should_work_today_custom_rule_enabled(self, sample_config):
        """测试启用自定义规则"""

        config = sample_config.copy()
        config["DATE_RULES"] = {
            "ENABLE_CUSTOM_RULE": True,
            "WEEKLY_EXECUTE_DAYS": [0, 1, 2],
            "CUSTOM_HOLIDAY_PERIODS": [
                {"name": "自定义假期", "start": "2026-01-05", "end": "2026-01-06"}
            ],
            "CUSTOM_WORKDAY_PERIODS": [],
        }
        # 自定义规则下，调休工作日不应再覆盖周末/规则；清空调休数据
        config["COMPENSATORY_WORKDAYS"] = []
        global_config.clear()
        global_config.update(config)

        # 2026-01-05 周一在 CUSTOM_HOLIDAY_PERIODS 内 -> False
        custom_holiday = datetime.date(2026, 1, 5)
        assert should_work_today(custom_holiday) is False

        # 2026-01-07 周三在 WEEKLY_EXECUTE_DAYS [0,1,2] 内 -> True
        wednesday = datetime.date(2026, 1, 7)
        assert should_work_today(wednesday) is True

        # 2026-01-08 周四不在 WEEKLY_EXECUTE_DAYS 内 -> False
        thursday = datetime.date(2026, 1, 8)
        assert should_work_today(thursday) is False

    def test_custom_rule_overrides_compensatory_workday(self, sample_config):
        """自定义规则启用时，硬编码调休上班日不再强制上班（M6 回归）。"""
        config = sample_config.copy()
        # 2026-01-04 是周日，且在 sample_config 的 COMPENSATORY_WORKDAYS 中
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04"]
        config["DATE_RULES"] = {
            "ENABLE_CUSTOM_RULE": True,
            "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],  # 仅工作日
            "CUSTOM_HOLIDAY_PERIODS": [],
            "CUSTOM_WORKDAY_PERIODS": [],
        }
        global_config.clear()
        global_config.update(config)

        # 自定义规则下按周末处理，硬编码调休不再覆盖用户意图
        sunday = datetime.date(2026, 1, 4)
        assert should_work_today(sunday) is False

    def test_custom_workday_period_overrides_base_holiday(self, sample_config):
        """自定义工作日区间优先于硬编码节假日。"""
        config = sample_config.copy()
        config["COMPENSATORY_WORKDAYS"] = []
        config["HOLIDAY_PERIODS"] = [{"name": "劳动节", "start": "2026-05-01", "end": "2026-05-05"}]
        config["DATE_RULES"] = {
            "ENABLE_CUSTOM_RULE": True,
            "WEEKLY_EXECUTE_DAYS": [],
            "CUSTOM_HOLIDAY_PERIODS": [],
            "CUSTOM_WORKDAY_PERIODS": [
                {"name": "自定义上班", "start": "2026-05-04", "end": "2026-05-05"}
            ],
        }
        global_config.clear()
        global_config.update(config)

        # 2026-05-04 在硬编码劳动节假期内，但自定义工作日区间优先
        workday = datetime.date(2026, 5, 4)
        assert should_work_today(workday) is True


class TestISPMapping:
    """ISP 映射测试"""

    def test_isp_mapping_exists(self):
        """测试 ISP 映射存在"""
        assert "cmcc" in ISP_MAPPING
        assert "telecom" in ISP_MAPPING
        assert "unicom" in ISP_MAPPING
        assert "local" in ISP_MAPPING

    def test_isp_mapping_values(self):
        """测试 ISP 映射值"""
        assert ISP_MAPPING["cmcc"] == "@cmcc"
        assert ISP_MAPPING["telecom"] == "@telecom"
        assert ISP_MAPPING["unicom"] == "@unicom"
        assert ISP_MAPPING["local"] == "@local"
