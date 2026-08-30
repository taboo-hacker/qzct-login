"""
系统托盘管理模块

将 MainWindow 中的系统托盘逻辑封装为独立组件。

职责：托盘图标与右键菜单（显示主窗口 / 退出）、双击还原窗口、
气泡通知。系统不支持托盘时（如部分精简系统/远程会话）自动降级：
is_available() 返回 False，主窗口关闭按钮将直接退出程序。
"""

from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QSystemTrayIcon,
    QWidget,
)


class TrayManager:
    """系统托盘管理器。

    封装 QSystemTrayIcon 的创建、菜单、通知和显示/隐藏逻辑。

    与主窗口的交互契约：
        - 显示窗口：直接调用 parent.showNormal/activateWindow/raise_
        - 退出程序：调用 parent.quit_application()（由 MainWindow 提供）
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
        """创建托盘图标、右键菜单并显示（仅系统支持托盘时调用）。"""
        style = QApplication.style()
        assert style is not None
        # 使用系统内置图标，避免额外打包图标资源
        icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
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
        """托盘是否可用且可见（决定关闭按钮是"最小化"还是"退出"）。"""
        return self._tray_icon is not None and self._tray_icon.isVisible()

    def show_window(self) -> None:
        """还原并前置主窗口（菜单"显示主窗口" / 托盘双击共用）。"""
        self._parent.showNormal()
        self._parent.activateWindow()
        self._parent.raise_()

    def notify(self, title: str, message: str) -> None:
        """弹出托盘气泡通知（3 秒自动消失，托盘不可用时静默跳过）。"""
        if self.is_available():
            assert self._tray_icon is not None
            self._tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """托盘图标点击事件：双击还原窗口（单击不响应，避免误触）。"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def _on_quit(self) -> None:
        """退出程序——调用主窗口的 quit 公共方法"""
        # 反射查找避免硬编码依赖 MainWindow 类型，便于测试替身
        quit_method = getattr(self._parent, "quit_application", None)
        if callable(quit_method):
            quit_method()
