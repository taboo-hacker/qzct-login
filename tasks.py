import datetime
from config import global_config
from date_rules import should_work_today
from wifi import auto_connect_wifi
from campus_login import campus_login
from shutdown import set_shutdown_timer
from logger import info, error


# ==========================================
# 业务逻辑模块
# ==========================================
# 本模块负责协调执行完整的自动化任务流程：
# 1. 检查执行条件
# 2. 连接WiFi网络
# 3. 登录校园网认证系统
# 4. 设置定时关机
#
# 任务执行条件：
#     - 仅在 should_work_today() 返回 True 时执行
#     - 节假日自动跳过
#     - 调休上班日强制执行
#
# 注意事项：
#     - WiFi连接和校园网登录是独立的步骤
#     - 即使WiFi连接失败，也会尝试登录（可能已连接）
#     - 关机时间可配置，默认为每天23:00
# ==========================================


def run_tasks_once():
    """
    执行一次完整的自动化任务
    
    执行以下步骤：
        1. 检查今天是否需要执行任务（根据日期规则）
        2. 连接WiFi网络（如果需要）
        3. 登录校园网认证系统
        4. 设置定时关机
    
    任务执行条件（优先级从高到低）：
        1. 调休上班日 - 强制执行
        2. 自定义工作日时间段 - 强制执行
        3. 自定义假期时间段 - 强制不执行
        4. 基础节假日 - 不执行
        5. 每周执行日（默认周一至周五）- 执行
    
    错误处理：
        - WiFi连接失败：记录错误信息，继续尝试登录
        - 登录失败：记录错误信息
        - 关机时间已过：不设置关机任务
    
    日志输出：
        - 任务开始/结束标记
        - 当前日期和执行状态
        - 每一步的执行结果
    
    使用示例：
        # 手动执行一次任务
        run_tasks_once()
        
        # 程序启动时自动执行
        QTimer.singleShot(100, run_tasks_once)
    """
    info("tasks", "开始执行完整任务链")
    
    today = datetime.date.today()
    info("tasks", f"当前日期：{today}")
    
    # 步骤1：检查执行条件
    info("tasks", "正在检查执行条件...")
    need_work = should_work_today()
    
    if not need_work:
        info("tasks", "今天无需执行任务（节假日或周末）")
        return
    
    info("tasks", "今天需要执行任务，开始执行流程")
    
    # 步骤2：连接WiFi
    info("tasks", "开始连接WiFi网络")
    try:
        auto_connect_wifi()
        info("tasks", "WiFi网络连接成功")
    except TimeoutError as e:
        error("tasks", f"WiFi连接超时：{e}")
    except Exception as e:
        error("tasks", f"WiFi连接异常：{e}")
    
    # 步骤3：登录校园网
    info("tasks", "开始登录校园网认证系统")
    try:
        campus_login()
        info("tasks", "校园网认证系统登录成功")
    except Exception as e:
        error("tasks", f"校园网登录异常：{e}")
    
    # 步骤4：设置定时关机
    info("tasks", "开始设置定时关机")
    
    try:
        shutdown_hour = global_config["SHUTDOWN_HOUR"]
        shutdown_min = global_config["SHUTDOWN_MIN"]
        shutdown_time = datetime.datetime.combine(
            today, datetime.time(shutdown_hour, shutdown_min)
        )
        now = datetime.datetime.now()
        
        if now >= shutdown_time:
            info("tasks", f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机")
        else:
            seconds = int((shutdown_time - now).total_seconds())
            if seconds > 0:
                set_shutdown_timer(seconds)
                info("tasks", f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）")
            else:
                error("tasks", "关机时间计算无效，无法设置关机", exc_info=False)
    except Exception as e:
        error("tasks", f"设置关机异常：{e}")
    
    info("tasks", "完整任务链执行完成")
