"""
主窗口模块
现代卡片式设计 - 浅灰背景 + 纯白卡片 + 圆角胶囊按钮
"""
import datetime
import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QMessageBox, QLabel, QPushButton, QMenu,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRectF
from PyQt5.QtGui import QMouseEvent, QPainter, QPainterPath, QColor, QCursor
from gui.style_manager import ThemeManager

from infrastructure import (
    Logger, logger, StreamRedirector, info, debug, warning,
    error, critical, init_logger, parse_date_str,
)
from system_core import load_config, global_config, should_work_today
from business import (
    run_tasks_once, cancel_shutdown, is_wifi_connected,
    connect_wifi, campus_login,
)
from infrastructure import get_thread_pool_manager
from concurrency import TaskChain, TaskExecutor
from business import (
    task_check_condition, task_connect_wifi,
    task_campus_login, task_set_shutdown,
)
from utils.version import get_project_version
from gui.dialogs import SettingsDialog, AboutDialog, CalendarDialog
from gui.style_helpers import (
    create_button, create_label, create_header_widget,
    create_card_widget, create_tip_label, LogTextEdit, BaseWidget,
)
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle, StyleConstants


class TitleMenuBar(QFrame):
    """可拖拽的标题菜单栏"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleMenuBar")
        self.setFixedHeight(42)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        title_label = QLabel("校园网自动登录 + 定时关机")
        title_label.setObjectName("titleLabel")
        title_label.setFont(FontStyle.bold(14))
        layout.addWidget(title_label)

        layout.addStretch()

        self._settings_menu = QMenu("设置", self)
        self._settings_menu.addAction("配置设置").triggered.connect(self._parent_on_settings)
        self._settings_menu.addSeparator()
        self._settings_menu.addAction("任务日历").triggered.connect(self._parent_show_calendar)
        self._settings_btn = QPushButton("设置 \u25be")
        self._settings_btn.setObjectName("menuBtn")
        self._settings_btn.setFixedHeight(34)
        self._settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._settings_btn.clicked.connect(self._show_settings_menu)
        layout.addWidget(self._settings_btn)

        self._help_menu = QMenu("帮助", self)
        self._help_menu.addAction("关于我们").triggered.connect(self._parent_show_about)
        self._help_btn = QPushButton("帮助 \u25be")
        self._help_btn.setObjectName("menuBtn")
        self._help_btn.setFixedHeight(34)
        self._help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._help_btn.clicked.connect(self._show_help_menu)
        layout.addWidget(self._help_btn)

        layout.addStretch()

    def _show_settings_menu(self) -> None:
        pos = self._settings_btn.mapToGlobal(QPoint(0, self._settings_btn.height()))
        self._settings_menu.exec(pos)

    def _show_help_menu(self) -> None:
        pos = self._help_btn.mapToGlobal(QPoint(0, self._help_btn.height()))
        self._help_menu.exec(pos)

    def _parent_on_settings(self) -> None:
        w = self.window()
        if hasattr(w, "on_settings"):
            w.on_settings()

    def _parent_show_calendar(self) -> None:
        w = self.window()
        if hasattr(w, "show_calendar"):
            w.show_calendar()

    def _parent_show_about(self) -> None:
        w = self.window()
        if hasattr(w, "show_about"):
            w.show_about()


class MainWindow(QMainWindow):
    """主窗口类 - 校园网自动登录 + 定时关机工具"""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setWindowTitle("校园网自动登录 + 定时关机")
        self._drag_pos: Optional[QPoint] = None
        self._corner_radius = 12
        self._shadow_margin = 6
        self._shadow_blur = 5
        self._shadow_opacity = 30

        total_w = 860 + 2 * self._shadow_margin
        total_h = 620 + 2 * self._shadow_margin
        self.setMinimumSize(total_w, total_h)
        self.resize(total_w, total_h)

        # 基础 UI（用于日志系统）
        self._init_basic_ui()

        # 初始化日志
        init_logger(gui_log_widget=self.log_text, level=1)

        # 加载配置
        load_config()

        # 重定向输出
        sys.stdout = StreamRedirector("stdout", 1)
        sys.stderr = StreamRedirector("stderr", 3)

        # 标题菜单栏（顶部固定）
        self.title_menu_bar = TitleMenuBar(self)
        self.main_layout.addWidget(self.title_menu_bar)

        # 分割线
        sep1 = QFrame()
        sep1.setObjectName("sectionSeparator")
        sep1.setFixedHeight(1)
        self.main_layout.addWidget(sep1)

        # 中间内容区（可拖动）
        self._create_content_area()

        # 分割线
        sep2 = QFrame()
        sep2.setObjectName("sectionSeparator")
        sep2.setFixedHeight(1)
        self.main_layout.addWidget(sep2)

        # 底部状态栏 + 运行日志（紧贴）
        self._create_bottom_section()

        # 任务管理器
        self.task_manager: Optional[TaskChain] = None
        self.task_executor: Optional[TaskExecutor] = None

        # 应用全局样式
        self._apply_global_style()

        # 启动后自动执行
        QTimer.singleShot(200, self.run_on_start)

        # 更新时间
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time_display)
        self._timer.start(1000)

        info("main", "主窗口初始化完成")

    def _init_basic_ui(self) -> None:
        """初始化基础 UI 组件（用于日志系统）"""
        central = QWidget()
        central.setObjectName("centralWidget")
        central.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 最外层容器（四个角 12px 圆角，内边距 8px）
        outer = QFrame()
        outer.setObjectName("outerContainer")
        self.main_layout = QVBoxLayout(outer)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(0)

        root_layout.addWidget(outer)

        # 日志文本（提前创建，用于日志系统初始化）
        self.log_text = LogTextEdit()

    def _create_content_area(self) -> None:
        """创建中间内容区域（可拖动）"""
        content = QWidget()
        content.setObjectName("contentArea")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 统一外框容器
        outer = QFrame()
        outer.setObjectName("contentOuterFrame")

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._create_status_section(outer_layout)

        content_layout.addWidget(outer)

        self.main_layout.addWidget(content, 0)

        # 更新状态显示
        QTimer.singleShot(0, self._update_status_display)

    def _create_status_section(self, parent_layout: QVBoxLayout) -> None:
        """创建状态信息卡片"""
        status_card = QWidget()
        status_card.setObjectName("contentStatusSection")
        status_card.setMinimumHeight(110)

        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(8)
        status_layout.setContentsMargins(24, 24, 24, 24)

        # 状态标题
        theme = ThemeManager.current_theme()
        status_title = create_label(
            "当前状态",
            font_size=16,
            bold=True,
            color=theme.text_primary,
        )
        status_layout.addWidget(status_title)

        # 信息网格
        info_grid = QHBoxLayout()
        info_grid.setSpacing(16)

        # 左侧 50%
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)

        self.date_label = create_label("", font_size=14)
        left_layout.addWidget(self.date_label)

        self.status_label = create_label(
            "", font_size=14
        )
        left_layout.addWidget(self.status_label)

        info_grid.addLayout(left_layout, 1)
        info_grid.addSpacing(24)

        # 右侧 50%
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        self.rule_label = create_label(
            "", font_size=14, color=theme.text_secondary
        )
        right_layout.addWidget(self.rule_label)

        self.time_label = create_label(
            "", font_size=14, color=theme.text_secondary
        )
        right_layout.addWidget(self.time_label)

        info_grid.addLayout(right_layout, 1)

        status_layout.addLayout(info_grid)
        parent_layout.addWidget(status_card)

    def _update_time_display(self) -> None:
        """更新时间显示"""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"就绪  |  {time_str}")

    def paintEvent(self, event) -> None:
        """绘制圆角窗口及柔和阴影"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        sm = self._shadow_margin
        content_rect = QRectF(self.rect()).adjusted(sm, sm, -sm, -sm)

        # 绘制阴影 — 多层同心圆角矩形，从外到内逐渐变深
        steps = self._shadow_blur
        for i in range(steps, 0, -1):
            offset = sm * i / steps
            alpha = int(self._shadow_opacity * ((1 - i / steps) ** 1.5))
            if alpha < 1:
                continue
            path = QPainterPath()
            path.addRoundedRect(
                content_rect.adjusted(-offset, -offset, offset, offset),
                self._corner_radius, self._corner_radius,
            )
            painter.fillPath(path, QColor(0, 0, 0, alpha))

        # 绘制窗口内容背景
        path = QPainterPath()
        path.addRoundedRect(content_rect, self._corner_radius, self._corner_radius)
        theme = ThemeManager.current_theme()
        painter.fillPath(path, QColor(theme.background))

        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下事件（用于窗口拖拽）"""
        if event.button() == Qt.LeftButton:
            widget = self.childAt(event.pos())
            if widget and (
                widget.objectName() in ("titleMenuBar", "contentArea")
                or (widget.parent() and widget.parent().objectName() in ("titleMenuBar", "contentArea"))
            ):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动事件（用于窗口拖拽）"""
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放事件"""
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _create_bottom_section(self) -> None:
        """创建底部运行日志区域"""
        bottom = QFrame()
        bottom.setObjectName("bottomSection")

        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # 统一外框容器（白底，12px 圆角）
        outer = QFrame()
        outer.setObjectName("logOuterFrame")

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 运行日志
        log_card = QFrame()
        log_card.setObjectName("logCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)

        log_header = QHBoxLayout()
        log_header.setContentsMargins(18, 10, 18, 6)

        log_title = create_label(
            "运行日志",
            font_size=FontSize.SECTION_TITLE,
            bold=True,
            color=ThemeManager.current_theme().primary,
        )
        log_header.addWidget(log_title)
        log_header.addStretch()
        log_layout.addLayout(log_header)

        self.log_text.setMinimumHeight(160)
        log_layout.addWidget(self.log_text)

        outer_layout.addWidget(log_card)

        # 分割线
        separator = QFrame()
        separator.setObjectName("logSeparator")
        separator.setFixedHeight(1)
        outer_layout.addWidget(separator)

        # 按钮 + 状态合并行
        combined_bar = QFrame()
        combined_bar.setObjectName("bottomStatusBar")
        combined_layout = QHBoxLayout(combined_bar)
        combined_layout.setContentsMargins(18, 6, 18, 4)
        combined_layout.setSpacing(8)

        # 左侧按钮
        self.run_btn = create_button("执行", btn_type="primary", min_width=110, font_size=13)
        self.run_btn.setToolTip("执行 WiFi 连接、校园网登录、定时关机")
        self.run_btn.clicked.connect(self.on_run_once)
        combined_layout.addWidget(self.run_btn)

        self.cancel_btn = create_button("取消关机", btn_type="outline_danger", min_width=100, font_size=12)
        self.cancel_btn.setToolTip("取消已设置的关机任务")
        self.cancel_btn.clicked.connect(self.on_cancel_shutdown)
        combined_layout.addWidget(self.cancel_btn)

        combined_layout.addSpacing(8)

        self.test_wifi_btn = create_button("WiFi", btn_type="text", min_width=80, font_size=12)
        self.test_wifi_btn.setToolTip("仅测试 WiFi 连接")
        self.test_wifi_btn.clicked.connect(self.on_test_wifi)
        combined_layout.addWidget(self.test_wifi_btn)

        self.test_login_btn = create_button("登录", btn_type="text", min_width=80, font_size=12)
        self.test_login_btn.setToolTip("仅测试校园网登录")
        self.test_login_btn.clicked.connect(self.on_test_login)
        combined_layout.addWidget(self.test_login_btn)

        self.exit_btn = create_button("退出", btn_type="text", min_width=70, font_size=12)
        self.exit_btn.clicked.connect(self.close)
        combined_layout.addWidget(self.exit_btn)

        combined_layout.addStretch()

        # 右侧状态
        self.footer_status = QLabel("就绪")
        self.footer_status.setObjectName("footerStatus")
        self.footer_status.setFont(FontStyle.normal(12))
        combined_layout.addWidget(self.footer_status)

        version_label = create_label(
            f"v{get_project_version()}",
            font_size=9,
            color=ThemeManager.current_theme().text_tertiary,
        )
        combined_layout.addWidget(version_label)

        outer_layout.addWidget(combined_bar)

        bottom_layout.addWidget(outer)
        self.main_layout.addWidget(bottom, 1)

    def _apply_global_style(self) -> None:
        """应用全局主题样式"""
        qss = StyleManager.get_global_stylesheet()
        self.setStyleSheet(qss)

    def _log_write(self, text: str) -> None:
        """写入日志（线程安全）"""
        if text.strip():
            QTimer.singleShot(0, lambda: self._append_log(text))

    def _append_log(self, text: str) -> None:
        """追加日志到文本框"""
        if not self.log_text:
            return

        level = "INFO"
        if "ERROR" in text or "出错" in text:
            level = "ERROR"
        elif "WARNING" in text or "警告" in text:
            level = "WARNING"
        elif "CRITICAL" in text:
            level = "CRITICAL"
        elif "DEBUG" in text:
            level = "DEBUG"

        self.log_text.append_colored(text.strip(), level)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """设置按钮可用状态"""
        self.run_btn.setEnabled(enabled)
        self.test_wifi_btn.setEnabled(enabled)
        self.test_login_btn.setEnabled(enabled)

    def run_on_start(self) -> None:
        """启动时自动执行一次"""
        if hasattr(self, "_task_chain_started") and self._task_chain_started:
            return
        self._task_chain_started = True

        info("main", "程序启动，开始自动执行任务链")
        QTimer.singleShot(1000, self.start_task_chain)

    def start_task_chain(self) -> None:
        """启动任务链"""
        self._set_buttons_enabled(False)

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
        """任务开始回调"""
        info("main", f"任务开始: {task_name}")

    def _on_task_finished(self, task_name: str, result: dict) -> None:
        """任务完成回调"""
        info("main", f"任务完成: {task_name}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 完成")

    def _on_task_error(self, task_name: str, error_msg: str) -> None:
        """任务出错回调"""
        error("main", f"任务出错: {task_name} - {error_msg}")
        if hasattr(self, "footer_status"):
            self.footer_status.setText(f"{task_name} 出错")

    def _on_task_progress(self, task_name: str, percent: int) -> None:
        """任务进度回调"""
        info("main", f"任务进度: {task_name} - {percent}%")

    def _on_chain_success(self, success: bool, results: list) -> None:
        """任务链成功回调"""
        self._set_buttons_enabled(True)
        if success:
            self.footer_status.setText("所有任务执行完成")
            info("main", "任务链执行成功")
        else:
            self.footer_status.setText("任务链执行完成，部分任务失败")
            info("main", "任务链执行完成，但有任务失败")

    def _on_chain_error(self, results: list) -> None:
        """任务链出错回调"""
        self._set_buttons_enabled(True)
        self.footer_status.setText("任务链执行失败")
        error("main", f"任务链执行失败: {results}")

    def _on_all_tasks_finished(self, success: bool) -> None:
        """所有任务完成回调"""
        self._set_buttons_enabled(True)
        info("main", f"所有任务执行完成，成功: {success}")

    def on_run_once(self) -> None:
        """手动执行一次完整任务"""
        if (
            QMessageBox.question(
                self, "确认", "是否立即执行一次完整任务（WiFi+登录+关机）？"
            )
            == QMessageBox.StandardButton.Yes
        ):
            info("main", "用户手动触发：开始执行完整任务链")
            self.start_task_chain()

    def on_cancel_shutdown(self) -> None:
        """取消关机任务"""
        if (
            QMessageBox.question(
                self, "确认", "是否取消已设置的关机任务？"
            )
            == QMessageBox.StandardButton.Yes
        ):
            cancel_shutdown()
            info("main", "用户手动取消了已设置的关机任务")
            self.footer_status.setText("已取消关机")
            QMessageBox.information(self, "完成", "已尝试取消关机任务")

    def on_test_wifi(self) -> None:
        """测试 WiFi 连接"""
        wifi_name = global_config.get("WIFI_NAME", "")
        if not wifi_name:
            QMessageBox.warning(
                self, "提示", "请先在设置中配置 WiFi 名称"
            )
            return

        if (
            QMessageBox.question(
                self, "确认", f"是否测试连接 WiFi：{wifi_name}？"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.footer_status.setText("正在测试 WiFi...")
        info("main", f"开始测试 WiFi 连接：{wifi_name}")

        if is_wifi_connected(wifi_name):
            info("main", f"已成功连接到 WiFi：{wifi_name}")
            self.footer_status.setText("WiFi 已连接")
            QMessageBox.information(
                self, "测试结果", f"已成功连接到 WiFi：{wifi_name}"
            )
        else:
            info("main", "WiFi 未连接，尝试建立连接...")
            if connect_wifi(
                wifi_name, global_config.get("WIFI_PASSWORD", "")
            ):
                self.footer_status.setText("正在建立 WiFi 连接...")
                QTimer.singleShot(
                    3000, lambda: self._check_wifi_result(wifi_name)
                )
            else:
                error("main", "WiFi 连接命令执行失败", exc_info=False)
                self.footer_status.setText("WiFi 连接失败")
                QMessageBox.critical(
                    self,
                    "错误",
                    "WiFi 连接命令执行失败，请检查 WiFi 名称和密码是否正确",
                )

    def _check_wifi_result(self, wifi_name: str) -> None:
        """检查 WiFi 连接结果"""
        if is_wifi_connected(wifi_name):
            info("main", f"WiFi 连接成功：{wifi_name}")
            self.footer_status.setText("WiFi 连接成功")
            QMessageBox.information(
                self, "测试结果", f"WiFi 连接成功：{wifi_name}"
            )
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

    def on_test_login(self) -> None:
        """测试校园网登录"""
        username = global_config.get("USERNAME", "")
        if not username:
            QMessageBox.warning(
                self, "提示", "请先在设置中配置校园网账号"
            )
            return

        if (
            QMessageBox.question(self, "确认", "是否测试校园网登录？")
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.footer_status.setText("正在测试登录...")
        info("main", "测试校园网登录")

        try:
            campus_login()
            self.footer_status.setText("登录测试完成")
            QMessageBox.information(
                self,
                "测试结果",
                "校园网登录测试完成，请查看日志了解详细结果",
            )
        except Exception as e:
            self.footer_status.setText("登录测试失败")
            QMessageBox.critical(
                self, "错误", f"校园网登录测试失败：{str(e)}"
            )

    def on_settings(self) -> None:
        """打开设置窗口"""
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
        """更新状态显示"""
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

        self.date_label.setText(
            f"当前日期：{today}（{today.strftime('%A')}）"
        )
        self.status_label.setText(f"今天状态：{work_status}")
        self.rule_label.setText(f"规则来源：{rule_source}")
        self.time_label.setText(
            f"关机时间："
            f"{global_config.get('SHUTDOWN_HOUR', 23):02d}:"
            f"{global_config.get('SHUTDOWN_MIN', 0):02d}"
        )

    def show_about(self) -> None:
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def show_calendar(self) -> None:
        """显示任务日历对话框"""
        dialog = CalendarDialog(self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        """关闭窗口事件"""
        if self.task_executor:
            self.task_executor.cancel_all()
            self.task_executor.shutdown(wait=False)

        active_threads = get_thread_pool_manager().get_active_threads()
        if active_threads > 0:
            if (
                QMessageBox.question(
                    self,
                    "确认",
                    f"有 {active_threads} 个任务正在执行中，是否强制退出？",
                )
                != QMessageBox.StandardButton.Yes
            ):
                event.ignore()
                return

        sys.stdout = sys.__stdout__
        event.accept()

    def log_write(self, text: str) -> None:
        """写入日志（外部调用）"""
        self._log_write(text)
