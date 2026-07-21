"""
Pytest 配置文件

提供测试夹具和通用配置。
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_config() -> dict:
    """提供示例配置字典"""
    return {
        "WIFI_NAME": "TestWiFi",
        "WIFI_PASSWORD": "test_password",
        "MAX_WIFI_RETRY": 3,
        "RETRY_INTERVAL": 2,
        "USERNAME": "test_user",
        "PASSWORD": "test_pass",
        "ISP_TYPE": "telecom",
        "WAN_IP": "192.168.1.100",
        "SHUTDOWN_HOUR": 23,
        "SHUTDOWN_MIN": 0,
        "AUTOSTART": False,
        "SHOW_LUNAR_CALENDAR": True,
        "HOLIDAY_PERIODS": [{"name": "测试假期", "start": "2026-01-01", "end": "2026-01-03"}],
        "COMPENSATORY_WORKDAYS": ["2026-01-04"],
        "DATE_RULES": {
            "ENABLE_CUSTOM_RULE": False,
            "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
            "CUSTOM_HOLIDAY_PERIODS": [],
            "CUSTOM_WORKDAY_PERIODS": [],
        },
    }


@pytest.fixture(autouse=True)
def reset_global_config():
    """每个测试前后重置全局配置状态（含 current_derived_key）"""
    import core.config as cfg_module
    from core.config import global_config

    original_config = global_config.snapshot()
    original_key = cfg_module.current_derived_key
    yield
    global_config.replace_all(original_config)
    cfg_module.current_derived_key = original_key


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for system commands"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        yield mock_run


@pytest.fixture
def mock_requests():
    """Mock requests for network operations"""
    with patch("requests.Session") as mock_session:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'dr1004({"ret_code": 0, "msg": "success"})'
        mock_instance.get.return_value = mock_response
        mock_instance.post.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_session.return_value = mock_instance
        yield mock_instance
