"""
gui/tray_manager.py + gui/log_sink.py 补充测试

TrayManager：托盘可用性检测（patch QSystemTrayIcon.isSystemTrayAvailable）、
显示窗口、气泡通知与激活/退出事件处理；
QtLogSink：loguru -> GUI 控件的日志桥接，重点验证跨线程 Signal 投递
（QueuedConnection）与启动期无控件时的缓冲逻辑。
"""

from PySide6.QtWidgets import QApplication, QTextEdit, QWidget
from pytestqt.qtbot import QtBot

from gui.log_sink import QtLogSink


def _ensure_qapp() -> QApplication:
    """模块级辅助函数：确保 QApplication 实例存在（托盘/信号机制依赖）。"""
    return QApplication.instance() or QApplication([])


# =====================================================================
# TrayManager
# =====================================================================


class TestTrayManager:
    """TrayManager 测试：托盘可用/不可用两种环境下的创建与交互行为。"""

    def test_tray_unavailable(self, qtbot: QtBot) -> None:
        """系统托盘不可用时不创建图标"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=False):
            tm = TrayManager(parent)
            assert tm._tray_icon is None
            assert tm.is_available() is False

    def test_tray_available(self, qtbot: QtBot) -> None:
        """系统托盘可用时应创建托盘图标并报告可用。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            assert tm._tray_icon is not None
            assert tm.is_available() is True

    def test_show_window(self, qtbot: QtBot) -> None:
        """show_window 显示并激活父窗口"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm.show_window()
            assert parent.isVisible()

    def test_notify_when_available(self, qtbot: QtBot) -> None:
        """托盘图标可见时 notify 应调用 showMessage 弹出气泡通知。"""
        _ensure_qapp()
        from unittest.mock import MagicMock, patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            # 用 MagicMock 替换真实图标，便于断言 showMessage 被调用
            tm._tray_icon = MagicMock()
            tm._tray_icon.isVisible.return_value = True
            tm.notify("Title", "Message")
            tm._tray_icon.showMessage.assert_called_once()

    def test_notify_when_unavailable(self, qtbot: QtBot) -> None:
        """托盘图标为 None 时 notify 应静默不崩溃。"""
        _ensure_qapp()
        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        # 绕过 __init__ 手工构造半成品对象，模拟"托盘初始化失败"状态
        tm = TrayManager.__new__(TrayManager)
        tm._parent = parent
        tm._tray_icon = None
        tm.notify("Title", "Message")

    def test_on_activated_double_click(self, qtbot: QtBot) -> None:
        """双击托盘图标应显示并激活父窗口。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            from PySide6.QtWidgets import QSystemTrayIcon

            tm._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
            assert parent.isVisible()

    def test_on_activated_single_click_noop(self, qtbot: QtBot) -> None:
        """单击（Trigger）托盘图标不应弹出父窗口。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_activated(0)  # Trigger
            assert not parent.isVisible()

    def test_on_quit_calls_real_close(self, qtbot: QtBot) -> None:
        """托盘菜单退出时应调用 parent.quit_application 完成真正的退出清理。"""
        _ensure_qapp()
        from unittest.mock import MagicMock, patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)
        parent.quit_application = MagicMock()

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_quit()
            parent.quit_application.assert_called_once()

    def test_on_quit_no_real_close(self, qtbot: QtBot) -> None:
        """parent 未提供 quit_application 时退出也不崩溃。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_quit()


# =====================================================================
# QtLogSink
# =====================================================================


class TestQtLogSink:
    """QtLogSink 测试：loguru sink 与 GUI 控件绑定、跨线程投递与缓冲。"""

    def setup_method(self) -> None:
        """每个测试前重置 QtLogSink 单例的类属性，保证用例独立。"""
        QtLogSink._instance = None
        QtLogSink._pending_logs = []

    def test_set_gui_widget_creates_instance(self, qtbot: QtBot) -> None:
        """首次 set_gui_widget 应创建单例并持有控件引用。"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        assert QtLogSink._instance is not None
        assert QtLogSink._instance.gui_widget is widget

    def test_set_gui_widget_updates_existing(self, qtbot: QtBot) -> None:
        """重复 set_gui_widget 应更新现有单例指向新控件。"""
        _ensure_qapp()
        w1 = QTextEdit()
        w2 = QTextEdit()
        qtbot.addWidget(w1)
        qtbot.addWidget(w2)
        QtLogSink.set_gui_widget(w1)
        QtLogSink.set_gui_widget(w2)
        assert QtLogSink._instance is not None
        assert QtLogSink._instance.gui_widget is w2

    def test_write_with_gui_widget(self, qtbot: QtBot) -> None:
        """主线程 write() 后泵事件循环，日志应出现在 GUI 控件中。"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        assert QtLogSink._instance is not None
        sink = QtLogSink._instance
        sink.write("test message\n")
        # 处理事件循环
        QApplication.processEvents()
        assert "test message" in widget.toPlainText()

    def test_write_from_worker_thread_delivers_to_gui(self, qtbot: QtBot) -> None:
        """工作线程调用 write() 后日志投递到 GUI（回归：旧 singleShot 实现丢失）"""
        import threading

        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        assert QtLogSink._instance is not None
        sink = QtLogSink._instance

        def worker() -> None:
            # 模拟 TaskExecutor 工作线程里的 loguru 调用
            sink.write("from worker thread\n")

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        # 跨线程信号为 QueuedConnection，泵事件循环后送达
        for _ in range(50):
            QApplication.processEvents()
        assert "from worker thread" in widget.toPlainText()

    def test_write_without_gui_widget_buffers(self, qtbot: QtBot) -> None:
        """GUI 控件尚未创建（启动期）时 write() 应把日志暂存到缓冲列表。"""
        _ensure_qapp()
        from PySide6.QtCore import QTimer

        sink = QtLogSink(None)
        QtLogSink._flush_timer = QTimer()  # 模拟已设置 flush_timer
        sink.write("buffered msg\n")
        assert any("buffered msg" in log for log in QtLogSink._pending_logs)
        QtLogSink._flush_timer = None  # 清理

    def test_flush_pending_logs(self, qtbot: QtBot) -> None:
        """_flush_pending_logs 应把缓冲日志写入 GUI 并清空缓冲。"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        QtLogSink._pending_logs = ["msg1\n", "msg2\n"]
        QtLogSink._flush_pending_logs()
        QApplication.processEvents()
        assert "msg1" in widget.toPlainText()
        assert "msg2" in widget.toPlainText()
        assert len(QtLogSink._pending_logs) == 0

    def test_flush_pending_logs_empty(self) -> None:
        """缓冲为空时刷新应为空操作不崩溃。"""
        QtLogSink._flush_pending_logs()

    def test_flush_pending_logs_no_instance(self) -> None:
        """单例尚未创建时刷新应直接返回不崩溃。"""
        QtLogSink._instance = None
        QtLogSink._pending_logs = ["msg\n"]
        QtLogSink._flush_pending_logs()

    def test_flush_pending_logs_classmethod(self, qtbot: QtBot) -> None:
        """公共方法 flush_pending_logs 应触发 QTimer 定时刷新流程。"""
        _ensure_qapp()
        QtLogSink._pending_logs = ["test\n"]
        QtLogSink._instance = QtLogSink(QTextEdit())
        QtLogSink.flush_pending_logs()
        QApplication.processEvents()
