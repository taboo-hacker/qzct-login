"""
gui/dialogs/* 补充测试

覆盖 PeriodEditDialog, AboutDialog, SettingsDialog。
"""

from PyQt5.QtWidgets import QApplication

from core.config import global_config


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class TestPeriodEditDialog:
    """PeriodEditDialog 测试"""

    def test_constructs_add_mode(self, qtbot):
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "添加时间段"
        assert dialog.name_edit is not None
        assert dialog.start_edit is not None
        assert dialog.end_edit is not None

    def test_constructs_edit_mode(self, qtbot):
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        period = {"name": "测试", "start": "2026-01-01", "end": "2026-01-07"}
        dialog = PeriodEditDialog(period=period)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "编辑时间段"
        assert dialog.name_edit.text() == "测试"

    def test_save_empty_name(self, qtbot):
        """空名称不保存"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("")
        with patch("gui.dialogs.period_edit_dialog.QMessageBox.warning"):
            dialog.save()
        assert dialog.result_period is None

    def test_save_success(self, qtbot):
        _ensure_qapp()
        from PyQt5.QtCore import QDate

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("测试假期")
        dialog.start_edit.setDate(QDate(2026, 1, 1))
        dialog.end_edit.setDate(QDate(2026, 1, 7))
        dialog.save()
        assert dialog.result_period is not None
        assert dialog.result_period["name"] == "测试假期"
        assert dialog.result_period["start"] == "2026-01-01"

    def test_save_invalid_dates(self, qtbot):
        """开始日期晚于结束日期"""
        _ensure_qapp()
        from unittest.mock import patch

        from PyQt5.QtCore import QDate

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        dialog.name_edit.setText("测试")
        dialog.start_edit.setDate(QDate(2026, 1, 10))
        dialog.end_edit.setDate(QDate(2026, 1, 5))
        with patch("gui.dialogs.period_edit_dialog.QMessageBox.warning"):
            dialog.save()
        assert dialog.result_period is None


class TestAboutDialog:
    """AboutDialog 测试"""

    def test_constructs(self, qtbot):
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "关于我们"
        assert dialog.version_btn is not None

    def test_copy_version(self, qtbot):
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        original_text = dialog.version_btn.text()
        dialog._copy_version()
        assert dialog.version_btn.text() != original_text

    def test_restore_version_button(self, qtbot):
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        dialog._restore_version_button("Original")
        assert dialog.version_btn.text() == "Original"


class TestSettingsDialog:
    """SettingsDialog 测试"""

    def test_constructs(self, qtbot):
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "配置设置"
        assert dialog.tab_widget is not None
        assert dialog.tab_widget.count() == 7

    def test_theme_selector(self, qtbot):
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.theme_combo is not None
        assert dialog.theme_combo.count() >= 2

    def test_get_theme_display_name(self, qtbot):
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert "亮色" in dialog._get_theme_display_name("light")
        assert "暗色" in dialog._get_theme_display_name("dark")
        assert dialog._get_theme_display_name("unknown") == "unknown"

    def test_toggle_password_visibility(self, qtbot):
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from PyQt5.QtWidgets import QLineEdit, QPushButton

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        edit = QLineEdit("password")
        btn = QPushButton("显示")
        btn.setCheckable(True)
        btn.setChecked(True)
        dialog.toggle_password_visibility(edit, btn)
        assert edit.echoMode() == QLineEdit.EchoMode.Normal
        assert btn.text() == "隐藏"

        btn.setChecked(False)
        dialog.toggle_password_visibility(edit, btn)
        assert edit.echoMode() == QLineEdit.EchoMode.Password
        assert btn.text() == "显示"

    def test_on_theme_changed(self, qtbot):
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        # 切换到 dark 主题
        dark_index = dialog.theme_combo.findData("dark")
        if dark_index >= 0:
            dialog._on_theme_changed(dark_index)
            assert global_config.get("THEME") == "dark"
