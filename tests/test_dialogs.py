"""
gui/dialogs/* 补充测试

覆盖三个对话框：
- PeriodEditDialog（时间段添加/编辑、名称与日期校验）；
- AboutDialog（构造、复制版本号按钮反馈）；
- SettingsDialog（构造、滚动区域子页、主题选择与切换、密码可见性切换）。
弹窗提示均已 patch QMessageBox，测试通过 qtbot 管理控件生命周期。
"""

from PySide6.QtWidgets import QApplication

from core.config import global_config


def _ensure_qapp() -> QApplication:
    """模块级辅助函数：确保 QApplication 实例存在（对话框渲染依赖）。"""
    return QApplication.instance() or QApplication([])


class TestPeriodEditDialog:
    """PeriodEditDialog 测试：添加/编辑两种构造模式与保存校验逻辑。"""

    def test_constructs_add_mode(self, qtbot):
        """不传 period 时进入添加模式，标题为"添加时间段"且含名称/起止输入框。"""
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "添加时间段"
        assert dialog.name_edit is not None
        assert dialog.start_edit is not None
        assert dialog.end_edit is not None

    def test_constructs_edit_mode(self, qtbot):
        """传入 period 时进入编辑模式，标题为"编辑时间段"且回显名称。"""
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        period = {"name": "测试", "start": "2026-01-01", "end": "2026-01-07"}
        dialog = PeriodEditDialog(period=period)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "编辑时间段"
        assert dialog.name_edit.text() == "测试"

    def test_save_empty_name(self, qtbot):
        """名称为空时保存应被拒绝，result_period 保持 None。"""
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
        """填写合法名称与起止日期后保存，result_period 应含正确字段值。"""
        _ensure_qapp()
        from PySide6.QtCore import QDate

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
        """开始日期晚于结束日期时保存应被拒绝，result_period 保持 None。"""
        _ensure_qapp()
        from unittest.mock import patch

        from PySide6.QtCore import QDate

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
    """AboutDialog 测试：构造与版本号复制按钮的文本反馈。"""

    def test_constructs(self, qtbot):
        """构造后标题应为"关于我们"且版本按钮存在。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "关于我们"
        assert dialog.version_btn is not None

    def test_copy_version(self, qtbot):
        """点击复制版本号后按钮文本应变化以给出操作反馈。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        original_text = dialog.version_btn.text()
        dialog._copy_version()
        assert dialog.version_btn.text() != original_text

    def test_restore_version_button(self, qtbot):
        """_restore_version_button 应把按钮文本恢复为"版本 + 版本号"（定时器回调用）。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        dialog.version_btn.setText("✓ 已复制")
        dialog._restore_version_button()
        assert dialog.version_btn.text() == f"版本 {dialog.version}"


class TestSettingsDialog:
    """SettingsDialog 测试：构造布局、主题选择切换与密码框可见性。"""

    def test_constructs(self, qtbot):
        """默认配置下构造成功，应含 7 个设置子页的 tab_widget。"""
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        # SettingsDialog 从 global_config 读初值，先重置为默认配置保证可复现
        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "配置设置"
        assert dialog.tab_widget is not None
        assert dialog.tab_widget.count() == 7

    def test_tab_pages_are_scrollable(self, qtbot):
        """每个设置子页包在滚动区域内（窗口小时可上下滚动，回归修复）。"""
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from PySide6.QtWidgets import QScrollArea

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        for i in range(dialog.tab_widget.count()):
            page = dialog.tab_widget.widget(i)
            assert isinstance(page, QScrollArea), f"第 {i} 个设置子页不是滚动区域"

    def test_save_config_disk_failure_rolls_back(self, qtbot, monkeypatch):
        """回归（事务性）：落盘失败时内存配置应回滚，不得出现半程写入。

        旧实现三个子组件 save 方法在校验阶段就直接写 global_config，
        落盘失败后内存与文件不一致，重启后设置"丢失"。
        """
        _ensure_qapp()
        from PySide6.QtWidgets import QMessageBox

        import gui.dialogs.settings_panel as sp_mod
        from core.config import DEFAULT_CONFIG

        monkeypatch.setattr(sp_mod, "save_config_to_disk", lambda: False)
        monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_panel import SettingsPanel

        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.wifi_name_edit.setText("NewWiFi")
        panel.save_config()

        # 落盘失败：内存配置应保持原样
        assert global_config.get("WIFI_NAME") == DEFAULT_CONFIG["WIFI_NAME"]

    def test_save_config_success_persists(self, qtbot, tmp_path, monkeypatch):
        """正常保存：所有字段写入 global_config 并落盘，发出 config_saved 信号。"""
        _ensure_qapp()
        import json

        import core.config as cfg_module
        from core.config import DEFAULT_CONFIG

        monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_panel import SettingsPanel

        panel = SettingsPanel()
        qtbot.addWidget(panel)
        saved_signals: list[bool] = []
        panel.config_saved.connect(lambda: saved_signals.append(True))

        panel.wifi_name_edit.setText("NewWiFi")
        panel.save_config()

        assert global_config.get("WIFI_NAME") == "NewWiFi"
        assert (tmp_path / "config.json").exists()
        assert (
            json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["WIFI_NAME"]
            == "NewWiFi"
        )
        assert saved_signals == [True]

    def test_theme_selector(self, qtbot):
        """主题下拉框应存在且至少提供亮/暗两个选项。"""
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
        """主题 key 应映射为中文名（light=亮色、dark=暗色），未知 key 原样返回。"""
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
        """切换密码可见性：按钮选中显示明文/文案"隐藏"，取消则恢复密文/"显示"。"""
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from PySide6.QtWidgets import QLineEdit, QPushButton

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

    def test_on_theme_changed(self, qtbot, tmp_path, monkeypatch):
        """选择 dark 主题项后 THEME 应同步更新并即时落盘到配置文件。"""
        _ensure_qapp()
        import core.config as cfg_module
        from core.config import DEFAULT_CONFIG

        # 重定向配置文件到临时目录，避免测试写坏真实 ~/.qzct/config.json
        monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))

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
            # 主题切换应即时持久化（切完直接退出也不回退）
            import json

            saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
            assert saved["THEME"] == "dark"
