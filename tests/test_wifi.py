"""
services/wifi.py 补充测试

覆盖 _wifi_profile_exists, _do_connect_wifi, connect_wifi, auto_connect_wifi 等函数。
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from core.exceptions import WiFiConnectionError, WiFiProfileError
from services.wifi import (
    _do_connect_wifi,
    _wifi_profile_exists,
    auto_connect_wifi,
    connect_wifi,
    create_windows_wifi_profile,
    is_wifi_connected,
)


class TestIsWifiConnected:
    """is_wifi_connected 测试"""

    def test_already_connected(self):
        """WiFi 已连接时返回 True"""
        with patch("subprocess.check_output", return_value="SSID: MyWiFi\n"):
            assert is_wifi_connected("MyWiFi") is True

    def test_not_connected(self):
        """WiFi 未连接时返回 False"""
        with patch("subprocess.check_output", return_value="SSID: OtherNet\n"):
            assert is_wifi_connected("MyWiFi") is False

    def test_called_process_error_returns_false(self):
        """netsh 异常时返回 False"""
        with patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "netsh")
        ):
            assert is_wifi_connected("MyWiFi") is False


class TestCreateWifiProfile:
    """create_windows_wifi_profile 测试"""

    def test_contains_ssid_and_password(self):
        profile = create_windows_wifi_profile("TestNet", "pass123")
        assert "TestNet" in profile
        assert "pass123" in profile
        assert "WPA2PSK" in profile
        assert "AES" in profile

    def test_escapes_special_characters(self):
        """XML 特殊字符被正确转义（xml.sax.saxutils.escape 转义 & < >）"""
        profile = create_windows_wifi_profile("Test&Net<", "pass>word")
        assert "&amp;" in profile
        assert "&lt;" in profile
        assert "&gt;" in profile

    def test_empty_ssid(self):
        """空 SSID 仍生成合法 XML"""
        profile = create_windows_wifi_profile("", "")
        assert "<name></name>" in profile


class TestWifiProfileExists:
    """_wifi_profile_exists 测试"""

    def test_profile_exists(self):
        with patch("subprocess.check_output", return_value="    All User Profile: MyWiFi\n"):
            assert _wifi_profile_exists("MyWiFi") is True

    def test_profile_not_exists(self):
        with patch("subprocess.check_output", return_value="    All User Profile: OtherNet\n"):
            assert _wifi_profile_exists("MyWiFi") is False

    def test_called_process_error(self):
        with patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "netsh")
        ):
            assert _wifi_profile_exists("MyWiFi") is False


class TestDoConnectWifi:
    """_do_connect_wifi 测试"""

    def test_connect_with_existing_profile(self):
        """已有 profile 时直接连接"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=True),
            patch("services.wifi.subprocess.run") as mock_run,
            patch("services.wifi.time.sleep"),
            patch("services.wifi.is_wifi_connected", return_value=True),
        ):
            _do_connect_wifi("MyWiFi", "password")
            # 应该调用 netsh wlan connect
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "connect" in call_args

    def test_connect_creates_new_profile(self):
        """没有 profile 时创建新 profile"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=False),
            patch("services.wifi.subprocess.run") as mock_run,
            patch("services.wifi.time.sleep"),
            patch("services.wifi.is_wifi_connected", return_value=True),
            patch("services.wifi.os.close"),
            patch("services.wifi.os.unlink"),
            patch("services.wifi.os.path.exists", return_value=True),
            patch("builtins.open", new_callable=MagicMock),
            patch("services.wifi.tempfile.mkstemp", return_value=(123, "/tmp/test.xml")),
        ):
            _do_connect_wifi("MyWiFi", "password")
            # 应该先 add profile 再 connect
            assert mock_run.call_count >= 2

    def test_connect_profile_error(self):
        """profile 加载失败时抛出 WiFiProfileError"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=False),
            patch("services.wifi.subprocess.run") as mock_run,
            patch("services.wifi.os.close"),
            patch("services.wifi.os.unlink"),
            patch("services.wifi.os.path.exists", return_value=True),
            patch("builtins.open", new_callable=MagicMock),
            patch("services.wifi.tempfile.mkstemp", return_value=(123, "/tmp/test.xml")),
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "netsh")
            with pytest.raises(WiFiProfileError):
                _do_connect_wifi("MyWiFi", "password")

    def test_connect_timeout_raises_connection_error(self):
        """连接后验证失败时抛出 WiFiConnectionError"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=True),
            patch("services.wifi.subprocess.run"),
            patch("services.wifi.time.sleep"),
            patch("services.wifi.is_wifi_connected", return_value=False),
            pytest.raises(WiFiConnectionError),
        ):
            _do_connect_wifi("MyWiFi", "password")

    def test_connect_cleanup_on_error(self):
        """profile 加载失败时仍清理临时文件"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=False),
            patch("services.wifi.subprocess.run") as mock_run,
            patch("services.wifi.os.close"),
            patch("services.wifi.os.unlink") as mock_unlink,
            patch("services.wifi.os.path.exists", return_value=True),
            patch("builtins.open", new_callable=MagicMock),
            patch("services.wifi.tempfile.mkstemp", return_value=(123, "/tmp/test.xml")),
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "netsh")
            with pytest.raises(WiFiProfileError):
                _do_connect_wifi("MyWiFi", "password")
            mock_unlink.assert_called_once_with("/tmp/test.xml")


