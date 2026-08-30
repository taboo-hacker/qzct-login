"""
基础节假日组件模块

设置页"节假日"标签页的主体：以表格形式编辑 HOLIDAY_PERIODS 配置
（国务院法定假日 + 学校寒暑假），基于 BaseListEditorWidget 骨架实现。
数据在点击"保存配置"时经 save_holidays() 返回给 SettingsPanel，
与其余字段统一收集、校验后一次性写入（保存事务性）。
"""

import copy
from typing import Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import DEFAULT_CONFIG, global_config
from gui.styling.widgets import create_button, create_card_widget
from gui.widgets.base_list_editor import BaseListEditorWidget


class BaseHolidayWidget(BaseListEditorWidget):
    """基础节假日编辑组件（表格 + 顶部内联添加表单 + 弹窗编辑）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        # 深拷贝配置数据：面板上的编辑是"草稿"，点保存才写回 global_config
        self.holiday_periods: list[dict[str, Any]] = copy.deepcopy(
            global_config.get("HOLIDAY_PERIODS", DEFAULT_CONFIG["HOLIDAY_PERIODS"])
        )
        self.name_edit: QLineEdit | None = None
        self.start_edit: QDateEdit | None = None
        self.end_edit: QDateEdit | None = None

        super().__init__(
            parent=parent,
            title="\U0001f389 基础节假日列表",
            tip="管理国务院发布的法定节假日，节假日期间不执行联网和关机任务",
            columns=["名称", "开始日期", "结束日期"],
        )

    def _setup_edit_area(self, layout: QVBoxLayout) -> None:
        """覆盖基类：在表格上方添加"名称+起止日期"的内联添加表单。"""
        edit_frame = create_card_widget()
        edit_frame.setObjectName("holidayEditFrame")
        edit_layout = QHBoxLayout(edit_frame)
        edit_layout.setSpacing(10)
        edit_layout.setContentsMargins(15, 10, 15, 10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("节假日名称")
        self.name_edit.setFixedWidth(150)
        edit_layout.addWidget(QLabel("名称："))
        edit_layout.addWidget(self.name_edit)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_edit.setDate(QDate.currentDate())
        edit_layout.addWidget(QLabel("开始："))
        edit_layout.addWidget(self.start_edit)

        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_edit.setDate(QDate.currentDate())
        edit_layout.addWidget(QLabel("结束："))
        edit_layout.addWidget(self.end_edit)

        add_btn = create_button("\u2795 添加", btn_type="success", min_width=80)
        add_btn.clicked.connect(self.add_item)
        edit_layout.addWidget(add_btn)

        layout.addWidget(edit_frame)

    # ------------------------------------------------------------------
    # 数据操作钩子
    # ------------------------------------------------------------------

    def _get_items(self) -> list[dict[str, Any]]:
        """数据源：组件持有的节假日区间草稿列表。"""
        return self.holiday_periods

    def _set_items(self, items: list[dict[str, Any]]) -> None:
        """整体写回草稿列表。"""
        self.holiday_periods = items

    def _row_to_cells(self, item: dict[str, Any]) -> list[QTableWidgetItem]:
        """渲染一行：名称 / 开始日期 / 结束日期。"""
        return [
            QTableWidgetItem(item.get("name", "")),
            QTableWidgetItem(item.get("start", "")),
            QTableWidgetItem(item.get("end", "")),
        ]

    def _add_item(self) -> None:
        """从内联表单读取并校验后追加一条（名称必填，起止日期合法）。"""
        if self.name_edit is None or self.start_edit is None or self.end_edit is None:
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入节假日名称")
            return

        start_date = self.start_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_edit.date().toString("yyyy-MM-dd")

        from infra.date_utils import parse_date_str

        start = parse_date_str(start_date)
        end = parse_date_str(end_date)
        if start is not None and end is not None and start > end:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return

        self.holiday_periods.append({"name": name, "start": start_date, "end": end_date})
        self.name_edit.clear()

    def _edit_item(self, row: int) -> None:
        """弹窗编辑指定行的区间（PeriodEditDialog，确认后写回）。"""
        if row < 0 or row >= len(self.holiday_periods):
            return
        period = self.holiday_periods[row]
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog(
            self,
            period={
                "name": period.get("name", ""),
                "start": period.get("start", ""),
                "end": period.get("end", ""),
            },
        )
        if dialog.exec() and dialog.result_period:
            self.holiday_periods[row] = {
                "name": dialog.result_period["name"],
                "start": dialog.result_period["start"],
                "end": dialog.result_period["end"],
            }

    def _sort_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按开始日期升序排序。"""
        return sorted(items, key=lambda x: x["start"])

    def _get_select_warning_text(self) -> str:
        return "请先选择要编辑的节假日"

    def _get_clear_confirm_text(self) -> str:
        return "确定要清空所有节假日吗？"

    def save_holidays(self) -> list[dict[str, Any]]:
        """返回待保存的节假日区间列表。

        不直接写 global_config：由 SettingsPanel.save_config 收集进 pending，
        全部验证通过后统一写入并落盘，保证保存的事务性。
        """
        return self.holiday_periods
