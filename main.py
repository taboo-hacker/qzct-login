import datetime
import os
import sys
from zhdate import ZhDate
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QApplication, QStatusBar,
                             QScrollArea, QFrame, QDialog, QFormLayout, QLineEdit, QDateEdit,
                             QComboBox, QInputDialog, QCheckBox, QGridLayout, QListWidget,
                             QListWidgetItem, QTabWidget, QDialogButtonBox, QCalendarWidget,
                             QSplitter)
from PyQt5.QtGui import QFont, QPixmap, QTextCharFormat, QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate
import logging

# 导入新的日志系统
from infrastructure import Logger, logger, StreamRedirector, info, debug, warning, error, critical, init_logger, parse_date_str, is_date_in_period, format_period

# 版本号缓存
_cached_project_version = None


def get_project_version():
    """
    从 pyproject.toml 中读取项目版本号
    
    功能说明：
        - 定位项目根目录下的 pyproject.toml 文件
        - 解析文件内容并提取 version 字段
        - 使用缓存机制避免重复读取
        - 如果读取失败，返回默认版本号 "1.0.0"
    
    参数：
        无
    
    返回值：
        str: 项目版本号
    
    异常：
        无（异常会被捕获并返回默认值）
    """
    global _cached_project_version
    if _cached_project_version is not None:
        return _cached_project_version
    
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        pyproject_path = os.path.join(base_dir, 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            parent_dir = os.path.dirname(base_dir)
            pyproject_path = os.path.join(parent_dir, 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            warning("main", "找不到 pyproject.toml 文件，使用默认版本号")
            _cached_project_version = "1.0.0"
            return _cached_project_version
        
        try:
            import tomllib
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    data = tomli.load(f)
            except ImportError:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('version'):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        _cached_project_version = version
                        debug("main", f"从 pyproject.toml 读取到版本号: {version}")
                        return version
                _cached_project_version = "1.0.0"
                return _cached_project_version
        
        version = data.get('project', {}).get('version', '1.0.0')
        _cached_project_version = version
        debug("main", f"从 pyproject.toml 读取到版本号: {version}")
        return version
    
    except Exception as e:
        error("main", f"读取 pyproject.toml 失败: {e}", exc_info=True)
        _cached_project_version = "1.0.0"
        return _cached_project_version


from system_core import load_config, global_config, DEFAULT_CONFIG, WEEKDAY_MAPPING, save_config, should_work_today, LunarUtils

from business import run_tasks_once, cancel_shutdown, is_wifi_connected, connect_wifi, campus_login

# 导入线程池和任务管理
from infrastructure import run_full_task_chain, get_thread_pool_manager


class PeriodEditDialog(QDialog):
    """
    编辑时间段对话框
    
    功能说明：
        - 编辑或添加时间段
        - 包含名称、开始日期、结束日期
        - 验证日期逻辑
    """
    def __init__(self, parent=None, period=None):
        super().__init__(parent)
        self.setWindowTitle("编辑时间段" if period else "添加时间段")
        self.setFixedSize(400, 200)
        self.period = period if period else {"name": "", "start": "", "end": ""}
        self.result_period = None

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setText(self.period.get("name", ""))
        layout.addRow("时间段名称：", self.name_edit)

        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd")
        if self.period.get("start"):
            start_date = parse_date_str(self.period["start"])
            if start_date:
                self.start_edit.setDate(QDate(start_date.year, start_date.month, start_date.day))
        else:
            self.start_edit.setDate(QDate.currentDate())
        layout.addRow("开始日期：", self.start_edit)

        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd")
        if self.period.get("end"):
            end_date = parse_date_str(self.period["end"])
            if end_date:
                self.end_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))
        else:
            self.end_edit.setDate(QDate.currentDate())
        layout.addRow("结束日期：", self.end_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def save(self):
        """保存时间段"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入时间段名称")
            return

        start_date = self.start_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_edit.date().toString("yyyy-MM-dd")

        start = parse_date_str(start_date)
        end = parse_date_str(end_date)
        if start > end:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return

        self.result_period = {
            "name": name,
            "start": start_date,
            "end": end_date
        }
        self.accept()


class CompensatoryWorkdayWidget(QWidget):
    """
    调休上班日配置组件
    
    功能说明：
        - 管理调休上班日列表
        - 支持添加、删除、清空、恢复默认
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.compensatory_days = global_config.get("COMPENSATORY_WORKDAYS",
                                                   DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("调休上班日（强制工作日，优先级最高）：")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        self.day_list = QListWidget()
        self.day_list.addItems(self.compensatory_days)
        main_layout.addWidget(self.day_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加日期")
        add_btn.clicked.connect(self.add_day)
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self.del_day)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_days)
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(reset_btn)
        main_layout.addLayout(btn_layout)

        tip_label = QLabel("提示：调休上班日格式为 YYYY-MM-DD（如 2025-01-26），该日期强制执行业务逻辑")
        tip_label.setStyleSheet("color: #666666; font-size: 9px;")
        main_layout.addWidget(tip_label)
        main_layout.addStretch()

    def add_day(self):
        """添加调休上班日"""
        date_str, ok = QInputDialog.getText(self, "添加调休上班日", "请输入日期（格式：YYYY-MM-DD）：")
        if ok and date_str.strip():
            if parse_date_str(date_str.strip()):
                if date_str.strip() not in self.compensatory_days:
                    self.compensatory_days.append(date_str.strip())
                    self.day_list.addItem(date_str.strip())
                else:
                    QMessageBox.warning(self, "提示", "该日期已存在")
            else:
                QMessageBox.warning(self, "格式错误", "日期格式不正确，请输入如 2025-01-26 的格式")

    def del_day(self):
        """删除选中的调休上班日"""
        selected_items = self.day_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选中要删除的日期")
            return

        if QMessageBox.question(self, "确认", "是否确定删除选中的调休上班日？") == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                self.compensatory_days.remove(item.text())
                self.day_list.takeItem(self.day_list.row(item))

    def clear_days(self):
        """清空调休上班日"""
        if QMessageBox.question(self, "确认", "是否确定清空所有调休上班日？") == QMessageBox.StandardButton.Yes:
            self.compensatory_days.clear()
            self.day_list.clear()

    def reset_to_default(self):
        """恢复默认调休上班日"""
        if QMessageBox.question(self, "确认", "是否确定恢复默认的调休上班日？") == QMessageBox.StandardButton.Yes:
            self.compensatory_days = DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy()
            self.day_list.clear()
            self.day_list.addItems(self.compensatory_days)

    def save_days(self):
        """保存调休上班日到配置"""
        global_config["COMPENSATORY_WORKDAYS"] = self.compensatory_days
        return True


class DateRuleWidget(QWidget):
    """
    日期规则配置组件
    
    功能说明：
        - 自定义日期规则配置
        - 每周执行日设置
        - 自定义假期/工作日时间段
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.custom_rule_check = QCheckBox("启用自定义日期规则（优先生效）")
        self.custom_rule_check.setChecked(self.date_rules.get("ENABLE_CUSTOM_RULE", False))
        main_layout.addWidget(self.custom_rule_check)
        main_layout.addSpacing(15)

        week_frame = QFrame()
        week_layout = QVBoxLayout(week_frame)
        week_title = QLabel("每周执行日（勾选需要自动执行的星期）：")
        week_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        week_layout.addWidget(week_title)

        self.week_checks = {}
        week_grid = QGridLayout()
        for idx, (week_code, week_name) in enumerate(WEEKDAY_MAPPING.items()):
            check = QCheckBox(week_name)
            check.setChecked(week_code in self.date_rules.get("WEEKLY_EXECUTE_DAYS", []))
            self.week_checks[week_code] = check
            week_grid.addWidget(check, idx // 3, idx % 3)
        week_layout.addLayout(week_grid)
        main_layout.addWidget(week_frame)
        main_layout.addSpacing(15)

        holiday_frame = QFrame()
        holiday_layout = QVBoxLayout(holiday_frame)
        holiday_title = QLabel("自定义假期时间段（以下时间段强制不执行）：")
        holiday_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        holiday_layout.addWidget(holiday_title)

        self.holiday_list = QListWidget()
        self.load_period_list(self.holiday_list, self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []))
        holiday_layout.addWidget(self.holiday_list)

        holiday_btn_layout = QHBoxLayout()
        add_holiday_btn = QPushButton("添加时间段")
        add_holiday_btn.clicked.connect(lambda: self.add_period(self.holiday_list, "假期"))
        edit_holiday_btn = QPushButton("编辑选中")
        edit_holiday_btn.clicked.connect(lambda: self.edit_period(self.holiday_list, "假期"))
        del_holiday_btn = QPushButton("删除选中")
        del_holiday_btn.clicked.connect(lambda: self.del_period(self.holiday_list))
        clear_holiday_btn = QPushButton("清空")
        clear_holiday_btn.clicked.connect(lambda: self.clear_period(self.holiday_list))
        holiday_btn_layout.addWidget(add_holiday_btn)
        holiday_btn_layout.addWidget(edit_holiday_btn)
        holiday_btn_layout.addWidget(del_holiday_btn)
        holiday_btn_layout.addWidget(clear_holiday_btn)
        holiday_layout.addLayout(holiday_btn_layout)
        main_layout.addWidget(holiday_frame)
        main_layout.addSpacing(15)

        workday_frame = QFrame()
        workday_layout = QVBoxLayout(workday_frame)
        workday_title = QLabel("自定义工作日时间段（以下时间段强制执行）：")
        workday_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        workday_layout.addWidget(workday_title)

        self.workday_list = QListWidget()
        self.load_period_list(self.workday_list, self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []))
        workday_layout.addWidget(self.workday_list)

        workday_btn_layout = QHBoxLayout()
        add_workday_btn = QPushButton("添加时间段")
        add_workday_btn.clicked.connect(lambda: self.add_period(self.workday_list, "工作日"))
        edit_workday_btn = QPushButton("编辑选中")
        edit_workday_btn.clicked.connect(lambda: self.edit_period(self.workday_list, "工作日"))
        del_workday_btn = QPushButton("删除选中")
        del_workday_btn.clicked.connect(lambda: self.del_period(self.workday_list))
        clear_workday_btn = QPushButton("清空")
        clear_workday_btn.clicked.connect(lambda: self.clear_period(self.workday_list))
        workday_btn_layout.addWidget(add_workday_btn)
        workday_btn_layout.addWidget(edit_workday_btn)
        workday_btn_layout.addWidget(del_workday_btn)
        workday_btn_layout.addWidget(clear_workday_btn)
        workday_layout.addLayout(workday_btn_layout)
        main_layout.addWidget(workday_frame)

        tip_label = QLabel(
            "提示：时间段名称建议清晰（如「2025校运会」），日期选择后自动按格式保存，自定义规则启用后将覆盖默认节假日规则（调休上班日除外）")
        tip_label.setStyleSheet("color: #666666; font-size: 9px;")
        tip_label.setWordWrap(True)
        main_layout.addWidget(tip_label)
        main_layout.addStretch()

    def load_period_list(self, list_widget, periods):
        """加载时间段列表"""
        list_widget.clear()
        for period in periods:
            item = QListWidgetItem(format_period(period))
            item.setData(Qt.ItemDataRole.UserRole, period)
            list_widget.addItem(item)

    def add_period(self, list_widget, type_name):
        """添加时间段"""
        dialog = PeriodEditDialog(self)
        dialog.setWindowTitle(f"添加自定义{type_name}时间段")
        if dialog.exec():
            period = dialog.result_period
            item = QListWidgetItem(format_period(period))
            item.setData(Qt.ItemDataRole.UserRole, period)
            list_widget.addItem(item)

    def edit_period(self, list_widget, type_name):
        """编辑选中的时间段"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", f"请先选中要编辑的{type_name}时间段")
            return

        item = selected_items[0]
        period = item.data(Qt.ItemDataRole.UserRole)
        dialog = PeriodEditDialog(self, period)
        dialog.setWindowTitle(f"编辑自定义{type_name}时间段")
        if dialog.exec():
            new_period = dialog.result_period
            item.setText(format_period(new_period))
            item.setData(Qt.ItemDataRole.UserRole, new_period)

    def del_period(self, list_widget):
        """删除选中的时间段"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选中要删除的时间段")
            return

        if QMessageBox.question(self, "确认", "是否确定删除选中的时间段？") == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                list_widget.takeItem(list_widget.row(item))

    def clear_period(self, list_widget):
        """清空时间段"""
        if QMessageBox.question(self, "确认", "是否确定清空所有时间段？") == QMessageBox.StandardButton.Yes:
            list_widget.clear()

    def save_rules(self):
        """保存日期规则到配置"""
        self.date_rules["ENABLE_CUSTOM_RULE"] = self.custom_rule_check.isChecked()

        weekly_days = []
        for code, check in self.week_checks.items():
            if check.isChecked():
                weekly_days.append(code)
        self.date_rules["WEEKLY_EXECUTE_DAYS"] = weekly_days

        holiday_periods = []
        for i in range(self.holiday_list.count()):
            item = self.holiday_list.item(i)
            holiday_periods.append(item.data(Qt.ItemDataRole.UserRole))
        self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = holiday_periods

        workday_periods = []
        for i in range(self.workday_list.count()):
            item = self.workday_list.item(i)
            workday_periods.append(item.data(Qt.ItemDataRole.UserRole))
        self.date_rules["CUSTOM_WORKDAY_PERIODS"] = workday_periods
        
        return True


class BaseHolidayWidget(QWidget):
    """
    基础节假日配置组件
    
    功能说明：
        - 管理国务院官方节假日和高校假期
        - 支持添加、编辑、删除、恢复默认
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_holidays = global_config.get("HOLIDAY_PERIODS", DEFAULT_CONFIG["HOLIDAY_PERIODS"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("基础节假日时间段（国务院2025/2026官方安排+高校假期）：")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        self.holiday_list = QListWidget()
        self.load_period_list(self.holiday_list, self.base_holidays)
        main_layout.addWidget(self.holiday_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加节假日")
        add_btn.clicked.connect(lambda: self.add_period(self.holiday_list))
        edit_btn = QPushButton("编辑选中")
        edit_btn.clicked.connect(lambda: self.edit_period(self.holiday_list))
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(lambda: self.del_period(self.holiday_list))
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(reset_btn)
        main_layout.addLayout(btn_layout)

        tip_label = QLabel("提示：修改基础节假日后，仅在未启用自定义规则且非调休上班日时生效")
        tip_label.setStyleSheet("color: #666666; font-size: 9px;")
        main_layout.addWidget(tip_label)
        main_layout.addStretch()

    def load_period_list(self, list_widget, periods):
        """加载时间段列表"""
        list_widget.clear()
        for period in periods:
            item = QListWidgetItem(format_period(period))
            item.setData(Qt.ItemDataRole.UserRole, period)
            list_widget.addItem(item)

    def add_period(self, list_widget):
        """添加时间段"""
        dialog = PeriodEditDialog(self)
        dialog.setWindowTitle("添加基础节假日时间段")
        if dialog.exec():
            period = dialog.result_period
            item = QListWidgetItem(format_period(period))
            item.setData(Qt.ItemDataRole.UserRole, period)
            list_widget.addItem(item)
            self.base_holidays.append(period)

    def edit_period(self, list_widget):
        """编辑选中的时间段"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选中要编辑的节假日时间段")
            return

        item = selected_items[0]
        period = item.data(Qt.ItemDataRole.UserRole)
        dialog = PeriodEditDialog(self, period)
        dialog.setWindowTitle("编辑基础节假日时间段")
        if dialog.exec():
            new_period = dialog.result_period
            item.setText(format_period(new_period))
            item.setData(Qt.ItemDataRole.UserRole, new_period)
            idx = self.base_holidays.index(period)
            self.base_holidays[idx] = new_period

    def del_period(self, list_widget):
        """删除选中的时间段"""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选中要删除的时间段")
            return

        if QMessageBox.question(self, "确认", "是否确定删除选中的节假日时间段？") == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                period = item.data(Qt.ItemDataRole.UserRole)
                self.base_holidays.remove(period)
                list_widget.takeItem(list_widget.row(item))

    def reset_to_default(self):
        """恢复默认节假日"""
        if QMessageBox.question(self, "确认",
                                "是否确定恢复默认的节假日时间段（国务院2025/2026官方安排）？") == QMessageBox.StandardButton.Yes:
            self.base_holidays = DEFAULT_CONFIG["HOLIDAY_PERIODS"].copy()
            self.load_period_list(self.holiday_list, self.base_holidays)

    def save_holidays(self):
        """保存基础节假日到配置"""
        global_config["HOLIDAY_PERIODS"] = self.base_holidays
        return True


class ChangeMasterPasswordDialog(QDialog):
    """
    更改主密码对话框
    
    功能说明：
        - 验证旧密码
        - 设置新密码
        - 确认新密码
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更改主密码")
        self.setFixedSize(400, 250)
        
        main_layout = QVBoxLayout(self)
        
        title_label = QLabel("更改加密主密码")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)
        
        form_layout = QFormLayout()
        
        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("旧主密码：", self.old_password_edit)
        
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("新主密码：", self.new_password_edit)
        
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("确认新密码：", self.confirm_password_edit)
        
        main_layout.addLayout(form_layout)
        main_layout.addSpacing(20)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.change_password)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def change_password(self):
        """
        更改主密码
        """
        old_password = self.old_password_edit.text()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        
        if not old_password:
            QMessageBox.warning(self, "提示", "请输入旧主密码")
            return
        
        if not new_password:
            QMessageBox.warning(self, "提示", "请输入新主密码")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        
        from system_core import change_master_password
        success = change_master_password(old_password, new_password)
        
        if success:
            QMessageBox.information(self, "成功", "主密码更改成功，配置已重新加密")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "主密码更改失败，请检查旧密码是否正确")


