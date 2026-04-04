from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QApplication, QStatusBar,
                             QScrollArea, QFrame)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import datetime
import sys
import logging

# 导入新的日志系统
from logger import Logger, logger, StreamRedirector

# 配置日志
def info(module_name, message):
    logging.info(message, extra={"logger_name": module_name})

def error(module_name, message):
    logging.error(message, extra={"logger_name": module_name})

def debug(module_name, message):
    logging.debug(message, extra={"logger_name": module_name})

def warning(module_name, message):
    logging.warning(message, extra={"logger_name": module_name})

def critical(module_name, message):
    logging.critical(message, extra={"logger_name": module_name})

from config import load_config, global_config
from date_rules import should_work_today
from utils import parse_date_str
from tasks import run_tasks_once
from shutdown import cancel_shutdown
from dialogs import AboutDialog, SettingsDialog
from wifi import is_wifi_connected, connect_wifi
from campus_login import campus_login


# 导入线程池和任务管理
from thread_pool import run_full_task_chain, get_thread_pool_manager


class MainWindow(QMainWindow):
    """
    主窗口类 - 校园网自动登录 + 定时关机工具
    
    功能说明：
        - 显示当前日期状态（是否需要执行任务）
        - 提供立即执行、取消关机、测试WiFi、测试登录按钮
        - 实时显示运行日志
        - 底部状态栏显示当前状态
    
    架构设计：
        - GUI运行在主线程
        - 网络任务运行在工作线程（WorkerThread）
        - 使用信号机制实现线程间通信
    
    使用方法：
        1. 启动程序后自动执行一次任务
        2. 可手动点击按钮执行或测试
        3. 可在设置中修改配置
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("校园网自动登录 + 定时关机")
        self.setMinimumSize(800, 550)
        
        # 1. 创建基础UI组件（至少创建日志组件）
        self._init_basic_ui()
        
        # 2. 初始化日志系统 - 确保日志系统能捕获所有错误
        from logger import init_logger
        init_logger(gui_log_widget=self.log_text, level=1)  # 1=INFO，只输出INFO及以上级别日志
        
        # 3. 加载配置（在重定向stdout之前）
        load_config()
        
        # 4. 重定向stdout和stderr到日志系统
        sys.stdout = StreamRedirector("stdout", 1)  # 1=INFO
        sys.stderr = StreamRedirector("stderr", 3)  # 3=ERROR
        
        # 5. 初始化完整UI
        self._init_complete_ui()
        
        # 6. 创建菜单
        self._create_menu()
        
        # 7. 初始化任务管理器属性，防止被垃圾回收
        self.task_manager = None
        
        # 8. 初始化其他组件
        QTimer.singleShot(200, self.run_on_start)
        
        info("main_window", "主窗口初始化完成")
    
    def _init_basic_ui(self):
        """
        初始化基础UI组件（用于日志系统）
        
        创建日志相关的UI组件，确保日志系统能在完整UI初始化前正常工作
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # 先创建日志组件，确保日志系统能正常工作
        log_title = QLabel("运行日志：")
        log_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.main_layout.addWidget(log_title)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(250)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        scroll_area.setWidget(self.log_text)
        self.main_layout.addWidget(scroll_area)
    
    def _init_complete_ui(self):
        """
        初始化完整UI组件
        
        在日志系统初始化完成后，创建其他所有UI组件
        """
        # 插入其他UI组件到日志组件之前
        # 标题
        title_label = QLabel("校园网自动登录 + 定时关机")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.insertWidget(0, title_label)
        
        subtitle_label = QLabel("同步国务院2025/2026节假日规则")
        subtitle_label.setFont(QFont("Microsoft YaHei", 10))
        subtitle_label.setStyleSheet("color: #666666;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.insertWidget(1, subtitle_label)
        
        self.main_layout.insertSpacing(2, 15)
        
        # 状态信息区域
        self._create_status_section(self.main_layout)
        
        # 按钮区域
        self._create_button_section(self.main_layout)
        
        # 状态栏
        self._create_statusbar()
    
    def _create_status_section(self, parent_layout):
        """创建状态信息区域"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        status_layout = QVBoxLayout(status_frame)
        
        # 创建空标签，延迟填充内容
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Microsoft YaHei", 11))
        status_layout.addWidget(self.date_label)
        
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Microsoft YaHei", 11))
        status_layout.addWidget(self.status_label)
        
        self.rule_label = QLabel()
        self.rule_label.setFont(QFont("Microsoft YaHei", 10))
        self.rule_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.rule_label)
        
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Microsoft YaHei", 10))
        self.time_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.time_label)
        
        parent_layout.addWidget(status_frame)
        parent_layout.addSpacing(10)
        
        # 延迟更新状态显示，确保配置已加载
        QTimer.singleShot(0, self._update_status_display)
    
    def _create_button_section(self, parent_layout):
        """创建按钮区域"""
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("立即执行一次")
        self.run_btn.setFont(QFont("Microsoft YaHei", 10))
        self.run_btn.setMinimumWidth(120)
        self.run_btn.setToolTip("执行WiFi连接、校园网登录、定时关机")
        self.run_btn.clicked.connect(self.on_run_once)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addSpacing(8)
        
        self.cancel_btn = QPushButton("取消关机")
        self.cancel_btn.setFont(QFont("Microsoft YaHei", 10))
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setToolTip("取消已设置的关机任务")
        self.cancel_btn.clicked.connect(self.on_cancel_shutdown)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addSpacing(8)
        
        self.test_wifi_btn = QPushButton("测试WiFi")
        self.test_wifi_btn.setFont(QFont("Microsoft YaHei", 10))
        self.test_wifi_btn.setMinimumWidth(90)
        self.test_wifi_btn.setToolTip("仅测试WiFi连接")
        self.test_wifi_btn.clicked.connect(self.on_test_wifi)
        btn_layout.addWidget(self.test_wifi_btn)
        btn_layout.addSpacing(8)
        
        self.test_login_btn = QPushButton("测试登录")
        self.test_login_btn.setFont(QFont("Microsoft YaHei", 10))
        self.test_login_btn.setMinimumWidth(90)
        self.test_login_btn.setToolTip("仅测试校园网登录")
        self.test_login_btn.clicked.connect(self.on_test_login)
        btn_layout.addWidget(self.test_login_btn)
        btn_layout.addSpacing(15)
        
        self.exit_btn = QPushButton("退出程序")
        self.exit_btn.setFont(QFont("Microsoft YaHei", 10))
        self.exit_btn.setMinimumWidth(80)
        self.exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.exit_btn)
        
        btn_layout.addStretch()
        parent_layout.addLayout(btn_layout)
        parent_layout.addSpacing(10)
    

    
    def _create_statusbar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("准备就绪")
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setFont(QFont("Microsoft YaHei", 10))
        
        settings_menu = menubar.addMenu("设置")
        config_action = settings_menu.addAction("配置设置")
        config_action.triggered.connect(self.on_settings)
        
        # 添加日历菜单项
        settings_menu.addSeparator()
        calendar_action = settings_menu.addAction("任务日历")
        calendar_action.triggered.connect(self.show_calendar)
        
        help_menu = menubar.addMenu("帮助")
        about_action = help_menu.addAction("关于我们")
        about_action.triggered.connect(self.show_about)
    
    def _log_write(self, text):
        """写入日志（线程安全）"""
        if text.strip():
            # 使用QTimer确保在主线程中更新UI，避免阻塞
            QTimer.singleShot(0, lambda: self._append_log(text))
    
    def _append_log(self, text):
        """追加日志到文本框"""
        # 确保在主线程中执行UI操作
        if not self.log_text:
            return
        
        # 优化日志追加操作，避免频繁更新UI
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        
        # 只在必要时更新光标位置，减少UI刷新
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    

    
    def _set_buttons_enabled(self, enabled):
        """设置按钮可用状态"""
        self.run_btn.setEnabled(enabled)
        self.test_wifi_btn.setEnabled(enabled)
        self.test_login_btn.setEnabled(enabled)
    
    def run_on_start(self):
        """启动时自动执行一次"""
        # 避免重复执行
        if hasattr(self, '_task_chain_started') and self._task_chain_started:
            return
        self._task_chain_started = True
        
        info("main_window", "程序启动，开始自动执行任务链")
        # 延迟执行任务链，确保UI完全初始化，提高响应速度
        QTimer.singleShot(1000, self.start_task_chain)
    
    def start_task_chain(self):
        """启动任务链执行
        
        使用线程池执行完整的任务流程，提高执行效率
        """
        self._set_buttons_enabled(False)
        
        # 执行完整任务链
        run_full_task_chain(parent=self)
    
    def on_worker_finished(self, success):
        """旧工作线程完成回调（保留兼容性，实际不再使用）"""
        self._set_buttons_enabled(True)
        
        if success:
            self.statusBar.showMessage("任务执行完成")
        else:
            self.statusBar.showMessage("任务执行失败，请查看日志")
    
    def on_run_once(self):
        """手动执行一次完整任务"""
        if QMessageBox.question(
            self, "确认", "是否立即执行一次完整任务（WiFi+登录+关机）？"
        ) == QMessageBox.StandardButton.Yes:
            from logger import info
            info("main_window", "用户手动触发：开始执行完整任务链")
            self.start_task_chain()
    
    def on_cancel_shutdown(self):
        """取消关机任务"""
        if QMessageBox.question(
            self, "确认", "是否取消已设置的关机任务？"
        ) == QMessageBox.StandardButton.Yes:
            from logger import info
            cancel_shutdown()
            info("main_window", "用户手动取消了已设置的关机任务")
            self.statusBar.showMessage("已取消关机")
            QMessageBox.information(self, "完成", "已尝试取消关机任务")
    
    def on_test_wifi(self):
        """测试WiFi连接"""
        wifi_name = global_config.get("WIFI_NAME", "")
        if not wifi_name:
            QMessageBox.warning(self, "提示", "请先在设置中配置WiFi名称")
            return
        
        if QMessageBox.question(
            self, "确认", f"是否测试连接WiFi：{wifi_name}？"
        ) != QMessageBox.StandardButton.Yes:
            return
        
        from logger import info, error
        
        self.statusBar.showMessage("正在测试WiFi...")
        info("wifi", f"开始测试WiFi连接：{wifi_name}")
        
        if is_wifi_connected(wifi_name):
            info("wifi", f"已成功连接到WiFi：{wifi_name}")
            self.statusBar.showMessage("WiFi已连接")
            QMessageBox.information(self, "测试结果", f"✅ 已成功连接到WiFi：{wifi_name}")
        else:
            info("wifi", "WiFi未连接，尝试建立连接...")
            if connect_wifi(wifi_name, global_config.get("WIFI_PASSWORD", "")):
                self.statusBar.showMessage("正在建立WiFi连接...")
                QTimer.singleShot(3000, lambda: self._check_wifi_result(wifi_name))
            else:
                error("wifi", "WiFi连接命令执行失败", exc_info=False)
                self.statusBar.showMessage("WiFi连接失败")
                QMessageBox.critical(self, "错误", "❌ WiFi连接命令执行失败，请检查WiFi名称和密码是否正确")
    
    def _check_wifi_result(self, wifi_name):
        """检查WiFi连接结果"""
        from logger import info, error
        
        if is_wifi_connected(wifi_name):
            info("wifi", f"WiFi连接成功：{wifi_name}")
            self.statusBar.showMessage("WiFi连接成功")
            QMessageBox.information(self, "测试结果", f"✅ WiFi连接成功：{wifi_name}")
        else:
            error("wifi", f"WiFi连接失败：{wifi_name}", exc_info=False)
            self.statusBar.showMessage("WiFi连接失败")
            QMessageBox.warning(self, "测试结果", f"❌ WiFi连接失败：{wifi_name}\n\n可能的原因：\n- WiFi名称或密码错误\n- WiFi信号弱\n- 网络设备故障")
    
    def on_test_login(self):
        """测试校园网登录"""
        username = global_config.get("USERNAME", "")
        if not username:
            QMessageBox.warning(self, "提示", "请先在设置中配置校园网账号")
            return
        
        if QMessageBox.question(
            self, "确认", "是否测试校园网登录？"
        ) != QMessageBox.StandardButton.Yes:
            return
        
        self.statusBar.showMessage("正在测试登录...")
        info("main_window", "测试校园网登录")
        
        try:
            campus_login()
            self.statusBar.showMessage("登录测试完成")
            QMessageBox.information(self, "测试结果", "✅ 校园网登录测试完成，请查看日志了解详细结果")
        except Exception as e:
            self.statusBar.showMessage("登录测试失败")
            QMessageBox.critical(self, "错误", f"❌ 校园网登录测试失败：{str(e)}")
    
    def on_settings(self):
        """打开设置窗口"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._update_status_display()
    
    def _update_status_display(self):
        """更新状态显示"""
        today = datetime.date.today()
        need_work = should_work_today()
        date_rules = global_config.get("DATE_RULES", {})
        
        rule_source = "国务院官方节假日"
        if today in [parse_date_str(d) for d in global_config.get("COMPENSATORY_WORKDAYS", []) if parse_date_str(d)]:
            rule_source = "调休上班日"
        elif date_rules.get("ENABLE_CUSTOM_RULE", False):
            rule_source = "自定义规则"
        
        work_status = "需要联网并关机" if need_work else "不执行任何操作"
        
        self.date_label.setText(f"当前日期：{today}（{today.strftime('%A')}）")
        self.status_label.setText(f"今天状态：{work_status}")
        self.rule_label.setText(f"规则来源：{rule_source}")
        self.time_label.setText(f"关机时间：{global_config.get('SHUTDOWN_HOUR', 23):02d}:{global_config.get('SHUTDOWN_MIN', 0):02d}")
    
    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def show_calendar(self):
        """显示任务日历对话框"""
        from dialogs import CalendarDialog
        dialog = CalendarDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 检查是否有活跃任务
        active_threads = get_thread_pool_manager().get_active_threads()
        if active_threads > 0:
            if QMessageBox.question(
                self, "确认", f"有 {active_threads} 个任务正在执行中，是否强制退出？"
            ) != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        
        sys.stdout = sys.__stdout__
        event.accept()
    
    def log_write(self, text):
        """写入日志（外部调用）"""
        self._log_write(text)


if __name__ == "__main__":
    # 确保只创建一个应用程序实例
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
