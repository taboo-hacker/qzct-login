"""
基础节假日组件模块
使用主题系统重构的节假日编辑组件
"""

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.style_helpers import (
    create_button,
    create_card_widget,
    create_section_title,
    create_tip_label,
)
from gui.style_manager import StyleManager
from system_core import DEFAULT_CONFIG, global_config


class BaseHolidayWidget(QWidget):
    """基础节假日组件"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.holiday_periods: List[Dict[str, Any]] = global_config.get(
            "HOLIDAY_PERIODS", DEFAULT_CONFIG["HOLIDAY_PERIODS"]
        )[:]

        # 组件引用
        self.table: Optional[QTableWidget] = None
        self.name_edit: Optional[QLineEdit] = None
        self.start_edit: Optional[QDateEdit] = None
        self.end_edit: Optional[QDateEdit] = None

        self.init_ui()
        self._apply_styles()

    def _apply_styles(self) -> None:
        """应用 QSS 样式"""
        self.setStyleSheet(StyleManager.get_global_stylesheet())

    def init_ui(self) -> None:
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 标题和提示
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)

        title = create_section_title("\U0001f389 基础节假日列表")
        header_layout.addWidget(title)

        tip_label = create_tip_label("管理国务院发布的法定节假日，节假日期间不执行联网和关机任务")
        header_layout.addWidget(tip_label)

        main_layout.addLayout(header_layout)

        # 编辑区域
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
        add_btn.clicked.connect(self.add_period)
        edit_layout.addWidget(add_btn)

        main_layout.addWidget(edit_frame)

        # 表格区域
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["名称", "开始日期", "结束日期"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        edit_btn = create_button("\u270f\ufe0f 编辑", btn_type="primary", min_width=100)
        edit_btn.clicked.connect(self.edit_period)
        btn_layout.addWidget(edit_btn)

        delete_btn = create_button("\u274c 删除", btn_type="danger", min_width=100)
        delete_btn.clicked.connect(self.delete_period)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        clear_btn = create_button("\U0001f5d1\ufe0f 清空所有", btn_type="gray", min_width=100)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        main_layout.addLayout(btn_layout)

        # 加载数据
        self.load_holidays()

    def update_theme(self) -> None:
        """更新主题样式"""
        self._apply_styles()

    def load_holidays(self) -> None:
        """加载节假日到表格"""
        if self.table is None:
            return

        self.table.setRowCount(0)
        for row, period in enumerate(self.holiday_periods):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(period.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(period.get("start", "")))
            self.table.setItem(row, 2, QTableWidgetItem(period.get("end", "")))

    def add_period(self) -> None:
        """添加节假日"""
        if self.name_edit is None or self.start_edit is None or self.end_edit is None:
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入节假日名称")
            return

        start_date = self.start_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_edit.date().toString("yyyy-MM-dd")

        from infrastructure import parse_date_str

        start = parse_date_str(start_date)
        end = parse_date_str(end_date)
        if start > end:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return

        new_period = {
            "name": name,
            "start": start_date,
            "end": end_date,
        }
        self.holiday_periods.append(new_period)
        self.holiday_periods.sort(key=lambda x: x["start"])
        self.load_holidays()

        # 清空输入
        self.name_edit.clear()

    def edit_period(self) -> None:
        """编辑节假日"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的节假日")
            return

        row = selected_rows[0].row()
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
            self.holiday_periods.sort(key=lambda x: x["start"])
            self.load_holidays()

    def delete_period(self) -> None:
        """删除节假日"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的节假日")
            return

        row = selected_rows[0].row()
        self.holiday_periods.pop(row)
        self.load_holidays()

    def clear_all(self) -> None:
        """清空所有节假日"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有节假日吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.holiday_periods.clear()
            self.load_holidays()

    def save_holidays(self) -> None:
        """保存节假日到配置"""
        global_config["HOLIDAY_PERIODS"] = self.holiday_periods
