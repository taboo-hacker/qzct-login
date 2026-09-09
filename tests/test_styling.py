"""
gui/styling/widgets.py + theme_manager.py + qss.py 补充测试

覆盖样式工厂函数（create_button/create_label/create_section_title/
create_card_widget/create_tip_label）、LogTextEdit 彩色日志控件、
ThemeManager 主题切换/注册，以及 build_qss 全局样式表的生成。
"""

from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from gui.styling.theme_manager import ThemeManager
from gui.styling.themes import ThemeColors, create_light_theme
from gui.styling.widgets import (
    LogTextEdit,
    create_button,
    create_card_widget,
    create_label,
    create_section_title,
    create_tip_label,
    is_scrolled_to_bottom,
)
from tests.conftest import ensure_qapp as _ensure_qapp


class TestCreateButton:
    """create_button 测试：文本、图标前缀与尺寸参数。"""

    def test_creates_button_with_text(self) -> None:
        """创建的按钮应显示传入的文本。"""
        _ensure_qapp()
        btn = create_button("Test")
        assert btn.text() == "Test"

    def test_creates_button_with_icon_prefix(self) -> None:
        """传入 icon 时应作为文本前缀拼进按钮文案。"""
        _ensure_qapp()
        btn = create_button("Label", icon=">")
        assert ">" in btn.text()

    def test_sets_min_width(self) -> None:
        """min_width 参数应映射为按钮的 minimumWidth。"""
        _ensure_qapp()
        btn = create_button("Test", min_width=120)
        assert btn.minimumWidth() == 120

    def test_sets_min_height(self) -> None:
        """min_height 参数应映射为按钮的 minimumHeight。"""
        _ensure_qapp()
        btn = create_button("Test", min_height=40)
        assert btn.minimumHeight() == 40

    def test_different_btn_types(self) -> None:
        """primary/success/danger/gray 各 btn_type 均能正常创建。"""
        _ensure_qapp()
        for btn_type in ("primary", "success", "danger", "gray"):
            btn = create_button("Test", btn_type=btn_type)
            assert btn is not None


class TestCreateLabel:
    """create_label 测试：文本、加粗、颜色与自动换行参数。"""

    def test_creates_label_with_text(self) -> None:
        """创建的标签应显示传入文本。"""
        _ensure_qapp()
        label = create_label("Hello")
        assert label.text() == "Hello"

    def test_bold_font(self) -> None:
        """bold=True 时标签字体应为加粗。"""
        _ensure_qapp()
        label = create_label("Bold", bold=True)
        assert label.font().bold() is True

    def test_color_style(self) -> None:
        """传入 color 时应写入 styleSheet 的 color 规则。"""
        _ensure_qapp()
        label = create_label("Colored", color="#ff0000")
        assert "color" in label.styleSheet()

    def test_word_wrap(self) -> None:
        """word_wrap=True 时标签应启用自动换行。"""
        _ensure_qapp()
        label = create_label("Long text", word_wrap=True)
        assert label.wordWrap() is True


class TestCreateSectionTitle:
    """create_section_title 测试：分区标题的文本与样式。"""

    def test_creates_section_title(self) -> None:
        """分区标题应含传入文本且默认加粗。"""
        _ensure_qapp()
        label = create_section_title("Section")
        assert label.text() == "Section"
        assert label.font().bold() is True

    def test_creates_with_icon(self) -> None:
        """传入 icon 时应作为前缀拼入标题文本。"""
        _ensure_qapp()
        label = create_section_title("Section", icon=">")
        assert ">" in label.text()


class TestCreateCardWidget:
    """create_card_widget 测试：卡片容器工厂。"""

    def test_returns_frame(self) -> None:
        """应返回非 None 的 QFrame 卡片容器。"""
        _ensure_qapp()
        card = create_card_widget()
        assert card is not None
        from PySide6.QtWidgets import QFrame

        assert isinstance(card, QFrame)


