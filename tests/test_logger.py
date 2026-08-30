"""
utils/logger.py 补充测试

覆盖 setup_logger 的各类 sink 组合（stderr / 文件 / GUI 控件）
以及 get_logger、set_gui_widget（QtLogSink 单例绑定）功能。
日志文件相关用例使用 pytest 的 tmp_path 隔离磁盘写入。
"""

import os
from pathlib import Path

import pytest
from loguru import logger
from pytestqt.qtbot import QtBot


class TestSetupLogger:
    """setup_logger 测试：按 sink 类型（stderr/文件/GUI）分组验证配置行为。"""

    def test_returns_logger(self) -> None:
        """setup_logger 正常执行并返回 logger 实例。"""
        from utils.logger import setup_logger

        result = setup_logger(level="DEBUG")
        assert result is not None

    def test_adds_stderr_handler(self) -> None:
        """默认配置应成功添加 stderr sink（不崩溃即通过）。"""
        from utils.logger import setup_logger

        setup_logger()
        # 验证没有崩溃即可——stderr handler 已添加

    def test_skips_stderr_sink_when_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """打包模式（console=False）下 sys.stderr 为 None 时不崩溃（回归）。"""
        from utils.logger import setup_logger

        # PyInstaller --noconsole 打包后 sys.stderr 为 None，需跳过 stderr sink
        monkeypatch.setattr("sys.stderr", None)
        log_file = str(tmp_path / "qzct.log")
        result = setup_logger(log_file=log_file, level="INFO")
        assert result is not None

    def test_adds_file_handler(self, tmp_path: Path) -> None:
        """指定 log_file 时应添加文件 sink，写入日志后文件存在。"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        logger.info("test message")
        # 验证日志文件被创建
        assert os.path.exists(log_file)

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        """log_file 所在目录不存在时应自动创建多级目录。"""
        from utils.logger import setup_logger

        log_dir = tmp_path / "subdir" / "logs"
        log_file = str(log_dir / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        assert log_dir.exists()

    def test_gui_widget_adds_handler(self, qtbot: QtBot) -> None:
        """传入 gui_widget 时应成功挂载 QtLogSink handler（不崩溃）。"""
        from PySide6.QtWidgets import QTextEdit

        from utils.logger import setup_logger

        widget = QTextEdit()
        qtbot.addWidget(widget)
        result = setup_logger(gui_widget=widget)
        assert result is not None


class TestGetLogger:
    """get_logger 测试。"""

    def test_returns_logger_instance(self) -> None:
        """get_logger 应返回非 None 的 logger 实例。"""
        from utils.logger import get_logger

        result = get_logger()
        assert result is not None


class TestSetGuiWidget:
    """set_gui_widget 测试：验证 GUI 日志控件与 QtLogSink 单例的绑定。"""

    def test_sets_widget(self, qtbot: QtBot) -> None:
        """设置 widget 后 QtLogSink 单例应被创建并持有该控件引用。"""
        from PySide6.QtWidgets import QTextEdit

        from gui.log_sink import QtLogSink
        from utils.logger import set_gui_widget

        # QtLogSink 为单例，先重置类属性，避免受其他测试执行顺序影响
        QtLogSink._instance = None
        QtLogSink._pending_logs = []

        widget = QTextEdit()
        qtbot.addWidget(widget)
        set_gui_widget(widget)
        assert QtLogSink._instance is not None
        assert QtLogSink._instance.gui_widget is widget
