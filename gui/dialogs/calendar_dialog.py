"""
日历对话框模块
使用主题系统重构的万年历对话框
"""

import datetime
from typing import Any, Dict, List, Optional

from lunar_python import Solar
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QTextCharFormat
from PyQt5.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.style_helpers import (
    create_card_widget,
    create_label,
)
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle
from infrastructure import debug, error, info, is_date_in_period, parse_date_str, warning
from system_core import global_config, should_work_today


class CalendarDialog(QDialog):
    """万年历对话框"""

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("万年历 - 任务执行计划")
        self.setMinimumSize(750, 650)
        self._lunar_cache: Dict[datetime.date, Dict[str, Any]] = {}

        # 组件引用
        self.calendar: Optional[QCalendarWidget] = None
        self.solar_label: Optional[QLabel] = None
        self.lunar_date_label: Optional[QLabel] = None
        self.ganzhi_label: Optional[QLabel] = None
        self.yi_label: Optional[QLabel] = None
        self.ji_label: Optional[QLabel] = None
        self.extra_info_label: Optional[QLabel] = None
        self.work_status_label: Optional[QLabel] = None

        self.init_ui()
        self._apply_styles()
        info("main", "万年历对话框初始化完成")

    def _apply_styles(self) -> None:
        """应用 QSS 样式"""
        qss = StyleManager.get_global_stylesheet()
        dialog_qss = StyleManager.get_dialog_stylesheet()
        self.setStyleSheet(qss + dialog_qss)

    def init_ui(self) -> None:
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部标题区域
        header_frame = QFrame()
        header_frame.setObjectName("calendarHeader")
        header_frame.setMinimumHeight(80)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(5)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title = create_label(
            "\U0001f4c5 万年历 - 任务执行计划",
            font_size=FontSize.DIALOG_TITLE,
            bold=True,
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("calendarTitle")
        header_layout.addWidget(title)

        main_layout.addWidget(header_frame)
        main_layout.addSpacing(10)

        # 日历组件
        self.calendar = QCalendarWidget()
        self.calendar.setFont(FontStyle.normal(FontSize.CALENDAR_NORMAL))
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.currentPageChanged.connect(self.on_month_changed)
        self.calendar.setMinimumHeight(300)
        main_layout.addWidget(self.calendar)
        main_layout.addSpacing(10)

        # 详情区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.detail_frame = create_card_widget()
        self.detail_frame.setObjectName("detailCard")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(25, 20, 25, 20)
        detail_layout.setSpacing(10)

        theme = ThemeManager.current_theme()

        # 公历日期
        self.solar_label = create_label("", font_size=FontSize.CALENDAR_LARGE, bold=True)
        self.solar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_layout.addWidget(self.solar_label)

        # 农历日期
        self.lunar_date_label = create_label("", font_size=FontSize.CALENDAR_DETAIL)
        self.lunar_date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lunar_date_label.setStyleSheet(f"color: {theme.danger}; background: transparent;")
        detail_layout.addWidget(self.lunar_date_label)

        # 干支
        self.ganzhi_label = create_label("", font_size=FontSize.CALENDAR_NORMAL)
        self.ganzhi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ganzhi_label.setStyleSheet(f"color: {theme.text_primary}; background: transparent;")
        detail_layout.addWidget(self.ganzhi_label)

        # 分隔线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        detail_layout.addWidget(sep1)

        # 宜
        self.yi_label = create_label("", font_size=FontSize.CALENDAR_NORMAL)
        self.yi_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.yi_label.setWordWrap(True)
        self._style_yi_label()
        detail_layout.addWidget(self.yi_label)

        # 忌
        self.ji_label = create_label("", font_size=FontSize.CALENDAR_NORMAL)
        self.ji_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.ji_label.setWordWrap(True)
        self._style_ji_label()
        detail_layout.addWidget(self.ji_label)

        # 分隔线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        detail_layout.addWidget(sep2)

        # 额外信息
        self.extra_info_label = create_label("", font_size=FontSize.CALENDAR_SMALL)
        self.extra_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.extra_info_label.setStyleSheet(
            f"color: {theme.text_secondary}; background: transparent;"
        )
        self.extra_info_label.setWordWrap(True)
        detail_layout.addWidget(self.extra_info_label)

        # 工作状态
        self.work_status_label = create_label("", font_size=FontSize.CALENDAR_NORMAL, bold=True)
        self.work_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.work_status_label.setStyleSheet(
            f"background-color: {theme.primary_bg}; color: {theme.primary}; "
            f"padding: 8px; border-radius: 5px; margin-top: 5px;"
        )
        detail_layout.addWidget(self.work_status_label)

        scroll_area.setWidget(self.detail_frame)
        main_layout.addWidget(scroll_area)
        main_layout.addSpacing(10)

        # 图例
        legend_layout = self._create_legend()
        main_layout.addLayout(legend_layout)

        # 连接事件
        self.calendar.selectionChanged.connect(self.on_date_selected)
        self.mark_execution_dates()
        self.on_date_selected()

    def _style_yi_label(self) -> None:
        """设置宜标签样式"""
        theme = ThemeManager.current_theme()
        if self.yi_label:
            self.yi_label.setStyleSheet(
                f"color: {theme.success}; margin-top: 3px; "
                f"padding: 5px; background-color: {theme.success_bg}; "
                f"border-radius: 3px;"
            )

    def _style_ji_label(self) -> None:
        """设置忌标签样式"""
        theme = ThemeManager.current_theme()
        if self.ji_label:
            self.ji_label.setStyleSheet(
                f"color: {theme.danger}; margin-top: 3px; "
                f"padding: 5px; background-color: {theme.danger_bg}; "
                f"border-radius: 3px;"
            )

    def _create_legend(self) -> QHBoxLayout:
        """创建图例"""
        theme = ThemeManager.current_theme()
        legend_layout = QHBoxLayout()
        legend_layout.addStretch()

        # 需要执行任务
        exec_legend = self._create_legend_item(theme.success, "需要执行任务")
        legend_layout.addWidget(exec_legend)
        legend_layout.addSpacing(20)

        # 不执行任务
        no_exec_legend = self._create_legend_item(theme.danger, "不执行任务")
        legend_layout.addWidget(no_exec_legend)
        legend_layout.addSpacing(20)

        # 调休上班
        compensatory_legend = self._create_legend_item(theme.warning, "调休上班")
        legend_layout.addWidget(compensatory_legend)
        legend_layout.addStretch()

        return legend_layout

    def _create_legend_item(self, color: str, text: str) -> QWidget:
        """创建单个图例项"""
        legend = QWidget()
        layout = QHBoxLayout(legend)

        color_label = QLabel()
        color_label.setFixedSize(16, 16)
        color_label.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

        text_label = create_label(text, font_size=FontSize.CALENDAR_NORMAL)

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

            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday_str = weekday_names[date.weekday()]

            if self.solar_label:
                self.solar_label.setText(f"{date.year}年{date.month}月{date.day}日 ({weekday_str})")

            should_work, status = self.should_work_on_date(date)

            if global_config.get("SHOW_LUNAR_CALENDAR", True):
                lunar_detail = self._get_lunar_detail(date)

                if self.lunar_date_label:
                    self.lunar_date_label.setText(lunar_detail.get("lunar_date", ""))
                if self.ganzhi_label:
                    self.ganzhi_label.setText(lunar_detail.get("ganzhi", ""))

                yi_list = lunar_detail.get("yi", [])
                ji_list = lunar_detail.get("ji", [])

                if self.yi_label:
                    if yi_list:
                        self.yi_label.setText(f"宜：{' '.join(yi_list)}")
                        self.yi_label.setVisible(True)
                    else:
                        self.yi_label.setVisible(False)

                if self.ji_label:
                    if ji_list:
                        self.ji_label.setText(f"忌：{' '.join(ji_list)}")
                        self.ji_label.setVisible(True)
                    else:
                        self.ji_label.setVisible(False)

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
                if self.lunar_date_label:
                    self.lunar_date_label.setVisible(False)
                if self.ganzhi_label:
                    self.ganzhi_label.setVisible(False)
                if self.yi_label:
                    self.yi_label.setVisible(False)
                if self.ji_label:
                    self.ji_label.setVisible(False)
                if self.extra_info_label:
                    self.extra_info_label.setVisible(False)

            if self.work_status_label:
                self.work_status_label.setText(status)
                self._style_work_status(status)

            debug("main", f"万年历日期选中：{date}")
        except Exception as e:
            error("main", "日期选择处理出错", exc_info=True)
            if self.solar_label:
                self.solar_label.setText(f"日期处理出错：{str(e)}")

    def _style_work_status(self, status: str) -> None:
        """设置工作状态样式"""
        theme = ThemeManager.current_theme()
        if self.work_status_label is None:
            return

        if "不执行" in status:
            self.work_status_label.setStyleSheet(
                f"background-color: {theme.danger_bg}; color: {theme.danger}; "
                f"padding: 8px; border-radius: 5px; margin-top: 5px;"
            )
        elif "调休" in status:
            self.work_status_label.setStyleSheet(
                f"background-color: {theme.warning_bg}; color: {theme.warning}; "
                f"padding: 8px; border-radius: 5px; margin-top: 5px;"
            )
        elif "需要执行" in status:
            self.work_status_label.setStyleSheet(
                f"background-color: {theme.success_bg}; color: {theme.success}; "
                f"padding: 8px; border-radius: 5px; margin-top: 5px;"
            )
        else:
            self.work_status_label.setStyleSheet(
                f"background-color: {theme.primary_bg}; color: {theme.primary}; "
                f"padding: 8px; border-radius: 5px; margin-top: 5px;"
            )

    def _get_lunar_detail(self, date: datetime.date) -> Dict[str, Any]:
        """获取完整万年历信息，使用缓存提高性能"""
        if date in self._lunar_cache:
            return self._lunar_cache[date]

        try:
            solar = Solar.fromYmd(date.year, date.month, date.day)
            lunar = solar.getLunar()

            lunar_month = lunar.getMonthInChinese()
            lunar_day = lunar.getDayInChinese()
            lunar_date_str = f"农历 {lunar_month}月{lunar_day}"

            year_ganzhi = lunar.getYearInGanZhi()
            month_ganzhi = lunar.getMonthInGanZhi()
            day_ganzhi = lunar.getDayInGanZhi()
            year_shengxiao = lunar.getYearShengXiao()
            ganzhi_str = f"{year_ganzhi}年 ({year_shengxiao}年) " f"{month_ganzhi}月 {day_ganzhi}日"

            yi_list = lunar.getDayYi()
            ji_list = lunar.getDayJi()
            jieqi = lunar.getJieQi()

            festivals: Dict[str, List[str]] = {"traditional": [], "solar": []}
            lunar_festivals = lunar.getFestivals()
            if lunar_festivals:
                festivals["traditional"].extend(lunar_festivals)
            solar_festivals = solar.getFestivals()
            if solar_festivals:
                festivals["solar"].extend(solar_festivals)

            other_info_parts = []
            lunar_year_str = lunar.getYearInChinese()
            other_info_parts.append(f"农历{lunar_year_str}年")
            other_info = " | ".join(other_info_parts)

            result = {
                "lunar_date": lunar_date_str,
                "ganzhi": ganzhi_str,
                "yi": yi_list,
                "ji": ji_list,
                "jieqi": jieqi if jieqi else "",
                "festivals": festivals,
                "other_info": other_info,
            }

            self._lunar_cache[date] = result
            return result
        except Exception as e:
            warning("main", f"农历转换失败：{e}")
            return {
                "lunar_date": "（农历转换失败）",
                "ganzhi": "",
                "yi": [],
                "ji": [],
                "jieqi": "",
                "festivals": {"traditional": [], "solar": []},
                "other_info": "",
            }

    def should_work_on_date(self, date: datetime.date) -> tuple:
        """判断指定日期是否需要执行任务"""
        try:
            result = should_work_today(date)
            debug(
                "main",
                f"检查日期 {date} 是否需要执行任务: {'是' if result else '否'}",
            )

            status = "不执行任务"
            if result:
                status = "需要执行任务"

            compensatory_days = [
                parse_date_str(d)
                for d in global_config.get("COMPENSATORY_WORKDAYS", [])
                if parse_date_str(d)
            ]
            if date in compensatory_days:
                status = "调休上班日 - 需要执行任务"
            else:
                base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
                for period in base_holiday_periods:
                    if is_date_in_period(date, period):
                        if not result:
                            status = f"节假日({period.get('name')}) - 不执行任务"
                        break

            date_rules = global_config.get("DATE_RULES", {})
            if date_rules.get("ENABLE_CUSTOM_RULE", False):
                custom_work_periods = date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
                for period in custom_work_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义工作日({period.get('name')}) - 需要执行任务"
                        break

                custom_holiday_periods = date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
                for period in custom_holiday_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义假期({period.get('name')}) - 不执行任务"
                        break

            return (result, status)
        except Exception as e:
            error(
                "main",
                f"判断日期 {date} 是否需要执行任务时出错",
                exc_info=True,
            )
            return (False, f"错误：{str(e)}")

    def mark_execution_dates(self) -> None:
        """标记日历中需要执行任务的日期"""
        try:
            if self.calendar is None:
                return

            current_date = self.calendar.selectedDate()
            current_year = current_date.year()
            current_month = current_date.month()

            debug("main", f"开始标记 {current_year}年{current_month}月 的执行日期")

            first_day = datetime.date(current_year, current_month, 1)
            if current_month == 12:
                last_day = datetime.date(current_year, current_month, 31)
            else:
                last_day = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(
                    days=1
                )

            current_date = first_day
            day_count = 0
            while current_date <= last_day:
                try:
                    should_work, status = self.should_work_on_date(current_date)
                    qt_date = QDate(current_date.year, current_date.month, current_date.day)

                    if should_work:
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(76, 175, 80, 100))
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)
                    else:
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(244, 67, 54, 100))
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)

                    day_count += 1
                except Exception as e:
                    warning("main", f"标记日期 {current_date} 时出错: {e}")

                current_date += datetime.timedelta(days=1)

            debug(
                "main",
                f"完成标记 {current_year}年{current_month}月 的执行日期，共标记 {day_count} 天",
            )
        except Exception as e:
            error("main", "标记执行日期时出错", exc_info=True)
            QMessageBox.warning(self, "错误", f"标记日历日期时出错: {str(e)}")

    def showEvent(self, event) -> None:
        """窗口显示时重新标记日期"""
        super().showEvent(event)
        self.mark_execution_dates()
