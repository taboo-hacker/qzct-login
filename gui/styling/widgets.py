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
    """按钮工厂：统一字体、手型光标，并通过 btnType 属性接入全局 QSS。

    Args:
        text: 按钮文字
        btn_type: 样式变体，对应 QSS 中的属性选择器，可选
            primary（主操作）/ success / danger / warning / gray /
            outline / outline_danger（描边危险）/ text（无底色文字钮）
        min_width/min_height: 最小尺寸（像素）
        font_size: 字号（pt），默认 FontSize.BUTTON_PRIMARY
        icon: 图标字符（emoji 或符号），非空时拼接在文字前
    """
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
    """标签工厂：统一字体族与字号，可选加粗/颜色/自动换行。

    Args:
        text: 标签文字
        font_size: 字号（pt），默认 FontSize.CONTENT_NORMAL
        bold: 是否加粗
        color: 文字颜色（CSS 色值，如 "#C50F1F"），None 用 QSS 默认色
        word_wrap: 长文本是否自动换行
    """
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
    """小节标题工厂：加粗小字号（如设置页中的"万年历显示设置"）。"""
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
    """提示文字工厂：小字号 + 自动换行。

    颜色经 role="tip" 属性接入全局 QSS（主题切换时随 QSS 重绘自动变色），
    不再使用创建时刻的主题色内联样式——内联样式优先级高于 QSS，
    会导致暗色切换后仍显示亮色主题的提示文字色。
    """
    label = QLabel(text)
    label.setFont(FontStyle.normal(FontSize.TIP_TEXT))
    label.setProperty("role", "tip")
    label.setWordWrap(True)
    return label


class LogTextEdit(QTextEdit):
    """支持彩色日志输出的文本编辑组件（objectName=logView 接入全局 QSS）"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logView")
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        # 常驻托盘应用日志昼夜累积：限制文档块数，Qt 自动删除最旧日志行，
        # 防止内存持续增长与追加/重绘变慢（文件日志不受影响）
        self.document().setMaximumBlockCount(2000)

    def append_colored(self, text: str, level: str = "INFO") -> None:
        """按日志级别着色追加一行（颜色取自当前主题的 log_* 配色）。

        文本先经 html.escape 转义再嵌入 <span>，防止日志内容中的
        <、& 等字符破坏富文本结构（日志常含 URL/异常堆栈）。

        Args:
            text: 日志文本
            level: DEBUG/INFO/WARNING/ERROR/CRITICAL
        """
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
