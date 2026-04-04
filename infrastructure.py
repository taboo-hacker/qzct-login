import logging
import sys
import os
import datetime
import traceback
from PyQt5.QtCore import QTimer, QThreadPool, QRunnable, pyqtSignal, QObject


# ==========================================
# 工具函数模块
# ==========================================
def parse_date_str(date_str: str):
    """
    解析日期字符串为 date 对象
    
    将 "YYYY-MM-DD" 格式的字符串转换为 Python datetime.date 对象。
    
    Args:
        date_str (str): 日期字符串，格式为 "YYYY-MM-DD"
                        例如："2025-01-26"、"2026-02-14"
    
    Returns:
        datetime.date: 解析后的日期对象
        None: 如果解析失败（格式错误）
    
    使用示例：
        date = parse_date_str("2025-01-26")
        if date:
            print(date.year, date.month, date.day)
    
    错误处理：
        如果日期格式不正确，返回 None 而不抛出异常
    """
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


def is_date_in_period(check_date: datetime.date, period: dict) -> bool:
    """
    判断日期是否在指定的时间段内
    
    检查给定的日期是否在时间段 [start, end] 范围内。
    
    Args:
        check_date (datetime.date): 要检查的日期
        period (dict): 时间段字典，包含以下键：
            - start (str): 开始日期，"YYYY-MM-DD" 格式
            - end (str): 结束日期，"YYYY-MM-DD" 格式
            - name (str, optional): 时间段名称
    
    Returns:
        bool: True表示日期在时间段内，False表示不在
    
    使用示例：
        today = datetime.date.today()
        period = {"name": "寒假", "start": "2025-01-10", "end": "2025-02-28"}
        if is_date_in_period(today, period):
            print("今天在寒假期间")
    
    边界处理：
        开始日期和结束日期都包含在内（闭区间）
        即：start <= check_date <= end
    """
    start_date = parse_date_str(period.get("start"))
    end_date = parse_date_str(period.get("end"))
    if not start_date or not end_date:
        return False
    return start_date <= check_date <= end_date


def format_period(period: dict) -> str:
    """
    格式化时间段为可读字符串
    
    将时间段字典转换为易读的显示格式。
    
    Args:
        period (dict): 时间段字典，包含以下键：
            - name (str): 时间段名称
            - start (str): 开始日期
            - end (str): 结束日期
    
    Returns:
        str: 格式化后的字符串
             格式："名称（YYYY-MM-DD ~ YYYY-MM-DD）"
    
    使用示例：
        period = {"name": "春节", "start": "2025-01-28", "end": "2025-02-04"}
        print(format_period(period))
        # 输出：春节（2025-01-28 ~ 2025-02-04）
    """
    return f"{period.get('name', '未命名')}（{period.get('start')} ~ {period.get('end')}）"


# ==========================================
# 日志系统模块
# ==========================================
_global_logger_instance = None


class GUIHandler(logging.Handler):
    """
    自定义日志处理器，将标准logging日志转发到GUI日志窗口
    """
    def emit(self, record):
        """
        处理日志记录
        
        Args:
            record (logging.LogRecord): 日志记录对象
        """
        global _global_logger_instance
        if _global_logger_instance:
            logger_name = getattr(record, 'logger_name', record.name)
            
            if record.levelno == logging.DEBUG:
                level = 0
            elif record.levelno == logging.INFO:
                level = 1
            elif record.levelno == logging.WARNING:
                level = 2
            elif record.levelno == logging.ERROR:
                level = 3
            elif record.levelno == logging.CRITICAL:
                level = 4
            else:
                level = 1
            
            QTimer.singleShot(0, lambda: _global_logger_instance.log(
                logger_name, level, record.getMessage(), exc_info=record.exc_info, from_handler=True
            ))


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d] [%(logger_name)s] [%(levelname)s] %(message)s',
    datefmt='[%Y-%m-%d %H:%M:%S'
)

LOG_LEVEL_MAP = {
    0: logging.DEBUG,
    1: logging.INFO,
    2: logging.WARNING,
    3: logging.ERROR,
    4: logging.CRITICAL
}


