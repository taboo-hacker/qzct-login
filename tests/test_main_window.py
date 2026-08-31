"""
gui/main_window.py 冒烟测试

MainWindow 构造需要加载配置、初始化日志与托盘，测试中全部打桩
（patch load_config / init_logger / TrayManager），
仅验证新布局下的关键控件存在、设置面板回显与状态徽标刷新流程。
"""

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytestqt.qtbot import QtBot

from tests.conftest import ensure_qapp as _ensure_qapp

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class TestMainWindowSmoke:
    """主窗口冒烟测试：构造流程、配置回显、状态显示三大场景。"""

    def test_constructs_with_layout_widgets(self, qtbot: QtBot) -> None:
        """构造主窗口成功后，两栏布局与三个标签页的关键控件应全部存在。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.main_window import MainWindow

        # 暂存标准流：Qt/托盘可能在 C++ 层写 stderr，测试环境需原样恢复
        original_out, original_err = sys.stdout, sys.stderr
        window = None
        try:
            with (
                patch("gui.main_window.load_config", return_value=None),
                patch("gui.main_window.init_logger"),
                patch("gui.main_window.TrayManager"),
            ):
                window = MainWindow()
                # 阻止 200ms 后的自动任务链在测试事件循环中触发真实网络操作
                window._task_chain_started = True
                window._timer.stop()

                assert window.log_text is not None
                assert window.run_btn is not None
                assert window.cancel_btn is not None
                assert window.test_wifi_btn is not None
                assert window.test_login_btn is not None
                assert window.exit_btn is not None
                assert window.about_btn is not None
                assert window.clear_log_btn is not None
                assert window.main_tabs.count() == 3
                assert window.main_tabs.tabText(0) == "运行日志"
                assert window.main_tabs.tabText(1) == "设置"
                assert window.main_tabs.tabText(2) == "任务日历"
                assert window.status_badge is not None
                assert window.date_label is not None
                assert window.rule_label is not None
                assert window.time_label is not None
                assert window.footer_status is not None
        finally:
            sys.stdout, sys.stderr = original_out, original_err
            if window is not None:
                window.deleteLater()

    def test_settings_panel_reflects_loaded_config(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """设置面板应回显从磁盘加载的配置值（回归：曾因构建顺序颠倒显示默认空值）。"""
        _ensure_qapp()
        import json
        from unittest.mock import patch

        import core.config as cfg_module

        # 将 CONFIG_DIR/CONFIG_FILE 指向临时目录并写入测试配置，验证真实加载链路
        monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))
        (tmp_path / "config.json").write_text(
            json.dumps(
                {
                    "WIFI_NAME": "DormWiFi",
                    "USERNAME": "20230101",
                    "SHUTDOWN_HOUR": 22,
                    "SHUTDOWN_MIN": 30,
                }
            ),
            encoding="utf-8",
        )

        from gui.main_window import MainWindow

        original_out, original_err = sys.stdout, sys.stderr
        window = None
        try:
            with (
                patch("gui.main_window.init_logger"),
                patch("gui.main_window.TrayManager"),
            ):
                window = MainWindow()
                window._task_chain_started = True
                window._timer.stop()

                panel = window._settings_panel
                assert (
                    panel.wifi_name_edit is not None
                    and panel.username_edit is not None
                    and panel.shutdown_hour_edit is not None
                    and panel.shutdown_min_edit is not None
                )
                assert panel.wifi_name_edit.text() == "DormWiFi"
                assert panel.username_edit.text() == "20230101"
                assert panel.shutdown_hour_edit.text() == "22"
                assert panel.shutdown_min_edit.text() == "30"
        finally:
            sys.stdout, sys.stderr = original_out, original_err
            if window is not None:
                window.deleteLater()

    def test_status_badge_state_reflects_need_work(self, qtbot: QtBot) -> None:
        """should_work_today 返回 False/True 时，状态徽标应分别显示休息/工作态。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.main_window import MainWindow

        original_out, original_err = sys.stdout, sys.stderr
        window = None
        try:
            with (
                patch("gui.main_window.load_config", return_value=None),
                patch("gui.main_window.init_logger"),
                patch("gui.main_window.TrayManager"),
                patch("gui.main_window.should_work_today", return_value=False),
            ):
                window = MainWindow()
                window._task_chain_started = True
                window._timer.stop()
                window._update_status_display()
                assert window.status_badge.property("state") == "rest"
                assert "无需执行" in window.status_badge.text()

            # 复用同一窗口，切换 should_work_today 的返回值验证徽标随之更新
            with patch("gui.main_window.should_work_today", return_value=True):
                window._update_status_display()
                assert window.status_badge.property("state") == "work"
                assert "需要执行" in window.status_badge.text()
        finally:
            sys.stdout, sys.stderr = original_out, original_err
            if window is not None:
                window.deleteLater()


