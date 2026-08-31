"""
D2 测试：Config Schema 验证

测试 validate_config() 函数对各类字段类型、值域、缺失字段、
嵌套结构（DATE_RULES）的校验行为。
策略：以 deepcopy(DEFAULT_CONFIG) 为基线，逐项注入非法值后断言
字段被修复且函数返回被修复字段名列表（原地修改 + 返回修复清单）。
另含 F07/B4 回归：区间列表（HOLIDAY_PERIODS / CUSTOM_*_PERIODS /
COMPENSATORY_WORKDAYS）的元素级清洗，及清洗后 should_work_today
不再因畸形元素抛 AttributeError。
"""

import copy
import datetime

import pytest

from core.config import DEFAULT_CONFIG, global_config
from core.config_validator import validate_config
from core.date_rules import should_work_today


class TestValidateConfigValid:
    """合法配置不应修改任何字段（validate_config 原地校验，返回空修复列表）。"""

    def test_valid_config_no_changes(self) -> None:
        """合法的默认配置不应触发任何修复"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        fixed = validate_config(config)
        assert fixed == []

    def test_valid_config_preserves_values(self) -> None:
        """合法值应原样保留"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["WIFI_NAME"] = "MyWifi"
        config["MAX_WIFI_RETRY"] = 5
        config["SHUTDOWN_HOUR"] = 22
        config["SHUTDOWN_MIN"] = 30
        config["ISP_TYPE"] = "cmcc"
        config["THEME"] = "dark"

        fixed = validate_config(config)
        assert fixed == []
        assert config["WIFI_NAME"] == "MyWifi"
        assert config["MAX_WIFI_RETRY"] == 5
        assert config["SHUTDOWN_HOUR"] == 22
        assert config["SHUTDOWN_MIN"] == 30
        assert config["ISP_TYPE"] == "cmcc"
        assert config["THEME"] == "dark"