class Logger:
    """
    标准日志系统包装类
    
    封装Python标准库logging，提供与原有接口兼容的日志记录功能。
    支持同时输出到GUI日志窗口和日志文件。
    
    功能特点：
        - 基于Python标准库logging
        - 支持5种日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
        - 时间戳精确到毫秒
        - 统一的日志格式：[时间戳] [模块名] [日志级别] 消息内容
        - 支持记录详细的错误堆栈信息
        - 支持同时输出到GUI日志窗口和文件
        - 线程安全，使用QTimer确保在主线程更新UI
    """
    
    def __init__(self, gui_log_widget=None, log_file_path=None, level=1,
                 max_log_size=10*1024*1024, backup_count=5):
        """
        初始化日志系统
        
        Args:
            gui_log_widget (QTextEdit, optional): GUI日志文本框
            log_file_path (str, optional): 日志文件路径
            level (int): 日志级别阈值，低于该级别的日志不会被记录
            max_log_size (int, optional): 最大日志文件大小（字节），默认10MB
            backup_count (int, optional): 保留的备份日志数量，默认5个
        """
        self.gui_log_widget = gui_log_widget
        self.log_file_path = log_file_path
        self.level = level
        self.max_log_size = max_log_size
        self.backup_count = backup_count
        
        self.log_buffer = []
        self.buffer_size = 10
        self.flush_interval = 500
        self.flush_timer = None
        
        global _global_logger_instance
        _global_logger_instance = self
        
        if gui_log_widget:
            try:
                self.flush_timer = QTimer()
                self.flush_timer.timeout.connect(self._flush_log_buffer)
                self.flush_timer.start(self.flush_interval)
            except ImportError:
                self.buffer_size = 1
        else:
            self.buffer_size = 1
        
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVEL_MAP.get(level, logging.INFO))
        
        root_logger.handlers.clear()
        
        if gui_log_widget:
            gui_handler = GUIHandler()
            root_logger.addHandler(gui_handler)
        
        if log_file_path:
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except Exception:
                    pass
            
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_log_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] %(message)s',
                datefmt='[%Y-%m-%d %H:%M:%S'
            ))
            
            root_logger.addHandler(file_handler)
        
        if not gui_log_widget:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d] [%(logger_name)s] [%(levelname)s] %(message)s',
                datefmt='[%Y-%m-%d %H:%M:%S'
            ))
            root_logger.addHandler(stream_handler)
        
        root_logger.info("日志系统初始化完成", extra={"logger_name": "infrastructure"})
    
    def _flush_log_buffer(self):
        """
        刷新日志缓存，将缓存中的日志批量写入GUI
        
        批量处理日志更新，减少UI刷新频率，提高程序响应速度。
        """
        if not self.gui_log_widget or not self.log_buffer:
            return
        
        combined_log = "".join(self.log_buffer)
        self.log_buffer.clear()
        
        QTimer.singleShot(0, lambda: self._append_to_gui(combined_log))
    
    def _append_to_gui(self, log_message):
        """
        将日志追加到GUI日志窗口
        
        Args:
            log_message (str): 日志消息
        """
        if self.gui_log_widget:
            cursor = self.gui_log_widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(log_message)
            self.gui_log_widget.setTextCursor(cursor)
            self.gui_log_widget.ensureCursorVisible()
    
    def log(self, module_name, level, message, exc_info=None, from_handler=False):
        """
        记录日志
        
        Args:
            module_name (str): 模块名称
            level (int): 日志级别
            message (str): 日志消息内容
            exc_info (bool, optional): 是否记录异常信息
            from_handler (bool): 是否来自GUIHandler，用于防止递归调用
        """
        if level < self.level:
            return
        
        std_level = LOG_LEVEL_MAP.get(level, logging.INFO)
        
        if not from_handler:
            root_logger = logging.getLogger()
            
            extra = {"logger_name": module_name}
            if std_level == logging.DEBUG:
                root_logger.debug(message, exc_info=exc_info, extra=extra)
            elif std_level == logging.INFO:
                root_logger.info(message, exc_info=exc_info, extra=extra)
            elif std_level == logging.WARNING:
                root_logger.warning(message, exc_info=exc_info, extra=extra)
            elif std_level == logging.ERROR:
                root_logger.error(message, exc_info=exc_info, extra=extra)
            elif std_level == logging.CRITICAL:
                root_logger.critical(message, exc_info=exc_info, extra=extra)
        
        if self.gui_log_widget:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level_name = logging.getLevelName(std_level)
            log_message = f"[{timestamp}] [{module_name}] [{level_name}] {message}\n"
            
            if exc_info and level >= 3:
                try:
                    stack_trace = traceback.format_exc()
                    if stack_trace:
                        log_message += f"{stack_trace}\n"
                except Exception:
                    pass
            
            self.log_buffer.append(log_message)
            
            if len(self.log_buffer) >= self.buffer_size:
                self._flush_log_buffer()
    
    def debug(self, module_name, message, exc_info=False):
        """记录DEBUG级别日志"""
        self.log(module_name, 0, message, exc_info)
    
    def info(self, module_name, message, exc_info=False):
        """记录INFO级别日志"""
        self.log(module_name, 1, message, exc_info)
    
    def warning(self, module_name, message, exc_info=False):
        """记录WARNING级别日志"""
        self.log(module_name, 2, message, exc_info)
    
    def error(self, module_name, message, exc_info=False):
        """记录ERROR级别日志"""
        self.log(module_name, 3, message, exc_info)
    
    def critical(self, module_name, message, exc_info=False):
        """记录CRITICAL级别日志"""
        self.log(module_name, 4, message, exc_info)


