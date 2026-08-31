"""
万年历视图组件

从 CalendarDialog 抽取的可嵌入视图：日历 + 农历详情 + 执行计划图例。
完整适配亮色/暗色主题（update_theme 重新着色，QCalendarWidget 使用主题调色板）。
"""

import datetime
from typing import Any

from lunar_python import Solar
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QPalette, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.config import global_config
from core.date_rules import rule_source, should_work_today
from gui.styling.theme_manager import ThemeManager
from gui.styling.widgets import create_card_widget, create_label
from infra import debug, error, info, warning

# 星期名称常量（模块级，避免每次调用重新创建）
WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# _lunar_cache 的最大条目数
_LUNAR_CACHE_MAX_SIZE = 400


class CalendarView(QWidget):
    """万年历视图：日历组件 + 农历详情 + 执行计划图例。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lunar_cache: dict[datetime.date, dict[str, Any]] = {}
        self._current_status: str = ""

        # 组件引用
        self.calendar: QCalendarWidget | None = None
        self.solar_label: QLabel | None = None
        self.lunar_date_label: QLabel | None = None
        self.ganzhi_label: QLabel | None = None
        self.yi_label: QLabel | None = None
        self.ji_label: QLabel | None = None
        self.extra_info_label: QLabel | None = None
        self.work_status_label: QLabel | None = None
        self._legend_color_labels: list[QLabel] = []

        self._init_ui()
        info("main", "万年历视图初始化完成")

    @property
    def lunar_cache(self) -> dict[datetime.date, dict[str, Any]]:
        """农历详情缓存（公开只读视图，供 CalendarDialog 等外部访问）。"""
        return self._lunar_cache

    def _init_ui(self) -> None:
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 日历组件
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.currentPageChanged.connect(self.on_month_changed)
        self.calendar.setMinimumHeight(240)
        main_layout.addWidget(self.calendar)

        # 详情区域（滚动，空间不足时可滚动查看）
        scroll_area = QScrollArea()
        scroll_area.setObjectName("calendarScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.detail_frame = create_card_widget()
        self.detail_frame.setObjectName("detailCard")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(20, 16, 20, 16)
        detail_layout.setSpacing(8)

        # 公历日期
        self.solar_label = create_label("", font_size=11, bold=True)
        self.solar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.solar_label)

        # 农历日期
        self.lunar_date_label = create_label("", font_size=10)
        self.lunar_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.lunar_date_label)

        # 干支
        self.ganzhi_label = create_label("", font_size=10)
        self.ganzhi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.ganzhi_label)

        # 分隔线
        detail_layout.addWidget(self._make_separator())

        # 宜
        self.yi_label = create_label("", font_size=10)
        self.yi_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.yi_label.setWordWrap(True)
        detail_layout.addWidget(self.yi_label)

        # 忌
        self.ji_label = create_label("", font_size=10)
        self.ji_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ji_label.setWordWrap(True)
        detail_layout.addWidget(self.ji_label)

        # 分隔线
        detail_layout.addWidget(self._make_separator())

        # 额外信息
        self.extra_info_label = create_label("", font_size=9)
        self.extra_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.extra_info_label.setWordWrap(True)
        detail_layout.addWidget(self.extra_info_label)

        # 工作状态
        self.work_status_label = create_label("", font_size=10, bold=True)
        self.work_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.work_status_label)

        scroll_area.setWidget(self.detail_frame)
        scroll_area.setMaximumHeight(200)
        main_layout.addWidget(scroll_area)

        # 图例
        legend_layout = self._create_legend()
        main_layout.addLayout(legend_layout)

        # 连接事件
        self.calendar.selectionChanged.connect(self.on_date_selected)
        # update_theme() 内部已调用 mark_execution_dates()，无需再显式标记一次
        self.update_theme()
        self.on_date_selected()

    @staticmethod
    def _make_separator() -> QFrame:
        """详情卡片内的水平分隔线（objectName=divider 接入全局 QSS）。"""
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    def update_theme(self) -> None:
        """按当前主题重新着色（日历调色板 + 详情标签 + 图例 + 日期标记）。"""
        theme = ThemeManager.current_theme()

        # QCalendarWidget 调色板：深色模式下 QSS 无法覆盖的部分由调色板兜底
        if self.calendar is not None:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(theme.card_bg))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.text_primary))
            palette.setColor(QPalette.ColorRole.Base, QColor(theme.card_bg))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.hover_bg))
            palette.setColor(QPalette.ColorRole.Text, QColor(theme.text_primary))
            palette.setColor(QPalette.ColorRole.Button, QColor(theme.card_bg))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.text_primary))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.primary))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            self.calendar.setPalette(palette)

        if self.lunar_date_label is not None:
            self.lunar_date_label.setStyleSheet(f"color: {theme.danger}; background: transparent;")
        if self.ganzhi_label is not None:
            self.ganzhi_label.setStyleSheet(
                f"color: {theme.text_primary}; background: transparent;"
            )
        if self.extra_info_label is not None:
            self.extra_info_label.setStyleSheet(
                f"color: {theme.text_secondary}; background: transparent;"
            )
        if self.yi_label is not None:
            self.yi_label.setStyleSheet(
                f"color: {theme.success}; margin-top: 3px; padding: 5px; "
                f"background-color: {theme.success_bg}; border-radius: 3px;"
            )
        if self.ji_label is not None:
            self.ji_label.setStyleSheet(
                f"color: {theme.danger}; margin-top: 3px; padding: 5px; "
                f"background-color: {theme.danger_bg}; border-radius: 3px;"
            )
        self._style_work_status()

        # 图例色块
        legend_colors = (theme.success, theme.danger, theme.warning)
        for label, color in zip(self._legend_color_labels, legend_colors, strict=True):
            label.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        # 重新标记本月日期
        self.mark_execution_dates()

    def _create_legend(self) -> QHBoxLayout:
        """创建图例"""
        legend_layout = QHBoxLayout()
        legend_layout.addStretch()
        legend_layout.addWidget(self._create_legend_item("需要执行任务"))
        legend_layout.addSpacing(16)
        legend_layout.addWidget(self._create_legend_item("不执行任务"))
        legend_layout.addSpacing(16)
        legend_layout.addWidget(self._create_legend_item("调休上班"))
        legend_layout.addStretch()
        return legend_layout

    def _create_legend_item(self, text: str) -> QWidget:
        """创建单个图例项（色块颜色由 update_theme 统一填充）。"""
        legend = QWidget()
        layout = QHBoxLayout(legend)

        color_label = QLabel()
        color_label.setFixedSize(14, 14)
        color_label.setStyleSheet("border-radius: 2px;")
        self._legend_color_labels.append(color_label)

        text_label = create_label(text, font_size=9)
        layout.addWidget(color_label)
        layout.addWidget(text_label)
        layout.setContentsMargins(0, 0, 0, 0)
        return legend

    def on_month_changed(self, year: int, month: int) -> None:
        """月份变化时重新标记日期"""
        debug("main", f"万年历月份切换到：{year}-{month}")
        self.mark_execution_dates()

    def on_date_selected(self) -> None:
        """当选择日期变化时更新状态显示"""
        try:
            if self.calendar is None:
                return

            selected_date = self.calendar.selectedDate()
            date = datetime.date(selected_date.year(), selected_date.month(), selected_date.day())

            weekday_str = WEEKDAY_NAMES[date.weekday()]

            if self.solar_label:
                self.solar_label.setText(f"{date.year}年{date.month}月{date.day}日 ({weekday_str})")

            should_work, status = self.should_work_on_date(date)
            self._current_status = status

            if global_config.get("SHOW_LUNAR_CALENDAR", True):
                lunar_detail = self._get_lunar_detail(date)

                # 农历显示格式：0=简化（正月初一）/ 1=完整（农历二〇二五年正月初一）
                lunar_date_key = (
                    "lunar_date_full"
                    if global_config.get("LUNAR_DISPLAY_FORMAT", 0) == 1
                    else "lunar_date_simple"
                )

                if self.lunar_date_label:
                    self.lunar_date_label.setText(lunar_detail.get(lunar_date_key, ""))
                if self.ganzhi_label:
                    self.ganzhi_label.setText(lunar_detail.get("ganzhi", ""))

                yi_list = lunar_detail.get("yi", [])
                ji_list = lunar_detail.get("ji", [])

                if self.yi_label:
                    self.yi_label.setVisible(bool(yi_list))
                    if yi_list:
                        self.yi_label.setText(f"宜：{' '.join(yi_list)}")
                if self.ji_label:
                    self.ji_label.setVisible(bool(ji_list))
                    if ji_list:
                        self.ji_label.setText(f"忌：{' '.join(ji_list)}")

                extra_parts = []
                if lunar_detail.get("jieqi"):
                    extra_parts.append(f"节气：{lunar_detail['jieqi']}")
                if lunar_detail.get("festivals"):
                    all_festivals = lunar_detail["festivals"].get("traditional", []) + lunar_detail[
                        "festivals"
                    ].get("solar", [])
                    if all_festivals:
                        extra_parts.append(f"节日：{'、'.join(all_festivals)}")
                if lunar_detail.get("other_info"):
                    extra_parts.append(lunar_detail["other_info"])

                if self.extra_info_label:
                    if extra_parts:
                        self.extra_info_label.setText(" | ".join(extra_parts))
                        self.extra_info_label.setVisible(True)
                    else:
                        self.extra_info_label.setVisible(False)
            else:
                for label in (
                    self.lunar_date_label,
                    self.ganzhi_label,
                    self.yi_label,
                    self.ji_label,
                    self.extra_info_label,
                ):
                    if label is not None:
                        label.setVisible(False)

            if self.work_status_label:
                self.work_status_label.setText(status)
                self._style_work_status()

            debug("main", f"万年历日期选中：{date}")
        except Exception as e:
            error("main", "日期选择处理出错", exc_info=True)
            if self.solar_label:
                self.solar_label.setText(f"日期处理出错：{str(e)}")

    def _style_work_status(self) -> None:
        """按当前主题与状态设置工作状态标签样式。"""
        theme = ThemeManager.current_theme()
        if self.work_status_label is None:
            return

        status = self._current_status
        if "不执行" in status:
            bg, fg = theme.danger_bg, theme.danger
        elif "调休" in status:
            bg, fg = theme.warning_bg, theme.warning
        elif "需要执行" in status:
            bg, fg = theme.success_bg, theme.success
        else:
            bg, fg = theme.primary_bg, theme.primary

        self.work_status_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"padding: 6px; border-radius: 4px; margin-top: 4px;"
        )

    def _get_lunar_detail(self, date: datetime.date) -> dict[str, Any]:
        """获取完整万年历信息，使用缓存提高性能"""
        if date in self._lunar_cache:
            return self._lunar_cache[date]

        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()

            lunar_month = lunar.getMonthInChinese()
            lunar_day = lunar.getDayInChinese()
            lunar_year_str = lunar.getYearInChinese()
            # 两种显示格式都算好缓存（LUNAR_DISPLAY_FORMAT 运行时可切换）
            lunar_date_simple = f"农历 {lunar_month}月{lunar_day}"
            lunar_date_full = f"农历{lunar_year_str}年{lunar_month}月{lunar_day}"

            year_ganzhi = lunar.getYearInGanZhi()
            month_ganzhi = lunar.getMonthInGanZhi()
            day_ganzhi = lunar.getDayInGanZhi()
            year_shengxiao = lunar.getYearShengXiao()
            ganzhi_str = f"{year_ganzhi}年 ({year_shengxiao}年) {month_ganzhi}月 {day_ganzhi}日"

            yi_list = lunar.getDayYi()
            ji_list = lunar.getDayJi()
            jieqi = lunar.getJieQi()

            festivals: dict[str, list[str]] = {"traditional": [], "solar": []}
            lunar_festivals = lunar.getFestivals()
            if lunar_festivals:
                festivals["traditional"].extend(lunar_festivals)
            solar_festivals = solar.getFestivals()
            if solar_festivals:
                festivals["solar"].extend(solar_festivals)

            result = {
                "lunar_date_simple": lunar_date_simple,
                "lunar_date_full": lunar_date_full,
                "ganzhi": ganzhi_str,
                "yi": yi_list,
                "ji": ji_list,
                "jieqi": jieqi if jieqi else "",
                "festivals": festivals,
                "other_info": f"农历{lunar_year_str}年",
            }

            self._lunar_cache[date] = result
            # 缓存超过上限时淘汰最旧条目（保持插入序），翻回旧月份仍能命中
            while len(self._lunar_cache) > _LUNAR_CACHE_MAX_SIZE:
                oldest = next(iter(self._lunar_cache))
                del self._lunar_cache[oldest]
            return result
        except Exception as e:
            warning("main", f"农历转换失败：{e}")
            return {
                "lunar_date_simple": "（农历转换失败）",
                "lunar_date_full": "（农历转换失败）",
                "ganzhi": "",
                "yi": [],
                "ji": [],
                "jieqi": "",
                "festivals": {"traditional": [], "solar": []},
                "other_info": "",
            }

    # 来源标识 → 状态文案前缀（与 core.date_rules.rule_source 的返回值对应；
    # 法定假日/周末等无名称来源不加前缀，保持简洁）
    _SOURCE_TEXT = {
        "custom_workday": "自定义工作日",
        "custom_holiday": "自定义假期",
        "custom_weekly_work": "自定义每周执行日",
        "custom_weekly_rest": "自定义每周休息日",
        "compensatory": "调休上班日",
        "builtin_holiday": "节假日",
    }

    def should_work_on_date(self, date: datetime.date) -> tuple[bool, str]:
        """判断指定日期是否需要执行任务，并给出状态文案。

        布尔判定与来源均委托 core.date_rules.rule_source（唯一优先级阶梯），
        本方法只负责把来源翻译成用户可读文案，避免两处阶梯实现漂移。
        """
        try:
            result = should_work_today(date)
            source, period = rule_source(date)
            debug(
                "main",
                f"检查日期 {date} 是否需要执行任务: {'是' if result else '否'}（来源 {source}）",
            )

            prefix = self._SOURCE_TEXT.get(source)
            if prefix is None:
                status = "需要执行任务" if result else "不执行任务"
            else:
                name = period.get("name") if period else None
                label = f"{prefix}({name})" if name else prefix
                status = f"{label} - {'需要执行任务' if result else '不执行任务'}"

            return (result, status)
        except Exception as e:
            error(
                "main",
                f"判断日期 {date} 是否需要执行任务时出错",
                exc_info=True,
            )
            return (False, f"错误：{str(e)}")

    def mark_execution_dates(self) -> None:
        """标记日历当前显示月份的执行日期（颜色取自当前主题）。

        以 yearShown()/monthShown() 为准：currentPageChanged 信号触发时
        selectedDate 仍停留在旧页（翻页不改变选中日期），用它定位会把
        颜色标到错误月份，导致新翻到的月份完全没有标记。
        每次先清空全部日期格式再重标：setDateTextFormat 按 QDate 永久生效，
        不清除会残留旧主题色、旧配置下计算的标记。
        """
        try:
            if self.calendar is None:
                return

            theme = ThemeManager.current_theme()
            current_year = self.calendar.yearShown()
            current_month = self.calendar.monthShown()

            first_day = datetime.date(current_year, current_month, 1)
            if current_month == 12:
                last_day = datetime.date(current_year, current_month, 31)
            else:
                last_day = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(
                    days=1
                )

            work_bg = QColor(theme.success)
            work_bg.setAlpha(80)
            rest_bg = QColor(theme.danger)
            rest_bg.setAlpha(80)
            fg = QColor(theme.text_primary)

            # 传入无效 QDate 清除所有日期的自定义格式（Qt 约定行为）
            self.calendar.setDateTextFormat(QDate(), QTextCharFormat())

            day_count = 0
            iter_date = first_day
            while iter_date <= last_day:
                try:
                    # 直接用判定核心（bool 即可，跳过 should_work_on_date 的
                    # 状态文案拼装——那是选中详情专用，逐日标记时是纯开销）
                    should_work = should_work_today(iter_date)
                    qt_date = QDate(iter_date.year, iter_date.month, iter_date.day)

                    fmt = QTextCharFormat()
                    fmt.setBackground(work_bg if should_work else rest_bg)
                    fmt.setForeground(fg)
                    self.calendar.setDateTextFormat(qt_date, fmt)
                    day_count += 1
                except Exception as e:
                    warning("main", f"标记日期 {iter_date} 时出错: {e}")

                iter_date += datetime.timedelta(days=1)

            debug(
                "main", f"完成标记 {current_year}年{current_month}月 的执行日期，共 {day_count} 天"
            )
        except Exception as e:
            error("main", "标记执行日期时出错", exc_info=True)
            QMessageBox.warning(self, "错误", f"标记日历日期时出错: {str(e)}")
