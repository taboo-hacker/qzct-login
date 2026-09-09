"""
infra/concurrency.py 模块测试

测试并发框架的四个核心组件：
- TaskContext：任务上下文（日志、取消标志）；
- @task 装饰器：为函数附加 task_name 元数据；
- TaskExecutor：线程池执行器（提交、取消、线程数）；
- TaskChain：流式任务链（add/on_success/on_error、顺序执行、失败中断、
  CHAIN_BREAK_KEY 提前成功终止、执行中 shutdown 的安全性）。
集成用例依赖 Qt 信号，通过"泵 processEvents + 轮询 Event"等待异步回调。
"""

import threading
import time
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from infra.concurrency import (
    CHAIN_BREAK_KEY,
    TaskChain,
    TaskContext,
    TaskExecutor,
    task,
)
from tests.conftest import ensure_qapp as _ensure_qapp


class TestTaskContext:
    """TaskContext 测试：初始化状态、日志追加与取消标志。"""

    def test_context_initialization(self) -> None:
        """新建上下文应记录任务名，且取消标志与日志列表为初始空状态。"""
        ctx = TaskContext("test_task")

        assert ctx.task_name == "test_task"
        assert ctx._cancelled is False
        assert ctx._logs == []

    def test_log(self) -> None:
        """log() 应按调用顺序把消息追加到内部日志列表。"""
        ctx = TaskContext("test")
        ctx.log("message 1")
        ctx.log("message 2")

        assert len(ctx._logs) == 2
        assert ctx._logs[0] == "message 1"
        assert ctx._logs[1] == "message 2"

    def test_get_logs(self) -> None:
        """get_logs() 应返回日志副本而非内部列表引用（防止外部篡改）。"""
        ctx = TaskContext("test")
        ctx.log("message")
        logs = ctx.get_logs()

        assert logs == ["message"]
        assert logs is not ctx._logs

    def test_cancel(self) -> None:
        """cancel() 调用后 is_cancelled() 应由 False 翻转为 True。"""
        ctx = TaskContext("test")

        assert ctx.is_cancelled() is False
        ctx.cancel()
        assert ctx.is_cancelled() is True


class TestTaskDecorator:
    """@task 装饰器测试：元数据注入与直接调用执行。"""

    def test_task_decorator(self) -> None:
        """被 @task 装饰的函数应携带 task_name 属性。"""

        @task("测试任务")
        def sample_task(ctx: TaskContext) -> dict:
            ctx.log("执行任务")
            return {"success": True}

        assert hasattr(sample_task, "task_name")
        assert sample_task.task_name == "测试任务"

    def test_task_execution(self) -> None:
        """直接调用被装饰函数应正常执行并写入上下文日志。"""

        @task("执行测试任务", timeout=30)
        def executing_task(ctx: TaskContext) -> dict:
            ctx.log("开始执行")
            return {"done": True}

        ctx = TaskContext("test")
        result = executing_task(ctx)

        assert result["done"] is True
        assert "开始执行" in ctx.get_logs()


class TestTaskExecutor:
    """TaskExecutor 测试：线程池初始化、任务提交与批量取消。"""

    def test_executor_initialization(self) -> None:
        """新建执行器应有正的线程数上限与空的任务/上下文表。"""
        executor = TaskExecutor()

        assert executor._max_workers > 0
        assert executor._tasks == {}
        assert executor._contexts == {}

    def test_executor_max_workers(self) -> None:
        """显式传入 max_workers=4 时应按该值生效。"""
        executor = TaskExecutor(max_workers=4)
        assert executor.max_workers == 4

    def test_submit_task(self) -> None:
        """submit() 应返回非 None 的 Future 对象。"""
        executor = TaskExecutor()

        @task("提交测试")
        def simple_task(ctx: TaskContext) -> dict:
            return {"result": "ok"}

        future = executor.submit(simple_task, "提交测试")
        assert future is not None

    def test_cancel_all(self) -> None:
        """cancel_all() 应给所有已注册上下文设置取消标志。"""
        executor = TaskExecutor()

        @task("取消测试")
        def long_task(ctx: TaskContext) -> dict:
            # 协作式取消：线程池无法强杀线程，任务须自查取消标志尽快退出。
            # 若直接 sleep(10)，测试结束后线程仍在运行，醒来会在已被回收的
            # TaskExecutor 上 emit 信号，导致整个测试进程段错误
            # （Linux CI 上必现：退出码 139）
            for _ in range(100):
                if ctx.is_cancelled():
                    return {}
                time.sleep(0.1)
            return {}

        executor.submit(long_task, "取消测试")
        executor.cancel_all()

        # 验证所有 context 的 cancel 标志已设置
        # （加锁读取，避免与工作线程修改contexts 的竞争）
        with executor._lock:
            for ctx in executor._contexts.values():
                assert ctx.is_cancelled()
        # wait=True：等协作式取消生效（≤0.1s），确保线程退出后再释放 executor
        executor.shutdown(wait=True)


