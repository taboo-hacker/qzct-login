"""
并发框架模块

提供项目统一的并发调度能力，是"后台任务不卡界面"的核心：

- TaskContext  —— 任务运行上下文（任务内日志缓冲 + 协作式取消标志）
- TaskExecutor —— 线程池封装，通过 Qt Signal 把任务进度安全回报到主线程
- @task        —— 任务函数装饰器（统一命名 / 耗时统计 / 可选超时）
- TaskChain    —— 声明式顺序任务链（add → on_success/on_error → execute）

线程模型：
    主线程 = GUI（Qt 事件循环）；工作线程 = ThreadPoolExecutor。
    任务函数在工作线程执行，绝不能直接操作任何 Qt 界面控件；
    回报进度只能通过 Signal（跨线程 emit 自动走 QueuedConnection）。

取消模型（协作式）：
    cancel_all() 只是置位 TaskContext 的取消标志，不能强杀线程。
    任务函数需在长循环 / 长睡眠中主动检查 ctx.is_cancelled() 并尽快返回
    （services/wifi.py 的 _interruptible_sleep 是标准实现参考）。

典型用法见 services/tasks.py 与 gui/main_window.py 的 start_task_chain()。
"""

import functools
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

# 任务链步骤结果字典中的提前终止标记：值为真时链以"成功"结束并跳过剩余步骤
# （典型场景：task_check_condition 判定今天无需执行 → 跳过 WiFi/登录/关机）
CHAIN_BREAK_KEY = "chain_break"


class TaskContext:
    """任务运行上下文 —— 每个提交到 TaskExecutor 的任务各持有一个。

    承担两个职责：
    1. 任务内日志缓冲：任务函数通过 ctx.log() 记录过程信息，
       与全局日志分离，便于任务结束时统一查看。
    2. 协作式取消标志：cancel() 置位后，任务函数在长循环/睡眠中
       检查 is_cancelled() 自行退出（线程无法被外部强杀）。

    线程安全：所有读写均持锁，log/is_cancelled 可在任意线程调用。
    """

    def __init__(self, task_name: str):
        self.task_name = task_name
        self._cancelled = False
        self._logs: list[str] = []
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        """追加一条任务日志到缓冲区（线程安全）。"""
        with self._lock:
            self._logs.append(message)

    def is_cancelled(self) -> bool:
        """任务是否已被请求取消（任务函数应在长操作中轮询此标志）。"""
        with self._lock:
            return self._cancelled

    def cancel(self) -> None:
        """请求取消任务：置位取消标志并记录日志（不会中断已运行的代码）。"""
        with self._lock:
            self._cancelled = True
            self._logs.append("任务已取消")

    def get_logs(self) -> list[str]:
        """返回任务日志缓冲区的副本（线程安全）。"""
        with self._lock:
            return self._logs.copy()