logger = None


def init_logger(gui_log_widget=None, log_file_path=None, level=1):
    """
    初始化全局日志对象
    
    Args:
        gui_log_widget (QTextEdit, optional): GUI日志文本框
        log_file_path (str, optional): 日志文件路径
        level (int): 日志级别阈值
    """
    global logger
    logger = Logger(gui_log_widget=gui_log_widget, log_file_path=log_file_path, level=level)
    return logger


def debug(module_name, message, exc_info=False):
    """
    便捷的DEBUG日志记录函数
    """
    if logger:
        logger.debug(module_name, message, exc_info)


def info(module_name, message, exc_info=False):
    """
    便捷的INFO日志记录函数
    """
    if logger:
        logger.info(module_name, message, exc_info)


def warning(module_name, message, exc_info=False):
    """
    便捷的WARNING日志记录函数
    """
    if logger:
        logger.warning(module_name, message, exc_info)


def error(module_name, message, exc_info=True):
    """
    便捷的ERROR日志记录函数
    """
    if logger:
        logger.error(module_name, message, exc_info)


def critical(module_name, message, exc_info=True):
    """
    便捷的CRITICAL日志记录函数
    """
    if logger:
        logger.critical(module_name, message, exc_info)


class StreamRedirector:
    """
    输出流重定向器
    
    将Python的标准输出和标准错误重定向到日志系统
    """
    
    def __init__(self, module_name="stdout", level=1):
        """
        初始化输出流重定向器
        
        Args:
            module_name (str): 模块名称
            level (int): 日志级别
        """
        self.module_name = module_name
        self.level = level
    
    def write(self, text):
        """
        写入文本到日志系统
        
        Args:
            text (str): 要写入的文本
        """
        if text.strip():
            if logger:
                logger.log(self.module_name, self.level, text.strip())
    
    def flush(self):
        """
        刷新输出缓冲区（空实现，保持兼容）"""
        pass


# ==========================================
# 线程池管理模块
# ==========================================
class TaskSignals(QObject):
    """
    任务信号类
    
    用于线程间通信，将任务执行状态、结果和日志信息
    发送回主线程处理。
    
    信号说明：
        - status: 任务状态更新信号
        - log: 日志消息信号
        - finished: 任务完成信号
        - error: 任务出错信号
    """
    status = pyqtSignal(str)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, object)
    error = pyqtSignal(str, str)


