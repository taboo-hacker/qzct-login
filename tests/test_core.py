"""
core 包模块测试

测试三块核心逻辑：
- 配置管理：get_config_snapshot 的快照与深拷贝语义；
- 日期规则 should_work_today：工作日/周末/节假日/调休/自定义规则的优先级组合。
日期规则用例通过覆写 global_config 控制输入，conftest 的
reset_global_config autouse fixture 负责测试后还原全局配置。
"""

import datetime
from typing import Any

from core.config import ISP_MAPPING, get_config_snapshot, global_config
from core.date_rules import SOURCE_TEXT, describe_source, rule_source, should_work_today


class TestConfigManagement:
    """配置管理测试：get_config_snapshot 的返回语义。"""

    def test_get_config_snapshot(self, sample_config: dict[str, Any]) -> None:
        """快照内容应与 global_config 一致，但不是同一对象引用。"""

        global_config.clear()
        global_config.update(sample_config)

        snapshot = get_config_snapshot()

        assert snapshot == sample_config
        assert snapshot is not global_config

    def test_get_config_snapshot_is_deep_copy(self, sample_config: dict[str, Any]) -> None:
        """修改快照不应影响 global_config（深拷贝语义）。"""

        global_config.clear()
        global_config.update(sample_config)

        snapshot = get_config_snapshot()
        snapshot["WIFI_NAME"] = "ModifiedWiFi"

        assert global_config["WIFI_NAME"] == "TestWiFi"


class TestDateRules:
    """日期规则测试：should_work_today 在各类日历场景下的判定。"""

    def test_should_work_today_weekday(self, sample_config: dict[str, Any]) -> None:
        """默认规则下普通周一（2026-01-05）应判定为需要执行任务。"""

        global_config.clear()
        global_config.update(sample_config)

        monday = datetime.date(2026, 1, 5)
        result = should_work_today(monday)
        assert result is True

    def test_should_work_today_weekend(self, sample_config: dict[str, Any]) -> None:
        """默认规则下周末（周六/周日）应判定为不执行任务。"""

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

    def test_should_work_today_holiday(self, sample_config: dict[str, Any]) -> None:
        """日期落在 HOLIDAY_PERIODS 节假日区间内时应判定为不执行。"""

        config = sample_config.copy()
        config["HOLIDAY_PERIODS"] = [
            {"name": "测试假期", "start": "2026-01-05", "end": "2026-01-07"}
        ]
        global_config.clear()
        global_config.update(config)

        holiday = datetime.date(2026, 1, 6)
        result = should_work_today(holiday)
        assert result is False

    def test_should_work_today_compensatory_workday(self, sample_config: dict[str, Any]) -> None:
        """周末调休上班日（COMPENSATORY_WORKDAYS）应判定为执行。"""

        config = sample_config.copy()
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04"]
        global_config.clear()
        global_config.update(config)

        compensatory_day = datetime.date(2026, 1, 4)
        result = should_work_today(compensatory_day)
        assert result is True

    def test_should_work_today_custom_rule_enabled(self, sample_config: dict[str, Any]) -> None:
        """启用自定义规则后按 WEEKLY_EXECUTE_DAYS 与自定义假期判定。"""

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

    def test_custom_rule_overrides_compensatory_workday(
        self, sample_config: dict[str, Any]
    ) -> None:
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

    def test_custom_workday_period_overrides_base_holiday(
        self, sample_config: dict[str, Any]
    ) -> None:
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


class TestRuleSourceText:
    """来源文案单一数据源测试：SOURCE_TEXT / describe_source 的映射与兜底。"""

    def test_source_text_covers_six_named_sources(self) -> None:
        """SOURCE_TEXT 应恰好覆盖六个具名来源（自定义 4 项 + 调休 + 内置节假日）。"""
        assert set(SOURCE_TEXT) == {
            "custom_workday",
            "custom_holiday",
            "custom_weekly_work",
            "custom_weekly_rest",
            "compensatory",
            "builtin_holiday",
        }

    def test_describe_source_maps_named_sources(self) -> None:
        """具名来源应翻译为对应文案。"""
        assert describe_source("custom_workday") == "自定义工作日"
        assert describe_source("custom_holiday") == "自定义假期"
        assert describe_source("custom_weekly_work") == "自定义每周执行日"
        assert describe_source("custom_weekly_rest") == "自定义每周休息日"
        assert describe_source("compensatory") == "调休上班日"
        assert describe_source("builtin_holiday") == "节假日"

    def test_describe_source_fallback_for_unnamed_sources(self) -> None:
        """无名称来源（法定假日/周末等）应回退到主窗口旧版兜底文案。"""
        assert describe_source("legal_holiday") == "国务院官方节假日"
        assert describe_source("legal_workday") == "国务院官方节假日"
        assert describe_source("weekday") == "国务院官方节假日"
        assert describe_source("weekend") == "国务院官方节假日"

    def test_rule_source_custom_overrides_compensatory(self, sample_config: dict[str, Any]) -> None:
        """rule_source：自定义规则启用且当天为调休日，来源必须是自定义（优先级钉死）。"""
        config = sample_config.copy()
        # 2026-01-04 是周日且在 COMPENSATORY_WORKDAYS 中
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04"]
        config["DATE_RULES"] = {
            "ENABLE_CUSTOM_RULE": True,
            "WEEKLY_EXECUTE_DAYS": [6],  # 含周日 → custom_weekly_work
            "CUSTOM_HOLIDAY_PERIODS": [],
            "CUSTOM_WORKDAY_PERIODS": [],
        }
        global_config.clear()
        global_config.update(config)

        source, period = rule_source(datetime.date(2026, 1, 4))
        assert source == "custom_weekly_work"
        assert period is None
        # 左卡片文案由 describe_source 派生，应来自自定义来源
        assert describe_source(source) == "自定义每周执行日"


class TestISPMapping:
    """ISP 映射测试：ISP_MAPPING 常量的键值完整性。"""

    def test_isp_mapping_exists(self) -> None:
        """映射表应包含移动/电信/联通/本地四种 ISP 键。"""
        assert "cmcc" in ISP_MAPPING
        assert "telecom" in ISP_MAPPING
        assert "unicom" in ISP_MAPPING
        assert "local" in ISP_MAPPING

    def test_isp_mapping_values(self) -> None:
        """每个 ISP 键应映射到 (登录账号后缀, 显示名) 二元组。"""
        assert ISP_MAPPING["cmcc"] == ("@cmcc", "移动")
        assert ISP_MAPPING["telecom"] == ("@telecom", "电信")
        assert ISP_MAPPING["unicom"] == ("@unicom", "联通")
        assert ISP_MAPPING["local"] == ("@local", "本地")

    def test_isp_mapping_single_source(self) -> None:
        """单一数据源：校验值域应与 ISP_MAPPING 派生一致。"""
        from core.constants import ISP_MAPPING as SOURCE

        assert set(ISP_MAPPING) == set(SOURCE)
        assert all(isinstance(v, tuple) and len(v) == 2 for v in ISP_MAPPING.values())
