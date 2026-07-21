"""
关机操作模块（仅Windows）

提供定时关机设置和取消功能。
"""

import subprocess

from infra.logging import error, info


def cancel_shutdown() -> bool:
    """
    取消之前设置的关机任务

    执行 Windows shutdown /a 命令，取消任何待执行的关机任务。
    如果没有待执行的关机任务，此命令不会产生错误。

    Returns:
        bool: True 表示取消成功（或无待执行任务），False 表示取消失败
    """
    result = subprocess.run(["shutdown", "/a"], capture_output=True, timeout=10)
    # returncode 1119 表示没有待取消的关机任务，不算错误
    if result.returncode != 0 and result.returncode != 1119:
        error(
            "business",
            f"取消关机任务失败 (returncode={result.returncode}): {result.stderr.decode(errors='ignore')}",
        )
        return False
    info("business", "已尝试取消之前的关机任务（如果有）")
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
    result = subprocess.run(["shutdown", "/s", "/t", str(seconds)], capture_output=True, timeout=10)
    if result.returncode != 0:
        error(
            "business",
            f"设置关机任务失败 (returncode={result.returncode}): {result.stderr.decode(errors='ignore')}",
        )
        return False
    info("business", f"已设置在 {seconds} 秒后自动关机")
    return True