class BaseTask(QRunnable):
    """
    基础任务类
    
    所有异步任务的基类，封装了任务执行的基本逻辑和信号机制。
    
    属性：
        signals: 任务信号对象
        task_name: 任务名称
        priority: 任务优先级
    """
    
    def __init__(self, task_name="Unknown", priority=0):
        """
        初始化任务
        
        Args:
            task_name (str): 任务名称
            priority (int): 任务优先级
        """
        super().__init__()
        self.signals = TaskSignals()
        self.task_name = task_name
        self.priority = priority
        self.setAutoDelete(True)
    
    def run(self):
        """
        任务执行入口
        
        封装了任务执行的异常处理，确保所有异常都能被捕获并发送信号。
        """
        try:
            from infrastructure import debug
            debug("infrastructure", f"开始执行任务：{self.task_name}")
            self.execute()
        except Exception as e:
            from infrastructure import error
            error("infrastructure", f"任务执行出错：{self.task_name}", exc_info=True)
            self.signals.error.emit(self.task_name, str(e))
            self.signals.finished.emit(False, None)
    
    def execute(self):
        """
        任务执行逻辑
        
        子类需要重写此方法，实现具体的任务逻辑。
        """
        raise NotImplementedError("子类必须实现execute方法")


class ThreadPoolManager:
    """
    线程池管理器
    
    管理全局线程池，提供任务提交和管理功能。
    
    单例模式设计，确保整个应用只有一个线程池实例。
    """
    _instance = None
    
    def __new__(cls):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_thread_pool()
        return cls._instance
    
    def _init_thread_pool(self):
        """
        初始化线程池
        
        配置线程池参数，包括线程数量、优先级等。
        根据CPU核心数动态设置线程池大小，提高任务执行效率。
        """
        self.thread_pool = QThreadPool()
        cpu_count = os.cpu_count() or 4
        max_threads = min(cpu_count * 4, 16)
        self.thread_pool.setMaxThreadCount(max_threads)
        self.thread_pool.setStackSize(1024 * 1024)
        
        info("infrastructure", f"线程池初始化完成，最大线程数：{self.thread_pool.maxThreadCount()}")
    
    def submit_task(self, task):
        """
        提交任务到线程池执行
        
        Args:
            task (BaseTask): 要执行的任务对象
        
        Returns:
            BaseTask: 提交的任务对象（包含信号）
        """
        debug("infrastructure", f"提交任务到线程池：{task.task_name}")
        self.thread_pool.start(task)
        return task
    
    def wait_for_done(self, msecs=-1):
        """
        等待所有任务完成
        
        Args:
            msecs (int): 等待超时时间，-1表示无限等待
        
        Returns:
            bool: 是否所有任务都已完成
        """
        return self.thread_pool.waitForDone(msecs)
    
    def get_active_threads(self):
        """
        获取当前活跃线程数
        
        Returns:
            int: 活跃线程数
        """
        return self.thread_pool.activeThreadCount()
    
    def get_max_threads(self):
        """
        获取最大线程数
        
        Returns:
            int: 最大线程数
        """
        return self.thread_pool.maxThreadCount()


thread_pool_manager = None


def get_thread_pool_manager():
    """
    获取线程池管理器实例，延迟初始化
    
    Returns:
        ThreadPoolManager: 线程池管理器实例
    """
    global thread_pool_manager
    if thread_pool_manager is None:
        info("infrastructure", "初始化线程池管理器")
        thread_pool_manager = ThreadPoolManager()
    return thread_pool_manager


class Task1CheckCondition(BaseTask):
    """
    任务1：检查执行条件
    
    检查当前日期是否需要执行任务。
    """
    
    def __init__(self, check_date=None):
        """
        初始化任务
        
        Args:
            check_date (datetime.date, optional): 要检查的日期，默认今天
        """
        super().__init__(task_name="检查执行条件")
        self.check_date = check_date
    
    def execute(self):
        """
        执行检查条件任务
        """
        from system_core import should_work_today
        
        self.signals.status.emit("正在检查执行条件...")
        
        today = self.check_date if self.check_date else datetime.date.today()
        
        self.signals.log.emit(f"开始执行任务，当前日期：{today}")
        
        need_work = should_work_today(today)
        
        if not need_work:
            self.signals.log.emit("今天无需执行任务（节假日或周末）")
            self.signals.status.emit("今天不执行任务")
            self.signals.finished.emit(True, {"need_work": False, "date": today})
            return
        
        self.signals.log.emit("今天需要执行任务，开始执行流程")
        self.signals.status.emit("准备执行任务")
        self.signals.finished.emit(True, {"need_work": True, "date": today})


