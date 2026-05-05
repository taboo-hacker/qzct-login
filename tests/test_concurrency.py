"""
concurrency.py 模块测试

测试任务执行器、任务链、任务装饰器等功能。
"""
import time
from typing import Dict

from concurrency import (
    TaskChain,
    TaskContext,
    TaskExecutor,
    get_registered_task,
    list_registered_tasks,
    task,
)


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
        def sample_task(ctx: TaskContext) -> Dict:
            ctx.log("执行任务")
            return {"success": True}

        assert hasattr(sample_task, "task_name")
        assert sample_task.task_name == "测试任务"

    def test_task_registration(self):
        """测试任务注册"""

        @task("注册测试任务")
        def registered_task(ctx: TaskContext) -> Dict:
            return {}

        assert "注册测试任务" in list_registered_tasks()

    def test_task_execution(self):
        """测试任务执行"""

        @task("执行测试任务", timeout=30)
        def executing_task(ctx: TaskContext) -> Dict:
            ctx.log("开始执行")
            ctx.set_progress(50)
            return {"done": True}

        ctx = TaskContext("test")
        result = executing_task(ctx)

        assert result["done"] is True
        assert "开始执行" in ctx.get_logs()

    def test_get_registered_task(self):
        """测试获取已注册任务"""

        @task("获取测试任务")
        def task_to_get(ctx: TaskContext) -> Dict:
            return {}

        retrieved = get_registered_task("获取测试任务")
        assert retrieved is not None

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        result = get_registered_task("不存在的任务")
        assert result is None


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
        def simple_task(ctx: TaskContext) -> Dict:
            return {"result": "ok"}

        future = executor.submit(simple_task, "提交测试")
        assert future is not None

    def test_cancel_all(self):
        """测试取消所有任务"""
        executor = TaskExecutor()

        @task("取消测试")
        def long_task(ctx: TaskContext) -> Dict:
            time.sleep(10)
            return {}

        executor.submit(long_task, "取消测试")
        executor.cancel_all()

        assert executor._cancelled is True


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
        def step1(ctx: TaskContext) -> Dict:
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
        def step_a(ctx: TaskContext) -> Dict:
            return {}

        @task("步骤B")
        def step_b(ctx: TaskContext) -> Dict:
            return {}

        chain = (
            TaskChain()
            .add(step_a, "步骤A")
            .add(step_b, "步骤B")
            .on_success(lambda s, r: None)
            .on_error(lambda r: None)
        )

        assert len(chain._steps) == 2


class TestListRegisteredTasks:
    """列出已注册任务测试"""

    def test_list_registered_tasks(self):
        """测试列出已注册任务"""

        @task("列表测试任务")
        def list_test_task(ctx: TaskContext) -> Dict:
            return {}

        tasks = list_registered_tasks()
        assert isinstance(tasks, list)
        assert "列表测试任务" in tasks
