"""
concurrency.py 模块测试

测试任务执行器、任务链、任务装饰器等功能。
"""

import threading
import time

from PyQt5.QtWidgets import QApplication

from infra.concurrency import (
    CHAIN_BREAK_KEY,
    TaskChain,
    TaskContext,
    TaskExecutor,
    task,
)


def _ensure_qapp() -> QApplication:
    """确保存在 QApplication 实例（Qt 信号机制所必需）。"""
    return QApplication.instance() or QApplication([])


class TestTaskContext:
    """任务上下文测试"""

    def test_context_initialization(self):
        """测试上下文初始化"""
        ctx = TaskContext("test_task")

        assert ctx.task_name == "test_task"
        assert ctx._progress == 0
        assert ctx._cancelled is False
        assert ctx._logs == []

    def test_log(self):
        """测试日志记录"""
        ctx = TaskContext("test")
        ctx.log("message 1")
        ctx.log("message 2")

        assert len(ctx._logs) == 2
        assert ctx._logs[0] == "message 1"
        assert ctx._logs[1] == "message 2"

    def test_get_logs(self):
        """测试获取日志"""
        ctx = TaskContext("test")
        ctx.log("message")
        logs = ctx.get_logs()

        assert logs == ["message"]
        assert logs is not ctx._logs

    def test_set_progress(self):
        """测试设置进度"""
        ctx = TaskContext("test")

        ctx.set_progress(50)
        assert ctx._progress == 50

        ctx.set_progress(100)
        assert ctx._progress == 100

    def test_set_progress_bounds(self):
        """测试进度边界"""
        ctx = TaskContext("test")

        ctx.set_progress(-10)
        assert ctx._progress == 0

        ctx.set_progress(150)
        assert ctx._progress == 100

    def test_cancel(self):
        """测试取消任务"""
        ctx = TaskContext("test")

        assert ctx.is_cancelled() is False
        ctx.cancel()
        assert ctx.is_cancelled() is True


class TestTaskDecorator:
    """任务装饰器测试"""

    def test_task_decorator(self):
        """测试任务装饰器"""

        @task("测试任务")
        def sample_task(ctx: TaskContext) -> dict:
            ctx.log("执行任务")
            return {"success": True}

        assert hasattr(sample_task, "task_name")
        assert sample_task.task_name == "测试任务"

    def test_task_execution(self):
        """测试任务执行"""

        @task("执行测试任务", timeout=30)
        def executing_task(ctx: TaskContext) -> dict:
            ctx.log("开始执行")
            ctx.set_progress(50)
            return {"done": True}

        ctx = TaskContext("test")
        result = executing_task(ctx)

        assert result["done"] is True
        assert "开始执行" in ctx.get_logs()


class TestTaskExecutor:
    """任务执行器测试"""

    def test_executor_initialization(self):
        """测试执行器初始化"""
        executor = TaskExecutor()

        assert executor._max_workers > 0
        assert executor._tasks == {}
        assert executor._contexts == {}

    def test_executor_max_workers(self):
        """测试最大工作线程数"""
        executor = TaskExecutor(max_workers=4)
        assert executor.max_workers == 4

    def test_submit_task(self):
        """测试提交任务"""
        executor = TaskExecutor()

        @task("提交测试")
        def simple_task(ctx: TaskContext) -> dict:
            return {"result": "ok"}

        future = executor.submit(simple_task, "提交测试")
        assert future is not None

    def test_cancel_all(self):
        """测试取消所有任务"""
        executor = TaskExecutor()

        @task("取消测试")
        def long_task(ctx: TaskContext) -> dict:
            time.sleep(10)
            return {}

        executor.submit(long_task, "取消测试")
        executor.cancel_all()

        assert executor._cancelled is True
        # 验证所有 context 的 cancel 标志已设置
        with executor._lock:
            for ctx in executor._contexts.values():
                assert ctx.is_cancelled()
        executor.shutdown(wait=False)


class TestTaskChain:
    """任务链测试"""

    def test_chain_initialization(self):
        """测试任务链初始化"""
        chain = TaskChain()

        assert chain._steps == []
        assert chain._on_success_callback is None
        assert chain._on_error_callback is None

    def test_chain_add(self):
        """测试添加任务到链"""

        @task("步骤1")
        def step1(ctx: TaskContext) -> dict:
            return {"step": 1}

        chain = TaskChain()
        result = chain.add(step1, "步骤1")

        assert result is chain
        assert len(chain._steps) == 1
        assert chain._steps[0]["name"] == "步骤1"

    def test_chain_on_success(self):
        """测试成功回调"""

        def success_handler(success, results):
            pass

        chain = TaskChain()
        result = chain.on_success(success_handler)

        assert result is chain
        assert chain._on_success_callback is success_handler

    def test_chain_on_error(self):
        """测试错误回调"""

        def error_handler(results):
            pass

        chain = TaskChain()
        result = chain.on_error(error_handler)

        assert result is chain
        assert chain._on_error_callback is error_handler

    def test_chain_fluent_api(self):
        """测试流式 API"""

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
    """TaskChain.execute() 集成测试"""

    def test_chain_execute_sequential_success(self, qtbot):
        """测试多个任务顺序执行成功"""
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
        captured = {}

        def on_success(success, results):
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
        try:
            # 轮询事件循环，等待回调触发
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

    def test_chain_execute_failure_breaks_chain(self, qtbot):
        """测试任务失败后中断后续任务"""
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
        captured = {}

        def on_error(results):
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

    def test_chain_execute_empty_steps(self):
        """测试空任务链直接调用 on_success"""
        _ensure_qapp()

        captured = {}

        def on_success(success, results):
            captured["success"] = success
            captured["results"] = results

        chain = TaskChain().on_success(on_success)

        result = chain.execute()

        # 空步骤链不创建 executor，直接同步回调
        assert result is None
        assert captured["success"] is True
        assert captured["results"] == {}

    def test_chain_execute_breaks_on_chain_break(self, qtbot):
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
        captured = {}

        def on_success(success, results):
            captured["success"] = success
            captured["results"] = results
            done.set()

        chain = TaskChain().add(step1, "条件检查").add(step2, "不应执行").on_success(on_success)

        executor = chain.execute()
        try:
            timeout = 10.0
            elapsed = 0.0
            while not done.is_set() and elapsed < timeout:
                QApplication.processEvents()
                time.sleep(0.05)
                elapsed += 0.05

            assert done.is_set(), "on_success 回调未在超时内触发"
            assert captured["success"] is True
            assert executed == ["条件检查"]
            assert "条件检查" in captured["results"]
            assert "不应执行" not in captured["results"]
        finally:
            executor.shutdown(wait=False)

    def test_chain_shutdown_during_execution_no_crash(self, qtbot):
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

        def on_complete(success, results):
            done.set()

        chain = TaskChain().add(slow_step, "慢步骤").add(follow, "后续步骤").on_success(on_complete)
        executor = chain.execute()
        assert started.wait(timeout=5)
        # 运行中直接关闭：断开链信号，任务完成信号不得再触发链推进
        executor.shutdown(wait=False)
        for _ in range(20):
            QApplication.processEvents()
            time.sleep(0.05)
        # 未崩溃即通过；完成回调不应触发（链信号已断开）
        assert not done.is_set()
