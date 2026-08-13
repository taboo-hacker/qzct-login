"""
设置对话框模块

SettingsDialog 为 SettingsPanel 的对话框包装（兼容旧调用方与测试），
主窗口内已改用嵌入式"设置"标签页，不再弹窗。
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from gui.dialogs.settings_panel import SettingsPanel


class SettingsDialog(QDialog):
    """配置设置对话框（包装 SettingsPanel，属性转发以兼容旧调用方）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setMinimumSize(820, 620)

        self._panel = SettingsPanel(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._panel)

        # 属性转发：兼容旧调用方与测试
        self.tab_widget = self._panel.tab_widget
        self.theme_combo = self._panel.theme_combo

    def _get_theme_display_name(self, theme_name: str) -> str:
        """获取主题显示名称（转发到面板）"""
        return self._panel._get_theme_display_name(theme_name)

    def toggle_password_visibility(self, password_edit: object, button: object) -> None:
        """切换密码可见性（转发到面板）"""
        self._panel.toggle_password_visibility(password_edit, button)  # type: ignore[arg-type]

    def _on_theme_changed(self, index: int) -> None:
        """主题切换处理（转发到面板）"""
        self._panel._on_theme_changed(index)
