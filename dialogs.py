import datetime
import os
import sys
from zhdate import ZhDate
from lunar_utils import LunarUtils
from PyQt5.QtWidgets import QDialog, QMainWindow, QWidget, QFormLayout, QLineEdit, QDateEdit, QHBoxLayout, QPushButton, QMessageBox, QVBoxLayout, QLabel, QListWidget, QComboBox, QInputDialog, QFrame, QCheckBox, QGridLayout, QListWidgetItem, QTabWidget, QDialogButtonBox, QCalendarWidget, QSplitter
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont, QTextCharFormat, QColor

# 导入新的日志系统
from logger import info, debug, warning, error, critical


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
    # 如果缓存存在，直接返回
    if _cached_project_version is not None:
        return _cached_project_version
    
    try:
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的程序
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        pyproject_path = os.path.join(base_dir, 'pyproject.toml')
        
        # 如果当前目录找不到，尝试向上查找
        if not os.path.exists(pyproject_path):
            parent_dir = os.path.dirname(base_dir)
            pyproject_path = os.path.join(parent_dir, 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            warning("dialogs", "找不到 pyproject.toml 文件，使用默认版本号")
            _cached_project_version = "1.0.0"
            return _cached_project_version
        
        # 使用 tomllib 或 tomli 解析
        try:
            import tomllib
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
        except ImportError:
            # Python 3.11 以下使用 tomli
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    data = tomli.load(f)
            except ImportError:
                # 如果都没有，手动解析
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('version'):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        _cached_project_version = version
                        debug("dialogs", f"从 pyproject.toml 读取到版本号: {version}")
                        return version
                _cached_project_version = "1.0.0"
                return _cached_project_version
        
        version = data.get('project', {}).get('version', '1.0.0')
        _cached_project_version = version
        debug("dialogs", f"从 pyproject.toml 读取到版本号: {version}")
        return version
    
    except Exception as e:
        error("dialogs", f"读取 pyproject.toml 失败: {e}", exc_info=True)
        _cached_project_version = "1.0.0"
        return _cached_project_version

from config import global_config, DEFAULT_CONFIG, WEEKDAY_MAPPING, save_config
from date_rules import should_work_today
from utils import parse_date_str, format_period, is_date_in_period


class PeriodEditDialog(QDialog):
    def __init__(self, parent=None, period=None):
        super().__init__(parent)
        self.setWindowTitle("编辑时间段" if period else "添加时间段")
        self.setFixedSize(400, 200)
        self.period = period if period else {"name": "", "start": "", "end": ""}
        self.result_period = None

        # 布局
        layout = QFormLayout(self)

        # 名称输入
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.period.get("name", ""))
        layout.addRow("时间段名称：", self.name_edit)

        # 开始日期
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

        # 结束日期
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

        # 按钮
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

        # 检查开始日期是否晚于结束日期
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.compensatory_days = global_config.get("COMPENSATORY_WORKDAYS",
                                                   DEFAULT_CONFIG["COMPENSATORY_WORKDAYS"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 标题
        title = QLabel("调休上班日（强制工作日，优先级最高）：")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        # 调休日列表
        self.day_list = QListWidget()
        self.day_list.addItems(self.compensatory_days)
        main_layout.addWidget(self.day_list)

        # 操作按钮
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

        # 提示
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. 自定义规则开关
        self.custom_rule_check = QCheckBox("启用自定义日期规则（优先生效）")
        self.custom_rule_check.setChecked(self.date_rules.get("ENABLE_CUSTOM_RULE", False))
        main_layout.addWidget(self.custom_rule_check)
        main_layout.addSpacing(15)

        # 2. 每周执行日设置
        week_frame = QFrame()
        week_layout = QVBoxLayout(week_frame)
        week_title = QLabel("每周执行日（勾选需要自动执行的星期）：")
        week_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        week_layout.addWidget(week_title)

        # 星期勾选框
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

        # 3. 自定义假期时间段设置
        holiday_frame = QFrame()
        holiday_layout = QVBoxLayout(holiday_frame)
        holiday_title = QLabel("自定义假期时间段（以下时间段强制不执行）：")
        holiday_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        holiday_layout.addWidget(holiday_title)

        # 假期列表
        self.holiday_list = QListWidget()
        self.load_period_list(self.holiday_list, self.date_rules.get("CUSTOM_HOLIDAY_PERIODS", []))
        holiday_layout.addWidget(self.holiday_list)

        # 假期操作按钮
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

        # 4. 自定义工作日时间段设置
        workday_frame = QFrame()
        workday_layout = QVBoxLayout(workday_frame)
        workday_title = QLabel("自定义工作日时间段（以下时间段强制执行）：")
        workday_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        workday_layout.addWidget(workday_title)

        # 工作日列表
        self.workday_list = QListWidget()
        self.load_period_list(self.workday_list, self.date_rules.get("CUSTOM_WORKDAY_PERIODS", []))
        workday_layout.addWidget(self.workday_list)

        # 工作日操作按钮
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

        # 提示信息
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
        # 1. 自定义规则开关
        self.date_rules["ENABLE_CUSTOM_RULE"] = self.custom_rule_check.isChecked()

        # 2. 每周执行日
        weekly_days = []
        for code, check in self.week_checks.items():
            if check.isChecked():
                weekly_days.append(code)
        self.date_rules["WEEKLY_EXECUTE_DAYS"] = weekly_days

        # 3. 自定义假期时间段
        holiday_periods = []
        for i in range(self.holiday_list.count()):
            item = self.holiday_list.item(i)
            holiday_periods.append(item.data(Qt.ItemDataRole.UserRole))
        self.date_rules["CUSTOM_HOLIDAY_PERIODS"] = holiday_periods

        # 4. 自定义工作日时间段
        workday_periods = []
        for i in range(self.workday_list.count()):
            item = self.workday_list.item(i)
            workday_periods.append(item.data(Qt.ItemDataRole.UserRole))
        self.date_rules["CUSTOM_WORKDAY_PERIODS"] = workday_periods
        
        return True


class BaseHolidayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_holidays = global_config.get("HOLIDAY_PERIODS", DEFAULT_CONFIG["HOLIDAY_PERIODS"].copy())
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 标题
        title = QLabel("基础节假日时间段（国务院2025/2026官方安排+高校假期）：")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        # 节假日列表
        self.holiday_list = QListWidget()
        self.load_period_list(self.holiday_list, self.base_holidays)
        main_layout.addWidget(self.holiday_list)

        # 操作按钮
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

        # 提示
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
            # 更新列表项
            item.setText(format_period(new_period))
            item.setData(Qt.ItemDataRole.UserRole, new_period)
            # 更新基础节假日列表
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更改主密码")
        self.setFixedSize(400, 250)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("更改加密主密码")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 旧密码输入
        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("旧主密码：", self.old_password_edit)
        
        # 新密码输入
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("新主密码：", self.new_password_edit)
        
        # 确认新密码输入
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("确认新密码：", self.confirm_password_edit)
        
        main_layout.addLayout(form_layout)
        main_layout.addSpacing(20)
        
        # 按钮
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
        
        # 验证输入
        if not old_password:
            QMessageBox.warning(self, "提示", "请输入旧主密码")
            return
        
        if not new_password:
            QMessageBox.warning(self, "提示", "请输入新主密码")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        
        # 调用更改主密码函数
        from config import change_master_password
        success = change_master_password(old_password, new_password)
        
        if success:
            QMessageBox.information(self, "成功", "主密码更改成功，配置已重新加密")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "主密码更改失败，请检查旧密码是否正确")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置设置")
        self.setMinimumSize(800, 600)
        
        # 重新加载配置，确保使用最新的配置
        from config import load_config
        load_config()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 1. WiFi配置标签页
        wifi_tab = QWidget()
        wifi_layout = QFormLayout(wifi_tab)
        
        self.wifi_name_edit = QLineEdit()
        self.wifi_name_edit.setText(global_config.get("WIFI_NAME", DEFAULT_CONFIG["WIFI_NAME"]))
        wifi_layout.addRow("WiFi名称：", self.wifi_name_edit)
        
        # WiFi密码输入框和显示/隐藏按钮
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
        
        # 2. 校园网登录配置标签页
        login_tab = QWidget()
        login_layout = QFormLayout(login_tab)
        
        self.username_edit = QLineEdit()
        self.username_edit.setText(global_config.get("USERNAME", DEFAULT_CONFIG["USERNAME"]))
        login_layout.addRow("用户名：", self.username_edit)
        
        # 校园网密码输入框和显示/隐藏按钮
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
        
        # 3. 自动关机配置标签页
        shutdown_tab = QWidget()
        shutdown_layout = QFormLayout(shutdown_tab)
        
        self.shutdown_hour_edit = QLineEdit()
        self.shutdown_hour_edit.setText(str(global_config.get("SHUTDOWN_HOUR", DEFAULT_CONFIG["SHUTDOWN_HOUR"])))
        shutdown_layout.addRow("关机小时：", self.shutdown_hour_edit)
        
        self.shutdown_min_edit = QLineEdit()
        self.shutdown_min_edit.setText(str(global_config.get("SHUTDOWN_MIN", DEFAULT_CONFIG["SHUTDOWN_MIN"])))
        shutdown_layout.addRow("关机分钟：", self.shutdown_min_edit)
        
        self.tab_widget.addTab(shutdown_tab, "自动关机配置")
        
        # 4. 日期规则配置标签页
        self.date_rule_widget = DateRuleWidget(self)
        self.tab_widget.addTab(self.date_rule_widget, "自定义日期规则")
        
        # 5. 调休上班日配置标签页
        self.compensatory_widget = CompensatoryWorkdayWidget(self)
        self.tab_widget.addTab(self.compensatory_widget, "调休上班日")
        
        # 6. 基础节假日配置标签页
        self.base_holiday_widget = BaseHolidayWidget(self)
        self.tab_widget.addTab(self.base_holiday_widget, "基础节假日")
        
        # 应用程序设置标签页
        app_tab = QWidget()
        app_layout = QVBoxLayout(app_tab)
        
        app_layout.addSpacing(10)

        # 自启动设置 - 使用动态按钮根据当前状态切换
        autostart_label = QLabel("开机自启动设置：")
        app_layout.addWidget(autostart_label)

        autostart_buttons = QHBoxLayout()
        self.autostart_btn = QPushButton()
        self.update_autostart_button()  # 根据当前状态更新按钮文本
        self.autostart_btn.clicked.connect(self.on_toggle_autostart)
        autostart_buttons.addWidget(self.autostart_btn)
        app_layout.addLayout(autostart_buttons)

        # 显示当前状态
        self.autostart_status_label = QLabel()
        self.update_autostart_status()
        app_layout.addWidget(self.autostart_status_label)
        app_layout.addSpacing(20)
        
        # 安全设置
        security_label = QLabel("安全设置：")
        security_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        app_layout.addWidget(security_label)
        
        security_buttons = QHBoxLayout()
        self.change_password_btn = QPushButton("更改主密码")
        self.change_password_btn.clicked.connect(self.on_change_password)
        security_buttons.addWidget(self.change_password_btn)
        app_layout.addLayout(security_buttons)
        
        # 提示信息
        security_tip_label = QLabel("提示：主密码用于生成加密密钥，更改后会重新加密所有配置")
        security_tip_label.setStyleSheet("color: #666666; font-size: 9px;")
        security_tip_label.setWordWrap(True)
        app_layout.addWidget(security_tip_label)
        app_layout.addSpacing(20)
        
        # 日历显示设置
        calendar_label = QLabel("日历显示设置：")
        calendar_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        app_layout.addWidget(calendar_label)
        
        # 显示农历日期复选框
        self.show_lunar_check = QCheckBox("显示农历日期")
        self.show_lunar_check.setChecked(global_config.get("SHOW_LUNAR_CALENDAR", True))
        app_layout.addWidget(self.show_lunar_check)
        
        # 农历显示格式
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
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_config)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
    def save_config(self):
        """保存配置"""
        # 1. WiFi配置
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
        
        # 2. 校园网登录配置
        global_config["USERNAME"] = self.username_edit.text()
        global_config["PASSWORD"] = self.password_edit.text()
        
        isp_mapping = {0: "cmcc", 1: "telecom", 2: "unicom"}
        global_config["ISP_TYPE"] = isp_mapping[self.isp_combo.currentIndex()]
        
        global_config["WAN_IP"] = self.wan_ip_edit.text()
        
        # 3. 自动关机配置
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
        
        # 4. 日期规则配置
        self.date_rule_widget.save_rules()
        global_config["DATE_RULES"] = self.date_rule_widget.date_rules
        
        # 5. 调休上班日配置
        self.compensatory_widget.save_days()
        
        # 6. 基础节假日配置
        self.base_holiday_widget.save_holidays()
        
        # 7. 日历显示设置
        global_config["SHOW_LUNAR_CALENDAR"] = self.show_lunar_check.isChecked()
        global_config["LUNAR_DISPLAY_FORMAT"] = self.lunar_format_combo.currentIndex()
        
        # 保存配置到文件
        save_config()
        
        QMessageBox.information(self, "提示", "配置已保存")
        self.accept()
    
    def update_autostart_button(self):
        """根据当前自启动状态更新按钮文本"""
        from qzct_login import check_autostart
        is_enabled = check_autostart()
        if is_enabled:
            self.autostart_btn.setText("关闭自启动")
        else:
            self.autostart_btn.setText("开启自启动")

    def update_autostart_status(self):
        """更新自启动状态显示"""
        from qzct_login import check_autostart
        is_enabled = check_autostart()
        if is_enabled:
            self.autostart_status_label.setText("✅ 已启用自启动（系统启动时自动运行）")
            self.autostart_status_label.setStyleSheet("color: green;")
        else:
            self.autostart_status_label.setText("❌ 未启用自启动")
            self.autostart_status_label.setStyleSheet("color: red;")
        global_config["AUTOSTART"] = is_enabled
        self.update_autostart_button()  # 同时更新按钮文本

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

    def on_toggle_autostart(self):
        """
        切换自启动状态
        """
        from qzct_login import check_autostart, set_autostart
        current_status = check_autostart()
        try:
            success = set_autostart(enable=not current_status)
            if success:
                # 仅当操作成功且不是通过管理员权限重新运行时显示消息
                import sys
                if "--set-autostart" not in sys.argv:
                    # 重新检查实际状态，确保UI与系统状态一致
                    new_status = check_autostart()
                    # 更新UI状态
                    self.update_autostart_status()
                    # 显示消息
                    msg = "成功开启开机自启动" if new_status else "已关闭开机自启动"
                    QMessageBox.information(self, "提示", msg)
            else:
                # 权限不足时，set_autostart会自动请求管理员权限重新运行，这里不需要额外处理
                pass
        except Exception as e:
            QMessageBox.critical(self, "错误", f"切换自启动状态失败：{str(e)}")

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
        
        # 标题
        title_label = QLabel("校园网自动登录 + 定时关机")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(20)
        
        # 版本 - 从 pyproject.toml 读取
        version = get_project_version()
        version_label = QLabel(f"版本：{version}")
        version_label.setFont(QFont("Microsoft YaHei", 13))
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        layout.addSpacing(10)
        
        # 说明
        desc_label = QLabel("这是一个用于自动连接校园网并定时关机的工具")
        desc_label.setFont(QFont("Microsoft YaHei", 11))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        layout.addSpacing(15)
        
        # GitHub链接
        github_label = QLabel('GitHub: <a href="https://github.com/taboo-hacker">https://github.com/taboo-hacker</a>')
        github_label.setFont(QFont("Microsoft YaHei", 11))
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)
        layout.addSpacing(30)
        
        # 版权信息
        copyright_label = QLabel("© 2026 校园网自动登录工具")
        copyright_label.setFont(QFont("Microsoft YaHei", 10))
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet("color: #666666;")
        layout.addWidget(copyright_label)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


class CalendarDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("日历 - 任务执行计划")
        self.setMinimumSize(600, 500)
        # 添加农历日期缓存，提高性能
        self._lunar_cache = {}
        self.init_ui()
        info("dialogs", "日历对话框初始化完成")

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 标题
        title = QLabel("任务执行计划日历")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        main_layout.addSpacing(15)

        # 日历控件
        self.calendar = QCalendarWidget()
        self.calendar.setFont(QFont("Microsoft YaHei", 10))
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        # 连接月份变化信号，只在月份变化时重新标记日期
        self.calendar.currentPageChanged.connect(self.on_month_changed)
        main_layout.addWidget(self.calendar)

        # 状态信息
        self.status_label = QLabel("选择日期查看状态")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("background-color: #f5f5f5; padding: 8px; border-radius: 5px;")
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(10)

        # 图例说明
        legend_layout = QHBoxLayout()
        legend_layout.addStretch()
        
        # 执行任务图例
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

        # 不执行任务图例
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

        # 调休上班图例
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

        # 连接信号
        self.calendar.selectionChanged.connect(self.on_date_selected)
        
        # 初始标记当前月份日期
        self.mark_execution_dates()
        
        # 显示当前日期状态
        self.on_date_selected()
        
    def on_month_changed(self, year, month):
        """
        月份变化时重新标记日期
        
        Args:
            year (int): 年份
            month (int): 月份
        """
        debug("dialogs", f"日历月份切换到：{year}-{month}")
        self.mark_execution_dates()
        
    def on_date_selected(self):
        """
        当选择日期变化时更新状态显示
        """
        try:
            selected_date = self.calendar.selectedDate()
            date = datetime.date(selected_date.year(), selected_date.month(), selected_date.day())
            
            should_work, status = self.should_work_on_date(date)
            
            # 添加农历日期显示，使用缓存提高性能
            lunar_str = self._get_lunar_date(date)
            
            self.status_label.setText(f"{date} ({date.strftime('%A')}) {lunar_str} - {status}")
            debug("dialogs", f"日历日期选中：{date}，农历：{lunar_str}，状态：{status}")
        except Exception as e:
            error("dialogs", f"日期选择处理出错", exc_info=True)
            self.status_label.setText(f"日期处理出错：{str(e)}")
    
    def _get_lunar_date(self, date):
        """
        获取农历日期，使用缓存提高性能
        
        Args:
            date (datetime.date): 公历日期
            
        Returns:
            str: 农历日期字符串
        """
        from config import global_config
        
        # 检查是否启用农历显示
        if not global_config.get("SHOW_LUNAR_CALENDAR", True):
            return ""
        
        # 检查缓存
        if date in self._lunar_cache:
            return self._lunar_cache[date]
        
        try:
            dt = datetime.datetime.combine(date, datetime.time.min)
            lunar = ZhDate.from_datetime(dt)
            lunar_str = str(lunar)
            
            # 根据配置选择显示格式
            display_format = global_config.get("LUNAR_DISPLAY_FORMAT", 0)
            if display_format == 0 and lunar_str.startswith("农历"):
                # 简化格式：移除"农历"前缀
                lunar_str = lunar_str[2:]
            
            # 缓存结果
            self._lunar_cache[date] = lunar_str
            return lunar_str
        except Exception as e:
            warning("dialogs", f"农历转换失败：{e}")
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
            from date_rules import should_work_today
            from config import global_config
            from utils import parse_date_str, is_date_in_period
            
            # 直接调用带参数的should_work_today函数
            result = should_work_today(date)
            debug("dialogs", f"检查日期 {date} 是否需要执行任务: {'是' if result else '否'}")
            
            status = "不执行任务"
            if result:
                status = "需要执行任务"
            
            # 检查是否为调休上班日
            compensatory_days = [parse_date_str(d) for d in global_config.get("COMPENSATORY_WORKDAYS", []) if parse_date_str(d)]
            if date in compensatory_days:
                status = "调休上班日 - 需要执行任务"
            
            # 检查是否在节假日
            base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
            for period in base_holiday_periods:
                if is_date_in_period(date, period):
                    if not result:
                        status = f"节假日({period.get('name')}) - 不执行任务"
                    break
            
            # 检查自定义规则
            date_rules = global_config.get("DATE_RULES", {})
            if date_rules.get("ENABLE_CUSTOM_RULE", False):
                # 自定义工作日
                custom_work_periods = date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
                for period in custom_work_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义工作日({period.get('name')}) - 需要执行任务"
                        break
                
                # 自定义假期
                custom_holiday_periods = date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
                for period in custom_holiday_periods:
                    if is_date_in_period(date, period):
                        status = f"自定义假期({period.get('name')}) - 不执行任务"
                        break
            
            return (result, status)
        except Exception as e:
            error("dialogs", f"判断日期 {date} 是否需要执行任务时出错", exc_info=True)
            return (False, f"错误：{str(e)}")

    def mark_execution_dates(self):
        """
        标记日历中需要执行任务的日期
        """
        try:
            import datetime
            
            # 获取当前显示的月份
            current_date = self.calendar.selectedDate()
            current_year = current_date.year()
            current_month = current_date.month()
            
            debug("dialogs", f"开始标记 {current_year}年{current_month}月 的执行日期")
            
            # 计算当前月份的第一天和最后一天
            first_day = datetime.date(current_year, current_month, 1)
            if current_month == 12:
                last_day = datetime.date(current_year, current_month, 31)
            else:
                last_day = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)
            
            # 检查并标记当前月份的所有日期
            current_date = first_day
            day_count = 0
            while current_date <= last_day:
                try:
                    should_work, status = self.should_work_on_date(current_date)
                    qt_date = QDate(current_date.year, current_date.month, current_date.day)
                    
                    if should_work:
                        # 绿色标记 - 需要执行任务
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(76, 175, 80, 100))  # 半透明绿色
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)
                    else:
                        # 红色标记 - 不需要执行任务
                        self.calendar.setDateTextFormat(qt_date, QTextCharFormat())
                        fmt = QTextCharFormat()
                        fmt.setBackground(QColor(244, 67, 54, 100))  # 半透明红色
                        fmt.setForeground(QColor(0, 0, 0))
                        self.calendar.setDateTextFormat(qt_date, fmt)
                    
                    day_count += 1
                except Exception as e:
                    warning("dialogs", f"标记日期 {current_date} 时出错: {e}")
                
                current_date += datetime.timedelta(days=1)
            
            debug("dialogs", f"完成标记 {current_year}年{current_month}月 的执行日期，共标记 {day_count} 天")
        except Exception as e:
            error("dialogs", "标记执行日期时出错", exc_info=True)
            QMessageBox.warning(self, "错误", f"标记日历日期时出错: {str(e)}")

    def showEvent(self, event):
        """
        窗口显示时重新标记日期
        """
        super().showEvent(event)
        self.mark_execution_dates()