class TestConnectWifi:
    """connect_wifi 包装函数测试"""

    def test_connect_success(self):
        """连接成功返回 True"""
        with patch("services.wifi._do_connect_wifi"):
            assert connect_wifi("MyWiFi", "password") is True

    def test_connect_profile_error_returns_false(self):
        """WiFiProfileError 时返回 False"""
        with patch("services.wifi._do_connect_wifi", side_effect=WiFiProfileError("err", "detail")):
            assert connect_wifi("MyWiFi", "password") is False

    def test_connect_connection_error_returns_false(self):
        """WiFiConnectionError 时返回 False"""
        with patch(
            "services.wifi._do_connect_wifi",
            side_effect=WiFiConnectionError("err"),
        ):
            assert connect_wifi("MyWiFi", "password") is False

    def test_connect_generic_exception_returns_false(self):
        """其他异常时返回 False"""
        with patch("services.wifi._do_connect_wifi", side_effect=RuntimeError("unexpected")):
            assert connect_wifi("MyWiFi", "password") is False


class TestAutoConnectWifi:
    """auto_connect_wifi 测试"""

    def test_already_connected(self):
        """已连接时直接返回 True"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 1,
        }
        with patch("services.wifi.is_wifi_connected", return_value=True):
            assert auto_connect_wifi(cfg) is True

    def test_connects_on_first_try(self):
        """首次连接成功"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 1,
        }
        with (
            patch("services.wifi.is_wifi_connected", side_effect=[False, True]),
            patch("services.wifi.connect_wifi", return_value=True),
        ):
            assert auto_connect_wifi(cfg) is True

    def test_retries_until_max(self):
        """重试到最大次数后返回 False"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 2,
            "RETRY_INTERVAL": 1,
        }
        with (
            patch("services.wifi.is_wifi_connected", return_value=False),
            patch("services.wifi.connect_wifi", return_value=False),
            patch("services.wifi.time.sleep"),
        ):
            assert auto_connect_wifi(cfg) is False

    def test_uses_config_snapshot_when_none(self):
        """cfg=None 时从 get_config_snapshot 获取"""
        with (
            patch(
                "services.wifi.get_config_snapshot",
                return_value={
                    "WIFI_NAME": "Auto",
                    "WIFI_PASSWORD": "p",
                    "MAX_WIFI_RETRY": 1,
                    "RETRY_INTERVAL": 1,
                },
            ),
            patch("services.wifi.is_wifi_connected", return_value=True),
        ):
            assert auto_connect_wifi(None) is True

    def test_exponential_backoff(self):
        """验证指数退避延迟"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 2,
        }
        sleep_calls = []
        with (
            patch("services.wifi.is_wifi_connected", return_value=False),
            patch("services.wifi.connect_wifi", return_value=False),
            patch("services.wifi.time.sleep", side_effect=lambda s: sleep_calls.append(s)),
        ):
            auto_connect_wifi(cfg)
        # 第1次重试后 sleep 2s, 第2次后 sleep 4s
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 2
        assert sleep_calls[1] == 4
