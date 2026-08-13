"""
关于对话框模块

紧凑版关于对话框：应用名、版本（可点击复制）、简介、链接与许可证，
视觉与主窗口全局 QSS 风格一致。
"""

from typing import cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.styling.widgets import create_button, create_label
from utils.version import get_project_version


class AboutDialog(QDialog):
    """关于对话框（简洁版）"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.version: str = get_project_version()
        self.version_btn: QPushButton | None = None
        self._restore_timer: QTimer | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        self.setWindowTitle("关于我们")
        self.setFixedWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # type: ignore[attr-defined]

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 16)
        v.setSpacing(8)

        # 应用名
        title = create_label("校园网自动登录", font_size=12, bold=True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)

        # 版本（点击复制）
        self.version_btn = create_button(f"版本 {self.version}", btn_type="text", min_height=24)
        self.version_btn.setToolTip("点击复制版本号")
        self.version_btn.clicked.connect(self._copy_version)
        version_row = QHBoxLayout()
        version_row.addStretch(1)
        version_row.addWidget(self.version_btn)
        version_row.addStretch(1)
        v.addLayout(version_row)

        # 简介
        desc = create_label(
            "专为衢州职业技术学院校园网设计的自动登录工具："
            "WiFi 自动连接、校园网认证、定时关机，并支持节假日智能判断。",
            word_wrap=True,
        )
        desc.setProperty("role", "muted")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(desc)

        v.addSpacing(4)

        # 分隔线
        from PySide6.QtWidgets import QFrame

        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        v.addWidget(line)

        # 链接与许可证
        link_label = QLabel('<a href="https://github.com/taboo-hacker/qzct-login">项目主页</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setCursor(Qt.CursorShape.PointingHandCursor)
        v.addWidget(link_label)

        license_label = create_label("许可证：CC BY-NC-SA 4.0")
        license_label.setProperty("role", "muted")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(license_label)

        copyright_label = create_label("© 2026 QZCT Developer", font_size=9)
        copyright_label.setProperty("role", "muted")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(copyright_label)

        v.addSpacing(6)

        # 关闭按钮
        ok_btn = create_button("关闭", btn_type="primary", min_width=110)
        ok_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        btn_row.addStretch(1)
        v.addLayout(btn_row)

    def _copy_version(self) -> None:
        """复制版本号到剪贴板"""
        if self.version_btn is None:
            return

        app = QApplication.instance()
        assert app is not None
        app_instance = cast(QApplication, app)
        clipboard = app_instance.clipboard()
        if clipboard:
            clipboard.setText(self.version)

        original_text = self.version_btn.text()
        self.version_btn.setText("✓ 已复制")

        self._restore_timer = QTimer(self)
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(lambda: self._restore_version_button(original_text))
        self._restore_timer.start(2000)

    def _restore_version_button(self, original_text: str) -> None:
        """恢复版本按钮文本"""
        if self.version_btn:
            self.version_btn.setText(original_text)

    def closeEvent(self, event: QCloseEvent) -> None:
        """关闭时停止定时器，避免在对话框销毁后触发回调"""
        if self._restore_timer is not None:
            self._restore_timer.stop()
        super().closeEvent(event)
