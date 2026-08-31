"""
主窗口模块
简洁商务风界面：左侧"今日状态 + 任务操作"卡片，右侧运行日志，底部状态栏。
视觉由全局 QSS 统一控制（gui/styling/qss.py），支持亮色/暗色主题即时切换。
"""

import contextlib
import datetime
import sys
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import global_config, load_config
from core.constants import CONFIG_FILE, LOG_FILE
from core.date_rules import should_work_today
from gui.dialogs import AboutDialog, SettingsPanel
from gui.log_sink import QtLogSink
from gui.styling.theme_manager import ThemeManager
from gui.styling.widgets import LogTextEdit, create_button, create_card_widget
from gui.tray_manager import TrayManager
from gui.widgets import CalendarView
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
from services.wifi import connect_wifi, interruptible_sleep, is_wifi_connected
from utils.version import get_project_version


class MainWindow(QMainWindow):
    """主窗口

    布局结构：

        ┌────────────┬──────────────────────────┐
        │ 今日状态    │  QTabWidget              │
        │  日期/徽标   │   ├ 运行日志（log_text） │
        │  规则/关机   │   ├ 设置（SettingsPanel）│
        │ ──────────  │   └ 任务日历（Calendar） │
        │ 任务操作    │                          │
        │  执行/取消   │                          │
        │  测试按钮    │                          │
        ├────────────┴──────────────────────────┤
        │ 退出 | 状态文本 ...          关于 | 版本 │
        └───────────────────────────────────────┘

    初始化顺序（顺序敏感，见 __init__ 内注释）：
        日志组件 → 日志系统 → 加载配置 → 应用主题 → 构建界面 → 托盘 → 定时器
    界面视觉统一由全局 QSS 控制（gui/styling/qss.py），窗口代码只设置
    objectName / role / btnType 等选择器属性，不写具体颜色。
    """

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("校园网自动登录 + 定时关机")
        self.setMinimumSize(660, 460)
        self.resize(800, 500)
        self._force_quit = False
        self._task_chain_started: bool = False
        # 本次会话是否成功设置过定时关机（退出时据此提醒"退出不会取消关机"）
        self._shutdown_scheduled: bool = False

        # 日志组件先创建，供日志系统使用
        self.log_text = LogTextEdit()

        # 初始化日志（日志文件落盘到 ~/.qzct/qzct.log，10MB 轮转、保留 35 天）；
        # GUI sink 由本层绑定 QtLogSink 后以回调注入，utils/infra 不反向依赖 gui
        QtLogSink.set_gui_widget(self.log_text)
        init_logger(gui_sink=QtLogSink.instance().write, log_file_path=LOG_FILE, level=1)

        # 必须先加载配置并应用保存的主题，再构建界面：
        # 设置面板/状态显示在构建时读取 global_config，顺序颠倒会导致
        # 面板显示默认空值，保存时把空值写回、覆盖已保存的配置
        load_error = load_config()
        if load_error:
            QMessageBox.warning(
                self,
                "配置加载失败",
                f"配置文件加载失败，已恢复为默认设置：\n{load_error}\n\n"
                f"请检查 {CONFIG_FILE} 文件是否损坏。",
            )
        ThemeManager.set_theme(str(global_config.get("THEME", "light")))

        # 构建界面（此时 global_config 已是加载后的值）；
        # 万年历在 _init_ui 内部已随主题刷新（update_theme 含标记执行日期），
        # 这里不再重复调用
        self._init_ui()

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

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        """构建界面：左侧状态/操作卡片 + 右侧日志卡片 + 底部状态行。"""
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)

        v_root = QVBoxLayout(central)
        v_root.setContentsMargins(14, 12, 14, 8)
        v_root.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(12)

        # --- 左侧栏：状态 + 操作（单卡片） ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._create_left_card())
        left_panel.setFixedWidth(220)
        body.addWidget(left_panel)

        # --- 右侧：运行日志 / 任务日历 标签页 ---
        body.addWidget(self._create_right_tabs(), 1)

        v_root.addLayout(body, 1)

        # --- 底部状态行 ---
        v_root.addLayout(self._create_footer())

        # 全局快捷键（窗口级）：设置页 / 任务日历
        QShortcut(QKeySequence("Ctrl+,"), self, self.on_settings)
        QShortcut(QKeySequence("Ctrl+K"), self, self.show_calendar)

        self._update_status_display()

    @staticmethod
    def _h_line() -> QFrame:
        """卡片内分隔线。"""
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    def _create_left_card(self) -> QWidget:
        """左侧单卡片：今日状态 + 分隔线 + 任务操作，比例紧凑对齐。"""
        card = create_card_widget()
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)

        # ---- 今日状态 ----
        title = QLabel("今日状态")
        title.setProperty("role", "cardTitle")
        v.addWidget(title)

        # 日期（单行，不含多余修饰）
        self.date_label = QLabel()
        self.date_label.setProperty("role", "dateBig")
        v.addWidget(self.date_label)

        # 执行状态徽标
        self.status_badge = QLabel()
        self.status_badge.setProperty("role", "badge")
        v.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)

        # 规则与关机时间
        self.rule_label = QLabel()
        self.rule_label.setProperty("role", "muted")
        v.addWidget(self.rule_label)
        self.time_label = QLabel()
        self.time_label.setProperty("role", "muted")
        v.addWidget(self.time_label)

        # ---- 分隔 + 任务操作 ----
        v.addWidget(self._h_line())

        action_title = QLabel("任务操作")
        action_title.setProperty("role", "sectionTitle")
        v.addWidget(action_title)

        self.run_btn = create_button("立即执行", btn_type="primary", min_height=32)
        self.run_btn.setToolTip("执行 WiFi 连接、校园网登录、定时关机 (Ctrl+R)")
        self.run_btn.setShortcut("Ctrl+R")
        self.run_btn.clicked.connect(self.on_run_once)
        v.addWidget(self.run_btn)

        self.cancel_btn = create_button("取消关机", btn_type="outline_danger", min_height=30)
        self.cancel_btn.setToolTip("取消已设置的关机任务")
        self.cancel_btn.clicked.connect(self.on_cancel_shutdown)
        v.addWidget(self.cancel_btn)

        # 单项测试（同高同宽，规整网格）
        test_row = QHBoxLayout()
        test_row.setSpacing(8)
        self.test_wifi_btn = create_button("测试 WiFi", btn_type="outline", min_height=28)
        self.test_wifi_btn.setToolTip("仅测试 WiFi 连接")
        self.test_wifi_btn.clicked.connect(self.on_test_wifi)
        test_row.addWidget(self.test_wifi_btn, 1)

        self.test_login_btn = create_button("测试登录", btn_type="outline", min_height=28)
        self.test_login_btn.setToolTip("仅测试校园网登录")
        self.test_login_btn.clicked.connect(self.on_test_login)
        test_row.addWidget(self.test_login_btn, 1)
        v.addLayout(test_row)

        v.addStretch(1)
        return card

    def _create_right_tabs(self) -> QWidget:
        """右侧标签页：运行日志 / 设置 / 任务日历（均嵌入式，不弹窗）。"""
        self.main_tabs = QTabWidget()

        # 标签页 1：运行日志
        log_tab = QWidget()
        log_v = QVBoxLayout(log_tab)
        log_v.setContentsMargins(14, 12, 14, 12)
        log_v.setSpacing(8)
        title_row = QHBoxLayout()
        title = QLabel("运行日志")
        title.setProperty("role", "cardTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.clear_log_btn = create_button("清空", btn_type="text", min_height=24)
        self.clear_log_btn.setToolTip("清空日志显示")
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        title_row.addWidget(self.clear_log_btn)
        log_v.addLayout(title_row)
        log_v.addWidget(self.log_text, 1)
        self.main_tabs.addTab(log_tab, "运行日志")

        # 标签页 2：设置
        self._settings_panel = SettingsPanel()
        self.main_tabs.addTab(self._settings_panel, "设置")
        self._settings_panel.config_saved.connect(self._on_config_saved)
        self._settings_panel.theme_changed.connect(self._on_theme_changed_external)

        # 标签页 3：任务日历
        self._calendar_view = CalendarView()
        self.main_tabs.addTab(self._calendar_view, "任务日历")
        return self.main_tabs

    def _create_footer(self) -> QHBoxLayout:
        """底部状态行：退出 + 状态文本 | 关于 + 版本号（设置/日历已是标签页）。"""
        h = QHBoxLayout()
        h.setContentsMargins(2, 0, 2, 0)
        h.setSpacing(4)

        self.exit_btn = create_button("退出", btn_type="text", min_height=24)
        self.exit_btn.setToolTip("退出程序（关闭窗口仅最小化到托盘）")
        self.exit_btn.clicked.connect(lambda: self._real_close())
        h.addWidget(self.exit_btn)

        self.footer_status = QLabel("就绪")
        self.footer_status.setProperty("role", "muted")
        h.addWidget(self.footer_status)
        h.addStretch(1)

        # 常驻时钟（独立标签）：与业务状态分区显示，每秒刷新不冲掉状态反馈
        self.clock_label = QLabel(datetime.datetime.now().strftime("%H:%M:%S"))
        self.clock_label.setProperty("role", "muted")
        h.addWidget(self.clock_label)

        self.about_btn = create_button("关于", btn_type="text", min_height=24)
        self.about_btn.setToolTip("关于 (F1)")
        self.about_btn.setShortcut("F1")
        self.about_btn.clicked.connect(self.show_about)
        h.addWidget(self.about_btn)

        version_label = QLabel(f"v{get_project_version()}")
        version_label.setProperty("role", "muted")
        h.addWidget(version_label)
        return h

    def _on_clear_log(self) -> None:
        """清空日志显示（不影响日志文件）。"""
        self.log_text.clear()
        info("main", "用户清空了日志显示")

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------

    def _update_time_display(self) -> None:
        """每秒刷新底部时钟。

        时钟是独立的常驻标签，不与业务状态共用 footer_status——
        否则每秒刷新会把"正在测试/已保存"等瞬时反馈立即冲掉。
        """
        now = datetime.datetime.now()
        if hasattr(self, "clock_label"):
            self.clock_label.setText(now.strftime("%H:%M:%S"))

    def _set_buttons_enabled(self, enabled: bool, busy_text: str = "运行中...") -> None:
        """任务/测试运行期间禁用任务相关按钮，结束后恢复（防止重复触发）。"""
        self.run_btn.setEnabled(enabled)
        self.test_wifi_btn.setEnabled(enabled)
        self.test_login_btn.setEnabled(enabled)
        self.run_btn.setText("立即执行" if enabled else busy_text)

    def _update_status_display(self) -> None:
        """刷新左侧卡片：日期、执行状态徽标、生效规则来源、关机时间。

        规则来源的判断顺序：硬编码调休日 → 自定义规则 → 默认（国务院安排）。
        徽标状态变化后需 unpolish/polish 手动刷新 QSS（属性选择器不自动重绘）。
        """
        today = datetime.date.today()
        need_work = should_work_today()
        date_rules = global_config.get("DATE_RULES", {})

        rule_source = "国务院官方节假日"
        if today in [
            parsed
            for d in global_config.get("COMPENSATORY_WORKDAYS", [])
            if (parsed := parse_date_str(d)) is not None
        ]:
            rule_source = "调休上班日"
        elif date_rules.get("ENABLE_CUSTOM_RULE", False):
            rule_source = "自定义规则"

        work_status = "今天需要执行任务" if need_work else "今天无需执行"
        weekday = "一二三四五六日"[today.weekday()]

        self.date_label.setText(f"{today.year}年{today.month}月{today.day}日 · 星期{weekday}")
        self.status_badge.setText(work_status)
        self.status_badge.setProperty("state", "work" if need_work else "rest")
        # 属性变更后刷新样式
        style = self.status_badge.style()
        if style is not None:
            style.unpolish(self.status_badge)
            style.polish(self.status_badge)
        self.rule_label.setText(f"执行规则：{rule_source}")
        self.time_label.setText(
            f"关机时间：{global_config.get('SHUTDOWN_HOUR', 23):02d}:"
            f"{global_config.get('SHUTDOWN_MIN', 0):02d}"
        )

    # ------------------------------------------------------------------
    # 任务链
    # ------------------------------------------------------------------

    def run_on_start(self) -> None:
        """程序启动后延迟 1 秒自动执行任务链（仅一次，_task_chain_started 防重）。

        首次使用（账号与 WiFi 均未配置）时跳过自动执行：空账号登录注定
        失败，且链尾仍会按默认 23:00 设置关机——相当于"装完即被安排关机"。
        """
        if self._task_chain_started:
            return
        self._task_chain_started = True
        username = str(global_config.get("USERNAME", ""))
        wifi_name = str(global_config.get("WIFI_NAME", ""))
        if not username and not wifi_name:
            info("main", "首次使用：账号与 WiFi 均未配置，跳过启动自动执行")
            self.footer_status.setText("尚未配置账号，已跳过自动执行")
            self._tray.notify(
                "校园网自动登录",
                "尚未配置账号，已跳过自动执行。请到「设置」填写 WiFi 与账号后手动执行",
            )
            return
        info("main", "程序启动，开始自动执行任务链")
        QTimer.singleShot(1000, self.start_task_chain)

    def start_task_chain(self) -> None:
        """组装并启动完整任务链：检查条件 → WiFi → 登录 → 定时关机。

        每次启动新建 TaskExecutor（旧 executor 先关闭），链进度通过
        started/finished/error 三个信号驱动底部状态栏。
        """
        # 防重入：旧链仍在执行时忽略重复启动请求（否则旧链信号会在
        # 已关闭的线程池上触发提交，导致 PySide6 abort）
        if self.task_executor is not None and self.task_executor.is_chain_active():
            info("main", "任务链正在执行，忽略重复启动请求")
            return
        self._set_buttons_enabled(False)
        # 清理旧的 executor，避免线程池泄漏（shutdown 会断开旧链信号）
        if self.task_executor is not None:
            self.task_executor.cancel_all()
            self.task_executor.shutdown(wait=False)
        self.task_executor = TaskExecutor()

        self.task_executor.started.connect(self._on_task_started)
        self.task_executor.finished.connect(self._on_task_finished)
        self.task_executor.error.connect(self._on_task_error)

        chain = TaskChain(parent=self)
        chain.add(task_check_condition)
        chain.add(task_connect_wifi)
        chain.add(task_campus_login)
        chain.add(task_set_shutdown)
        chain.on_success(self._on_chain_success)
        chain.on_error(self._on_chain_error)
        chain.execute(self.task_executor)

    def _on_task_started(self, task_name: str) -> None:
        """单个任务开始（TaskExecutor.started 信号，主线程执行）。"""
        info("main", f"任务开始: {task_name}")

    def _on_task_finished(self, task_name: str, result: dict[str, Any]) -> None:
        """单个任务成功（TaskExecutor.finished 信号，主线程执行）。"""
        info("main", f"任务完成: {task_name}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 完成")

    def _on_task_error(self, task_name: str, error_msg: str) -> None:
        """单个任务抛异常（TaskExecutor.error 信号，主线程执行）。"""
        error("main", f"任务出错: {task_name} - {error_msg}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 出错")

    def _on_chain_success(self, success: bool, results: dict[str, Any]) -> None:
        """任务链整体完成回调：如实报告每一步的成败与关机设置状态。

        任务失败不抛异常（链仍会"成功"走完，保底设置关机），因此
        success=True 不代表每步都成功——需逐项核对 results。
        """
        self._set_buttons_enabled(True)
        if not success:
            self.footer_status.setText("部分任务失败")
            info("main", "任务链执行完成，但有任务失败")
            self._tray.notify("校园网自动登录", "部分任务执行失败，请查看日志")
            return

        check_result = results.get("检查执行条件")
        need_work = not isinstance(check_result, dict) or check_result.get("need_work", True)
        if not need_work:
            self.footer_status.setText("今天无需执行（节假日/周末）")
            info("main", "任务链提前结束：今天无需执行")
            self._tray.notify("校园网自动登录", "今天无需执行任务")
            return

        # 逐项核对：wifi_connected=None 表示未配置 WiFi（有线用户），不算失败
        failed: list[str] = []
        wifi_result = results.get("连接WiFi")
        if isinstance(wifi_result, dict) and wifi_result.get("wifi_connected") is False:
            failed.append("WiFi 连接")
        login_result = results.get("登录校园网")
        if isinstance(login_result, dict) and not login_result.get("login_successful", False):
            failed.append("校园网登录")

        shutdown_result = results.get("设置定时关机")
        shutdown_set = isinstance(shutdown_result, dict) and shutdown_result.get(
            "shutdown_set", False
        )
        # reason=time_passed（已过今日关机时间）是正常跳过，不算失败
        shutdown_failed = isinstance(shutdown_result, dict) and (
            shutdown_result.get("reason") == "command_failed" or "error" in shutdown_result
        )
        if shutdown_failed:
            failed.append("定时关机")

        hh = int(global_config.get("SHUTDOWN_HOUR", 23))
        mm = int(global_config.get("SHUTDOWN_MIN", 0))
        if shutdown_set:
            # 记录本次会话已设置关机：退出程序时的提醒与取消入口都依赖它
            self._shutdown_scheduled = True
        if failed:
            fail_text = "、".join(failed)
            summary = (
                f"{fail_text}失败；已设置 {hh:02d}:{mm:02d} 定时关机"
                if shutdown_set
                else f"{fail_text}失败"
            )
            self.footer_status.setText(summary)
            error("main", f"任务链执行完成，存在失败步骤：{fail_text}", exc_info=False)
            self._tray.notify("校园网自动登录", f"{summary}，详情见运行日志")
        elif shutdown_set:
            self.footer_status.setText(f"所有任务执行完成，已设置 {hh:02d}:{mm:02d} 关机")
            info("main", "任务链执行成功")
            self._tray.notify(
                "校园网自动登录", f"所有任务执行完成，已设置 {hh:02d}:{mm:02d} 定时关机"
            )
        else:
            self.footer_status.setText("所有任务执行完成（已过今日关机时间，未设置关机）")
            info("main", "任务链执行成功（已过今日关机时间，未设置关机）")
            self._tray.notify("校园网自动登录", "任务执行完成（已过今日关机时间，未设置关机）")

    def _on_chain_error(self, results: dict[str, Any]) -> None:
        """任务链异常终止回调：恢复按钮并提示失败。"""
        self._set_buttons_enabled(True)
        self.footer_status.setText("任务链执行失败")
        error("main", f"任务链执行失败: {results}")

    # ------------------------------------------------------------------
    # 按钮事件
    # ------------------------------------------------------------------

    def on_run_once(self) -> None:
        """「立即执行」按钮：确认后手动触发一次完整任务链（Ctrl+R）。

        确认框默认聚焦"否"：执行链会设置定时关机，属危险操作，回车不应直接放行。
        """
        if (
            QMessageBox.question(
                self,
                "确认",
                "是否立即执行一次完整任务（WiFi+登录+关机）？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            info("main", "用户手动触发：开始执行完整任务链")
            self.start_task_chain()

    def on_cancel_shutdown(self) -> None:
        """「取消关机」按钮：确认后在后台执行 shutdown /a，并按返回值反馈结果。"""
        if (
            QMessageBox.question(
                self,
                "确认",
                "是否取消已设置的关机任务？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        # 防重入：任务链/其他测试进行中时不再受理
        if not self.run_btn.isEnabled():
            info("main", "已有任务进行中，忽略取消关机请求")
            return

        self._set_buttons_enabled(False, busy_text="取消中...")
        self.footer_status.setText("正在取消关机...")

        def _do_cancel_shutdown(ctx: TaskContext) -> bool:
            """后台线程执行取消命令（shutdown /a 最坏可阻塞 10 秒，不能卡界面）。"""
            return cancel_shutdown()

        self._run_background_test(
            _do_cancel_shutdown,
            "cancel_shutdown",
            self._on_cancel_shutdown_finished,
            self._on_cancel_shutdown_error,
        )

    def _on_cancel_shutdown_finished(self, task_name: str, result: object) -> None:
        """取消关机完成：按返回值区分成功/失败反馈。"""
        self._set_buttons_enabled(True)
        if result is True:
            self._shutdown_scheduled = False
            info("main", "用户手动取消了已设置的关机任务")
            self.footer_status.setText("已取消关机")
            QMessageBox.information(self, "完成", "已成功取消关机任务")
        else:
            error("main", "取消关机任务失败（shutdown /a 返回失败）", exc_info=False)
            self.footer_status.setText("取消关机失败")
            QMessageBox.warning(
                self,
                "错误",
                "取消关机任务失败！\n\n电脑仍会按计划关机，"
                "请手动打开命令行执行 shutdown /a，详情见运行日志。",
            )

    def _on_cancel_shutdown_error(self, task_name: str, error_msg: str) -> None:
        """取消关机线程抛异常时的错误提示。"""
        self._set_buttons_enabled(True)
        self.footer_status.setText("取消关机出错")
        error("main", f"取消关机异常：{error_msg}")
        QMessageBox.critical(self, "错误", f"取消关机出错：{self._friendly_error(error_msg)}")

    @staticmethod
    def _friendly_error(error_msg: str) -> str:
        """把技术异常信息映射为用户可读文案（技术细节保留在日志里）。"""
        if error_msg.startswith("TimeoutError"):
            return "操作超时，请检查网络环境后重试"
        if error_msg.startswith("ConnectionError") or error_msg.startswith("RequestException"):
            return "网络连接失败，请检查网络后重试"
        return error_msg

    def on_test_wifi(self) -> None:
        """「测试 WiFi」按钮：后台线程单独测试 WiFi 连接（不走任务链）。

        结果通过字符串状态码区分（见 _do_wifi_test 返回值），
        完成后弹窗告知用户。
        """
        wifi_name = global_config.get("WIFI_NAME", "")
        if not wifi_name:
            QMessageBox.warning(self, "提示", "请先在设置中配置 WiFi 名称")
            return

        if (
            QMessageBox.question(self, "确认", f"是否测试连接 WiFi：{wifi_name}？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        # 防重入：任务链/其他测试进行中时不再受理（避免并发操作 WiFi）
        if not self.run_btn.isEnabled():
            info("main", "已有任务进行中，忽略 WiFi 测试请求")
            return

        self._set_buttons_enabled(False, busy_text="测试中...")
        self.footer_status.setText("正在测试 WiFi...")
        info("main", f"开始测试 WiFi 连接：{wifi_name}")
        self._test_wifi_name = wifi_name

        def _do_wifi_test(ctx: TaskContext) -> str:
            """在后台线程执行的测试逻辑，返回状态码供 UI 判断。"""
            if is_wifi_connected(wifi_name):
                return "already_connected"  # 本来就已连接
            wifi_password = global_config.get("WIFI_PASSWORD", "")
            if connect_wifi(wifi_name, wifi_password):
                # 等待连接稳定后再验证（分片睡眠，任务取消时可提前退出）
                interruptible_sleep(3, ctx.is_cancelled)
                if is_wifi_connected(wifi_name):
                    return "connected"  # 连接成功且稳定
                return "failed_after_connect"  # 发起连接但未稳定连上
            return "connect_command_failed"  # 连接命令执行失败

        self._run_background_test(
            _do_wifi_test, "test_wifi", self._on_wifi_test_finished, self._on_wifi_test_error
        )

    def _on_wifi_test_finished(self, task_name: str, result: object) -> None:
        """WiFi 测试完成：按状态码弹出对应结果提示。"""
        self._set_buttons_enabled(True)
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
        """WiFi 测试线程抛异常时的错误提示。"""
        self._set_buttons_enabled(True)
        self.footer_status.setText("WiFi 测试出错")
        error("main", f"WiFi 测试异常：{error_msg}")
        QMessageBox.critical(self, "错误", f"WiFi 测试出错：{self._friendly_error(error_msg)}")

    def on_test_login(self) -> None:
        """「测试登录」按钮：后台线程单独测试校园网认证（不走任务链）。

        按返回值区分成功/失败弹窗，详细过程写入运行日志
        （campus_login 内部已分级记录）。
        """
        username = global_config.get("USERNAME", "")
        if not username:
            QMessageBox.warning(self, "提示", "请先在设置中配置校园网账号")
            return

        if (
            QMessageBox.question(self, "确认", "是否测试校园网登录？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        # 防重入：任务链/其他测试进行中时不再受理
        if not self.run_btn.isEnabled():
            info("main", "已有任务进行中，忽略登录测试请求")
            return

        self._set_buttons_enabled(False, busy_text="测试中...")
        self.footer_status.setText("正在测试登录...")
        info("main", "测试校园网登录")

        def _do_login_test(ctx: TaskContext) -> bool:
            """后台线程执行登录测试，成功与否都通过 finished 信号回报。"""
            return campus_login()

        self._run_background_test(
            _do_login_test, "test_login", self._on_login_test_finished, self._on_login_test_error
        )

    def _run_background_test(
        self,
        func: Callable[[TaskContext], Any],
        name: str,
        on_finished: Callable[[str, object], None],
        on_error: Callable[[str, str], None],
    ) -> None:
        """在独立单线程 executor 中运行单项测试任务，完成后自动回收线程池。

        WiFi/登录两个测试按钮共用的装配逻辑：连接 finished/error 信号、
        持有 executor 防 GC、任务结束后从列表移除并关闭。
        """
        executor = TaskExecutor(max_workers=1)
        self._test_executors.append(executor)
        executor.finished.connect(on_finished)
        executor.error.connect(on_error)
        executor.finished.connect(lambda *_: self._release_test_executor(executor))
        executor.error.connect(lambda *_: self._release_test_executor(executor))
        executor.submit(func, name)

    def _release_test_executor(self, executor: TaskExecutor) -> None:
        """从测试 executor 列表中移除已完成的 executor 并关闭它。"""
        with contextlib.suppress(ValueError):
            self._test_executors.remove(executor)
        executor.shutdown(wait=False)

    def _on_login_test_finished(self, task_name: str, result: object) -> None:
        """登录测试完成：按返回值区分成功/失败（详细过程见运行日志）。"""
        self._set_buttons_enabled(True)
        if result is True:
            info("main", "校园网登录测试成功")
            self.footer_status.setText("登录测试成功")
            QMessageBox.information(self, "测试结果", "校园网登录测试成功")
        else:
            error("main", "校园网登录测试失败", exc_info=False)
            self.footer_status.setText("登录测试失败")
            QMessageBox.warning(
                self,
                "测试结果",
                "校园网登录测试失败\n\n"
                "请检查：\n"
                "- 账号密码是否正确\n"
                "- 运营商类型是否匹配\n"
                "- 网络是否连通\n\n"
                "详情见运行日志",
            )

    def _on_login_test_error(self, task_name: str, error_msg: str) -> None:
        """登录测试线程抛异常时的错误提示。"""
        self._set_buttons_enabled(True)
        self.footer_status.setText("登录测试失败")
        error("main", f"校园网登录测试异常：{error_msg}")
        QMessageBox.critical(self, "错误", f"校园网登录测试失败：{self._friendly_error(error_msg)}")

    def on_settings(self) -> None:
        """切换到设置标签页（嵌入式设置，不再弹窗）。"""
        self.main_tabs.setCurrentWidget(self._settings_panel)

    def _on_config_saved(self) -> None:
        """设置面板保存配置后刷新状态显示与万年历。"""
        self._update_status_display()
        self._calendar_view.update_theme()
        self.footer_status.setText("配置已保存")
        info("main", "配置已保存")

    def _on_theme_changed_external(self, theme_name: str) -> None:
        """设置面板切换主题后刷新万年历视图（全局 QSS 已即时重绘）。"""
        self._calendar_view.update_theme()

    # ------------------------------------------------------------------
    # 对话框
    # ------------------------------------------------------------------

    def show_about(self) -> None:
        """弹出"关于"对话框（F1）。"""
        AboutDialog(self).exec()

    def show_calendar(self) -> None:
        """切换到任务日历标签页（嵌入式万年历，不再弹窗）。"""
        self.main_tabs.setCurrentWidget(self._calendar_view)

    # ------------------------------------------------------------------
    # 窗口关闭
    # ------------------------------------------------------------------

    def show_from_tray(self) -> None:
        """显示并激活主窗口（供托盘双击/单实例通知调用）。"""
        self.showNormal()
        self.activateWindow()
        self.raise_()
        info("main", "已显示主窗口")

    def _real_close(self) -> None:
        """真实退出：确认关机仍在生效后置标志，触发 closeEvent 走完整清理流程。"""
        # 已设置定时关机时提醒一次：关机由 Windows 调度，退出程序不会取消它
        if self._shutdown_scheduled:
            ret = QMessageBox.question(
                self,
                "确认退出",
                "确定退出程序？\n\n"
                "注意：已设置的定时关机由 Windows 调度，退出本程序后仍会按时执行；"
                "如需取消请先点「取消关机」。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return
        self._force_quit = True
        self.close()

    def quit_application(self) -> None:
        """公共退出方法，供 TrayManager 等外部组件调用。"""
        self._real_close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """关闭事件分流：托盘可用时隐藏驻留，否则走真实退出清理。

        真实退出流程：确认有任务运行 → 取消/关闭所有 executor →
        恢复 stdout/stderr → 显式退出事件循环（托盘驻留时必需）。
        """
        # 未点"退出"而只是点窗口关闭按钮：最小化到托盘继续运行
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

        # 窗口处于隐藏（托盘驻留）状态时，接受关闭不会触发 lastWindowClosed
        # （Qt 只对可见窗口计数），需显式退出事件循环——修复托盘"退出"
        # 在窗口隐藏时无效的问题
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)
