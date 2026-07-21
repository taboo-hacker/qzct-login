"""
加密 GUI 交互模块

将原 core/encryption.py 中的 GUI 弹窗逻辑上移到此模块，
使 core 层不再在模块加载时硬耦合 PyQt5。

本模块由 core/encryption.py 通过延迟导入调用。
"""

from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from infra.logging import info


def _ensure_qapp() -> QApplication:
    """确保 QApplication 实例存在"""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app  # type: ignore[return-value]


def prompt_for_master_password() -> str:
    """
    提示用户输入主密码

    Returns:
        str: 主密码
    """
    _ensure_qapp()

    while True:
        password, ok = QInputDialog.getText(
            None,
            "设置主密码",
            "请设置加密主密码（用于保护您的敏感信息）：",
            echo=QLineEdit.Password,
        )

        if not ok:
            info("system_core", "用户取消设置主密码，程序终止")
            raise SystemExit("用户取消设置主密码，无法继续运行")

        if not password:
            QMessageBox.warning(None, "提示", "主密码不能为空，请重新输入：")
            continue

        confirm_password, ok = QInputDialog.getText(
            None, "确认主密码", "请再次输入主密码以确认：", echo=QLineEdit.Password
        )

        if not ok:
            info("system_core", "用户取消确认主密码，程序终止")
            raise SystemExit("用户取消确认主密码，无法继续运行")

        if password != confirm_password:
            QMessageBox.warning(None, "提示", "两次输入的密码不一致，请重新输入：")
            continue

        info("system_core", "主密码设置成功")
        return password


def confirm_reset_master_password(error_msg: str) -> bool:
    """
    确认是否重置主密码（解密失败时调用）

    Args:
        error_msg: 解密失败的错误消息

    Returns:
        True 表示用户确认重置，False 表示取消
    """
    _ensure_qapp()
    reply = QMessageBox.question(
        None,
        "解密失败",
        "主密码解密失败，是否重置主密码？\n\n注意：重置后所有已加密信息将无法恢复。",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    return reply == QMessageBox.Yes  # type: ignore[no-any-return]