class TestValidateConfigTypeErrors:
    """类型错误应回退到默认值（bool->int 特例：1/0 转换而非回退）。"""

    def test_int_field_receives_string(self) -> None:
        """int 字段收到 string 应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["MAX_WIFI_RETRY"] = "ten"

        fixed = validate_config(config)
        assert "MAX_WIFI_RETRY" in fixed
        assert config["MAX_WIFI_RETRY"] == DEFAULT_CONFIG["MAX_WIFI_RETRY"]

    def test_str_field_receives_int(self) -> None:
        """str 字段收到 int 应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["WIFI_NAME"] = 12345

        fixed = validate_config(config)
        assert "WIFI_NAME" in fixed
        assert config["WIFI_NAME"] == DEFAULT_CONFIG["WIFI_NAME"]

    def test_bool_field_receives_int(self) -> None:
        """bool 字段收到 int 应转换为 bool（JSON 里 true/false 可能存成 1/0）"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["AUTOSTART"] = 1

        fixed = validate_config(config)
        assert "AUTOSTART" in fixed
        assert config["AUTOSTART"] is True

    def test_int_field_receives_bool(self) -> None:
        """int 字段收到 bool 应回退（bool 是 int 子类，需显式排除）"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["MAX_WIFI_RETRY"] = True

        fixed = validate_config(config)
        assert "MAX_WIFI_RETRY" in fixed
        assert config["MAX_WIFI_RETRY"] == DEFAULT_CONFIG["MAX_WIFI_RETRY"]

    def test_list_field_receives_string(self) -> None:
        """list 字段收到 string 应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["HOLIDAY_PERIODS"] = "not a list"

        fixed = validate_config(config)
        assert "HOLIDAY_PERIODS" in fixed
        assert isinstance(config["HOLIDAY_PERIODS"], list)


class TestValidateConfigValueRange:
    """值域不合法应回退到默认值（小时/分钟/枚举/格式等参数化边界）。"""

    @pytest.mark.parametrize("hour", [-1, 24, 25, 100])
    def test_shutdown_hour_out_of_range(self, hour: int) -> None:
        """SHUTDOWN_HOUR 超出 0-23 应回退（含 -1/24 两个紧邻边界）"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["SHUTDOWN_HOUR"] = hour

        fixed = validate_config(config)
        assert "SHUTDOWN_HOUR" in fixed
        assert config["SHUTDOWN_HOUR"] == DEFAULT_CONFIG["SHUTDOWN_HOUR"]

    @pytest.mark.parametrize("minute", [-1, 60, 61, 100])
    def test_shutdown_min_out_of_range(self, minute: int) -> None:
        """SHUTDOWN_MIN 超出 0-59 应回退（含 -1/60 两个紧邻边界）"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["SHUTDOWN_MIN"] = minute

        fixed = validate_config(config)
        assert "SHUTDOWN_MIN" in fixed
        assert config["SHUTDOWN_MIN"] == DEFAULT_CONFIG["SHUTDOWN_MIN"]

    def test_isp_type_invalid(self) -> None:
        """ISP_TYPE 不在枚举中应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["ISP_TYPE"] = "unknown_provider"

        fixed = validate_config(config)
        assert "ISP_TYPE" in fixed
        assert config["ISP_TYPE"] == DEFAULT_CONFIG["ISP_TYPE"]

    def test_theme_invalid(self) -> None:
        """THEME 不在 ('light', 'dark') 中应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["THEME"] = "purple"

        fixed = validate_config(config)
        assert "THEME" in fixed
        assert config["THEME"] == DEFAULT_CONFIG["THEME"]

    def test_max_wifi_retry_negative(self) -> None:
        """MAX_WIFI_RETRY 为负数应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["MAX_WIFI_RETRY"] = -1

        fixed = validate_config(config)
        assert "MAX_WIFI_RETRY" in fixed
        assert config["MAX_WIFI_RETRY"] == DEFAULT_CONFIG["MAX_WIFI_RETRY"]

    @pytest.mark.parametrize("fmt", [-1, 2, 5])
    def test_lunar_display_format_invalid(self, fmt: object) -> None:
        """LUNAR_DISPLAY_FORMAT 不在 (0, 1) 中应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["LUNAR_DISPLAY_FORMAT"] = fmt

        fixed = validate_config(config)
        assert "LUNAR_DISPLAY_FORMAT" in fixed
        assert config["LUNAR_DISPLAY_FORMAT"] == DEFAULT_CONFIG["LUNAR_DISPLAY_FORMAT"]


class TestValidateConfigMissingFields:
    """缺失字段应补充默认值（顶层字段与整个嵌套节）。"""

    def test_missing_top_level_field(self) -> None:
        """缺失顶级字段应补充"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        del config["WIFI_NAME"]

        fixed = validate_config(config)
        assert "WIFI_NAME" in fixed
        assert config["WIFI_NAME"] == DEFAULT_CONFIG["WIFI_NAME"]

    def test_missing_multiple_fields(self) -> None:
        """同时缺失多个字段应全部补充"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        del config["WIFI_NAME"]
        del config["USERNAME"]
        del config["SHUTDOWN_HOUR"]

        fixed = validate_config(config)
        assert "WIFI_NAME" in fixed
        assert "USERNAME" in fixed
        assert "SHUTDOWN_HOUR" in fixed

    def test_missing_date_rules_entirely(self) -> None:
        """DATE_RULES 完全缺失应重置为含全部子键的默认结构"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        del config["DATE_RULES"]

        fixed = validate_config(config)
        assert "DATE_RULES" in fixed
        assert isinstance(config["DATE_RULES"], dict)
        assert "ENABLE_CUSTOM_RULE" in config["DATE_RULES"]


