import signal
import sys
import traceback
from types import TracebackType

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from core.config import global_config


def main() -> None:
    """主函数 - 程序入口点"""

    def _excepthook(
        etype: type[BaseException],
        evalue: BaseException,
        tb: TracebackType | None,
    ) -> None:
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
    app.setFont(QFont("Microsoft YaHei", 9))  # type: ignore[attr-defined]

    # 应用默认浅色主题（全局 QSS）；主窗口加载配置后会切换为保存的主题
    from gui.styling.theme_manager import ThemeManager

    ThemeManager.set_theme(str(global_config.get("THEME", "light")))

    from gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    # 允许 Ctrl+C 在终端中干净退出
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