class TestTaskChain:
    """TaskChain 测试：链的构建 API（add/回调注册/流式串联）。"""

    def test_chain_initialization(self) -> None:
        """新建任务链的步骤列表与成功/失败回调均应为空。"""
        chain = TaskChain()

        assert chain._steps == []
        assert chain._on_success_callback is None
        assert chain._on_error_callback is None

    def test_chain_add(self) -> None:
        """add() 应记录步骤并返回链自身以支持链式调用。"""

        @task("步骤1")
        def step1(ctx: TaskContext) -> dict:
            return {"step": 1}

        chain = TaskChain()
        result = chain.add(step1, "步骤1")

        assert result is chain
        assert len(chain._steps) == 1
        assert chain._steps[0]["name"] == "步骤1"

    def test_chain_on_success(self) -> None:
        """on_success() 应注册成功回调并返回链自身。"""

        def success_handler(success: bool, results: dict[str, Any]) -> None:
            pass

        chain = TaskChain()
        result = chain.on_success(success_handler)

        assert result is chain
        assert chain._on_success_callback is success_handler

    def test_chain_on_error(self) -> None:
        """on_error() 应注册失败回调并返回链自身。"""

        def error_handler(results: dict[str, Any]) -> None:
            pass

        chain = TaskChain()
        result = chain.on_error(error_handler)

        assert result is chain
        assert chain._on_error_callback is error_handler

    def test_chain_fluent_api(self) -> None:
        """add/on_success/on_error 连缀成流式调用后应得到两步任务链。"""

        @task("步骤A")
        def step_a(ctx: TaskContext) -> dict:
            return {}

        @task("步骤B")
        def step_b(ctx: TaskContext) -> dict:
            return {}

        chain = (
            TaskChain()
            .add(step_a, "步骤A")
            .add(step_b, "步骤B")
            .on_success(lambda s, r: None)
            .on_error(lambda r: None)
        )

        assert len(chain._steps) == 2


