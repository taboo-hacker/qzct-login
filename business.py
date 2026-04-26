import os
import time
import re
import json
import requests
import subprocess
import datetime
import xml.sax.saxutils
from requests.exceptions import RequestException
from system_core import global_config, ISP_MAPPING, should_work_today
from infrastructure import info, error
from concurrency import task, TaskContext


# ==========================================
# 自动关机模块（仅Windows）
# ==========================================
def cancel_shutdown():
    """
    取消之前设置的关机任务
    
    执行 Windows shutdown /a 命令，取消任何待执行的关机任务。
    如果没有待执行的关机任务，此命令不会产生错误。
    """
    os.system("shutdown /a >nul 2>&1")
    info("business", "已尝试取消之前的关机任务（如果有）")


def set_shutdown_timer(seconds: int):
    """
    设置定时关机
    
    在指定的秒数后自动关机。
    调用此函数前会先取消之前的关机任务。
    
    Args:
        seconds (int): 关机倒计时（秒）
    """
    cancel_shutdown()
    os.system(f"shutdown /s /t {seconds}")
    info("business", f"已设置在 {seconds} 秒后自动关机")


# ==========================================
# WiFi连接模块（仅Windows）
# ==========================================
def is_wifi_connected(wifi_name: str) -> bool:
    """
    检查是否已连接到指定的WiFi网络
    
    Args:
        wifi_name (str): 要检查的WiFi名称（SSID）
    
    Returns:
        bool: True表示已连接，False表示未连接
    """
    try:
        result = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            encoding="gbk",
            errors="ignore"
        )
        return wifi_name in result
    except subprocess.CalledProcessError:
        return False


def create_windows_wifi_profile(wifi_name: str, password: str) -> str:
    """
    创建Windows WiFi配置文件（XML格式）
    
    Args:
        wifi_name (str): WiFi网络名称（SSID）
        password (str): WiFi连接密码
    
    Returns:
        str: XML格式的WiFi配置文件内容
    """
    escaped_wifi_name = xml.sax.saxutils.escape(wifi_name)
    escaped_password = xml.sax.saxutils.escape(password)
    
    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_wifi_name}</name>
    <SSIDConfig>
        <SSID>
            <name>{escaped_wifi_name}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
    <MacRandomization xmlns="http://www.microsoft.com/networking/WLAN/profile/v3">
        <enableRandomization>false</enableRandomization>
    </MacRandomization>
