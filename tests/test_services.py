"""
services 包模块测试

测试 WiFi 连接、校园网登录、定时关机等功能。
"""

import datetime
from unittest.mock import patch

import pytest

from core.config import global_config
from infra.concurrency import TaskContext
from services.campus_login import campus_login, parse_jsonp
from services.shutdown import cancel_shutdown, set_shutdown_timer
from services.tasks import (
    task_campus_login,
    task_check_condition,
    task_connect_wifi,
    task_set_shutdown,
)
from services.wifi import create_windows_wifi_profile, is_wifi_connected


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
        # 业务代码使用 check_output(encoding='gbk')，因此返回 str，不是 bytes
        with patch("subprocess.check_output", return_value="MyWiFi\nSSID: MyWiFi"):
            result = is_wifi_connected("MyWiFi")
            assert result is True

    def test_is_wifi_connected_false(self, mock_subprocess):
        """测试 WiFi 未连接"""
        with patch(
            "subprocess.check_output",
            return_value="OtherWiFi\nSSID: OtherWiFi",
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
        from core.exceptions import JSONPParseError

        invalid_response = "not a valid jsonp response"

        with pytest.raises(JSONPParseError):
            parse_jsonp(invalid_response, "dr1004")

    def test_campus_login_success(self, sample_config, mock_requests):
        """测试校园网登录成功"""
        global_config.clear()
        global_config.update(sample_config)

        with patch("services.campus_login.get_config_snapshot", return_value=sample_config):
            result = campus_login(sample_config)
            assert result is True

        # 验证实际发送了 HTTP 请求
        assert mock_requests.get.called or mock_requests.post.called
        # 验证请求 URL 包含认证服务器地址
        call_args = mock_requests.get.call_args or mock_requests.post.call_args
        if call_args:
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "192.168" in str(url) or "http" in str(url)


class TestTaskFunctions:
    """任务函数测试"""

    def test_task_check_condition_weekday(self, sample_config):
        """测试工作日检查条件"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")
        monday = datetime.date(2026, 1, 5)

        result = task_check_condition(ctx, monday)

        assert result["need_work"] is True
        assert result["date"] == monday

    def test_task_check_condition_weekend(self, sample_config):
        """测试周末检查条件"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")
        saturday = datetime.date(2026, 1, 3)

        result = task_check_condition(ctx, saturday)

        assert result["need_work"] is False

    def test_task_connect_wifi(self, sample_config):
        """测试 WiFi 连接任务"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("services.tasks.auto_connect_wifi", return_value=True):
            result = task_connect_wifi(ctx)
            assert result["wifi_connected"] is True

    def test_task_campus_login(self, sample_config):
        """测试校园网登录任务"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("services.tasks.campus_login", return_value=True):
            result = task_campus_login(ctx)
            assert result["login_successful"] is True

    def test_task_set_shutdown(self, sample_config):
        """测试设置关机任务"""
        config = sample_config.copy()
        config["SHUTDOWN_HOUR"] = 23
        config["SHUTDOWN_MIN"] = 0
        global_config.clear()
        global_config.update(config)

        ctx = TaskContext("test")

        with (
            patch("services.tasks.set_shutdown_timer"),
            patch("services.tasks.get_config_snapshot", return_value=config),
        ):
            now = datetime.datetime.now()
            future_date = (now + datetime.timedelta(hours=1)).date()
            result = task_set_shutdown(ctx, future_date)

            assert "shutdown_set" in result


class TestSanitize:
    """日志脱敏测试"""

    def test_sanitize_password(self):
        """测试密码脱敏"""
        from services.campus_login import _sanitize

        log = "user_password=secret123&username=test"
        result = _sanitize(log)

        assert "secret123" not in result
        assert "user_password=***" in result

    def test_sanitize_no_password(self):
        """测试无密码日志"""
        from services.campus_login import _sanitize

        log = "username=test&action=login"
        result = _sanitize(log)

        assert result == log


class TestParseJsonpParametrized:
    """JSONP 解析参数化测试"""

    @pytest.mark.parametrize(
        "jsonp_text,expected",
        [
            ('dr1004({"ret_code": 0, "msg": "success"})', {"ret_code": 0, "msg": "success"}),
            ('dr1004({"result": 1, "data": "test"})', {"result": 1, "data": "test"}),
            ("dr1004({})", {}),
            ('dr1004({"nested": {"key": "value"}}) ', {"nested": {"key": "value"}}),
        ],
    )
    def test_parse_jsonp_valid(self, jsonp_text, expected):
        from services.campus_login import parse_jsonp

        assert parse_jsonp(jsonp_text, "dr1004") == expected

    @pytest.mark.parametrize(
        "jsonp_text",
        [
            "",
            "not a jsonp",
            "dr1004(",
            "dr1004()",
            "dr1004(invalid json)",
            'wrong_callback({"key": "value"})',
        ],
    )
    def test_parse_jsonp_invalid(self, jsonp_text):
        from core.exceptions import JSONPParseError
        from services.campus_login import parse_jsonp

        with pytest.raises(JSONPParseError):
            parse_jsonp(jsonp_text, "dr1004")
