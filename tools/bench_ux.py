"""
UX 性能基准工具（开发者工具，不参与打包）

用于在 UX 优化前后采集**同一口径**的耗时数据，回答"用户是否真的感觉更流畅"。
所有指标均以"主线程被占用的时长"为核心——桌面 GUI 的卡顿几乎都来自
主线程被同步工作阻塞，而非算法复杂度。

指标口径：
    startup_ms      子进程冷启动到主窗口首帧可见（含解释器启动），中位数
    log_visible_ms  后台线程投递 N 条日志后，主线程把全部日志渲染可见的耗时
    theme_ms        连续切换主题 R 次，每次强制重绘的耗时
    calendar_ms     构建万年历视图 + 连续翻月，每次强制重绘的耗时

用法::

    python tools/bench_ux.py --out baseline.json
    python tools/bench_ux.py --out after.json
    python tools/bench_ux.py --compare baseline.json after.json

注意：必须在 offscreen 平台运行（脚本内部自动设置），无需真实显示器。
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# 以 `python tools/bench_ux.py` 运行时 sys.path[0] 是 tools/，需把仓库根加回，
# 才能以顶层包名导入 core/gui 等模块
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 单条日志样本：贴近真实 loguru sink 输出（带时间戳/级别/模块，以换行结尾）
_LOG_SAMPLE = "2026-01-01 00:00:00.000 | INFO     | infra.logging:info:42 - 测试日志行 {idx}\n"

# 渲染可见性轮询的兜底超时（秒），防止基准脚本自身挂死
_PUMP_TIMEOUT_SEC = 30.0


def _ensure_offscreen() -> None:
    """强制 offscreen 平台：基准不依赖显示器，且避免弹出真实窗口。"""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


def _ensure_app() -> Any:
    """创建或复用 QApplication。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    return app


def _isolated_env() -> dict[str, str]:
    """返回把用户主目录指向临时目录的环境变量。

    避免基准读取/污染真实用户的 ~/.qzct 配置，也让 MainWindow 的启动
    自动执行逻辑因"未配置账号"而跳过，不会触发真实网络任务。
    """
    env = dict(os.environ)
    home = os.environ.get("BENCH_HOME", "")
    if not home:
        import tempfile

        home = tempfile.mkdtemp(prefix="qzct-bench-")
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["QT_QPA_PLATFORM"] = "offscreen"
    return env


# ----------------------------------------------------------------------
# 指标 1：冷启动
# ----------------------------------------------------------------------


def _startup_child_code() -> str:
    """子进程启动脚本：导入 → 建主窗口 → 显示 → 泵事件，最后向原始 fd 写 READY。

    必须用 os.write(1, ...) 而非 print：MainWindow 初始化时会把 sys.stdout
    重定向到日志系统（StreamRedirector），print 的内容不会到达父进程管道。
    """
    return (
        "import os, sys\n"
        "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        f"sys.path.insert(0, r'{ROOT}')\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication([])\n"
        "from gui.main_window import MainWindow\n"
        "w = MainWindow()\n"
        "w.show()\n"
        "for _ in range(5):\n"
        "    app.processEvents()\n"
        "os.write(1, b'READY\\n')\n"
    )


def bench_startup(repeats: int = 5) -> float:
    """测量子进程冷启动到主窗口首帧的中位耗时（毫秒）。"""
    env = _isolated_env()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-c", _startup_child_code()],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            check=False,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if "READY" not in proc.stdout:
            raise RuntimeError(f"启动子进程未就绪：{proc.stderr[-500:]}")
        samples.append(elapsed_ms)
    return statistics.median(samples)


# ----------------------------------------------------------------------
# 指标 2：日志渲染可见耗时
# ----------------------------------------------------------------------


