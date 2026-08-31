"""
Pytest 全局配置文件

提供所有测试文件共享的夹具（fixture）和通用配置：
- ``sample_config``: 标准示例配置字典，作为各测试的配置基线；
- ``reset_global_config``: autouse 夹具，每个测试结束后恢复 core.config.global_config
  的原始状态，避免测试间通过全局单例互相污染；
- ``mock_subprocess`` / ``mock_requests``: 分别 mock 掉 subprocess.run 和
  requests.Session，隔离系统命令与网络请求等外部依赖。
"""

import os
import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

# 将项目根目录加入 sys.path，使测试可直接以顶层包名导入 core/infra/gui 等模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ensure_qapp() -> QApplication:
    """共享辅助函数：确保 QApplication 实例存在（qtbot 之外的兜底初始化）。

    原先在 9 个 GUI 测试文件中逐字复制，收敛到 conftest 单一实现；
    各文件以 ``from tests.conftest import ensure_qapp as _ensure_qapp`` 引用。
    """
    app = QApplication.instance()
    return app if isinstance(app, QApplication) else QApplication([])


@pytest.fixture
def sample_config() -> dict:
    """提供一份字段齐全的示例配置字典（function 作用域），作为被测配置的基线数据。"""
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
def reset_global_config() -> Iterator[None]:
    """autouse（function 作用域）：每个测试前快照、测试后还原全局配置单例，防止状态泄漏。"""
    from core.config import global_config

    # 先保存当前配置快照，yield 后恢复，保证并行修改 global_config 的测试互不影响
    original_config = global_config.snapshot()
    yield
    global_config.replace_all(original_config)


@pytest.fixture
def mock_subprocess() -> Iterator[MagicMock]:
    """Mock subprocess.run（function 作用域），供 wifi/shutdown 等服务测试隔离系统命令调用。"""
    with patch("subprocess.run") as mock_run:
        # 默认返回执行成功且输出为空，测试可按需覆盖 returncode/stdout
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        yield mock_run


@pytest.fixture
def mock_requests() -> Iterator[MagicMock]:
    """Mock requests.Session（function 作用域），供 campus_login 测试隔离 JSONP 网络请求。"""
    with patch("requests.Session") as mock_session:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        # 模拟校园网认证服务器返回的 JSONP 成功响应，作为默认网络返回值
        mock_response.status_code = 200
        mock_response.text = 'dr1004({"ret_code": 0, "msg": "success"})'
        mock_instance.get.return_value = mock_response
        mock_instance.post.return_value = mock_response
        # 支持 with requests.Session() as s: 的上下文管理器用法
        mock_instance.__enter__.return_value = mock_instance
        mock_session.return_value = mock_instance
        yield mock_instance
