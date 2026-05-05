"""
日期规则组件模块
使用主题系统和组件工厂重构的日期规则编辑组件
"""

from typing import Any, Dict, Optional

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui.dialogs.period_edit_dialog import PeriodEditDialog
from gui.style_helpers import (
    create_button,
    create_card_widget,
    create_section_title,
)
from gui.style_manager import StyleManager
from system_core import DEFAULT_CONFIG, WEEKDAY_MAPPING, global_config


class DateRuleWidget(QWidget):
    """日期规则组件"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.date_rules: Dict[str, Any] = global_config.get("DATE_RULES", {})
        self.date_rules = dict(self.date_rules)

        # 确保子键存在
        for key in ("CUSTOM_HOLIDAY_PERIODS", "CUSTOM_WORKDAY_PERIODS", "WEEKLY_EXECUTE_DAYS"):
            if key not in self.date_rules:
                self.date_rules[key] = DEFAULT_CONFIG["DATE_RULES"].get(key, [])

        # 组件引用
        self.enable_checkbox: Optional[QCheckBox] = None
        self.table: Optional[QTableWidget] = None
        self.type_combo: Optional[QComboBox] = None
        self.weekday_checkboxes: Dict[int, QCheckBox] = {}

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

        # 启用/禁用复选框
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("启用自定义日期规则")
        self.enable_checkbox.setChecked(self.date_rules.get("ENABLE_CUSTOM_RULE", False))
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addStretch()
        main_layout.addLayout(enable_layout)

        # 每周执行日选择
        weekday_title = create_section_title("\U0001f4c6 每周执行日")
        main_layout.addWidget(weekday_title)

        weekday_layout = QHBoxLayout()
        weekday_layout.setSpacing(10)
        weekday_execute_days = self.date_rules.get("WEEKLY_EXECUTE_DAYS", [0, 1, 2, 3, 4])
        for day_idx in range(7):
            cb = QCheckBox(WEEKDAY_MAPPING[day_idx])
            cb.setChecked(day_idx in weekday_execute_days)
            self.weekday_checkboxes[day_idx] = cb
            weekday_layout.addWidget(cb)
        weekday_layout.addStretch()
        main_layout.addLayout(weekday_layout)

        # 表格标题
        title = create_section_title("\U0001f4c5 自定义日期规则列表")
        main_layout.addWidget(title)

        # 编辑区域
        edit_frame = create_card_widget()
        edit_frame.setObjectName("dateRuleEditFrame")
        edit_layout = QHBoxLayout(edit_frame)
        edit_layout.setSpacing(10)
        edit_layout.setContentsMargins(15, 10, 15, 10)

        self.type_combo = QComboBox()
        self.type_combo.addItem("工作日（强制执行）", "workday")
        self.type_combo.addItem("假期（强制跳过）", "holiday")
        edit_layout.addWidget(QLabel("类型："))
        edit_layout.addWidget(self.type_combo)

        add_btn = create_button("\u2795 添加规则", btn_type="success", min_width=100)
        add_btn.clicked.connect(self.add_rule)
        edit_layout.addWidget(add_btn)

        main_layout.addWidget(edit_frame)

        # 表格区域
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["名称", "开始日期", "结束日期", "类型"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        edit_btn = create_button("\u270f\ufe0f 编辑规则", btn_type="primary", min_width=100)
        edit_btn.clicked.connect(self.edit_rule)
        btn_layout.addWidget(edit_btn)

        delete_btn = create_button("\u274c 删除规则", btn_type="danger", min_width=100)
        delete_btn.clicked.connect(self.delete_rule)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        clear_btn = create_button("\U0001f5d1\ufe0f 清空所有", btn_type="gray", min_width=100)
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        main_layout.addLayout(btn_layout)

        # 加载规则
        self.load_rules()

    def update_theme(self) -> None:
        """更新主题样式"""
        self._apply_styles()

    def load_rules(self) -> None:
        """加载规则到表格"""
        if self.table is None:
            return

        self.table.setRowCount(0)
        row = 0

        # 加载自定义工作日规则
        for rule in self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(rule.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.get("start", "")))
            self.table.setItem(row, 2, QTableWidgetItem(rule.get("end", "")))
            self.table.setItem(row, 3, QTableWidgetItem("工作日"))
            row += 1

        # 加载自定义假期规则
        for rule in self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(rule.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.get("start", "")))
            self.table.setItem(row, 2, QTableWidgetItem(rule.get("end", "")))
            self.table.setItem(row, 3, QTableWidgetItem("假期"))
            row += 1

    def add_rule(self) -> None:
        """添加规则"""
        dialog = PeriodEditDialog(self)
        if dialog.exec() and dialog.result_period:
            rule_type = self.type_combo.currentData()  # "workday" or "holiday"
            new_rule = dict(dialog.result_period)
            new_rule["type"] = rule_type

            if rule_type == "workday":
                rules = self.date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
                rules.append(new_rule)
                self.date_rules["CUSTOM_WORKDAY_PERIODS"] = rules
            else:
                rules = self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
                rules.append(new_rule)
                self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = rules

            self.load_rules()

    def edit_rule(self) -> None:
        """编辑规则"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的规则")
            return

        row_idx = selected_rows[0].row()

        # 找出该行对应的规则
        workday_rules = self.date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
        holiday_rules = self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])

        if row_idx < len(workday_rules):
            rule = workday_rules[row_idx]
            rule_type = "workday"
        else:
            rule_idx = row_idx - len(workday_rules)
            if rule_idx < len(holiday_rules):
                rule = holiday_rules[rule_idx]
                rule_type = "holiday"
            else:
                QMessageBox.warning(self, "提示", "规则索引无效")
                return

        dialog = PeriodEditDialog(
            self,
            period={
                "name": rule.get("name", ""),
                "start": rule.get("start", ""),
                "end": rule.get("end", ""),
            },
        )
        if dialog.exec() and dialog.result_period:
            updated_rule = dict(dialog.result_period)
            updated_rule["type"] = rule_type

            if rule_type == "workday":
                workday_rules[row_idx] = updated_rule
                self.date_rules["CUSTOM_WORKDAY_PERIODS"] = workday_rules
            else:
                rule_idx = row_idx - len(workday_rules)
                holiday_rules[rule_idx] = updated_rule
                self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = holiday_rules

            self.load_rules()

    def delete_rule(self) -> None:
        """删除规则"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的规则")
            return

        row_idx = selected_rows[0].row()
        workday_rules = self.date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
        holiday_rules = self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])

        if row_idx < len(workday_rules):
            workday_rules.pop(row_idx)
            self.date_rules["CUSTOM_WORKDAY_PERIODS"] = workday_rules
        else:
            rule_idx = row_idx - len(workday_rules)
            if rule_idx < len(holiday_rules):
                holiday_rules.pop(rule_idx)
                self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = holiday_rules

        self.load_rules()

    def clear_all(self) -> None:
        """清空所有规则"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空所有自定义日期规则吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.date_rules["CUSTOM_WORKDAY_PERIODS"] = []
            self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = []
            self.load_rules()

    def save_rules(self) -> None:
        """保存规则到配置"""
        self.date_rules["ENABLE_CUSTOM_RULE"] = self.enable_checkbox.isChecked()

        # 保存每周执行日
        weekday_days = [
            day_idx for day_idx, cb in self.weekday_checkboxes.items() if cb.isChecked()
        ]
        self.date_rules["WEEKLY_EXECUTE_DAYS"] = weekday_days

        # 清理规则中的 type 标记（type 仅用于内部区分，不写入配置）
        for rule in self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []):
            rule.pop("type", None)
        for rule in self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []):
            rule.pop("type", None)
