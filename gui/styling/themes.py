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

    # 文本色（style_helpers 中 create_tip_label 等少量使用；
    # 亮/暗两侧均按 WCAG AA（≥4.5:1）对最浅卡片背景校准）
    text_primary: str = "#1F1F1F"
    text_secondary: str = "#666666"
    text_tertiary: str = "#6B6B6B"

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
    # 前景专用主色：供"彩色文字画在浅/深背景上"的场景（tab 选中文字、outline
    # 按钮文字与边框、键盘焦点边框）。取 primary 的深变体（= primary_dark），
    # 保证对实际背景 ≥ WCAG AA（4.5:1）：对 #FFFFFF 5.82:1、#F5F6F8（窗口/tab 底）
    # 5.38:1、#E3F2FD（outline hover 底）5.10:1（原 primary #0078D4 对 #F5F6F8 仅
    # 4.19:1，不达标）。
    primary_fg: str = "#0067B5"
    success_hover: str = "#0E6A0E"
    danger_hover: str = "#A10F1C"
    warning_hover: str = "#A8430D"


def create_light_theme() -> ThemeColors:
    """亮色主题（默认）：全部字段使用 ThemeColors 数据类的默认值。"""
    return ThemeColors(name="light")


def create_dark_theme() -> ThemeColors:
    """暗色主题：逐字段覆盖配色（背景加深、文字提亮）。

    语义色按钮配白色文字，底色取 Material 800 级深色调，
    保证白字对比度 ≥ WCAG AA（4.5:1）。
    """
    return ThemeColors(
        name="dark",
        log_debug="#707070",
        log_info="#E0E0E0",
        log_warning="#E89540",
        log_error="#E85E5E",
        log_critical="#D04848",
        primary="#1565C0",
        primary_dark="#0D47A1",
        success="#2E7D32",
        warning="#A06000",
        danger="#C62828",
        primary_bg="#1A3A52",
        success_bg="#1B3B1F",
        warning_bg="#3D2E14",
        danger_bg="#3B1B1B",
        text_primary="#E0E0E0",
        text_secondary="#A0A0A0",
        text_tertiary="#9A9A9A",
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
        # 前景专用主色（亮蓝调，与 primary 同色系）：对暗色实际背景均 ≥ WCAG AA
        # （4.5:1）——对 #1F1F1F（窗口/tab 底）7.47:1、#2A2A2A（卡片底）6.50:1、
        # #1A3A52（outline hover 底）5.37:1（原 primary #1565C0 分别仅
        # 2.87:1 / 2.50:1 / 2.06:1，不达标）。
        primary_fg="#7CB3EC",
        success_hover="#4FB14F",
        danger_hover="#D05050",
        warning_hover="#D08030",
    )


# 内置主题注册表：ThemeManager.available_themes() / set_theme() 的数据源。
# 新增主题：实现 create_xxx_theme() 工厂后在此注册即可被设置页自动发现。
BUILTIN_THEMES: dict[str, ThemeColors] = {
    "light": create_light_theme(),
    "dark": create_dark_theme(),
}
