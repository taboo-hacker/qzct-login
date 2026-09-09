"""
gui/main_window.py 冒烟测试

MainWindow 构造需要加载配置、初始化日志与托盘，测试中全部打桩
（patch load_config / init_logger / TrayManager），
覆盖新布局下的关键控件存在、设置面板回显、状态徽标刷新、任务链
结果报告、布防可见性、托盘通知分级、防重入时序、业务级忙标志
与确认框默认按钮等场景。
"""

import datetime
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

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
def main_window(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator["MainWindow"]:
    """构造打桩后的主窗口：日志/托盘/配置加载全部 mock，测试后恢复标准流。

    CONFIG_FILE 重定向到 tmp_path：退出路径会调用 save_config() 持久化窗口
    几何与标签页，若不隔离会把测试用的 global_config 写进开发者真实配置。
    """
    from unittest.mock import patch

    import core.config as cfg_module
    from gui.main_window import MainWindow

    monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))

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


class TestTaskBusyFlag:
    """业务级忙标志与按钮禁用解耦：防重入守卫只读 _task_busy，不看控件状态。"""

    def test_busy_flag_follows_buttons_toggle(self, main_window: "MainWindow") -> None:
        """_set_buttons_enabled(False/True) 应同步置位/复位 _task_busy。"""
        assert main_window._task_busy is False  # 初始空闲

        main_window._set_buttons_enabled(False, busy_text="测试中...")
        assert main_window._task_busy is True

        main_window._set_buttons_enabled(True)
        assert main_window._task_busy is False

    def test_wifi_test_blocked_by_busy_flag_without_button_state(
        self, main_window: "MainWindow"
    ) -> None:
        """手动置忙（按钮保持可用）时 WiFi 测试应直接忽略：不弹确认框、不建 executor。"""
        from unittest.mock import patch

        from core.config import global_config

        global_config.update({"WIFI_NAME": "DormWiFi"})
        main_window._task_busy = True  # 未经 _set_buttons_enabled，按钮仍可用
        with (
            patch("gui.main_window.QMessageBox.question") as mock_q,
            patch("gui.main_window.is_wifi_connected") as mock_conn,
        ):
            main_window.on_test_wifi()
            mock_q.assert_not_called()
            mock_conn.assert_not_called()
        assert main_window._test_executors == []
        assert main_window.run_btn.isEnabled() is True  # 按钮状态未被牵连

    def test_login_test_blocked_by_busy_flag_without_button_state(
        self, main_window: "MainWindow"
    ) -> None:
        """手动置忙（按钮保持可用）时登录测试应直接忽略：不弹确认框、不建 executor。"""
        from unittest.mock import patch

        from core.config import global_config

        global_config.update({"USERNAME": "20230101"})
        main_window._task_busy = True
        with (
            patch("gui.main_window.QMessageBox.question") as mock_q,
            patch("gui.main_window.campus_login") as mock_login,
        ):
            main_window.on_test_login()
            mock_q.assert_not_called()
            mock_login.assert_not_called()
        assert main_window._test_executors == []

    def test_cancel_shutdown_blocked_by_busy_flag_without_button_state(
        self, main_window: "MainWindow"
    ) -> None:
        """手动置忙（按钮保持可用）时取消关机应弹"提示"信息框而非确认框。"""
        from unittest.mock import patch

        main_window._task_busy = True
        with (
            patch("gui.main_window.QMessageBox.information") as mock_info,
            patch("gui.main_window.QMessageBox.question") as mock_q,
        ):
            main_window.on_cancel_shutdown()
        mock_info.assert_called_once()
        mock_q.assert_not_called()
        assert main_window._test_executors == []
        assert main_window.run_btn.isEnabled() is True


