"""
主题系统模块
定义亮色和暗色主题的配色方案，提供统一的主题变量
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ThemeColors:
    """主题配色数据类"""

    name: str

    primary: str = "#2563EB"
    primary_dark: str = "#1D4ED8"
    primary_darkest: str = "#1E40AF"
    primary_light: str = "#60A5FA"
    primary_bg: str = "#DBEAFE"

    success: str = "#10B981"
    success_hover: str = "#059669"
    success_bg: str = "#D1FAE5"

    warning: str = "#F59E0B"
    warning_hover: str = "#D97706"
    warning_bg: str = "#FEF3C7"

    danger: str = "#EF4444"
    danger_hover: str = "#DC2626"
    danger_darkest: str = "#B91C1C"
    danger_bg: str = "#FEE2E2"

    info: str = "#3B82F6"
    info_hover: str = "#2563EB"

    gray: str = "#94A3B8"
    gray_hover: str = "#64748B"
    gray_dark: str = "#475569"

    background: str = "#F0F2F5"
    background_secondary: str = "#E2E8F0"
    surface: str = "#FFFFFF"
    surface_variant: str = "#F8FAFC"

    text_primary: str = "#1E293B"
    text_secondary: str = "#64748B"
    text_tertiary: str = "#94A3B8"
    text_disabled: str = "#CBD5E1"
    text_inverse: str = "#FFFFFF"

    border: str = "#CBD5E1"
    border_focus: str = "#2563EB"

    shadow: str = "rgba(0, 0, 0, 0.06)"
    shadow_heavy: str = "rgba(0, 0, 0, 0.1)"

    log_debug: str = "#94A3B8"
    log_info: str = "#1E293B"
    log_warning: str = "#F59E0B"
    log_error: str = "#EF4444"
    log_critical: str = "#DC2626"

    overlay: str = "rgba(0, 0, 0, 0.4)"


def create_light_theme() -> ThemeColors:
    """创建极简商务风格浅色主题"""
    return ThemeColors(
        name="light",
        primary="#2563EB",
        primary_dark="#1D4ED8",
        primary_darkest="#1E40AF",
        primary_light="#60A5FA",
        primary_bg="#DBEAFE",
        success="#10B981",
        success_hover="#059669",
        success_bg="#D1FAE5",
        warning="#F59E0B",
        warning_hover="#D97706",
        warning_bg="#FEF3C7",
        danger="#EF4444",
        danger_hover="#DC2626",
        danger_darkest="#B91C1C",
        danger_bg="#FEE2E2",
        info="#3B82F6",
        info_hover="#2563EB",
        gray="#94A3B8",
        gray_hover="#64748B",
        gray_dark="#475569",
        background="#F0F2F5",
        background_secondary="#E2E8F0",
        surface="#FFFFFF",
        surface_variant="#F8FAFC",
        text_primary="#1E293B",
        text_secondary="#64748B",
        text_tertiary="#94A3B8",
        text_disabled="#CBD5E1",
        text_inverse="#FFFFFF",
        border="#CBD5E1",
        border_focus="#2563EB",
        shadow="rgba(0,0,0,0.06)",
        shadow_heavy="rgba(0,0,0,0.1)",
        log_debug="#94A3B8",
        log_info="#1E293B",
        log_warning="#F59E0B",
        log_error="#EF4444",
        log_critical="#DC2626",
    )


def create_dark_theme() -> ThemeColors:
    """创建暗色主题"""
    return ThemeColors(
        name="dark",
        primary="#60A5FA",
        primary_dark="#3B82F6",
        primary_darkest="#2563EB",
        primary_light="#93C5FD",
        primary_bg="#1E293B",
        success="#34D399",
        success_hover="#10B981",
        success_bg="#064E3B",
        warning="#FBBF24",
        warning_hover="#F59E0B",
        warning_bg="#78350F",
        danger="#F87171",
        danger_hover="#EF4444",
        danger_darkest="#DC2626",
        danger_bg="#7F1D1D",
        info="#60A5FA",
        info_hover="#3B82F6",
        gray="#64748B",
        gray_hover="#94A3B8",
        gray_dark="#CBD5E1",
        background="#0F172A",
        background_secondary="#1E293B",
        surface="#1E293B",
        surface_variant="#334155",
        text_primary="#F1F5F9",
        text_secondary="#94A3B8",
        text_tertiary="#64748B",
        text_disabled="#475569",
        text_inverse="#0F172A",
        border="#334155",
        border_focus="#60A5FA",
        shadow="rgba(0,0,0,0.3)",
        shadow_heavy="rgba(0,0,0,0.5)",
        log_debug="#64748B",
        log_info="#F1F5F9",
        log_warning="#FBBF24",
        log_error="#F87171",
        log_critical="#EF4444",
    )


BUILTIN_THEMES: Dict[str, ThemeColors] = {
    "light": create_light_theme(),
    "dark": create_dark_theme(),
}
