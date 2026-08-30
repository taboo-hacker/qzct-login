"""
调休上班日组件模块

设置页"调休上班"标签页的主体：编辑 COMPENSATORY_WORKDAYS 配置
（周末补班日期，判定优先级高于节假日），基于 BaseListEditorWidget 骨架。
日期的添加/编辑统一走 AddDateDialog 日历选择弹窗。
"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
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
    """调休上班日编辑组件（表格 + 日历弹窗增改）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        # 配置存储为日期字符串列表，组件内部转成 {name, date} 字典行
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
        """数据源：组件持有的调休日字典行列表。"""
        return self.compensatory_days

    def _set_items(self, items: list[dict[str, str]]) -> None:
        """整体写回字典行列表。"""
        self.compensatory_days = items

    def _row_to_cells(self, item: dict[str, str]) -> list[QTableWidgetItem]:
        """渲染一行：名称（缺省同日期） / 日期。"""
        return [
            QTableWidgetItem(item.get("name", item.get("date", ""))),
            QTableWidgetItem(item.get("date", "")),
        ]

    def _add_item(self) -> None:
        """弹窗选择日期后追加（名称即日期本身）。"""
        dialog = AddDateDialog(self)
        if dialog.exec() and dialog.selected_date:
            date_str = dialog.selected_date.toString("yyyy-MM-dd")
            self.compensatory_days.append({"name": date_str, "date": date_str})

    def _edit_item(self, row: int) -> None:
        """弹窗重新选择日期，替换指定行（越界保护与其他子类一致）。"""
        if not 0 <= row < len(self.compensatory_days):
            return
        old_date_str = self.compensatory_days[row].get("date", "")
        dialog = AddDateDialog(self, old_date_str)
        if dialog.exec() and dialog.selected_date:
            new_date_str = dialog.selected_date.toString("yyyy-MM-dd")
            self.compensatory_days[row] = {"name": new_date_str, "date": new_date_str}

    def _sort_items(self, items: list[dict[str, str]]) -> list[dict[str, str]]:
        """按日期升序排序。"""
        return sorted(items, key=lambda x: x["date"])

    def _get_select_warning_text(self) -> str:
        return "请先选择要编辑的日期"

    def _get_clear_confirm_text(self) -> str:
        return "确定要清空所有调休上班日吗？"

    def save_days(self) -> None:
        """保存调休上班日到配置（还原为纯日期字符串列表）。"""
        global_config["COMPENSATORY_WORKDAYS"] = [d["date"] for d in self.compensatory_days]


class AddDateDialog(QDialog):
    """日期选择对话框（QDateEdit + 日历弹出面板，确定/取消）。"""

    def __init__(self, parent: QWidget | None = None, current_date: str = "") -> None:
        super().__init__(parent)
        # 用户确认选择后非 None；取消则为 None（调用方以是否 exec+非空判断）
        self.selected_date: QDate | None = None
        self.setWindowTitle("选择日期")
        self.setMinimumWidth(300)
        self._init_ui(current_date)

    def _init_ui(self, current_date: str) -> None:
        """构建界面；current_date 非空时作为初始选中值（编辑场景）。"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)

        title = create_label(
            "选择日期", font_size=14, bold=True, color=ThemeManager.current_theme().primary
        )
        layout.addWidget(title)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        # 显示格式固定为 ISO 风格，不随系统 locale 变化（与配置存储格式一致）
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
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
