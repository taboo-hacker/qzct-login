"""core/holidays.py 的单元测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.holidays import (
    COMPENSATORY_WORKDAYS,
    HOLIDAY_PERIODS,
    check_holiday_data_freshness,
)


class TestCheckHolidayDataFreshness:
    """check_holiday_data_freshness 的测试。"""

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
        """验证不同当前年份下的数据新鲜度检测。"""
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
        """验证警告消息中包含最新覆盖年份。"""
        with patch("core.holidays.datetime") as mock_dt:
            mock_dt.date.today.return_value = type("FakeDate", (), {"year": 2050})()
            result = check_holiday_data_freshness()

        assert result is not None
        latest_year = max(int(p["start"][:4]) for p in HOLIDAY_PERIODS)
        assert str(latest_year) in result

    def test_freshness_check_returns_none_when_data_covers_current_year(self) -> None:
        """当前年份等于最新覆盖年份时应返回 None。"""
        latest_year = max(int(p["start"][:4]) for p in HOLIDAY_PERIODS)
        with patch("core.holidays.datetime") as mock_dt:
            mock_dt.date.today.return_value = type("FakeDate", (), {"year": latest_year})()
            assert check_holiday_data_freshness() is None


class TestHolidayDataIntegrity:
    """验证 HOLIDAY_PERIODS 和 COMPENSATORY_WORKDAYS 数据完整性。"""

    def test_holiday_periods_not_empty(self) -> None:
        assert len(HOLIDAY_PERIODS) > 0

    def test_each_holiday_period_has_required_fields(self) -> None:
        for period in HOLIDAY_PERIODS:
            assert "name" in period
            assert "start" in period
            assert "end" in period
            assert len(period["start"]) == 10
            assert len(period["end"]) == 10

    def test_compensatory_workdays_format(self) -> None:
        for date_str in COMPENSATORY_WORKDAYS:
            assert len(date_str) == 10
            assert date_str[4] == "-"
            assert date_str[7] == "-"

    def test_holiday_periods_start_dates_are_valid_dates(self) -> None:
        """所有 start 日期都是有效的 YYYY-MM-DD 格式。"""
        for period in HOLIDAY_PERIODS:
            year = int(period["start"][:4])
            assert 2020 <= year <= 2030
