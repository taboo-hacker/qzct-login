import functools
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class TaskContext:
    def __init__(self, task_name: str):
        self.task_name = task_name
        self._progress = 0
        self._cancelled = False
        self._logs: List[str] = []

    def log(self, message: str):
        self._logs.append(message)

    def set_progress(self, percent: int):
        self._progress = max(0, min(100, percent))

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True
        self.log("任务已取消")

    def get_logs(self) -> List[str]:
        return self._logs.copy()


class TaskExecutor(QObject):
    started = pyqtSignal(str)
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)
    progress = pyqtSignal(str, int)
    all_finished = pyqtSignal(bool)

    def __init__(self, max_workers: Optional[int] = None):
        super().__init__()
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = min(cpu_count * 4, 16)

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers
        self._tasks: Dict[str, Future] = {}
        self._contexts: Dict[str, TaskContext] = {}
        self._cancelled = False
        self._chain_index = 0
        self._chain_tasks: List[Dict] = []
        self._chain_results: Dict = {}
        self._chain_on_complete: Optional[Callable] = None

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def submit(self, func: Callable, task_name: str = "Unknown", *args, **kwargs) -> Future:
        # started 在主线程发出（submit 由主线程调用）
        self.started.emit(task_name)

        ctx = TaskContext(task_name)
        self._contexts[task_name] = ctx

        def wrapped():
            # 工作线程：finished / error 是 pyqtSignal，跨线程时 Qt 自动用
            # QueuedConnection 投递到接收者所在线程，无需手动队列。
            try:
                result = func(ctx, *args, **kwargs)
                self.finished.emit(task_name, result)
            except Exception as e:
                self.error.emit(task_name, str(e))

        future = self._executor.submit(wrapped)
        self._tasks[task_name] = future

        return future

    def submit_chain(self, tasks: List[Dict], on_complete: Optional[Callable] = None):
        self._chain_index = 0
        self._chain_tasks = tasks
        self._chain_results = {}
        self._chain_on_complete = on_complete

        self._execute_chain_next()

    def _execute_chain_next(self):
        if self._chain_index >= len(self._chain_tasks) or self._cancelled:
            if self._chain_on_complete:
                self._chain_on_complete(not self._cancelled, self._chain_results)
            self.all_finished.emit(not self._cancelled)
            return

        task_info = self._chain_tasks[self._chain_index]
        func = task_info["func"]
        task_name = task_info.get("name", f"Task-{self._chain_index}")
        args = task_info.get("args", ())
        kwargs = task_info.get("kwargs", {})

        self.submit(func, task_name, *args, **kwargs)

    def _on_chain_task_finished(self, task_name: str, result):
        self._chain_results[task_name] = result
        self._chain_index += 1
        self._execute_chain_next()

    def _on_chain_task_error(self, task_name: str, error_msg: str):
        self._chain_results[task_name] = {"error": error_msg}
        self._chain_index += 1
        self._execute_chain_next()

    def submit_parallel(self, tasks: List[Dict], on_complete: Optional[Callable] = None):
        results = {}
        completed_count = [0]
        total = len(tasks)

        def on_task_done(future: Future, task_name: str):
            # add_done_callback 由完成 future 的工作线程调用。
            # finished / error 是跨线程信号，Qt 会投递到主线程。
            try:
                result = future.result()
                results[task_name] = result
                self.finished.emit(task_name, result)
            except Exception as e:
                results[task_name] = {"error": str(e)}
                self.error.emit(task_name, str(e))
            finally:
                completed_count[0] += 1
                if completed_count[0] >= total:
                    if on_complete:
                        on_complete(not self._cancelled, results)
                    self.all_finished.emit(not self._cancelled)

        for i, task_info in enumerate(tasks):
            func = task_info["func"]
            task_name = task_info.get("name", f"Parallel-Task-{i}")
            args = task_info.get("args", ())
            kwargs = task_info.get("kwargs", {})

            ctx = TaskContext(task_name)
            self._contexts[task_name] = ctx

            def wrapped(fn=func, name=task_name):
                return fn(ctx, *args, **kwargs)

            future = self._executor.submit(wrapped)
            self._tasks[task_name] = future
            future.add_done_callback(lambda f, name=task_name: on_task_done(f, name))
            self.started.emit(task_name)

    def cancel_all(self):
        self._cancelled = True
        for name, ctx in self._contexts.items():
            ctx.cancel()

        for name, future in self._tasks.items():
            future.cancel()

    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        from concurrent.futures import ALL_COMPLETED, wait

        done, not_done = wait(self._tasks.values(), timeout=timeout, return_when=ALL_COMPLETED)
        return len(not_done) == 0

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)


_task_registry = {}


def task(name: str, timeout: Optional[float] = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(ctx: TaskContext, *args, **kwargs):
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

        wrapper.task_name = name
        wrapper.timeout = timeout
        _task_registry[name] = wrapper
        return wrapper

    return decorator


def get_registered_task(name: str) -> Optional[Callable]:
    return _task_registry.get(name)


def list_registered_tasks() -> List[str]:
    return list(_task_registry.keys())


class TaskChain:
    def __init__(self, parent: Optional[QObject] = None):
        self._steps: List[Dict] = []
        self._on_success_callback: Optional[Callable] = None
        self._on_error_callback: Optional[Callable] = None
        self._parent = parent
        self._executor: Optional[TaskExecutor] = None
        self._connections: list = []

    def add(self, func: Callable, name: str = None, *args, **kwargs):
        task_name = name or getattr(func, "task_name", f"Step-{len(self._steps)}")
        self._steps.append({"func": func, "name": task_name, "args": args, "kwargs": kwargs})
        return self

    def on_success(self, callback: Callable):
        self._on_success_callback = callback
        return self

    def on_error(self, callback: Callable):
        self._on_error_callback = callback
        return self

    def execute(self, executor: Optional["TaskExecutor"] = None):
        if not self._steps:
            if self._on_success_callback:
                self._on_success_callback(True, {})
            return None

        if executor:
            self._executor = executor
        else:
            self._executor = TaskExecutor()

        self._disconnect_signals()

        def on_complete(success, results):
            self._disconnect_signals()
            if success:
                if self._on_success_callback:
                    self._on_success_callback(success, results)
            else:
                if self._on_error_callback:
                    self._on_error_callback(results)
                elif self._on_success_callback:
                    self._on_success_callback(False, results)

        self._executor._chain_on_complete = on_complete
        self._executor._chain_tasks = self._steps
        self._executor._chain_index = 0
        self._executor._chain_results = {}

        conn1 = self._executor.finished.connect(self._executor._on_chain_task_finished)
        conn2 = self._executor.error.connect(self._executor._on_chain_task_error)
        self._connections = [conn1, conn2]

        self._executor._execute_chain_next()

        return self._executor

    def _disconnect_signals(self):
        if not self._executor or not self._connections:
            return
        for conn in self._connections:
            try:
                self._executor.finished.disconnect(conn)
            except TypeError:
                pass
            try:
                self._executor.error.disconnect(conn)
            except TypeError:
                pass
        self._connections = []

    def get_executor(self) -> Optional[TaskExecutor]:
        return self._executor
