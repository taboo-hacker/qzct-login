#!/usr/bin/env python3
"""
线程池管理模块

提供高效的线程池实现，用于管理和执行异步任务，
减少线程创建销毁开销，提高任务执行效率。

使用Qt的QThreadPool和QRunnable实现，与PyQt6
GUI框架无缝集成，支持信号机制进行线程间通信。
"""

from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSignal, QObject
import traceback
import sys
import os
import logging

# 配置日志
def info(module_name, message):
    logging.info(message, extra={"logger_name": module_name})

def error(module_name, message, exc_info=False):
    logging.error(message, extra={"logger_name": module_name}, exc_info=exc_info)

def debug(module_name, message):
    logging.debug(message, extra={"logger_name": module_name})

def warning(module_name, message):
    logging.warning(message, extra={"logger_name": module_name})


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
            # 使用全局logger对象记录日志
            from logger import debug
            debug("thread_pool", f"开始执行任务：{self.task_name}")
            self.execute()
        except Exception as e:
            # 使用全局logger对象记录日志
            from logger import error
            error("thread_pool", f"任务执行出错：{self.task_name}", exc_info=True)
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
        # 根据CPU核心数动态设置线程池大小
        # 一般设置为CPU核心数的2-4倍，这里使用4倍
        cpu_count = os.cpu_count() or 4
        max_threads = min(cpu_count * 4, 16)  # 最多16个线程
        self.thread_pool.setMaxThreadCount(max_threads)
        # 设置线程优先级
        self.thread_pool.setStackSize(1024 * 1024)  # 1MB堆栈大小
        
        info("thread_pool", f"线程池初始化完成，最大线程数：{self.thread_pool.maxThreadCount()}")
    
    def submit_task(self, task):
        """
        提交任务到线程池执行
        
        Args:
            task (BaseTask): 要执行的任务对象
        
        Returns:
            BaseTask: 提交的任务对象（包含信号）
        """
        debug("thread_pool", f"提交任务到线程池：{task.task_name}")
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


# 全局线程池实例引用（延迟初始化）
thread_pool_manager = None


