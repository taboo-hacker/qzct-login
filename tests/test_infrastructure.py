"""
infrastructure.py 模块测试

测试工具函数、日志系统、线程池管理等功能。
"""
import datetime
from unittest.mock import MagicMock, patch

from infrastructure import (
    Logger,
    StreamRedirector,
    format_period,
    get_thread_pool_manager,
    init_logger,
    is_date_in_period,
    parse_date_str,
)


class TestParseDateStr:
    """日期字符串解析测试"""

    def test_parse_valid_date(self):
        """测试解析有效日期"""
        result = parse_date_str("2026-01-15")
        assert result == datetime.date(2026, 1, 15)

    def test_parse_invalid_format(self):
        """测试解析无效格式"""
        result = parse_date_str("2026/01/15")
        assert result is None

    def test_parse_invalid_date(self):
        """测试解析无效日期"""
        result = parse_date_str("2026-13-45")
        assert result is None

    def test_parse_empty_string(self):
        """测试解析空字符串"""
        result = parse_date_str("")
        assert result is None

    def test_parse_none(self):
        """测试解析 None"""
        result = parse_date_str(None)
        assert result is None


class TestIsDateInPeriod:
    """日期期间判断测试"""

    def test_date_in_period(self):
        """测试日期在期间内"""
        period = {"start": "2026-01-01", "end": "2026-01-31", "name": "测试期间"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_at_start(self):
        """测试日期在开始边界"""
        period = {"start": "2026-01-01", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 1)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_at_end(self):
        """测试日期在结束边界"""
        period = {"start": "2026-01-01", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 31)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_before_period(self):
        """测试日期在期间前"""
        period = {"start": "2026-01-10", "end": "2026-01-20"}
        check_date = datetime.date(2026, 1, 5)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_date_after_period(self):
        """测试日期在期间后"""
        period = {"start": "2026-01-10", "end": "2026-01-20"}
        check_date = datetime.date(2026, 1, 25)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_invalid_period_start(self):
        """测试无效期间开始日期"""
        period = {"start": "invalid", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_invalid_period_end(self):
        """测试无效期间结束日期"""
        period = {"start": "2026-01-01", "end": "invalid"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is False


class TestFormatPeriod:
    """期间格式化测试"""

    def test_format_period_full(self):
        """测试完整期间格式化"""
        period = {"name": "寒假", "start": "2026-01-10", "end": "2026-02-28"}
        result = format_period(period)

        assert "寒假" in result
        assert "2026-01-10" in result
        assert "2026-02-28" in result

    def test_format_period_no_name(self):
        """测试无名称期间格式化"""
        period = {"start": "2026-01-01", "end": "2026-01-31"}
        result = format_period(period)

        assert "未命名" in result


class TestLogger:
    """日志系统测试"""

    def test_logger_initialization(self):
        """测试日志初始化"""
        with patch("infrastructure.setup_logger"):
            logger = init_logger(level=1)
            assert logger is not None

    def test_logger_levels(self):
        """测试日志级别"""
        with patch("infrastructure.setup_logger") as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger

            logger = Logger(level=1)
            logger.debug("test", "debug message")
            logger.info("test", "info message")
            logger.warning("test", "warning message")
            logger.error("test", "error message")
            logger.critical("test", "critical message")

            assert mock_logger.log.call_count == 5


class TestStreamRedirector:
    """输出流重定向测试"""

    def test_write_with_content(self):
        """测试写入内容"""
        with patch("infrastructure.logger", MagicMock()):
            redirector = StreamRedirector("test", 1)
            redirector.write("test message")

    def test_write_empty(self):
        """测试写入空内容"""
        redirector = StreamRedirector("test", 1)
        redirector.write("")
        redirector.write("   ")

    def test_flush(self):
        """测试刷新"""
        redirector = StreamRedirector("test", 1)
        redirector.flush()

    def test_isatty(self):
        """测试终端判断"""
        redirector = StreamRedirector("test", 1)
        assert redirector.isatty() is False

    def test_writable(self):
        """测试可写判断"""
        redirector = StreamRedirector("test", 1)
        assert redirector.writable() is True

    def test_readable(self):
        """测试可读判断"""
        redirector = StreamRedirector("test", 1)
        assert redirector.readable() is False


class TestThreadPoolManager:
    """线程池管理测试"""

    def test_singleton(self):
        """测试单例模式"""
        manager1 = get_thread_pool_manager()
        manager2 = get_thread_pool_manager()

        assert manager1 is manager2

    def test_thread_pool_initialized(self):
        """测试线程池初始化"""
        manager = get_thread_pool_manager()

        assert manager.thread_pool is not None
        assert manager.get_max_threads() > 0

    def test_max_threads_reasonable(self):
        """测试最大线程数合理"""
        import os

        manager = get_thread_pool_manager()
        max_threads = manager.get_max_threads()
        cpu_count = os.cpu_count() or 4

        assert max_threads <= cpu_count * 4
        assert max_threads <= 16
        assert max_threads >= 1
