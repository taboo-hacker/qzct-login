import logging
import sys
import os
from PyQt5.QtCore import QTimer

# 全局Logger实例引用，用于在Handler中访问
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
            # 从record中获取logger_name，如果没有则使用record.name
            logger_name = getattr(record, 'logger_name', record.name)
            
            # 转换日志级别
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
            
            # 使用QTimer.singleShot确保在主线程中执行日志记录
            # 直接调用logger.log可能导致线程安全问题
            # 传递from_handler=True参数，防止递归调用
            QTimer.singleShot(0, lambda: _global_logger_instance.log(
                logger_name, level, record.getMessage(), exc_info=record.exc_info, from_handler=True
            ))

# 设置日志格式和配置
# 注意：在Logger类中会清除所有处理器，所以这里不需要添加处理器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d] [%(logger_name)s] [%(levelname)s] %(message)s',
    datefmt='[%Y-%m-%d %H:%M:%S'
)

# 映射原日志级别到标准logging级别
LOG_LEVEL_MAP = {
    0: logging.DEBUG,
    1: logging.INFO,
    2: logging.WARNING,
    3: logging.ERROR,
    4: logging.CRITICAL
}


# ==========================================
# 标准日志系统包装类
# ==========================================
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
    
    def __init__(self, gui_log_widget=None, log_file_path=None, level=1,  # INFO
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
        
        # 日志缓存优化
        self.log_buffer = []
        self.buffer_size = 10  # 日志缓存大小
        self.flush_interval = 500  # 自动刷新间隔（毫秒）
        self.flush_timer = None
        
        # 保存实例到全局变量，供GUIHandler使用
        global _global_logger_instance
        _global_logger_instance = self
        
        # 仅在GUI环境下初始化日志刷新计时器
        if gui_log_widget:
            try:
                self.flush_timer = QTimer()
                self.flush_timer.timeout.connect(self._flush_log_buffer)
                self.flush_timer.start(self.flush_interval)
            except ImportError:
                # 非GUI环境下，直接禁用缓存
                self.buffer_size = 1
        else:
            # 非GUI环境下，直接禁用缓存
            self.buffer_size = 1
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVEL_MAP.get(level, logging.INFO))
        
        # 清除所有现有的处理器，防止重复配置
        root_logger.handlers.clear()
        
        # 仅在有GUI窗口时添加GUIHandler
        if gui_log_widget:
            gui_handler = GUIHandler()
            root_logger.addHandler(gui_handler)
        
        # 设置文件处理器
        if log_file_path:
            # 检查并创建日志目录
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                try:
                    os.makedirs(log_dir)
                except Exception:
                    pass
            
            # 使用RotatingFileHandler自动处理日志轮换
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
        
        # 仅在非GUI环境下添加控制台输出处理器
        if not gui_log_widget:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d] [%(logger_name)s] [%(levelname)s] %(message)s',
                datefmt='[%Y-%m-%d %H:%M:%S'
            ))
            root_logger.addHandler(stream_handler)
        
        # 添加一个测试日志，验证初始化成功
        root_logger.info("日志系统初始化完成", extra={"logger_name": "logger"})
    
    def _flush_log_buffer(self):
        """
        刷新日志缓存，将缓存中的日志批量写入GUI
        
        批量处理日志更新，减少UI刷新频率，提高程序响应速度。
        """
        if not self.gui_log_widget or not self.log_buffer:
            return
        
        # 合并所有缓存的日志
        combined_log = "".join(self.log_buffer)
        self.log_buffer.clear()
        
        # 批量写入GUI
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
        
        # 转换为标准logging级别
        std_level = LOG_LEVEL_MAP.get(level, logging.INFO)
        
        # 仅在非GUIHandler调用时，才记录到标准logging
        # 防止递归调用
        if not from_handler:
            # 直接使用root_logger，避免子logger级别问题
            root_logger = logging.getLogger()
            
            # 记录日志，传入logger_name作为extra参数
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
        
        # 同时输出到GUI日志窗口
        if self.gui_log_widget:
            # 格式化为字符串，用于GUI显示
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level_name = logging.getLevelName(std_level)
            log_message = f"[{timestamp}] [{module_name}] [{level_name}] {message}\n"
            
            # 如果有异常信息，添加堆栈跟踪
            if exc_info and level >= 3:  # ERROR级别及以上
                import traceback
                try:
                    stack_trace = traceback.format_exc()
                    if stack_trace:
                        log_message += f"{stack_trace}\n"
                except Exception:
                    pass
            
            # 添加到缓存
            self.log_buffer.append(log_message)
            
            # 如果缓存已满，立即刷新
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


# ==========================================
# 全局日志对象
# ==========================================
# 初始化为None，后续在主程序中配置
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


# ==========================================
# 便捷日志函数
# ==========================================
def debug(module_name, message, exc_info=False):
    """
    便捷的DEBUG日志记录函数
    """
    from logger import logger
    if logger:
        logger.debug(module_name, message, exc_info)


def info(module_name, message, exc_info=False):
    """
    便捷的INFO日志记录函数
    """
    from logger import logger
    if logger:
        logger.info(module_name, message, exc_info)


def warning(module_name, message, exc_info=False):
    """
    便捷的WARNING日志记录函数
    """
    from logger import logger
    if logger:
        logger.warning(module_name, message, exc_info)


def error(module_name, message, exc_info=True):
    """
    便捷的ERROR日志记录函数
    """
    from logger import logger
    if logger:
        logger.error(module_name, message, exc_info)


def critical(module_name, message, exc_info=True):
    """
    便捷的CRITICAL日志记录函数
    """
    from logger import logger
    if logger:
        logger.critical(module_name, message, exc_info)


# ==========================================
# 输出流重定向类
# ==========================================
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
