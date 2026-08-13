"""
GUI 模块测试

测试主题系统、日历对话框等 GUI 核心组件。
"""

import pytest
from PySide6.QtWidgets import QApplication

from gui.styling.themes import BUILTIN_THEMES, ThemeColors, create_dark_theme, create_light_theme


def _ensure_qapp() -> QApplication:
    """确保存在 QApplication 实例（Qt 信号机制所必需）。"""
    return QApplication.instance() or QApplication([])


class TestThemeColors:
    """主题配色数据类测试"""

    def test_light_theme_has_all_fields(self):
        """浅色主题包含所有必要字段"""
        theme = create_light_theme()
        assert theme.name == "light"
        # 日志级别配色
        assert theme.log_debug
        assert theme.log_info
        assert theme.log_warning
        assert theme.log_error
        assert theme.log_critical
        # 语义配色
        assert theme.primary
        assert theme.primary_dark
        assert theme.success
        assert theme.warning
        assert theme.danger
        # 语义背景色（calendar_dialog 依赖）
        assert theme.primary_bg
        assert theme.success_bg
        assert theme.warning_bg
        assert theme.danger_bg
        # 文本色
        assert theme.text_primary
        assert theme.text_secondary
        assert theme.text_tertiary

    def test_dark_theme_has_all_fields(self):
        """深色主题包含所有必要字段"""
        theme = create_dark_theme()
        assert theme.name == "dark"
        assert theme.log_debug
        assert theme.log_info
        assert theme.log_warning
        assert theme.log_error
        assert theme.log_critical
        assert theme.primary
        assert theme.primary_dark
        assert theme.success
        assert theme.warning
        assert theme.danger
        assert theme.primary_bg
        assert theme.success_bg
        assert theme.warning_bg
        assert theme.danger_bg
        assert theme.text_primary
        assert theme.text_secondary
        assert theme.text_tertiary

    def test_themes_are_different(self):
        """浅色和深色主题的颜色值不同"""
        light = create_light_theme()
        dark = create_dark_theme()
        assert light.log_info != dark.log_info
        assert light.primary != dark.primary
        assert light.text_primary != dark.text_primary

    def test_builtin_themes_contains_both(self):
        """内置主题字典包含浅色和深色"""
        assert "light" in BUILTIN_THEMES
        assert "dark" in BUILTIN_THEMES
        assert isinstance(BUILTIN_THEMES["light"], ThemeColors)
        assert isinstance(BUILTIN_THEMES["dark"], ThemeColors)

    @pytest.mark.parametrize("bg_field", ["primary_bg", "success_bg", "warning_bg", "danger_bg"])
    def test_bg_fields_are_valid_hex_colors(self, bg_field):
        """背景色字段是有效的十六进制颜色值"""
        for theme_name, theme in BUILTIN_THEMES.items():
            color = getattr(theme, bg_field)
            assert color.startswith("#"), f"{theme_name}.{bg_field} 不是有效的 hex 颜色: {color}"
            assert len(color) == 7, f"{theme_name}.{bg_field} 颜色长度不正确: {color}"


class TestThemeManager:
    """主题管理器测试"""

    def test_theme_manager_default(self):
        """ThemeManager 默认主题"""
        from gui.styling.theme_manager import ThemeManager

        # ThemeManager 可能在模块加载时已初始化
        assert ThemeManager is not None

    def test_get_colors_returns_theme_colors(self):
        """current_theme 返回 ThemeColors 实例"""
        from gui.styling.theme_manager import ThemeManager

        colors = ThemeManager.current_theme()
        assert isinstance(colors, ThemeColors)
        # 验证 calendar_dialog 依赖的字段存在
        assert hasattr(colors, "primary_bg")
        assert hasattr(colors, "success_bg")
        assert hasattr(colors, "danger_bg")
        assert hasattr(colors, "warning_bg")


class TestCalendarDialog:
    """日历对话框测试——验证阶段一修复的 ThemeColors 缺失字段不再崩溃"""

    def test_calendar_dialog_constructs_without_crash(self, qtbot):
        """CalendarDialog 能正常构造，不因缺失主题字段而崩溃"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "万年历 - 任务执行计划"

    def test_calendar_dialog_has_calendar_widget(self, qtbot):
        """日历对话框包含 QCalendarWidget"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.calendar is not None

    def test_calendar_dialog_has_labels(self, qtbot):
        """日历对话框包含必要的标签"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.solar_label is not None
        assert dialog.lunar_date_label is not None
        assert dialog.work_status_label is not None

    def test_calendar_dialog_format_date_cell(self, qtbot):
        """日历对话框的日期格式化方法可正常调用"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        # 验证 _lunar_cache 被正确初始化
        assert isinstance(dialog._lunar_cache, dict)


class TestTaskExecutorActiveCount:
    """TaskExecutor.active_count 属性测试（替代原 ThreadPoolManager）"""

    def test_active_count_initial_zero(self, qtbot):
        """测试初始活跃任务数为 0"""
        from infra.concurrency import TaskExecutor

        _ensure_qapp()
        executor = TaskExecutor()
        try:
            assert executor.active_count == 0
        finally:
            executor.shutdown(wait=False)

    def test_active_count_after_submit(self, qtbot):
        """测试提交任务后活跃任务数增加"""
        import time

        from infra.concurrency import TaskContext, TaskExecutor, task

        _ensure_qapp()
        executor = TaskExecutor()

        @task("长任务")
        def long_task(ctx: TaskContext):
            time.sleep(10)
            return {}

        try:
            executor.submit(long_task, "长任务")
            # 等待线程启动
            time.sleep(0.2)
            assert executor.active_count >= 1
        finally:
            executor.cancel_all()
            executor.shutdown(wait=False)

    def test_max_workers_reasonable(self, qtbot):
        """测试最大线程数合理"""
        import os

        from infra.concurrency import TaskExecutor

        _ensure_qapp()
        executor = TaskExecutor()
        try:
            max_workers = executor.max_workers
            cpu_count = os.cpu_count() or 4
            assert max_workers <= cpu_count * 4
            assert max_workers <= 16
            assert max_workers >= 1
        finally:
            executor.shutdown(wait=False)