class TestTaskChainExecute:
    """TaskChain.execute() 集成测试：异步顺序执行、失败中断与安全关闭。"""

    def test_chain_execute_sequential_success(self, qtbot: QtBot) -> None:
        """三个步骤顺序执行成功后，on_success 应收到各步骤的完整结果。"""
        _ensure_qapp()

        @task("步骤1")
        def step1(ctx: TaskContext) -> dict:
            ctx.log("执行步骤1")
            return {"step": 1}

        @task("步骤2")
        def step2(ctx: TaskContext) -> dict:
            ctx.log("执行步骤2")
            return {"step": 2}

        @task("步骤3")
        def step3(ctx: TaskContext) -> dict:
            ctx.log("执行步骤3")
            return {"step": 3}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_success(success: bool, results: dict[str, Any]) -> None:
            captured["success"] = success
            captured["results"] = results
            done.set()

        chain = (
            TaskChain()
            .add(step1, "步骤1")
            .add(step2, "步骤2")
            .add(step3, "步骤3")
            .on_success(on_success)
        )

        executor = chain.execute()

        assert executor is not None
        try:
            # 回调经 Qt 信号（QueuedConnection）投递到主线程，
            # 必须边泵事件循环边轮询，否则 done 永远不会被置位
            timeout = 10.0
            elapsed = 0.0
            interval = 0.05
            while not done.is_set() and elapsed < timeout:
                QApplication.processEvents()
                time.sleep(interval)
                elapsed += interval

            assert done.is_set(), "on_success 回调未在超时内触发"
            assert captured["success"] is True
            assert "步骤1" in captured["results"]
            assert "步骤2" in captured["results"]
            assert "步骤3" in captured["results"]
            assert captured["results"]["步骤1"]["step"] == 1
            assert captured["results"]["步骤2"]["step"] == 2
            assert captured["results"]["步骤3"]["step"] == 3
        finally:
            executor.shutdown(wait=False)

    def test_chain_execute_failure_breaks_chain(self, qtbot: QtBot) -> None:
        """中间步骤抛异常时应触发 on_error，后续步骤不再执行。"""
        _ensure_qapp()

        @task("成功步骤")
        def step1(ctx: TaskContext) -> dict:
            ctx.log("执行成功步骤")
            return {"ok": True}

        @task("失败步骤")
        def step2(ctx: TaskContext) -> dict:
            ctx.log("执行失败步骤")
            raise ValueError("故意失败")

        @task("不应执行")
        def step3(ctx: TaskContext) -> dict:
            ctx.log("此任务不应被执行")
            return {"step": 3}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_error(results: dict[str, Any]) -> None:
            captured["results"] = results
            done.set()

        chain = (
            TaskChain()
            .add(step1, "成功步骤")
            .add(step2, "失败步骤")
            .add(step3, "不应执行")
            .on_error(on_error)
        )

        executor = chain.execute()

        assert executor is not None
        try:
            timeout = 10.0
            elapsed = 0.0
            interval = 0.05
            while not done.is_set() and elapsed < timeout:
                QApplication.processEvents()
                time.sleep(interval)
                elapsed += interval

            assert done.is_set(), "on_error 回调未在超时内触发"
            # 成功步骤的结果应被记录
            assert "成功步骤" in captured["results"]
            # 失败步骤应包含错误信息
            assert "失败步骤" in captured["results"]
            assert "error" in captured["results"]["失败步骤"]
            # 第三个任务不应被执行：其结果不应出现在 results 中
            assert "不应执行" not in captured["results"]
        finally:
            executor.shutdown(wait=False)

    def test_chain_execute_empty_steps(self) -> None:
        """空任务链 execute() 不创建 executor，直接同步回调 on_success。"""
        _ensure_qapp()

        captured: dict[str, Any] = {}

        def on_success(success: bool, results: dict[str, Any]) -> None:
            captured["success"] = success
            captured["results"] = results

        chain = TaskChain().on_success(on_success)

        result = chain.execute()

        # 空步骤链不创建 executor，直接同步回调
        assert result is None
        assert captured["success"] is True
        assert captured["results"] == {}

    def test_chain_execute_breaks_on_chain_break(self, qtbot: QtBot) -> None:
        """步骤返回 chain_break 时提前成功终止，跳过剩余步骤（回归 C2）"""
        _ensure_qapp()

        executed = []

        @task("条件检查")
        def step1(ctx: TaskContext) -> dict:
            executed.append("条件检查")
            return {"need_work": False, CHAIN_BREAK_KEY: True}

        @task("不应执行")
        def step2(ctx: TaskContext) -> dict:
            executed.append("不应执行")
            return {"step": 2}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_success(success: bool, results: dict[str, Any]) -> None:
            captured["success"] = success
            captured["results"] = results
            done.set()

        chain = TaskChain().add(step1, "条件检查").add(step2, "不应执行").on_success(on_success)

        executor = chain.execute()

        assert executor is not None
        try:
            timeout = 10.0
            elapsed = 0.0
            while not done.is_set() and elapsed < timeout:
                QApplication.processEvents()
                time.sleep(0.05)
                elapsed += 0.05

            assert done.is_set(), "on_success 回调未在超时内触发"
            # chain_break 属于"成功"终止：success=True，但后续步骤未运行
            assert captured["success"] is True
            assert executed == ["条件检查"]
            assert "条件检查" in captured["results"]
            assert "不应执行" not in captured["results"]
        finally:
            executor.shutdown(wait=False)

    def test_chain_shutdown_during_execution_no_crash(self, qtbot: QtBot) -> None:
        """链执行中 shutdown 后运行中任务完成不再触发提交（回归 C5）"""
        _ensure_qapp()

        started = threading.Event()

        @task("慢步骤")
        def slow_step(ctx: TaskContext) -> dict:
            started.set()
            time.sleep(0.3)
            return {"ok": True}

        @task("后续步骤")
        def follow(ctx: TaskContext) -> dict:
            return {"step": 2}

        done = threading.Event()

        def on_complete(success: bool, results: dict[str, Any]) -> None:
            done.set()

        chain = TaskChain().add(slow_step, "慢步骤").add(follow, "后续步骤").on_success(on_complete)
        executor = chain.execute()
        assert executor is not None
        assert started.wait(timeout=5)
        # 运行中直接关闭：断开链信号，任务完成信号不得再触发链推进
        executor.shutdown(wait=False)
        for _ in range(20):
            QApplication.processEvents()
            time.sleep(0.05)
        # 未崩溃即通过；完成回调不应触发（链信号已断开）
        assert not done.is_set()


