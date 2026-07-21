"""
组件工厂和工具函数
基于 Fusion 原生风格，不注入自定义 QSS。
"""


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QTextEdit, QWidget

from gui.styling.constants import FontSize, FontStyle
from gui.styling.theme_manager import ThemeManager


def create_button(
    text: str,
    btn_type: str = "primary",
    min_width: int | None = None,
    min_height: int | None = None,
    font_size: int | None = None,
    icon: str | None = None,
) -> QPushButton:
    btn = QPushButton(f"{icon} {text}" if icon else text)
    btn.setFont(FontStyle.normal(font_size or FontSize.BUTTON_PRIMARY))
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    if min_width:
        btn.setMinimumWidth(min_width)
    if min_height:
        btn.setMinimumHeight(min_height)

    return btn


def create_label(
    text: str,
    font_size: int | None = None,
    bold: bool = False,
    color: str | None = None,
    word_wrap: bool = False,
) -> QLabel:
    label = QLabel(text)
    label.setFont(
        FontStyle.bold(font_size or FontSize.CONTENT_NORMAL)
        if bold
        else FontStyle.normal(font_size or FontSize.CONTENT_NORMAL)
    )

    if color:
        label.setStyleSheet(f"color: {color}; background: transparent;")

    if word_wrap:
        label.setWordWrap(True)

    return label


def create_section_title(title: str, icon: str | None = None) -> QLabel:
    text = f"{icon} {title}" if icon else title
    label = create_label(text, FontSize.SECTION_TITLE, bold=True)
    return label


def create_card_widget() -> QFrame:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    return frame


def create_tip_label(text: str) -> QLabel:
    theme = ThemeManager.current_theme()
    label = QLabel(text)
    label.setFont(FontStyle.normal(FontSize.TIP_TEXT))
    label.setStyleSheet(f"color: {theme.text_tertiary}; background: transparent;")
    label.setWordWrap(True)
    return label


class LogTextEdit(QTextEdit):
    """支持彩色日志输出的文本编辑组件"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self._update_colors()

    def _update_colors(self) -> None:
        """配色由 ThemeManager 管理，不注入 QSS"""
        pass

    def update_theme(self) -> None:
        self._update_colors()

    def append_colored(self, text: str, level: str = "INFO") -> None:
        theme = ThemeManager.current_theme()
        color_map = {
            "DEBUG": theme.log_debug,
            "INFO": theme.log_info,
            "WARNING": theme.log_warning,
            "ERROR": theme.log_error,
            "CRITICAL": theme.log_critical,
        }
        color = color_map.get(level, theme.log_info)

        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        html = f'<span style="color: {color};">{text}</span>'
        cursor.insertHtml(html + "<br>")

        self.setTextCursor(cursor)
        self.ensureCursorVisible()
