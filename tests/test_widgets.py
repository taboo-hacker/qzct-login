"""
gui/widgets/* 补充测试

覆盖 BaseListEditorWidget, BaseHolidayWidget, CompensatoryWorkdayWidget, DateRuleWidget。
"""

from PySide6.QtWidgets import QApplication

from core.config import global_config


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class TestBaseListEditorWidget:
    """BaseListEditorWidget 基类测试"""

    def _make_concrete_editor(self, columns=None, title="", tip=""):
        """创建可实例化的子类（基类是抽象的，__init__ 调用 refresh 触发 _get_items）"""
        from PySide6.QtWidgets import QTableWidgetItem

        from gui.widgets.base_list_editor import BaseListEditorWidget

        class ConcreteEditor(BaseListEditorWidget):
            def __init__(self_):
                self_._items = []
                super().__init__(title=title, tip=tip, columns=columns or [])

            def _get_items(self_):
                return self_._items

            def _set_items(self_, items):
                self_._items = items

            def _row_to_cells(self_, item):
                return [QTableWidgetItem(str(item))]

            def _add_item(self_):
                pass

            def _edit_item(self_, row):
                pass

        return ConcreteEditor()

    def test_constructs_with_columns(self, qtbot):
        _ensure_qapp()
        widget = self._make_concrete_editor(columns=["Col1", "Col2"], title="Test", tip="Test tip")
        qtbot.addWidget(widget)
        assert widget.table is not None
        assert widget.table.columnCount() == 2

    def test_constructs_without_title(self, qtbot):
        _ensure_qapp()
        widget = self._make_concrete_editor()
        qtbot.addWidget(widget)
        assert widget.table is not None

    def test_refresh_populates_table(self, qtbot):
        _ensure_qapp()
        from gui.widgets.base_list_editor import BaseListEditorWidget

        class TestEditor(BaseListEditorWidget):
            def __init__(self):
                self._items = [{"name": "A", "start": "2026-01-01", "end": "2026-01-02"}]
                super().__init__(columns=["Name", "Start", "End"])

            def _get_items(self):
                return self._items

            def _set_items(self, items):
                self._items = items

            def _row_to_cells(self, item):
                from PySide6.QtWidgets import QTableWidgetItem

                return [
                    QTableWidgetItem(item["name"]),
                    QTableWidgetItem(item["start"]),
                    QTableWidgetItem(item["end"]),
                ]

        editor = TestEditor()
        qtbot.addWidget(editor)
        assert editor.table.rowCount() == 1

    def test_clear_all(self, qtbot):
        _ensure_qapp()
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from gui.widgets.base_list_editor import BaseListEditorWidget

        class TestEditor(BaseListEditorWidget):
            def __init__(self):
                self._items = [{"name": "A"}]
                super().__init__(columns=["Name"])

            def _get_items(self):
                return self._items

            def _set_items(self, items):
                self._items = items

            def _row_to_cells(self, item):
                from PySide6.QtWidgets import QTableWidgetItem

                return [QTableWidgetItem(item["name"])]

        editor = TestEditor()
        qtbot.addWidget(editor)
        with patch(
            "gui.widgets.base_list_editor.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            editor.clear_all()
            assert len(editor._items) == 0

    def test_delete_item(self, qtbot):
        _ensure_qapp()
        from gui.widgets.base_list_editor import BaseListEditorWidget

        class TestEditor(BaseListEditorWidget):
            def __init__(self):
                self._items = [{"name": "A"}, {"name": "B"}]
                super().__init__(columns=["Name"])

            def _get_items(self):
                return self._items

            def _set_items(self, items):
                self._items = items

            def _row_to_cells(self, item):
                from PySide6.QtWidgets import QTableWidgetItem

                return [QTableWidgetItem(item["name"])]

        editor = TestEditor()
        qtbot.addWidget(editor)
        # 选中第一行
        editor.table.selectRow(0)
        editor.delete_item()
        assert len(editor._items) == 1
        assert editor._items[0]["name"] == "B"

    def test_edit_item_no_selection(self, qtbot):
        """无选中行时不崩溃"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.widgets.base_list_editor import BaseListEditorWidget

        class TestEditor(BaseListEditorWidget):
            def __init__(self):
                self._items = []
                super().__init__(columns=["Name"])

            def _get_items(self):
                return self._items

            def _set_items(self, items):
                self._items = items

            def _row_to_cells(self, item):
                from PySide6.QtWidgets import QTableWidgetItem

                return [QTableWidgetItem(str(item))]

            def _edit_item(self, row):
                pass

        editor = TestEditor()
        qtbot.addWidget(editor)
        with patch("gui.widgets.base_list_editor.QMessageBox.warning"):
            editor.edit_item()  # 无选中行

    def test_sort_items_default_none(self, qtbot):
        """默认 _sort_items 返回 None"""
        _ensure_qapp()
        widget = self._make_concrete_editor(columns=["A"])
        qtbot.addWidget(widget)
        assert widget._sort_items([3, 1, 2]) is None

    def test_get_select_warning_text(self, qtbot):
        _ensure_qapp()
        widget = self._make_concrete_editor()
        qtbot.addWidget(widget)
        assert "请先选择" in widget._get_select_warning_text()

    def test_get_clear_confirm_text(self, qtbot):
        _ensure_qapp()
        widget = self._make_concrete_editor()
        qtbot.addWidget(widget)
        assert "确定" in widget._get_clear_confirm_text()

    def test_update_theme_no_crash(self, qtbot):
        _ensure_qapp()
        widget = self._make_concrete_editor()
        qtbot.addWidget(widget)
        widget.update_theme()


class TestBaseHolidayWidget:
    """BaseHolidayWidget 测试"""

    def test_constructs(self, qtbot):
        _ensure_qapp()
        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        assert widget.name_edit is not None
        assert widget.start_edit is not None
        assert widget.end_edit is not None

    def test_add_item(self, qtbot):
        _ensure_qapp()
        from PySide6.QtCore import QDate

        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        widget.name_edit.setText("测试假期")
        widget.start_edit.setDate(QDate(2026, 1, 1))
        widget.end_edit.setDate(QDate(2026, 1, 7))
        widget._add_item()
        assert len(widget.holiday_periods) == 1
        assert widget.holiday_periods[0]["name"] == "测试假期"

    def test_add_item_empty_name(self, qtbot):
        """空名称不添加"""
        _ensure_qapp()
        from unittest.mock import patch

        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        widget.name_edit.setText("")
        with patch("gui.widgets.holiday_widget.QMessageBox.warning"):
            widget._add_item()
        assert len(widget.holiday_periods) == 0

    def test_add_item_invalid_dates(self, qtbot):
        """开始日期晚于结束日期不添加"""
        _ensure_qapp()
        from PySide6.QtCore import QDate

        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        widget.name_edit.setText("测试")
        widget.start_edit.setDate(QDate(2026, 1, 10))
        widget.end_edit.setDate(QDate(2026, 1, 5))
        from unittest.mock import patch

        with patch("gui.widgets.holiday_widget.QMessageBox.warning"):
            widget._add_item()
        assert len(widget.holiday_periods) == 0

    def test_sort_items(self, qtbot):
        _ensure_qapp()
        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        items = [
            {"name": "B", "start": "2026-02-01", "end": "2026-02-07"},
            {"name": "A", "start": "2026-01-01", "end": "2026-01-07"},
        ]
        sorted_items = widget._sort_items(items)
        assert sorted_items[0]["name"] == "A"

    def test_save_holidays(self, qtbot):
        _ensure_qapp()
        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        widget.holiday_periods = [{"name": "测试", "start": "2026-01-01", "end": "2026-01-03"}]
        widget.save_holidays()
        assert global_config["HOLIDAY_PERIODS"] == widget.holiday_periods

    def test_row_to_cells(self, qtbot):
        _ensure_qapp()
        from gui.widgets.holiday_widget import BaseHolidayWidget

        global_config.clear()
        global_config.update({"HOLIDAY_PERIODS": []})

        widget = BaseHolidayWidget()
        qtbot.addWidget(widget)
        cells = widget._row_to_cells({"name": "测试", "start": "2026-01-01", "end": "2026-01-03"})
        assert len(cells) == 3


class TestCompensatoryWorkdayWidget:
    """CompensatoryWorkdayWidget 测试"""

    def test_constructs(self, qtbot):
        _ensure_qapp()
        from gui.widgets.compensatory_widget import CompensatoryWorkdayWidget

        global_config.clear()
        global_config.update({"COMPENSATORY_WORKDAYS": ["2026-01-04"]})

        widget = CompensatoryWorkdayWidget()
        qtbot.addWidget(widget)
        assert len(widget.compensatory_days) == 1

    def test_row_to_cells(self, qtbot):
        _ensure_qapp()
        from gui.widgets.compensatory_widget import CompensatoryWorkdayWidget

        global_config.clear()
        global_config.update({"COMPENSATORY_WORKDAYS": []})

        widget = CompensatoryWorkdayWidget()
        qtbot.addWidget(widget)
        cells = widget._row_to_cells({"name": "2026-01-04", "date": "2026-01-04"})
        assert len(cells) == 2

    def test_sort_items(self, qtbot):
        _ensure_qapp()
        from gui.widgets.compensatory_widget import CompensatoryWorkdayWidget

        global_config.clear()
        global_config.update({"COMPENSATORY_WORKDAYS": []})

        widget = CompensatoryWorkdayWidget()
        qtbot.addWidget(widget)
        items = [
            {"name": "2026-02-01", "date": "2026-02-01"},
            {"name": "2026-01-01", "date": "2026-01-01"},
        ]
        sorted_items = widget._sort_items(items)
        assert sorted_items[0]["date"] == "2026-01-01"

    def test_save_days(self, qtbot):
        _ensure_qapp()
        from gui.widgets.compensatory_widget import CompensatoryWorkdayWidget

        global_config.clear()
        global_config.update({"COMPENSATORY_WORKDAYS": []})

        widget = CompensatoryWorkdayWidget()
        qtbot.addWidget(widget)
        widget.compensatory_days = [
            {"name": "2026-01-04", "date": "2026-01-04"},
            {"name": "2026-01-05", "date": "2026-01-05"},
        ]
        widget.save_days()
        assert global_config["COMPENSATORY_WORKDAYS"] == ["2026-01-04", "2026-01-05"]


class TestDateRuleWidget:
    """DateRuleWidget 测试"""

    def test_constructs(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        assert widget.enable_checkbox is not None
        assert widget.type_combo is not None
        assert len(widget.weekday_checkboxes) == 7

    def test_get_items_combined(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update(
            {
                "DATE_RULES": {
                    "CUSTOM_WORKDAY_PERIODS": [
                        {"name": "W1", "start": "2026-01-04", "end": "2026-01-05"}
                    ],
                    "CUSTOM_HOLIDAY_PERIODS": [
                        {"name": "H1", "start": "2026-01-01", "end": "2026-01-03"}
                    ],
                }
            }
        )

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        items = widget._get_items()
        assert len(items) == 2
        assert any(item.get("_type") == "workday" for item in items)
        assert any(item.get("_type") == "holiday" for item in items)

    def test_set_items(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        items = [
            {"name": "W1", "start": "2026-01-04", "end": "2026-01-05", "_type": "workday"},
            {"name": "H1", "start": "2026-01-01", "end": "2026-01-03", "_type": "holiday"},
        ]
        widget._set_items(items)
        assert len(widget.date_rules["CUSTOM_WORKDAY_PERIODS"]) == 1
        assert len(widget.date_rules["CUSTOM_HOLIDAY_PERIODS"]) == 1

    def test_row_to_cells(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        cells = widget._row_to_cells(
            {"name": "Test", "start": "2026-01-01", "end": "2026-01-03", "_type": "workday"}
        )
        assert len(cells) == 4
        assert cells[3].text() == "工作日"

    def test_row_to_cells_holiday(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        cells = widget._row_to_cells(
            {"name": "Test", "start": "2026-01-01", "end": "2026-01-03", "_type": "holiday"}
        )
        assert cells[3].text() == "假期"

    def test_save_rules(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        widget.enable_checkbox.setChecked(True)
        widget.save_rules()
        assert global_config["DATE_RULES"]["ENABLE_CUSTOM_RULE"] is True

    def test_save_rules_weekly_days(self, qtbot):
        _ensure_qapp()
        from gui.widgets.date_rule_widget import DateRuleWidget

        global_config.clear()
        global_config.update({"DATE_RULES": {}})

        widget = DateRuleWidget()
        qtbot.addWidget(widget)
        # 勾选周一和周三
        widget.weekday_checkboxes[0].setChecked(True)
        widget.weekday_checkboxes[2].setChecked(True)
        widget.save_rules()
        assert 0 in global_config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
        assert 2 in global_config["DATE_RULES"]["WEEKLY_EXECUTE_DAYS"]
