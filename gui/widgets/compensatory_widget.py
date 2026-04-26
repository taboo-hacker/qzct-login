"""
调休上班日组件模块
使用主题系统重构的调休上班日编辑组件
"""
from typing import List, Optional, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QMessageBox, QAbstractItemView,
    QDateEdit, QDialog,
)
from PyQt5.QtCore import Qt, QDate

from system_core import global_config, DEFAULT_CONFIG
from infrastructure import parse_date_str
from gui.style_helpers import (
    create_button, create_label, create_section_title,
    create_tip_label,
)
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle


class CompensatoryWorkdayWidget(QWidget):
    """调休上班日组件"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # config.json 存储的是字符串列表，内部使用字典列表
        raw_days: List[str] = global_config.get(
            "COMPENSATORY_WORKDAYS", DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"]
        )
        self.compensatory_days: List[Dict[str, str]] = [
            {"name": d, "date": d} for d in raw_days
        ]

        # 组件引用
        self.table: Optional[QTableWidget] = None

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

        title = create_section_title("\U0001F4C5 调休上班日列表")
        header_layout.addWidget(title)

        tip_label = create_tip_label("添加国务院发布的调休补班日期，这些日期即使在节假日期间也需要执行任务")
        header_layout.addWidget(tip_label)

        main_layout.addLayout(header_layout)

        # 表格区域
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["名称", "日期"])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        add_btn = create_button(
            "\u2795 添加", btn_type="success", min_width=100
        )
        add_btn.clicked.connect(self.add_day)
        btn_layout.addWidget(add_btn)

        edit_btn = create_button(
            "\u270F\ufe0f 编辑", btn_type="primary", min_width=100
        )
        edit_btn.clicked.connect(self.edit_day)
        btn_layout.addWidget(edit_btn)

        delete_btn = create_button(
            "\u274C 删除", btn_type="danger", min_width=100
        )
        delete_btn.clicked.connect(self.delete_day)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        clear_btn = create_button(
            "\U0001F5D1\ufe0f 清空", btn_type="gray", min_width=100
        )
        clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_btn)

        main_layout.addLayout(btn_layout)

        # 加载数据
        self.load_days()

    def update_theme(self) -> None:
        """更新主题样式"""
        self._apply_styles()

    def load_days(self) -> None:
        """加载调休上班日到表格"""
        if self.table is None:
            return

        self.table.setRowCount(0)
        for row, day in enumerate(self.compensatory_days):
            self.table.insertRow(row)
            name = day.get("name", day.get("date", ""))
            date_str = day.get("date", "")
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

    def add_day(self) -> None:
        """添加调休上班日"""
        dialog = AddDateDialog(self)
        if dialog.exec() and dialog.selected_date:
            date_str = dialog.selected_date.toString("yyyy-MM-dd")
            new_day = {
                "name": date_str,
                "date": date_str,
            }
            self.compensatory_days.append(new_day)
            self.compensatory_days.sort(key=lambda x: x["date"])
            self.load_days()

    def edit_day(self) -> None:
        """编辑调休上班日"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的日期")
            return

        row = selected_rows[0].row()
        day = self.compensatory_days[row]
        old_date_str = day.get("date", "")

        dialog = AddDateDialog(self, old_date_str)
        if dialog.exec() and dialog.selected_date:
            new_date_str = dialog.selected_date.toString("yyyy-MM-dd")
            self.compensatory_days[row] = {
                "name": new_date_str,
                "date": new_date_str,
            }
            self.compensatory_days.sort(key=lambda x: x["date"])
            self.load_days()

    def delete_day(self) -> None:
        """删除调休上班日"""
        if self.table is None:
            return

        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的日期")
            return

        row = selected_rows[0].row()
        self.compensatory_days.pop(row)
        self.load_days()

    def clear_all(self) -> None:
        """清空所有调休上班日"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有调休上班日吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.compensatory_days.clear()
            self.load_days()

    def save_days(self) -> None:
        """保存调休上班日到配置"""
        global_config["COMPENSATORY_WORKDAYS"] = [
            d["date"] for d in self.compensatory_days
        ]


class AddDateDialog(QDialog):
    """日期选择对话框"""
    
    def __init__(self, parent=None, current_date: str = "") -> None:
        super().__init__(parent)
        self.selected_date: Optional[QDate] = None
        self.setWindowTitle("选择日期")
        self.setMinimumWidth(300)
        
        self._init_ui(current_date)
        self._apply_style()
        
    def _init_ui(self, current_date: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)
        
        title = create_label("选择日期", font_size=14, bold=True, color=ThemeManager.current_theme().primary)
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
    
    def _apply_style(self) -> None:
        self.setStyleSheet(StyleManager.get_global_stylesheet() + StyleManager.get_dialog_stylesheet())
