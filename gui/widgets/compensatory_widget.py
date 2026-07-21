"""
调休上班日组件模块
使用主题系统重构的调休上班日编辑组件
"""


from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import DEFAULT_CONFIG, global_config
from gui.styling.constants import FontStyle
from gui.styling.theme_manager import ThemeManager
from gui.styling.widgets import create_button, create_label
from gui.widgets.base_list_editor import BaseListEditorWidget
from infra.date_utils import parse_date_str


class CompensatoryWorkdayWidget(BaseListEditorWidget):
    """调休上班日组件"""

    def __init__(self, parent: QWidget | None = None) -> None:
        raw_days: list[str] = global_config.get(
            "COMPENSATORY_WORKDAYS", DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"]
        )
        self.compensatory_days: list[dict[str, str]] = [{"name": d, "date": d} for d in raw_days]

        super().__init__(
            parent=parent,
            title="\U0001f4c5 调休上班日列表",
            tip="添加国务院发布的调休补班日期，这些日期即使在节假日期间也需要执行任务",
            columns=["名称", "日期"],
        )

    # ------------------------------------------------------------------
    # 数据操作钩子
    # ------------------------------------------------------------------

    def _get_items(self) -> list[dict[str, str]]:
        return self.compensatory_days

    def _set_items(self, items: list[dict[str, str]]) -> None:
        self.compensatory_days = items

    def _row_to_cells(self, item: dict[str, str]) -> list[QTableWidgetItem]:
        return [
            QTableWidgetItem(item.get("name", item.get("date", ""))),
            QTableWidgetItem(item.get("date", "")),
        ]

    def _add_item(self) -> None:
        dialog = AddDateDialog(self)
        if dialog.exec() and dialog.selected_date:
            date_str = dialog.selected_date.toString("yyyy-MM-dd")
            self.compensatory_days.append({"name": date_str, "date": date_str})

    def _edit_item(self, row: int) -> None:
        old_date_str = self.compensatory_days[row].get("date", "")
        dialog = AddDateDialog(self, old_date_str)
        if dialog.exec() and dialog.selected_date:
            new_date_str = dialog.selected_date.toString("yyyy-MM-dd")
            self.compensatory_days[row] = {"name": new_date_str, "date": new_date_str}

    def _sort_items(self, items: list[dict[str, str]]) -> list[dict[str, str]]:
        return sorted(items, key=lambda x: x["date"])

    def _get_select_warning_text(self) -> str:
        return "请先选择要编辑的日期"

    def _get_clear_confirm_text(self) -> str:
        return "确定要清空所有调休上班日吗？"

    def save_days(self) -> None:
        """保存调休上班日到配置"""
        global_config["COMPENSATORY_WORKDAYS"] = [d["date"] for d in self.compensatory_days]


class AddDateDialog(QDialog):
    """日期选择对话框"""

    def __init__(self, parent: QWidget | None = None, current_date: str = "") -> None:
        super().__init__(parent)
        self.selected_date: QDate | None = None
        self.setWindowTitle("选择日期")
        self.setMinimumWidth(300)
        self._init_ui(current_date)

    def _init_ui(self, current_date: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)

        title = create_label(
            "选择日期", font_size=14, bold=True, color=ThemeManager.current_theme().primary
        )
        layout.addWidget(title)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(38)
        self.date_edit.setFont(FontStyle.normal(13))

        if current_date:
            dt = parse_date_str(current_date)
            if dt:
                self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
        else:
            self.date_edit.setDate(QDate.currentDate())

        layout.addWidget(self.date_edit)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        ok_btn = create_button("确定", btn_type="success", min_width=80)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = create_button("取消", btn_type="gray", min_width=80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
