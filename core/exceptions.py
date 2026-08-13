"""
异常定义模块

定义项目中使用的自定义异常类，提供更精细的异常处理。
"""


class QZCTError(Exception):
    """QZCT 项目基础异常类"""

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


# ==========================================
# WiFi 相关异常
# ==========================================
class WiFiError(QZCTError):
    """WiFi 操作基础异常"""

    pass


class WiFiConnectionError(WiFiError):
    """WiFi 连接失败异常"""

    pass


class WiFiProfileError(WiFiError):
    """WiFi 配置文件异常"""

    pass


# ==========================================
# 校园网登录相关异常
# ==========================================
class CampusLoginError(QZCTError):
    """校园网登录基础异常"""

    pass


class CampusNetworkError(CampusLoginError):
    """校园网网络异常"""

    pass


class CampusAuthError(CampusLoginError):
    """校园网认证失败异常"""

    pass


class CampusResponseError(CampusLoginError):
    """校园网响应解析异常"""

    pass


class JSONPParseError(CampusResponseError):
    """JSONP 解析异常"""

    def __init__(self, message: str, response_text: str | None = None) -> None:
        self.response_text = response_text[:500] if response_text else None
        super().__init__(message, self.response_text)