class Task2ConnectWifi(BaseTask):
    """
    任务2：连接WiFi
    
    自动连接到配置的WiFi网络。
    """
    
    def __init__(self):
        """
        初始化任务
        """
        super().__init__(task_name="连接WiFi")
    
    def execute(self):
        """
        执行WiFi连接任务
        """
        from business import auto_connect_wifi
        
        self.signals.status.emit("正在连接WiFi...")
        
        self.signals.log.emit("开始连接WiFi网络")
        
        try:
            auto_connect_wifi()
            self.signals.log.emit("WiFi网络连接成功")
            self.signals.status.emit("WiFi连接成功")
            self.signals.finished.emit(True, {"wifi_connected": True})
        except TimeoutError as e:
            self.signals.log.emit(f"WiFi连接超时：{e}")
            self.signals.status.emit("WiFi连接失败")
            self.signals.finished.emit(True, {"wifi_connected": False, "error": str(e)})
        except Exception as e:
            self.signals.log.emit(f"WiFi连接异常：{e}")
            self.signals.status.emit("WiFi连接异常")
            self.signals.finished.emit(True, {"wifi_connected": False, "error": str(e)})


class Task3CampusLogin(BaseTask):
    """
    任务3：登录校园网
    
    自动登录到校园网认证系统。
    """
    
    def __init__(self):
        """
        初始化任务
        """
        super().__init__(task_name="登录校园网")
    
    def execute(self):
        """
        执行校园网登录任务
        """
        from business import campus_login
        
        self.signals.status.emit("正在登录校园网...")
        
        self.signals.log.emit("开始登录校园网认证系统")
        
        try:
            campus_login()
            self.signals.log.emit("校园网认证系统登录成功")
            self.signals.status.emit("校园网登录完成")
            self.signals.finished.emit(True, {"login_successful": True})
        except Exception as e:
            self.signals.log.emit(f"校园网登录异常：{e}")
            self.signals.status.emit("校园网登录异常")
            self.signals.finished.emit(True, {"login_successful": False, "error": str(e)})


