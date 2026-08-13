"""
GUI 日志 Sink

将 Loguru 日志安全转发到 PyQt GUI 组件。
从 utils/logger.py 中拆出，使 utils/ 层不再在模块加载时耦合 PyQt5。

跨线程投递机制：
    loguru 的 sink.write() 在调用线程（可能是 TaskExecutor 工作线程）执行，
    直接操作 widget 违反 Qt 线程规则。旧实现用 QTimer.singleShot(0, callable)
    从工作线程投递，但该回调需要调用线程存在事件循环，工作线程没有事件循环，
    导致服务层日志在 GUI 中全部静默丢失。
    现改用 pyqtSignal 投递：槽函数绑定在 sink 所属线程（主线程），
    Qt 对跨线程 emit 自动使用 QueuedConnection，消息可靠送达。
"""

import contextlib
import threading
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget


class QtLogSink(QObject):
    """
    Loguru 自定义 Sink，将日志安全转发到 PyQt GUI 组件

    无 GUI widget 时（初始化前、widget 销毁后），日志缓冲到 _pending_logs，
    在 set_gui_widget 时通过 flush_pending_logs 统一 flush。
    """

    _instance: Optional["QtLogSink"] = None
    _pending_logs: list[str] = []
    _pending_lock = threading.Lock()

    # 跨线程日志消息通道（emit 可发生在任意线程，槽在主线程执行）
    _log_message = pyqtSignal(str)

    def __init__(self, gui_widget: QWidget | None = None) -> None:
        super().__init__()
        self._gui_widget: QWidget | None = None
        self._destroyed_conn: Any = None
        self._log_message.connect(self._on_log_message)
        if gui_widget is not None:
            self.set_widget(gui_widget)

    @property
    def gui_widget(self) -> QWidget | None:
        return self._gui_widget

    def set_widget(self, widget: QWidget) -> None:
        """设置 GUI widget 并监听其 destroyed 信号以清空引用。"""
        # 断开旧 widget 的 destroyed 信号
        if self._gui_widget is not None:
            with contextlib.suppress(TypeError):
                self._gui_widget.destroyed.disconnect(self._on_widget_destroyed)
        self._gui_widget = widget
        # 监听 widget 销毁，防止访问已删除的 C++ 对象
        self._destroyed_conn = widget.destroyed.connect(self._on_widget_destroyed)

    def _on_widget_destroyed(self) -> None:
        """widget 被 Qt C++ 侧销毁时清空引用。"""
        self._gui_widget = None
        self._destroyed_conn = None

    @classmethod
    def set_gui_widget(cls, widget: QWidget) -> None:
        if cls._instance is None:
            cls._instance = cls(widget)
        else:
            cls._instance.set_widget(widget)
        # widget 就绪后 flush 缓冲的日志
        cls.flush_pending_logs()

    def write(self, message: str) -> None:
        """loguru sink 入口，可在任意线程调用。"""
        if self._gui_widget is not None:
            # 跨线程 emit：Qt 自动转为 QueuedConnection 投递到主线程
            self._log_message.emit(message)
        else:
            # 无 GUI widget 时缓冲日志（保留最近日志，超出上限丢弃最旧的）
            with QtLogSink._pending_lock:
                QtLogSink._pending_logs.append(message)
                if len(QtLogSink._pending_logs) > 500:
                    del QtLogSink._pending_logs[:100]

    def _on_log_message(self, message: str) -> None:
        """日志消息槽（在 sink 所属线程执行）。"""
        if self._gui_widget is not None:
            self._safe_append_to_gui(self._gui_widget, message)

    def _safe_append_to_gui(self, widget: QWidget, message: str) -> None:
        """安全地向 GUI 追加日志，widget 已销毁时静默丢弃。"""
        try:
            cursor = widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(message)
            widget.setTextCursor(cursor)
            widget.ensureCursorVisible()
        except RuntimeError:
            # widget 的 C++ 对象已被销毁
            self._gui_widget = None

    @classmethod
    def _flush_pending_logs(cls) -> None:
        with cls._pending_lock:
            if not cls._pending_logs:
                return
            combined = "".join(cls._pending_logs)
            cls._pending_logs.clear()
        if cls._instance is not None and cls._instance._gui_widget is not None:
            cls._instance._log_message.emit(combined)

    @classmethod
    def flush_pending_logs(cls) -> None:
        if cls._pending_logs:
            cls._flush_pending_logs()