class TestCreateTipLabel:
    """create_tip_label 测试：提示文本标签。"""

    def test_creates_tip_label(self) -> None:
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

    def test_constructs_readonly(self, qtbot: QtBot) -> None:
        """构造后应为只读文本框（日志仅展示不允许编辑）。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert edit.isReadOnly() is True

    def test_document_block_limit(self, qtbot: QtBot) -> None:
        """常驻应用日志应限制文档块数，防止内存无限增长。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert edit.document().maximumBlockCount() > 0

    def test_append_colored_info(self, qtbot: QtBot) -> None:
        """append_colored 追加 INFO 消息后控件应有可见文本。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("test message", "INFO")
        assert edit.toPlainText() != ""

    def test_append_colored_all_levels(self, qtbot: QtBot) -> None:
        """五个标准日志级别逐个追加均应写入成功。"""
        _ensure_qapp()
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            edit = LogTextEdit()
            qtbot.addWidget(edit)
            edit.append_colored(f"msg {level}", level)
            assert "msg" in edit.toPlainText()

    def test_append_colored_unknown_level(self, qtbot: QtBot) -> None:
        """未知日志级别应回退使用 INFO 颜色并不崩溃。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("unknown", "UNKNOWN")
        assert "unknown" in edit.toPlainText()

    def test_no_theme_hook_remains(self) -> None:
        """LogTextEdit 的主题空钩子（update_theme/_update_colors）应已移除。"""
        _ensure_qapp()
        assert not hasattr(LogTextEdit, "update_theme")
        assert not hasattr(LogTextEdit, "_update_colors")


class TestThemeManagerExtended:
    """ThemeManager 扩展测试：主题重置、切换、注册与回退行为。"""

    def test_reset(self) -> None:
        """reset 后当前主题应回到默认的 light。"""
        ThemeManager.reset()
        assert ThemeManager.current_theme_name() == "light"

    def test_set_theme_valid(self) -> None:
        """set_theme("dark") 应切换当前主题为 dark。"""
        ThemeManager.set_theme("dark")
        assert ThemeManager.current_theme_name() == "dark"
        ThemeManager.set_theme("light")

    def test_set_theme_invalid_does_nothing(self) -> None:
        """设置不存在的主题名应被忽略，当前主题保持不变。"""
        ThemeManager.set_theme("light")
        ThemeManager.set_theme("nonexistent_theme")
        assert ThemeManager.current_theme_name() == "light"

    def test_available_themes_includes_builtin(self) -> None:
        """可用主题列表应包含内置的 light 与 dark。"""
        themes = ThemeManager.available_themes()
        assert "light" in themes
        assert "dark" in themes

    def test_register_custom_theme(self) -> None:
        """register_theme 注册自定义主题后应出现在可用列表中。"""
        custom = create_light_theme()
        ThemeManager.register_theme("custom_test", custom)
        assert "custom_test" in ThemeManager.available_themes()

    def test_current_theme_returns_builtin_for_unknown(self) -> None:
        """设置未知主题名后 current_theme 回退到内置主题（返回 ThemeColors 而非 None）。"""
        # 直接篡改内部状态模拟脏数据，验证取值端有兜底
        ThemeManager._current_theme_name = "nonexistent"
        result = ThemeManager.current_theme()
        assert isinstance(result, ThemeColors)


class TestBuildQss:
    """全局 QSS 生成测试：build_qss 按主题变量渲染样式表。"""

    def test_build_qss_contains_theme_colors(self) -> None:
        """生成的 QSS 应包含主题的关键颜色变量（primary/window_bg/card_bg/card_border）。"""
        from gui.styling.qss import build_qss

        theme = create_light_theme()
        qss = build_qss(theme)
        assert theme.primary in qss
        assert theme.window_bg in qss
        assert theme.card_bg in qss
        assert theme.card_border in qss

    def test_build_qss_light_and_dark_differ(self) -> None:
        """浅色与深色主题生成的 QSS 应不相同。"""
        from gui.styling.qss import build_qss
        from gui.styling.themes import create_dark_theme

        light_qss = build_qss(create_light_theme())
        dark_qss = build_qss(create_dark_theme())
        assert light_qss != dark_qss

    def test_build_qss_colored_buttons_have_disabled_state(self) -> None:
        """success/danger/warning 按钮变体应有禁用态样式（否则禁用时仍显示鲜亮实色）。"""
        from gui.styling.qss import build_qss

        qss = build_qss(create_light_theme())
        for btn_type in ("success", "danger", "warning"):
            selector = f'QPushButton[btnType="{btn_type}"]:disabled'
            assert selector in qss, f"{selector} 缺失"

    def test_build_qss_tip_label_role(self) -> None:
        """QSS 应包含 role=tip 提示标签规则（create_tip_label 依赖）。"""
        from gui.styling.qss import build_qss

        qss = build_qss(create_light_theme())
        assert 'QLabel[role="tip"]' in qss


