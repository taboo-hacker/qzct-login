"""
更改主密码对话框模块
使用组件工厂重构的密码对话框
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from gui.style_helpers import create_button, create_card_widget, create_label
from gui.style_manager import StyleManager
from gui.styles import FontSize


class ChangeMasterPasswordDialog(QDialog):
    """更改主密码对话框"""

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("更改主密码")
        self.setFixedSize(450, 320)

        # 控件引用
        self.old_password_edit: Optional[QLineEdit] = None
        self.new_password_edit: Optional[QLineEdit] = None
        self.confirm_password_edit: Optional[QLineEdit] = None

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部标题区域
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(25, 20, 25, 15)
        title_label = create_label(
            "\U0001f510 更改加密主密码",
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

        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_password_edit.setPlaceholderText("请输入旧主密码")
        form_layout.addRow(create_label("旧主密码："), self.old_password_edit)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_edit.setPlaceholderText("请输入新主密码")
        form_layout.addRow(create_label("新主密码："), self.new_password_edit)

        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_edit.setPlaceholderText("请再次输入新主密码")
        form_layout.addRow(create_label("确认新密码："), self.confirm_password_edit)

        main_layout.addWidget(form_frame)
        main_layout.addSpacing(10)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        ok_btn = create_button("\U0001f4be 更改密码", btn_type="success", min_width=120)
        ok_btn.clicked.connect(self.change_password)
        btn_layout.addWidget(ok_btn)

        cancel_btn = create_button("\u274c 取消", btn_type="gray", min_width=100)
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

    def change_password(self) -> None:
        """更改主密码"""
        if (
            self.old_password_edit is None
            or self.new_password_edit is None
            or self.confirm_password_edit is None
        ):
            return

        old_password = self.old_password_edit.text()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()

        if not old_password:
            QMessageBox.warning(self, "提示", "请输入旧主密码")
            return

        if not new_password:
            QMessageBox.warning(self, "提示", "请输入新主密码")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return

        from system_core import change_master_password

        success = change_master_password(old_password, new_password)

        if success:
            QMessageBox.information(self, "成功", "主密码更改成功，配置已重新加密")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "主密码更改失败，请检查旧密码是否正确")
