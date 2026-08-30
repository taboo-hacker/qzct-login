"""
gui/styling/widgets.py + theme_manager.py + qss.py 补充测试

覆盖样式工厂函数（create_button/create_label/create_section_title/
create_card_widget/create_tip_label）、LogTextEdit 彩色日志控件、
ThemeManager 主题切换/注册，以及 build_qss 全局样式表的生成。
"""

from PySide6.QtWidgets import QApplication, QLabel

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
    """模块级辅助函数：确保 QApplication 实例存在（控件创建依赖）。"""
    return QApplication.instance() or QApplication([])


class TestCreateButton:
    """create_button 测试：文本、图标前缀与尺寸参数。"""

    def test_creates_button_with_text(self):
        """创建的按钮应显示传入的文本。"""
        _ensure_qapp()
        btn = create_button("Test")
        assert btn.text() == "Test"

    def test_creates_button_with_icon_prefix(self):
        """传入 icon 时应作为文本前缀拼进按钮文案。"""
        _ensure_qapp()
        btn = create_button("Label", icon=">")
        assert ">" in btn.text()

    def test_sets_min_width(self):
        """min_width 参数应映射为按钮的 minimumWidth。"""
        _ensure_qapp()
        btn = create_button("Test", min_width=120)
        assert btn.minimumWidth() == 120

    def test_sets_min_height(self):
        """min_height 参数应映射为按钮的 minimumHeight。"""
        _ensure_qapp()
        btn = create_button("Test", min_height=40)
        assert btn.minimumHeight() == 40

    def test_different_btn_types(self):
        """primary/success/danger/gray 各 btn_type 均能正常创建。"""
        _ensure_qapp()
        for btn_type in ("primary", "success", "danger", "gray"):
            btn = create_button("Test", btn_type=btn_type)
            assert btn is not None


class TestCreateLabel:
    """create_label 测试：文本、加粗、颜色与自动换行参数。"""

    def test_creates_label_with_text(self):
        """创建的标签应显示传入文本。"""
        _ensure_qapp()
        label = create_label("Hello")
        assert label.text() == "Hello"

    def test_bold_font(self):
        """bold=True 时标签字体应为加粗。"""
        _ensure_qapp()
        label = create_label("Bold", bold=True)
        assert label.font().bold() is True

    def test_color_style(self):
        """传入 color 时应写入 styleSheet 的 color 规则。"""
        _ensure_qapp()
        label = create_label("Colored", color="#ff0000")
        assert "color" in label.styleSheet()

    def test_word_wrap(self):
        """word_wrap=True 时标签应启用自动换行。"""
        _ensure_qapp()
        label = create_label("Long text", word_wrap=True)
        assert label.wordWrap() is True


class TestCreateSectionTitle:
    """create_section_title 测试：分区标题的文本与样式。"""

    def test_creates_section_title(self):
        """分区标题应含传入文本且默认加粗。"""
        _ensure_qapp()
        label = create_section_title("Section")
        assert label.text() == "Section"
        assert label.font().bold() is True

    def test_creates_with_icon(self):
        """传入 icon 时应作为前缀拼入标题文本。"""
        _ensure_qapp()
        label = create_section_title("Section", icon=">")
        assert ">" in label.text()


class TestCreateCardWidget:
    """create_card_widget 测试：卡片容器工厂。"""

    def test_returns_frame(self):
        """应返回非 None 的 QFrame 卡片容器。"""
        _ensure_qapp()
        card = create_card_widget()
        assert card is not None
        from PySide6.QtWidgets import QFrame

        assert isinstance(card, QFrame)


class TestCreateTipLabel:
    """create_tip_label 测试：提示文本标签。"""

    def test_creates_tip_label(self):
        """提示标签应含文本、启用换行，并经 role 属性接入全局 QSS。"""
        _ensure_qapp()
        label = create_tip_label("Tip text")
        assert label.text() == "Tip text"
        assert label.wordWrap() is True
        # 颜色由 QSS 按 role=tip 提供（主题切换可自动变色），不使用内联样式
        assert label.property("role") == "tip"
        assert label.styleSheet() == ""


