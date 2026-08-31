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
            time.sleep(10)
            return {}

        executor.submit(long_task, "取消测试")
        executor.cancel_all()

        # 验证所有 context 的 cancel 标志已设置
        # （加锁读取，避免与工作线程修改contexts 的竞争）
        with executor._lock:
            for ctx in executor._contexts.values():
                assert ctx.is_cancelled()
        executor.shutdown(wait=False)


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
