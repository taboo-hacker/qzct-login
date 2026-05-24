import datetime
import json
import os
import re
import subprocess
import time
import xml.sax.saxutils

import requests
from requests.exceptions import RequestException

from concurrency import TaskContext, task
from constants import CAMPUS_LOGIN_CONFIG, CAMPUS_LOGIN_HEADERS, CONFIG_DIR
from exceptions import (
    CampusAuthError,
    CampusNetworkError,
    JSONPParseError,
    WiFiConnectionError,
    WiFiProfileError,
)
from infrastructure import error, info
from system_core import ISP_MAPPING, get_config_snapshot, should_work_today


def _sanitize(msg: str) -> str:
    """移除日志中可能出现的密码明文"""
    return re.sub(r"user_password=[^&]+", "user_password=***", str(msg))


# ==========================================
# 自动关机模块（仅Windows）
# ==========================================
def cancel_shutdown():
    """
    取消之前设置的关机任务

    执行 Windows shutdown /a 命令，取消任何待执行的关机任务。
    如果没有待执行的关机任务，此命令不会产生错误。
    """
    subprocess.run(["shutdown", "/a"], capture_output=True)
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
    subprocess.run(["shutdown", "/s", "/t", str(seconds)], capture_output=True)
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
            ["netsh", "wlan", "show", "interfaces"], encoding="gbk", errors="ignore"
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


def _wifi_profile_exists(wifi_name: str) -> bool:
    """检查 Windows 是否已保存该 WiFi 的 profile。

    若已存在，可直接 connect 而不需要再写入明文密码文件。

    Args:
        wifi_name (str): WiFi 网络名称（SSID）

    Returns:
        bool: True 表示已存在 profile，False 表示不存在
    """
    try:
        result = subprocess.check_output(
            ["netsh", "wlan", "show", "profile"], encoding="gbk", errors="ignore"
        )
        return wifi_name in result
    except subprocess.CalledProcessError:
        return False


