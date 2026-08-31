"""
校园网登录模块

提供 JSONP 解析、校园网认证登录等功能。
"""

import json
import re
from typing import Any

import requests
from requests.exceptions import RequestException

from core.config import get_config_snapshot
from core.constants import CAMPUS_LOGIN_CONFIG, CAMPUS_LOGIN_HEADERS, ISP_MAPPING
from core.exceptions import CampusAuthError, CampusNetworkError, JSONPParseError
from infra.logging import error, info


def _sanitize(msg: str) -> str:
    """移除日志中可能出现的密码明文"""
    result = re.sub(r"user_password=[^&]+", "user_password=***", str(msg))
    result = re.sub(
        r"user_account=([^&]{0,2})[^&]*",
        lambda m: f"user_account={m.group(1)}***" if m.group(1) else "user_account=***",
        result,
    )
    return result


def parse_jsonp(jsonp_text: str, callback: str) -> dict[str, Any]:
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
        return dict(json.loads(jsonp_text[start + len(prefix) : end]))
    except json.JSONDecodeError as e:
        raise JSONPParseError(f"JSON 解析失败：{e}", jsonp_text) from e


def campus_login(cfg: dict[str, Any] | None = None) -> bool:
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
    isp_suffix = ISP_MAPPING.get(isp_type, ISP_MAPPING["telecom"])[0]

    callback: str = CAMPUS_LOGIN_CONFIG["callback"]
    login_url: str = CAMPUS_LOGIN_CONFIG["login_url"]

    params = {
        "callback": callback,
        "login_method": "1",
        # 账号拼接运营商后缀：如 "20230001@telecom"，网关按后缀路由认证
        "user_account": f"{cfg.get('USERNAME', '')}{isp_suffix}",
        "user_password": cfg.get("PASSWORD", ""),
        "wlan_user_ip": cfg.get("WAN_IP", ""),
        # 以下字段网关不校验，保留门户页默认值即可
        "wlan_user_ipv6": "",
        "wlan_user_mac": "",
        "wlan_ac_ip": "",
        "wlan_ac_name": "",
        "jsVersion": CAMPUS_LOGIN_CONFIG["js_version"],
        "terminal_type": "1",
        "lang": "zh",
        "v": CAMPUS_LOGIN_CONFIG["version"],
    }

    headers: dict[str, str] = {
        **CAMPUS_LOGIN_HEADERS,
        "Referer": str(CAMPUS_LOGIN_CONFIG["referer"]),
    }

    try:
        with requests.Session() as session:
            info("services.campus_login", f"开始发送登录请求到 {login_url}")

            # timeout=(connect, read)：3秒内必须建立 TCP 连接（区分网络不可达），
            # 一旦连上则允许服务器最多 10 秒响应（区分服务器慢）。
            try:
                response = session.post(
                    url=login_url,
                    data=params,
                    headers=headers,
                    timeout=(3, 10),
                )
            except RequestException as e:
                raise CampusNetworkError("校园网请求失败", _sanitize(str(e))) from e

            response.encoding = "utf-8"
            info("services.campus_login", f"登录请求返回状态码：{response.status_code}")

            result = parse_jsonp(response.text, callback)

            ret_code = result.get("ret_code")
            # 兼容服务器返回 int 0 或 str "0"
            if (
                ret_code == 0
                or ret_code == "0"
                or result.get("result") == 1
                or result.get("result") == "1"
            ):
                info("services.campus_login", f"登录成功：{result.get('msg', '登录成功')}")
                return True

            raise CampusAuthError("校园网认证失败", _sanitize(result.get("msg", "未知错误")))

    except CampusAuthError as e:
        error("services.campus_login", f"登录失败：{e}", exc_info=False)
        return False
    except CampusNetworkError as e:
        error("services.campus_login", f"网络请求异常：{e}")
        return False
    except JSONPParseError as e:
        error("services.campus_login", f"响应解析异常：{e}")
        return False
    except Exception as e:
        error("services.campus_login", f"登录过程发生未知异常：{_sanitize(str(e))}")
        return False