</WLANProfile>"""
    return profile_xml


def connect_wifi(wifi_name: str, password: str) -> bool:
    """
    连接到指定的WiFi网络
    
    Args:
        wifi_name (str): WiFi网络名称
        password (str): WiFi密码
    
    Returns:
        bool: True表示连接成功（或已连接），False表示连接失败
    """
    temp_file = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(create_windows_wifi_profile(wifi_name, password))
            temp_file = f.name

        info("business", f"创建临时WiFi配置文件：{temp_file}")

        subprocess.run(
            ["netsh", "wlan", "add", "profile", f"filename={temp_file}", "user=all"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        info("business", f"发起WiFi连接请求：{wifi_name}")
        subprocess.run(
            ["netsh", "wlan", "connect", "name=" + wifi_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
            info("business", f"清理临时配置文件：{temp_file}")
        
        info("business", "等待WiFi连接稳定...")
        time.sleep(5)
        
        connected = is_wifi_connected(wifi_name)
        if connected:
            info("business", f"WiFi连接成功：{wifi_name}")
        else:
            error("business", f"WiFi连接失败：{wifi_name}")
        return connected
    except subprocess.CalledProcessError as e:
        error("business", f"WiFi连接命令执行失败：{str(e)}")
        return False
    except Exception as e:
        error("business", f"WiFi连接异常：{str(e)}")
        return False
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                info("business", f"清理临时配置文件：{temp_file}")
            except Exception as e:
                error("business", f"清理临时文件失败：{str(e)}")


def auto_connect_wifi():
    """
    自动连接WiFi（使用全局配置）

    从全局配置读取WiFi信息，尝试自动连接。
    包含重试逻辑，直到连接成功或达到最大重试次数。

    Returns:
        bool: True表示连接成功，False表示连接失败
    """
    wifi_name = global_config["WIFI_NAME"]
    wifi_password = global_config["WIFI_PASSWORD"]
    max_retry = global_config["MAX_WIFI_RETRY"]
    retry_interval = global_config["RETRY_INTERVAL"]

    info("business", f"开始自动连接WiFi：{wifi_name}")
    info("business", f"最大重试次数：{max_retry}，重试间隔：{retry_interval}秒")

    retry_count = 0
    while retry_count < max_retry:
        if is_wifi_connected(wifi_name):
            info("business", f"WiFi已连接：{wifi_name}")
            return True

        retry_count += 1
        info("business", f"第{retry_count}次尝试连接WiFi：{wifi_name}")

        if connect_wifi(wifi_name, wifi_password):
            info("business", f"WiFi连接成功：{wifi_name}")
            return True

        if retry_count < max_retry:
            info("business", f"等待{retry_interval}秒后重试...")
            time.sleep(retry_interval)

    error("business", f"超过{max_retry}次重试，WiFi连接失败")
    return False


# ==========================================
# 校园网登录模块
# ==========================================
def parse_jsonp(jsonp_text: str, callback: str) -> dict:
    """
    解析JSONP格式的响应数据
    
    Args:
        jsonp_text (str): JSONP格式的响应文本
        callback (str): JSONP回调函数名称，如 "dr1004"
    
    Returns:
        dict: 解析后的字典数据
    """
    pattern = re.compile(f"{re.escape(callback)}\\((.*?)\\)")
    match = pattern.search(jsonp_text)
    if match:
        return json.loads(match.group(1))
    raise ValueError("JSONP格式解析失败，响应内容：" + jsonp_text[:100])


def campus_login():
    """
    校园网登录函数（使用全局配置）
    
    读取全局配置中的账号信息，构建登录请求并发送到校园网认证服务器。
    """
    isp_type = global_config.get("ISP_TYPE", "telecom")
    isp_suffix = ISP_MAPPING.get(isp_type, "@telecom")

    config = {
        "username": global_config["USERNAME"],
        "password": global_config["PASSWORD"],
        "isp_suffix": isp_suffix,
        "login_url": "http://192.168.51.2:801/eportal/portal/login",
        "wlan_user_ip": global_config["WAN_IP"],
        "wlan_user_mac": "",
        "wlan_ac_ip": "",
        "wlan_ac_name": "",
        "callback": "dr1004",
        "v": "7213"
    }

    HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Referer": "http://192.168.51.2/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    }

    session = requests.Session()
    try:
        params = {
            "callback": config["callback"],
            "login_method": "1",
            "user_account": f"{config['username']}{config['isp_suffix']}",
            "user_password": config["password"],
            "wlan_user_ip": config["wlan_user_ip"],
            "wlan_user_ipv6": "",
            "wlan_user_mac": config["wlan_user_mac"],
            "wlan_ac_ip": config["wlan_ac_ip"],
            "wlan_ac_name": config["wlan_ac_name"],
            "jsVersion": "4.2.2",
            "terminal_type": "1",
            "lang": "zh",
            "v": config["v"]
        }

        info("business", f"开始发送登录请求到 {config['login_url']}")
        
        response = session.get(
            url=config["login_url"],
            params=params,
            headers=HEADERS,
            verify=False,
            timeout=15
        )
        response.encoding = "utf-8"

        info("business", f"登录请求返回状态码：{response.status_code}")

        result = parse_jsonp(response.text, config["callback"])
        
        if result.get("ret_code") == 0 or result.get("result") == 1:
            info("business", f"登录成功：{result.get('msg', '登录成功')}")
        else:
            error("business", f"登录失败：{result.get('msg', '未知错误')}", exc_info=False)

    except RequestException as e:
        error("business", f"网络请求异常：{str(e)}")
    except ValueError as e:
        error("business", f"响应解析异常：{str(e)}")
    except Exception as e:
        error("business", f"登录过程发生未知异常：{str(e)}")
    finally:
        session.close()
        info("business", "登录会话已关闭")


# ==========================================
# 业务逻辑模块
# ==========================================
def run_tasks_once():
    """
    执行一次完整的自动化任务
    
    执行以下步骤：
        1. 检查今天是否需要执行任务（根据日期规则）
        2. 连接WiFi网络（如果需要）
        3. 登录校园网认证系统
        4. 设置定时关机
    """
    info("business", "开始执行完整任务链")
    
    today = datetime.date.today()
    info("business", f"当前日期：{today}")
    
    info("business", "正在检查执行条件...")
    need_work = should_work_today()
    
    if not need_work:
        info("business", "今天无需执行任务（节假日或周末）")
        return
    
    info("business", "今天需要执行任务，开始执行流程")
    
    info("business", "开始连接WiFi网络")
    wifi_connected = auto_connect_wifi()
    if wifi_connected:
        info("business", "WiFi网络连接成功")
    else:
        error("business", "WiFi连接失败，终止后续任务")
        return

    info("business", "开始登录校园网认证系统")
    try:
        campus_login()
        info("business", "校园网认证系统登录成功")
    except Exception as e:
        error("business", f"校园网登录异常：{e}")
    
    info("business", "开始设置定时关机")
    
    try:
        shutdown_hour = global_config["SHUTDOWN_HOUR"]
        shutdown_min = global_config["SHUTDOWN_MIN"]
        shutdown_time = datetime.datetime.combine(
            today, datetime.time(shutdown_hour, shutdown_min)
        )
        now = datetime.datetime.now()
        
        if now >= shutdown_time:
            info("business", f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机")
        else:
            seconds = int((shutdown_time - now).total_seconds())
            if seconds > 0:
                set_shutdown_timer(seconds)
                info("business", f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）")
            else:
                error("business", "关机时间计算无效，无法设置关机", exc_info=False)
    except Exception as e:
        error("business", f"设置关机异常：{e}")
    
    info("business", "完整任务链执行完成")


@task("检查执行条件", timeout=10)
def task_check_condition(ctx: TaskContext, check_date=None) -> dict:
    ctx.log("正在检查执行条件...")
    today = check_date if check_date else datetime.date.today()
    ctx.log(f"当前日期：{today}")
    
    need_work = should_work_today(today)
    
    if not need_work:
        ctx.log("今天无需执行任务（节假日或周末）")
        return {"need_work": False, "date": today}
    
    ctx.log("今天需要执行任务，开始执行流程")
    return {"need_work": True, "date": today}


@task("连接WiFi", timeout=120)
def task_connect_wifi(ctx: TaskContext) -> dict:
    ctx.log("开始连接WiFi网络")
    ctx.set_progress(10)

    wifi_connected = auto_connect_wifi()
    if wifi_connected:
        ctx.log("WiFi网络连接成功")
        ctx.set_progress(100)
        return {"wifi_connected": True}
    else:
        ctx.log("WiFi连接失败")
        return {"wifi_connected": False, "error": "连接失败"}


@task("登录校园网", timeout=30)
def task_campus_login(ctx: TaskContext) -> dict:
    ctx.log("开始登录校园网认证系统")
    ctx.set_progress(10)
    
    try:
        campus_login()
        ctx.log("校园网认证系统登录成功")
        ctx.set_progress(100)
        return {"login_successful": True}
    except Exception as e:
        ctx.log(f"校园网登录异常：{e}")
        return {"login_successful": False, "error": str(e)}


@task("设置定时关机", timeout=10)
def task_set_shutdown(ctx: TaskContext, check_date=None) -> dict:
    ctx.log("开始设置定时关机")
    
    try:
        shutdown_hour = global_config["SHUTDOWN_HOUR"]
        shutdown_min = global_config["SHUTDOWN_MIN"]
        
        today = check_date if check_date else datetime.date.today()
        shutdown_time = datetime.datetime.combine(
            today, datetime.time(shutdown_hour, shutdown_min)
        )
        now = datetime.datetime.now()
        
        if now >= shutdown_time:
            ctx.log(f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机")
            return {"shutdown_set": False, "reason": "time_passed"}
        else:
            seconds = int((shutdown_time - now).total_seconds())
            if seconds > 0:
                set_shutdown_timer(seconds)
                ctx.log(f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）")
                ctx.set_progress(100)
                return {"shutdown_set": True, "seconds": seconds}
            else:
                ctx.log("关机时间计算无效，无法设置关机")
                return {"shutdown_set": False, "reason": "invalid_time"}
    except Exception as e:
        ctx.log(f"设置关机异常：{e}")
        return {"shutdown_set": False, "error": str(e)}
