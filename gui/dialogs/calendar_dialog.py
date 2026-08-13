"""
日历对话框模块

CalendarDialog 为 CalendarView 的对话框包装（保留给独立使用场景），
主窗口内已改用嵌入式标签页，不再弹窗。
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget

from gui.widgets.calendar_view import CalendarView


class CalendarDialog(QDialog):
    """万年历对话框（包装 CalendarView，属性转发以兼容旧调用方）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("万年历 - 任务执行计划")
        self.setMinimumSize(720, 620)

        self._view = CalendarView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._view)

        # 属性转发：兼容旧调用方与测试
        self.calendar = self._view.calendar
        self.solar_label = self._view.solar_label
        self.lunar_date_label = self._view.lunar_date_label
        self.ganzhi_label = self._view.ganzhi_label
        self.yi_label = self._view.yi_label
        self.ji_label = self._view.ji_label
        self.extra_info_label = self._view.extra_info_label
        self.work_status_label = self._view.work_status_label
        self._lunar_cache = self._view._lunar_cache
