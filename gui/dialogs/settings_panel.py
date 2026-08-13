"""
设置面板模块

设置功能的嵌入式面板（主窗口"设置"标签页使用），
SettingsDialog 是其对话框包装。修改后点击"保存配置"生效，
通过 config_saved / theme_changed 信号通知主窗口刷新。
"""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import DEFAULT_CONFIG, global_config, save_config
from gui.styling.constants import FontSize
from gui.styling.theme_manager import ThemeManager
from gui.styling.widgets import (
    create_button,
    create_label,
    create_section_title,
    create_tip_label,
)
from gui.widgets import BaseHolidayWidget, CompensatoryWorkdayWidget, DateRuleWidget


class SettingsPanel(QWidget):
    """配置设置面板（嵌入主窗口标签页）。"""

    # 配置保存成功后发出（主窗口据此刷新状态显示）
    config_saved = Signal()
    # 主题即时切换后发出（主窗口据此刷新万年历视图）
    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 注意：不要在构造函数中调用 load_config()！
        # MainWindow 启动时已经加载过配置，这里再调会重置 global_config 导致设置显示空白。
        self.tab_widget: QTabWidget | None = None
        self.wifi_name_edit: QLineEdit | None = None
        self.wifi_password_edit: QLineEdit | None = None
        self.wifi_retry_edit: QLineEdit | None = None
        self.retry_interval_edit: QLineEdit | None = None
        self.username_edit: QLineEdit | None = None
        self.password_edit: QLineEdit | None = None
        self.isp_combo: QComboBox | None = None
        self.wan_ip_edit: QLineEdit | None = None
        self.shutdown_hour_edit: QLineEdit | None = None
        self.shutdown_min_edit: QLineEdit | None = None
        self.date_rule_widget: DateRuleWidget | None = None
        self.compensatory_widget: CompensatoryWorkdayWidget | None = None
        self.base_holiday_widget: BaseHolidayWidget | None = None
        self.show_lunar_check: QCheckBox | None = None
        self.lunar_format_combo: QComboBox | None = None
        self.theme_combo: QComboBox | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI（紧凑布局适配嵌入式标签页）"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 主题切换区域
        self._create_theme_selector(main_layout)

        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("settingsTab")
        main_layout.addWidget(self.tab_widget, 1)

        # 创建所有标签页（一次性创建，不用懒加载避免 bug）；
        # 每个页面包一层滚动区域，窗口较小时内容可上下滚动不被截断
        self.tab_widget.addTab(self._wrap_scrollable(self._create_wifi_tab()), "WiFi")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_login_tab()), "校园网登录")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_shutdown_tab()), "定时关机")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_date_rule_tab()), "日期规则")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_compensatory_tab()), "调休上班")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_base_holiday_tab()), "节假日")
        self.tab_widget.addTab(self._wrap_scrollable(self._create_app_tab()), "其他")

        # 保存按钮
        self._create_save_row(main_layout)

    @staticmethod
    def _wrap_scrollable(widget: QWidget) -> QScrollArea:
        """将标签页内容包进滚动区域（内容超高时可滚动查看）。"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        scroll.setWidget(widget)
        return scroll

    def _create_theme_selector(self, parent_layout: QVBoxLayout) -> None:
        """创建主题选择器"""
        theme_frame = QWidget()
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.setContentsMargins(2, 2, 2, 2)

        theme_label = create_label("主题：", font_size=FontSize.CONTENT_SMALL, bold=True)
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeSelector")
        self.theme_combo.setMinimumWidth(140)

        themes = ThemeManager.available_themes()
        current_theme = ThemeManager.current_theme_name()

        for theme_name in themes:
            display_name = self._get_theme_display_name(theme_name)
            self.theme_combo.addItem(display_name, theme_name)
            if theme_name == current_theme:
                self.theme_combo.setCurrentIndex(self.theme_combo.count() - 1)

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()

        parent_layout.addWidget(theme_frame)

    def _get_theme_display_name(self, theme_name: str) -> str:
        """获取主题显示名称"""
        display_map = {
            "light": "☀️ 亮色主题",
            "dark": "\U0001f319 暗色主题",
        }
        return display_map.get(theme_name, theme_name)

    def _on_theme_changed(self, index: int) -> None:
        """主题切换处理（即时生效并通知主窗口）"""
        assert self.theme_combo is not None
        theme_name = self.theme_combo.itemData(index)
        if theme_name:
            ThemeManager.set_theme(theme_name)
            global_config["THEME"] = theme_name
            self._update_child_themes()
            self.theme_changed.emit(theme_name)

    def _update_child_themes(self) -> None:
        """更新子组件主题"""
        if self.date_rule_widget:
            self.date_rule_widget.update_theme()
        if self.compensatory_widget:
            self.compensatory_widget.update_theme()
        if self.base_holiday_widget:
            self.base_holiday_widget.update_theme()

    def _create_form_tab(self) -> tuple[QWidget, QFormLayout]:
        """创建统一规格的表单标签页（紧凑间距）。"""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)
        form.setContentsMargins(16, 12, 16, 12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        return tab, form

    def _create_wifi_tab(self) -> QWidget:
        """创建 WiFi 配置标签页"""
        wifi_tab, wifi_layout = self._create_form_tab()

        self.wifi_name_edit = QLineEdit()
        self.wifi_name_edit.setText(global_config.get("WIFI_NAME", DEFAULT_CONFIG["WIFI_NAME"]))
        self.wifi_name_edit.setPlaceholderText("请输入 WiFi 名称")
        self.wifi_name_edit.setMinimumHeight(30)
        wifi_layout.addRow("WiFi 名称：", self.wifi_name_edit)

        self.wifi_password_edit, self.wifi_password_visible, pwd_layout = (
            self._create_password_field("WIFI_PASSWORD")
        )
        wifi_layout.addRow("WiFi 密码：", pwd_layout)

        self.wifi_retry_edit = QLineEdit()
        self.wifi_retry_edit.setText(
            str(global_config.get("MAX_WIFI_RETRY", DEFAULT_CONFIG["MAX_WIFI_RETRY"]))
        )
        self.wifi_retry_edit.setMinimumHeight(30)
        wifi_layout.addRow("最大重试次数：", self.wifi_retry_edit)

        self.retry_interval_edit = QLineEdit()
        self.retry_interval_edit.setText(
            str(global_config.get("RETRY_INTERVAL", DEFAULT_CONFIG["RETRY_INTERVAL"]))
        )
        self.retry_interval_edit.setMinimumHeight(30)
        wifi_layout.addRow("重试间隔(秒)：", self.retry_interval_edit)

        return wifi_tab

    def _create_login_tab(self) -> QWidget:
        """创建校园网登录配置标签页"""
        login_tab, login_layout = self._create_form_tab()

        self.username_edit = QLineEdit()
        self.username_edit.setText(global_config.get("USERNAME", DEFAULT_CONFIG["USERNAME"]))
        self.username_edit.setPlaceholderText("请输入校园网用户名")
        self.username_edit.setMinimumHeight(30)
        login_layout.addRow("用户名：", self.username_edit)

        self.password_edit, self.password_visible, login_pwd_layout = self._create_password_field(
            "PASSWORD"
        )
        login_layout.addRow("密码：", login_pwd_layout)

        self.isp_combo = QComboBox()
        self.isp_combo.addItems(["移动", "电信", "联通"])
        self.isp_combo.setMinimumHeight(30)
        isp_mapping = {"cmcc": 0, "telecom": 1, "unicom": 2}
        self.isp_combo.setCurrentIndex(
            isp_mapping.get(global_config.get("ISP_TYPE", DEFAULT_CONFIG["ISP_TYPE"]), 1)
        )
        login_layout.addRow("运营商类型：", self.isp_combo)

        self.wan_ip_edit = QLineEdit()
        self.wan_ip_edit.setText(global_config.get("WAN_IP", DEFAULT_CONFIG["WAN_IP"]))
        self.wan_ip_edit.setPlaceholderText("请输入 WAN IP 地址")
        self.wan_ip_edit.setMinimumHeight(30)
        login_layout.addRow("WAN IP：", self.wan_ip_edit)

        return login_tab

    def _create_shutdown_tab(self) -> QWidget:
        """创建自动关机配置标签页"""
        shutdown_tab, shutdown_layout = self._create_form_tab()

        self.shutdown_hour_edit = QLineEdit()
        self.shutdown_hour_edit.setText(
            str(global_config.get("SHUTDOWN_HOUR", DEFAULT_CONFIG["SHUTDOWN_HOUR"]))
        )
        self.shutdown_hour_edit.setPlaceholderText("请输入关机小时（0-23）")
        self.shutdown_hour_edit.setMinimumHeight(30)
        shutdown_layout.addRow("关机小时：", self.shutdown_hour_edit)

        self.shutdown_min_edit = QLineEdit()
        self.shutdown_min_edit.setText(
            str(global_config.get("SHUTDOWN_MIN", DEFAULT_CONFIG["SHUTDOWN_MIN"]))
        )
        self.shutdown_min_edit.setPlaceholderText("请输入关机分钟（0-59）")
        self.shutdown_min_edit.setMinimumHeight(30)
        shutdown_layout.addRow("关机分钟：", self.shutdown_min_edit)

        tip = create_tip_label("提示：关机时间格式为 24 小时制，例如 23:00 表示晚上 11 点")
        shutdown_layout.addRow("", tip)

        return shutdown_tab

    def _create_date_rule_tab(self) -> QWidget:
        """创建自定义日期规则标签页"""
        self.date_rule_widget = DateRuleWidget(self)
        return self.date_rule_widget

    def _create_compensatory_tab(self) -> QWidget:
        """创建调休上班日标签页"""
        self.compensatory_widget = CompensatoryWorkdayWidget(self)
        return self.compensatory_widget

    def _create_base_holiday_tab(self) -> QWidget:
        """创建基础节假日标签页"""
        self.base_holiday_widget = BaseHolidayWidget(self)
        return self.base_holiday_widget

    def _create_app_tab(self) -> QWidget:
        """创建应用程序设置标签页"""
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)
        app_layout.setSpacing(10)
        app_layout.setContentsMargins(16, 12, 16, 12)

        # 万年历显示设置
        calendar_title = create_section_title("万年历显示设置")
        app_layout.addWidget(calendar_title)

        self.show_lunar_check = QCheckBox("显示农历、干支、宜忌等信息")
        self.show_lunar_check.setChecked(global_config.get("SHOW_LUNAR_CALENDAR", True))
        app_layout.addWidget(self.show_lunar_check)

        lunar_format_label = create_label("农历显示格式：", bold=True)
        app_layout.addWidget(lunar_format_label)

        lunar_format_layout = QHBoxLayout()
        self.lunar_format_combo = QComboBox()
        self.lunar_format_combo.setMinimumHeight(30)
        self.lunar_format_combo.addItems(
            [
                "简化格式（如：正月初一）",
                "完整格式（如：农历2025年正月初一）",
            ]
        )
        self.lunar_format_combo.setCurrentIndex(global_config.get("LUNAR_DISPLAY_FORMAT", 0))
        lunar_format_layout.addWidget(self.lunar_format_combo)
        lunar_format_layout.addStretch()
        app_layout.addLayout(lunar_format_layout)

        app_layout.addStretch()

        return app_tab

    def _create_save_row(self, parent_layout: QVBoxLayout) -> None:
        """创建保存按钮行"""
        save_row = QHBoxLayout()
        save_row.setContentsMargins(2, 2, 2, 2)

        tip = create_tip_label('点击右侧"保存配置"生效')
        tip.setWordWrap(False)  # 保持单行，避免在窄窗口下换行
        save_row.addWidget(tip)
        save_row.addStretch()

        save_btn = create_button("\U0001f4be 保存配置", btn_type="success", min_width=110)
        save_btn.clicked.connect(self.save_config)
        save_row.addWidget(save_btn)

        parent_layout.addLayout(save_row)

    def _create_password_field(self, field_name: str) -> tuple[QLineEdit, QPushButton, QHBoxLayout]:
        """创建带显示/隐藏切换的密码输入框"""
        edit = QLineEdit()
        edit.setText(global_config.get(field_name, DEFAULT_CONFIG.get(field_name, "")))
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setMinimumHeight(30)

        btn = create_button("显示", btn_type="gray", font_size=10, min_height=28)
        btn.setCheckable(True)
        btn.setFixedWidth(56)
        btn.clicked.connect(self._make_toggle_handler(edit, btn))

        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(btn)
        return edit, btn, layout

    def toggle_password_visibility(self, password_edit: QLineEdit, button: QPushButton) -> None:
        """切换密码可见性"""
        if button.isChecked():
            password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("隐藏")
        else:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("显示")

    def _make_toggle_handler(self, edit: QLineEdit, button: QPushButton) -> Callable[[], None]:
        """为密码可见性切换创建独立回调，避免 lambda 形成引用链。"""

        def _handler() -> None:
            self.toggle_password_visibility(edit, button)

        return _handler

    def save_config(self) -> None:
        """保存配置——先收集到临时 dict，全部验证通过后统一写入 global_config"""
        # _init_ui 保证以下控件已初始化
        assert (
            self.wifi_name_edit is not None
            and self.wifi_password_edit is not None
            and self.wifi_retry_edit is not None
            and self.retry_interval_edit is not None
            and self.username_edit is not None
            and self.password_edit is not None
            and self.isp_combo is not None
            and self.wan_ip_edit is not None
            and self.shutdown_hour_edit is not None
            and self.shutdown_min_edit is not None
            and self.show_lunar_check is not None
            and self.lunar_format_combo is not None
        )

        # 先收集到临时 dict，全部验证通过后再写入 global_config
        pending: dict[str, object] = {}

        # WiFi 配置
        pending["WIFI_NAME"] = self.wifi_name_edit.text()
        pending["WIFI_PASSWORD"] = self.wifi_password_edit.text()

        try:
            val = int(self.wifi_retry_edit.text())
            if val < 0:
                raise ValueError
            pending["MAX_WIFI_RETRY"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "最大重试次数请输入非负整数")
            return

        try:
            val = int(self.retry_interval_edit.text())
            if val < 1:
                raise ValueError
            pending["RETRY_INTERVAL"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "重试间隔请输入大于 0 的整数")
            return

        # 校园网登录配置
        pending["USERNAME"] = self.username_edit.text()
        pending["PASSWORD"] = self.password_edit.text()

        isp_mapping = {0: "cmcc", 1: "telecom", 2: "unicom"}
        pending["ISP_TYPE"] = isp_mapping[self.isp_combo.currentIndex()]

        pending["WAN_IP"] = self.wan_ip_edit.text()

        # 自动关机配置
        try:
            val = int(self.shutdown_hour_edit.text())
            if not (0 <= val <= 23):
                raise ValueError
            pending["SHUTDOWN_HOUR"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "关机小时请输入 0~23 之间的整数")
            return

        try:
            val = int(self.shutdown_min_edit.text())
            if not (0 <= val <= 59):
                raise ValueError
            pending["SHUTDOWN_MIN"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "关机分钟请输入 0~59 之间的整数")
            return

        # 日期规则
        if self.date_rule_widget:
            self.date_rule_widget.save_rules()
            pending["DATE_RULES"] = self.date_rule_widget.date_rules

        # 调休上班日
        if self.compensatory_widget:
            self.compensatory_widget.save_days()

        # 基础节假日
        if self.base_holiday_widget:
            self.base_holiday_widget.save_holidays()

        # 应用程序设置
        pending["SHOW_LUNAR_CALENDAR"] = self.show_lunar_check.isChecked()
        pending["LUNAR_DISPLAY_FORMAT"] = self.lunar_format_combo.currentIndex()

        # 所有验证通过，统一写入 global_config
        for key, value in pending.items():
            global_config[key] = value

        if not save_config():
            QMessageBox.critical(self, "错误", "保存配置失败，请检查文件权限或查看日志")
            return

        self.config_saved.emit()
