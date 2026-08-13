"""
样式管理器

统一管理主题配色与全局 QSS 样式表：切换主题时重新生成 QSS
并应用到 QApplication，所有窗口与对话框立即重绘（真实主题切换）。
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
        """设置当前主题并立即应用全局 QSS（若 QApplication 已存在）。"""
        if theme_name not in BUILTIN_THEMES and not (
            cls._instance and theme_name in cls._instance._custom_themes
        ):
            return
        cls._current_theme_name = theme_name
        cls._apply_qss()

    @classmethod
    def _apply_qss(cls) -> None:
        """将当前主题的全局 QSS 应用到 QApplication（尚未创建时跳过）。"""
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        from gui.styling.qss import build_qss

        app.setStyleSheet(build_qss(cls.current_theme()))

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
    def apply_to_widget(
        cls, widget: QWidget, theme_name: str | None = None  # noqa: ARG003
    ) -> None:
        """应用主题：指定名称则切换主题，否则按当前主题重刷全局 QSS。

        实际重绘由 QApplication.setStyleSheet 完成，widget 参数仅为
        兼容旧调用方保留。
        """
        if theme_name:
            cls.set_theme(theme_name)
        else:
            cls._apply_qss()
