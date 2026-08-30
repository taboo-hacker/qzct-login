"""
infra 包模块测试

测试日期工具（parse_date_str / is_date_in_period）、
Logger 日志封装与 StreamRedirector 输出流重定向。
通过 patch infra.logging.setup_logger 与 infra.logging.logger
隔离真实日志输出。线程池管理测试已移至 test_gui.py（因依赖 PySide6）。
"""

import datetime
from unittest.mock import MagicMock, patch

from infra import (
    Logger,
    StreamRedirector,
    init_logger,
    is_date_in_period,
    parse_date_str,
)


class TestParseDateStr:
    """parse_date_str 测试：有效/无效格式、越界日期与空值输入。"""

    def test_parse_valid_date(self):
        """合法的 YYYY-MM-DD 字符串应解析为对应 date 对象。"""
        result = parse_date_str("2026-01-15")
        assert result == datetime.date(2026, 1, 15)

    def test_parse_invalid_format(self):
        """使用斜杠分隔的非法格式应返回 None。"""
        result = parse_date_str("2026/01/15")
        assert result is None

    def test_parse_invalid_date(self):
        """格式正确但数值越界的日期（13 月 45 日）应返回 None。"""
        result = parse_date_str("2026-13-45")
        assert result is None

    def test_parse_empty_string(self):
        """空字符串应返回 None。"""
        result = parse_date_str("")
        assert result is None

    def test_parse_none(self):
        """传入 None 应安全返回 None 而不抛异常。"""
        result = parse_date_str(None)
        assert result is None


class TestIsDateInPeriod:
    """is_date_in_period 测试：期间内外、起止边界及非法期间数据。"""

    def test_date_in_period(self):
        """日期落在期间中间时应返回 True。"""
        period = {"start": "2026-01-01", "end": "2026-01-31", "name": "测试期间"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_at_start(self):
        """边界值：日期等于期间起始日时应返回 True（闭区间）。"""
        period = {"start": "2026-01-01", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 1)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_at_end(self):
        """边界值：日期等于期间结束日时应返回 True（闭区间）。"""
        period = {"start": "2026-01-01", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 31)

        result = is_date_in_period(check_date, period)
        assert result is True

    def test_date_before_period(self):
        """日期早于期间起始时应返回 False。"""
        period = {"start": "2026-01-10", "end": "2026-01-20"}
        check_date = datetime.date(2026, 1, 5)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_date_after_period(self):
        """日期晚于期间结束时应返回 False。"""
        period = {"start": "2026-01-10", "end": "2026-01-20"}
        check_date = datetime.date(2026, 1, 25)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_invalid_period_start(self):
        """期间 start 字段非法时应返回 False 而不抛异常。"""
        period = {"start": "invalid", "end": "2026-01-31"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is False

    def test_invalid_period_end(self):
        """期间 end 字段非法时应返回 False 而不抛异常。"""
        period = {"start": "2026-01-01", "end": "invalid"}
        check_date = datetime.date(2026, 1, 15)

        result = is_date_in_period(check_date, period)
        assert result is False



class TestLogger:
    """Logger 封装测试：初始化与各级别日志转发。"""

    def test_logger_initialization(self):
        """init_logger 应返回非 None 的 Logger 实例（setup_logger 已打桩）。"""
        with patch("infra.logging.setup_logger"):
            logger = init_logger(level=1)
            assert logger is not None

    def test_logger_levels(self):
        """debug/info/warning/error/critical 五个级别均应转发到底层 logger.log。"""
        with patch("infra.logging.setup_logger") as mock_setup:
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
    """StreamRedirector 测试：stdout/stderr 桥接到日志系统的写接口行为。"""

    def test_write_with_content(self):
        """写入非空内容应被转发到日志（不崩溃即通过）。"""
        with patch("infra.logging.logger", MagicMock()):
            redirector = StreamRedirector("test", 1)
            redirector.write("test message")

    def test_write_empty(self):
        """写入空串或纯空白应被静默忽略（避免无意义的空日志行）。"""
        redirector = StreamRedirector("test", 1)
        redirector.write("")
        redirector.write("   ")

    def test_flush(self):
        """flush 应为空操作（日志系统自行管理刷新）。"""
        redirector = StreamRedirector("test", 1)
        redirector.flush()

    def test_isatty(self):
        """重定向流并非真实终端，isatty 应返回 False。"""
        redirector = StreamRedirector("test", 1)
        assert redirector.isatty() is False

    def test_writable(self):
        """流角色为输出，writable 应返回 True。"""
        redirector = StreamRedirector("test", 1)
        assert redirector.writable() is True

    def test_readable(self):
        """流角色为输出，readable 应返回 False。"""
        redirector = StreamRedirector("test", 1)
        assert redirector.readable() is False
