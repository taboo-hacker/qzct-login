"""
CalendarView 万年历视图测试

覆盖三块核心行为：
- mark_execution_dates：标记跟随“当前显示月份”（翻页后 selectedDate 停留旧页，
  必须以 yearShown/monthShown 定位——回归：翻页后新月份无标记），
  且重标前清空历史标记（无跨月残留）；
- LUNAR_DISPLAY_FORMAT 设置项消费：简化/完整两种农历显示格式切换生效；
- should_work_on_date：状态文案与判定核心（core.date_rules）的优先级一致；
- 非颜色冗余编码（UX-11）：执行日数字加粗、休息日常规字重，图例含
  “加粗”文字提示——红绿色觉障碍用户不依赖底色也能区分执行/不执行。

各用例先替换 global_config 为受控数据（conftest autouse fixture 负责还原），
判定函数按需 patch 为确定值，避免依赖真实节假日库数据。
"""

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCalendarWidget, QLabel
from pytestqt.qtbot import QtBot

from core.config import global_config

if TYPE_CHECKING:
    from gui.widgets.calendar_view import CalendarView


from tests.conftest import ensure_qapp as _ensure_qapp


def _make_view(qtbot: QtBot) -> "CalendarView":
    """创建受控配置下的 CalendarView（判定函数由调用方自行 patch）。"""
    from gui.widgets.calendar_view import CalendarView

    view = CalendarView()
    qtbot.addWidget(view)
    return view


def _has_custom_format(calendar: QCalendarWidget, qdate: QDate) -> bool:
    """该日期是否被设置过自定义格式（有实底色即视为已标记）。"""
    fmt = calendar.dateTextFormat(qdate)
    return bool(fmt.background().style() == Qt.BrushStyle.SolidPattern)


