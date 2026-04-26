import sys
import os
from loguru import logger
from PyQt5.QtCore import QObject, QMetaObject, Qt, QTimer


class QtLogSink(QObject):
    """
    Loguru 自定义 Sink，将日志安全转发到 PyQt GUI 组件
    """
    _instance = None
    _pending_logs = []
    _flush_timer = None

    def __init__(self, gui_widget=None):
        super().__init__()
        self.gui_widget = gui_widget

    @classmethod
    def set_gui_widget(cls, widget):
        if cls._instance is None:
            cls._instance = cls(widget)
        else:
            cls._instance.gui_widget = widget

    def write(self, message):
        if self.gui_widget:
            QTimer.singleShot(0, lambda: self._append_to_gui(message))
        elif QtLogSink._flush_timer is not None:
            QtLogSink._pending_logs.append(message)
            if len(QtLogSink._pending_logs) >= 20:
                QtLogSink._flush_pending_logs()

    def _append_to_gui(self, message):
        if self.gui_widget:
            cursor = self.gui_widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(message)
            self.gui_widget.setTextCursor(cursor)
            self.gui_widget.ensureCursorVisible()

    @classmethod
    def _flush_pending_logs(cls):
        if cls._instance and cls._pending_logs:
            combined = "".join(cls._pending_logs)
            cls._pending_logs.clear()
            cls._instance._append_to_gui(combined)

    @classmethod
    def flush_pending_logs(cls):
        if cls._pending_logs:
            QTimer.singleShot(0, cls._flush_pending_logs)


def setup_logger(gui_widget=None, log_file=None, level="INFO", max_size="10 MB", retention="30 days"):
    """
    配置 Loguru 日志系统

    Args:
        gui_widget: PyQt QTextEdit 组件，用于显示日志
        log_file: 日志文件路径
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_size: 日志文件最大大小，默认 10 MB
        retention: 日志保留时间，默认 30 天
    """
    logger.remove()

    log_format = "[{time:YYYY-MM-DD HH:mm:ss.SSS}] [{name}] [{level}] {message}"

    if gui_widget:
        QtLogSink.set_gui_widget(gui_widget)
        logger.add(
            QtLogSink._instance.write,
            level=level,
            format=log_format + "\n",
            colorize=False
        )

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            format=log_format,
            rotation=max_size,
            compression="zip",
            retention=retention,
            encoding="utf-8"
        )

    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True
    )

    logger.info("日志系统初始化完成 [Loguru]")
    return logger


def set_gui_widget(widget):
    """运行时更新 GUI 日志组件"""
    QtLogSink.set_gui_widget(widget)
    if QtLogSink._instance and QtLogSink._pending_logs:
        QtLogSink.flush_pending_logs()


def get_logger():
    """获取 Loguru logger 实例"""
    return logger
