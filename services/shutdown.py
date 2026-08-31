"""
关机操作模块（仅Windows）

提供定时关机设置和取消功能。

实现说明：
    直接调用系统 shutdown 命令（参数列表方式，无 shell 拼接）。
    - 设置：shutdown /s /t <秒>   —— 到点关机，提前 5 分钟弹系统提示
    - 取消：shutdown /a           —— 中止待执行的关机任务
    程序重启后设置的关机任务依然有效（由 Windows 调度），
    所以每次设置前先取消旧任务，避免叠加多个关机倒计时。
"""

import subprocess

from core.constants import SHUTDOWN_CMD_TIMEOUT_SEC, SUBPROCESS_NO_WINDOW
from infra.logging import error, info


def cancel_shutdown() -> bool:
    """
    取消之前设置的关机任务

    执行 Windows shutdown /a 命令，取消任何待执行的关机任务。
    如果没有待执行的关机任务，此命令不会产生错误。

    Returns:
        bool: True 表示取消成功（或无待执行任务），False 表示取消失败
    """
    try:
        result = subprocess.run(
            ["shutdown", "/a"],
            capture_output=True,
            timeout=SHUTDOWN_CMD_TIMEOUT_SEC,
            creationflags=SUBPROCESS_NO_WINDOW,
        )
    except (subprocess.SubprocessError, OSError) as e:
        error("services.shutdown", f"取消关机任务异常: {e}")
        return False
    # returncode 1119 表示没有待取消的关机任务，不算错误
    if result.returncode != 0 and result.returncode != 1119:
        error(
            "services.shutdown",
            f"取消关机任务失败 (returncode={result.returncode}): {result.stderr.decode(errors='ignore')}",
        )
        return False
    info("services.shutdown", "已尝试取消之前的关机任务（如果有）")
    return True


def set_shutdown_timer(seconds: int) -> bool:
    """
    设置定时关机

    在指定的秒数后自动关机。
    调用此函数前会先取消之前的关机任务。

    Args:
        seconds (int): 关机倒计时（秒）

    Returns:
        bool: True 表示设置成功，False 表示设置失败
    """
    cancel_shutdown()
    try:
        result = subprocess.run(
            ["shutdown", "/s", "/t", str(seconds)],
            capture_output=True,
            timeout=SHUTDOWN_CMD_TIMEOUT_SEC,
            creationflags=SUBPROCESS_NO_WINDOW,
        )
    except (subprocess.SubprocessError, OSError) as e:
        error("services.shutdown", f"设置关机任务异常: {e}")
        return False
    if result.returncode != 0:
        error(
            "services.shutdown",
            f"设置关机任务失败 (returncode={result.returncode}): {result.stderr.decode(errors='ignore')}",
        )
        return False
    info("services.shutdown", f"已设置在 {seconds} 秒后自动关机")
    return True