class TestMarkExecutionDates:
    """mark_execution_dates 测试：标记跟随显示月份、翻页清残留。"""

    def test_marks_shown_month_after_page_flip(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """回归：翻页后新显示月份必须有执行标记（selectedDate 停留旧页）。"""
        _ensure_qapp()
        view = _make_view(qtbot)
        assert view.calendar is not None

        import gui.widgets.calendar_view as cv

        monkeypatch.setattr(cv, "should_work_today", lambda d: True)

        # 翻到下一个月：selectedDate 不变（停留旧月），monthShown 前进
        view.calendar.showNextMonth()
        shown_year = view.calendar.yearShown()
        shown_month = view.calendar.monthShown()
        assert (shown_year, shown_month) != (
            view.calendar.selectedDate().year(),
            view.calendar.selectedDate().month(),
        )

        view.mark_execution_dates()
        # 新显示月份的月初/月中/月末都应有标记
        for day in (1, 15, 28):
            marked = _has_custom_format(view.calendar, QDate(shown_year, shown_month, day))
            assert marked, f"{shown_year}-{shown_month}-{day} 翻页后未标记"

    def test_clears_stale_formats_from_other_months(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """重标前清空全部历史格式：其他月份日期不应残留旧标记。"""
        _ensure_qapp()
        view = _make_view(qtbot)
        assert view.calendar is not None

        import gui.widgets.calendar_view as cv

        monkeypatch.setattr(cv, "should_work_today", lambda d: True)

        shown_year = view.calendar.yearShown()
        shown_month = view.calendar.monthShown()

        # 先人为给“下个月 15 日”塞一个旧标记，再重标当前月
        stale = QDate(shown_year, shown_month, 15).addMonths(1)
        from PySide6.QtGui import QColor, QTextCharFormat

        stale_fmt = QTextCharFormat()
        stale_fmt.setBackground(QColor(255, 0, 0))
        view.calendar.setDateTextFormat(stale, stale_fmt)
        assert _has_custom_format(view.calendar, stale)

        view.mark_execution_dates()
        assert not _has_custom_format(view.calendar, stale), "其他月份的旧标记未被清除"

    def test_workday_and_restday_get_different_colors(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """执行日与休息日应分别使用 success/danger 底色。"""
        _ensure_qapp()
        view = _make_view(qtbot)
        assert view.calendar is not None

        import gui.widgets.calendar_view as cv

        # 偶数日执行、奇数日休息，保证两种状态都被触发
        monkeypatch.setattr(cv, "should_work_today", lambda d: d.day % 2 == 0)

        year, month = view.calendar.yearShown(), view.calendar.monthShown()
        view.mark_execution_dates()

        work_fmt = view.calendar.dateTextFormat(QDate(year, month, 2))
        rest_fmt = view.calendar.dateTextFormat(QDate(year, month, 1))
        assert work_fmt.background().color() != rest_fmt.background().color()

    def test_workday_bold_restday_normal_font_weight(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """UX-11：执行日数字加粗（Bold）、休息日显式常规字重（Normal）。"""
        _ensure_qapp()
        view = _make_view(qtbot)
        assert view.calendar is not None

        import gui.widgets.calendar_view as cv

        monkeypatch.setattr(cv, "should_work_today", lambda d: d.day % 2 == 0)

        year, month = view.calendar.yearShown(), view.calendar.monthShown()
        view.mark_execution_dates()

        work_fmt = view.calendar.dateTextFormat(QDate(year, month, 2))
        rest_fmt = view.calendar.dateTextFormat(QDate(year, month, 1))
        assert work_fmt.fontWeight() == int(QFont.Weight.Bold)
        assert rest_fmt.fontWeight() == int(QFont.Weight.Normal)

        # update_theme 刷新路径内部重跑 mark_execution_dates，加粗编码应保持
        view.update_theme()
        refreshed = view.calendar.dateTextFormat(QDate(year, month, 2))
        assert refreshed.fontWeight() == int(QFont.Weight.Bold)


class TestLegendAccessibility:
    """图例可访问性测试：非颜色冗余编码（UX-11 色觉障碍友好）。"""

    def test_legend_contains_bold_hint(self, qtbot: QtBot) -> None:
        """图例应包含“加粗日期 = 需要执行任务”文字提示。"""
        _ensure_qapp()
        view = _make_view(qtbot)

        hint = view.findChild(QLabel, "legendBoldHint")
        assert hint is not None, "图例缺少加粗提示标签"
        assert "加粗" in hint.text()
        assert "需要执行任务" in hint.text()


class TestLunarDisplayFormat:
    """LUNAR_DISPLAY_FORMAT 消费测试：简化/完整农历格式切换生效。"""

    def test_simple_format_by_default(self, qtbot: QtBot) -> None:
        """默认（0）显示简化格式：不含农历年份（如“农历 正月十五”）。"""
        _ensure_qapp()
        global_config["LUNAR_DISPLAY_FORMAT"] = 0
        view = _make_view(qtbot)
        assert view.calendar is not None

        view.calendar.setSelectedDate(QDate(2026, 8, 15))
        assert view.lunar_date_label is not None
        assert "年" not in view.lunar_date_label.text()

    def test_full_format_shows_year(self, qtbot: QtBot) -> None:
        """完整格式（1）显示农历年份（如“农历二〇二六年…”）。"""
        _ensure_qapp()
        global_config["LUNAR_DISPLAY_FORMAT"] = 1
        view = _make_view(qtbot)
        assert view.calendar is not None

        view.calendar.setSelectedDate(QDate(2026, 8, 15))
        assert view.lunar_date_label is not None
        assert "年" in view.lunar_date_label.text()

    def test_format_switch_without_date_change(self, qtbot: QtBot) -> None:
        """同一日期上切换格式设置后刷新应立即生效（缓存存两种格式）。"""
        _ensure_qapp()
        view = _make_view(qtbot)
        assert view.calendar is not None

        view.calendar.setSelectedDate(QDate(2026, 10, 1))
        global_config["LUNAR_DISPLAY_FORMAT"] = 1
        view.on_date_selected()
        assert view.lunar_date_label is not None
        assert "年" in view.lunar_date_label.text()

        global_config["LUNAR_DISPLAY_FORMAT"] = 0
        view.on_date_selected()
        assert "年" not in view.lunar_date_label.text()


class TestShouldWorkOnDateStatus:
    """should_work_on_date 状态文案测试：与判定核心优先级一致。"""

    def test_custom_rule_overrides_holiday_status_text(self, qtbot: QtBot) -> None:
        """自定义规则模式下，文案应反映自定义来源而非内置节假日。"""
        _ensure_qapp()
        global_config.replace_all(
            {
                "HOLIDAY_PERIODS": [
                    {"name": "内置假期", "start": "2026-07-01", "end": "2026-07-31"}
                ],
                "COMPENSATORY_WORKDAYS": [],
                "DATE_RULES": {
                    "ENABLE_CUSTOM_RULE": True,
                    "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
                    "CUSTOM_HOLIDAY_PERIODS": [
                        {"name": "自定义暑假", "start": "2026-07-10", "end": "2026-07-20"}
                    ],
                    "CUSTOM_WORKDAY_PERIODS": [],
                },
            }
        )
        view = _make_view(qtbot)

        import datetime

        # 7 月 15 日同时落在内置假期与自定义假期区间：文案应说“自定义假期”
        need_work, status = view.should_work_on_date(datetime.date(2026, 7, 15))
        assert need_work is False
        assert "自定义假期" in status
        assert "内置假期" not in status

        # 7 月 25 日不在自定义区间，靠每周执行日判定：文案应说“自定义每周”
        _, status2 = view.should_work_on_date(datetime.date(2026, 7, 25))  # 周六
        assert "自定义每周休息日" in status2

    def test_base_mode_holiday_status_text(self, qtbot: QtBot) -> None:
        """非自定义模式下文案保持调休/内置节假日来源。"""
        _ensure_qapp()
        global_config.replace_all(
            {
                "HOLIDAY_PERIODS": [
                    {"name": "测试假期", "start": "2026-01-01", "end": "2026-01-03"}
                ],
                "COMPENSATORY_WORKDAYS": ["2026-01-04"],
                "DATE_RULES": {
                    "ENABLE_CUSTOM_RULE": False,
                    "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
                    "CUSTOM_HOLIDAY_PERIODS": [],
                    "CUSTOM_WORKDAY_PERIODS": [],
                },
            }
        )
        view = _make_view(qtbot)

        import datetime

        _, status = view.should_work_on_date(datetime.date(2026, 1, 2))
        assert "节假日(测试假期)" in status

        _, status2 = view.should_work_on_date(datetime.date(2026, 1, 4))
        assert "调休上班日" in status2


class TestSourceTextSingleSource:
    """来源文案单一数据源测试：_SOURCE_TEXT 是 core.date_rules.SOURCE_TEXT 的别名。"""

    def test_source_text_is_alias_of_core_constant(self) -> None:
        """类属性 _SOURCE_TEXT 应直接引用 core 的 SOURCE_TEXT（不再第三份私有实现）。"""
        from core.date_rules import SOURCE_TEXT
        from gui.widgets.calendar_view import CalendarView

        assert CalendarView._SOURCE_TEXT is SOURCE_TEXT
