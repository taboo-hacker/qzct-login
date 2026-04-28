import os
import datetime
import sys
from PyQt5.QtCore import QThreadPool

from utils.logger import setup_logger, set_gui_widget, get_logger

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
    except (ValueError, TypeError, AttributeError):
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
# 日志系统模块（基于 Loguru）
# ==========================================

LOG_LEVEL_MAP = {
    0: "DEBUG",
    1: "INFO",
    2: "WARNING",
    3: "ERROR",
    4: "CRITICAL"
}

logger = None


class Logger:
    """
    向后兼容的日志包装类
    
    保持与原 Logger API 一致，内部使用 Loguru。
    """
    
    def __init__(self, gui_log_widget=None, log_file_path=None, level=1,
                 max_log_size=10*1024*1024, backup_count=5):
        global logger
        logger = self
        
        max_size_mb = max_log_size / (1024 * 1024)
        rotation_str = f"{max_size_mb:.0f} MB"
        retention_days = backup_count * 7
        
        self._loguru_logger = setup_logger(
            gui_widget=gui_log_widget,
            log_file=log_file_path,
            level=LOG_LEVEL_MAP.get(level, "INFO"),
            max_size=rotation_str,
            retention=f"{retention_days} days"
        )
    
    def log(self, module_name, level, message, exc_info=None, from_handler=False):
        std_level = LOG_LEVEL_MAP.get(level, "INFO")
        if exc_info and level >= 3:
            self._loguru_logger.opt(exception=True).log(std_level, "<{name}> {message}", name=module_name, message=message)
        else:
            self._loguru_logger.log(std_level, "<{name}> {message}", name=module_name, message=message)
    
    def debug(self, module_name, message, exc_info=False):
        self.log(module_name, 0, message, exc_info)
    
    def info(self, module_name, message, exc_info=False):
        self.log(module_name, 1, message, exc_info)
    
    def warning(self, module_name, message, exc_info=False):
        self.log(module_name, 2, message, exc_info)
    
    def error(self, module_name, message, exc_info=False):
        self.log(module_name, 3, message, exc_info)
    
    def critical(self, module_name, message, exc_info=False):
        self.log(module_name, 4, message, exc_info)


def init_logger(gui_log_widget=None, log_file_path=None, level=1):
    """初始化全局日志对象"""
    global logger
    logger = Logger(gui_log_widget=gui_log_widget, log_file_path=log_file_path, level=level)
    return logger


def debug(module_name, message, exc_info=False):
    if logger:
        logger.debug(module_name, message, exc_info)


def info(module_name, message, exc_info=False):
    if logger:
        logger.info(module_name, message, exc_info)


def warning(module_name, message, exc_info=False):
    if logger:
        logger.warning(module_name, message, exc_info)


def error(module_name, message, exc_info=True):
    if logger:
        exc_type = sys.exc_info()[0]
        if exc_info and exc_type is not None:
            logger.error(module_name, message, exc_info=True)
        else:
            logger.error(module_name, message, exc_info=False)


def critical(module_name, message, exc_info=True):
    if logger:
        exc_type = sys.exc_info()[0]
        if exc_info and exc_type is not None:
            logger.critical(module_name, message, exc_info=True)
        else:
            logger.critical(module_name, message, exc_info=False)


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
    
    def isatty(self):
        """
        判断是否为终端设备
        
        Returns:
            bool: 始终返回 False，因为这是重定向流
        """
        return False
    
    def fileno(self):
        """
        获取文件描述符

        返回标准错误流的文件描述符作为回退，避免依赖 fileno() 的第三方库崩溃。
        """
        import sys
        return sys.__stderr__.fileno()
    
    def readable(self):
        """
        判断是否可读
        
        Returns:
            bool: 始终返回 False
        """
        return False
    
    def writable(self):
        """
        判断是否可写
        
        Returns:
            bool: 始终返回 True
        """
        return True
    
    def seekable(self):
        """
        判断是否可搜索
        
        Returns:
            bool: 始终返回 False
        """
        return False



# ==========================================
# 线程池管理模块
# ==========================================
class ThreadPoolManager:
    """
    线程池管理器

    管理全局线程池，提供任务提交和管理功能。
    单例模式设计，确保整个应用只有一个线程池实例。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_thread_pool()
        return cls._instance

    def _init_thread_pool(self):
        self.thread_pool = QThreadPool()
        cpu_count = os.cpu_count() or 4
        max_threads = min(cpu_count * 4, 16)
        self.thread_pool.setMaxThreadCount(max_threads)
        self.thread_pool.setStackSize(1024 * 1024)

        info("infrastructure", f"线程池初始化完成，最大线程数：{self.thread_pool.maxThreadCount()}")

    def get_active_threads(self):
        return self.thread_pool.activeThreadCount()

    def get_max_threads(self):
        return self.thread_pool.maxThreadCount()


_thread_pool_manager = None


def get_thread_pool_manager():
    """获取线程池管理器实例，延迟初始化"""
    global _thread_pool_manager
    if _thread_pool_manager is None:
        info("infrastructure", "初始化线程池管理器")
        _thread_pool_manager = ThreadPoolManager()
    return _thread_pool_manager