class TaskExecutor(QObject):
    """任务执行器 — 统一的并发框架。

    封装 ThreadPoolExecutor 并通过 Qt 信号向主线程报告进度。
    支持 submit（单任务）和 execute_chain（顺序任务链）两种模式。

    三个信号均在主线程消费（跨线程 emit 自动 QueuedConnection），
    因此槽函数里可以安全地操作界面控件：
        started(task_name)              任务开始执行
        finished(task_name, result)     任务成功，result 为任务返回值
        error(task_name, error_msg)     任务抛出异常
    """

    started = Signal(str)
    finished = Signal(str, object)
    error = Signal(str, str)

    def __init__(self, max_workers: int | None = None):
        super().__init__()
        # 线程数默认按 CPU 核数×4 估算并封顶 16：
        # 任务多为 IO 等待（WiFi/HTTP），少量 CPU 即可支撑较高并发
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = min(cpu_count * 4, 16)

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers
        self._tasks: dict[str, Future[Any]] = {}
        self._contexts: dict[str, TaskContext] = {}
        self._lock = threading.Lock()

        # 链式执行状态
        self._chain_steps: list[dict[str, Any]] = []
        self._chain_index = 0
        self._chain_results: dict[str, Any] = {}
        self._chain_on_complete: Callable[[bool, dict[str, Any]], None] | None = None
        # 链信号连接（信号, 连接对象）成对记录，断开时用对应信号精确断开
        self._chain_connections: list[tuple[Any, Any]] = []
        self._chain_active = False

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def active_count(self) -> int:
        """当前活跃任务数（基于未完成的 future）。"""
        with self._lock:
            tasks = list(self._tasks.values())
        return sum(1 for f in tasks if not f.done())

    def submit(
        self, func: Callable[..., Any], task_name: str = "Unknown", *args: Any, **kwargs: Any
    ) -> Future[Any]:
        """提交单个任务到线程池执行。

        func 的第一个参数会被注入 TaskContext（任务函数签名约定为
        ``func(ctx, *args, **kwargs)``，见 @task 装饰器和 services/tasks.py）。

        Args:
            func: 任务函数，首参为 TaskContext
            task_name: 任务显示名（同名任务自动追加 _2/_3 序号避免冲突）
            *args/**kwargs: 透传给任务函数的其余参数

        Returns:
            外层 Future —— 完成即代表信号已发出，不携带任务返回值；
            任务结果请通过 finished 信号获取。
        """
        ctx = TaskContext(task_name)

        with self._lock:
            # 清理已完成的任务，防止字典无限增长
            done_keys = [k for k, f in self._tasks.items() if f.done()]
            for k in done_keys:
                del self._tasks[k]
                self._contexts.pop(k, None)

            # task_name 冲突时追加序号，避免覆盖已有任务的 context/future
            original_name = task_name
            counter = 2
            while task_name in self._tasks:
                task_name = f"{original_name}_{counter}"
                counter += 1

            self._contexts[task_name] = ctx

        def wrapped() -> None:
            try:
                # 检查任务是否有 timeout 属性
                timeout_val = getattr(func, "timeout", None)
                if timeout_val is not None:
                    # 使用 future.result(timeout=...) 实现超时
                    inner_future = self._executor.submit(func, ctx, *args, **kwargs)
                    try:
                        result = inner_future.result(timeout=timeout_val)
                    except FutureTimeoutError:
                        # 协作式取消：先置取消标志（长循环任务会自行退出），
                        # 再尝试取消 future（对已运行线程无效，但可拦截排队任务）
                        ctx.cancel()
                        inner_future.cancel()
                        raise TimeoutError(f"任务 {task_name} 超时 ({timeout_val}s)") from None
                else:
                    result = func(ctx, *args, **kwargs)
                self.finished.emit(task_name, result)
            except Exception as e:
                # 带上异常类型名：仅 str(e) 在空消息异常（如 raise RuntimeError()）
                # 或自定义异常时缺乏排障信息
                self.error.emit(task_name, f"{type(e).__name__}: {e}")

        future = self._executor.submit(wrapped)

        with self._lock:
            self._tasks[task_name] = future

        # started.emit 在 future 提交和 _tasks 记录之后发出，
        # 确保接收方收到信号时任务已注册完成。
        self.started.emit(task_name)

        return future

    def cancel_all(self) -> None:
        """取消所有已提交的任务。

        运行中任务通过 TaskContext 的取消标志协作式停止（任务函数需检查
        ctx.is_cancelled()）；未启动的 future 直接取消。
        """
        with self._lock:
            contexts = list(self._contexts.values())
            tasks = list(self._tasks.values())
        for ctx in contexts:
            ctx.cancel()
        for future in tasks:
            future.cancel()

    def is_chain_active(self) -> bool:
        """当前是否有任务链在执行。"""
        with self._lock:
            return self._chain_active

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池。

        同时中止未完成的任务链并断开其信号连接：避免关闭后运行中任务
        完成时信号触发 _execute_chain_next 在已关闭线程池上 submit，
        抛出 RuntimeError 导致 PySide6 abort。
        """
        with self._lock:
            self._chain_active = False
        self._disconnect_chain_signals()
        self._executor.shutdown(wait=wait)

    # ------------------------------------------------------------------
    # 任务链执行（封装内部细节，外部通过 TaskChain 调用）
    # ------------------------------------------------------------------

    def execute_chain(
        self, steps: list[dict[str, Any]], on_complete: Callable[[bool, dict[str, Any]], None]
    ) -> None:
        """执行顺序任务链。

        Args:
            steps: 任务步骤列表，每项为 {"func", "name", "args", "kwargs"}。
            on_complete: 完成回调，签名为 (success: bool, results: Dict)。
        """
        if self._chain_active:
            raise RuntimeError("execute_chain 不支持重入，请等待当前链完成或创建新实例")

        with self._lock:
            self._chain_active = True
        self._chain_steps = steps
        self._chain_index = 0
        self._chain_results = {}
        self._chain_on_complete = on_complete

        self._disconnect_chain_signals()
        self._chain_connections = [
            (self.finished, self.finished.connect(self._on_chain_task_finished)),
            (self.error, self.error.connect(self._on_chain_task_error)),
        ]

        self._execute_chain_next()

    def _disconnect_chain_signals(self) -> None:
        """断开任务链使用的信号连接（用对应信号精确断开，避免误断/告警）。"""
        for signal, conn in self._chain_connections:
            with suppress(RuntimeError, TypeError):
                signal.disconnect(conn)
        self._chain_connections = []

    def _execute_chain_next(self) -> None:
        """执行任务链中的下一个任务。"""
        if self._chain_index >= len(self._chain_steps):
            self._finish_chain(True)
            return

        step = self._chain_steps[self._chain_index]
        try:
            self.submit(step["func"], step["name"], *step["args"], **step["kwargs"])
        except RuntimeError:
            # 线程池已被关闭（如主窗口退出/链被中止）：按失败终止链，
            # 不能让异常逃逸出 Qt 槽（PySide6 会直接 abort 进程）
            self._chain_results[step["name"]] = {"error": "线程池已关闭，无法提交任务"}
            self._finish_chain(False)

    def _finish_chain(self, success: bool) -> None:
        """终止任务链：置未激活、断开信号、触发完成回调（幂等）。

        所有链结束路径（正常完成/提前终止/错误/关闭）统一走此方法，
        保证信号断开与回调只发生一次。
        """
        with self._lock:
            if not self._chain_active:
                return
            self._chain_active = False
            results = dict(self._chain_results)
        self._disconnect_chain_signals()
        if self._chain_on_complete:
            self._chain_on_complete(success, results)

    def _on_chain_task_finished(self, task_name: str, result: object) -> None:
        """任务链中单个任务完成的槽函数。"""
        self._chain_results[task_name] = result
        # 步骤可通过返回 {CHAIN_BREAK_KEY: True} 提前成功终止链
        # （如"今天无需执行"，跳过 WiFi/登录/关机等剩余步骤）
        if isinstance(result, dict) and result.get(CHAIN_BREAK_KEY):
            self._finish_chain(True)
            return
        self._chain_index += 1
        self._execute_chain_next()

    def _on_chain_task_error(self, task_name: str, error_msg: str) -> None:
        """任务链中单个任务失败的槽函数。"""
        self._chain_results[task_name] = {"error": error_msg}
        self._finish_chain(False)


# 全局任务注册表：@task 装饰器注册的包装函数按名称索引，
# 便于按名字查找任务（当前主要供测试与调试使用）
_task_registry: dict[str, Callable[..., Any]] = {}


def task(name: str, timeout: float | None = None) -> Callable[..., Any]:
    """任务函数装饰器 —— 统一命名、耗时统计、可选超时。

    用法：

        @task("连接WiFi", timeout=120)
        def task_connect_wifi(ctx: TaskContext) -> dict[str, Any]:
            ...

    行为说明：
    - 包装后函数的首参仍为 TaskContext（由 TaskExecutor.submit 注入）；
    - 自动记录"任务开始/完成/失败"及耗时到 ctx 日志；
    - timeout 生效机制：TaskExecutor.submit 读取 wrapper.timeout 属性，
      用 inner_future.result(timeout=...) 等待；超时后置 ctx 取消标志
      （协作式，任务函数需自行检查）并取消排队中的 future。

    Args:
        name: 任务显示名（出现在信号与链结果字典的键中）
        timeout: 超时秒数，None 表示不限时

    Returns:
        装饰器（带 task_name/timeout 属性的包装函数）
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(ctx: TaskContext, *args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            ctx.log(f"任务开始: {name}")

            try:
                result = func(ctx, *args, **kwargs)

                elapsed = time.time() - start_time
                ctx.log(f"任务完成: {name} (耗时: {elapsed:.2f}s)")

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                ctx.log(f"任务失败: {name} (耗时: {elapsed:.2f}s, 错误: {str(e)})")
                raise

        # 属性供 TaskExecutor.submit / TaskChain.add 识别任务名与超时
        wrapper.task_name = name  # type: ignore[attr-defined]
        wrapper.timeout = timeout  # type: ignore[attr-defined]
        _task_registry[name] = wrapper
        return wrapper

    return decorator


class TaskChain:
    """任务链 — 声明式顺序任务编排。

    通过 add() 添加步骤，on_success()/on_error() 注册回调，
    execute() 委托给 TaskExecutor.execute_chain() 执行。
    """

    def __init__(self, parent: QObject | None = None):
        self._steps: list[dict[str, Any]] = []
        self._on_success_callback: Callable[[bool, dict[str, Any]], None] | None = None
        self._on_error_callback: Callable[[dict[str, Any]], None] | None = None
        self._parent = parent
        self._executor: TaskExecutor | None = None

    def add(
        self, func: Callable[..., Any], name: str | None = None, *args: Any, **kwargs: Any
    ) -> "TaskChain":
        """追加一个步骤到链尾（支持链式调用）。

        Args:
            func: 任务函数（首参为 TaskContext；通常用 @task 装饰）
            name: 步骤名，缺省取 func.task_name（即 @task 的名字）
        """
        task_name = name or getattr(func, "task_name", f"Step-{len(self._steps)}")
        self._steps.append({"func": func, "name": task_name, "args": args, "kwargs": kwargs})
        return self

    def on_success(self, callback: Callable[[bool, dict[str, Any]], None]) -> "TaskChain":
        """注册链完成回调：链内所有步骤走完（含 chain_break 提前结束）时触发，
        签名 (success, results)；未注册 on_error 时失败也会走此回调。"""
        self._on_success_callback = callback
        return self

    def on_error(self, callback: Callable[[dict[str, Any]], None]) -> "TaskChain":
        """注册链失败回调：任一步骤抛异常导致链终止时触发，签名为 (results)。"""
        self._on_error_callback = callback
        return self

    def execute(self, executor: Optional["TaskExecutor"] = None) -> Optional["TaskExecutor"]:
        """启动任务链执行。

        Args:
            executor: 可选的 TaskExecutor 实例，不提供则自动创建。

        Returns:
            使用的 TaskExecutor 实例（空步骤链返回 None）。
        """
        if not self._steps:
            if self._on_success_callback:
                self._on_success_callback(True, {})
            return None

        if executor:
            self._executor = executor
        else:
            self._executor = TaskExecutor()

        def on_complete(success: bool, results: dict[str, Any]) -> None:
            if success:
                if self._on_success_callback:
                    self._on_success_callback(success, results)
            else:
                if self._on_error_callback:
                    self._on_error_callback(results)
                elif self._on_success_callback:
                    self._on_success_callback(False, results)

        self._executor.execute_chain(self._steps, on_complete)
        return self._executor
