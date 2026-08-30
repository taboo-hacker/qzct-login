"""
gui/main_window.py 冒烟测试

MainWindow 构造需要加载配置、初始化日志与托盘，测试中全部打桩
（patch load_config / init_logger / TrayManager），
仅验证新布局下的关键控件存在、设置面板回显与状态徽标刷新流程。
"""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot


def _ensure_qapp() -> QApplication:
    """模块级辅助函数：确保 QApplication 实例存在（qtbot 之外的兜底初始化）。"""
    return QApplication.instance() or QApplication([])


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
                patch("gui.main_window.load_config"),
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
                patch("gui.main_window.load_config"),
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
