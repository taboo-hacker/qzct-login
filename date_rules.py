import datetime
from config import global_config, WEEKDAY_MAPPING, DEFAULT_CONFIG
from utils import parse_date_str, is_date_in_period


# ==========================================
# 日期判断模块
# ==========================================
# 本模块负责判断今天是否需要执行任务。
# 根据中国节假日规则和自定义配置，决定自动化任务的执行时机。
#
# 判断优先级（从高到低）：
#     1. 调休上班日（COMPENSATORY_WORKDAYS）- 强制执行
#     2. 自定义工作日时间段（CUSTOM_WORKDAY_PERIODS）- 强制执行
#     3. 自定义假期时间段（CUSTOM_HOLIDAY_PERIODS）- 强制不执行
#     4. 基础节假日时间段（HOLIDAY_PERIODS）- 不执行
#     5. 每周执行日（WEEKLY_EXECUTE_DAYS）- 执行/不执行
#
# 日期格式：
#     - 假期时间段：{"name": "名称", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
#     - 调休上班日：["YYYY-MM-DD", ...]
#
# 使用方法：
#     if should_work_today():
#         执行自动化任务
# ==========================================


def should_work_today(check_date=None):
    """
    判断指定日期是否需要执行自动化任务
    
    根据日期规则配置，判断指定日期是否需要执行 WiFi连接 + 校园网登录 + 定时关机。
    
    优先级判断流程：
        1. 检查是否为调休上班日（最高优先级，强制执行）
        2. 如果启用自定义规则：
           - 检查是否在自定义工作日时间段（强制执行）
           - 检查是否在自定义假期时间段（强制不执行）
           - 检查每周执行日
        3. 如果使用默认规则：
           - 检查是否在基础节假日时间段
           - 检查每周执行日（周一至周五）
    
    Args:
        check_date (datetime.date, optional): 要检查的日期，默认为今天
    
    Returns:
        bool: True表示需要执行任务，False表示不需要执行
    
    使用示例：
        from date_rules import should_work_today
        
        # 检查今天
        if should_work_today():
            run_tasks_once()
        
        # 检查指定日期
        import datetime
        some_date = datetime.date(2025, 1, 1)
        if should_work_today(some_date):
            print("该日期需要执行任务")
    
    注意事项：
        - 调休上班日即使是周末也会强制执行
        - 自定义规则启用后会覆盖默认节假日
        - 每周执行日使用Python的weekday()，0=周一，6=周日
    """
    today = check_date if check_date is not None else datetime.date.today()
    date_rules = global_config.get("DATE_RULES", DEFAULT_CONFIG["DATE_RULES"])

    # 优先级1：检查调休上班日
    # 调休上班日优先级最高，即使是周末也强制执行
    # 例如：2025年春节调休，1月26日（周日）需要上班
    compensatory_days = [parse_date_str(d) for d in global_config.get("COMPENSATORY_WORKDAYS", []) if parse_date_str(d)]
    if today in compensatory_days:
        return True

    # 优先级2：如果启用自定义规则
    if date_rules.get("ENABLE_CUSTOM_RULE", False):
        # 2a：检查是否在自定义工作日时间段（强制执行）
        # 自定义工作日可以覆盖默认的节假日设置
        custom_work_periods = date_rules.get("CUSTOM_WORKDAY_PERIODS", [])
        for period in custom_work_periods:
            if is_date_in_period(today, period):
                return True

        # 2b：检查是否在自定义假期时间段（强制不执行）
        # 自定义假期可以覆盖默认的每周执行日设置
        custom_holiday_periods = date_rules.get("CUSTOM_HOLIDAY_PERIODS", [])
        for period in custom_holiday_periods:
            if is_date_in_period(today, period):
                return False

        # 2c：检查每周执行日
        # 根据配置的执行日列表判断
        weekday = today.weekday()  # 0=周一，6=周日
        weekly_execute_days = date_rules.get("WEEKLY_EXECUTE_DAYS", [0, 1, 2, 3, 4])
        if weekday in weekly_execute_days:
            return True
        else:
            return False

    # 优先级3：使用默认规则
    else:
        # 3a：检查是否在基础节假日时间段
        # 基础节假日包括：国务院官方节假日 + 高校寒暑假
        base_holiday_periods = global_config.get("HOLIDAY_PERIODS", [])
        for period in base_holiday_periods:
            if is_date_in_period(today, period):
                return False

        # 3b：检查每周执行日（默认周一至周五）
        weekday = today.weekday()
        weekly_execute_days = [0, 1, 2, 3, 4]  # 周一至周五
        if weekday in weekly_execute_days:
            return True
        else:
            return False