class TestValidateConfigDateRulesNested:
    """DATE_RULES 嵌套结构校验：整体类型、子字段缺失与子字段非法值。"""

    def test_date_rules_wrong_type(self) -> None:
        """DATE_RULES 为非 dict 应重置"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["DATE_RULES"] = "not a dict"

        fixed = validate_config(config)
        assert "DATE_RULES" in fixed
        assert isinstance(config["DATE_RULES"], dict)

    def test_date_rules_missing_subfield(self) -> None:
        """DATE_RULES 缺失子字段应补充"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        del config["DATE_RULES"]["ENABLE_CUSTOM_RULE"]

        fixed = validate_config(config)
        assert "DATE_RULES.ENABLE_CUSTOM_RULE" in fixed
        assert "ENABLE_CUSTOM_RULE" in config["DATE_RULES"]

    def test_weekly_execute_days_invalid_element(self) -> None:
        """WEEKLY_EXECUTE_DAYS 包含非法元素（8 超出 0-6）应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"] = [0, 1, 8]  # 8 超出范围

        fixed = validate_config(config)
        assert "DATE_RULES.WEEKLY_EXECUTE_DAYS" in fixed
        assert (
            config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
            == DEFAULT_CONFIG["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
        )

    def test_weekly_execute_days_wrong_type(self) -> None:
        """WEEKLY_EXECUTE_DAYS 类型错误应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"] = "not a list"

        fixed = validate_config(config)
        assert "DATE_RULES.WEEKLY_EXECUTE_DAYS" in fixed
        assert (
            config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
            == DEFAULT_CONFIG["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
        )

    def test_enable_custom_rule_wrong_type(self) -> None:
        """ENABLE_CUSTOM_RULE 类型错误应回退"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["DATE_RULES"]["ENABLE_CUSTOM_RULE"] = "yes"

        fixed = validate_config(config)
        assert "DATE_RULES.ENABLE_CUSTOM_RULE" in fixed
        assert (
            config["DATE_RULES"]["ENABLE_CUSTOM_RULE"]
            == DEFAULT_CONFIG["DATE_RULES"]["ENABLE_CUSTOM_RULE"]
        )


class TestValidateConfigReturnList:
    """返回值是修复字段名列表（用于日志记录哪些字段被自动修复）。"""

    def test_returns_list(self) -> None:
        """返回值应为 list"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["MAX_WIFI_RETRY"] = "bad"

        result = validate_config(config)
        assert isinstance(result, list)

    def test_empty_list_for_valid_config(self) -> None:
        """合法配置返回空列表"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        result = validate_config(config)
        assert result == []

    def test_multiple_fixes_count(self) -> None:
        """多个错误应全部出现在返回列表中"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["MAX_WIFI_RETRY"] = "bad"
        config["SHUTDOWN_HOUR"] = 99
        config["ISP_TYPE"] = "bad"
        del config["WIFI_NAME"]

        result = validate_config(config)
        assert len(result) >= 4


class TestValidateConfigPeriodListElementCleaning:
    """区间列表元素级清洗（F07/B4）：畸形元素被丢弃而非保留。

    修复前 HOLIDAY_PERIODS / CUSTOM_HOLIDAY_PERIODS / CUSTOM_WORKDAY_PERIODS
    仅校验 list 类型，字符串/数字等非 dict 元素会让 is_date_in_period 的
    period.get("start") 抛 AttributeError，沿 should_work_today 传播到主窗口
    构造期（_update_status_display 无 try/except），程序启动即崩且重启复现。
    """

    def test_holiday_periods_invalid_elements_dropped(self) -> None:
        """HOLIDAY_PERIODS 仅保留正常 dict，畸形元素丢弃并记入 fixed"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        valid = {"name": "测试假期", "start": "2026-01-01", "end": "2026-01-03"}
        config["HOLIDAY_PERIODS"] = [
            valid,
            "not a dict",
            5,
            {"start": "x", "end": "y"},
            {"start": "2026-01-01"},  # 缺 end
            {"start": ["2026-01-01"], "end": "2026-01-02"},  # start 不可哈希
        ]

        fixed = validate_config(config)
        assert "HOLIDAY_PERIODS" in fixed
        assert config["HOLIDAY_PERIODS"] == [valid]

    def test_custom_holiday_periods_invalid_elements_dropped(self) -> None:
        """CUSTOM_HOLIDAY_PERIODS 畸形元素丢弃，fixed 用 DATE_RULES. 前缀键名"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        valid = {"name": "自定义假", "start": "2026-02-01", "end": "2026-02-05"}
        config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] = [
            valid,
            "not a dict",
            5,
            {"start": "x", "end": "y"},
            {"start": "2026-01-01"},  # 缺 end
        ]

        fixed = validate_config(config)
        assert "DATE_RULES.CUSTOM_HOLIDAY_PERIODS" in fixed
        assert config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] == [valid]

    def test_custom_workday_periods_invalid_elements_dropped(self) -> None:
        """CUSTOM_WORKDAY_PERIODS 畸形元素丢弃，fixed 用 DATE_RULES. 前缀键名"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        valid = {"name": "自定义班", "start": "2026-03-02", "end": "2026-03-03"}
        config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] = [
            valid,
            "not a dict",
            5,
            {"start": "x", "end": "y"},
            {"start": "2026-01-01"},  # 缺 end
        ]

        fixed = validate_config(config)
        assert "DATE_RULES.CUSTOM_WORKDAY_PERIODS" in fixed
        assert config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] == [valid]

    def test_compensatory_workdays_invalid_elements_dropped(self) -> None:
        """COMPENSATORY_WORKDAYS 中不可解析为 "YYYY-MM-DD" 的元素被过滤"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04", "not-a-date", "2026/01/05", 5, None]

        fixed = validate_config(config)
        assert "COMPENSATORY_WORKDAYS" in fixed
        assert config["COMPENSATORY_WORKDAYS"] == ["2026-01-04"]

    def test_valid_period_lists_not_reported_fixed(self) -> None:
        """全部合法的区间/日期列表不应触发任何修复"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["HOLIDAY_PERIODS"] = [{"name": "寒假", "start": "2026-01-15", "end": "2026-02-28"}]
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04", "2026-02-14"]
        config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] = [
            {"start": "2026-03-01", "end": "2026-03-02"}
        ]
        config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] = [
            {"start": "2026-03-03", "end": "2026-03-04"}
        ]

        fixed = validate_config(config)
        assert fixed == []


class TestMalformedPeriodsShouldWorkTodayRegression:
    """F07/B4 回归钉板：含畸形区间元素的配置清洗后，should_work_today 不抛异常且返回 bool。"""

    def test_should_work_today_custom_rule_after_cleaning(self) -> None:
        """自定义规则分支遍历清洗后的 CUSTOM_*_PERIODS，判定正常返回 bool"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["HOLIDAY_PERIODS"] = [
            "not a dict",
            5,
            {"start": "x", "end": "y"},
            {"name": "有效假期", "start": "2026-01-05", "end": "2026-01-06"},
        ]
        config["COMPENSATORY_WORKDAYS"] = ["not-a-date", 7]
        config["DATE_RULES"]["ENABLE_CUSTOM_RULE"] = True
        config["DATE_RULES"]["CUSTOM_HOLIDAY_PERIODS"] = [
            "not a dict",
            {"start": "x", "end": "y"},
        ]
        config["DATE_RULES"]["CUSTOM_WORKDAY_PERIODS"] = [42, {"start": "2026-01-05"}]
        validate_config(config)

        global_config.clear()
        global_config.update(config)

        # 2026-01-05 周一：自定义分支先遍历清洗后的两个区间列表（均为空），
        # 再按 WEEKLY_EXECUTE_DAYS 判定 -> True。修复前此处抛 AttributeError。
        result = should_work_today(datetime.date(2026, 1, 5))
        assert isinstance(result, bool)
        assert result is True

    def test_should_work_today_base_branch_after_cleaning(self) -> None:
        """基础规则分支遍历清洗后的 HOLIDAY_PERIODS，合法区间照常生效"""
        config = copy.deepcopy(DEFAULT_CONFIG)
        config["HOLIDAY_PERIODS"] = [
            "not a dict",
            5,
            {"name": "测试假期", "start": "2026-01-05", "end": "2026-01-06"},
        ]
        config["COMPENSATORY_WORKDAYS"] = ["not-a-date", "2026-01-04"]
        validate_config(config)

        global_config.clear()
        global_config.update(config)

        # 2026-01-05 周一命中清洗后保留的假期区间 -> False
        assert should_work_today(datetime.date(2026, 1, 5)) is False
        # 2026-01-04 周日命中清洗后保留的调休上班日 -> True
        assert should_work_today(datetime.date(2026, 1, 4)) is True
