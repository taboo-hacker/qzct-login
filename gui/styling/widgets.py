"""
组件工厂和工具函数

按钮/卡片等组件通过动态属性与 objectName 接入全局 QSS 样式表
（见 gui/styling/qss.py），具体视觉由主题统一控制。
"""

import html
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont, QTextCursor
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

        追加后仅在用户原本就贴着底部时自动滚动；用户上滚查阅历史时
        保持其阅读位置，不被新日志拽走（见 is_scrolled_to_bottom）。

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

        # 转义日志文本，防止 <、& 等字符破坏 HTML 结构或注入标签
        escaped = html.escape(text)
        snippet = f'<span style="color: {color};">{escaped}</span>'
        append_preserving_scroll(self, lambda cursor: cursor.insertHtml(snippet + "<br>"))


def is_scrolled_to_bottom(widget: QTextEdit, tolerance: int = 4) -> bool:
    """判断文本控件的滚动条是否已贴近底部。

    用于日志追加时决定是否自动滚动：用户在底部时跟随最新日志（常见期望），
    用户已上滚查阅历史时保持其位置（否则每条新日志都会把视图拽回底部）。

    Args:
        widget: 目标文本控件
        tolerance: 视为"到底"的像素容差，吸收字体行高与滚动精度误差

    Returns:
        bool: 滚动条距底部不超过 tolerance 像素时为 True
    """
    scrollbar = widget.verticalScrollBar()
    # bool(...) 收敛返回类型：无存根环境下 verticalScrollBar() 推断为 Any，
    # 真实存根下为 QScrollBar，两种 mypy 模式都要得到 bool
    return bool(scrollbar.maximum() - scrollbar.value() <= tolerance)


def append_preserving_scroll(widget: QTextEdit, insert: Callable[[QTextCursor], None]) -> None:
    """在文档末尾插入内容，并按用户当前滚动位置决定是否跟随到最新内容。

    必须由本函数统一处理滚动，原因有二：
    1. 是否"在底部"要在插入前判断——插入后滚动条最大值已变大，
       再判断必然得出"不在底部"；
    2. ``setTextCursor`` 本身就会把视图滚动到游标处，仅去掉
       ``ensureCursorVisible`` 并不足以保留用户的阅读位置，还需还原滚动值。

    Args:
        widget: 目标文本控件
        insert: 接收已定位到文档末尾的游标，执行实际插入（纯文本或 HTML）
    """
    stick_to_bottom = is_scrolled_to_bottom(widget)
    scroll_value = widget.verticalScrollBar().value()

    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    insert(cursor)
    widget.setTextCursor(cursor)

    if stick_to_bottom:
        widget.ensureCursorVisible()
    else:
        # 还原到插入前的滚动位置，用户上滚查阅历史时视图不被拽走
        widget.verticalScrollBar().setValue(scroll_value)
