"""
services 包模块测试

测试定时关机（shutdown）、WiFi 连接（wifi）、校园网 JSONP 认证（campus_login）、
四步任务链中的任务函数（tasks）以及日志脱敏。
通过 mock_subprocess / mock_requests fixture（conftest 提供）与
patch 服务函数，隔离系统命令和真实网络请求。
"""

import datetime
import importlib
from typing import Any
from unittest.mock import MagicMock, patch

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
    """关机功能测试：shutdown 命令的取消与定时设置。"""

    def test_cancel_shutdown(self, mock_subprocess: MagicMock) -> None:
        """取消关机应调用 shutdown /a 命令中止已计划的关机。"""
        cancel_shutdown()
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "shutdown" in call_args[0][0]
        assert "/a" in call_args[0][0]

    def test_set_shutdown_timer(self, mock_subprocess: MagicMock) -> None:
        """设置 3600 秒定时关机应至少调用一次 shutdown 命令。"""
        set_shutdown_timer(3600)
        assert mock_subprocess.call_count >= 1

    def test_cancel_shutdown_timeout_returns_false(self) -> None:
        """shutdown 命令超时应捕获异常并返回 False，而不是抛给调用方。"""
        import subprocess as sp

        with patch(
            "subprocess.run",
            side_effect=sp.TimeoutExpired(cmd="shutdown", timeout=10),
        ):
            assert cancel_shutdown() is False

    def test_set_shutdown_timer_timeout_returns_false(self) -> None:
        """设置关机时命令超时应捕获异常并返回 False。"""
        import subprocess as sp

        with patch(
            "subprocess.run",
            side_effect=sp.TimeoutExpired(cmd="shutdown", timeout=10),
        ):
            assert set_shutdown_timer(60) is False


class TestWiFiFunctions:
    """WiFi 功能测试：连接状态检测与 profile XML 生成。"""

    def test_is_wifi_connected_true(self, mock_subprocess: MagicMock) -> None:
        """netsh 输出包含目标 SSID 时应判定为已连接。"""
        # 业务代码使用 check_output(encoding='gbk')，因此返回 str，不是 bytes
        with patch("subprocess.check_output", return_value="MyWiFi\nSSID: MyWiFi"):
            result = is_wifi_connected("MyWiFi")
            assert result is True

    def test_is_wifi_connected_false(self, mock_subprocess: MagicMock) -> None:
        """netsh 输出的 SSID 与目标不一致时应判定为未连接。"""
        with patch(
            "subprocess.check_output",
            return_value="OtherWiFi\nSSID: OtherWiFi",
        ):
            result = is_wifi_connected("MyWiFi")
            assert result is False

    def test_create_windows_wifi_profile(self) -> None:
        """生成的 profile XML 应包含 SSID、WPA2PSK/AES 加密与 XML 声明。"""
        profile = create_windows_wifi_profile("TestWiFi", "password123")

        assert "TestWiFi" in profile
        assert "WPA2PSK" in profile
        assert "AES" in profile
        assert "<?xml" in profile

    def test_create_windows_wifi_profile_escapes_special_chars(self) -> None:
        """SSID/密码中的 XML 特殊字符（& < >）应被转义或原样保留为合法 XML。"""
        profile = create_windows_wifi_profile("Test&WiFi", "pass<word>")

        assert "&amp;" in profile or "Test&WiFi" in profile
        assert "&lt;" in profile or "&gt;" in profile


