"""
gui/dialogs/* 补充测试

覆盖三个对话框：
- PeriodEditDialog（时间段添加/编辑、名称与日期校验）；
- AboutDialog（构造、复制版本号按钮反馈）；
- SettingsDialog（构造、滚动区域子页、主题选择与切换、密码可见性切换）。
另有 SettingsPanel 保存前集中校验（静默失效配置的确认框流程）。
弹窗提示均已 patch QMessageBox，测试通过 qtbot 管理控件生命周期。
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytestqt.qtbot import QtBot

from core.config import global_config
from tests.conftest import ensure_qapp as _ensure_qapp

if TYPE_CHECKING:
    from gui.dialogs.settings_panel import SettingsPanel


class TestPeriodEditDialog:
    """PeriodEditDialog 测试：添加/编辑两种构造模式与保存校验逻辑。"""

    def test_constructs_add_mode(self, qtbot: QtBot) -> None:
        """不传 period 时进入添加模式，标题为"添加时间段"且含名称/起止输入框。"""
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "添加时间段"
        assert dialog.name_edit is not None
        assert dialog.start_edit is not None
        assert dialog.end_edit is not None

    def test_constructs_edit_mode(self, qtbot: QtBot) -> None:
        """传入 period 时进入编辑模式，标题为"编辑时间段"且回显名称。"""
        _ensure_qapp()
        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        period = {"name": "测试", "start": "2026-01-01", "end": "2026-01-07"}
        dialog = PeriodEditDialog(period=period)
        qtbot.addWidget(dialog)
        assert dialog.name_edit is not None
        assert dialog.windowTitle() == "编辑时间段"
        assert dialog.name_edit.text() == "测试"

    def test_save_empty_name(self, qtbot: QtBot) -> None:
        """名称为空时保存应被拒绝，result_period 保持 None。"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.name_edit is not None
        dialog.name_edit.setText("")
        with patch("gui.dialogs.period_edit_dialog.QMessageBox.warning"):
            dialog.save()
        assert dialog.result_period is None

    def test_save_success(self, qtbot: QtBot) -> None:
        """填写合法名称与起止日期后保存，result_period 应含正确字段值。"""
        _ensure_qapp()
        from PySide6.QtCore import QDate

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.name_edit is not None and dialog.start_edit is not None
        assert dialog.end_edit is not None
        dialog.name_edit.setText("测试假期")
        dialog.start_edit.setDate(QDate(2026, 1, 1))
        dialog.end_edit.setDate(QDate(2026, 1, 7))
        dialog.save()
        assert dialog.result_period is not None
        assert dialog.result_period["name"] == "测试假期"
        assert dialog.result_period["start"] == "2026-01-01"

    def test_save_invalid_dates(self, qtbot: QtBot) -> None:
        """开始日期晚于结束日期时保存应被拒绝，result_period 保持 None。"""
        _ensure_qapp()
        from unittest.mock import patch

        from PySide6.QtCore import QDate

        from gui.dialogs.period_edit_dialog import PeriodEditDialog

        dialog = PeriodEditDialog()
        qtbot.addWidget(dialog)
        assert dialog.name_edit is not None and dialog.start_edit is not None
        assert dialog.end_edit is not None
        dialog.name_edit.setText("测试")
        dialog.start_edit.setDate(QDate(2026, 1, 10))
        dialog.end_edit.setDate(QDate(2026, 1, 5))
        with patch("gui.dialogs.period_edit_dialog.QMessageBox.warning"):
            dialog.save()
        assert dialog.result_period is None


class TestAboutDialog:
    """AboutDialog 测试：构造与版本号复制按钮的文本反馈。"""

    def test_constructs(self, qtbot: QtBot) -> None:
        """构造后标题应为"关于我们"且版本按钮存在。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "关于我们"
        assert dialog.version_btn is not None

    def test_copy_version(self, qtbot: QtBot) -> None:
        """点击复制版本号后按钮文本应变化以给出操作反馈。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        assert dialog.version_btn is not None
        original_text = dialog.version_btn.text()
        dialog._copy_version()
        assert dialog.version_btn.text() != original_text

    def test_restore_version_button(self, qtbot: QtBot) -> None:
        """_restore_version_button 应把按钮文本恢复为"版本 + 版本号"（定时器回调用）。"""
        _ensure_qapp()
        from gui.dialogs.about_dialog import AboutDialog

        dialog = AboutDialog()
        qtbot.addWidget(dialog)
        assert dialog.version_btn is not None
        dialog.version_btn.setText("✓ 已复制")
        dialog._restore_version_button()
        assert dialog.version_btn.text() == f"版本 {dialog.version}"