class TestConfirmDialogDefaults:
    """统一确认框 _confirm：各调用点的默认按钮语义与既有行为保持一致。"""

    def test_run_once_confirm_defaults_to_no(self, main_window: "MainWindow") -> None:
        """「立即执行」确认框默认聚焦"否"（危险操作，回车不直接放行）。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        no = QMessageBox.StandardButton.No
        with (
            patch("gui.main_window.QMessageBox.question", return_value=no) as mock_q,
            patch.object(type(main_window), "start_task_chain") as mock_start,
        ):
            main_window.on_run_once()
            mock_q.assert_called_once()
            assert mock_q.call_args.args[4] is QMessageBox.StandardButton.No
            mock_start.assert_not_called()

    def test_wifi_test_confirm_defaults_to_yes(self, main_window: "MainWindow") -> None:
        """「测试 WiFi」确认框默认"是"（非破坏性测试，维持既有隐式 Yes 行为）。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from core.config import global_config

        global_config.update({"WIFI_NAME": "DormWiFi"})
        yes = QMessageBox.StandardButton.Yes
        with (
            patch("gui.main_window.QMessageBox.question", return_value=yes) as mock_q,
            patch.object(main_window, "_run_background_test") as mock_run,
        ):
            main_window.on_test_wifi()
            mock_q.assert_called_once()
            assert mock_q.call_args.args[4] is QMessageBox.StandardButton.Yes
            assert (
                mock_q.call_args.args[3]
                == QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            mock_run.assert_called_once()

    def test_login_test_confirm_defaults_to_yes(self, main_window: "MainWindow") -> None:
        """「测试登录」确认框默认"是"（非破坏性测试，维持既有隐式 Yes 行为）。"""
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from core.config import global_config

        global_config.update({"USERNAME": "20230101"})
        yes = QMessageBox.StandardButton.Yes
        with (
            patch("gui.main_window.QMessageBox.question", return_value=yes) as mock_q,
            patch.object(main_window, "_run_background_test") as mock_run,
        ):
            main_window.on_test_login()
            mock_q.assert_called_once()
            assert mock_q.call_args.args[4] is QMessageBox.StandardButton.Yes
            mock_run.assert_called_once()


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


def _tray_mock(window: "MainWindow") -> MagicMock:
    """取主窗口被打桩的 TrayManager 替身（fixture 中 patch 类构造所得）。"""
    return cast(MagicMock, window._tray)


class TestChainErrorNotification:
    """任务链异常终止可见性：托盘常驻形态下链级失败必须以 Critical 气泡可见。"""

    def test_chain_error_notifies_tray_critical(self, main_window: "MainWindow") -> None:
        """_on_chain_error 应弹 Critical 级托盘通知（窗口可能最小化在托盘中）。"""
        from PySide6.QtWidgets import QSystemTrayIcon

        tray = _tray_mock(main_window)
        main_window._on_chain_error({"检查执行条件": {"error": "boom"}})
        tray.notify.assert_called_once_with(
            "任务链执行失败",
            "任务链异常终止，定时关机未设置，详情见运行日志",
            icon=QSystemTrayIcon.MessageIcon.Critical,
        )


class TestShutdownArmedVisibility:
    """定时关机布防状态可见性：左卡片剩余时间 + 托盘状态同步。"""

    def _success_results(self, seconds: int = 7200) -> dict[str, object]:
        return {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": True},
            "登录校园网": {"login_successful": True},
            "设置定时关机": {"shutdown_set": True, "seconds": seconds},
        }

    def test_armed_label_visible_after_chain_success(self, main_window: "MainWindow") -> None:
        """链成功设置关机后左卡片应显示"已布防 · 剩 HH:MM:SS"。"""
        main_window._on_chain_success(True, self._success_results(seconds=7200))
        label = main_window.shutdown_armed_label
        assert not label.isHidden()
        assert "已布防" in label.text()
        assert "剩" in label.text()
        assert main_window._shutdown_deadline is not None
        assert main_window._shutdown_deadline > datetime.datetime.now()

    def test_armed_label_shows_expired_after_deadline(self, main_window: "MainWindow") -> None:
        """截止时刻已过应显示"已到关机时间"（不显示负倒计时）。"""
        main_window._shutdown_deadline = datetime.datetime.now() - datetime.timedelta(seconds=1)
        main_window._update_shutdown_armed_display()
        label = main_window.shutdown_armed_label
        assert not label.isHidden()
        assert label.text() == "已布防关机 · 已到关机时间"

    def test_cancel_hides_armed_label(self, main_window: "MainWindow") -> None:
        """取消关机成功后布防标签隐藏、截止时刻清空。"""
        from unittest.mock import patch

        main_window._on_chain_success(True, self._success_results(seconds=7200))
        assert not main_window.shutdown_armed_label.isHidden()
        with patch("gui.main_window.QMessageBox.information"):
            main_window._on_cancel_shutdown_finished("cancel_shutdown", True)
        assert main_window.shutdown_armed_label.isHidden()
        assert main_window._shutdown_deadline is None
        assert main_window._shutdown_scheduled is False

    def test_tray_receives_armed_status(self, main_window: "MainWindow") -> None:
        """布防后托盘 set_shutdown_status 应收到 armed=True 与剩余时间文案。"""
        tray = _tray_mock(main_window)
        main_window._on_chain_success(True, self._success_results(seconds=7200))
        armed_calls = [
            c for c in tray.set_shutdown_status.call_args_list if c.kwargs.get("armed") is True
        ]
        assert armed_calls, "托盘未收到 armed=True 状态更新"
        detail = str(armed_calls[-1].kwargs.get("detail", ""))
        assert detail.startswith("剩 ")

    def test_tray_receives_disarmed_after_cancel(self, main_window: "MainWindow") -> None:
        """取消关机后托盘应收到 armed=False。"""
        from unittest.mock import patch

        tray = _tray_mock(main_window)
        main_window._on_chain_success(True, self._success_results(seconds=7200))
        with patch("gui.main_window.QMessageBox.information"):
            main_window._on_cancel_shutdown_finished("cancel_shutdown", True)
        tray.set_shutdown_status.assert_called_with(armed=False, detail="")


class TestCancelShutdownGuardOrder:
    """取消关机防重入时序：检查必须先于确认框，命中时给用户可见反馈。"""

    def test_busy_shows_information_instead_of_question(self, main_window: "MainWindow") -> None:
        """任务执行中触发取消：弹"提示"信息框，且不再弹确认框。"""
        from unittest.mock import patch

        main_window._set_buttons_enabled(False, busy_text="运行中...")
        with (
            patch("gui.main_window.QMessageBox.information") as mock_info,
            patch("gui.main_window.QMessageBox.question") as mock_q,
        ):
            main_window.on_cancel_shutdown()
        mock_info.assert_called_once()
        mock_q.assert_not_called()
        # 未进入取消流程（不新建 executor）
        assert main_window._test_executors == []


class TestRuleSourceDisplay:
    """左卡片规则来源显示：与 core.date_rules 唯一优先级阶梯一致。"""

    def test_custom_rule_overrides_compensatory_text(self, main_window: "MainWindow") -> None:
        """自定义规则启用 + 当天为调休日：应显示自定义来源而非"调休上班日"。

        回归：旧版手写阶梯先查 COMPENSATORY_WORKDAYS，与 core 的
        自定义规则最高优先级相反，导致左卡片与日历同屏矛盾。
        """
        from core.config import global_config

        today = datetime.date.today()
        global_config.update(
            {
                "COMPENSATORY_WORKDAYS": [today.isoformat()],
                "DATE_RULES": {
                    "ENABLE_CUSTOM_RULE": True,
                    "WEEKLY_EXECUTE_DAYS": [today.weekday()],
                    "CUSTOM_HOLIDAY_PERIODS": [],
                    "CUSTOM_WORKDAY_PERIODS": [],
                },
            }
        )
        main_window._update_status_display()
        text = main_window.rule_label.text()
        assert "调休上班日" not in text
        assert "自定义每周执行日" in text

    def test_compensatory_text_when_custom_rule_disabled(self, main_window: "MainWindow") -> None:
        """未启用自定义规则 + 当天为调休日：仍应显示"调休上班日"。"""
        from core.config import global_config

        today = datetime.date.today()
        global_config.update(
            {
                "COMPENSATORY_WORKDAYS": [today.isoformat()],
                "HOLIDAY_PERIODS": [],
                "DATE_RULES": {
                    "ENABLE_CUSTOM_RULE": False,
                    "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
                    "CUSTOM_HOLIDAY_PERIODS": [],
                    "CUSTOM_WORKDAY_PERIODS": [],
                },
            }
        )
        main_window._update_status_display()
        assert "调休上班日" in main_window.rule_label.text()


class TestMidnightStatusRefresh:
    """常驻跨零点刷新：换天后"今日状态"卡片应随之更新。"""

    def test_date_change_triggers_status_refresh(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_shown_date 落后一天时调用 _update_time_display 应触发状态刷新。"""
        calls: list[int] = []
        monkeypatch.setattr(main_window, "_update_status_display", lambda: calls.append(1))

        main_window._shown_date = datetime.date.today() - datetime.timedelta(days=1)
        main_window._update_time_display()
        assert calls == [1]
        assert main_window._shown_date == datetime.date.today()

        # 同一天内重复走秒不再刷新（避免无谓重绘）
        calls.clear()
        main_window._update_time_display()
        assert calls == []


class TestStartTaskChainWiring:
    """任务链装配测试：WiFi 步骤应使用按配置动态估算的超时预算。"""

    def test_wifi_step_uses_dynamic_timeout_budget(self, main_window: "MainWindow") -> None:
        """task_connect_wifi 的 add 调用应带 timeout>0（estimate_wifi_retry_budget 结果）。"""
        from unittest.mock import patch

        from services.tasks import task_connect_wifi

        with patch("gui.main_window.TaskChain") as mock_chain_cls:
            chain = mock_chain_cls.return_value
            main_window.start_task_chain()
            wifi_calls = [
                c for c in chain.add.call_args_list if c.args and c.args[0] is task_connect_wifi
            ]
            assert len(wifi_calls) == 1
            timeout = wifi_calls[0].kwargs.get("timeout")
            assert isinstance(timeout, int)
            assert timeout >= 30  # estimate_wifi_retry_budget 恒 ≥ 30（固定余量）

        # 清理真实创建的 executor，避免线程池泄漏
        assert main_window.task_executor is not None
        main_window.task_executor.cancel_all()
        main_window.task_executor.shutdown(wait=False)


class TestTrayNotifyLevels:
    """托盘通知分级：失败路径传 Warning，成功路径保持默认 Information。"""

    def test_partial_failure_notifies_warning(self, main_window: "MainWindow") -> None:
        """链完成但 success=False（部分任务失败）应以 Warning 图标通知。"""
        from PySide6.QtWidgets import QSystemTrayIcon

        tray = _tray_mock(main_window)
        main_window._on_chain_success(False, {})
        tray.notify.assert_called_once_with(
            "校园网自动登录",
            "部分任务执行失败，请查看日志",
            icon=QSystemTrayIcon.MessageIcon.Warning,
        )

    def test_failure_summary_notifies_warning(self, main_window: "MainWindow") -> None:
        """存在失败步骤的摘要通知应以 Warning 图标发出，并附带可执行的排查建议。"""
        from PySide6.QtWidgets import QSystemTrayIcon

        tray = _tray_mock(main_window)
        results = {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": False},
            "登录校园网": {"login_successful": True},
            "设置定时关机": {"shutdown_set": True, "seconds": 3600},
        }
        main_window._on_chain_success(True, results)
        tray.notify.assert_called_once_with(
            "校园网自动登录",
            "WiFi 连接失败；已设置 23:00 定时关机\n请到「设置」核对 WiFi 名称与密码",
            icon=QSystemTrayIcon.MessageIcon.Warning,
        )

    def test_success_path_keeps_default_information(self, main_window: "MainWindow") -> None:
        """全部成功路径不显式传 icon（保持默认 Information）。"""
        tray = _tray_mock(main_window)
        results = {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": True},
            "登录校园网": {"login_successful": True},
            "设置定时关机": {"shutdown_set": True, "seconds": 3600},
        }
        main_window._on_chain_success(True, results)
        tray.notify.assert_called_once()  # 单次成功通知，无 icon 覆盖
        assert "icon" not in tray.notify.call_args.kwargs


class TestFooterTooltip:
    """footer 长文案测试：_set_footer 同步 tooltip，截断文案悬停可读。"""

    def test_set_footer_sets_text_and_tooltip(self, main_window: "MainWindow") -> None:
        """_set_footer 应同时写文本与 tooltip。"""
        long_text = "WiFi 连接、校园网登录失败；已设置 23:00 定时关机，详情见运行日志"
        main_window._set_footer(long_text)
        assert main_window.footer_status.text() == long_text
        assert main_window.footer_status.toolTip() == long_text

    def test_chain_error_footer_has_tooltip(self, main_window: "MainWindow") -> None:
        """链失败文案经 _set_footer 写入后应带同名 tooltip。"""
        main_window._on_chain_error({})
        assert main_window.footer_status.text() == "任务链执行失败"
        assert main_window.footer_status.toolTip() == "任务链执行失败"


class TestWindowStatePersistence:
    """窗口几何与标签页持久化：退出写回配置，启动还原。

    回归：此前无任何 saveGeometry/restoreGeometry，用户每次启动都要
    重新调整窗口大小与位置，并总是被带回"运行日志"标签页。
    """

    def test_save_writes_geometry_and_active_tab(
        self, main_window: "MainWindow", tmp_path: Path
    ) -> None:
        """_save_window_state 应写入几何串、当前标签页并落盘。"""
        from core.config import global_config

        main_window.main_tabs.setCurrentIndex(2)  # 任务日历
        main_window._save_window_state()

        assert global_config["ACTIVE_TAB"] == "calendar"
        assert str(global_config["WINDOW_GEOMETRY"]) != ""
        assert (tmp_path / "config.json").exists(), "退出路径应把状态落盘"

    def test_restore_selects_saved_tab(self, main_window: "MainWindow") -> None:
        """_restore_window_state 按 ACTIVE_TAB 还原标签页索引。"""
        from core.config import global_config

        global_config["ACTIVE_TAB"] = "settings"
        main_window._restore_window_state()

        assert main_window.main_tabs.currentIndex() == 1

    def test_restore_keeps_current_tab_on_unknown_value(self, main_window: "MainWindow") -> None:
        """未知标签页标识应忽略，不改变当前标签页。"""
        from core.config import global_config

        main_window.main_tabs.setCurrentIndex(1)
        global_config["ACTIVE_TAB"] = "不存在的标签页"
        main_window._restore_window_state()

        assert main_window.main_tabs.currentIndex() == 1

    def test_restore_survives_corrupt_geometry(self, main_window: "MainWindow") -> None:
        """几何串损坏（非 base64）时不得抛异常，回退默认尺寸。"""
        from core.config import global_config

        global_config["WINDOW_GEOMETRY"] = "!!!not-valid-base64!!!"
        main_window._restore_window_state()  # 不应抛异常

        assert main_window.width() > 0

    def test_save_failure_does_not_interrupt_exit(
        self, main_window: "MainWindow", monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """落盘失败时 _save_window_state 应吞掉异常，不阻断退出流程。"""
        import gui.main_window as mw_module

        def _boom() -> bool:
            raise OSError("磁盘已满")

        monkeypatch.setattr(mw_module, "save_config", _boom)
        main_window._save_window_state()  # 不应抛异常


class TestTaskChainProgressFeedback:
    """任务链进度反馈：状态栏显示"第 N/M 步"与单步耗时。

    回归：此前 started 信号只写日志，任务执行期间（WiFi 重试可达数分钟）
    状态栏一直停在上一步的"完成"文案，用户看不出程序仍在工作。
    """

    _STEPS = ["检查执行条件", "连接WiFi", "登录校园网", "设置定时关机"]

    def test_started_shows_step_position(self, main_window: "MainWindow") -> None:
        """步骤开始时状态栏应显示当前序号与总步数。"""
        main_window._chain_step_names = list(self._STEPS)
        main_window._on_task_started("连接WiFi")

        assert main_window.footer_status.text() == "正在执行：连接WiFi（第 2/4 步）"

    def test_started_without_chain_shows_name_only(self, main_window: "MainWindow") -> None:
        """步骤名不在链内时只显示任务名，不显示错误的序号。"""
        main_window._chain_step_names = []
        main_window._on_task_started("孤立任务")

        assert "孤立任务" in main_window.footer_status.text()
        assert "第" not in main_window.footer_status.text()

    def test_finished_appends_elapsed(self, main_window: "MainWindow") -> None:
        """步骤完成后状态栏应带上耗时。"""
        main_window._chain_step_names = list(self._STEPS)
        main_window._on_task_started("连接WiFi")
        main_window._on_task_finished("连接WiFi", {})

        text = main_window.footer_status.text()
        assert text.startswith("连接WiFi 完成")
        assert "耗时" in text

    def test_error_appends_elapsed_and_clears_record(self, main_window: "MainWindow") -> None:
        """步骤出错同样显示耗时，且起始时刻记录被清除（不跨链残留）。"""
        main_window._chain_step_names = list(self._STEPS)
        main_window._on_task_started("登录校园网")
        main_window._on_task_error("登录校园网", "boom")

        assert "耗时" in main_window.footer_status.text()
        assert main_window._step_started_at == {}


class TestFailureHints:
    """失败摘要可操作化：footer 附带排查入口，用户无需翻日志找原因。"""

    def test_wifi_failure_hint_points_to_settings(self, main_window: "MainWindow") -> None:
        """WiFi 失败应提示到设置页核对 WiFi 名称与密码。"""
        results = {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": False},
            "登录校园网": {"login_successful": True},
            "设置定时关机": {"shutdown_set": True, "seconds": 3600},
        }
        main_window._on_chain_success(True, results)

        assert "请到「设置」核对 WiFi 名称与密码" in main_window.footer_status.text()

    def test_login_failure_hint_mentions_isp(self, main_window: "MainWindow") -> None:
        """登录失败应提示核对账号密码与运营商类型。"""
        results = {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": True},
            "登录校园网": {"login_successful": False},
            "设置定时关机": {"shutdown_set": True, "seconds": 3600},
        }
        main_window._on_chain_success(True, results)

        assert "运营商类型" in main_window.footer_status.text()

    def test_all_success_has_no_hint(self, main_window: "MainWindow") -> None:
        """全部成功时不应出现排查建议。"""
        results = {
            "检查执行条件": {"need_work": True},
            "连接WiFi": {"wifi_connected": True},
            "登录校园网": {"login_successful": True},
            "设置定时关机": {"shutdown_set": True, "seconds": 3600},
        }
        main_window._on_chain_success(True, results)

        assert "请到「设置」" not in main_window.footer_status.text()
