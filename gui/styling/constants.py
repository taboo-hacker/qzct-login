"""
字体常量

字体使用规范：
1. 通用组件（标签/按钮/提示）的字体大小通过 FontSize 类配置
2. QFont 设置统一使用 FontStyle.normal/bold()
3. 日历等自定义视觉视图允许按需指定字号（视觉密度特殊）
"""

from PySide6.QtGui import QFont


class FontSize:
    """字体大小配置（单位: pt）——仅保留实际使用的成员"""

    SECTION_TITLE = 12
    DIALOG_TITLE = 13

    BUTTON_PRIMARY = 11

    CONTENT_NORMAL = 10
    CONTENT_SMALL = 10

    TIP_TEXT = 10


class FontStyle:
    """字体样式配置"""

    FONT_FAMILY = "Microsoft YaHei"

    @staticmethod
    def normal(size: int = FontSize.CONTENT_NORMAL) -> QFont:
        return QFont(FontStyle.FONT_FAMILY, size)

    @staticmethod
    def bold(size: int = FontSize.CONTENT_NORMAL) -> QFont:
        return QFont(FontStyle.FONT_FAMILY, size, QFont.Weight.Bold)
