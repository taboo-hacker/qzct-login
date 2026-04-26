"""
时间段编辑对话框模块
使用组件工厂重构的编辑对话框
"""
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QFrame,
    QDateEdit, QHBoxLayout, QPushButton, QMessageBox,
)
from PyQt5.QtCore import QDate

from infrastructure import parse_date_str
from gui.style_helpers import create_button, create_label, create_card_widget
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle, StyleConstants


class PeriodEditDialog(QDialog):
    """编辑时间段对话框"""

    def __init__(
        self,
        parent: Optional[QDialog] = None,
        period: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        is_edit = period is not None
        self.setWindowTitle("编辑时间段" if is_edit else "添加时间段")
        self.setFixedSize(420, 280)

        self.period = period if period else {"name": "", "start": "", "end": ""}
        self.result_period: Optional[dict] = None

        # 控件引用
        self.name_edit: Optional[QLineEdit] = None
        self.start_edit: Optional[QDateEdit] = None
        self.end_edit: Optional[QDateEdit] = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部标题区域
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(25, 20, 25, 15)
        title_label = create_label(
            "\U0001F4C5 " + ("编辑时间段" if is_edit else "添加时间段"),
            font_size=FontSize.DIALOG_TITLE,
            bold=True,
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)

        header_frame = QFrame()
        header_frame.setLayout(header_layout)
        header_frame.setObjectName("headerFrame")
        header_frame.setMinimumHeight(70)
        main_layout.addWidget(header_frame)

        # 表单区域
        form_frame = create_card_widget()
        form_frame.setObjectName("formFrame")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(24, 20, 24, 20)

        self.name_edit = QLineEdit()
        self.name_edit.setText(self.period.get("name", ""))
        self.name_edit.setPlaceholderText("请输入时间段名称（如：2025校运会）")
        form_layout.addRow(create_label("时间段名称："), self.name_edit)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        if self.period.get("start"):
            start_date = parse_date_str(self.period["start"])
            if start_date:
                self.start_edit.setDate(
                    QDate(start_date.year, start_date.month, start_date.day)
                )
        else:
            self.start_edit.setDate(QDate.currentDate())
        form_layout.addRow(create_label("开始日期："), self.start_edit)

        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        if self.period.get("end"):
            end_date = parse_date_str(self.period["end"])
            if end_date:
                self.end_edit.setDate(
                    QDate(end_date.year, end_date.month, end_date.day)
                )
        else:
            self.end_edit.setDate(QDate.currentDate())
        form_layout.addRow(create_label("结束日期："), self.end_edit)

        main_layout.addWidget(form_frame)
        main_layout.addSpacing(10)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        save_btn = create_button(
            "\U0001F4BE 保存", btn_type="success", min_width=100, font_size=11
        )
        save_btn.clicked.connect(self.save)
        btn_layout.addWidget(save_btn)

        cancel_btn = create_button(
            "\u274C 取消", btn_type="gray", min_width=100, font_size=11
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addSpacing(20)
        main_layout.addLayout(btn_layout)
        main_layout.addSpacing(15)

        self._apply_styles()

    def _apply_styles(self) -> None:
        """应用 QSS 样式"""
        qss = StyleManager.get_global_stylesheet()
        dialog_qss = StyleManager.get_dialog_stylesheet()
        self.setStyleSheet(qss + dialog_qss)

    def save(self) -> None:
        """保存时间段"""
        if self.name_edit is None:
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入时间段名称")
            return

        if self.start_edit is None or self.end_edit is None:
            return

        start_date = self.start_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_edit.date().toString("yyyy-MM-dd")

        start = parse_date_str(start_date)
        end = parse_date_str(end_date)
        if start > end:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return

        self.result_period = {
            "name": name,
            "start": start_date,
            "end": end_date,
        }
        self.accept()