class Task4SetShutdown(BaseTask):
    """
    任务4：设置定时关机
    
    根据配置设置自动关机时间。
    """
    
    def __init__(self, check_date=None):
        """
        初始化任务
        
        Args:
            check_date (datetime.date, optional): 要设置关机的日期，默认今天
        """
        super().__init__(task_name="设置定时关机")
        self.check_date = check_date
    
    def execute(self):
        """
        执行设置定时关机任务
        """
        from system_core import global_config
        from business import set_shutdown_timer
        
        self.signals.status.emit("正在设置关机...")
        
        self.signals.log.emit("开始设置定时关机")
        
        try:
            shutdown_hour = global_config["SHUTDOWN_HOUR"]
            shutdown_min = global_config["SHUTDOWN_MIN"]
            
            today = self.check_date if self.check_date else datetime.date.today()
            shutdown_time = datetime.datetime.combine(
                today, datetime.time(shutdown_hour, shutdown_min)
            )
            now = datetime.datetime.now()
            
            if now >= shutdown_time:
                self.signals.log.emit(f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机")
                self.signals.finished.emit(True, {"shutdown_set": False, "reason": "time_passed"})
            else:
                seconds = int((shutdown_time - now).total_seconds())
                if seconds > 0:
                    set_shutdown_timer(seconds)
                    self.signals.log.emit(f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）")
                    self.signals.finished.emit(True, {"shutdown_set": True, "seconds": seconds})
                else:
                    self.signals.log.emit("关机时间计算无效，无法设置关机")
                    self.signals.finished.emit(True, {"shutdown_set": False, "reason": "invalid_time"})
        except Exception as e:
            self.signals.log.emit(f"设置关机异常：{e}")
            self.signals.finished.emit(True, {"shutdown_set": False, "error": str(e)})


class TaskManager:
    """
    任务管理器
    
    管理任务执行流程，处理任务间依赖关系，
    按顺序执行多个相关任务。
    """
    
    def __init__(self, parent=None):
        """
        初始化任务管理器
        
        Args:
            parent (QObject, optional): 父对象，用于信号连接
        """
        self.parent = parent
        self.tasks = []
        self.results = {}
        self.current_task_index = 0
    
    def execute_task_chain(self):
        """
        执行任务链
        
        按顺序执行所有任务，处理任务间依赖关系。
        """
        self.current_task_index = 0
        self.results = {}
        self._execute_next_task()
    
    def _execute_next_task(self):
        """
        执行下一个任务
        """
        if self.current_task_index >= len(self.tasks):
            self._on_all_tasks_finished()
            return
        
        task = self.tasks[self.current_task_index]
        
        task.signals.status.connect(self._on_task_status)
        task.signals.log.connect(self._on_task_log)
        task.signals.finished.connect(self._on_task_finished)
        task.signals.error.connect(self._on_task_error)
        
        get_thread_pool_manager().submit_task(task)
    
    def _on_task_status(self, status):
        """
        任务状态更新处理
        
        Args:
            status (str): 任务状态信息
        """
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar.showMessage(status)
    
    def _on_task_log(self, log_msg):
        """
        任务日志处理
        
        Args:
            log_msg (str): 日志消息
        """
        if hasattr(self.parent, '_log_write'):
            self.parent._log_write(log_msg)
        
        import re
        
        clean_log = log_msg.strip()
        if not clean_log:
            return
        
        if re.match(r'^=+$', clean_log):
            return
        
        module_name = "task"
        if "WiFi" in clean_log:
            module_name = "infrastructure"
        elif "校园网" in clean_log:
            module_name = "infrastructure"
        elif "关机" in clean_log:
            module_name = "infrastructure"
        
        info(module_name, clean_log)
    
    def _on_task_finished(self, success, result):
        """
        单个任务完成处理
        
        Args:
            success (bool): 任务是否成功
            result (object): 任务执行结果
        """
        task = self.tasks[self.current_task_index]
        self.results[task.task_name] = {"success": success, "result": result}
        
        debug("infrastructure", f"任务完成：{task.task_name}，结果：{success}")
        
        if task.task_name == "检查执行条件":
            if result and isinstance(result, dict) and not result.get("need_work", True):
                self.current_task_index = len(self.tasks)
                self._on_all_tasks_finished()
                return
        
        self.current_task_index += 1
        self._execute_next_task()
    
    def _on_task_error(self, task_name, error_msg):
        """
        任务错误处理
        
        Args:
            task_name (str): 任务名称
            error_msg (str): 错误信息
        """
        warning("infrastructure", f"任务出错：{task_name}，错误：{error_msg}")
        
        self.current_task_index += 1
        self._execute_next_task()
    
    def _on_all_tasks_finished(self):
        """
        所有任务完成处理
        
        发送任务链完成信号，通知主线程处理结果。
        """
        if hasattr(self, '_all_tasks_finished') and self._all_tasks_finished:
            return
        self._all_tasks_finished = True
        
        if hasattr(self.parent, '_set_buttons_enabled'):
            self.parent._set_buttons_enabled(True)
        
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar.showMessage("任务执行完成")
        
        info("infrastructure", "所有任务执行完成")


class FullTaskManager(TaskManager):
    """
    完整任务管理器
    
    管理完整的任务流程：
    1. 检查执行条件
    2. 连接WiFi
    3. 登录校园网
    4. 设置定时关机
    """
    
    def __init__(self, parent=None):
        """
        初始化完整任务管理器
        
        Args:
            parent (QObject, optional): 父对象
        """
        super().__init__(parent)
        self._build_task_chain()
    
    def _build_task_chain(self):
        """
        构建任务链
        
        创建并添加所有任务到任务列表。
        """
        self.tasks = [
            Task1CheckCondition(),
            Task2ConnectWifi(),
            Task3CampusLogin(),
            Task4SetShutdown()
        ]


_global_task_managers = []


def run_full_task_chain(parent=None):
    """
    执行完整任务流程
    
    Args:
        parent (QObject, optional): 父对象
    """
    task_manager = FullTaskManager(parent)
    
    if parent and hasattr(parent, 'task_manager'):
        parent.task_manager = task_manager
    else:
        _global_task_managers.append(task_manager)
    
    task_manager.execute_task_chain()
