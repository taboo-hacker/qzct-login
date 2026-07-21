"""
utils/logger.py 补充测试

覆盖 setup_logger 配置路径和 get_logger/set_gui_widget 功能。
"""

import os

from loguru import logger


class TestSetupLogger:
    """setup_logger 测试"""

    def test_returns_logger(self):
        """setup_logger 返回 logger 实例"""
        from utils.logger import setup_logger

        result = setup_logger(level="DEBUG")
        assert result is not None

    def test_adds_stderr_handler(self):
        """默认添加 stderr 输出"""
        from utils.logger import setup_logger

        setup_logger()
        # 验证没有崩溃即可——stderr handler 已添加

    def test_adds_file_handler(self, tmp_path):
        """指定 log_file 时添加文件 handler"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        logger.info("test message")
        # 验证日志文件被创建
        assert os.path.exists(log_file)

    def test_creates_log_directory(self, tmp_path):
        """log_file 目录不存在时自动创建"""
        from utils.logger import setup_logger

        log_dir = tmp_path / "subdir" / "logs"
        log_file = str(log_dir / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        assert log_dir.exists()

    def test_gui_widget_adds_handler(self, qtbot):
        """传入 gui_widget 时添加 QtLogSink handler"""
        from PyQt5.QtWidgets import QTextEdit

        from utils.logger import setup_logger

        widget = QTextEdit()
        qtbot.addWidget(widget)
        result = setup_logger(gui_widget=widget)
        assert result is not None


class TestGetLogger:
    """get_logger 测试"""

    def test_returns_logger_instance(self):
        from utils.logger import get_logger

        result = get_logger()
        assert result is not None


class TestSetGuiWidget:
    """set_gui_widget 测试"""

    def test_sets_widget(self, qtbot):
        from PyQt5.QtWidgets import QTextEdit

        from gui.log_sink import QtLogSink
        from utils.logger import set_gui_widget

        # 重置单例
        QtLogSink._instance = None
        QtLogSink._pending_logs = []

        widget = QTextEdit()
        qtbot.addWidget(widget)
        set_gui_widget(widget)
        assert QtLogSink._instance is not None
        assert QtLogSink._instance.gui_widget is widget
