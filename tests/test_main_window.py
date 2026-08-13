"""
gui/main_window.py 冒烟测试

MainWindow 构造需要加载配置、初始化日志与托盘，测试中全部打桩，
仅验证新布局下的关键控件存在与主题应用流程。
"""

import sys

from PySide6.QtWidgets import QApplication


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class TestMainWindowSmoke:
    """主窗口冒烟测试"""

    def test_constructs_with_layout_widgets(self, qtbot):
        """构造主窗口并验证两栏布局的关键控件存在"""
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

    def test_settings_panel_reflects_loaded_config(self, qtbot, tmp_path, monkeypatch):
        """设置面板显示加载后的配置值（回归：曾因构建顺序颠倒显示默认空值）"""
        _ensure_qapp()
        import json
        from unittest.mock import patch

        import core.config as cfg_module

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
                assert panel.wifi_name_edit.text() == "DormWiFi"
                assert panel.username_edit.text() == "20230101"
                assert panel.shutdown_hour_edit.text() == "22"
                assert panel.shutdown_min_edit.text() == "30"
        finally:
            sys.stdout, sys.stderr = original_out, original_err
            if window is not None:
                window.deleteLater()

    def test_status_badge_state_reflects_need_work(self, qtbot):
        """状态徽标 state 属性随需执行状态变化"""
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

            with patch("gui.main_window.should_work_today", return_value=True):
                window._update_status_display()
                assert window.status_badge.property("state") == "work"
                assert "需要执行" in window.status_badge.text()
        finally:
            sys.stdout, sys.stderr = original_out, original_err
            if window is not None:
                window.deleteLater()