def _do_connect_wifi(wifi_name: str, password: str) -> None:
    """实际执行 WiFi 连接，失败时 raise WiFiError 子类。

    分离的内部函数：相比 ``return False``，结构化异常能告诉调用方
    *为什么* 失败（profile 写入失败 / netsh 调用失败 / 连接超时），便于
    将来 UI 层做不同提示，或测试层 assertRaises。
    """
    if _wifi_profile_exists(wifi_name):
        info("business", f"使用已有 WiFi profile：{wifi_name}")
    else:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp_path = os.path.join(CONFIG_DIR, f".wifi_profile_{os.getpid()}.xml")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(create_windows_wifi_profile(wifi_name, password))
            info("business", "创建临时 WiFi profile")

            try:
                subprocess.run(
                    ["netsh", "wlan", "add", "profile", f"filename={tmp_path}", "user=all"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as e:
                raise WiFiProfileError(f"加载 WiFi profile 失败：{wifi_name}", str(e)) from e
        finally:
            # netsh add 完成后密码已入 Windows 凭据存储，临时文件无需保留——
            # 立即删除，缩短明文密码在磁盘上停留的时间窗口。
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    info("business", "已清理临时 profile 文件")
                except OSError as e:
                    error("business", f"清理临时文件失败：{e}")

    info("business", f"发起WiFi连接请求：{wifi_name}")
    try:
        subprocess.run(
            ["netsh", "wlan", "connect", "name=" + wifi_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        raise WiFiConnectionError(f"WiFi 连接命令失败：{wifi_name}", str(e)) from e

    info("business", "等待WiFi连接稳定...")
    time.sleep(5)

    if not is_wifi_connected(wifi_name):
        raise WiFiConnectionError(f"WiFi 已发起连接但未稳定连上：{wifi_name}")


def connect_wifi(wifi_name: str, password: str) -> bool:
    """
    连接到指定的WiFi网络（向后兼容包装：捕获异常并返回 bool）

    内部使用 ``_do_connect_wifi`` 抛结构化异常；本函数为旧调用方
    （UI、测试）保留 ``bool`` 返回。新代码建议直接调用 ``_do_connect_wifi``。

    Args:
        wifi_name (str): WiFi网络名称
        password (str): WiFi密码

    Returns:
        bool: True表示连接成功（或已连接），False表示连接失败
    """
    try:
        _do_connect_wifi(wifi_name, password)
        info("business", f"WiFi连接成功：{wifi_name}")
        return True
    except WiFiProfileError as e:
        error("business", f"WiFi profile 异常：{e}")
        return False
    except WiFiConnectionError as e:
        error("business", f"WiFi连接失败：{e}")
        return False
    except Exception as e:
        error("business", f"WiFi连接异常：{e}")
        return False


def auto_connect_wifi(cfg=None):
    """
    自动连接WiFi（使用全局配置）

    从全局配置读取WiFi信息，尝试自动连接。
    包含重试逻辑，直到连接成功或达到最大重试次数。

    Args:
        cfg (dict, optional): 配置字典快照，默认使用 get_config_snapshot()

    Returns:
        bool: True表示连接成功，False表示连接失败
    """
    if cfg is None:
        cfg = get_config_snapshot()
    wifi_name = cfg.get("WIFI_NAME", "")
    wifi_password = cfg.get("WIFI_PASSWORD", "")
    max_retry = cfg.get("MAX_WIFI_RETRY", 10)
    retry_interval = cfg.get("RETRY_INTERVAL", 5)

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
            # 指数退避：1s → 2s → 4s → 8s → ... 上限 60s
            delay = min(retry_interval * (2 ** (retry_count - 1)), 60)
            info("business", f"等待{delay}秒后重试...")
            time.sleep(delay)

    error("business", f"超过{max_retry}次重试，WiFi连接失败")
    return False


# ==========================================
# 校园网登录模块
# ==========================================
def parse_jsonp(jsonp_text: str, callback: str) -> dict:
    """
    解析JSONP格式的响应数据

    使用字符串切片定位 callback( 和最后一个 )，比正则简洁可靠。

    Args:
        jsonp_text (str): JSONP格式的响应文本
        callback (str): JSONP回调函数名称，如 "dr1004"

    Returns:
        dict: 解析后的字典数据

    Raises:
        JSONPParseError: JSONP 格式不合法或解析失败
    """
    prefix = f"{callback}("
    start = jsonp_text.find(prefix)
    end = jsonp_text.rfind(")")
    if start == -1 or end == -1 or end <= start + len(prefix):
        raise JSONPParseError("JSONP格式解析失败", jsonp_text)
    try:
        return json.loads(jsonp_text[start + len(prefix) : end])
    except json.JSONDecodeError as e:
        raise JSONPParseError(f"JSON 解析失败：{e}", jsonp_text) from e


def campus_login(cfg=None) -> bool:
    """
    校园网登录函数（向后兼容包装：捕获异常并返回 bool）

    内部分类抛出：
    - CampusNetworkError：网络层失败（超时、不可达、协议错误）
    - JSONPParseError：服务器返回格式异常
    - CampusAuthError：账号/密码错误，认证失败

    Args:
        cfg (dict, optional): 配置字典快照，默认使用 get_config_snapshot()

    Returns:
        bool: True 表示登录成功，False 表示登录失败
    """
    if cfg is None:
        cfg = get_config_snapshot()
    isp_type = cfg.get("ISP_TYPE", "telecom")
    isp_suffix = ISP_MAPPING.get(isp_type, "@telecom")

    callback = CAMPUS_LOGIN_CONFIG["callback"]
    login_url = CAMPUS_LOGIN_CONFIG["login_url"]

    params = {
        "callback": callback,
        "login_method": "1",
        "user_account": f"{cfg.get('USERNAME', '')}{isp_suffix}",
        "user_password": cfg.get("PASSWORD", ""),
        "wlan_user_ip": cfg.get("WAN_IP", ""),
        "wlan_user_ipv6": "",
        "wlan_user_mac": "",
        "wlan_ac_ip": "",
        "wlan_ac_name": "",
        "jsVersion": CAMPUS_LOGIN_CONFIG["js_version"],
        "terminal_type": "1",
        "lang": "zh",
        "v": CAMPUS_LOGIN_CONFIG["version"],
    }

    headers = {**CAMPUS_LOGIN_HEADERS, "Referer": CAMPUS_LOGIN_CONFIG["referer"]}

    # 校园网认证服务器通常使用自签名证书，无法验证链
    info("business", "注意：SSL证书验证已禁用（校园网自签名证书）")

    try:
        with requests.Session() as session:
            info("business", f"开始发送登录请求到 {login_url}")

            # timeout=(connect, read)：3秒内必须建立 TCP 连接（区分网络不可达），
            # 一旦连上则允许服务器最多 10 秒响应（区分服务器慢）。
            try:
                response = session.get(
                    url=login_url,
                    params=params,
                    headers=headers,
                    verify=False,
                    timeout=(3, 10),
                )
            except RequestException as e:
                raise CampusNetworkError("校园网请求失败", _sanitize(str(e))) from e

            response.encoding = "utf-8"
            info("business", f"登录请求返回状态码：{response.status_code}")

            result = parse_jsonp(response.text, callback)

            if result.get("ret_code") == 0 or result.get("result") == 1:
                info("business", f"登录成功：{result.get('msg', '登录成功')}")
                return True

            raise CampusAuthError(
                "校园网认证失败", _sanitize(result.get("msg", "未知错误"))
            )

    except CampusAuthError as e:
        error("business", f"登录失败：{e}", exc_info=False)
        return False
    except CampusNetworkError as e:
        error("business", f"网络请求异常：{e}")
        return False
    except JSONPParseError as e:
        error("business", f"响应解析异常：{e}")
        return False
    except Exception as e:
        error("business", f"登录过程发生未知异常：{_sanitize(e)}")
        return False


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
        cfg = get_config_snapshot()
        shutdown_hour = cfg.get("SHUTDOWN_HOUR", 23)
        shutdown_min = cfg.get("SHUTDOWN_MIN", 0)
        shutdown_time = datetime.datetime.combine(today, datetime.time(shutdown_hour, shutdown_min))
        now = datetime.datetime.now()

        if now >= shutdown_time:
            info(
                "business",
                f"当前时间已过今日关机时间（{shutdown_hour:02d}:{shutdown_min:02d}），不再设置关机",
            )
        else:
            seconds = int((shutdown_time - now).total_seconds())
            if seconds > 0:
                set_shutdown_timer(seconds)
                info(
                    "business",
                    f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）",
                )
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

    login_ok = campus_login()
    if login_ok:
        ctx.log("校园网认证系统登录成功")
        ctx.set_progress(100)
        return {"login_successful": True}
    else:
        ctx.log("校园网登录失败，请检查账号密码或网络")
        return {"login_successful": False, "error": "登录返回失败"}


@task("设置定时关机", timeout=10)
def task_set_shutdown(ctx: TaskContext, check_date=None) -> dict:
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
                set_shutdown_timer(seconds)
                ctx.log(
                    f"已设置定时关机，将在 {shutdown_hour:02d}:{shutdown_min:02d} 自动关机（{seconds}秒后）"
                )
                ctx.set_progress(100)
                return {"shutdown_set": True, "seconds": seconds}
            else:
                ctx.log("关机时间计算无效，无法设置关机")
                return {"shutdown_set": False, "reason": "invalid_time"}
    except Exception as e:
        ctx.log(f"设置关机异常：{e}")
        return {"shutdown_set": False, "error": str(e)}
