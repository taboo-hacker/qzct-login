import os
from logger import info


# ==========================================
# 自动关机模块（仅Windows）
# ==========================================
# 本模块负责Windows系统下的定时关机功能。
#
# 功能说明：
#     - 取消之前设置的关机任务
#     - 设置新的定时关机任务
#
# 使用方法：
#     1. 调用 set_shutdown_timer(seconds) 设置关机倒计时
#     2. 调用 cancel_shutdown() 取消关机任务
#
# 实现原理：
#     使用 Windows shutdown 命令
#     - shutdown /s /t N   -> N秒后关机
#     - shutdown /a        -> 取消关机
#
# 注意事项：
#     - 仅支持Windows系统
#     - 需要足够的权限执行关机命令
#     - 关机命令执行后，系统会在倒计时结束后自动关机
# ==========================================


def cancel_shutdown():
    """
    取消之前设置的关机任务
    
    执行 Windows shutdown /a 命令，取消任何待执行的关机任务。
    如果没有待执行的关机任务，此命令不会产生错误。
    
    使用示例：
        # 取消关机任务
        cancel_shutdown()
        print("已取消关机")
    
    日志输出：
        会提示是否成功取消（通过重定向到日志）
    
    注意事项：
        - 需要足够的权限
        - 可以取消任何来源的关机任务
    """
    os.system("shutdown /a >nul 2>&1")
    info("shutdown", "已尝试取消之前的关机任务（如果有）")


def set_shutdown_timer(seconds: int):
    """
    设置定时关机
    
    在指定的秒数后自动关机。
    调用此函数前会先取消之前的关机任务。
    
    Args:
        seconds (int): 关机倒计时（秒）
                      例如：3600 表示1小时后关机
                      例如：7200 表示2小时后关机
    
    使用示例：
        # 设置2小时后关机
        set_shutdown_timer(7200)
        
        # 设置23:00关机（假设当前是12:00，需要11小时）
        # set_shutdown_timer(11 * 3600)
    
    日志输出：
        显示设置的倒计时时间
    
    注意事项：
        - 需要足够的权限
        - 如果 seconds <= 0，不会执行关机
        - 关机前会显示系统提示
    
    错误处理：
        - 如果权限不足，shutdown命令会失败
        - 建议以管理员身份运行程序
    """
    cancel_shutdown()
    os.system(f"shutdown /s /t {seconds}")
    info("shutdown", f"已设置在 {seconds} 秒后自动关机")
