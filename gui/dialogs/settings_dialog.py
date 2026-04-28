"""
设置对话框模块
现代卡片式设计，支持主题切换
"""
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFormLayout, QTabWidget, QWidget, QCheckBox, QComboBox,
    QMessageBox,
)
from PyQt5.QtCore import Qt

from system_core import global_config, DEFAULT_CONFIG, save_config
from gui.widgets import DateRuleWidget, CompensatoryWorkdayWidget, BaseHolidayWidget
from gui.dialogs.password_dialog import ChangeMasterPasswordDialog
from gui.style_helpers import (
    create_button, create_label, create_section_title,
    create_tip_label,
)
from gui.style_manager import StyleManager, ThemeManager
from gui.styles import FontSize, FontStyle, StyleConstants

# 解密失败的字段在 UI 中显示此占位符
_DECRYPT_FAILED_PLACEHOLDER = "********"


class SettingsDialog(QDialog):
    """配置设置对话框"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setMinimumSize(850, 650)

        # 注意：不要在构造函数中调用 load_config()！
        # MainWindow 启动时已经加载过配置，这里再调会重置 global_config 导致设置显示空白。
        # 控件引用
        self.tab_widget: Optional[QTabWidget] = None
        self.wifi_name_edit: Optional[QLineEdit] = None
        self.wifi_password_edit: Optional[QLineEdit] = None
        self.wifi_retry_edit: Optional[QLineEdit] = None
        self.retry_interval_edit: Optional[QLineEdit] = None
        self.username_edit: Optional[QLineEdit] = None
        self.password_edit: Optional[QLineEdit] = None
        self.isp_combo: Optional[QComboBox] = None
        self.wan_ip_edit: Optional[QLineEdit] = None
        self.shutdown_hour_edit: Optional[QLineEdit] = None
        self.shutdown_min_edit: Optional[QLineEdit] = None
        self.date_rule_widget: Optional[DateRuleWidget] = None
        self.compensatory_widget: Optional[CompensatoryWorkdayWidget] = None
        self.base_holiday_widget: Optional[BaseHolidayWidget] = None
        self.show_lunar_check: Optional[QCheckBox] = None
        self.lunar_format_combo: Optional[QComboBox] = None
        self.theme_combo: Optional[QComboBox] = None

        self._init_ui()
        self._apply_styles()

    def _is_field_decrypt_failed(self, field_name: str) -> bool:
        """检查指定字段是否解密失败"""
        return field_name in global_config.get("_DECRYPT_FAILED_FIELDS", [])

    def _set_password_field_text(self, edit: QLineEdit, field_name: str) -> None:
        """安全地设置密码字段文本（解密失败时显示占位符）"""
        if self._is_field_decrypt_failed(field_name):
            edit.setText(_DECRYPT_FAILED_PLACEHOLDER)
            edit.setToolTip("该字段解密失败，保留上次加密值。如需修改请重新输入。")
        else:
            edit.setText(global_config.get(field_name, DEFAULT_CONFIG.get(field_name, "")))

    def _is_password_placeholder(self, text: str) -> bool:
        """检查密码字段文本是否为占位符（表示解密失败未修改）"""
        return text == _DECRYPT_FAILED_PLACEHOLDER

    def _init_ui(self) -> None:
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 主题切换区域
        self._create_theme_selector(main_layout)

        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("settingsTab")
        main_layout.addWidget(self.tab_widget)

        # 创建所有标签页（一次性创建，不用懒加载避免 bug）
        self.tab_widget.addTab(self._create_wifi_tab(), "WiFi 配置")
        self.tab_widget.addTab(self._create_login_tab(), "校园网登录配置")
        self.tab_widget.addTab(self._create_shutdown_tab(), "自动关机配置")
        self.tab_widget.addTab(self._create_date_rule_tab(), "自定义日期规则")
        self.tab_widget.addTab(self._create_compensatory_tab(), "调休上班日")
        self.tab_widget.addTab(self._create_base_holiday_tab(), "基础节假日")
        self.tab_widget.addTab(self._create_app_tab(), "应用程序设置")

        # 按钮区域
        self._create_button_box(main_layout)

    def _create_theme_selector(self, parent_layout: QVBoxLayout) -> None:
        """创建主题选择器"""
        theme_frame = QWidget()
        theme_frame.setMinimumHeight(48)
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.setContentsMargins(16, 8, 16, 8)

        theme_label = create_label("主题：", font_size=FontSize.CONTENT_SMALL, bold=True)
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeSelector")
        self.theme_combo.setMinimumWidth(160)

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
            "light": "\u2600\ufe0f 亮色主题",
            "dark": "\U0001F319 暗色主题",
        }
        return display_map.get(theme_name, theme_name)

    def _on_theme_changed(self, index: int) -> None:
        """主题切换处理"""
        theme_name = self.theme_combo.itemData(index)
        if theme_name:
            ThemeManager.set_theme(theme_name)
            self._apply_styles()
            self._update_child_themes()

    def _update_child_themes(self) -> None:
        """更新子组件主题"""
        if self.date_rule_widget:
            self.date_rule_widget.update_theme()
        if self.compensatory_widget:
            self.compensatory_widget.update_theme()
        if self.base_holiday_widget:
            self.base_holiday_widget.update_theme()

    def _create_wifi_tab(self) -> QWidget:
        """创建 WiFi 配置标签页"""
        wifi_tab = QWidget()
        wifi_layout = QFormLayout(wifi_tab)
        wifi_layout.setSpacing(15)
        wifi_layout.setContentsMargins(24, 20, 24, 20)
        wifi_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.wifi_name_edit = QLineEdit()
        self.wifi_name_edit.setText(global_config.get("WIFI_NAME", DEFAULT_CONFIG["WIFI_NAME"]))
        self.wifi_name_edit.setPlaceholderText("请输入 WiFi 名称")
        self.wifi_name_edit.setMinimumHeight(38)
        wifi_layout.addRow("WiFi 名称：", self.wifi_name_edit)

        self.wifi_password_edit, self.wifi_password_visible, pwd_layout = self._create_password_field("WIFI_PASSWORD")
        wifi_layout.addRow("WiFi 密码：", pwd_layout)

        self.wifi_retry_edit = QLineEdit()
        self.wifi_retry_edit.setText(str(global_config.get("MAX_WIFI_RETRY", DEFAULT_CONFIG["MAX_WIFI_RETRY"])))
        self.wifi_retry_edit.setMinimumHeight(38)
        wifi_layout.addRow("最大重试次数：", self.wifi_retry_edit)

        self.retry_interval_edit = QLineEdit()
        self.retry_interval_edit.setText(str(global_config.get("RETRY_INTERVAL", DEFAULT_CONFIG["RETRY_INTERVAL"])))
        self.retry_interval_edit.setMinimumHeight(38)
        wifi_layout.addRow("重试间隔(秒)：", self.retry_interval_edit)

        return wifi_tab

    def _create_login_tab(self) -> QWidget:
        """创建校园网登录配置标签页"""
        login_tab = QWidget()
        login_layout = QFormLayout(login_tab)
        login_layout.setSpacing(15)
        login_layout.setContentsMargins(24, 20, 24, 20)
        login_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_edit = QLineEdit()
        self.username_edit.setText(global_config.get("USERNAME", DEFAULT_CONFIG["USERNAME"]))
        self.username_edit.setPlaceholderText("请输入校园网用户名")
        self.username_edit.setMinimumHeight(38)
        login_layout.addRow("用户名：", self.username_edit)

        self.password_edit, self.password_visible, login_pwd_layout = self._create_password_field("PASSWORD")
        login_layout.addRow("密码：", login_pwd_layout)

        self.isp_combo = QComboBox()
        self.isp_combo.addItems(["移动", "电信", "联通"])
        self.isp_combo.setMinimumHeight(38)
        isp_mapping = {"cmcc": 0, "telecom": 1, "unicom": 2}
        self.isp_combo.setCurrentIndex(
            isp_mapping.get(global_config.get("ISP_TYPE", DEFAULT_CONFIG["ISP_TYPE"]), 1)
        )
        login_layout.addRow("运营商类型：", self.isp_combo)

        self.wan_ip_edit = QLineEdit()
        self.wan_ip_edit.setText(global_config.get("WAN_IP", DEFAULT_CONFIG["WAN_IP"]))
        self.wan_ip_edit.setPlaceholderText("请输入 WAN IP 地址")
        self.wan_ip_edit.setMinimumHeight(38)
        login_layout.addRow("WAN IP：", self.wan_ip_edit)

        return login_tab

    def _create_shutdown_tab(self) -> QWidget:
        """创建自动关机配置标签页"""
        shutdown_tab = QWidget()
        shutdown_layout = QFormLayout(shutdown_tab)
        shutdown_layout.setSpacing(15)
        shutdown_layout.setContentsMargins(24, 20, 24, 20)
        shutdown_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.shutdown_hour_edit = QLineEdit()
        self.shutdown_hour_edit.setText(str(global_config.get("SHUTDOWN_HOUR", DEFAULT_CONFIG["SHUTDOWN_HOUR"])))
        self.shutdown_hour_edit.setPlaceholderText("请输入关机小时（0-23）")
        self.shutdown_hour_edit.setMinimumHeight(38)
        shutdown_layout.addRow("关机小时：", self.shutdown_hour_edit)

        self.shutdown_min_edit = QLineEdit()
        self.shutdown_min_edit.setText(str(global_config.get("SHUTDOWN_MIN", DEFAULT_CONFIG["SHUTDOWN_MIN"])))
        self.shutdown_min_edit.setPlaceholderText("请输入关机分钟（0-59）")
        self.shutdown_min_edit.setMinimumHeight(38)
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
        app_layout.setSpacing(15)
        app_layout.setContentsMargins(24, 20, 24, 20)

        # 安全设置
        security_title = create_section_title("安全设置")
        app_layout.addWidget(security_title)

        self.change_password_btn = create_button("更改主密码", btn_type="warning", min_width=150)
        self.change_password_btn.clicked.connect(self.on_change_password)
        app_layout.addWidget(self.change_password_btn)

        security_tip = create_tip_label("提示：主密码用于生成加密密钥，更改后会重新加密所有配置")
        app_layout.addWidget(security_tip)
        app_layout.addSpacing(20)

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
        self.lunar_format_combo.setMinimumHeight(38)
        self.lunar_format_combo.addItems([
            "简化格式（如：正月初一）",
            "完整格式（如：农历2025年正月初一）",
        ])
        self.lunar_format_combo.setCurrentIndex(global_config.get("LUNAR_DISPLAY_FORMAT", 0))
        lunar_format_layout.addWidget(self.lunar_format_combo)
        lunar_format_layout.addStretch()
        app_layout.addLayout(lunar_format_layout)

        app_layout.addStretch()

        return app_tab

    def _create_button_box(self, parent_layout: QVBoxLayout) -> None:
        """创建按钮区域"""
        button_box = QHBoxLayout()
        button_box.setSpacing(12)
        button_box.setContentsMargins(16, 12, 16, 16)

        button_box.addStretch()

        save_btn = create_button("\U0001F4BE 保存配置", btn_type="success", min_width=120)
        save_btn.clicked.connect(self.save_config)
        button_box.addWidget(save_btn)

        cancel_btn = create_button("\u274C 取消", btn_type="gray", min_width=100)
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)

        parent_layout.addLayout(button_box)

    def _apply_styles(self) -> None:
        """应用 QSS 样式"""
        qss = StyleManager.get_global_stylesheet()
        dialog_qss = StyleManager.get_dialog_stylesheet()
        self.setStyleSheet(qss + dialog_qss)

    def _create_password_field(self, field_name: str) -> tuple:
        """创建带显示/隐藏切换的密码输入框"""
        edit = QLineEdit()
        self._set_password_field_text(edit, field_name)
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setMinimumHeight(38)

        btn = create_button("显示", btn_type="gray", font_size=10, min_height=34)
        btn.setCheckable(True)
        btn.setFixedWidth(60)
        btn.clicked.connect(
            lambda: self.toggle_password_visibility(edit, btn)
        )

        layout = QHBoxLayout()
        layout.addWidget(edit)
        layout.addWidget(btn)
        return edit, btn, layout

    def toggle_password_visibility(self, password_edit: QLineEdit, button) -> None:
        """切换密码可见性"""
        if button.isChecked():
            password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("隐藏")
        else:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("显示")

    def save_config(self) -> None:
        """保存配置"""
        # WiFi 配置
        global_config["WIFI_NAME"] = self.wifi_name_edit.text()

        wifi_pwd = self.wifi_password_edit.text()
        if not self._is_password_placeholder(wifi_pwd):
            global_config["WIFI_PASSWORD"] = wifi_pwd

        try:
            val = int(self.wifi_retry_edit.text())
            if val < 0:
                raise ValueError
            global_config["MAX_WIFI_RETRY"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "最大重试次数请输入非负整数")
            return

        try:
            val = int(self.retry_interval_edit.text())
            if val < 1:
                raise ValueError
            global_config["RETRY_INTERVAL"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "重试间隔请输入大于 0 的整数")
            return

        # 校园网登录配置
        global_config["USERNAME"] = self.username_edit.text()

        login_pwd = self.password_edit.text()
        if not self._is_password_placeholder(login_pwd):
            global_config["PASSWORD"] = login_pwd

        isp_mapping = {0: "cmcc", 1: "telecom", 2: "unicom"}
        global_config["ISP_TYPE"] = isp_mapping[self.isp_combo.currentIndex()]

        global_config["WAN_IP"] = self.wan_ip_edit.text()

        # 自动关机配置
        try:
            val = int(self.shutdown_hour_edit.text())
            if not (0 <= val <= 23):
                raise ValueError
            global_config["SHUTDOWN_HOUR"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "关机小时请输入 0~23 之间的整数")
            return

        try:
            val = int(self.shutdown_min_edit.text())
            if not (0 <= val <= 59):
                raise ValueError
            global_config["SHUTDOWN_MIN"] = val
        except ValueError:
            QMessageBox.warning(self, "提示", "关机分钟请输入 0~59 之间的整数")
            return

        # 日期规则
        if self.date_rule_widget:
            self.date_rule_widget.save_rules()
            global_config["DATE_RULES"] = self.date_rule_widget.date_rules

        # 调休上班日
        if self.compensatory_widget:
            self.compensatory_widget.save_days()

        # 基础节假日
        if self.base_holiday_widget:
            self.base_holiday_widget.save_holidays()

        # 应用程序设置
        global_config["SHOW_LUNAR_CALENDAR"] = self.show_lunar_check.isChecked()
        global_config["LUNAR_DISPLAY_FORMAT"] = self.lunar_format_combo.currentIndex()

        if not save_config():
            QMessageBox.critical(self, "错误", "保存配置失败，请检查文件权限或查看日志")
            return

        QMessageBox.information(self, "提示", "配置已保存")
        self.accept()

    def on_change_password(self) -> None:
        """打开更改主密码对话框"""
        dialog = ChangeMasterPasswordDialog(self)
        dialog.exec()
