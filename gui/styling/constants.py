"""
字体与布局常量

字体使用规范：
1. 所有字体大小必须通过 FontSize 类配置
2. QFont 设置使用 FontStyle.normal/bold()
"""

from PyQt5.QtGui import QFont


class FontSize:
    """字体大小配置（单位: pt）"""

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
    """布局常量配置"""

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
