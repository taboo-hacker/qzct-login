"""
gui/styling/widgets.py + theme_manager.py 补充测试
"""

from PyQt5.QtWidgets import QApplication, QLabel

from gui.styling.theme_manager import ThemeManager
from gui.styling.themes import ThemeColors, create_light_theme
from gui.styling.widgets import (
    LogTextEdit,
    create_button,
    create_card_widget,
    create_label,
    create_section_title,
    create_tip_label,
)


def _ensure_qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


class TestCreateButton:
    """create_button 测试"""

    def test_creates_button_with_text(self):
        _ensure_qapp()
        btn = create_button("Test")
        assert btn.text() == "Test"

    def test_creates_button_with_icon_prefix(self):
        _ensure_qapp()
        btn = create_button("Label", icon=">")
        assert ">" in btn.text()

    def test_sets_min_width(self):
        _ensure_qapp()
        btn = create_button("Test", min_width=120)
        assert btn.minimumWidth() == 120

    def test_sets_min_height(self):
        _ensure_qapp()
        btn = create_button("Test", min_height=40)
        assert btn.minimumHeight() == 40

    def test_different_btn_types(self):
        """不同 btn_type 不崩溃"""
        _ensure_qapp()
        for btn_type in ("primary", "success", "danger", "gray"):
            btn = create_button("Test", btn_type=btn_type)
            assert btn is not None


class TestCreateLabel:
    """create_label 测试"""

    def test_creates_label_with_text(self):
        _ensure_qapp()
        label = create_label("Hello")
        assert label.text() == "Hello"

    def test_bold_font(self):
        _ensure_qapp()
        label = create_label("Bold", bold=True)
        assert label.font().bold() is True

    def test_color_style(self):
        _ensure_qapp()
        label = create_label("Colored", color="#ff0000")
        assert "color" in label.styleSheet()

    def test_word_wrap(self):
        _ensure_qapp()
        label = create_label("Long text", word_wrap=True)
        assert label.wordWrap() is True


class TestCreateSectionTitle:
    """create_section_title 测试"""

    def test_creates_section_title(self):
        _ensure_qapp()
        label = create_section_title("Section")
        assert label.text() == "Section"
        assert label.font().bold() is True

    def test_creates_with_icon(self):
        _ensure_qapp()
        label = create_section_title("Section", icon=">")
        assert ">" in label.text()


class TestCreateCardWidget:
    """create_card_widget 测试"""

    def test_returns_frame(self):
        _ensure_qapp()
        card = create_card_widget()
        assert card is not None
        from PyQt5.QtWidgets import QFrame

        assert isinstance(card, QFrame)


class TestCreateTipLabel:
    """create_tip_label 测试"""

    def test_creates_tip_label(self):
        _ensure_qapp()
        label = create_tip_label("Tip text")
        assert label.text() == "Tip text"
        assert label.wordWrap() is True
        assert "color" in label.styleSheet()


class TestLogTextEdit:
    """LogTextEdit 测试"""

    def test_constructs_readonly(self, qtbot):
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert edit.isReadOnly() is True

    def test_append_colored_info(self, qtbot):
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("test message", "INFO")
        assert edit.toPlainText() != ""

    def test_append_colored_all_levels(self, qtbot):
        _ensure_qapp()
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            edit = LogTextEdit()
            qtbot.addWidget(edit)
            edit.append_colored(f"msg {level}", level)
            assert "msg" in edit.toPlainText()

    def test_append_colored_unknown_level(self, qtbot):
        """未知日志级别使用 INFO 颜色"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("unknown", "UNKNOWN")
        assert "unknown" in edit.toPlainText()

    def test_update_theme_no_crash(self, qtbot):
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.update_theme()


class TestThemeManagerExtended:
    """ThemeManager 扩展测试"""

    def test_reset(self):
        ThemeManager.reset()
        assert ThemeManager.current_theme_name() == "light"

    def test_set_theme_valid(self):
        ThemeManager.set_theme("dark")
        assert ThemeManager.current_theme_name() == "dark"
        ThemeManager.set_theme("light")

    def test_set_theme_invalid_does_nothing(self):
        ThemeManager.set_theme("light")
        ThemeManager.set_theme("nonexistent_theme")
        assert ThemeManager.current_theme_name() == "light"

    def test_available_themes_includes_builtin(self):
        themes = ThemeManager.available_themes()
        assert "light" in themes
        assert "dark" in themes

    def test_register_custom_theme(self):
        custom = create_light_theme()
        ThemeManager.register_theme("custom_test", custom)
        assert "custom_test" in ThemeManager.available_themes()

    def test_current_theme_returns_builtin_for_unknown(self):
        """设置未知主题名后 current_theme 回退到 light"""
        ThemeManager._current_theme_name = "nonexistent"
        result = ThemeManager.current_theme()
        assert isinstance(result, ThemeColors)

    def test_apply_to_widget_sets_theme(self):
        _ensure_qapp()
        widget = QLabel()
        ThemeManager.apply_to_widget(widget, "dark")
        assert ThemeManager.current_theme_name() == "dark"
        ThemeManager.set_theme("light")

    def test_apply_to_widget_no_theme_name(self):
        _ensure_qapp()
        widget = QLabel()
        ThemeManager.apply_to_widget(widget)
        # 不崩溃即可