def get_thread_pool_manager():
    """
    获取线程池管理器实例，延迟初始化
    
    Returns:
        ThreadPoolManager: 线程池管理器实例
    """
    global thread_pool_manager
    if thread_pool_manager is None:
        info("thread_pool", "初始化线程池管理器")
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
        from date_rules import should_work_today
        import datetime
        from logger import info
        
        self.signals.status.emit("正在检查执行条件...")
        
        today = self.check_date if self.check_date else datetime.date.today()
        
        info("task_checker", f"开始执行任务，当前日期：{today}")
        
        need_work = should_work_today(today)
        
        if not need_work:
            info("task_checker", "今天无需执行任务（节假日或周末）")
            self.signals.status.emit("今天不执行任务")
            self.signals.finished.emit(True, {"need_work": False, "date": today})
            return
        
        info("task_checker", "今天需要执行任务，开始执行流程")
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
        from wifi import auto_connect_wifi
        from logger import info, error
        
        self.signals.status.emit("正在连接WiFi...")
        
        info("wifi", "开始连接WiFi网络")
        
        try:
            auto_connect_wifi()
            info("wifi", "WiFi网络连接成功")
            self.signals.status.emit("WiFi连接成功")
            self.signals.finished.emit(True, {"wifi_connected": True})
        except TimeoutError as e:
            error("wifi", f"WiFi连接超时：{e}")
            self.signals.status.emit("WiFi连接失败")
            # WiFi连接失败不影响后续任务执行
            self.signals.finished.emit(True, {"wifi_connected": False, "error": str(e)})
        except Exception as e:
            error("wifi", f"WiFi连接异常：{e}")
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
        from campus_login import campus_login
        from logger import info, error
        
        self.signals.status.emit("正在登录校园网...")
        
        info("campus_login", "开始登录校园网认证系统")
        
        try:
            campus_login()
            info("campus_login", "校园网认证系统登录成功")
            self.signals.status.emit("校园网登录完成")
            self.signals.finished.emit(True, {"login_successful": True})
        except Exception as e:
            error("campus_login", f"校园网登录异常：{e}")
            self.signals.status.emit("校园网登录异常")
            # 登录失败不影响后续任务执行
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
        from config import global_config
        from shutdown import set_shutdown_timer
        import datetime
        from logger import info, error
        
        self.signals.status.emit("正在设置关机...")
        
        info("shutdown", "开始设置定时关机")
        
        try:
            shutdown_hour = global_config["SHUTDOWN_HOUR"]
            shutdown_min = global_config["SHUTDOWN_MIN"]
            
            today = self.check_date if self.check_date else datetime.date.today()
            shutdown_time = datetime.datetime.combine(
                today, datetime.time(shutdown_hour, shutdown_min)
            )
            now = datetime.datetime.now()
            
            if now >= shutdown_time:
                info("shutdown", f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机")
                self.signals.finished.emit(True, {"shutdown_set": False, "reason": "time_passed"})
            else:
                seconds = int((shutdown_time - now).total_seconds())
                if seconds > 0:
                    set_shutdown_timer(seconds)
                    info("shutdown", f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）")
                    self.signals.finished.emit(True, {"shutdown_set": True, "seconds": seconds})
                else:
                    error("shutdown", "关机时间计算无效，无法设置关机", exc_info=False)
                    self.signals.finished.emit(True, {"shutdown_set": False, "reason": "invalid_time"})
        except Exception as e:
            error("shutdown", f"设置关机异常：{e}")
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
            # 所有任务执行完成
            self._on_all_tasks_finished()
            return
        
        task = self.tasks[self.current_task_index]
        
        # 连接任务信号
        task.signals.status.connect(self._on_task_status)
        task.signals.log.connect(self._on_task_log)
        task.signals.finished.connect(self._on_task_finished)
        task.signals.error.connect(self._on_task_error)
        
        # 提交任务到线程池
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
        # 直接调用父对象的日志写入方法，确保日志显示在GUI上
        if hasattr(self.parent, '_log_write'):
            self.parent._log_write(log_msg)
        
        # 同时使用专业日志系统记录日志
        import re
        
        # 提取日志内容，去除格式字符
        clean_log = log_msg.strip()
        if not clean_log:
            return
        
        # 去除等号分隔符
        if re.match(r'^=+$', clean_log):
            return
        
        # 根据日志内容判断模块名称
        module_name = "task"
        if "WiFi" in clean_log:
            module_name = "wifi"
        elif "校园网" in clean_log:
            module_name = "campus_login"
        elif "关机" in clean_log:
            module_name = "shutdown"
        
        # 使用专业日志系统记录日志
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
        
        debug("thread_pool", f"任务完成：{task.task_name}，结果：{success}")
        
        # 检查任务结果，如果是检查条件任务且不需要工作，结束整个任务链
        if task.task_name == "检查执行条件":
            if result and isinstance(result, dict) and not result.get("need_work", True):
                # 今天不需要工作，结束任务链
                self.current_task_index = len(self.tasks)  # 直接跳到最后
                self._on_all_tasks_finished()
                return
        
        # 执行下一个任务
        self.current_task_index += 1
        self._execute_next_task()
    
    def _on_task_error(self, task_name, error_msg):
        """
        任务错误处理
        
        Args:
            task_name (str): 任务名称
            error_msg (str): 错误信息
        """
        warning("thread_pool", f"任务出错：{task_name}，错误：{error_msg}")
        
        # 继续执行下一个任务
        self.current_task_index += 1
        self._execute_next_task()
    
    def _on_all_tasks_finished(self):
        """
        所有任务完成处理
        
        发送任务链完成信号，通知主线程处理结果。
        """
        # 避免重复执行
        if hasattr(self, '_all_tasks_finished') and self._all_tasks_finished:
            return
        self._all_tasks_finished = True
        
        # 发送最终状态
        if hasattr(self.parent, '_set_buttons_enabled'):
            self.parent._set_buttons_enabled(True)
        
        if hasattr(self.parent, 'statusBar'):
            self.parent.statusBar.showMessage("任务执行完成")
        
        # 记录日志
        info("thread_pool", "所有任务执行完成")


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


# 全局任务管理器引用，防止被垃圾回收
_global_task_managers = []

# 便捷函数：执行完整任务流程
def run_full_task_chain(parent=None):
    """
    执行完整任务流程
    
    Args:
        parent (QObject, optional): 父对象
    """
    # 创建任务管理器实例
    task_manager = FullTaskManager(parent)
    
    # 保存到父对象或全局列表，防止被垃圾回收
    if parent and hasattr(parent, 'task_manager'):
        parent.task_manager = task_manager
    else:
        # 非GUI模式下保存到全局列表
        _global_task_managers.append(task_manager)
    
    task_manager.execute_task_chain()