class TestCampusLogin:
    """校园网登录测试：JSONP 解析与登录请求链路（网络已 mock）。"""

    def test_parse_jsonp_success(self) -> None:
        """标准 dr1004 JSONP 响应应解析出 ret_code/msg 字段。"""
        jsonp_response = 'dr1004({"ret_code": 0, "msg": "success"})'
        result = parse_jsonp(jsonp_response, "dr1004")

        assert result["ret_code"] == 0
        assert result["msg"] == "success"

    def test_parse_jsonp_with_complex_data(self) -> None:
        """含嵌套结构的 JSONP 响应应完整解析。"""
        jsonp_response = 'callback({"result": 1, "data": {"user": "test"}})'
        result = parse_jsonp(jsonp_response, "callback")

        assert result["result"] == 1
        assert result["data"]["user"] == "test"

    def test_parse_jsonp_invalid_format(self) -> None:
        """非 JSONP 格式的响应应抛出 JSONPParseError。"""
        from core.exceptions import JSONPParseError

        invalid_response = "not a valid jsonp response"

        with pytest.raises(JSONPParseError):
            parse_jsonp(invalid_response, "dr1004")

    def test_campus_login_success(
        self, sample_config: dict[str, Any], mock_requests: MagicMock
    ) -> None:
        """认证服务器返回 ret_code=0（mock_requests 默认值）时登录应成功。"""
        global_config.clear()
        global_config.update(sample_config)

        # patch 快照函数，保证登录流程读取到测试配置而非真实配置。
        # 用 patch.object 而非 "services.campus_login.X" 字符串目标：
        # services/__init__.py 的 `from services.campus_login import campus_login`
        # 会把包属性 campus_login 遮蔽成同名函数，Python 3.10–3.13 的 mock
        # 用 getattr 逐段解析目标，会取到函数而非模块（3.14 改用 importlib
        # 解析才不暴露该问题），故显式取模块对象。
        campus_login_module = importlib.import_module("services.campus_login")
        with patch.object(campus_login_module, "get_config_snapshot", return_value=sample_config):
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
    """任务函数测试：tasks.py 中供 TaskChain 编排的单步任务。"""

    def test_task_check_condition_weekday(self, sample_config: dict[str, Any]) -> None:
        """工作日（周一 2026-01-05）检查条件应返回 need_work=True。"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")
        monday = datetime.date(2026, 1, 5)

        result = task_check_condition(ctx, monday)

        assert result["need_work"] is True
        assert result["date"] == monday

    def test_task_check_condition_weekend(self, sample_config: dict[str, Any]) -> None:
        """周末（周六 2026-01-03）检查条件应返回 need_work=False。"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")
        saturday = datetime.date(2026, 1, 3)

        result = task_check_condition(ctx, saturday)

        assert result["need_work"] is False

    def test_task_connect_wifi(self, sample_config: dict[str, Any]) -> None:
        """WiFi 连接任务（auto_connect_wifi 已 mock 成功）应返回 wifi_connected=True。"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("services.tasks.auto_connect_wifi", return_value=True):
            result = task_connect_wifi(ctx)
            assert result["wifi_connected"] is True

    def test_task_campus_login(self, sample_config: dict[str, Any]) -> None:
        """登录任务（campus_login 已 mock 成功）应返回 login_successful=True。"""
        global_config.clear()
        global_config.update(sample_config)

        ctx = TaskContext("test")

        with patch("services.tasks.campus_login", return_value=True):
            result = task_campus_login(ctx)
            assert result["login_successful"] is True

    def test_task_set_shutdown(self, sample_config: dict[str, Any]) -> None:
        """设置关机任务（定时器已 mock）应返回含 shutdown_set 键的结果。"""
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
            # 用未来一天的日期保证计算出的关机时刻有效
            now = datetime.datetime.now()
            future_date = (now + datetime.timedelta(hours=1)).date()
            result = task_set_shutdown(ctx, future_date)

            assert "shutdown_set" in result


class TestSanitize:
    """日志脱敏测试：_sanitize 防止密码明文进入日志。"""

    def test_sanitize_password(self) -> None:
        """日志中的密码字段应被替换为 ***，用户名等信息保留。"""
        from services.campus_login import _sanitize

        log = "user_password=secret123&username=test"
        result = _sanitize(log)

        assert "secret123" not in result
        assert "user_password=***" in result

    def test_sanitize_no_password(self) -> None:
        """不含密码字段的日志应原样返回。"""
        from services.campus_login import _sanitize

        log = "username=test&action=login"
        result = _sanitize(log)

        assert result == log


class TestParseJsonpParametrized:
    """JSONP 解析参数化测试：合法/非法响应的批量边界覆盖。"""

    @pytest.mark.parametrize(
        "jsonp_text,expected",
        [
            ('dr1004({"ret_code": 0, "msg": "success"})', {"ret_code": 0, "msg": "success"}),
            ('dr1004({"result": 1, "data": "test"})', {"result": 1, "data": "test"}),
            ("dr1004({})", {}),
            ('dr1004({"nested": {"key": "value"}}) ', {"nested": {"key": "value"}}),
        ],
    )
    def test_parse_jsonp_valid(self, jsonp_text: str, expected: dict[str, Any]) -> None:
        """合法 JSONP 响应（含空对象/嵌套/尾部空格）应解析出预期字典。"""
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
    def test_parse_jsonp_invalid(self, jsonp_text: str) -> None:
        """非法输入（空串/残缺/回调名不匹配等）应统一抛出 JSONPParseError。"""
        from core.exceptions import JSONPParseError
        from services.campus_login import parse_jsonp

        with pytest.raises(JSONPParseError):
            parse_jsonp(jsonp_text, "dr1004")


class TestCampusLoginFailures:
    """校园网登录失败分支测试：各类失败均应捕获并返回 False（不抛异常）。"""

    def test_auth_failure_returns_false(
        self, sample_config: dict[str, Any], mock_requests: MagicMock
    ) -> None:
        """服务器返回 ret_code=1（认证失败）时应返回 False。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'dr1004({"ret_code": 1, "msg": "账号或密码错误"})'
        mock_requests.post.return_value = mock_response

        result = campus_login(sample_config)
        assert result is False

    def test_network_error_returns_false(self, sample_config: dict[str, Any]) -> None:
        """请求抛 RequestException（网络不可达）时应返回 False。"""
        from requests.exceptions import RequestException

        # 同上：经 importlib 取模块对象，避开包属性遮蔽
        campus_login_module = importlib.import_module("services.campus_login")
        with patch.object(campus_login_module.requests, "Session") as mock_session:
            mock_session.return_value.__enter__.side_effect = RequestException("unreachable")
            result = campus_login(sample_config)
        assert result is False

    def test_invalid_jsonp_returns_false(
        self, sample_config: dict[str, Any], mock_requests: MagicMock
    ) -> None:
        """响应非 JSONP 格式（解析失败）时应返回 False。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>gateway error page</html>"
        mock_requests.post.return_value = mock_response

        result = campus_login(sample_config)
        assert result is False

    def test_credentials_never_logged_in_plaintext(
        self, sample_config: dict[str, Any], mock_requests: MagicMock
    ) -> None:
        """_sanitize 应把日志中的密码字段脱敏为 ***（安全回归）。"""
        from services.campus_login import _sanitize

        raw = "post failed: user_account=secret_user&user_password=secret_pass&x=1"
        cleaned = _sanitize(raw)
        assert "secret_pass" not in cleaned
        assert "user_password=***" in cleaned


class TestTaskFailureBranches:
    """任务函数失败分支测试：失败不抛异常，以结果字典如实回报。"""

    def test_task_connect_wifi_failure(self, sample_config: dict[str, Any]) -> None:
        """auto_connect_wifi 返回 False 时结果应为 wifi_connected=False。"""
        global_config.clear()
        global_config.update(sample_config)
        ctx = TaskContext("test")

        with patch("services.tasks.auto_connect_wifi", return_value=False):
            result = task_connect_wifi(ctx)
        assert result["wifi_connected"] is False
        assert "error" in result

    def test_task_connect_wifi_not_configured(self) -> None:
        """未配置 WiFi 名称时应跳过并返回 wifi_connected=None（区别于失败）。"""
        global_config.clear()
        global_config.update({"WIFI_NAME": "", "WIFI_PASSWORD": ""})
        ctx = TaskContext("test")

        result = task_connect_wifi(ctx)
        assert result["wifi_connected"] is None
        assert result["reason"] == "not_configured"

    def test_task_campus_login_failure(self, sample_config: dict[str, Any]) -> None:
        """campus_login 返回 False 时结果应为 login_successful=False。"""
        global_config.clear()
        global_config.update(sample_config)
        ctx = TaskContext("test")

        with patch("services.tasks.campus_login", return_value=False):
            result = task_campus_login(ctx)
        assert result["login_successful"] is False

    def test_task_set_shutdown_command_failed(self, sample_config: dict[str, Any]) -> None:
        """shutdown 命令执行失败时结果应为 shutdown_set=False + command_failed。"""
        global_config.clear()
        global_config.update({**sample_config, "SHUTDOWN_HOUR": 23, "SHUTDOWN_MIN": 59})
        ctx = TaskContext("test")

        # 注入远期未来日期无意义：set_shutdown_timer 由真实 now 计算，
        # 用 23:59 保证 now < shutdown_time（除非测试恰在 23:59 运行，可接受）
        with patch("services.tasks.set_shutdown_timer", return_value=False):
            result = task_set_shutdown(ctx)
        assert result["shutdown_set"] is False
        assert result["reason"] == "command_failed"