class SettingsDialog(QDialog):
    """
    配置设置对话框
    
    功能说明：
        - WiFi配置
        - 校园网登录配置
        - 自动关机配置
        - 日期规则配置
        - 应用程序设置
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setMinimumSize(800, 600)
        
        from system_core import load_config
        load_config()
        
        main_layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        wifi_tab = QWidget()
        wifi_layout = QFormLayout(wifi_tab)
        
        self.wifi_name_edit = QLineEdit()
        self.wifi_name_edit.setText(global_config.get("WIFI_NAME", DEFAULT_CONFIG["WIFI_NAME"]))
        wifi_layout.addRow("WiFi名称：", self.wifi_name_edit)
        
        password_layout = QHBoxLayout()
        self.wifi_password_edit = QLineEdit()
        self.wifi_password_edit.setText(global_config.get("WIFI_PASSWORD", DEFAULT_CONFIG["WIFI_PASSWORD"]))
        self.wifi_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.wifi_password_edit)
        
        self.wifi_password_visible = QPushButton("显示")
        self.wifi_password_visible.setCheckable(True)
        self.wifi_password_visible.clicked.connect(lambda: self.toggle_password_visibility(self.wifi_password_edit, self.wifi_password_visible))
        password_layout.addWidget(self.wifi_password_visible)
        
        wifi_layout.addRow("WiFi密码：", password_layout)
        
        self.wifi_retry_edit = QLineEdit()
        self.wifi_retry_edit.setText(str(global_config.get("MAX_WIFI_RETRY", DEFAULT_CONFIG["MAX_WIFI_RETRY"])))
        wifi_layout.addRow("最大重试次数：", self.wifi_retry_edit)
        
        self.retry_interval_edit = QLineEdit()
        self.retry_interval_edit.setText(str(global_config.get("RETRY_INTERVAL", DEFAULT_CONFIG["RETRY_INTERVAL"])))
        wifi_layout.addRow("重试间隔(秒)：", self.retry_interval_edit)
        
        self.tab_widget.addTab(wifi_tab, "WiFi配置")
        
        login_tab = QWidget()
        login_layout = QFormLayout(login_tab)
        
        self.username_edit = QLineEdit()
        self.username_edit.setText(global_config.get("USERNAME", DEFAULT_CONFIG["USERNAME"]))
        login_layout.addRow("用户名：", self.username_edit)
        
        password_layout = QHBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setText(global_config.get("PASSWORD", DEFAULT_CONFIG["PASSWORD"]))
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.password_edit)
        
        self.password_visible = QPushButton("显示")
        self.password_visible.setCheckable(True)
        self.password_visible.clicked.connect(lambda: self.toggle_password_visibility(self.password_edit, self.password_visible))
        password_layout.addWidget(self.password_visible)
        
        login_layout.addRow("密码：", password_layout)
        
        self.isp_combo = QComboBox()
        self.isp_combo.addItems(["移动", "电信", "联通"])
        isp_mapping = {"cmcc": 0, "telecom": 1, "unicom": 2}
        self.isp_combo.setCurrentIndex(isp_mapping.get(global_config.get("ISP_TYPE", DEFAULT_CONFIG["ISP_TYPE"]), 1))
        login_layout.addRow("运营商类型：", self.isp_combo)
        
        self.wan_ip_edit = QLineEdit()
        self.wan_ip_edit.setText(global_config.get("WAN_IP", DEFAULT_CONFIG["WAN_IP"]))
        login_layout.addRow("WAN IP：", self.wan_ip_edit)
        
        self.tab_widget.addTab(login_tab, "校园网登录配置")
        
        shutdown_tab = QWidget()
        shutdown_layout = QFormLayout(shutdown_tab)
        
        self.shutdown_hour_edit = QLineEdit()
        self.shutdown_hour_edit.setText(str(global_config.get("SHUTDOWN_HOUR", DEFAULT_CONFIG["SHUTDOWN_HOUR"])))
        shutdown_layout.addRow("关机小时：", self.shutdown_hour_edit)
        
        self.shutdown_min_edit = QLineEdit()
        self.shutdown_min_edit.setText(str(global_config.get("SHUTDOWN_MIN", DEFAULT_CONFIG["SHUTDOWN_MIN"])))
        shutdown_layout.addRow("关机分钟：", self.shutdown_min_edit)
        
        self.tab_widget.addTab(shutdown_tab, "自动关机配置")
        
        self.date_rule_widget = DateRuleWidget(self)
        self.tab_widget.addTab(self.date_rule_widget, "自定义日期规则")
        
        self.compensatory_widget = CompensatoryWorkdayWidget(self)
        self.tab_widget.addTab(self.compensatory_widget, "调休上班日")
        
        self.base_holiday_widget = BaseHolidayWidget(self)
        self.tab_widget.addTab(self.base_holiday_widget, "基础节假日")
        
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)
        
        app_layout.addSpacing(10)

        autostart_label = QLabel("开机自启动设置：")
        app_layout.addWidget(autostart_label)
        
        autostart_disabled_label = QLabel("⚠️ 自启动功能暂时不可用（文件重构中）")
        autostart_disabled_label.setStyleSheet("color: #f39c12;")
        app_layout.addWidget(autostart_disabled_label)
        app_layout.addSpacing(20)
        
        security_label = QLabel("安全设置：")
        security_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        app_layout.addWidget(security_label)
        
        security_buttons = QHBoxLayout()
        self.change_password_btn = QPushButton("更改主密码")
        self.change_password_btn.clicked.connect(self.on_change_password)
        security_buttons.addWidget(self.change_password_btn)
        app_layout.addLayout(security_buttons)
        
        security_tip_label = QLabel("提示：主密码用于生成加密密钥，更改后会重新加密所有配置")
        security_tip_label.setStyleSheet("color: #666666; font-size: 9px;")
        security_tip_label.setWordWrap(True)
        app_layout.addWidget(security_tip_label)
        app_layout.addSpacing(20)
        
        calendar_label = QLabel("日历显示设置：")
        calendar_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        app_layout.addWidget(calendar_label)
        
        self.show_lunar_check = QCheckBox("显示农历日期")
        self.show_lunar_check.setChecked(global_config.get("SHOW_LUNAR_CALENDAR", True))
        app_layout.addWidget(self.show_lunar_check)
        
        lunar_format_label = QLabel("农历显示格式：")
        lunar_format_label.setStyleSheet("margin-top: 10px;")
        app_layout.addWidget(lunar_format_label)
        
        lunar_format_layout = QHBoxLayout()
        self.lunar_format_combo = QComboBox()
        self.lunar_format_combo.addItems(["简化格式（如：正月初一）", "完整格式（如：农历2025年正月初一）"])
        self.lunar_format_combo.setCurrentIndex(global_config.get("LUNAR_DISPLAY_FORMAT", 0))
        lunar_format_layout.addWidget(self.lunar_format_combo)
        lunar_format_layout.addStretch()
        app_layout.addLayout(lunar_format_layout)
        
        app_layout.addStretch()
        
        self.tab_widget.addTab(app_tab, "应用程序设置")
        
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        button_box.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)
        
        main_layout.addLayout(button_box)
        
    def save_config(self):
        """保存配置"""
        global_config["WIFI_NAME"] = self.wifi_name_edit.text()
        global_config["WIFI_PASSWORD"] = self.wifi_password_edit.text()
        
        try:
            global_config["MAX_WIFI_RETRY"] = int(self.wifi_retry_edit.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "最大重试次数请输入整数")
            return
        
        try:
            global_config["RETRY_INTERVAL"] = int(self.retry_interval_edit.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "重试间隔请输入整数")
            return
        
        global_config["USERNAME"] = self.username_edit.text()
        global_config["PASSWORD"] = self.password_edit.text()
        
        isp_mapping = {0: "cmcc", 1: "telecom", 2: "unicom"}
        global_config["ISP_TYPE"] = isp_mapping[self.isp_combo.currentIndex()]
        
        global_config["WAN_IP"] = self.wan_ip_edit.text()
        
        try:
            global_config["SHUTDOWN_HOUR"] = int(self.shutdown_hour_edit.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "关机小时请输入整数")
            return
        
        try:
            global_config["SHUTDOWN_MIN"] = int(self.shutdown_min_edit.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "关机分钟请输入整数")
            return
        
        self.date_rule_widget.save_rules()
        global_config["DATE_RULES"] = self.date_rule_widget.date_rules
        
        self.compensatory_widget.save_days()
        
        self.base_holiday_widget.save_holidays()
        
        global_config["SHOW_LUNAR_CALENDAR"] = self.show_lunar_check.isChecked()
        global_config["LUNAR_DISPLAY_FORMAT"] = self.lunar_format_combo.currentIndex()
        
        save_config()
        
        QMessageBox.information(self, "提示", "配置已保存")
        self.accept()
    
    def toggle_password_visibility(self, password_edit, button):
        """切换密码可见性
        
        Args:
            password_edit (QLineEdit): 密码输入框
            button (QPushButton): 显示/隐藏按钮
        """
        if button.isChecked():
            password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("隐藏")
        else:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("显示")

    def on_change_password(self):
        """
        打开更改主密码对话框
        """
        dialog = ChangeMasterPasswordDialog(self)
        dialog.exec()


class AboutDialog(QDialog):
    """
    关于我们对话框
    
    功能说明：
        - 显示程序标题、版本号、说明信息
        - 提供 GitHub 链接
        - 显示版权信息
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于我们")
        self.setMinimumSize(450, 380)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QLabel("校园网自动登录 + 定时关机")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(20)
        
        version = get_project_version()
        version_label = QLabel(f"版本：{version}")
        version_label.setFont(QFont("Microsoft YaHei", 13))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        layout.addSpacing(10)
        
        desc_label = QLabel("这是一个用于自动连接校园网并定时关机的工具")
        desc_label.setFont(QFont("Microsoft YaHei", 11))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        layout.addSpacing(15)
        
        github_label = QLabel('GitHub: <a href="https://github.com/taboo-hacker">https://github.com/taboo-hacker</a>')
        github_label.setFont(QFont("Microsoft YaHei", 11))
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)
        layout.addSpacing(30)
        
        copyright_label = QLabel("© 2026 校园网自动登录工具")
        copyright_label.setFont(QFont("Microsoft YaHei", 10))
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #666666;")
        layout.addWidget(copyright_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class CalendarDialog(QDialog):
    """
    任务日历对话框
    
    功能说明：
        - 显示任务执行计划日历
        - 标记需要执行任务的日期
        - 显示农历日期
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("日历 - 任务执行计划")
        self.setMinimumSize(600, 500)
        self._lunar_cache = {}
        self.init_ui()
        info("main", "日历对话框初始化完成")

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title = QLabel("任务执行计划日历")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addSpacing(15)

        self.calendar = QCalendarWidget()
        self.calendar.setFont(QFont("Microsoft YaHei", 10))
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.currentPageChanged.connect(self.on_month_changed)
        main_layout.addWidget(self.calendar)

        self.status_label = QLabel("选择日期查看状态")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("background-color: #f5f5f5; padding: 8px; border-radius: 5px;")
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(10)

        legend_layout = QHBoxLayout()
        legend_layout.addStretch()
        
        exec_legend = QWidget()
        exec_layout = QHBoxLayout(exec_legend)
        exec_color = QLabel()
        exec_color.setFixedSize(16, 16)
        exec_color.setStyleSheet("background-color: #4CAF50; border-radius: 2px;")
        exec_text = QLabel("需要执行任务")
        exec_text.setFont(QFont("Microsoft YaHei", 9))
        exec_layout.addWidget(exec_color)
        exec_layout.addWidget(exec_text)
        exec_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.addWidget(exec_legend)
        legend_layout.addSpacing(20)

        no_exec_legend = QWidget()
        no_exec_layout = QHBoxLayout(no_exec_legend)
        no_exec_color = QLabel()
        no_exec_color.setFixedSize(16, 16)
        no_exec_color.setStyleSheet("background-color: #F44336; border-radius: 2px;")
        no_exec_text = QLabel("不执行任务")
        no_exec_text.setFont(QFont("Microsoft YaHei", 9))
        no_exec_layout.addWidget(no_exec_color)
        no_exec_layout.addWidget(no_exec_text)
        no_exec_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.addWidget(no_exec_legend)
        legend_layout.addSpacing(20)

        compensatory_legend = QWidget()
        compensatory_layout = QHBoxLayout(compensatory_legend)
        compensatory_color = QLabel()
        compensatory_color.setFixedSize(16, 16)
        compensatory_color.setStyleSheet("background-color: #FFC107; border-radius: 2px;")
        compensatory_text = QLabel("调休上班")
        compensatory_text.setFont(QFont("Microsoft YaHei", 9))
        compensatory_layout.addWidget(compensatory_color)
        compensatory_layout.addWidget(compensatory_text)
        compensatory_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.addWidget(compensatory_legend)
        legend_layout.addStretch()

        main_layout.addLayout(legend_layout)

        self.calendar.selectionChanged.connect(self.on_date_selected)
        
        self.mark_execution_dates()
        
        self.on_date_selected()
        
    def on_month_changed(self, year, month):
        """
        月份变化时重新标记日期
        
        Args:
            year (int): 年份
            month (int): 月份
        """
        debug("main", f"日历月份切换到：{year}-{month}")
        self.mark_execution_dates()
        
    def on_date_selected(self):
        """
        当选择日期变化时更新状态显示
        """
        try:
            selected_date = self.calendar.selectedDate()
            date = datetime.date(selected_date.year(), selected_date.month(), selected_date.day())
            
            should_work, status = self.should_work_on_date(date)
            
            lunar_str = self._get_lunar_date(date)
            
            self.status_label.setText(f"{date} ({date.strftime('%A')}) {lunar_str} - {status}")
            debug("main", f"日历日期选中：{date}，农历：{lunar_str}，状态：{status}")
        except Exception as e:
            error("main", f"日期选择处理出错", exc_info=True)
            self.status_label.setText(f"日期处理出错：{str(e)}")
    
    def _get_lunar_date(self, date):
        """
        获取农历日期，使用缓存提高性能
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            str: 农历日期字符串
        """
        if not global_config.get("SHOW_LUNAR_CALENDAR", True):
            return ""
        
        if date in self._lunar_cache:
            return self._lunar_cache[date]
        
        try:
            dt = datetime.datetime.combine(date, datetime.time.min)
            lunar = ZhDate.from_datetime(dt)
            lunar_str = str(lunar)
            
            display_format = global_config.get("LUNAR_DISPLAY_FORMAT", 0)
            if display_format == 0 and lunar_str.startswith("农历"):
                lunar_str = lunar_str[2:]
            
            self._lunar_cache[date] = lunar_str
            return lunar_str
        except Exception as e:
            warning("main", f"农历转换失败：{e}")
            return "（农历转换失败）"

    def should_work_on_date(self, date):
        """
        判断指定日期是否需要执行任务
        
        Args:
            date (datetime.date): 要检查的日期
            
        Returns:
            tuple: (bool, str) - (是否执行任务, 状态描述)
        """
        try:
            result = should_work_today(date)
            debug("main", f"检查日期 {date} 是否需要执行任务: {'是' if result else '否'}")
            
            status = "不执行任务"
            if result:
                status = "需要执行任务"
            
            compensatory_days = [parse_date_str(d) for d in global_config.get("COMPENSATORY_WORKDAYS", []) if parse_date_str(d)]
            if date in compensatory_days:
                status = "调休上班日 - 需要执行任务"
            
            base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
            for period in base_holiday_periods:
                if is_date_in_period(date, period):
                    if not result:
                        status = f"节假日({period.get('name')}) - 不执行任务"
                    break
            
            date_rules = global_config.get("DATE_RULES", {})
            if date_rules.get("ENABLE_CUSTOM_RULE", False):
                custom_work_periods = date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
                for period in custom_work_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义工作日({period.get('name')}) - 需要执行任务"
                        break
                
                custom_holiday_periods = date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
                for period in custom_holiday_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义假期({period.get('name')}) - 不执行任务"
                        break
            
            return (result, status)
        except Exception as e:
            error("main", f"判断日期 {date} 是否需要执行任务时出错", exc_info=True)
            return (False, f"错误：{str(e)}")

    def mark_execution_dates(self):
        """
        标记日历中需要执行任务的日期
        """
        try:
            current_date = self.calendar.selectedDate()
            current_year = current_date.year()
            current_month = current_date.month()
            
            debug("main", f"开始标记 {current_year}年{current_month}月 的执行日期")
            
            first_day = datetime.date(current_year, current_month, 1)
            if current_month == 12:
                last_day = datetime.date(current_year, current_month, 31)
            else:
                last_day = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)
            
            current_date = first_day
            day_count = 0
            while current_date <= last_day:
                try:
                    should_work, status = self.should_work_on_date(current_date)
                    qt_date = QDate(current_date.year, current_date.month, current_date.day)
                    
                    if should_work:
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(76, 175, 80, 100))
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)
                    else:
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(244, 67, 54, 100))
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)
                    
                    day_count += 1
                except Exception as e:
                    warning("main", f"标记日期 {current_date} 时出错: {e}")
                
                current_date += datetime.timedelta(days=1)
            
            debug("main", f"完成标记 {current_year}年{current_month}月 的执行日期，共标记 {day_count} 天")
        except Exception as e:
            error("main", "标记执行日期时出错", exc_info=True)
            QMessageBox.warning(self, "错误", f"标记日历日期时出错: {str(e)}")

    def showEvent(self, event):
        """
        窗口显示时重新标记日期
        """
        super().showEvent(event)
        self.mark_execution_dates()


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
        
        self._init_basic_ui()
        

        init_logger(gui_log_widget=self.log_text, level=1)
        
        load_config()
        
        sys.stdout = StreamRedirector("stdout", 1)
        sys.stderr = StreamRedirector("stderr", 3)
        
        self._init_complete_ui()
        
        self._create_menu()
        
        self.task_manager = None
        
        QTimer.singleShot(200, self.run_on_start)
        
        info("main", "主窗口初始化完成")
    
    def _init_basic_ui(self):
        """
        初始化基础UI组件（用于日志系统）
        
        创建日志相关的UI组件，确保日志系统能在完整UI初始化前正常工作
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
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
        
        self._create_status_section(self.main_layout)
        
        self._create_button_section(self.main_layout)
        
        self._create_statusbar()
    
    def _create_status_section(self, parent_layout):
        """创建状态信息区域"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        status_layout = QVBoxLayout(status_frame)
        
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
        
        settings_menu.addSeparator()
        calendar_action = settings_menu.addAction("任务日历")
        calendar_action.triggered.connect(self.show_calendar)
        
        help_menu = menubar.addMenu("帮助")
        about_action = help_menu.addAction("关于我们")
        about_action.triggered.connect(self.show_about)
    
    def _log_write(self, text):
        """写入日志（线程安全）"""
        if text.strip():
            QTimer.singleShot(0, lambda: self._append_log(text))
    
    def _append_log(self, text):
        """追加日志到文本框"""
        if not self.log_text:
            return
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def _set_buttons_enabled(self, enabled):
        """设置按钮可用状态"""
        self.run_btn.setEnabled(enabled)
        self.test_wifi_btn.setEnabled(enabled)
        self.test_login_btn.setEnabled(enabled)
    
    def run_on_start(self):
        """启动时自动执行一次"""
        if hasattr(self, '_task_chain_started') and self._task_chain_started:
            return
        self._task_chain_started = True
        
        info("main", "程序启动，开始自动执行任务链")
        QTimer.singleShot(1000, self.start_task_chain)
    
    def start_task_chain(self):
        """启动任务链执行"""
        self._set_buttons_enabled(False)
        run_full_task_chain(parent=self)
    
    def on_worker_finished(self, success):
        """旧工作线程完成回调（保留兼容性）"""
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
            info("main", "用户手动触发：开始执行完整任务链")
            self.start_task_chain()
    
    def on_cancel_shutdown(self):
        """取消关机任务"""
        if QMessageBox.question(
            self, "确认", "是否取消已设置的关机任务？"
        ) == QMessageBox.StandardButton.Yes:
            cancel_shutdown()
            info("main", "用户手动取消了已设置的关机任务")
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
        
        self.statusBar.showMessage("正在测试WiFi...")
        info("main", f"开始测试WiFi连接：{wifi_name}")
        
        if is_wifi_connected(wifi_name):
            info("main", f"已成功连接到WiFi：{wifi_name}")
            self.statusBar.showMessage("WiFi已连接")
            QMessageBox.information(self, "测试结果", f"✅ 已成功连接到WiFi：{wifi_name}")
        else:
            info("main", "WiFi未连接，尝试建立连接...")
            if connect_wifi(wifi_name, global_config.get("WIFI_PASSWORD", "")):
                self.statusBar.showMessage("正在建立WiFi连接...")
                QTimer.singleShot(3000, lambda: self._check_wifi_result(wifi_name))
            else:
                error("main", "WiFi连接命令执行失败", exc_info=False)
                self.statusBar.showMessage("WiFi连接失败")
                QMessageBox.critical(self, "错误", "❌ WiFi连接命令执行失败，请检查WiFi名称和密码是否正确")
    
    def _check_wifi_result(self, wifi_name):
        """检查WiFi连接结果"""
        if is_wifi_connected(wifi_name):
            info("main", f"WiFi连接成功：{wifi_name}")
            self.statusBar.showMessage("WiFi连接成功")
            QMessageBox.information(self, "测试结果", f"✅ WiFi连接成功：{wifi_name}")
        else:
            error("main", f"WiFi连接失败：{wifi_name}", exc_info=False)
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
        info("main", "测试校园网登录")
        
        try:
            campus_login()
            self.statusBar.showMessage("登录测试完成")
            QMessageBox.information(self, "测试结果", "✅ 校园网登录测试完成，请查看日志了解详细结果")
        except Exception as e:
            self.statusBar.showMessage("登录测试失败")
            QMessageBox.critical(self, "错误", f"❌ 校园网登录测试失败：{str(e)}")
    
    def on_settings(self):
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
        dialog = CalendarDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """关闭窗口事件"""
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


def main():
    """
    主函数 - 程序入口点
    
    功能说明：
        - 创建或获取 QApplication 实例
        - 设置应用程序字体
        - 创建并显示主窗口
        - 启动应用程序事件循环
    
    参数：
        无
    
    返回值：
        int: 应用程序退出码
    
    异常：
        无
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()