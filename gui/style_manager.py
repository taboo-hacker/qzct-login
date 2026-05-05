"""
样式管理器模块
集中生成和管理所有 QSS 样式表，避免样式分散
"""

from typing import Optional

from PyQt5.QtWidgets import QWidget

from gui.themes import BUILTIN_THEMES, ThemeColors


class ThemeManager:
    """
    主题管理器类
    提供主题切换、查询和应用接口
    """

    _instance: Optional["ThemeManager"] = None
    _current_theme_name: str = "light"

    def __init__(self) -> None:
        self._custom_themes: dict = {}

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
    def available_themes(cls) -> list:
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
    def apply_to_widget(cls, widget: QWidget, theme_name: Optional[str] = None) -> None:
        if theme_name:
            cls.set_theme(theme_name)
        from gui.style_manager import StyleManager

        qss = StyleManager.get_global_stylesheet()
        widget.setStyleSheet(qss)


class StyleManager:
    """
    样式管理器
    集中生成 QSS 样式表
    """

    @classmethod
    def get_global_stylesheet(cls) -> str:
        theme = ThemeManager.current_theme()
        return cls._generate_global_stylesheet(theme)

    @classmethod
    def _generate_global_stylesheet(cls, theme: ThemeColors) -> str:
        return f"""
            QMainWindow, QDialog {{
                background-color: {theme.background};
                border: none;
            }}

            QWidget {{
                background-color: {theme.background};
                color: {theme.text_primary};
                font-family: "Microsoft YaHei", "PingFang SC";
                font-size: 13px;
            }}

            #headerFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {theme.primary}, stop:1 {theme.primary_light});
                border-radius: 6px;
                border: none;
            }}

            #headerIcon {{
                color: {theme.text_inverse};
                background: transparent;
            }}

            #headerTitle {{
                color: {theme.text_inverse};
                background: transparent;
                font-size: 18px;
                font-weight: bold;
            }}

            #headerSubtitle {{
                color: rgba(255, 255, 255, 0.92);
                background: transparent;
                font-size: 13px;
            }}

            #titleMenuBar {{
                background: {theme.surface};
            }}

            #titleIcon {{
                background: transparent;
                color: {theme.text_primary};
            }}

            #titleLabel {{
                background: transparent;
                color: {theme.text_primary};
                font-size: 15px;
                font-weight: bold;
            }}

            #menuBtn {{
                background: transparent;
                color: {theme.text_secondary};
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }}

            #menuBtn:hover {{
                background: {theme.background_secondary};
                color: {theme.primary};
            }}

            QLabel {{
                background: transparent;
                color: {theme.text_primary};
            }}

            QPushButton {{
                background: {theme.primary};
                color: {theme.text_inverse};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                font-weight: bold;
                min-height: 20px;
            }}

            QPushButton:hover {{
                background: {theme.primary_dark};
            }}

            QPushButton:pressed {{
                background: {theme.primary_darkest};
            }}

            QPushButton:disabled {{
                background: {theme.text_disabled};
                color: {theme.text_tertiary};
            }}

            QPushButton#secondaryButton {{
                background: {theme.surface};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                font-weight: normal;
            }}

            QPushButton#secondaryButton:hover {{
                border: 1px solid {theme.primary};
                color: {theme.primary};
            }}

            QPushButton#secondaryButton:pressed {{
                background: {theme.primary_bg};
                border: 1px solid {theme.primary};
                color: {theme.primary};
            }}

            QPushButton#successButton {{
                background: {theme.success};
            }}

            QPushButton#successButton:hover {{
                background: {theme.success_hover};
            }}

            QPushButton#successButton:disabled {{
                background: {theme.text_disabled};
                color: {theme.text_tertiary};
            }}

            QPushButton#warningButton {{
                background: {theme.warning};
            }}

            QPushButton#warningButton:hover {{
                background: {theme.warning_hover};
            }}

            QPushButton#dangerButton {{
                background: {theme.danger};
            }}

            QPushButton#dangerButton:hover {{
                background: {theme.danger_hover};
            }}

            QPushButton#outline_dangerButton {{
                background: {theme.surface};
                color: {theme.danger};
                border: 1px solid {theme.danger};
                font-weight: normal;
            }}

            QPushButton#outline_dangerButton:hover {{
                background: {theme.danger_bg};
                border: 1px solid {theme.danger_hover};
            }}

            QPushButton#textButton {{
                background: transparent;
                color: {theme.text_secondary};
                border: none;
                font-weight: normal;
            }}

            QPushButton#textButton:hover {{
                background: {theme.background_secondary};
                color: {theme.text_primary};
            }}

            QPushButton#grayButton {{
                background: {theme.surface};
                color: {theme.text_secondary};
                border: 1px solid {theme.border};
                font-weight: normal;
            }}

            QPushButton#grayButton:hover {{
                background: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.gray};
            }}

            QPushButton#saveButton {{
                background: {theme.success};
            }}

            QPushButton#saveButton:hover {{
                background: {theme.success_hover};
            }}

            QPushButton#cancelButton, QPushButton#closeButton, QPushButton#resetButton, QPushButton#resetButton2 {{
                background: {theme.surface};
                color: {theme.text_secondary};
                border: 1px solid {theme.border};
                font-weight: normal;
            }}

            QPushButton#cancelButton:hover, QPushButton#closeButton:hover, QPushButton#resetButton:hover, QPushButton#resetButton2:hover {{
                background: {theme.background_secondary};
                color: {theme.text_primary};
                border: 1px solid {theme.gray};
            }}

            QPushButton#editButton {{
                background: {theme.warning};
            }}

            QPushButton#editButton:hover {{
                background: {theme.warning_hover};
            }}

            QPushButton#addButton {{
                background: {theme.success};
            }}

            QPushButton#addButton:hover {{
                background: {theme.success_hover};
            }}

            QPushButton#deleteButton {{
                background: {theme.danger};
            }}

            QPushButton#deleteButton:hover {{
                background: {theme.danger_hover};
            }}

            QPushButton#okButton {{
                background: {theme.primary};
            }}

            QPushButton#okButton:hover {{
                background: {theme.primary_dark};
            }}

            QPushButton#versionButton {{
                background: rgba(255, 255, 255, 0.2);
                color: {theme.text_inverse};
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11px;
            }}

            QPushButton#versionButton:hover {{
                background: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.5);
            }}

            QLineEdit, QDateEdit {{
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 12px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                background: {theme.surface};
                color: {theme.text_primary};
                outline: none;
            }}

            QLineEdit:focus, QDateEdit:focus {{
                border: 1px solid {theme.border_focus};
                background: {theme.surface};
                outline: none;
            }}

            QTextEdit {{
                background-color: {theme.surface};
                color: {theme.text_primary};
                border: 1px solid {theme.background_secondary};
                border-radius: 6px;
                padding: 12px;
                font-family: "Consolas", "Courier New", "Microsoft YaHei";
                font-size: 12px;
                selection-background-color: {theme.primary_light};
                outline: none;
            }}

            QComboBox {{
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 8px 12px;
                padding-right: 30px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                background: {theme.surface};
                color: {theme.text_primary};
                outline: none;
            }}

            QComboBox:focus {{
                border: 1px solid {theme.border_focus};
                outline: none;
            }}

            QComboBox::drop-down {{
                border: none;
                width: 28px;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}

            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
            }}

            QComboBox QAbstractItemView {{
                background: {theme.surface};
                color: {theme.text_primary};
                selection-background-color: {theme.primary_bg};
                selection-color: {theme.primary};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}

            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                border-radius: 4px;
                min-height: 24px;
            }}

            QComboBox QAbstractItemView::item:hover {{
                background: {theme.background_secondary};
            }}

            QCheckBox {{
                font-family: "Microsoft YaHei";
                font-size: 13px;
                spacing: 8px;
                color: {theme.text_primary};
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {theme.border};
                border-radius: 4px;
                background: {theme.surface};
            }}

            QCheckBox::indicator:checked {{
                background: {theme.primary};
                border: 1px solid {theme.primary};
            }}

            QCheckBox::indicator:hover {{
                border: 1px solid {theme.primary};
            }}

            QListWidget {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 6px;
                padding: 4px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                color: {theme.text_primary};
                outline: none;
            }}

            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 4px;
            }}

            QListWidget::item:selected {{
                background: {theme.primary_bg};
                color: {theme.primary};
            }}

            QListWidget::item:hover {{
                background: {theme.surface_variant};
            }}

            QTableWidget, QTableView {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                color: {theme.text_primary};
                gridline-color: {theme.background_secondary};
                outline: none;
            }}

            QTableWidget::item, QTableView::item {{
                padding: 6px 10px;
            }}

            QTableWidget::item:selected, QTableView::item:selected {{
                background: {theme.primary_bg};
                color: {theme.primary};
            }}

            QHeaderView::section {{
                background: {theme.surface_variant};
                color: {theme.text_secondary};
                border: none;
                border-bottom: 1px solid {theme.border};
                padding: 8px 10px;
                font-weight: bold;
                font-size: 12px;
            }}

            QCalendarWidget {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}

            QCalendarWidget QToolButton {{
                background: transparent;
                color: {theme.text_primary};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-family: "Microsoft YaHei";
                font-weight: bold;
                font-size: 13px;
            }}

            QCalendarWidget QToolButton:hover {{
                background: {theme.background_secondary};
                color: {theme.primary};
            }}

            QCalendarWidget QToolButton#qt_calendar_monthbutton,
            QCalendarWidget QToolButton#qt_calendar_yearbutton {{
                color: {theme.text_primary};
            }}

            QCalendarWidget QMenu {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                font-family: "Microsoft YaHei";
                color: {theme.text_primary};
                border-radius: 6px;
            }}

            QCalendarWidget QSpinBox {{
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 4px 8px;
                background: {theme.surface};
                color: {theme.text_primary};
                font-size: 12px;
            }}

            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background: transparent;
                padding: 8px;
            }}

            QCalendarWidget QAbstractItemView:enabled {{
                color: {theme.text_primary};
                background: {theme.surface};
                font-size: 12px;
            }}

            QCalendarWidget QAbstractItemView:disabled {{
                color: {theme.text_disabled};
            }}

            QTabWidget {{
                background: transparent;
                border: none;
            }}

            QTabWidget::tab-bar {{
                alignment: left;
            }}

            QTabWidget QTabBar::tab {{
                background: transparent;
                color: {theme.text_secondary};
                padding: 8px 20px;
                margin-right: 2px;
                border: none;
                border-bottom: 2px solid transparent;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                font-weight: bold;
                min-width: 100px;
            }}

            QTabWidget QTabBar::tab:selected {{
                color: {theme.primary};
                border-bottom: 2px solid {theme.primary};
                background: transparent;
            }}

            QTabWidget QTabBar::tab:hover {{
                color: {theme.primary};
                background: {theme.primary_bg};
                border-radius: 4px 4px 0 0;
            }}

            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}

            #footerBar {{
                background: {theme.surface};
                border-top: 1px solid {theme.border};
            }}

            #footerStatus {{
                background: transparent;
                color: {theme.text_secondary};
                font-size: 12px;
            }}

            #bottomSection {{
                background: transparent;
                border: none;
            }}

            #bottomStatusBar {{
                background: transparent;
                border: none;
            }}

            #contentArea {{
                background: transparent;
                border: none;
            }}

            #footerCtrlBtn {{
                background: transparent;
                color: {theme.text_secondary};
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                min-width: 32px;
                min-height: 28px;
            }}

            #footerCtrlBtn:hover {{
                background: {theme.background_secondary};
                color: {theme.text_primary};
            }}

            #footerCloseBtn {{
                background: transparent;
                color: {theme.text_secondary};
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                min-width: 32px;
                min-height: 28px;
            }}

            #footerCloseBtn:hover {{
                background: {theme.danger};
                color: {theme.text_inverse};
            }}

            QMenuBar {{
                background: {theme.surface};
                border-bottom: 1px solid {theme.border};
            }}

            QMenuBar::item {{
                padding: 8px 16px;
                color: {theme.text_primary};
                background: transparent;
            }}

            QMenuBar::item:selected {{
                background: {theme.primary_bg};
                color: {theme.primary};
            }}

            QMenu {{
                background: {theme.surface};
                border: 1px solid {theme.border};
                color: {theme.text_primary};
                border-radius: 6px;
                padding: 6px;
            }}

            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background: {theme.primary_bg};
                color: {theme.primary};
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }}

            QScrollBar::handle:vertical {{
                background: {theme.gray};
                border-radius: 3px;
                min-height: 32px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {theme.gray_hover};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                background: transparent;
                height: 6px;
                border-radius: 3px;
                margin: 0;
            }}

            QScrollBar::handle:horizontal {{
                background: {theme.gray};
                border-radius: 3px;
                min-width: 32px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {theme.gray_hover};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            QFrame#cardFrame, #statusCard, #detailCard, #sectionFrame, #formFrame,
            #dateRuleEditFrame, #holidayEditFrame, #infoCard, #featuresCard, #linksCard {{
                background: {theme.surface};
                border: 1px solid {theme.background_secondary};
                border-radius: 8px;
            }}

            #outerContainer {{
                background: {theme.background};
                border: none;
                border-radius: 12px;
            }}

            #logOuterFrame {{
                background: {theme.surface};
                border: none;
            }}

            #contentOuterFrame {{
                background: {theme.surface};
                border: none;
            }}

            #logCard {{
                background: transparent;
                border: none;
            }}

            #contentStatusSection {{
                background: transparent;
                border: none;
            }}

            #logSeparator {{
                background: {theme.background_secondary};
                border: none;
                max-height: 1px;
            }}

            #sectionSeparator {{
                background: {theme.background_secondary};
                border: none;
                max-height: 1px;
            }}

            QFrame {{
                background: transparent;
            }}

            QSplitter::handle {{
                background: {theme.border};
            }}

            QSplitter::handle:horizontal {{
                width: 1px;
            }}

            QSplitter::handle:vertical {{
                height: 1px;
            }}

            QToolTip {{
                background: {theme.surface};
                color: {theme.text_primary};
                border: 1px solid {theme.border};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}

            QProgressBar {{
                background: {theme.background_secondary};
                border: none;
                border-radius: 4px;
                height: 6px;
                text-align: center;
                font-size: 11px;
            }}

            QProgressBar::chunk {{
                background: {theme.primary};
                border-radius: 4px;
            }}
        """

    @classmethod
    def get_dialog_stylesheet(cls) -> str:
        theme = ThemeManager.current_theme()
        return f"""
            QDialog {{
                background: {theme.background};
                border-radius: 8px;
            }}

            #topFrame, #calendarHeader {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {theme.primary}, stop:1 {theme.primary_light});
                border-radius: 8px 8px 0 0;
                border: none;
            }}

            #appIcon, #appTitle, #calendarTitle {{
                color: {theme.text_inverse};
                background: transparent;
            }}

            #bottomFrame {{
                background: transparent;
                border: none;
            }}

            #copyrightText {{
                color: {theme.text_tertiary};
                background: transparent;
                font-size: 11px;
            }}

            #linkLabel {{
                color: {theme.primary};
                text-decoration: none;
            }}

            #linkLabel:hover {{
                color: {theme.primary_dark};
                text-decoration: underline;
            }}

            #sectionTitle {{
                color: {theme.primary};
                font-weight: bold;
            }}

            #descText {{
                color: {theme.text_primary};
            }}

            #closeButton {{
                background: {theme.primary};
                color: {theme.text_inverse};
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }}

            #closeButton:hover {{
                background: {theme.primary_dark};
            }}

            #closeButton:pressed {{
                background: {theme.primary_darkest};
            }}
        """
