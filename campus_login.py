import re
import json
import requests
from requests.exceptions import RequestException
from config import global_config, ISP_MAPPING
from logger import info, error


# ==========================================
# 校园网登录模块
# ==========================================
# 本模块负责与校园网认证系统交互，实现自动登录功能。
#
# 支持的运营商：
#     - 电信（@telecom）
#     - 移动（@cmcc）
#     - 联通（@unicom）
#     - 校内资源（@local）
#
# 登录流程：
#     1. 构建登录请求参数（用户名、密码、运营商后缀等）
#     2. 发送GET请求到校园网认证服务器
#     3. 解析服务器返回的JSONP响应
#     4. 根据返回码判断登录结果
#
# 认证服务器地址：192.168.51.2:801
# 登录协议：HTTP GET + JSONP响应
#
# 响应码说明：
#     ret_code=0 或 result=1：登录成功
#     ret_code=1：登录失败（账号/密码错误）
#     其他：登录失败（查看msg了解原因）
# ==========================================


def parse_jsonp(jsonp_text: str, callback: str) -> dict:
    """
    解析JSONP格式的响应数据
    
    校园网服务器返回的是JSONP格式，需要提取其中的JSON数据。
    格式示例：dr1004({"ret_code": 0, "result": 1, "msg": "登录成功"})
    
    Args:
        jsonp_text (str): JSONP格式的响应文本
        callback (str): JSONP回调函数名称，如 "dr1004"
    
    Returns:
        dict: 解析后的字典数据
    
    Raises:
        ValueError: JSONP格式解析失败
    
    使用示例：
        response = session.get(url, params=params)
        result = parse_jsonp(response.text, "dr1004")
        if result["ret_code"] == 0:
            print("登录成功")
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
    
    配置项依赖：
        - USERNAME：校园网账号（学号）
        - PASSWORD：校园网密码
        - ISP_TYPE：运营商类型（cmcc/telecom/unicom）
        - WAN_IP：WAN IP地址（可选，程序会自动获取）
    
    登录请求参数：
        - callback：JSONP回调函数名
        - login_method：登录方式（1=用户名密码）
        - user_account：用户名 + 运营商后缀，如 "学号@telecom"
        - user_password：密码
        - wlan_user_ip：用户IP地址
        - wlan_user_mac：用户MAC地址（空）
        - wlan_ac_ip：AC IP地址（空）
        - wlan_ac_name：AC名称（空）
        - jsVersion：JS版本
        - terminal_type：终端类型（1=PC）
        - lang：语言
        - v：版本号
    
    Returns:
        None（结果通过print输出到日志）
    
    错误处理：
        - RequestException：网络请求异常
        - ValueError：响应解析异常
        - 其他异常：打印错误信息
    
    使用示例：
        # 在任务执行流程中调用
        campus_login()
    """
    # 步骤1：获取运营商后缀
    # 根据配置获取对应的运营商后缀
    # 例如：电信 -> @telecom，移动 -> @cmcc
    isp_type = global_config.get("ISP_TYPE", "telecom")
    isp_suffix = ISP_MAPPING.get(isp_type, "@telecom")

    # 步骤2：构建登录配置
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

    # HTTP请求头，模拟浏览器访问
    HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Referer": "http://192.168.51.2/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    }

    # 步骤3：发送登录请求
    session = requests.Session()
    try:
        # 构建查询参数
        params = {
            "callback": config["callback"],
            "login_method": "1",
            "user_account": f"{config['username']}{config['isp_suffix']}",
            "user_password": config["password"],
            "wlan_user_ip": config["wlan_user_ip"],
            "wlan_user_ipv6": "",
            "wlan_user_mac": config["wlan_user_mac"],
            "wlan_ac_ip": config["wlan_ac_name"],
            "wlan_ac_name": config["wlan_ac_name"],
            "jsVersion": "4.2.2",
            "terminal_type": "1",
            "lang": "zh",
            "v": config["v"]
        }

        info("campus_login", f"开始发送登录请求到 {config['login_url']}")
        
        # 发送GET请求
        response = session.get(
            url=config["login_url"],
            params=params,
            headers=HEADERS,
            verify=False,
            timeout=15
        )
        response.encoding = "utf-8"

        info("campus_login", f"登录请求返回状态码：{response.status_code}")

        # 步骤4：解析响应
        result = parse_jsonp(response.text, config["callback"])
        
        # 步骤5：判断登录结果
        if result.get("ret_code") == 0 or result.get("result") == 1:
            info("campus_login", f"登录成功：{result.get('msg', '登录成功')}")
        else:
            error("campus_login", f"登录失败：{result.get('msg', '未知错误')}", exc_info=False)

    except RequestException as e:
        error("campus_login", f"网络请求异常：{str(e)}")
    except ValueError as e:
        error("campus_login", f"响应解析异常：{str(e)}")
    except Exception as e:
        error("campus_login", f"登录过程发生未知异常：{str(e)}")
    finally:
        session.close()
        info("campus_login", "登录会话已关闭")
