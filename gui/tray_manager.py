"""
系统托盘管理模块

将 MainWindow 中的系统托盘逻辑封装为独立组件。

职责：托盘图标与右键菜单（显示主窗口 / 退出）、双击还原窗口、
气泡通知。系统不支持托盘时（如部分精简系统/远程会话）自动降级：
is_available() 返回 False，主窗口关闭按钮将直接退出程序。
"""

from PySide6.QtGui import QAction
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
        self._cancel_shutdown_action: QAction | None = None

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
        # 取消定时关机：仅在定时关机已布防时可见（set_shutdown_status 控制）
        self._cancel_shutdown_action = tray_menu.addAction("取消定时关机")
        assert self._cancel_shutdown_action is not None
        self._cancel_shutdown_action.setVisible(False)
        self._cancel_shutdown_action.triggered.connect(self._on_cancel_shutdown)
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

    def notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        """弹出托盘气泡通知（3 秒自动消失，托盘不可用时静默跳过）。

        Args:
            title: 通知标题
            message: 通知正文
            icon: 通知级别图标（Information/Warning/Critical），默认信息级
        """
        if self.is_available():
            assert self._tray_icon is not None
            self._tray_icon.showMessage(title, message, icon, 3000)

    def set_shutdown_status(self, armed: bool, detail: str = "") -> None:
        """同步定时关机布防状态到托盘 tooltip 与右键菜单。

        armed=True 时 tooltip 追加布防标记并显示"取消定时关机"菜单项
        （detail 非空时追加剩余时间）；False 时还原静态 tooltip 并隐藏
        菜单项。托盘不可用时安全 no-op。

        Args:
            armed: 是否有定时关机正在生效
            detail: 剩余时间文案（如 "剩 02:31:23"）
        """
        if self._tray_icon is None:
            return
        if armed:
            tooltip = "校园网自动登录 · 已布防关机"
            if detail:
                tooltip += f"（{detail}）"
            self._tray_icon.setToolTip(tooltip)
            if self._cancel_shutdown_action is not None:
                self._cancel_shutdown_action.setVisible(True)
        else:
            self._tray_icon.setToolTip("校园网自动登录")
            if self._cancel_shutdown_action is not None:
                self._cancel_shutdown_action.setVisible(False)

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

    def _on_cancel_shutdown(self) -> None:
        """菜单"取消定时关机"——反射调用主窗口回调（与 _on_quit 同模式）"""
        cancel_method = getattr(self._parent, "on_cancel_shutdown", None)
        if callable(cancel_method):
            cancel_method()
