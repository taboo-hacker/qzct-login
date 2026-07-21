"""
系统托盘管理模块

将 MainWindow 中的系统托盘逻辑封装为独立组件。
"""

from PyQt5.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QSystemTrayIcon,
    QWidget,
)


class TrayManager:
    """系统托盘管理器。

    封装 QSystemTrayIcon 的创建、菜单、通知和显示/隐藏逻辑。
    """

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._tray_icon: QSystemTrayIcon | None = None

        if not QSystemTrayIcon.isSystemTrayAvailable():
            from infra.logging import info

            info("main", "系统托盘不可用")
            return

        self._setup()

    def _setup(self) -> None:
        style = QApplication.style()
        assert style is not None
        icon = style.standardIcon(QStyle.SP_ComputerIcon)  # type: ignore[attr-defined]
        self._tray_icon = QSystemTrayIcon(icon, self._parent)
        self._tray_icon.setToolTip("校园网自动登录")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        assert show_action is not None
        show_action.triggered.connect(self.show_window)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("退出")
        assert quit_action is not None
        quit_action.triggered.connect(self._on_quit)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_activated)
        self._tray_icon.show()

    def is_available(self) -> bool:
        return self._tray_icon is not None and self._tray_icon.isVisible()

    def show_window(self) -> None:
        self._parent.showNormal()
        self._parent.activateWindow()
        self._parent.raise_()

    def notify(self, title: str, message: str) -> None:
        if self.is_available():
            assert self._tray_icon is not None
            self._tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.Information,  # type: ignore[attr-defined]
                3000,
            )

    def _on_activated(self, reason: int) -> None:
        if reason == QSystemTrayIcon.DoubleClick:  # type: ignore[attr-defined]
            self.show_window()

    def _on_quit(self) -> None:
        """退出程序——调用主窗口的 quit 公共方法"""
        quit_method = getattr(self._parent, "quit_application", None)
        if callable(quit_method):
            quit_method()
