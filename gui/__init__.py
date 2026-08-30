"""
GUI 包

界面层，子模块分工：
    main_window.py   主窗口（左状态卡片 + 右三标签页 + 底部状态行）
    tray_manager.py  系统托盘（最小化驻留 / 双击还原 / 菜单退出）
    log_sink.py      跨线程日志投递（Signal → 主线程 GUI）
    styling/         样式系统（主题配色 / 全局 QSS / 组件工厂）
    dialogs/         对话框（关于 / 时间段编辑 / 设置与日历的包装）
    widgets/         复用组件（万年历视图 / 列表编辑器骨架 / 规则编辑）
"""

from .main_window import MainWindow

__all__ = ["MainWindow"]
