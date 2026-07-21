"""
D3 测试：日志文件落盘配置

测试 setup_logger() 在传入 log_file 时的行为：文件创建、权限限制、日志写入。
"""

import os

import pytest
from loguru import logger


class TestSetupLoggerFileLogging:
    """setup_logger() 文件日志功能测试"""

    def test_log_file_created(self, tmp_path):
        """传入 log_file 后日志文件应被创建"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="INFO")

        logger.info("test message for file")

        assert os.path.exists(log_file)

    def test_log_message_written_to_file(self, tmp_path):
        """日志消息应被写入文件"""
        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="DEBUG")

        logger.info("unique marker message 12345")

        # 强制 flush
        logger.complete()

        with open(log_file, encoding="utf-8") as f:
            content = f.read()
        assert "unique marker message 12345" in content

    def test_log_file_directory_auto_created(self, tmp_path):
        """日志目录不存在时应自动创建"""
        from utils.logger import setup_logger

        log_dir = tmp_path / "logs" / "subdir"
        log_file = str(log_dir / "app.log")

        assert not log_dir.exists()

        setup_logger(log_file=log_file, level="INFO")

        assert log_dir.exists()

    def test_log_file_permissions_restricted_posix(self, tmp_path):
        """POSIX 上日志文件权限应为 0o600"""
        if os.name != "posix":
            pytest.skip("POSIX only")

        from utils.logger import setup_logger

        log_file = str(tmp_path / "app.log")
        setup_logger(log_file=log_file, level="INFO")

        logger.info("permission test")

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600

    def test_no_log_file_no_error(self, tmp_path):
        """不传 log_file 不应报错"""
        from utils.logger import setup_logger

        # 不传 log_file
        setup_logger(level="INFO")

        # 不应抛出异常
        logger.info("test without file")


class TestLogFileConstant:
    """LOG_FILE 常量定义测试"""

    def test_log_file_constant_exists(self):
        """core.constants 应导出 LOG_FILE"""
        from core.constants import LOG_FILE

        assert LOG_FILE is not None
        assert isinstance(LOG_FILE, str)
        assert LOG_FILE.endswith("qzct.log")

    def test_log_file_in_config_dir(self):
        """LOG_FILE 应在 CONFIG_DIR 下"""
        from core.constants import CONFIG_DIR, LOG_FILE

        assert os.path.dirname(LOG_FILE) == CONFIG_DIR
