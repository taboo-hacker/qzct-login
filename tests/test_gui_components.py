"""
gui/tray_manager.py + gui/log_sink.py 补充测试

TrayManager：托盘可用性检测（patch QSystemTrayIcon.isSystemTrayAvailable）、
显示窗口、气泡通知与激活/退出事件处理；
QtLogSink：loguru -> GUI 控件的日志桥接，重点验证跨线程 Signal 投递
（QueuedConnection）与启动期无控件时的缓冲逻辑。
"""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication, QTextEdit, QWidget
from pytestqt.qtbot import QtBot

from gui.log_sink import QtLogSink
from gui.styling.widgets import append_preserving_scroll
from tests.conftest import ensure_qapp as _ensure_qapp

if TYPE_CHECKING:
    from gui.tray_manager import TrayManager

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

        from PySide6.QtWidgets import QSystemTrayIcon

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
            assert not parent.isVisible()

    def test_on_quit_calls_real_close(self, qtbot: QtBot) -> None:
        """托盘菜单退出时应调用 parent.quit_application 完成真正的退出清理。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        class FakeMainWidget(QWidget):
            """带 quit_application 契约方法的 MainWindow 测试替身。"""

            quit_calls: int = 0

            def quit_application(self) -> None:
                self.quit_calls += 1

        parent = FakeMainWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
            tm._on_quit()
            assert parent.quit_calls == 1

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


class TestTrayManagerNotifyLevels:
    """notify 分级测试：默认 Information，显式 icon 参数透传给 showMessage。"""

    def _make_tray_with_mock_icon(self, qtbot: QtBot) -> "tuple[TrayManager, MagicMock]":
        """构造可用托盘管理器，图标替换为 MagicMock 便于断言 showMessage。"""
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)
        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
        icon = MagicMock()
        icon.isVisible.return_value = True
        tm._tray_icon = icon
        return tm, icon

    def test_notify_defaults_to_information(self, qtbot: QtBot) -> None:
        """不传 icon 时应以 Information 图标弹出（成功路径默认级别）。"""
        _ensure_qapp()
        from PySide6.QtWidgets import QSystemTrayIcon

        tm, icon = self._make_tray_with_mock_icon(qtbot)
        tm.notify("Title", "Message")
        icon.showMessage.assert_called_once_with(
            "Title", "Message", QSystemTrayIcon.MessageIcon.Information, 3000
        )

    def test_notify_passes_warning_icon(self, qtbot: QtBot) -> None:
        """显式传 Warning 时应透传给 showMessage（失败与成功可区分）。"""
        _ensure_qapp()
        from PySide6.QtWidgets import QSystemTrayIcon

        tm, icon = self._make_tray_with_mock_icon(qtbot)
        tm.notify("Title", "Message", icon=QSystemTrayIcon.MessageIcon.Warning)
        icon.showMessage.assert_called_once_with(
            "Title", "Message", QSystemTrayIcon.MessageIcon.Warning, 3000
        )

    def test_notify_passes_critical_icon(self, qtbot: QtBot) -> None:
        """显式传 Critical 时应透传给 showMessage（链级失败最高级别）。"""
        _ensure_qapp()
        from PySide6.QtWidgets import QSystemTrayIcon

        tm, icon = self._make_tray_with_mock_icon(qtbot)
        tm.notify("Title", "Message", icon=QSystemTrayIcon.MessageIcon.Critical)
        icon.showMessage.assert_called_once_with(
            "Title", "Message", QSystemTrayIcon.MessageIcon.Critical, 3000
        )


class TestTrayShutdownStatus:
    """托盘布防状态测试：tooltip 与"取消定时关机"菜单项随 armed 切换。"""

    def _make_tray_with_mocks(self, qtbot: QtBot) -> "tuple[TrayManager, MagicMock, MagicMock]":
        """构造可用托盘管理器，图标与菜单 action 均替换为 MagicMock。"""
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)
        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
        icon = MagicMock()
        icon.isVisible.return_value = True
        tm._tray_icon = icon
        action = MagicMock()
        tm._cancel_shutdown_action = action
        return tm, icon, action

    def test_armed_updates_tooltip_and_shows_menu_action(self, qtbot: QtBot) -> None:
        """armed=True：tooltip 追加布防标记与剩余时间，菜单项可见。"""
        _ensure_qapp()
        tm, icon, action = self._make_tray_with_mocks(qtbot)
        tm.set_shutdown_status(armed=True, detail="剩 02:31:23")
        icon.setToolTip.assert_called_with("校园网自动登录 · 已布防关机（剩 02:31:23）")
        action.setVisible.assert_called_with(True)

    def test_armed_without_detail_omits_parenthesis(self, qtbot: QtBot) -> None:
        """armed=True 且 detail 为空：tooltip 不追加空括号。"""
        _ensure_qapp()
        tm, icon, _action = self._make_tray_with_mocks(qtbot)
        tm.set_shutdown_status(armed=True)
        icon.setToolTip.assert_called_with("校园网自动登录 · 已布防关机")

    def test_disarmed_restores_tooltip_and_hides_menu_action(self, qtbot: QtBot) -> None:
        """armed=False：tooltip 还原静态文案，菜单项隐藏。"""
        _ensure_qapp()
        tm, icon, action = self._make_tray_with_mocks(qtbot)
        tm.set_shutdown_status(armed=False)
        icon.setToolTip.assert_called_with("校园网自动登录")
        action.setVisible.assert_called_with(False)

    def test_set_shutdown_status_noop_without_tray(self, qtbot: QtBot) -> None:
        """托盘不可用（_tray_icon=None）时布防状态更新应安全 no-op。"""
        _ensure_qapp()
        from gui.tray_manager import TrayManager

        # 绕过 __init__ 手工构造半成品对象，模拟"托盘初始化失败"状态
        tm = TrayManager.__new__(TrayManager)
        tm._parent = QWidget()
        tm._tray_icon = None
        tm._cancel_shutdown_action = None
        tm.set_shutdown_status(armed=True, detail="剩 01:00:00")  # 不崩溃即通过


class TestTrayCancelShutdownMenu:
    """托盘菜单测试：「取消定时关机」入口的位置、初始可见性与触发接线。"""

    def test_menu_contains_cancel_action_between_show_and_quit(self, qtbot: QtBot) -> None:
        """菜单应含"取消定时关机"，位于"显示主窗口"与"退出"之间且初始不可见。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
        assert tm._tray_icon is not None
        menu = tm._tray_icon.contextMenu()
        assert menu is not None
        texts = [action.text() for action in menu.actions()]
        assert texts.index("显示主窗口") < texts.index("取消定时关机") < texts.index("退出")
        assert tm._cancel_shutdown_action is not None
        assert tm._cancel_shutdown_action.isVisible() is False

    def test_cancel_action_triggers_parent_callback(self, qtbot: QtBot) -> None:
        """触发菜单 action 应反射调用 parent.on_cancel_shutdown。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        class FakeMainWidget(QWidget):
            """带 on_cancel_shutdown 契约方法的 MainWindow 测试替身。"""

            cancel_calls: int = 0

            def on_cancel_shutdown(self) -> None:
                self.cancel_calls += 1

        parent = FakeMainWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
        assert tm._cancel_shutdown_action is not None
        tm._cancel_shutdown_action.trigger()
        assert parent.cancel_calls == 1

    def test_cancel_action_without_parent_callback_noop(self, qtbot: QtBot) -> None:
        """parent 未提供 on_cancel_shutdown 时触发也不崩溃。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.tray_manager import TrayManager

        parent = QWidget()
        qtbot.addWidget(parent)

        with patch("gui.tray_manager.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
            tm = TrayManager(parent)
        assert tm._cancel_shutdown_action is not None
        tm._cancel_shutdown_action.trigger()


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

        sink = QtLogSink(None)
        sink.write("buffered msg\n")
        assert any("buffered msg" in log for log in QtLogSink._pending_logs)

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


class TestAppendPreservingScroll:
    """append_preserving_scroll：追加内容时按用户滚动位置决定是否跟随。

    回归：QtLogSink._safe_append_to_gui 此前每条日志都无条件
    ensureCursorVisible()，且 setTextCursor 本身也会把视图滚到游标处，
    用户无法在任务运行期间阅读已被刷走的历史日志。

    用例直接调用该函数而非构造 QtLogSink 实例：局部 QObject 在测试
    teardown 被回收时，会与 qtbot 销毁控件产生竞态，在 Linux offscreen
    平台触发段错误（退出码 139）。QtLogSink 自身的桥接逻辑由本文件
    既有的 TestQtLogSink 覆盖，此处只验证滚动策略。
    """

    def _filled_edit(self, qtbot: QtBot) -> QTextEdit:
        """构造已填充多行、滚动条可滚动的文本控件。"""
        _ensure_qapp()
        widget = QTextEdit()
        qtbot.addWidget(widget)
        widget.resize(240, 80)
        widget.show()
        for idx in range(200):
            widget.append(f"line {idx}")
        QApplication.processEvents()
        return widget

    def test_preserves_scroll_when_scrolled_up(self, qtbot: QtBot) -> None:
        """用户上滚到顶部后追加内容，滚动位置应保持不变。"""
        widget = self._filled_edit(qtbot)
        scrollbar = widget.verticalScrollBar()
        assert scrollbar.maximum() > 0, "测试前置条件：内容需足以产生滚动条"
        scrollbar.setValue(0)
        before = scrollbar.value()

        append_preserving_scroll(widget, lambda cursor: cursor.insertText("new line\n"))
        QApplication.processEvents()

        assert scrollbar.value() == before, "追加内容不应把用户拽回底部"
        assert "new line" in widget.toPlainText()

    def test_follows_when_at_bottom(self, qtbot: QtBot) -> None:
        """用户贴着底部时，追加内容应继续跟随到最新一行。"""
        widget = self._filled_edit(qtbot)
        scrollbar = widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        append_preserving_scroll(widget, lambda cursor: cursor.insertText("new line\n"))
        QApplication.processEvents()

        assert scrollbar.maximum() - scrollbar.value() <= 4
