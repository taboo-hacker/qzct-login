"""core/holidays.py 的单元测试。

覆盖两部分：
- check_holiday_data_freshness：通过 monkeypatch datetime 模拟不同"当前年份"，
  验证假期数据是否覆盖当年（未覆盖时应返回含"数据缺失"的警告字符串）；
- HOLIDAY_PERIODS / COMPENSATORY_WORKDAYS 静态数据完整性校验。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.holidays import (
    COMPENSATORY_WORKDAYS,
    HOLIDAY_PERIODS,
    check_holiday_data_freshness,
)


class TestCheckHolidayDataFreshness:
    """check_holiday_data_freshness 的测试：按当前年份是否被假期数据覆盖分组。"""

    @pytest.mark.parametrize(
        "mock_year,should_warn",
        [
            (2025, False),
            (2026, False),
            (2027, True),
            (2030, True),
        ],
    )
    def test_freshness_check(self, mock_year: int, should_warn: bool) -> None:
        """给定模拟的当前年份，数据已覆盖时返回 None，未覆盖时返回含年份的警告。"""
        # patch core.holidays 命名空间内的 datetime，避免依赖真实系统日期
        with patch("core.holidays.datetime") as mock_dt:
            mock_dt.date.today.return_value = type("FakeDate", (), {"year": mock_year})()
            result = check_holiday_data_freshness()

        if should_warn:
            assert result is not None
            assert str(mock_year) in result
            assert "数据缺失" in result
        else:
            assert result is None

    def test_freshness_message_contains_latest_year(self) -> None:
        """数据未覆盖当前年份（2050）时，警告消息应提示最新覆盖到的年份。"""
        with patch("core.holidays.datetime") as mock_dt:
            mock_dt.date.today.return_value = type("FakeDate", (), {"year": 2050})()
            result = check_holiday_data_freshness()

        assert result is not None
        latest_year = max(int(p["start"][:4]) for p in HOLIDAY_PERIODS)
        assert str(latest_year) in result

    def test_freshness_check_returns_none_when_data_covers_current_year(self) -> None:
        """边界情况：当前年份恰好等于最新覆盖年份，视为已覆盖，应返回 None。"""
        latest_year = max(int(p["start"][:4]) for p in HOLIDAY_PERIODS)
        with patch("core.holidays.datetime") as mock_dt:
            mock_dt.date.today.return_value = type("FakeDate", (), {"year": latest_year})()
            assert check_holiday_data_freshness() is None


class TestHolidayDataIntegrity:
    """验证 HOLIDAY_PERIODS 和 COMPENSATORY_WORKDAYS 静态数据的结构完整性。"""

    def test_holiday_periods_not_empty(self) -> None:
        """假期区间列表不应为空，否则日期规则判断会全部失效。"""
        assert len(HOLIDAY_PERIODS) > 0

    def test_each_holiday_period_has_required_fields(self) -> None:
        """每个假期区间必须含 name/start/end 字段，且日期为 10 位 YYYY-MM-DD。"""
        for period in HOLIDAY_PERIODS:
            assert "name" in period
            assert "start" in period
            assert "end" in period
            assert len(period["start"]) == 10
            assert len(period["end"]) == 10

    def test_compensatory_workdays_format(self) -> None:
        """补班日列表每项应为 10 位 YYYY-MM-DD 格式（检查分隔符位置）。"""
        for date_str in COMPENSATORY_WORKDAYS:
            assert len(date_str) == 10
            assert date_str[4] == "-"
            assert date_str[7] == "-"

    def test_holiday_periods_start_dates_are_valid_dates(self) -> None:
        """所有 start 日期的年份应落在 2020-2030 的合理范围内。"""
        for period in HOLIDAY_PERIODS:
            year = int(period["start"][:4])
            assert 2020 <= year <= 2030
