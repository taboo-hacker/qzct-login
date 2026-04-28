import sys
import traceback
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow
from gui.style_manager import StyleManager, ThemeManager


def apply_global_theme(app: QApplication) -> None:
    ThemeManager.set_theme("light")
    qss = StyleManager.get_global_stylesheet()
    app.setStyleSheet(qss)


def main():
    """主函数 - 程序入口点"""
    def _excepthook(etype, evalue, tb):
        msg = f"Fatal error: {etype.__name__}: {evalue}\n{traceback.format_exc()}"
        print(msg, file=sys.stderr)
        try:
            from infrastructure import error
            error("main", f"未捕获的异常: {etype.__name__}: {evalue}", exc_info=True)
        except Exception:
            pass  # 日志系统尚未初始化时静默忽略
    sys.excepthook = _excepthook
    
    # 启用高 DPI 缩放
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    app.setApplicationName("校园网自动登录")
    app.setOrganizationName("QZCT")
    
    apply_global_theme(app)
    
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
