"""
主题配色方案
Fusion 风格下仅保留日志级别配色等最小必要配色。
"""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """最小配色数据类 — 仅用于日志着色等少数场景"""

    name: str

    # 日志级别配色（LogTextEdit 着色用）
    log_debug: str = "#999999"
    log_info: str = "#1F1F1F"
    log_warning: str = "#CA5010"
    log_error: str = "#C50F1F"
    log_critical: str = "#A80D1A"

    # 语义配色（少量内联样式用，如 create_label color 参数）
    primary: str = "#0078D4"
    primary_dark: str = "#0067B5"
    success: str = "#107C10"
    warning: str = "#CA5010"
    danger: str = "#C50F1F"

    # 语义背景色（calendar_dialog 状态标签背景用，为对应语义色的浅色版本）
    primary_bg: str = "#E3F2FD"
    success_bg: str = "#E8F5E9"
    warning_bg: str = "#FFF3E0"
    danger_bg: str = "#FFEBEE"

    # 文本色（style_helpers 中 create_tip_label 等少量使用）
    text_primary: str = "#1F1F1F"
    text_secondary: str = "#666666"
    text_tertiary: str = "#999999"

    # ---- 界面配色（全局 QSS 使用，qss.build_qss 消费） ----
    window_bg: str = "#F5F6F8"
    card_bg: str = "#FFFFFF"
    card_border: str = "#E4E7EC"
    input_bg: str = "#FFFFFF"
    input_border: str = "#D1D5DB"
    hover_bg: str = "#F0F1F3"
    log_view_bg: str = "#FBFCFD"
    primary_hover: str = "#2357C4"
    primary_pressed: str = "#1C47A3"
    primary_disabled: str = "#A8C1F2"
    success_hover: str = "#0E6A0E"
    danger_hover: str = "#A10F1C"
    warning_hover: str = "#A8430D"


def create_light_theme() -> ThemeColors:
    return ThemeColors(name="light")


def create_dark_theme() -> ThemeColors:
    return ThemeColors(
        name="dark",
        log_debug="#707070",
        log_info="#E0E0E0",
        log_warning="#E89540",
        log_error="#E85E5E",
        log_critical="#D04848",
        primary="#4DA3E8",
        primary_dark="#3395DD",
        success="#5EC75E",
        warning="#E89540",
        danger="#E85E5E",
        primary_bg="#1A3A52",
        success_bg="#1B3B1F",
        warning_bg="#3D2E14",
        danger_bg="#3B1B1B",
        text_primary="#E0E0E0",
        text_secondary="#A0A0A0",
        text_tertiary="#707070",
        window_bg="#1F1F1F",
        card_bg="#2A2A2A",
        card_border="#3E3E3E",
        input_bg="#262626",
        input_border="#4A4A4A",
        hover_bg="#383838",
        log_view_bg="#222222",
        primary_hover="#3395DD",
        primary_pressed="#2A7DC2",
        primary_disabled="#3E5F7E",
        success_hover="#4FB14F",
        danger_hover="#D05050",
        warning_hover="#D08030",
    )


BUILTIN_THEMES: dict[str, ThemeColors] = {
    "light": create_light_theme(),
    "dark": create_dark_theme(),
}
