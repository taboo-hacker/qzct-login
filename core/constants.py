"""
常量配置模块

集中管理项目中的硬编码配置值：校园网认证协议参数与文件路径。

修改指引：
    - 换学校 / 认证服务器变更 → 改 CAMPUS_LOGIN_CONFIG；
    - 配置/日志文件位置 → 改下方"配置文件路径"（默认 ~/.qzct/）。
    WiFi 名称、账号密码等用户配置不在本模块，见 core/config.py 的 DEFAULT_CONFIG。
"""

import os
import subprocess
import sys
from typing import Any

# ==========================================
# 校园网登录配置
# ==========================================
# 锐捷 ePortal 认证协议参数（对应浏览器登录页发起的请求）。
# 抓包对照：登录页 F12 → Network → login 请求的 URL/表单字段。
# 值类型混合（str 协议参数 + int 预留超时），注解 dict[str, Any]
# 供消费方按需 narrow（campus_login 取 str 字段）。
CAMPUS_LOGIN_CONFIG: dict[str, Any] = {
    # 认证接口地址：192.168.51.2 为校园网认证网关，801 端口为 ePortal 服务。
    # 注意：当前为 http 明文协议（由网关决定），账号密码可被同网段截获；
    # 若网关启用 https，请勿关闭证书校验，改用 verify=<网关证书路径> 做证书固定。
    "login_url": "http://192.168.51.2:801/eportal/portal/login",
    # 请求 Referer 头，需与认证页同源，否则部分网关会拒绝
    "referer": "http://192.168.51.2/",
    # JSONP 回调函数名：服务器返回形如 dr1004({...}) 的脚本，parse_jsonp 据此定位
    "callback": "dr1004",
    # 认证页前端版本号参数（v），与门户 JS 版本对应
    "version": "7213",
    # 认证页 jsVersion 表单字段
    "js_version": "4.2.2",
    # 预留的请求超时秒数（实际超时在 campus_login 中用 (3, 10) 分段覆盖）
    "timeout": 15,
}

# 登录请求的 HTTP 头：伪装成主流浏览器，避免被网关的 UA 校验拦截
CAMPUS_LOGIN_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Connection": "keep-alive",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    ),
}

# ==========================================
# 配置文件路径
# ==========================================
# 统一存放在用户主目录 ~/.qzct/ 下，与程序安装位置解耦，
# 免安装运行/升级覆盖都不会丢失用户数据
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".qzct")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "qzct.log")

# ==========================================
# 子进程创建标志
# ==========================================
# 打包版为 console=False 的 GUI 进程，subprocess 调用控制台程序（netsh/shutdown）
# 默认会新开控制台窗口、在屏幕上闪黑框；CREATE_NO_WINDOW 抑制之。
# 该标志仅 Windows 存在，其他平台用 0 保持默认行为（跨平台测试可运行）。
SUBPROCESS_NO_WINDOW: int = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
