"""
日期规则组件模块

设置页"日期规则"标签页的主体：编辑 DATE_RULES 配置，包含三部分：
    1. "启用自定义日期规则"总开关（启用后完全按用户规则判定，优先级最高）
    2. 每周执行日复选（周一~周日）
    3. 自定义区间规则表（工作日=强制执行 / 假期=强制跳过）
基于 BaseListEditorWidget 骨架；判定逻辑见 core/date_rules.py。
"""

from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import DEFAULT_CONFIG, WEEKDAY_MAPPING, global_config
from gui.styling.widgets import create_button, create_card_widget, create_section_title
from gui.widgets.base_list_editor import BaseListEditorWidget


class DateRuleWidget(BaseListEditorWidget):
    """自定义日期规则编辑组件（开关 + 每周执行日 + 区间规则表）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        self.date_rules: dict[str, Any] = dict(global_config.get("DATE_RULES", {}))

        # 兜底补齐子字段，避免旧配置缺键导致 KeyError
        for key in ("CUSTOM_HOLIDAY_PERIODS", "CUSTOM_WORKDAY_PERIODS", "WEEKLY_EXECUTE_DAYS"):
            if key not in self.date_rules:
                self.date_rules[key] = DEFAULT_CONFIG["DATE_RULES"].get(key, [])

        self.enable_checkbox: QCheckBox | None = None
        self.type_combo: QComboBox | None = None
        self.weekday_checkboxes: dict[int, QCheckBox] = {}

        super().__init__(
            parent=parent,
            title="\U0001f4c5 自定义日期规则列表",
            columns=["名称", "开始日期", "结束日期", "类型"],
        )

    def _setup_edit_area(self, layout: QVBoxLayout) -> None:
        """覆盖基类：总开关 + 每周执行日复选 + 带类型下拉的添加表单。"""
        # 启用/禁用复选框（不勾选时下面的规则不生效，走默认判定）
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox("启用自定义日期规则")
        self.enable_checkbox.setChecked(self.date_rules.get("ENABLE_CUSTOM_RULE", False))
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)

        # 每周执行日选择
        layout.addWidget(create_section_title("\U0001f4c6 每周执行日"))
        weekday_layout = QHBoxLayout()
        weekday_layout.setSpacing(10)
        weekday_execute_days = self.date_rules.get("WEEKLY_EXECUTE_DAYS", [0, 1, 2, 3, 4])
        for day_idx in range(7):
            cb = QCheckBox(WEEKDAY_MAPPING[day_idx])
            cb.setChecked(day_idx in weekday_execute_days)
            self.weekday_checkboxes[day_idx] = cb
            weekday_layout.addWidget(cb)
        weekday_layout.addStretch()
        layout.addLayout(weekday_layout)

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
        add_btn.clicked.connect(self.add_item)
        edit_layout.addWidget(add_btn)

        layout.addWidget(edit_frame)

    # ------------------------------------------------------------------
    # 数据操作钩子
    # ------------------------------------------------------------------

    def _get_items(self) -> list[dict[str, Any]]:
        """合并工作日和假期规则为统一列表。"""
        combined = []
        for rule in self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []):
            combined.append({**rule, "_type": "workday"})
        for rule in self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []):
            combined.append({**rule, "_type": "holiday"})
        return combined

    def _set_items(self, items: list[dict[str, Any]]) -> None:
        """按 _type 标记把合并列表拆回工作日/假期两个配置键。"""
        workday_rules = [
            {k: v for k, v in item.items() if k != "_type"}
            for item in items
            if item.get("_type") == "workday"
        ]
        holiday_rules = [
            {k: v for k, v in item.items() if k != "_type"}
            for item in items
            if item.get("_type") == "holiday"
        ]
        self.date_rules["CUSTOM_WORKDAY_PERIODS"] = workday_rules
        self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = holiday_rules

    def _row_to_cells(self, item: dict[str, Any]) -> list[QTableWidgetItem]:
        """渲染一行：名称 / 开始 / 结束 / 类型（工作日或假期）。"""
        type_label = "工作日" if item.get("_type") == "workday" else "假期"
        return [
            QTableWidgetItem(item.get("name", "")),
            QTableWidgetItem(item.get("start", "")),
            QTableWidgetItem(item.get("end", "")),
            QTableWidgetItem(type_label),
        ]

    def _add_item(self) -> None:
        """弹窗录入区间，按类型下拉分别追加到工作日/假期规则。"""
        # 函数内延迟导入：widgets 与 dialogs 互有引用（settings_panel 反向引 widgets），
        # 顶部导入会形成包级循环依赖，靠导入顺序侥幸成立（与 holiday_widget 一致）
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog(self)
        if dialog.exec() and dialog.result_period:
            rule_type = self.type_combo.currentData() if self.type_combo else "workday"
            new_rule = dict(dialog.result_period)
            new_rule["_type"] = rule_type

            if rule_type == "workday":
                self.date_rules.setdefault("CUSTOM_WORKDAY_PERIODS", []).append(new_rule)
            else:
                self.date_rules.setdefault("CUSTOM_HOLIDAY_PERIODS", []).append(new_rule)

    def _edit_item(self, row: int) -> None:
        """弹窗编辑指定行（类型保持不变，只改名称与起止日期）。"""
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        items = self._get_items()
        if row >= len(items):
            QMessageBox.warning(self, "提示", "规则索引无效")
            return

        rule = items[row]
        rule_type = rule.get("_type", "workday")

        dialog = PeriodEditDialog(
            self,
            period={
                "name": rule.get("name", ""),
                "start": rule.get("start", ""),
                "end": rule.get("end", ""),
            },
        )
        if dialog.exec() and dialog.result_period:
            updated = dict(dialog.result_period)
            updated["_type"] = rule_type
            items[row] = updated
            self._set_items(items)

    def _get_select_warning_text(self) -> str:
        return "请先选择要编辑的规则"

    def _get_clear_confirm_text(self) -> str:
        return "确定要清空所有自定义日期规则吗？"

    def save_rules(self) -> dict[str, Any]:
        """收集开关与每周执行日到 date_rules 并返回（剥离 _type 临时标记）。

        不直接写 global_config：由 SettingsPanel.save_config 收集进 pending，
        全部验证通过后统一写入并落盘，保证保存的事务性。
        """
        assert self.enable_checkbox is not None
        self.date_rules["ENABLE_CUSTOM_RULE"] = self.enable_checkbox.isChecked()
        weekday_days = [
            day_idx for day_idx, cb in self.weekday_checkboxes.items() if cb.isChecked()
        ]
        self.date_rules["WEEKLY_EXECUTE_DAYS"] = weekday_days
        for rule in self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []):
            rule.pop("_type", None)
        for rule in self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []):
            rule.pop("_type", None)
        return self.date_rules