class TestLogTextEdit:
    """LogTextEdit 测试：只读属性、按级别着色追加与主题刷新。"""

    def test_constructs_readonly(self, qtbot):
        """构造后应为只读文本框（日志仅展示不允许编辑）。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert edit.isReadOnly() is True

    def test_document_block_limit(self, qtbot):
        """常驻应用日志应限制文档块数，防止内存无限增长。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert edit.document().maximumBlockCount() > 0

    def test_append_colored_info(self, qtbot):
        """append_colored 追加 INFO 消息后控件应有可见文本。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("test message", "INFO")
        assert edit.toPlainText() != ""

    def test_append_colored_all_levels(self, qtbot):
        """五个标准日志级别逐个追加均应写入成功。"""
        _ensure_qapp()
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            edit = LogTextEdit()
            qtbot.addWidget(edit)
            edit.append_colored(f"msg {level}", level)
            assert "msg" in edit.toPlainText()

    def test_append_colored_unknown_level(self, qtbot):
        """未知日志级别应回退使用 INFO 颜色并不崩溃。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("unknown", "UNKNOWN")
        assert "unknown" in edit.toPlainText()

    def test_update_theme_no_crash(self, qtbot):
        """update_theme 刷新主题配色应正常执行不崩溃。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.update_theme()


class TestThemeManagerExtended:
    """ThemeManager 扩展测试：主题重置、切换、注册与回退行为。"""

    def test_reset(self):
        """reset 后当前主题应回到默认的 light。"""
        ThemeManager.reset()
        assert ThemeManager.current_theme_name() == "light"

    def test_set_theme_valid(self):
        """set_theme("dark") 应切换当前主题为 dark。"""
        ThemeManager.set_theme("dark")
        assert ThemeManager.current_theme_name() == "dark"
        ThemeManager.set_theme("light")

    def test_set_theme_invalid_does_nothing(self):
        """设置不存在的主题名应被忽略，当前主题保持不变。"""
        ThemeManager.set_theme("light")
        ThemeManager.set_theme("nonexistent_theme")
        assert ThemeManager.current_theme_name() == "light"

    def test_available_themes_includes_builtin(self):
        """可用主题列表应包含内置的 light 与 dark。"""
        themes = ThemeManager.available_themes()
        assert "light" in themes
        assert "dark" in themes

    def test_register_custom_theme(self):
        """register_theme 注册自定义主题后应出现在可用列表中。"""
        custom = create_light_theme()
        ThemeManager.register_theme("custom_test", custom)
        assert "custom_test" in ThemeManager.available_themes()

    def test_current_theme_returns_builtin_for_unknown(self):
        """设置未知主题名后 current_theme 回退到内置主题（返回 ThemeColors 而非 None）。"""
        # 直接篡改内部状态模拟脏数据，验证取值端有兜底
        ThemeManager._current_theme_name = "nonexistent"
        result = ThemeManager.current_theme()
        assert isinstance(result, ThemeColors)

    def test_apply_to_widget_sets_theme(self):
        """apply_to_widget 指定主题名时应先切换全局主题再应用样式。"""
        _ensure_qapp()
        widget = QLabel()
        ThemeManager.apply_to_widget(widget, "dark")
        assert ThemeManager.current_theme_name() == "dark"
        ThemeManager.set_theme("light")

    def test_apply_to_widget_no_theme_name(self):
        """不传主题名时应使用当前主题应用样式（不崩溃即可）。"""
        _ensure_qapp()
        widget = QLabel()
        ThemeManager.apply_to_widget(widget)
        # 不崩溃即可


class TestBuildQss:
    """全局 QSS 生成测试：build_qss 按主题变量渲染样式表。"""

    def test_build_qss_contains_theme_colors(self):
        """生成的 QSS 应包含主题的关键颜色变量（primary/window_bg/card_bg/card_border）。"""
        from gui.styling.qss import build_qss

        theme = create_light_theme()
        qss = build_qss(theme)
        assert theme.primary in qss
        assert theme.window_bg in qss
        assert theme.card_bg in qss
        assert theme.card_border in qss

    def test_build_qss_light_and_dark_differ(self):
        """浅色与深色主题生成的 QSS 应不相同。"""
        from gui.styling.qss import build_qss
        from gui.styling.themes import create_dark_theme

        light_qss = build_qss(create_light_theme())
        dark_qss = build_qss(create_dark_theme())
        assert light_qss != dark_qss

    def test_build_qss_colored_buttons_have_disabled_state(self):
        """success/danger/warning 按钮变体应有禁用态样式（否则禁用时仍显示鲜亮实色）。"""
        from gui.styling.qss import build_qss

        qss = build_qss(create_light_theme())
        for btn_type in ("success", "danger", "warning"):
            selector = f'QPushButton[btnType="{btn_type}"]:disabled'
            assert selector in qss, f"{selector} 缺失"

    def test_build_qss_tip_label_role(self):
        """QSS 应包含 role=tip 提示标签规则（create_tip_label 依赖）。"""
        from gui.styling.qss import build_qss

        qss = build_qss(create_light_theme())
        assert 'QLabel[role="tip"]' in qss


class TestButtonQssIntegration:
    """按钮/卡片与全局 QSS 的衔接测试：objectName/property 选择器约定。"""

    def test_button_sets_btn_type_property(self):
        """btn_type 应写入 btnType 动态属性，供 QSS 属性选择器匹配样式。"""
        _ensure_qapp()
        btn = create_button("Test", btn_type="primary")
        assert btn.property("btnType") == "primary"
        btn2 = create_button("Test", btn_type="outline_danger")
        assert btn2.property("btnType") == "outline_danger"

    def test_card_has_card_object_name(self):
        """卡片容器应设置 objectName 为 "card"，供 QSS #card 选择器使用。"""
        _ensure_qapp()
        card = create_card_widget()
        assert card.objectName() == "card"

    def test_log_append_escapes_html(self, qtbot):
        """append_colored 应转义 HTML 特殊字符，防止日志内容被当作富文本渲染。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("<b>bold</b> & <i>x</i>", "INFO")
        # 原文以转义形式进入 HTML 源码，而不是被解释为标签
        assert "&lt;b&gt;" in edit.toHtml()
        assert "<b>bold</b> & <i>x</i>" in edit.toPlainText()
