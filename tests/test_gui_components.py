"""
gui/tray_manager.py + gui/log_sink.py 补充测试
"""

from PyQt5.QtWidgets import QApplication, QTextEdit, QWidget

from gui.log_sink import QtLogSink


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


# =====================================================================
# TrayManager
# =====================================================================


class TestTrayManager:
    """TrayManager 测试"""

    def test_tray_unavailable(self, qtbot):
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

    def test_tray_available(self, qtbot):
        """系统托盘可用时创建图标"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            assert tm._tray_icon is not None
            assert tm.is_available() is True

    def test_show_window(self, qtbot):
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

    def test_notify_when_available(self, qtbot):
        """可用时调用 showMessage"""
        _ensure_qapp()
        from unittest.mock import MagicMock, patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._tray_icon = MagicMock()
            tm._tray_icon.isVisible.return_value = True
            tm.notify("Title", "Message")
            tm._tray_icon.showMessage.assert_called_once()

    def test_notify_when_unavailable(self, qtbot):
        """不可用时不崩溃"""
        _ensure_qapp()
        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        tm = TrayManager.__new__(TrayManager)
        tm._parent = parent
        tm._tray_icon = None
        tm.notify("Title", "Message")

    def test_on_activated_double_click(self, qtbot):
        """双击激活窗口"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            from PyQt5.QtWidgets import QSystemTrayIcon

            tm._on_activated(QSystemTrayIcon.DoubleClick)
            assert parent.isVisible()

    def test_on_activated_single_click_noop(self, qtbot):
        """单击不激活窗口"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_activated(0)  # Trigger
            assert not parent.isVisible()

    def test_on_quit_calls_real_close(self, qtbot):
        """退出时调用 parent.quit_application"""
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

    def test_on_quit_no_real_close(self, qtbot):
        """parent 没有 _real_close 时不崩溃"""
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
    """QtLogSink 测试"""

    def setup_method(self) -> None:
        """每个测试前重置单例"""
        QtLogSink._instance = None
        QtLogSink._pending_logs = []

    def test_set_gui_widget_creates_instance(self, qtbot):
        """set_gui_widget 创建单例"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        assert QtLogSink._instance is not None
        assert QtLogSink._instance.gui_widget is widget

    def test_set_gui_widget_updates_existing(self, qtbot):
        """已存在实例时更新 widget"""
        _ensure_qapp()
        w1 = QTextEdit()
        w2 = QTextEdit()
        qtbot.addWidget(w1)
        qtbot.addWidget(w2)
        QtLogSink.set_gui_widget(w1)
        QtLogSink.set_gui_widget(w2)
        assert QtLogSink._instance.gui_widget is w2

    def test_write_with_gui_widget(self, qtbot):
        """有 gui_widget 时通过跨线程信号投递"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        sink = QtLogSink._instance
        sink.write("test message\n")
        # 处理事件循环
        QApplication.processEvents()
        assert "test message" in widget.toPlainText()

    def test_write_from_worker_thread_delivers_to_gui(self, qtbot):
        """工作线程调用 write() 后日志投递到 GUI（回归：旧 singleShot 实现丢失）"""
        import threading

        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        QtLogSink.set_gui_widget(widget)
        sink = QtLogSink._instance

        def worker():
            # 模拟 TaskExecutor 工作线程里的 loguru 调用
            sink.write("from worker thread\n")

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        # 跨线程信号为 QueuedConnection，泵事件循环后送达
        for _ in range(50):
            QApplication.processEvents()
        assert "from worker thread" in widget.toPlainText()

    def test_write_without_gui_widget_buffers(self, qtbot):
        """无 gui_widget 但有 flush_timer 时缓冲日志"""
        _ensure_qapp()
        from PyQt5.QtCore import QTimer

        sink = QtLogSink(None)
        QtLogSink._flush_timer = QTimer()  # 模拟已设置 flush_timer
        sink.write("buffered msg\n")
        assert any("buffered msg" in log for log in QtLogSink._pending_logs)
        QtLogSink._flush_timer = None  # 清理

    def test_flush_pending_logs(self, qtbot):
        """flush_pending_logs 将缓冲写入 GUI"""
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

    def test_flush_pending_logs_empty(self):
        """无待刷新日志时不崩溃"""
        QtLogSink._flush_pending_logs()

    def test_flush_pending_logs_no_instance(self):
        """无实例时不崩溃"""
        QtLogSink._instance = None
        QtLogSink._pending_logs = ["msg\n"]
        QtLogSink._flush_pending_logs()

    def test_flush_pending_logs_classmethod(self, qtbot):
        """flush_pending_logs 公共方法触发 QTimer"""
        _ensure_qapp()
        QtLogSink._pending_logs = ["test\n"]
        QtLogSink._instance = QtLogSink(QTextEdit())
        QtLogSink.flush_pending_logs()
        QApplication.processEvents()
