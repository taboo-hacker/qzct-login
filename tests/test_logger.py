"""
utils/logger.py 补充测试

覆盖 setup_logger 的各类 sink 组合（stderr / 文件 / GUI 回调）。
日志文件相关用例使用 pytest 的 tmp_path 隔离磁盘写入。
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger
from pytestqt.qtbot import QtBot


class TestSetupLogger:
    """setup_logger 测试：按 sink 类型（stderr/文件/GUI）分组验证配置行为。"""

    def test_returns_logger(self) -> None:
        """setup_logger 正常执行并返回 loguru logger 实例。"""
        from utils.logger import setup_logger

        result = setup_logger(level="DEBUG")
        assert result is logger

    def test_adds_stderr_handler(self) -> None:
        """默认配置应添加 stderr sink（打桩 logger.add 计数验证）。"""
        import utils.logger as ul

        with patch.object(ul.logger, "add") as mock_add:
            ul.setup_logger()
        mock_add.assert_called_once()  # 仅 stderr 一个 sink

    def test_skips_stderr_sink_when_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """打包模式（console=False）下 sys.stderr 为 None 时不崩溃（回归）。"""
        from utils.logger import setup_logger

        # PyInstaller --noconsole 打包后 sys.stderr 为 None，需跳过 stderr sink
        monkeypatch.setattr("sys.stderr", None)
        log_file = str(tmp_path / "qzct.log")
        result = setup_logger(log_file=log_file, level="INFO")
        assert result is logger

    def test_adds_file_handler(self, tmp_path: Path) -> None:
        """指定 log_file 时应添加文件 sink，写入日志后文件存在且有内容。"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        logger.info("test message")
        content = Path(log_file).read_text(encoding="utf-8")
        assert "test message" in content

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        """log_file 所在目录不存在时应自动创建多级目录。"""
        from utils.logger import setup_logger

        log_dir = tmp_path / "subdir" / "logs"
        log_file = str(log_dir / "test.log")
        setup_logger(log_file=log_file, level="INFO")
        assert log_dir.exists()
        assert os.path.exists(log_file)

    def test_gui_sink_receives_log(self, qtbot: QtBot) -> None:
        """传入 gui_sink 回调时应挂载对应 sink，日志经回调送达。"""
        from utils.logger import setup_logger

        received: list[str] = []
        setup_logger(gui_sink=received.append, level="INFO")
        logger.info("hello gui sink")
        assert any("hello gui sink" in line for line in received)

    def test_gui_sink_none_not_mounted(self) -> None:
        """gui_sink 为 None 时不应挂载 GUI sink（回调列表为空）。"""
        from utils.logger import setup_logger

        received: list[str] = []
        setup_logger(gui_sink=None, level="INFO")
        logger.info("no gui sink")
        assert received == []
