import os
import time
import functools
import logging
import queue
from typing import Any, Callable, Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, Future
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class _TaskMessage:
    def __init__(self, msg_type: str, task_name: str = "", data=None):
        self.msg_type = msg_type
        self.task_name = task_name
        self.data = data


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
        
        self._message_queue: queue.Queue = queue.Queue()
        
        self._poll_timer = QTimer(self)
        self._poll_timer.setSingleShot(False)
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._process_messages)
        self._poll_timer.start()

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def _enqueue(self, msg: _TaskMessage):
        self._message_queue.put(msg)

    def _process_messages(self):
        while not self._message_queue.empty():
            try:
                msg = self._message_queue.get_nowait()
            except queue.Empty:
                break
            
            if msg.msg_type == "log":
                try:
                    from infrastructure import info
                    info("concurrency", f"[{msg.task_name}] {msg.data}")
                except Exception:
                    logging.info(f"[{msg.task_name}] {msg.data}")
            elif msg.msg_type == "finished":
                self.finished.emit(msg.task_name, msg.data)
            elif msg.msg_type == "error":
                self.error.emit(msg.task_name, msg.data)
            elif msg.msg_type == "progress":
                self.progress.emit(msg.task_name, msg.data)
            elif msg.msg_type == "all_finished":
                self.all_finished.emit(msg.data)

    def _emit_log(self, task_name: str, message: str):
        self._enqueue(_TaskMessage("log", task_name, message))

    def _emit_progress(self, task_name: str, percent: int):
        self._enqueue(_TaskMessage("progress", task_name, percent))

    def submit(self, func: Callable, task_name: str = "Unknown", *args, **kwargs) -> Future:
        self.started.emit(task_name)
        
        ctx = TaskContext(task_name)
        self._contexts[task_name] = ctx
        
        def wrapped():
            try:
                result = func(ctx, *args, **kwargs)
                self._enqueue(_TaskMessage("finished", task_name, result))
            except Exception as e:
                self._enqueue(_TaskMessage("error", task_name, str(e)))

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
            self._enqueue(_TaskMessage("all_finished", "", not self._cancelled))
            return

        task_info = self._chain_tasks[self._chain_index]
        func = task_info['func']
        task_name = task_info.get('name', f"Task-{self._chain_index}")
        args = task_info.get('args', ())
        kwargs = task_info.get('kwargs', {})
        
        self.submit(func, task_name, *args, **kwargs)

    def _on_chain_task_finished(self, task_name: str, result):
        self._chain_results[task_name] = result
        self._chain_index += 1
        self._execute_chain_next()

    def _on_chain_task_error(self, task_name: str, error_msg: str):
        self._chain_results[task_name] = {'error': error_msg}
        self._chain_index += 1
        self._execute_chain_next()

    def submit_parallel(self, tasks: List[Dict], on_complete: Optional[Callable] = None):
        results = {}
        completed_count = [0]
        total = len(tasks)
        connections = []  # 追踪连接，完成后断开

        def make_on_done(name):
            def on_done(future_name, res):
                results[future_name] = res
                completed_count[0] += 1
                if completed_count[0] >= total:
                    # 断开所有并行的信号连接，防止泄漏
                    for conn in connections:
                        try:
                            self.finished.disconnect(conn)
                        except TypeError:
                            pass
                    connections.clear()
                    if on_complete:
                        on_complete(not self._cancelled, results)
                    self._enqueue(_TaskMessage("all_finished", "", not self._cancelled))
            return on_done

        for i, task_info in enumerate(tasks):
            func = task_info['func']
            task_name = task_info.get('name', f"Parallel-Task-{i}")
            args = task_info.get('args', ())
            kwargs = task_info.get('kwargs', {})

            self.submit(func, task_name, *args, **kwargs)

            conn = self.finished.connect(make_on_done(task_name))
            connections.append(conn)

    def cancel_all(self):
        self._cancelled = True
        for name, ctx in self._contexts.items():
            ctx.cancel()
        
        for name, future in self._tasks.items():
            future.cancel()

    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        from concurrent.futures import wait, ALL_COMPLETED
        done, not_done = wait(self._tasks.values(), timeout=timeout, return_when=ALL_COMPLETED)
        return len(not_done) == 0

    def shutdown(self, wait: bool = True):
        self._poll_timer.stop()
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

    def add(self, func: Callable, name: str = None, *args, **kwargs):
        task_name = name or getattr(func, 'task_name', f"Step-{len(self._steps)}")
        self._steps.append({
            'func': func,
            'name': task_name,
            'args': args,
            'kwargs': kwargs
        })
        return self

    def add_parallel(self, *task_funcs):
        for i, func in enumerate(task_funcs):
            task_name = getattr(func, 'task_name', f"Parallel-{i}")
            self._steps.append({
                'func': func,
                'name': task_name,
                'args': (),
                'kwargs': {}
            })
        return self

    def on_success(self, callback: Callable):
        self._on_success_callback = callback
        return self

    def on_error(self, callback: Callable):
        self._on_error_callback = callback
        return self

    def execute(self, executor: Optional['TaskExecutor'] = None):
        if not self._steps:
            if self._on_success_callback:
                self._on_success_callback(True, {})
            return None

        if executor:
            self._executor = executor
        else:
            self._executor = TaskExecutor()
        
        def on_complete(success, results):
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
        
        self._executor.finished.connect(
            self._executor._on_chain_task_finished
        )
        self._executor.error.connect(
            self._executor._on_chain_task_error
        )
        
        self._executor._execute_chain_next()

        return self._executor

    def get_executor(self) -> Optional[TaskExecutor]:
        return self._executor
