"""
GUI 模块测试

测试主题系统（ThemeColors 字段完整性、ThemeManager）、日历对话框构造，
以及 TaskExecutor.active_count / max_workers 属性
（从 test_infra.py 迁入，因 TaskExecutor 依赖 PySide6 信号机制）。
"""

import pytest
from PySide6.QtWidgets import QApplication

from gui.styling.themes import BUILTIN_THEMES, ThemeColors, create_dark_theme, create_light_theme


def _ensure_qapp() -> QApplication:
    """模块级辅助函数：确保存在 QApplication 实例（Qt 信号机制所必需）。"""
    return QApplication.instance() or QApplication([])


class TestThemeColors:
    """主题配色数据类测试：浅色/深色主题的字段完整性与差异校验。"""

    def test_light_theme_has_all_fields(self):
        """浅色主题应包含日志配色、语义配色、语义背景色与文本色等全部字段。"""
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
        """深色主题应包含与浅色主题同套的完整字段。"""
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
        """浅色和深色主题的关键颜色值应确实不同。"""
        light = create_light_theme()
        dark = create_dark_theme()
        assert light.log_info != dark.log_info
        assert light.primary != dark.primary
        assert light.text_primary != dark.text_primary

    def test_builtin_themes_contains_both(self):
        """内置主题字典 BUILTIN_THEMES 应同时包含 light 与 dark 两套 ThemeColors。"""
        assert "light" in BUILTIN_THEMES
        assert "dark" in BUILTIN_THEMES
        assert isinstance(BUILTIN_THEMES["light"], ThemeColors)
        assert isinstance(BUILTIN_THEMES["dark"], ThemeColors)

    @pytest.mark.parametrize("bg_field", ["primary_bg", "success_bg", "warning_bg", "danger_bg"])
    def test_bg_fields_are_valid_hex_colors(self, bg_field):
        """所有内置主题的背景色字段应为 #RRGGBB 七位十六进制颜色值。"""
        for theme_name, theme in BUILTIN_THEMES.items():
            color = getattr(theme, bg_field)
            assert color.startswith("#"), f"{theme_name}.{bg_field} 不是有效的 hex 颜色: {color}"
            assert len(color) == 7, f"{theme_name}.{bg_field} 颜色长度不正确: {color}"


class TestThemeManager:
    """主题管理器测试：ThemeManager 的可用性与主题取值。"""

    def test_theme_manager_default(self):
        """ThemeManager 类可正常导入（模块加载时已初始化单例）。"""
        from gui.styling.theme_manager import ThemeManager

        # ThemeManager 可能在模块加载时已初始化
        assert ThemeManager is not None

    def test_get_colors_returns_theme_colors(self):
        """current_theme() 应返回 ThemeColors 实例且含 calendar_dialog 依赖的字段。"""
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
        """CalendarDialog 能正常构造并设置窗口标题，不因缺失主题字段而崩溃。"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "万年历 - 任务执行计划"

    def test_calendar_dialog_has_calendar_widget(self, qtbot):
        """日历对话框应包含 QCalendarWidget 日历控件。"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.calendar is not None

    def test_calendar_dialog_has_labels(self, qtbot):
        """日历对话框应包含公历/农历/工作状态标签。"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        assert dialog.solar_label is not None
        assert dialog.lunar_date_label is not None
        assert dialog.work_status_label is not None

    def test_calendar_dialog_format_date_cell(self, qtbot):
        """构造后农历缓存 _lunar_cache 应被正确初始化为 dict。"""
        from gui.dialogs.calendar_dialog import CalendarDialog

        dialog = CalendarDialog()
        qtbot.addWidget(dialog)
        # 验证 _lunar_cache 被正确初始化
        assert isinstance(dialog._lunar_cache, dict)


class TestTaskExecutorActiveCount:
    """TaskExecutor.active_count 属性测试（替代原 ThreadPoolManager）"""

    def test_active_count_initial_zero(self, qtbot):
        """新建 executor 未提交任务时 active_count 应为 0。"""
        from infra.concurrency import TaskExecutor

        _ensure_qapp()
        executor = TaskExecutor()
        try:
            assert executor.active_count == 0
        finally:
            executor.shutdown(wait=False)

    def test_active_count_after_submit(self, qtbot):
        """提交长任务（sleep 10s）后 active_count 应至少为 1。"""
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
            # 等待工作线程真正启动，否则 active_count 可能尚未累加
            time.sleep(0.2)
            assert executor.active_count >= 1
        finally:
            executor.cancel_all()
            executor.shutdown(wait=False)

    def test_max_workers_reasonable(self, qtbot):
        """max_workers 应落在 [1, min(cpu_count*4, 16)] 的合理范围内。"""
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
