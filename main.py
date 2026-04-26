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
    sys.excepthook = lambda etype, evalue, tb: (
        print(f"Fatal error: {etype.__name__}: {evalue}", file=sys.stderr),
        print("".join(traceback.format_exception(etype, evalue, tb)), file=sys.stderr)
    )
    
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
