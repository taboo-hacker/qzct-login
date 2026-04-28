"""
组件工厂和工具函数模块
提供统一的组件创建接口，确保所有组件遵循统一的设计规范
"""
from typing import Optional
from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLabel, QVBoxLayout, QWidget, QTextEdit
)
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from gui.styles import FontSize, FontStyle
from gui.themes import ThemeColors
from gui.style_manager import ThemeManager, StyleManager


def create_button(
    text: str,
    btn_type: str = "primary",
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
    font_size: Optional[int] = None,
    icon: Optional[str] = None
) -> QPushButton:
    btn = QPushButton(f"{icon} {text}" if icon else text)
    btn.setObjectName(f"{btn_type}Button")
    btn.setFont(FontStyle.bold(font_size or FontSize.BUTTON_PRIMARY))
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    if min_width:
        btn.setMinimumWidth(min_width)
    if min_height:
        btn.setMinimumHeight(min_height)
    else:
        btn.setMinimumHeight(42)

    return btn


def create_label(
    text: str,
    font_size: Optional[int] = None,
    bold: bool = False,
    color: Optional[str] = None,
    word_wrap: bool = False
) -> QLabel:
    label = QLabel(text)
    label.setFont(
        FontStyle.bold(font_size or FontSize.CONTENT_NORMAL) if bold
        else FontStyle.normal(font_size or FontSize.CONTENT_NORMAL)
    )

    if color:
        label.setStyleSheet(f"color: {color}; background: transparent;")

    if word_wrap:
        label.setWordWrap(True)

    return label


def create_section_title(title: str, icon: Optional[str] = None) -> QLabel:
    text = f"{icon} {title}" if icon else title
    theme = ThemeManager.current_theme()
    label = create_label(
        text, FontSize.SECTION_TITLE, bold=True,
        color=theme.primary
    )
    return label


def create_card_widget() -> QFrame:
    frame = QFrame()
    frame.setObjectName("cardFrame")
    return frame


def create_tip_label(text: str) -> QLabel:
    theme = ThemeManager.current_theme()
    label = QLabel(text)
    label.setFont(FontStyle.normal(FontSize.TIP_TEXT))
    label.setStyleSheet(
        f"color: {theme.text_tertiary}; background: transparent;"
    )
    label.setWordWrap(True)
    return label


def create_header_widget(
    title: str,
    subtitle: Optional[str] = None,
    icon: Optional[str] = None,
    height: int = 100
) -> QFrame:
    header_frame = QFrame()
    header_frame.setObjectName("headerFrame")
    header_frame.setMinimumHeight(height)

    header_layout = QVBoxLayout(header_frame)
    header_layout.setSpacing(8)
    header_layout.setContentsMargins(24, 18, 24, 18)

    if icon:
        icon_label = QLabel(icon)
        icon_label.setFont(FontStyle.emoji(36))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("headerIcon")
        header_layout.addWidget(icon_label)

    title_label = QLabel(title)
    title_label.setFont(FontStyle.bold(FontSize.MAIN_TITLE))
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setObjectName("headerTitle")
    header_layout.addWidget(title_label)

    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(FontStyle.normal(FontSize.SUBTITLE))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setObjectName("headerSubtitle")
        header_layout.addWidget(subtitle_label)

    return header_frame


def create_primary_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "primary", **kwargs)


def create_secondary_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "secondary", **kwargs)


def create_success_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "success", **kwargs)


def create_warning_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "warning", **kwargs)


def create_danger_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "danger", **kwargs)


def create_gray_button(text: str, **kwargs) -> QPushButton:
    return create_button(text, "gray", **kwargs)


class BaseWidget(QWidget):
    """组件基类，统一事件处理和样式应用"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme_applied = False

    def apply_theme(self) -> None:
        if not self._theme_applied:
            self._theme_applied = True
            qss = StyleManager.get_global_stylesheet()
            self.setStyleSheet(qss)

    def update_theme(self) -> None:
        qss = StyleManager.get_global_stylesheet()
        self.setStyleSheet(qss)


class LoadingIndicator(QWidget):
    """加载指示器组件"""

    finished = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("加载中...")
        self._label.setFont(FontStyle.normal(FontSize.CONTENT_NORMAL))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self.setVisible(False)

    def show_loading(self, text: str = "加载中...") -> None:
        self._label.setText(text)
        self.setVisible(True)

    def hide_loading(self) -> None:
        self.setVisible(False)
        self.finished.emit()


class EmptyState(QWidget):
    """空状态组件"""

    def __init__(
        self,
        message: str = "暂无数据",
        icon: Optional[str] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._message = message
        self._icon = icon
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self._icon:
            icon_label = QLabel(self._icon)
            icon_label.setFont(FontStyle.emoji(48))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

        message_label = QLabel(self._message)
        message_label.setFont(FontStyle.normal(FontSize.CONTENT_NORMAL))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme = ThemeManager.current_theme()
        message_label.setStyleSheet(
            f"color: {theme.text_tertiary}; background: transparent;"
        )
        layout.addWidget(message_label)


class LogTextEdit(QTextEdit):
    """支持彩色日志输出的文本编辑组件 - 白色背景，柔和文字"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 12))
        self._apply_style()

    def _apply_style(self) -> None:
        theme = ThemeManager.current_theme()
        self.setStyleSheet(
            f"background-color: {theme.surface}; "
            f"color: {theme.text_primary}; "
            f"border: none; "
            f"border-radius: 4px; padding: 16px;"
        )

    def update_theme(self) -> None:
        self._apply_style()

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
