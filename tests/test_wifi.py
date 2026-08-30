"""
services/wifi.py 补充测试

覆盖 is_wifi_connected、create_windows_wifi_profile、_wifi_profile_exists、
_do_connect_wifi（含临时 profile 文件的创建/清理与异常路径）、connect_wifi
异常包装，以及 auto_connect_wifi 的重试/指数退避/取消（should_cancel）逻辑。
所有 subprocess 调用、time.sleep 与临时文件操作均被 patch，纯离线运行。
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
    """is_wifi_connected 测试：基于 netsh 输出的连接状态判断。"""

    def test_already_connected(self):
        """netsh 输出包含目标 SSID 时应判定已连接并返回 True。"""
        with patch("subprocess.check_output", return_value="SSID: MyWiFi\n"):
            assert is_wifi_connected("MyWiFi") is True

    def test_not_connected(self):
        """当前连接的是其他 SSID 时应返回 False。"""
        with patch("subprocess.check_output", return_value="SSID: OtherNet\n"):
            assert is_wifi_connected("MyWiFi") is False

    def test_called_process_error_returns_false(self):
        """netsh 命令执行失败时应返回 False 而非抛异常。"""
        with patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "netsh")
        ):
            assert is_wifi_connected("MyWiFi") is False


class TestCreateWifiProfile:
    """create_windows_wifi_profile 测试：WLAN profile XML 模板生成。"""

    def test_contains_ssid_and_password(self):
        """生成的 XML 应包含 SSID、密码及 WPA2PSK/AES 加密参数。"""
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
        """空 SSID 仍生成合法 XML（空 <name> 标签而非崩溃）。"""
        profile = create_windows_wifi_profile("", "")
        assert "<name></name>" in profile


class TestWifiProfileExists:
    """_wifi_profile_exists 测试：检查系统是否已保存指定 WiFi profile。"""

    def test_profile_exists(self):
        """netsh profile 列表包含目标 SSID 时应返回 True。"""
        with patch("subprocess.check_output", return_value="    All User Profile: MyWiFi\n"):
            assert _wifi_profile_exists("MyWiFi") is True

    def test_profile_not_exists(self):
        """profile 列表中无目标 SSID 时应返回 False。"""
        with patch("subprocess.check_output", return_value="    All User Profile: OtherNet\n"):
            assert _wifi_profile_exists("MyWiFi") is False

    def test_called_process_error(self):
        """netsh 执行失败时应返回 False 而非抛异常。"""
        with patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "netsh")
        ):
            assert _wifi_profile_exists("MyWiFi") is False


class TestDoConnectWifi:
    """_do_connect_wifi 测试：连接主流程、临时 profile 生命周期与异常路径。"""

    def test_connect_with_existing_profile(self):
        """系统已有 profile 时应跳过创建，直接 netsh wlan connect。"""
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
        """无已有 profile 时应先 add profile 再 connect（两次 netsh 调用）。"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=False),
            patch("services.wifi.subprocess.run") as mock_run,
            patch("services.wifi.time.sleep"),
            patch("services.wifi.is_wifi_connected", return_value=True),
            patch("services.wifi.os.close"),
            patch("services.wifi.os.unlink"),
            patch("services.wifi.os.path.exists", return_value=True),
            patch("builtins.open", new_callable=MagicMock),
            # mkstemp 打桩到固定的 /tmp/test.xml，避免真实磁盘写入
            patch("services.wifi.tempfile.mkstemp", return_value=(123, "/tmp/test.xml")),
        ):
            _do_connect_wifi("MyWiFi", "password")
            # 应该先 add profile 再 connect
            assert mock_run.call_count >= 2

    def test_connect_profile_error(self):
        """netsh add profile 失败时应抛出 WiFiProfileError。"""
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
        """connect 命令成功但始终验证不到连接时应抛出 WiFiConnectionError。"""
        with (
            patch("services.wifi._wifi_profile_exists", return_value=True),
            patch("services.wifi.subprocess.run"),
            patch("services.wifi.time.sleep"),
            patch("services.wifi.is_wifi_connected", return_value=False),
            pytest.raises(WiFiConnectionError),
        ):
            _do_connect_wifi("MyWiFi", "password")

    def test_connect_cleanup_on_error(self):
        """profile 加载失败抛异常前仍应删除临时 XML 文件。"""
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
    """connect_wifi 包装函数测试：把底层异常统一转成 False 返回值。"""

    def test_connect_success(self):
        """底层连接成功时应返回 True。"""
        with patch("services.wifi._do_connect_wifi"):
            assert connect_wifi("MyWiFi", "password") is True

    def test_connect_profile_error_returns_false(self):
        """WiFiProfileError 时应捕获并返回 False。"""
        with patch("services.wifi._do_connect_wifi", side_effect=WiFiProfileError("err", "detail")):
            assert connect_wifi("MyWiFi", "password") is False

    def test_connect_connection_error_returns_false(self):
        """WiFiConnectionError 时应捕获并返回 False。"""
        with patch(
            "services.wifi._do_connect_wifi",
            side_effect=WiFiConnectionError("err"),
        ):
            assert connect_wifi("MyWiFi", "password") is False

    def test_connect_generic_exception_returns_false(self):
        """其他未预期异常也应被兜底捕获并返回 False。"""
        with patch("services.wifi._do_connect_wifi", side_effect=RuntimeError("unexpected")):
            assert connect_wifi("MyWiFi", "password") is False


