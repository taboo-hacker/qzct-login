"""
D3 测试：日志文件落盘配置

测试 setup_logger() 在传入 log_file 时的行为：文件创建、目录自动创建、
权限限制（POSIX 0o600）、日志写入，以及 core.constants 中 LOG_FILE 常量定义。
磁盘写入全部使用 tmp_path 隔离，不触碰真实配置目录。
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger


class TestSetupLoggerFileLogging:
    """setup_logger() 文件日志功能测试：文件创建、内容写入、目录与权限。"""

    def test_log_file_created(self, tmp_path: Path) -> None:
        """传入 log_file 后，写一条日志即应触发日志文件创建。"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="INFO")

        logger.info("test message for file")

        assert os.path.exists(log_file)

    def test_log_message_written_to_file(self, tmp_path: Path) -> None:
        """日志消息应完整写入文件（含唯一标记串）。"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="DEBUG")

        logger.info("unique marker message 12345")

        # loguru 异步缓冲可能导致内容未落盘，logger.complete() 强制 flush
        logger.complete()

        with open(log_file, encoding="utf-8") as f:
            content = f.read()
        assert "unique marker message 12345" in content

    def test_log_file_directory_auto_created(self, tmp_path: Path) -> None:
        """日志目录不存在时，配置 log_file 后应自动创建多级目录。"""
        from utils.logger import setup_logger

        log_dir = tmp_path / "logs" / "subdir"
        log_file = str(log_dir / "app.log")

        assert not log_dir.exists()

        setup_logger(log_file=log_file, level="INFO")

        assert log_dir.exists()

    def test_log_file_permissions_restricted_posix(self, tmp_path: Path) -> None:
        """POSIX 平台上日志文件权限应为 0o600（仅属主可读写，防敏感信息泄露）。"""
        # Windows 无 POSIX 权限位，跳过该用例
        if os.name != "posix":
            pytest.skip("POSIX only")

        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="INFO")

        logger.info("permission test")

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600

    def test_no_log_file_no_error(self, tmp_path: Path) -> None:
        """不传 log_file（仅控制台输出）时调用不应报错。"""
        from utils.logger import setup_logger

        # 不传 log_file
        setup_logger(level="INFO")

        # 不应抛出异常
        logger.info("test without file")


class TestCrashLog:
    """main._write_crash_log 测试：crash.log 兜底落盘、写入后收权与容错。"""

    def test_write_crash_log_writes_and_restricts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """写入 crash.log 后文件应包含消息，并以该文件路径调用收权函数。"""
        import main

        monkeypatch.setattr("core.constants.CONFIG_DIR", str(tmp_path))
        # _write_crash_log 内部延迟导入 infra.file_permissions，patch 模块属性即生效
        with patch("infra.file_permissions.restrict_file_permissions") as mock_restrict:
            main._write_crash_log("Fatal error: X")

        crash_log = tmp_path / "crash.log"
        assert crash_log.exists()
        assert "Fatal error: X" in crash_log.read_text(encoding="utf-8")
        mock_restrict.assert_called_once_with(str(crash_log))

    def test_write_crash_log_swallows_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CONFIG_DIR 指向普通文件（路径不可写）时应静默吞掉异常，不向调用方抛错。"""
        import main

        blocker = tmp_path / "blocker"
        blocker.write_text("not a dir", encoding="utf-8")
        monkeypatch.setattr("core.constants.CONFIG_DIR", str(blocker))

        # 不应抛出 NotADirectoryError 等任何异常（excepthook 最后一级不得自身崩溃）
        main._write_crash_log("Fatal error: Y")


class TestLogFileConstant:
    """LOG_FILE 常量定义测试：验证日志文件路径常量的存在性与位置。"""

    def test_log_file_constant_exists(self) -> None:
        """core.constants 应导出字符串类型的 LOG_FILE 且以 qzct.log 结尾。"""
        from core.constants import LOG_FILE

        assert LOG_FILE is not None
        assert isinstance(LOG_FILE, str)
        assert LOG_FILE.endswith("qzct.log")

    def test_log_file_in_config_dir(self) -> None:
        """LOG_FILE 应位于 CONFIG_DIR 目录下（与其他配置文件集中管理）。"""
        from core.constants import CONFIG_DIR, LOG_FILE

        assert os.path.dirname(LOG_FILE) == CONFIG_DIR
