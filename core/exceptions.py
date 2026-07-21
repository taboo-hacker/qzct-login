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


# ==========================================
# 配置相关异常
# ==========================================
class ConfigError(QZCTError):
    """配置相关异常"""

    pass


class ConfigLoadError(ConfigError):
    """配置加载异常"""

    pass


class ConfigSaveError(ConfigError):
    """配置保存异常"""

    pass


class ConfigValidationError(ConfigError):
    """配置验证异常"""

    pass


# ==========================================
# 加密相关异常
# ==========================================
class EncryptionError(QZCTError):
    """加密相关异常"""

    pass


class EncryptionKeyError(EncryptionError):
    """加密密钥异常"""

    pass


class DecryptionError(EncryptionError):
    """解密失败异常"""

    pass


class MasterPasswordError(EncryptionError):
    """主密码异常"""

    pass


# ==========================================
# 任务相关异常
# ==========================================
class TaskError(QZCTError):
    """任务执行异常"""

    pass


# ==========================================
# 关机相关异常
# ==========================================
class ShutdownError(QZCTError):
    """关机操作异常"""

    pass


class DateRuleError(QZCTError):
    """日期规则异常"""

    pass
