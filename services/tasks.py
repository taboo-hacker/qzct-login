"""
任务链定义模块

定义主任务链的四个步骤（按顺序执行，任一步骤抛异常则链终止）：

    检查执行条件 → 连接WiFi → 登录校园网 → 设置定时关机

每个任务用 @task 装饰器注册（见 infra/concurrency.py），首参为 TaskContext。
任务返回 dict：结果会汇入链的 results（键为任务名），供完成回调判断；
返回 {"chain_break": True} 表示链以"成功"提前结束（今天无需执行的场景）。

组合位置见 gui/main_window.py 的 start_task_chain()。
"""

import datetime
from typing import Any

from core.config import get_config_snapshot
from core.date_rules import should_work_today
from infra.concurrency import CHAIN_BREAK_KEY, TaskContext, task
from services.campus_login import campus_login
from services.shutdown import set_shutdown_timer
from services.wifi import auto_connect_wifi


@task("检查执行条件", timeout=10)
def task_check_condition(
    ctx: TaskContext, check_date: datetime.date | None = None
) -> dict[str, Any]:
    """步骤 1：判断今天是否需要执行任务（节假日/周末则提前终止整条链）。

    Args:
        ctx: 任务上下文
        check_date: 待检查日期（默认今天；测试中用于注入固定日期）
    """
    ctx.log("正在检查执行条件...")
    today = check_date if check_date else datetime.date.today()
    ctx.log(f"当前日期：{today}")

    need_work = should_work_today(today)

    if not need_work:
        ctx.log("今天无需执行任务（节假日或周末）")
        # 提前成功终止任务链：跳过 WiFi 连接、校园网登录、定时关机
        return {"need_work": False, "date": today, CHAIN_BREAK_KEY: True}

    ctx.log("今天需要执行任务，开始执行流程")
    return {"need_work": True, "date": today}


@task("连接WiFi", timeout=120)
def task_connect_wifi(ctx: TaskContext) -> dict[str, Any]:
    """步骤 2：自动连接配置的 WiFi（含重试 + 指数退避，可协作取消）。

    超时给到 120s：最大重试 10 次 × 退避间隔（1+2+4+...封顶 60s）下
    最坏情况接近两分钟。
    """
    ctx.log("开始连接WiFi网络")

    # 传入取消检查回调：任务超时/取消时，重试循环与退避睡眠可协作式退出
    cfg = get_config_snapshot()
    wifi_connected = auto_connect_wifi(cfg, should_cancel=ctx.is_cancelled)
    if wifi_connected:
        ctx.log("WiFi网络连接成功")
        return {"wifi_connected": True}
    else:
        ctx.log("WiFi连接失败")
        return {"wifi_connected": False, "error": "连接失败"}


@task("登录校园网", timeout=30)
def task_campus_login(ctx: TaskContext) -> dict[str, Any]:
    """步骤 3：向认证网关发送 JSONP 登录请求。

    登录失败不抛异常（campus_login 内部已捕获并记日志），
    返回 login_successful=False 让链"正常走完"——失败详情看日志。
    """
    ctx.log("开始登录校园网认证系统")

    login_ok = campus_login()
    if login_ok:
        ctx.log("校园网认证系统登录成功")
        return {"login_successful": True}
    else:
        ctx.log("校园网登录失败，请检查账号密码或网络")
        return {"login_successful": False, "error": "登录返回失败"}


@task("设置定时关机", timeout=10)
def task_set_shutdown(ctx: TaskContext, check_date: datetime.date | None = None) -> dict[str, Any]:
    """步骤 4：按配置的 SHUTDOWN_HOUR/MIN 设置 Windows 定时关机。

    已过今日关机时间则跳过（例如中午开机时配置的是 0:30）；
    设置前会先取消已有关机任务（见 set_shutdown_timer）。
    """
    ctx.log("开始设置定时关机")

    cfg = get_config_snapshot()
    try:
        shutdown_hour = cfg.get("SHUTDOWN_HOUR", 23)
        shutdown_min = cfg.get("SHUTDOWN_MIN", 0)

        today = check_date if check_date else datetime.date.today()
        shutdown_time = datetime.datetime.combine(today, datetime.time(shutdown_hour, shutdown_min))
        now = datetime.datetime.now()

        if now >= shutdown_time:
            ctx.log(
                f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机"
            )
            return {"shutdown_set": False, "reason": "time_passed"}
        else:
            seconds = int((shutdown_time - now).total_seconds())
            if seconds > 0:
                success = set_shutdown_timer(seconds)
                if success:
                    ctx.log(
                        f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）"
                    )
                    return {"shutdown_set": True, "seconds": seconds}
                else:
                    ctx.log("关机命令执行失败，请检查系统权限")
                    return {"shutdown_set": False, "reason": "command_failed"}
            else:
                ctx.log("关机时间计算无效，无法设置关机")
                return {"shutdown_set": False, "reason": "invalid_time"}
    except Exception as e:
        ctx.log(f"设置关机异常：{e}")
        return {"shutdown_set": False, "error": str(e)}