def bench_log_visible(count: int = 1500, repeats: int = 3) -> float:
    """测量后台线程投递 count 条日志后，主线程全部渲染可见的耗时（毫秒）。

    通过 QtLogSink 的真实跨线程路径投递（与生产一致），主线程用
    processEvents 泵事件，以"文档块数达到 count"作为全部可见的判据。
    """
    from gui.log_sink import QtLogSink
    from gui.styling.widgets import LogTextEdit

    app = _ensure_app()
    samples: list[float] = []
    for _ in range(repeats):
        widget = LogTextEdit()
        QtLogSink.set_gui_widget(widget)
        sink = QtLogSink.instance()

        def _producer(sink: Any = sink) -> None:
            for idx in range(count):
                sink.write(_LOG_SAMPLE.format(idx=idx))

        # 每条消息以换行结尾，插入后新增 1 个文本块；文档初始已有 1 个空块，
        # 因此 count 条全部可见的判据是 blockCount 达到 count + 1
        target_blocks = count + 1
        thread = threading.Thread(target=_producer, daemon=True)
        start = time.perf_counter()
        thread.start()
        deadline = start + _PUMP_TIMEOUT_SEC
        while widget.document().blockCount() < target_blocks and time.perf_counter() < deadline:
            app.processEvents()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        thread.join(timeout=5)
        if widget.document().blockCount() < target_blocks:
            raise RuntimeError("日志未在超时内全部可见")
        samples.append(elapsed_ms)
        widget.deleteLater()
        app.processEvents()
    return statistics.median(samples)


# ----------------------------------------------------------------------
# 指标 3：主题切换
# ----------------------------------------------------------------------


def bench_theme(toggles: int = 20, repeats: int = 3) -> float:
    """测量连续切换主题 toggles 次的总耗时（毫秒），每次后强制重绘。"""
    from gui.styling.theme_manager import ThemeManager

    app = _ensure_app()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        for idx in range(toggles):
            ThemeManager.set_theme("dark" if idx % 2 == 0 else "light")
            app.processEvents()
        samples.append((time.perf_counter() - start) * 1000.0)
    ThemeManager.set_theme("light")
    return statistics.median(samples)


# ----------------------------------------------------------------------
# 指标 4：万年历
# ----------------------------------------------------------------------


def bench_calendar(months: int = 12, repeats: int = 3) -> float:
    """测量构建万年历视图 + 连续翻 months 个月的总耗时（毫秒）。"""
    from PySide6.QtCore import QDate

    from gui.widgets.calendar_view import CalendarView

    app = _ensure_app()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        view = CalendarView()
        view.show()
        app.processEvents()
        calendar = view.calendar
        if calendar is None:
            raise RuntimeError("万年历视图未构建 QCalendarWidget")
        base = QDate(2026, 1, 1)
        for idx in range(months):
            calendar.setSelectedDate(base.addMonths(idx))
            app.processEvents()
        samples.append((time.perf_counter() - start) * 1000.0)
        view.deleteLater()
        app.processEvents()
    return statistics.median(samples)


# ----------------------------------------------------------------------
# 编排与输出
# ----------------------------------------------------------------------


def run_all() -> dict[str, float]:
    """执行全部指标并返回结果字典。"""
    _ensure_offscreen()
    results: dict[str, float] = {}
    results["startup_ms"] = bench_startup()
    results["log_visible_ms"] = bench_log_visible()
    results["theme_ms"] = bench_theme()
    results["calendar_ms"] = bench_calendar()
    return results


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def print_table(results: dict[str, float]) -> None:
    """打印单次结果表格。"""
    print(f"{'指标':<20}{'耗时(ms)':>12}")
    print("-" * 32)
    for key, value in results.items():
        print(f"{key:<20}{_fmt(value):>12}")


def compare(before: dict[str, float], after: dict[str, float]) -> None:
    """打印前后对比表格（含变化百分比）。"""
    print(f"{'指标':<20}{'优化前(ms)':>14}{'优化后(ms)':>14}{'变化':>12}")
    print("-" * 60)
    for key in before:
        if key not in after:
            continue
        old, new = before[key], after[key]
        delta = (new - old) / old * 100.0 if old else 0.0
        sign = "+" if delta > 0 else ""
        print(f"{key:<20}{_fmt(old):>14}{_fmt(new):>14}{sign + _fmt(delta) + '%':>12}")


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="qzct-login UX 性能基准")
    parser.add_argument("--out", help="把本次结果写入 JSON 文件")
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BEFORE", "AFTER"),
        help="对比两个 JSON 结果文件",
    )
    args = parser.parse_args()

    if args.compare:
        with open(args.compare[0], encoding="utf-8") as fh:
            before = json.load(fh)
        with open(args.compare[1], encoding="utf-8") as fh:
            after = json.load(fh)
        compare(before, after)
        return

    results = run_all()
    print_table(results)
    if args.out:
        Path(args.out).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n已写入 {args.out}")


if __name__ == "__main__":
    main()
