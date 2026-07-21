"""
主窗口模块
基于 Qt Fusion 原生风格
"""

import contextlib
import datetime
import sys
import time
from typing import Any

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.config import global_config, load_config
from core.constants import LOG_FILE
from core.date_rules import should_work_today
from gui.dialogs import AboutDialog, CalendarDialog, SettingsDialog
from gui.styling.constants import FontSize, FontStyle
from gui.styling.widgets import LogTextEdit, create_button
from gui.tray_manager import TrayManager
from infra import (
    StreamRedirector,
    error,
    info,
    init_logger,
    parse_date_str,
)
from infra.concurrency import TaskChain, TaskContext, TaskExecutor
from services.campus_login import campus_login
from services.shutdown import cancel_shutdown
from services.tasks import (
    task_campus_login,
    task_check_condition,
    task_connect_wifi,
    task_set_shutdown,
)
from services.wifi import connect_wifi, is_wifi_connected
from utils.version import get_project_version


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("校园网自动登录 + 定时关机")
        self.setMinimumSize(600, 460)
        self.resize(680, 500)
        self._force_quit = False
        self._task_chain_started: bool = False

        # 基础 UI（日志组件在初始化阶段就创建好，供日志系统使用）
        self.log_text = LogTextEdit()
        self._init_ui()

        # 初始化日志（日志文件落盘到 ~/.qzct/qzct.log，5MB 轮转×5）
        init_logger(gui_log_widget=self.log_text, log_file_path=LOG_FILE, level=1)

        # 加载配置
        load_config()

        # 重定向输出
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = StreamRedirector("stdout", 1)
        sys.stderr = StreamRedirector("stderr", 3)

        # 系统托盘
        self._tray = TrayManager(self)

        # 任务管理器
        self.task_manager: TaskChain | None = None
        self.task_executor: TaskExecutor | None = None
        # 测试用临时 executor 持久化引用，防止 GC 回收
        self._test_executors: list[TaskExecutor] = []

        # 启动后自动执行
        QTimer.singleShot(200, self.run_on_start)

        # 时钟
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time_display)
        self._timer.start(1000)

        info("main", "主窗口初始化完成")

    def _init_ui(self) -> None:
        """构建界面"""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        # --- 菜单栏 ---
        self._setup_menubar()

        # --- 状态区 ---
        layout.addWidget(self._create_status_group())

        # --- 日志区 ---
        layout.addWidget(self._create_log_group(), 1)

        # --- 底部按钮栏 ---
        layout.addWidget(self._create_button_bar())

        self._update_status_display()

    def _setup_menubar(self) -> None:
        """标准菜单栏"""
        menubar = self.menuBar()
        assert menubar is not None

        menu_setting = menubar.addMenu("设置")
        assert menu_setting is not None
        act_config = menu_setting.addAction("配置设置")
        assert act_config is not None
        act_config.setShortcut("Ctrl+,")
        act_config.triggered.connect(self.on_settings)
        menu_setting.addSeparator()
        act_cal = menu_setting.addAction("任务日历")
        assert act_cal is not None
        act_cal.setShortcut("Ctrl+K")
        act_cal.triggered.connect(self.show_calendar)

        menu_help = menubar.addMenu("帮助")
        assert menu_help is not None
        act_about = menu_help.addAction("关于")
        assert act_about is not None
        act_about.setShortcut("F1")
        act_about.triggered.connect(self.show_about)

    def _create_status_group(self) -> QGroupBox:
        """状态信息"""
        group = QGroupBox("当前状态")
        v = QVBoxLayout(group)
        v.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(2)
        self.date_label = QLabel()
        left.addWidget(self.date_label)
        self.status_label = QLabel()
        left.addWidget(self.status_label)
        row.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(2)
        self.rule_label = QLabel()
        right.addWidget(self.rule_label)
        self.time_label = QLabel()
        right.addWidget(self.time_label)
        row.addLayout(right)

        row.addStretch()
        v.addLayout(row)
        return group

    def _create_log_group(self) -> QGroupBox:
        """日志区"""
        group = QGroupBox("运行日志")
        v = QVBoxLayout(group)
        v.setSpacing(4)

        self.log_text.setMinimumHeight(140)
        v.addWidget(self.log_text, 1)
        return group

    def _create_button_bar(self) -> QWidget:
        """底部按钮行"""
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 4, 0, 0)
        h.setSpacing(8)

        self.run_btn = create_button("执行", btn_type="primary", min_width=90, font_size=12)
        self.run_btn.setToolTip("执行 WiFi 连接、校园网登录、定时关机 (Ctrl+R)")
        self.run_btn.setShortcut("Ctrl+R")
        self.run_btn.clicked.connect(self.on_run_once)
        h.addWidget(self.run_btn)

        self.cancel_btn = create_button(
            "取消关机", btn_type="outline_danger", min_width=90, font_size=12
        )
        self.cancel_btn.setToolTip("取消已设置的关机任务")
        self.cancel_btn.clicked.connect(self.on_cancel_shutdown)
        h.addWidget(self.cancel_btn)

        h.addSpacing(8)

        self.test_wifi_btn = create_button("WiFi", btn_type="text", min_width=70, font_size=12)
        self.test_wifi_btn.setToolTip("仅测试 WiFi 连接")
        self.test_wifi_btn.clicked.connect(self.on_test_wifi)
        h.addWidget(self.test_wifi_btn)

        self.test_login_btn = create_button("登录", btn_type="text", min_width=70, font_size=12)
        self.test_login_btn.setToolTip("仅测试校园网登录")
        self.test_login_btn.clicked.connect(self.on_test_login)
        h.addWidget(self.test_login_btn)

        self.exit_btn = create_button("退出", btn_type="text", min_width=60, font_size=12)
        self.exit_btn.clicked.connect(lambda: self._real_close())
        h.addWidget(self.exit_btn)

        h.addStretch()

        self.footer_status = QLabel("就绪")
        self.footer_status.setFont(FontStyle.normal(FontSize.CONTENT_SMALL))
        h.addWidget(self.footer_status)

        version_label = QLabel(f"v{get_project_version()}")
        version_label.setFont(FontStyle.normal(9))
        h.addWidget(version_label)

        return bar

    def _update_time_display(self) -> None:
        # 有活跃任务时不覆盖状态栏，避免覆盖任务进度信息
        if self.task_executor and self.task_executor.active_count > 0:
            return
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"就绪  |  {time_str}")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self.run_btn.setEnabled(enabled)
        self.test_wifi_btn.setEnabled(enabled)
        self.test_login_btn.setEnabled(enabled)
        self.run_btn.setText("执行" if enabled else "运行中...")

    # ------------------------------------------------------------------
    # 任务链
    # ------------------------------------------------------------------

    def run_on_start(self) -> None:
        if self._task_chain_started:
            return
        self._task_chain_started = True
        info("main", "程序启动，开始自动执行任务链")
        QTimer.singleShot(1000, self.start_task_chain)

    def start_task_chain(self) -> None:
        self._set_buttons_enabled(False)
        # 清理旧的 executor，避免线程池泄漏
        if self.task_executor is not None:
            self.task_executor.cancel_all()
            self.task_executor.shutdown(wait=False)
        self.task_executor = TaskExecutor()

        self.task_executor.started.connect(self._on_task_started)
        self.task_executor.finished.connect(self._on_task_finished)
        self.task_executor.error.connect(self._on_task_error)
        self.task_executor.progress.connect(self._on_task_progress)
        self.task_executor.all_finished.connect(self._on_all_tasks_finished)

        chain = TaskChain(parent=self)
        chain.add(task_check_condition)
        chain.add(task_connect_wifi)
        chain.add(task_campus_login)
        chain.add(task_set_shutdown)
        chain.on_success(self._on_chain_success)
        chain.on_error(self._on_chain_error)
        chain.execute(self.task_executor)

    def _on_task_started(self, task_name: str) -> None:
        info("main", f"任务开始: {task_name}")

    def _on_task_finished(self, task_name: str, result: dict[str, Any]) -> None:
        info("main", f"任务完成: {task_name}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 完成")

    def _on_task_error(self, task_name: str, error_msg: str) -> None:
        error("main", f"任务出错: {task_name} - {error_msg}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 出错")

    def _on_task_progress(self, task_name: str, percent: int) -> None:
        info("main", f"任务进度: {task_name} - {percent}%")

    def _on_chain_success(self, success: bool, results: dict[str, Any]) -> None:
        self._set_buttons_enabled(True)
        if success:
            self.footer_status.setText("所有任务执行完成")
            info("main", "任务链执行成功")
            self._tray.notify("校园网自动登录", "所有任务执行完成")
        else:
            self.footer_status.setText("部分任务失败")
            info("main", "任务链执行完成，但有任务失败")
            self._tray.notify("校园网自动登录", "部分任务执行失败，请查看日志")

    def _on_chain_error(self, results: dict[str, Any]) -> None:
        self._set_buttons_enabled(True)
        self.footer_status.setText("任务链执行失败")
        error("main", f"任务链执行失败: {results}")

    def _on_all_tasks_finished(self, success: bool) -> None:
        self._set_buttons_enabled(True)
        info("main", f"所有任务执行完成，成功: {success}")

    # ------------------------------------------------------------------
    # 按钮事件
    # ------------------------------------------------------------------

    def on_run_once(self) -> None:
        if (
            QMessageBox.question(self, "确认", "是否立即执行一次完整任务（WiFi+登录+关机）？")
            == QMessageBox.StandardButton.Yes
        ):
            info("main", "用户手动触发：开始执行完整任务链")
            self.start_task_chain()

    def on_cancel_shutdown(self) -> None:
        if (
            QMessageBox.question(self, "确认", "是否取消已设置的关机任务？")
            == QMessageBox.StandardButton.Yes
        ):
            cancel_shutdown()
            info("main", "用户手动取消了已设置的关机任务")
            self.footer_status.setText("已取消关机")
            QMessageBox.information(self, "完成", "已尝试取消关机任务")

    def on_test_wifi(self) -> None:
        wifi_name = global_config.get("WIFI_NAME", "")
        if not wifi_name:
            QMessageBox.warning(self, "提示", "请先在设置中配置 WiFi 名称")
            return

        if (
            QMessageBox.question(self, "确认", f"是否测试连接 WiFi：{wifi_name}？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.footer_status.setText("正在测试 WiFi...")
        info("main", f"开始测试 WiFi 连接：{wifi_name}")
        self._test_wifi_name = wifi_name

        def _do_wifi_test(ctx: TaskContext) -> str:
            if is_wifi_connected(wifi_name):
                return "already_connected"
            wifi_password = global_config.get("WIFI_PASSWORD", "")
            if connect_wifi(wifi_name, wifi_password):
                time.sleep(3)
                if is_wifi_connected(wifi_name):
                    return "connected"
                return "failed_after_connect"
            return "connect_command_failed"

        executor = TaskExecutor(max_workers=1)
        self._test_executors.append(executor)
        executor.finished.connect(self._on_wifi_test_finished)
        executor.error.connect(self._on_wifi_test_error)
        # 任务完成后从列表中移除
        executor.finished.connect(lambda *_: self._release_test_executor(executor))
        executor.error.connect(lambda *_: self._release_test_executor(executor))
        executor.submit(_do_wifi_test, "test_wifi")

    def _on_wifi_test_finished(self, task_name: str, result: object) -> None:
        wifi_name = getattr(self, "_test_wifi_name", "")
        if result == "already_connected":
            info("main", f"已成功连接到 WiFi：{wifi_name}")
            self.footer_status.setText("WiFi 已连接")
            QMessageBox.information(self, "测试结果", f"已成功连接到 WiFi：{wifi_name}")
        elif result == "connected":
            info("main", f"WiFi 连接成功：{wifi_name}")
            self.footer_status.setText("WiFi 连接成功")
            QMessageBox.information(self, "测试结果", f"WiFi 连接成功：{wifi_name}")
        else:
            error("main", f"WiFi 连接失败：{wifi_name}", exc_info=False)
            self.footer_status.setText("WiFi 连接失败")
            QMessageBox.warning(
                self,
                "测试结果",
                f"WiFi 连接失败：{wifi_name}\n\n"
                "可能的原因：\n"
                "- WiFi 名称或密码错误\n"
                "- WiFi 信号弱\n"
                "- 网络设备故障",
            )

    def _on_wifi_test_error(self, task_name: str, error_msg: str) -> None:
        self.footer_status.setText("WiFi 测试出错")
        error("main", f"WiFi 测试异常：{error_msg}")
        QMessageBox.critical(self, "错误", f"WiFi 测试出错：{error_msg}")

    def on_test_login(self) -> None:
        username = global_config.get("USERNAME", "")
        if not username:
            QMessageBox.warning(self, "提示", "请先在设置中配置校园网账号")
            return

        if (
            QMessageBox.question(self, "确认", "是否测试校园网登录？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.footer_status.setText("正在测试登录...")
        info("main", "测试校园网登录")

        def _do_login_test(ctx: TaskContext) -> bool:
            return campus_login()

        executor = TaskExecutor(max_workers=1)
        self._test_executors.append(executor)
        executor.finished.connect(self._on_login_test_finished)
        executor.error.connect(self._on_login_test_error)
        executor.finished.connect(lambda *_: self._release_test_executor(executor))
        executor.error.connect(lambda *_: self._release_test_executor(executor))
        executor.submit(_do_login_test, "test_login")

    def _release_test_executor(self, executor: TaskExecutor) -> None:
        """从测试 executor 列表中移除已完成的 executor 并关闭它。"""
        with contextlib.suppress(ValueError):
            self._test_executors.remove(executor)
        executor.shutdown(wait=False)

    def _on_login_test_finished(self, task_name: str, result: object) -> None:
        self.footer_status.setText("登录测试完成")
        QMessageBox.information(
            self,
            "测试结果",
            "校园网登录测试完成，请查看日志了解详细结果",
        )

    def _on_login_test_error(self, task_name: str, error_msg: str) -> None:
        self.footer_status.setText("登录测试失败")
        QMessageBox.critical(self, "错误", f"校园网登录测试失败：{error_msg}")

    def on_settings(self) -> None:
        try:
            dialog = SettingsDialog(self)
            if dialog.exec():
                self._update_status_display()
        except Exception as e:
            import traceback

            error_msg = f"打开设置对话框失败：{str(e)}\n\n{traceback.format_exc()}"
            error("main", error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def _update_status_display(self) -> None:
        today = datetime.date.today()
        need_work = should_work_today()
        date_rules = global_config.get("DATE_RULES", {})

        rule_source = "国务院官方节假日"
        if today in [
            parse_date_str(d)
            for d in global_config.get("COMPENSATORY_WORKDAYS", [])
            if parse_date_str(d)
        ]:
            rule_source = "调休上班日"
        elif date_rules.get("ENABLE_CUSTOM_RULE", False):
            rule_source = "自定义规则"

        work_status = "需要联网并关机" if need_work else "不执行任何操作"

        self.date_label.setText(f"日期：{today}（{today.strftime('%A')}）")
        self.status_label.setText(f"状态：{work_status}")
        self.rule_label.setText(f"规则：{rule_source}")
        self.time_label.setText(
            f"关机：{global_config.get('SHUTDOWN_HOUR', 23):02d}:"
            f"{global_config.get('SHUTDOWN_MIN', 0):02d}"
        )

    def show_about(self) -> None:
        AboutDialog(self).exec()

    def show_calendar(self) -> None:
        CalendarDialog(self).exec()

    # ------------------------------------------------------------------
    # 窗口关闭
    # ------------------------------------------------------------------

    def _real_close(self) -> None:
        self._force_quit = True
        self.close()

    def quit_application(self) -> None:
        """公共退出方法，供 TrayManager 等外部组件调用。"""
        self._real_close()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        assert event is not None
        if not self._force_quit and self._tray.is_available():
            self.hide()
            self._tray.notify("校园网自动登录", "程序已最小化到系统托盘，右键可退出")
            event.ignore()
            return

        # 先询问用户是否强制退出（在 shutdown 之前）
        if self.task_executor:
            active_threads = self.task_executor.active_count
            if active_threads > 0 and (
                QMessageBox.question(
                    self,
                    "确认",
                    f"有 {active_threads} 个任务正在执行中，是否强制退出？",
                )
                != QMessageBox.StandardButton.Yes
            ):
                event.ignore()
                return

        # 用户确认退出后，清理所有 executor
        if self.task_executor:
            self.task_executor.cancel_all()
            self.task_executor.shutdown(wait=False)

        # 清理测试用临时 executor
        for ex in self._test_executors:
            ex.cancel_all()
            ex.shutdown(wait=False)
        self._test_executors.clear()

        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        event.accept()