class TestSettingsDialog:
    """SettingsDialog 测试：构造布局、主题选择切换与密码框可见性。"""

    def test_constructs(self, qtbot: QtBot) -> None:
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

    def test_tab_pages_are_scrollable(self, qtbot: QtBot) -> None:
        """每个设置子页包在滚动区域内（窗口小时可上下滚动，回归修复）。"""
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from PySide6.QtWidgets import QScrollArea

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.tab_widget is not None
        for i in range(dialog.tab_widget.count()):
            page = dialog.tab_widget.widget(i)
            assert isinstance(page, QScrollArea), f"第 {i} 个设置子页不是滚动区域"

    def test_save_config_disk_failure_rolls_back(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        assert panel.wifi_name_edit is not None
        panel.wifi_name_edit.setText("NewWiFi")
        panel.save_config()

        # 落盘失败：内存配置应保持原样
        assert global_config.get("WIFI_NAME") == DEFAULT_CONFIG["WIFI_NAME"]

    def test_save_config_success_persists(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

        assert panel.wifi_name_edit is not None
        panel.wifi_name_edit.setText("NewWiFi")
        panel.save_config()

        assert global_config.get("WIFI_NAME") == "NewWiFi"
        assert (tmp_path / "config.json").exists()
        assert (
            json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["WIFI_NAME"]
            == "NewWiFi"
        )
        assert saved_signals == [True]

    def test_theme_selector(self, qtbot: QtBot) -> None:
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

    def test_get_theme_display_name(self, qtbot: QtBot) -> None:
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

    def test_toggle_password_visibility(self, qtbot: QtBot) -> None:
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

    def test_on_theme_changed(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        assert dialog.theme_combo is not None
        # 切换到 dark 主题
        dark_index = dialog.theme_combo.findData("dark")
        if dark_index >= 0:
            dialog._on_theme_changed(dark_index)
            assert global_config.get("THEME") == "dark"
            # 主题切换应即时持久化（切完直接退出也不回退）
            import json

            saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
            assert saved["THEME"] == "dark"

    def test_on_theme_changed_disk_failure_warns(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """回归（CQ-06）：主题落盘失败应弹提示而非静默，内存主题保留即时生效。"""
        _ensure_qapp()
        from PySide6.QtWidgets import QMessageBox

        import gui.dialogs.settings_panel as sp_mod
        from core.config import DEFAULT_CONFIG

        monkeypatch.setattr(sp_mod, "save_config_to_disk", lambda: False)
        warned: list[bool] = []

        def _record_warning(*args: object, **kwargs: object) -> None:
            warned.append(True)

        monkeypatch.setattr(QMessageBox, "warning", staticmethod(_record_warning))

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)
        assert dialog.theme_combo is not None
        dark_index = dialog.theme_combo.findData("dark")
        assert dark_index >= 0
        dialog._on_theme_changed(dark_index)

        assert warned == [True]  # 失败不再静默
        assert global_config.get("THEME") == "dark"  # 内存主题保留（即时生效优先）


class TestSettingsPanelSaveValidation:
    """SettingsPanel 保存前集中校验：会"静默失效"的配置需经用户确认才落盘。"""

    def _make_panel(self, qtbot: QtBot) -> "SettingsPanel":
        """以默认配置构造设置面板（配置还原由 conftest 的 autouse 夹具负责）。"""
        _ensure_qapp()
        from core.config import DEFAULT_CONFIG

        global_config.clear()
        global_config.update(DEFAULT_CONFIG)

        from gui.dialogs.settings_panel import SettingsPanel

        panel = SettingsPanel()
        qtbot.addWidget(panel)
        return panel

    def _empty_weekly_days_draft(self, panel: "SettingsPanel") -> None:
        """把面板草稿置为"启用自定义规则但每周执行日一个不勾"。"""
        assert panel.date_rule_widget is not None
        assert panel.date_rule_widget.enable_checkbox is not None
        panel.date_rule_widget.enable_checkbox.setChecked(True)
        for checkbox in panel.date_rule_widget.weekday_checkboxes.values():
            checkbox.setChecked(False)

    def test_collect_warnings_empty_weekly_days(self, qtbot: QtBot) -> None:
        """启用自定义规则但每周执行日为空：应产出"任务将不会执行"警告。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "DATE_RULES": {
                "ENABLE_CUSTOM_RULE": True,
                "WEEKLY_EXECUTE_DAYS": [],
                "CUSTOM_HOLIDAY_PERIODS": [],
                "CUSTOM_WORKDAY_PERIODS": [],
            }
        }
        warnings = panel._collect_config_warnings(pending)
        assert warnings == ["启用了自定义日期规则，但未勾选任何每周执行日：任务将不会执行"]

    def test_collect_warnings_no_weekly_days_unenabled_is_clean(self, qtbot: QtBot) -> None:
        """未启用自定义规则时执行日为空不警告（规则本身未启用，无"静默失效"）。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "DATE_RULES": {
                "ENABLE_CUSTOM_RULE": False,
                "WEEKLY_EXECUTE_DAYS": [],
            }
        }
        assert panel._collect_config_warnings(pending) == []

    def test_collect_warnings_overlapping_periods(self, qtbot: QtBot) -> None:
        """自定义区间列表内部的日期重叠应产出警告，附区间名便于定位。

        基础节假日（HOLIDAY_PERIODS）的重叠是既定设计（默认数据"寒假包含
        春节"，core/holidays.py 先到先判），即使重叠也不警告——钉死该口径。
        """
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "HOLIDAY_PERIODS": [
                {"name": "假期A", "start": "2026-01-01", "end": "2026-01-10"},
                {"name": "假期B", "start": "2026-01-05", "end": "2026-01-15"},
            ],
            "DATE_RULES": {
                "CUSTOM_HOLIDAY_PERIODS": [
                    {"name": "自定义假A", "start": "2026-02-01", "end": "2026-02-10"},
                    # 闭区间共享 02-10 边界即有交集
                    {"name": "自定义假B", "start": "2026-02-10", "end": "2026-02-20"},
                ],
                "CUSTOM_WORKDAY_PERIODS": [
                    # 无 name：警告文案应回退到起止日期文本
                    {"name": "", "start": "2026-03-01", "end": "2026-03-05"},
                    {"name": "", "start": "2026-03-04", "end": "2026-03-08"},
                ],
            },
        }
        warnings = panel._collect_config_warnings(pending)
        assert len(warnings) == 2
        assert not any("基础节假日" in w for w in warnings)
        assert any("自定义假期区间" in w and "自定义假A" in w for w in warnings)
        assert any("自定义工作日区间" in w and "2026-03-01~2026-03-05" in w for w in warnings)

    def test_collect_warnings_disjoint_periods_clean(self, qtbot: QtBot) -> None:
        """相离区间（含首尾相接但不共享日期）不应误报重叠。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "HOLIDAY_PERIODS": [
                {"name": "A", "start": "2026-01-01", "end": "2026-01-05"},
                {"name": "B", "start": "2026-01-06", "end": "2026-01-10"},
                {"name": "C", "start": "2026-02-01", "end": "2026-02-10"},
            ]
        }
        assert panel._collect_config_warnings(pending) == []

    def test_collect_warnings_skips_unparseable_periods(self, qtbot: QtBot) -> None:
        """起止无法解析的区间跳过检查（不抛异常、不产出误报）。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "HOLIDAY_PERIODS": [
                {"name": "坏数据", "start": "not-a-date", "end": "2026-01-10"},
                {"name": "正常", "start": "2026-01-01", "end": "2026-01-05"},
            ]
        }
        assert panel._collect_config_warnings(pending) == []

    def test_collect_warnings_duplicate_compensatory_days(self, qtbot: QtBot) -> None:
        """调休上班日重复：应列出重复日期，未重复的不列出。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "COMPENSATORY_WORKDAYS": ["2026-01-04", "2026-01-04", "2026-02-28", "2026-01-04"]
        }
        warnings = panel._collect_config_warnings(pending)
        assert len(warnings) == 1
        assert "重复" in warnings[0]
        assert "2026-01-04" in warnings[0]
        assert "2026-02-28" not in warnings[0]

    def test_collect_warnings_clean_config_returns_empty(self, qtbot: QtBot) -> None:
        """正常配置（有执行日、区间相离、调休无重复）应返回空列表（保存零打扰）。"""
        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "DATE_RULES": {
                "ENABLE_CUSTOM_RULE": True,
                "WEEKLY_EXECUTE_DAYS": [0, 1, 2, 3, 4],
                "CUSTOM_HOLIDAY_PERIODS": [
                    {"name": "假A", "start": "2026-01-01", "end": "2026-01-05"}
                ],
                "CUSTOM_WORKDAY_PERIODS": [
                    {"name": "工A", "start": "2026-02-01", "end": "2026-02-05"}
                ],
            },
            "HOLIDAY_PERIODS": [{"name": "假期", "start": "2026-03-01", "end": "2026-03-05"}],
            "COMPENSATORY_WORKDAYS": ["2026-01-04", "2026-02-28"],
        }
        assert panel._collect_config_warnings(pending) == []

    def test_collect_warnings_default_config_zero_noise(self, qtbot: QtBot) -> None:
        """默认数据（寒假⊇春节重叠的 HOLIDAY_PERIODS）保存必须零警告。

        钉死口径：基础节假日重叠是 core/holidays.py 既定设计（先到先判），
        不参与重叠检查；自定义列表默认为空；调休默认无重复。
        """
        from copy import deepcopy

        from core.config import DEFAULT_CONFIG

        panel = self._make_panel(qtbot)
        pending: dict[str, object] = {
            "DATE_RULES": deepcopy(DEFAULT_CONFIG["DATE_RULES"]),
            "HOLIDAY_PERIODS": deepcopy(DEFAULT_CONFIG["HOLIDAY_PERIODS"]),
            "COMPENSATORY_WORKDAYS": deepcopy(DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"]),
        }
        assert panel._collect_config_warnings(pending) == []

    def test_save_config_warning_dialog_defaults_no(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """含警告时确认框标题应为"配置检查提示"且默认聚焦"否"（防回车误保存）。"""
        from PySide6.QtWidgets import QMessageBox

        panel = self._make_panel(qtbot)
        self._empty_weekly_days_draft(panel)

        captured: dict[str, object] = {}

        def fake_question(
            parent: object,
            title: str,
            text: str,
            buttons: object = None,
            default_button: object = None,
        ) -> object:
            captured["title"] = title
            captured["text"] = text
            captured["buttons"] = buttons
            captured["default_button"] = default_button
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(QMessageBox, "question", staticmethod(fake_question))
        panel.save_config()

        assert captured["title"] == "配置检查提示"
        assert "每周执行日" in str(captured["text"])
        assert "仍要保存" in str(captured["text"])
        assert captured["buttons"] == (
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        assert captured["default_button"] == QMessageBox.StandardButton.No

    def test_save_config_cancel_on_warnings_keeps_config(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """确认框选"否"：不写入 global_config、不落盘、不发 config_saved。"""
        from PySide6.QtWidgets import QMessageBox

        import gui.dialogs.settings_panel as sp_mod

        panel = self._make_panel(qtbot)
        self._empty_weekly_days_draft(panel)

        disk_calls: list[bool] = []

        def _record_disk_call() -> bool:
            disk_calls.append(True)
            return True

        monkeypatch.setattr(sp_mod, "save_config_to_disk", _record_disk_call)
        monkeypatch.setattr(
            QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
        )
        saved_signals: list[bool] = []
        panel.config_saved.connect(lambda: saved_signals.append(True))

        before = global_config.snapshot()
        panel.save_config()

        assert disk_calls == []  # 未落盘
        assert saved_signals == []  # 未发保存成功信号
        assert global_config.snapshot() == before  # 配置未被写入

    def test_save_config_confirm_on_warnings_still_saves(
        self, qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """确认框选"仍要保存"：照常写入 global_config 并落盘（知情确认优先）。"""
        from PySide6.QtWidgets import QMessageBox

        import core.config as cfg_module

        monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))

        panel = self._make_panel(qtbot)
        self._empty_weekly_days_draft(panel)

        question_calls: list[bool] = []

        def _confirm_save(*args: object, **kwargs: object) -> QMessageBox.StandardButton:
            question_calls.append(True)
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(QMessageBox, "question", staticmethod(_confirm_save))

        assert panel.wifi_name_edit is not None
        panel.wifi_name_edit.setText("WarnWiFi")
        panel.save_config()

        assert question_calls == [True]  # 确实弹出了确认框
        assert global_config.get("WIFI_NAME") == "WarnWiFi"
        assert (tmp_path / "config.json").exists()