class TestAutoConnectWifi:
    """auto_connect_wifi 测试：重试循环、指数退避与取消协作。"""

    def test_already_connected(self):
        """启动时已连接目标 WiFi 时应直接返回 True，不触发连接流程。"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 1,
        }
        with patch("services.wifi.is_wifi_connected", return_value=True):
            assert auto_connect_wifi(cfg) is True

    def test_connects_on_first_try(self):
        """首次未连接但 connect_wifi 成功后，复查应转为已连接并返回 True。"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 1,
        }
        # side_effect=[False, True] 模拟"先未连接、connect 后已连接"的序列
        with (
            patch("services.wifi.is_wifi_connected", side_effect=[False, True]),
            patch("services.wifi.connect_wifi", return_value=True),
        ):
            assert auto_connect_wifi(cfg) is True

    def test_retries_until_max(self):
        """持续连接失败时应重试到 MAX_WIFI_RETRY 次后返回 False。"""
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
        """cfg=None 时应改从 get_config_snapshot 读取 WiFi 配置。"""
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
        """验证指数退避延迟：RETRY_INTERVAL=2 时各次 sleep 应为 2s、4s。"""
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

    def test_cancelled_before_first_attempt(self):
        """取消标志置位时立即返回 False，不发起任何连接（回归 C4）"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 3,
            "RETRY_INTERVAL": 1,
        }
        with (
            patch("services.wifi.is_wifi_connected", return_value=False) as mock_conn,
            patch("services.wifi.connect_wifi") as mock_connect,
        ):
            assert auto_connect_wifi(cfg, should_cancel=lambda: True) is False
            mock_conn.assert_not_called()
            mock_connect.assert_not_called()

    def test_cancelled_during_backoff_sleep(self):
        """退避睡眠期间取消时提前退出（回归 C4）"""
        cfg = {
            "WIFI_NAME": "MyWiFi",
            "WIFI_PASSWORD": "pass",
            "MAX_WIFI_RETRY": 5,
            "RETRY_INTERVAL": 1,
        }
        cancel_flag = {"cancelled": False}
        with (
            patch("services.wifi.is_wifi_connected", return_value=False),
            patch("services.wifi.connect_wifi", return_value=False),
            patch("services.wifi.time.sleep") as mock_sleep,
        ):

            def fake_sleep(seconds):
                # 第一次睡眠时模拟外部取消
                cancel_flag["cancelled"] = True

            mock_sleep.side_effect = fake_sleep
            result = auto_connect_wifi(cfg, should_cancel=lambda: cancel_flag["cancelled"])
            assert result is False

    def test_empty_wifi_name_skips_retry_loop(self):
        """WIFI_NAME 为空时应直接返回 False，不进入重试循环（有线用户免拖慢任务链）。"""
        cfg = {
            "WIFI_NAME": "",
            "WIFI_PASSWORD": "",
            "MAX_WIFI_RETRY": 10,
            "RETRY_INTERVAL": 5,
        }
        with (
            patch("services.wifi.is_wifi_connected") as mock_conn,
            patch("services.wifi.connect_wifi") as mock_connect,
            patch("services.wifi.time.sleep") as mock_sleep,
        ):
            assert auto_connect_wifi(cfg) is False
            mock_conn.assert_not_called()
            mock_connect.assert_not_called()
            mock_sleep.assert_not_called()
