"""
样式管理器

使用 Qt Fusion 原生风格，不注入自定义 QSS。
ThemeManager 仅保留日志级别配色等最小必要配色。
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget

from gui.styling.themes import BUILTIN_THEMES, ThemeColors


class ThemeManager:
    _instance: Optional["ThemeManager"] = None
    _current_theme_name: str = "light"

    def __init__(self) -> None:
        self._custom_themes: dict[str, ThemeColors] = {}

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._current_theme_name = "light"

    @classmethod
    def current_theme(cls) -> ThemeColors:
        name = cls._current_theme_name
        if name in BUILTIN_THEMES:
            return BUILTIN_THEMES[name]
        if cls._instance and name in cls._instance._custom_themes:
            return cls._instance._custom_themes[name]
        return BUILTIN_THEMES["light"]

    @classmethod
    def current_theme_name(cls) -> str:
        return cls._current_theme_name

    @classmethod
    def set_theme(cls, theme_name: str) -> None:
        if theme_name not in BUILTIN_THEMES and not (
            cls._instance and theme_name in cls._instance._custom_themes
        ):
            return
        cls._current_theme_name = theme_name

    @classmethod
    def available_themes(cls) -> list[str]:
        names = list(BUILTIN_THEMES.keys())
        if cls._instance:
            names.extend(cls._instance._custom_themes.keys())
        return names

    @classmethod
    def register_theme(cls, name: str, colors: ThemeColors) -> None:
        if cls._instance is None:
            cls._instance = cls()
        cls._instance._custom_themes[name] = colors

    @classmethod
    def apply_to_widget(cls, widget: QWidget, theme_name: str | None = None) -> None:  # noqa: ARG003
        """Fusion 风格下无需注入 QSS"""
        if theme_name:
            cls.set_theme(theme_name)
