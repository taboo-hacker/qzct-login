"""
样式系统包

统一管理主题配色、字体常量、布局常量和组件工厂。
"""

from gui.styling.constants import FontSize, FontStyle, StyleConstants
from gui.styling.theme_manager import ThemeManager
from gui.styling.themes import BUILTIN_THEMES, ThemeColors, create_dark_theme, create_light_theme
from gui.styling.widgets import (
    LogTextEdit,
    create_button,
    create_card_widget,
    create_label,
    create_section_title,
    create_tip_label,
)

__all__ = [
    # 主题
    "BUILTIN_THEMES",
    "ThemeColors",
    "ThemeManager",
    "create_dark_theme",
    "create_light_theme",
    # 常量
    "FontSize",
    "FontStyle",
    "StyleConstants",
    # 组件工厂
    "LogTextEdit",
    "create_button",
    "create_card_widget",
    "create_label",
    "create_section_title",
    "create_tip_label",
]