@pytest.fixture
def main_window(qtbot: QtBot) -> Iterator["MainWindow"]:
    """构造打桩后的主窗口：日志/托盘/配置加载全部 mock，测试后恢复标准流。"""
    from unittest.mock import patch

    from gui.main_window import MainWindow

    _ensure_qapp()
    original_out, original_err = sys.stdout, sys.stderr
    window = None
    try:
        with (
            patch("gui.main_window.load_config", return_value=None),
            patch("gui.main_window.init_logger"),
            patch("gui.main_window.TrayManager"),
        ):
            window = MainWindow()
            # 阻止自动任务链与时钟在测试事件循环中触发真实操作
            window._task_chain_started = True
            window._timer.stop()
            yield window
    finally:
        sys.stdout, sys.stderr = original_out, original_err
        if window is not None:
            window.deleteLater()


class TestChainResultReporting:
    """任务链完成回调测试：如实报告失败步骤与关机设置状态。

    回归：曾出现 WiFi/登录失败仍提示"所有任务执行完成"的误报。
    """

    def _results(
        self,
        wifi: object = True,
        login: bool = True,
        shutdown_set: bool = True,
        shutdown_reason: str = "",
    ) -> dict[str, object]:
        return {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": wifi},
            "登录校园网": {"login_successful": login},
            "设置定时关机": (
                {"shutdown_set": shutdown_set}
                if shutdown_set
                else {"shutdown_set": False, "reason": shutdown_reason or "command_failed"}
            ),
        }

    def test_all_success_reports_shutdown_time(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """全部成功时状态栏应包含关机时间，并记录关机已设置。"""
        from core.config import global_config

        global_config.update({"SHUTDOWN_HOUR": 22, "SHUTDOWN_MIN": 30})
        main_window._on_chain_success(True, self._results())
        assert "已设置 22:30 关机" in main_window.footer_status.text()
        assert main_window._shutdown_scheduled is True

    def test_failed_steps_are_reported_honestly(self, main_window: "MainWindow") -> None:
        """WiFi/登录失败时应列出失败项，不再误报"所有任务执行完成"。"""
        main_window._on_chain_success(True, self._results(wifi=False, login=False))
        status = main_window.footer_status.text()
        assert "WiFi 连接、校园网登录失败" in status
        assert "已设置 23:00 定时关机" in status  # 保底关机仍生效，需明确告知

    def test_wifi_not_configured_is_not_failure(self, main_window: "MainWindow") -> None:
        """未配置 WiFi（有线用户，wifi_connected=None）不算失败。"""
        main_window._on_chain_success(True, self._results(wifi=None))
        assert "所有任务执行完成" in main_window.footer_status.text()

    def test_shutdown_command_failure_reported(self, main_window: "MainWindow") -> None:
        """关机命令执行失败应计入失败项。"""
        main_window._on_chain_success(
            True, self._results(shutdown_set=False, shutdown_reason="command_failed")
        )
        assert "定时关机失败" in main_window.footer_status.text()

    def test_shutdown_time_passed_is_not_failure(self, main_window: "MainWindow") -> None:
        """已过今日关机时间属正常跳过，不算失败。"""
        main_window._on_chain_success(
            True, self._results(shutdown_set=False, shutdown_reason="time_passed")
        )
        assert "所有任务执行完成" in main_window.footer_status.text()
        assert "未设置关机" in main_window.footer_status.text()

    def test_no_need_work_early_exit(self, main_window: "MainWindow") -> None:
        """今天无需执行时应提示节假日/周末提前结束。"""
        main_window._on_chain_success(
            True, {"检查执行条件": {"need_work": False, "chain_break": True}}
        )
        assert "今天无需执行" in main_window.footer_status.text()


class TestRunOnStart:
    """启动自动执行测试：首次使用（零配置）应跳过并引导，而非盲目执行。"""

    def test_skips_when_unconfigured(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """账号与 WiFi 均为空时应跳过自动执行并给出引导提示。"""
        from unittest.mock import patch

        from core.config import global_config

        main_window._task_chain_started = False  # fixture 预置了 True，这里显式放开
        global_config.update({"USERNAME": "", "WIFI_NAME": ""})
        with patch.object(type(main_window), "start_task_chain") as mock_start:
            main_window.run_on_start()
            mock_start.assert_not_called()
        assert "尚未配置账号" in main_window.footer_status.text()

    def test_runs_when_configured(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """已配置账号时应调度任务链（延迟 1 秒启动）。"""
        from unittest.mock import patch

        from core.config import global_config

        main_window._task_chain_started = False
        global_config.update({"USERNAME": "20230001", "WIFI_NAME": "DormWiFi"})
        with patch("gui.main_window.QTimer.singleShot") as mock_shot:
            main_window.run_on_start()
            mock_shot.assert_called_once()

    def test_runs_once_only(self, main_window: "MainWindow") -> None:
        """run_on_start 重复调用只应执行一次（_task_chain_started 防重）。"""
        from unittest.mock import patch

        from core.config import global_config

        main_window._task_chain_started = False
        with patch("gui.main_window.QTimer.singleShot") as mock_shot:
            global_config.update({"USERNAME": "20230001"})
            main_window.run_on_start()
            main_window.run_on_start()
            assert mock_shot.call_count == 1


class TestButtonsGuardAndCallbacks:
    """测试按钮防重入与回调恢复：任务期间按钮禁用，回调后恢复。"""

    def test_wifi_test_disables_and_restores_buttons(
        self, main_window: "MainWindow", qtbot: QtBot
    ) -> None:
        """WiFi 测试期间任务按钮禁用，完成后恢复并弹出结果。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from core.config import global_config

        global_config.update({"WIFI_NAME": "DormWiFi"})
        yes = QMessageBox.StandardButton.Yes
        with (
            patch("gui.main_window.QMessageBox.question", return_value=yes) as mock_q,
            patch("gui.main_window.QMessageBox.information") as mock_info,
            # 已连接短路：后台线程立即完成，不触发真实 netsh
            patch("gui.main_window.is_wifi_connected", return_value=True),
        ):
            main_window.on_test_wifi()
            mock_q.assert_called_once()
            assert main_window.run_btn.isEnabled() is False
            assert main_window.test_login_btn.isEnabled() is False

            qtbot.waitUntil(lambda: main_window.run_btn.isEnabled(), timeout=5000)
            mock_info.assert_called_once()
        assert "WiFi 已连接" in main_window.footer_status.text()

    def test_wifi_test_rejected_while_busy(self, main_window: "MainWindow") -> None:
        """任务进行中（按钮已禁用）时测试请求应被忽略。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from core.config import global_config

        global_config.update({"WIFI_NAME": "DormWiFi"})
        yes = QMessageBox.StandardButton.Yes
        with (
            patch("gui.main_window.QMessageBox.question", return_value=yes),
            patch("gui.main_window.is_wifi_connected", return_value=True),
            patch("gui.main_window.QMessageBox.information"),
        ):
            main_window._set_buttons_enabled(False, busy_text="测试中...")
            main_window.on_test_wifi()  # 应直接忽略，不再新建 executor
            assert main_window.run_btn.text() == "测试中..."
            assert main_window._test_executors == []


class TestCloseEvent:
    """关闭事件测试：强制退出走完整清理（恢复标准流、接受事件）。"""

    def test_force_quit_restores_streams_and_accepts(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_force_quit=True 时 closeEvent 应恢复 stdout/stderr 并接受关闭。"""
        from PySide6.QtGui import QCloseEvent

        event = QCloseEvent()
        # 托盘 mock 的 is_available() 返回 truthy MagicMock，
        # 置 _force_quit 确保走真实退出分支而非最小化到托盘
        main_window._force_quit = True
        main_window.closeEvent(event)
        assert event.isAccepted()
        assert sys.stdout is main_window._original_stdout
        assert sys.stderr is main_window._original_stderr

    def test_real_close_confirms_when_shutdown_scheduled(self, main_window: "MainWindow") -> None:
        """已设置定时关机时退出应先弹确认框（默认"否"），拒绝则不退出。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        main_window._shutdown_scheduled = True
        no = QMessageBox.StandardButton.No
        with (
            patch("gui.main_window.QMessageBox.question", return_value=no) as mock_q,
            patch.object(main_window, "close") as mock_close,
        ):
            main_window._real_close()
            mock_q.assert_called_once()
            mock_close.assert_not_called()