class TestTimeoutOverride:
    """链级超时覆盖测试：TaskChain.add(timeout=...) / submit(timeout_override=...)
    覆盖 @task 装饰器的静态超时，以及限时任务与单线程池的互斥守卫（回归 F01/F20）。"""

    def test_chain_timeout_override_triggers_error(self, qtbot: QtBot) -> None:
        """add(timeout=0.2) 覆盖 func.timeout=30：超期后链以 error 结束且 error_msg 含"超时"。"""
        _ensure_qapp()

        @task("限时任务", timeout=30)
        def timed_step(ctx: TaskContext) -> dict:
            # 分片睡眠并轮询取消标志：超时触发后 ctx.cancel() 令任务尽快退出，
            # 不让测试工作线程真的睡满 5s
            deadline = time.time() + 5
            while time.time() < deadline and not ctx.is_cancelled():
                time.sleep(0.05)
            return {"done": True}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_error(results: dict[str, Any]) -> None:
            captured["results"] = results
            done.set()

        chain = TaskChain().add(timed_step, "限时任务", timeout=0.2).on_error(on_error)

        executor = chain.execute()

        assert executor is not None
        try:
            elapsed = 0.0
            while not done.is_set() and elapsed < 10.0:
                QApplication.processEvents()
                time.sleep(0.05)
                elapsed += 0.05

            assert done.is_set(), "on_error 回调未在超时内触发"
            results = captured["results"]
            assert "限时任务" in results
            assert "超时" in results["限时任务"]["error"]
        finally:
            executor.shutdown(wait=False)

    def test_chain_timeout_none_override_disables_timeout(self, qtbot: QtBot) -> None:
        """add(timeout=None) 显式不限时：覆盖 func.timeout=0.1，慢任务（0.5s）仍成功。"""
        _ensure_qapp()

        @task("慢任务", timeout=0.1)
        def slow_step(ctx: TaskContext) -> dict:
            time.sleep(0.5)
            return {"done": True}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_success(success: bool, results: dict[str, Any]) -> None:
            captured["success"] = success
            captured["results"] = results
            done.set()

        chain = TaskChain().add(slow_step, "慢任务", timeout=None).on_success(on_success)

        executor = chain.execute()

        assert executor is not None
        try:
            elapsed = 0.0
            while not done.is_set() and elapsed < 10.0:
                QApplication.processEvents()
                time.sleep(0.05)
                elapsed += 0.05

            assert done.is_set(), "on_success 回调未在超时内触发"
            assert captured["success"] is True
            assert captured["results"]["慢任务"]["done"] is True
        finally:
            executor.shutdown(wait=False)

    def test_submit_timed_task_to_single_worker_pool_raises(self) -> None:
        """限时任务提交到 max_workers=1 线程池应同步 raise RuntimeError（F20 守卫）。"""
        executor = TaskExecutor(max_workers=1)

        @task("限时任务", timeout=10)
        def timed_task(ctx: TaskContext) -> dict:
            return {}

        with pytest.raises(RuntimeError, match="2 个工作线程"):
            executor.submit(timed_task, "限时任务")
        executor.shutdown(wait=False)

    def test_chain_timed_task_with_single_worker_ends_with_error(self, qtbot: QtBot) -> None:
        """max_workers=1 的链上提交限时任务：守卫异常被捕获，链以 error 结束而非逃逸。"""
        _ensure_qapp()

        @task("限时步骤", timeout=10)
        def timed_step(ctx: TaskContext) -> dict:
            return {"done": True}

        done = threading.Event()
        captured: dict[str, Any] = {}

        def on_error(results: dict[str, Any]) -> None:
            captured["results"] = results
            done.set()

        executor = TaskExecutor(max_workers=1)
        chain = TaskChain().add(timed_step, "限时步骤").on_error(on_error)
        chain.execute(executor)

        # 守卫在 _execute_chain_next 内同步触发并按失败终止链，
        # 回调无需事件循环泵即应已完成
        assert done.is_set()
        results = captured["results"]
        assert "限时步骤" in results
        assert "线程池" in results["限时步骤"]["error"]
        executor.shutdown(wait=False)


class TestTaskChainStepNames:
    """TaskChain.step_names：按添加顺序暴露步骤名，供 GUI 显示"第 N/M 步"。"""

    def test_step_names_follows_add_order(self) -> None:
        """多个步骤按 add 顺序返回名称。"""
        chain = TaskChain()
        chain.add(lambda ctx: None, name="第一步")
        chain.add(lambda ctx: None, name="第二步")
        assert chain.step_names == ["第一步", "第二步"]

    def test_step_names_defaults_to_task_decorator_name(self) -> None:
        """未显式传 name 时取 @task 装饰器上的名字。"""

        @task("默认名")
        def _step(ctx: TaskContext) -> None:
            pass

        chain = TaskChain().add(_step)
        assert chain.step_names == ["默认名"]

    def test_step_names_empty_chain(self) -> None:
        """空链返回空列表（不抛异常）。"""
        assert TaskChain().step_names == []

    def test_step_names_returns_copy(self) -> None:
        """返回新列表：调用方修改不影响链内部状态。"""
        chain = TaskChain().add(lambda ctx: None, name="A")
        names = chain.step_names
        names.append("污染")
        assert chain.step_names == ["A"]
