import functools
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class TaskContext:
    def __init__(self, task_name: str):
        self.task_name = task_name
        self._progress = 0
        self._cancelled = False
        self._logs: list[str] = []
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        with self._lock:
            self._logs.append(message)

    def set_progress(self, percent: int) -> None:
        with self._lock:
            self._progress = max(0, min(100, percent))

    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            self._logs.append("任务已取消")

    def get_logs(self) -> list[str]:
        with self._lock:
            return self._logs.copy()


class TaskExecutor(QObject):
    """任务执行器 — 统一的并发框架。

    封装 ThreadPoolExecutor 并通过 Qt 信号向主线程报告进度。
    支持 submit（单任务）和 execute_chain（顺序任务链）两种模式。
    """

    started = pyqtSignal(str)
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    all_finished = pyqtSignal(bool)

    def __init__(self, max_workers: int | None = None):
        super().__init__()
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = min(cpu_count * 4, 16)

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers
        self._tasks: dict[str, Future[Any]] = {}
        self._contexts: dict[str, TaskContext] = {}
        self._cancelled = False
        self._lock = threading.Lock()

        # 链式执行状态
        self._chain_steps: list[dict[str, Any]] = []
        self._chain_index = 0
        self._chain_results: dict[str, Any] = {}
        self._chain_on_complete: Callable[[bool, dict[str, Any]], None] | None = None
        self._chain_connections: list[Any] = []
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
        """提交单个任务到线程池执行。"""
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
                        inner_future.cancel()
                        raise TimeoutError(f"任务 {task_name} 超时 ({timeout_val}s)") from None
                else:
                    result = func(ctx, *args, **kwargs)
                self.finished.emit(task_name, result)
            except Exception as e:
                self.error.emit(task_name, str(e))

        future = self._executor.submit(wrapped)

        with self._lock:
            self._tasks[task_name] = future

        # started.emit 在 future 提交和 _tasks 记录之后发出，
        # 确保接收方收到信号时任务已注册完成。
        self.started.emit(task_name)

        return future

    def cancel_all(self) -> None:
        """取消所有已提交的任务。"""
        self._cancelled = True
        with self._lock:
            contexts = list(self._contexts.values())
            tasks = list(self._tasks.values())
        for ctx in contexts:
            ctx.cancel()
        for future in tasks:
            future.cancel()

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池。"""
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
            self.finished.connect(self._on_chain_task_finished),
            self.error.connect(self._on_chain_task_error),
        ]

        self._execute_chain_next()

    def _disconnect_chain_signals(self) -> None:
        """断开任务链使用的信号连接。"""
        for conn in self._chain_connections:
            with suppress(TypeError):
                self.finished.disconnect(conn)
            with suppress(TypeError):
                self.error.disconnect(conn)
        self._chain_connections = []

    def _execute_chain_next(self) -> None:
        """执行任务链中的下一个任务。"""
        if self._chain_index >= len(self._chain_steps):
            with self._lock:
                self._chain_active = False
            self._disconnect_chain_signals()
            if self._chain_on_complete:
                self._chain_on_complete(True, self._chain_results)
            return

        step = self._chain_steps[self._chain_index]
        self.submit(step["func"], step["name"], *step["args"], **step["kwargs"])

    def _on_chain_task_finished(self, task_name: str, result: object) -> None:
        """任务链中单个任务完成的槽函数。"""
        self._chain_results[task_name] = result
        self._chain_index += 1
        self._execute_chain_next()

    def _on_chain_task_error(self, task_name: str, error_msg: str) -> None:
        """任务链中单个任务失败的槽函数。"""
        self._chain_results[task_name] = {"error": error_msg}
        with self._lock:
            self._chain_active = False
        self._disconnect_chain_signals()
        if self._chain_on_complete:
            self._chain_on_complete(False, self._chain_results)


_task_registry: dict[str, Callable[..., Any]] = {}


def task(name: str, timeout: float | None = None) -> Callable[..., Any]:
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
        task_name = name or getattr(func, "task_name", f"Step-{len(self._steps)}")
        self._steps.append({"func": func, "name": task_name, "args": args, "kwargs": kwargs})
        return self

    def on_success(self, callback: Callable[[bool, dict[str, Any]], None]) -> "TaskChain":
        self._on_success_callback = callback
        return self

    def on_error(self, callback: Callable[[dict[str, Any]], None]) -> "TaskChain":
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