class TestButtonQssIntegration:
    """按钮/卡片与全局 QSS 的衔接测试：objectName/property 选择器约定。"""

    def test_button_sets_btn_type_property(self) -> None:
        """btn_type 应写入 btnType 动态属性，供 QSS 属性选择器匹配样式。"""
        _ensure_qapp()
        btn = create_button("Test", btn_type="primary")
        assert btn.property("btnType") == "primary"
        btn2 = create_button("Test", btn_type="outline_danger")
        assert btn2.property("btnType") == "outline_danger"

    def test_card_has_card_object_name(self) -> None:
        """卡片容器应设置 objectName 为 "card"，供 QSS #card 选择器使用。"""
        _ensure_qapp()
        card = create_card_widget()
        assert card.objectName() == "card"

    def test_log_append_escapes_html(self, qtbot: QtBot) -> None:
        """append_colored 应转义 HTML 特殊字符，防止日志内容被当作富文本渲染。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.append_colored("<b>bold</b> & <i>x</i>", "INFO")
        # 原文以转义形式进入 HTML 源码，而不是被解释为标签
        assert "&lt;b&gt;" in edit.toHtml()
        assert "<b>bold</b> & <i>x</i>" in edit.toPlainText()


def _relative_luminance(hex_color: str) -> float:
    """WCAG 相对亮度：sRGB 通道线性化后按 0.2126/0.7152/0.0722 加权。"""
    value = hex_color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 对比度：(L1+0.05)/(L2+0.05)，L1 为较亮一方。"""
    lighter, darker = sorted((_relative_luminance(fg), _relative_luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


class TestPrimaryFgContrast:
    """primary_fg 对比度回归测试（UX-06）：彩色前景文字对实际背景 ≥ WCAG AA。"""

    def test_dark_primary_fg_meets_aa_on_tab_and_card_backgrounds(self) -> None:
        """暗色 primary_fg 对 tab 背景（window_bg）与卡片背景均应 ≥ 4.5:1。"""
        from gui.styling.themes import create_dark_theme

        dark = create_dark_theme()
        assert _contrast_ratio(dark.primary_fg, dark.window_bg) >= 4.5
        assert _contrast_ratio(dark.primary_fg, dark.card_bg) >= 4.5

    def test_dark_primary_fg_meets_aa_on_outline_hover_background(self) -> None:
        """暗色 outline 按钮 hover 底（primary_bg）上的 primary_fg 也应 ≥ 4.5:1。"""
        from gui.styling.themes import create_dark_theme

        dark = create_dark_theme()
        assert _contrast_ratio(dark.primary_fg, dark.primary_bg) >= 4.5

    def test_light_primary_fg_meets_aa_and_does_not_regress(self) -> None:
        """亮色 primary_fg 对应组合应 ≥ 4.5:1，且不差于原 primary（不回归）。"""
        from gui.styling.themes import create_light_theme

        light = create_light_theme()
        assert _contrast_ratio(light.primary_fg, light.window_bg) >= 4.5
        assert _contrast_ratio(light.primary_fg, light.card_bg) >= 4.5
        assert _contrast_ratio(light.primary_fg, light.primary_bg) >= 4.5
        # 不回归：替换原 primary 的场景下对比度只允许更严格
        assert _contrast_ratio(light.primary_fg, light.window_bg) >= _contrast_ratio(
            light.primary, light.window_bg
        )
        assert _contrast_ratio(light.primary_fg, light.card_bg) >= _contrast_ratio(
            light.primary, light.card_bg
        )


class TestBuildQssFgAndFocus:
    """primary_fg 消费与键盘焦点规则测试（UX-06 / UX-05）。"""

    def test_outline_button_and_selected_tab_use_primary_fg(self) -> None:
        """outline 按钮与 tab 选中态的文字/边框应使用 primary_fg（而非 primary）。"""
        from gui.styling.qss import build_qss
        from gui.styling.themes import create_dark_theme, create_light_theme

        for theme in (create_light_theme(), create_dark_theme()):
            qss = build_qss(theme)
            outline_block = qss.split('QPushButton[btnType="outline"] {')[1].split("}")[0]
            assert theme.primary_fg in outline_block, f"{theme.name}: outline 未用 primary_fg"
            assert theme.primary not in outline_block, f"{theme.name}: outline 残留 primary"
            tab_block = qss.split("QTabBar::tab:selected {")[1].split("}")[0]
            assert theme.primary_fg in tab_block, f"{theme.name}: tab 选中态未用 primary_fg"
            assert theme.primary not in tab_block, f"{theme.name}: tab 选中态残留 primary"

    def test_qss_contains_keyboard_focus_rules_for_button_and_tab(self) -> None:
        """两主题 QSS 均应包含 QPushButton:focus 与 QTabBar::tab:focus 规则。"""
        from gui.styling.qss import build_qss
        from gui.styling.themes import create_dark_theme, create_light_theme

        for theme in (create_light_theme(), create_dark_theme()):
            qss = build_qss(theme)
            assert "QPushButton:focus" in qss, f"{theme.name}: 缺少 QPushButton:focus 规则"
            assert "QTabBar::tab:focus" in qss, f"{theme.name}: 缺少 QTabBar::tab:focus 规则"


class TestLogSmartScroll:
    """日志自动滚动策略：贴着底部才跟随，上滚查阅历史时不被拽回。

    回归：此前每条日志都无条件 ensureCursorVisible()，任务运行期间
    日志密集刷屏，用户上滚查看出错历史会被不断拽回底部。
    """

    def _make_scrolled_edit(self, qtbot: QtBot) -> LogTextEdit:
        """构造一个已填充多行、且滚动条可滚动的日志控件。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        edit.resize(240, 80)
        edit.show()
        for idx in range(200):
            edit.append_colored(f"line {idx}", "INFO")
        QApplication.processEvents()
        return edit

    def test_is_scrolled_to_bottom_true_on_fresh_widget(self, qtbot: QtBot) -> None:
        """空控件滚动条无内容，应视为在底部（首条日志需要跟随滚动）。"""
        _ensure_qapp()
        edit = LogTextEdit()
        qtbot.addWidget(edit)
        assert is_scrolled_to_bottom(edit) is True

    def test_is_scrolled_to_bottom_false_after_scrolling_up(self, qtbot: QtBot) -> None:
        """上滚到顶部后不应判定为在底部。"""
        edit = self._make_scrolled_edit(qtbot)
        scrollbar = edit.verticalScrollBar()
        assert scrollbar.maximum() > 0, "测试前置条件：内容需足以产生滚动条"
        scrollbar.setValue(0)
        assert is_scrolled_to_bottom(edit) is False

    def test_append_keeps_position_when_scrolled_up(self, qtbot: QtBot) -> None:
        """用户上滚后追加日志，滚动位置应保持不变。"""
        edit = self._make_scrolled_edit(qtbot)
        scrollbar = edit.verticalScrollBar()
        scrollbar.setValue(0)
        before = scrollbar.value()

        edit.append_colored("new line while reading history", "INFO")
        QApplication.processEvents()

        assert scrollbar.value() == before, "追加日志不应把用户拽回底部"

    def test_append_follows_when_at_bottom(self, qtbot: QtBot) -> None:
        """用户贴着底部时，追加日志应继续跟随到最新一行。"""
        edit = self._make_scrolled_edit(qtbot)
        scrollbar = edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        edit.append_colored("new line while following", "INFO")
        QApplication.processEvents()

        assert is_scrolled_to_bottom(edit) is True
