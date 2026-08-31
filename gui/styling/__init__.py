"""
样式系统包

统一管理主题配色、全局 QSS、字体常量和组件工厂。
"""

from gui.styling.constants import FontSize, FontStyle
from gui.styling.qss import build_qss
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
    "build_qss",
    "create_dark_theme",
    "create_light_theme",
    # 常量
    "FontSize",
    "FontStyle",
    # 组件工厂
    "LogTextEdit",
    "create_button",
    "create_card_widget",
    "create_label",
    "create_section_title",
    "create_tip_label",
]
