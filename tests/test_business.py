"""
business.py 模块测试

测试 WiFi 连接、校园网登录、定时关机等功能。
"""
import datetime
from unittest.mock import MagicMock, patch

import pytest

from business import (
    campus_login,
    cancel_shutdown,
    create_windows_wifi_profile,
    is_wifi_connected,
    parse_jsonp,
    set_shutdown_timer,
    task_campus_login,
    task_check_condition,
    task_connect_wifi,
    task_set_shutdown,
)
from concurrency import TaskContext


class TestShutdownFunctions:
    """关机功能测试"""

    def test_cancel_shutdown(self, mock_subprocess):
        """测试取消关机"""
        cancel_shutdown()
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "shutdown" in call_args[0][0]
        assert "/a" in call_args[0][0]

    def test_set_shutdown_timer(self, mock_subprocess):
        """测试设置定时关机"""
        set_shutdown_timer(3600)
        assert mock_subprocess.call_count >= 1


class TestWiFiFunctions:
    """WiFi 功能测试"""

    def test_is_wifi_connected_true(self, mock_subprocess):
        """测试 WiFi 已连接"""
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=b"MyWiFi\n  SSID: MyWiFi\n  State: connected",
        )

        with patch("subprocess.check_output", return_value=b"MyWiFi\nSSID: MyWiFi"):
            result = is_wifi_connected("MyWiFi")
            assert result is True

    def test_is_wifi_connected_false(self, mock_subprocess):
        """测试 WiFi 未连接"""
        with patch(
            "subprocess.check_output",
            return_value=b"OtherWiFi\nSSID: OtherWiFi",
        ):
            result = is_wifi_connected("MyWiFi")
            assert result is False

    def test_create_windows_wifi_profile(self):
        """测试创建 WiFi 配置文件"""
        profile = create_windows_wifi_profile("TestWiFi", "password123")

        assert "TestWiFi" in profile
        assert "WPA2PSK" in profile
        assert "AES" in profile
        assert "<?xml" in profile

    def test_create_windows_wifi_profile_escapes_special_chars(self):
        """测试 WiFi 配置文件转义特殊字符"""
        profile = create_windows_wifi_profile("Test&WiFi", "pass<word>")

        assert "&amp;" in profile or "Test&WiFi" in profile
        assert "&lt;" in profile or "&gt;" in profile


class TestCampusLogin:
    """校园网登录测试"""

    def test_parse_jsonp_success(self):
        """测试解析 JSONP 响应"""
        jsonp_response = 'dr1004({"ret_code": 0, "msg": "success"})'
        result = parse_jsonp(jsonp_response, "dr1004")

        assert result["ret_code"] == 0
        assert result["msg"] == "success"

    def test_parse_jsonp_with_complex_data(self):
        """测试解析复杂 JSONP 响应"""
        jsonp_response = 'callback({"result": 1, "data": {"user": "test"}})'
        result = parse_jsonp(jsonp_response, "callback")

        assert result["result"] == 1
        assert result["data"]["user"] == "test"

    def test_parse_jsonp_invalid_format(self):
        """测试解析无效 JSONP 格式"""
        invalid_response = "not a valid jsonp response"

        with pytest.raises(ValueError):
            parse_jsonp(invalid_response, "dr1004")

    def test_campus_login_success(self, sample_config, mock_requests):
        """测试校园网登录成功"""
        import system_core

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        with patch("business.get_config_snapshot", return_value=sample_config):
            result = campus_login(sample_config)
            assert isinstance(result, bool)


class TestTaskFunctions:
    """任务函数测试"""

    def test_task_check_condition_weekday(self, sample_config):
        """测试工作日检查条件"""
        import system_core

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        ctx = TaskContext("test")
        monday = datetime.date(2026, 1, 5)

        result = task_check_condition(ctx, monday)

        assert result["need_work"] is True
        assert result["date"] == monday

    def test_task_check_condition_weekend(self, sample_config):
        """测试周末检查条件"""
        import system_core

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        ctx = TaskContext("test")
        saturday = datetime.date(2026, 1, 3)

        result = task_check_condition(ctx, saturday)

        assert result["need_work"] is False

    def test_task_connect_wifi(self, sample_config):
        """测试 WiFi 连接任务"""
        import system_core

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("business.auto_connect_wifi", return_value=True):
            result = task_connect_wifi(ctx)
            assert result["wifi_connected"] is True

    def test_task_campus_login(self, sample_config):
        """测试校园网登录任务"""
        import system_core

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("business.campus_login", return_value=True):
            result = task_campus_login(ctx)
            assert result["login_successful"] is True

    def test_task_set_shutdown(self, sample_config):
        """测试设置关机任务"""
        import system_core

        config = sample_config.copy()
        config["SHUTDOWN_HOUR"] = 23
        config["SHUTDOWN_MIN"] = 0
        system_core.global_config.clear()
        system_core.global_config.update(config)

        ctx = TaskContext("test")

        with patch("business.set_shutdown_timer"):
            with patch("business.get_config_snapshot", return_value=config):
                now = datetime.datetime.now()
                future_date = (now + datetime.timedelta(hours=1)).date()
                result = task_set_shutdown(ctx, future_date)

                assert "shutdown_set" in result


class TestSanitize:
    """日志脱敏测试"""

    def test_sanitize_password(self):
        """测试密码脱敏"""
        from business import _sanitize

        log = "user_password=secret123&username=test"
        result = _sanitize(log)

        assert "secret123" not in result
        assert "user_password=***" in result

    def test_sanitize_no_password(self):
        """测试无密码日志"""
        from business import _sanitize

        log = "username=test&action=login"
        result = _sanitize(log)

        assert result == log
