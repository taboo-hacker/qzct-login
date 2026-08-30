"""
异常定义模块

定义项目中使用的自定义异常类，提供更精细的异常处理。

设计思路：
    所有业务异常继承 QZCTError（携带 message + 可选 details），
    便于调用方按异常类型区分失败原因（网络不通 / 认证失败 / 响应异常），
    而不是解析字符串。内部实现抛结构化异常，向后兼容包装层
    （connect_wifi / campus_login）捕获后转为 bool 返回值给 UI。

异常层级：

    QZCTError
    ├── WiFiError                WiFi 操作基础异常
    │   ├── WiFiConnectionError  连接失败/超时/被取消
    │   └── WiFiProfileError     profile 写入或 netsh add 失败
    └── CampusLoginError         校园网登录基础异常
        ├── CampusNetworkError   网络层失败（请求不可达/超时）
        ├── CampusAuthError      账号密码错误（认证被拒）
        └── CampusResponseError  响应异常
            └── JSONPParseError  JSONP 响应解析失败
"""


class QZCTError(Exception):
    """QZCT 项目基础异常类

    Attributes:
        message: 面向用户的错误概述
        details: 可选补充信息（如原始错误文本、服务器响应片段）
    """

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        # str(e) 输出 "message - details"，便于直接写入日志
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


# ==========================================
# WiFi 相关异常（由 services/wifi.py 抛出）
# ==========================================
class WiFiError(QZCTError):
    """WiFi 操作基础异常"""

    pass


class WiFiConnectionError(WiFiError):
    """WiFi 连接失败异常（连接超时 / 未稳定连上 / 连接被取消）"""

    pass


class WiFiProfileError(WiFiError):
    """WiFi 配置文件异常（临时 profile 写入失败 / netsh add profile 失败）"""

    pass


# ==========================================
# 校园网登录相关异常（由 services/campus_login.py 抛出）
# ==========================================
class CampusLoginError(QZCTError):
    """校园网登录基础异常"""

    pass


class CampusNetworkError(CampusLoginError):
    """校园网网络异常（DNS/网关不可达、连接超时等请求层失败）"""

    pass


class CampusAuthError(CampusLoginError):
    """校园网认证失败异常（服务器明确拒绝：账号密码错误 / 已欠费等）"""

    pass


class CampusResponseError(CampusLoginError):
    """校园网响应解析异常（服务器有响应但内容不符合预期）"""

    pass


class JSONPParseError(CampusResponseError):
    """JSONP 解析异常

    Attributes:
        response_text: 服务器原始响应文本（截断至 500 字符），用于日志排查
    """

    def __init__(self, message: str, response_text: str | None = None) -> None:
        self.response_text = response_text[:500] if response_text else None
        super().__init__(message, self.response_text)
