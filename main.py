"""
程序入口

启动流程（顺序敏感）：
    1. 安装全局异常钩子（未捕获异常写日志/崩溃文件，而非静默消失）
    2. 创建 QApplication，设置应用名/组织名/全局字体
    3. 先应用默认浅色主题（避免主窗口闪白），主窗口加载配置后再切保存的主题
    4. 构建主窗口（内部完成：初始化日志 → 加载配置 → 应用主题 → 构建 UI）
    5. 注册单实例：已有实例运行时通知其显示窗口，本进程直接退出
    6. 显示窗口，进入 Qt 事件循环

打包运行（PyInstaller）：`python build.py` 生成 dist/qzct-login.exe。
"""

import signal
import sys
import traceback
from types import TracebackType

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from core.config import global_config


def main() -> None:
    """主函数 - 程序入口点（启动流程见模块 docstring）"""

    def _excepthook(
        etype: type[BaseException],
        evalue: BaseException,
        tb: TracebackType | None,
    ) -> None:
        """全局异常钩子：兜底记录所有未捕获异常。

        三级落盘尝试：日志系统 → crash.log → 静默（保证钩子本身不抛错）。
        """
        # KeyboardInterrupt 静默退出，不记日志
        if issubclass(etype, KeyboardInterrupt):
            return
        msg = f"Fatal error: {etype.__name__}: {evalue}\n{traceback.format_exc()}"
        # 在打包模式（console=False）下 stderr 不可见，写到日志文件
        try:
            from infra.logging import error

            error("main", f"未捕获的异常: {etype.__name__}: {evalue}", exc_info=True)
        except Exception:
            # 日志系统尚未初始化时写到文件
            try:
                import os

                from core.constants import CONFIG_DIR

                crash_log = os.path.join(CONFIG_DIR, "crash.log")
                with open(crash_log, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except Exception:
                pass

    sys.excepthook = _excepthook

    # 高 DPI 缩放由 Qt6 默认启用，无需额外设置
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setApplicationName("校园网自动登录")
    app.setOrganizationName("QZCT")

    # 全局字体
    app.setFont(QFont("Microsoft YaHei", 9))

    # 应用默认浅色主题（全局 QSS）；主窗口加载配置后会切换为保存的主题
    from gui.styling.theme_manager import ThemeManager

    ThemeManager.set_theme(str(global_config.get("THEME", "light")))

    from gui.main_window import MainWindow

    window = MainWindow()

    # 单实例：若已有实例在运行，通知其显示主窗口并退出本进程
    from utils.single_instance import listen_single_instance

    _single_server = listen_single_instance(window.show_from_tray)
    if _single_server is None:
        return

    window.show()

    # 允许 Ctrl+C 在终端中干净退出
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
