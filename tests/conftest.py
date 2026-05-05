"""
Pytest 配置文件

提供测试夹具和通用配置。
"""
import os
import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_qapplication():
    """Mock QApplication for tests that don't need real GUI"""
    with patch("PyQt5.QtWidgets.QApplication"):
        yield MagicMock()


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
        "HOLIDAY_PERIODS": [
            {"name": "测试假期", "start": "2026-01-01", "end": "2026-01-03"}
        ],
        "COMPENSATORY_WORKDAYS": ["2026-01-04"],
        "DATE_RULES": {
            "ENABLE_CUSTOM_RULE": False,
            "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
            "CUSTOM_HOLIDAY_PERIODS": [],
            "CUSTOM_WORKDAY_PERIODS": [],
        },
    }


@pytest.fixture
def sample_holiday_periods() -> list:
    """提供示例节假日期间"""
    return [
        {"name": "元旦", "start": "2026-01-01", "end": "2026-01-03"},
        {"name": "春节", "start": "2026-02-15", "end": "2026-02-23"},
    ]


@pytest.fixture
def sample_compensatory_workdays() -> list:
    """提供示例调休上班日"""
    return ["2026-01-04", "2026-02-14"]


@pytest.fixture(autouse=True)
def reset_global_config():
    """每个测试前后重置全局配置状态"""
    import system_core

    original_config = system_core.global_config.copy()
    yield
    system_core.global_config.clear()
    system_core.global_config.update(original_config)


@pytest.fixture
def temp_config_dir(tmp_path) -> Generator[str, None, None]:
    """创建临时配置目录"""
    config_dir = tmp_path / ".qzct"
    config_dir.mkdir()
    yield str(config_dir)


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
        mock_session.return_value = mock_instance
        yield mock_instance
