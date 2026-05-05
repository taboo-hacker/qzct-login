from PyQt5.QtGui import QFont

from gui.style_manager import ThemeManager
from gui.themes import ThemeColors

"""
字体使用规范：
1. 所有字体大小必须通过 FontSize 类配置
2. QFont 设置使用 FontStyle.normal/bold()
3. QSS 中的 font-size 必须与 FontSize 配置一致
4. 禁止硬编码字体大小
"""


class FontSize:
    """字体大小配置（单位: pt，QSS 中转换为 px）"""

    MAIN_TITLE = 15
    SUBTITLE = 11
    SECTION_TITLE = 12
    DIALOG_TITLE = 13
    DIALOG_SUBTITLE = 11

    BUTTON_PRIMARY = 11
    BUTTON_SECONDARY = 11
    BUTTON_SMALL = 10
    BUTTON_ICON = 11

    CONTENT_NORMAL = 10
    CONTENT_LARGE = 12
    CONTENT_SMALL = 10

    STATUS_INFO = 10
    STATUS_SUB = 10

    LIST_ITEM = 10

    FORM_LABEL = 10

    COPYRIGHT = 9
    TIP_TEXT = 10

    CALENDAR_NORMAL = 10
    CALENDAR_DETAIL = 10
    CALENDAR_LARGE = 12
    CALENDAR_SMALL = 9


class FontStyle:
    """字体样式配置"""

    FONT_FAMILY = "Microsoft YaHei"
    EMOJI_FAMILY = "Segoe UI Emoji"

    @staticmethod
    def normal(size: int = FontSize.CONTENT_NORMAL) -> QFont:
        return QFont(FontStyle.FONT_FAMILY, size)

    @staticmethod
    def bold(size: int = FontSize.CONTENT_NORMAL) -> QFont:
        return QFont(FontStyle.FONT_FAMILY, size, QFont.Weight.Bold)

    @staticmethod
    def emoji(size: int = 24) -> QFont:
        return QFont(FontStyle.EMOJI_FAMILY, size)


class StyleConstants:
    """样式常量配置 - 使用主题变量"""

    @classmethod
    def _get_theme(cls) -> ThemeColors:
        return ThemeManager.current_theme()

    @classmethod
    def COLOR_PRIMARY(cls) -> str:
        return cls._get_theme().primary

    @classmethod
    def COLOR_PRIMARY_DARK(cls) -> str:
        return cls._get_theme().primary_dark

    @classmethod
    def COLOR_PRIMARY_DARKEST(cls) -> str:
        return cls._get_theme().primary_darkest

    @classmethod
    def COLOR_SUCCESS(cls) -> str:
        return cls._get_theme().success

    @classmethod
    def COLOR_SUCCESS_HOVER(cls) -> str:
        return cls._get_theme().success_hover

    @classmethod
    def COLOR_WARNING(cls) -> str:
        return cls._get_theme().warning

    @classmethod
    def COLOR_WARNING_HOVER(cls) -> str:
        return cls._get_theme().warning_hover

    @classmethod
    def COLOR_DANGER(cls) -> str:
        return cls._get_theme().danger

    @classmethod
    def COLOR_DANGER_HOVER(cls) -> str:
        return cls._get_theme().danger_hover

    @classmethod
    def COLOR_GRAY(cls) -> str:
        return cls._get_theme().gray

    @classmethod
    def COLOR_GRAY_HOVER(cls) -> str:
        return cls._get_theme().gray_hover

    @classmethod
    def COLOR_TEXT(cls) -> str:
        return cls._get_theme().text_primary

    @classmethod
    def COLOR_TEXT_SECOND(cls) -> str:
        return cls._get_theme().text_secondary

    @classmethod
    def COLOR_TEXT_THIRD(cls) -> str:
        return cls._get_theme().text_tertiary

    @classmethod
    def COLOR_BG_LIGHT(cls) -> str:
        return cls._get_theme().background

    @classmethod
    def COLOR_BG_LIGHTER(cls) -> str:
        return cls._get_theme().background_secondary

    @classmethod
    def COLOR_WHITE(cls) -> str:
        return cls._get_theme().surface

    @classmethod
    def COLOR_BORDER(cls) -> str:
        return cls._get_theme().border

    @classmethod
    def COLOR_BG_BLUE(cls) -> str:
        return cls._get_theme().primary_bg

    @classmethod
    def COLOR_BG_GREEN(cls) -> str:
        return cls._get_theme().success_bg

    @classmethod
    def COLOR_BG_RED(cls) -> str:
        return cls._get_theme().danger_bg

    RADIUS_LARGE = 8
    RADIUS_NORMAL = 6
    RADIUS_SMALL = 4
    RADIUS_TINY = 3
    RADIUS_CIRCLE = 50

    SPACING_TIGHT = 8
    SPACING_NORMAL = 16
    SPACING_LOOSE = 24
    SPACING_WIDE = 32

    PADDING_TIGHT = 8
    PADDING_NORMAL = 16
    PADDING_LOOSE = 24
    PADDING_WIDE = 32
    PADDING_EXTRA_WIDE = 40

    BUTTON_HEIGHT = 40
    BUTTON_HEIGHT_SMALL = 32
    BUTTON_MIN_WIDTH = 88
    DIALOG_MIN_WIDTH = 520
    DIALOG_MIN_HEIGHT = 520
