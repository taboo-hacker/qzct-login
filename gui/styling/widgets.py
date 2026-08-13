"""
组件工厂和工具函数

按钮/卡片等组件通过动态属性与 objectName 接入全局 QSS 样式表
（见 gui/styling/qss.py），具体视觉由主题统一控制。
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QTextEdit, QWidget

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
    # 动态属性接入全局 QSS（primary/success/danger/warning/gray/
    # outline/outline_danger/text 均有对应样式，见 qss.build_qss）
    btn.setProperty("btnType", btn_type)

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
    """创建卡片容器（objectName=card，由全局 QSS 绘制边框圆角）。"""
    frame = QFrame()
    frame.setObjectName("card")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    return frame


def create_tip_label(text: str) -> QLabel:
    theme = ThemeManager.current_theme()
    label = QLabel(text)
    label.setFont(FontStyle.normal(FontSize.TIP_TEXT))
    label.setStyleSheet(f"color: {theme.text_tertiary}; background: transparent;")
    label.setWordWrap(True)
    return label


class LogTextEdit(QTextEdit):
    """支持彩色日志输出的文本编辑组件（objectName=logView 接入全局 QSS）"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logView")
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self._update_colors()

    def _update_colors(self) -> None:
        """配色由全局 QSS 管理，无需组件内处理"""
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

        # 转义日志文本，防止 <、& 等字符破坏 HTML 结构或注入标签
        escaped = html.escape(text)
        snippet = f'<span style="color: {color};">{escaped}</span>'
        cursor.insertHtml(snippet + "<br>")

        self.setTextCursor(cursor)
        self.ensureCursorVisible()
