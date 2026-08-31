"""
WiFi 连接模块（仅Windows）

提供 WiFi 连接状态检查、WiFi profile 创建、自动连接等功能。
"""

import os
import subprocess
import tempfile
import time
import xml.sax.saxutils
from collections.abc import Callable
from typing import Any

from core.config import get_config_snapshot
from core.constants import CONFIG_DIR, SUBPROCESS_NO_WINDOW
from core.exceptions import WiFiConnectionError, WiFiProfileError
from infra.logging import error, info

# 取消检查回调：返回 True 表示任务已被取消。用于长循环/睡眠中的协作式取消。
CancelCheck = Callable[[], bool] | None


def _interruptible_sleep(seconds: float, should_cancel: CancelCheck = None) -> bool:
    """可中断的睡眠：分片 sleep 并轮询取消标志。

    Args:
        seconds: 总睡眠时长（秒）
        should_cancel: 取消检查回调，None 表示不可取消

    Returns:
        bool: True 表示正常睡完，False 表示期间被取消
    """
    if should_cancel is None:
        time.sleep(seconds)
        return True
    remaining = seconds
    while remaining > 0:
        if should_cancel():
            return False
        step = min(0.5, remaining)
        time.sleep(step)
        remaining -= step
    return True


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
            errors="ignore",
            timeout=15,
            creationflags=SUBPROCESS_NO_WINDOW,
        )
        # 精确匹配 SSID，避免子串误判（如 "WiFi" 误匹配 "WiFi-5G"）
        for line in result.splitlines():
            stripped = line.strip()
            if stripped.startswith("SSID"):
                # 格式: "SSID : WiFi名称" 或 "    SSID : WiFi名称"
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip() == wifi_name:
                    return True
        return False
    except (subprocess.SubprocessError, OSError):
        # SubprocessError 覆盖调用失败/超时；OSError 覆盖 netsh 不存在（非 Windows）
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
            ["netsh", "wlan", "show", "profile"],
            encoding="gbk",
            errors="ignore",
            timeout=15,
            creationflags=SUBPROCESS_NO_WINDOW,
        )
        # 精确匹配 profile 名称，避免子串误判
        for line in result.splitlines():
            stripped = line.strip()
            if stripped.startswith("All User Profile") or stripped.startswith("所有用户配置文件"):
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip() == wifi_name:
                    return True
        return False
    except (subprocess.SubprocessError, OSError):
        return False


def _do_connect_wifi(wifi_name: str, password: str, should_cancel: CancelCheck = None) -> None:
    """实际执行 WiFi 连接，失败时 raise WiFiError 子类。

    分离的内部函数：相比 ``return False``，结构化异常能告诉调用方
    *为什么* 失败（profile 写入失败 / netsh 调用失败 / 连接超时），便于
    将来 UI 层做不同提示，或测试层 assertRaises。
    """
    if _wifi_profile_exists(wifi_name):
        info("services.wifi", f"使用已有 WiFi profile：{wifi_name}")
    else:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # 使用 tempfile 生成不可预测的临时文件路径，避免密码文件被猜测路径访问
        fd, tmp_path = tempfile.mkstemp(suffix=".xml", prefix=".wifi_profile_", dir=CONFIG_DIR)
        try:
            # 直接经 mkstemp 返回的 fd 写入：不 close 再重开，消除路径被抢占的竞态窗口
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(create_windows_wifi_profile(wifi_name, password))
            info("services.wifi", "创建临时 WiFi profile")

            try:
                subprocess.run(
                    ["netsh", "wlan", "add", "profile", f"filename={tmp_path}", "user=all"],
                    check=True,
                    capture_output=True,
                    timeout=15,
                    creationflags=SUBPROCESS_NO_WINDOW,
                )
            except subprocess.CalledProcessError as e:
                raise WiFiProfileError(f"加载 WiFi profile 失败：{wifi_name}", str(e)) from e
        finally:
            # netsh add 完成后密码已入 Windows 凭据存储，临时文件无需保留——
            # 立即删除，缩短明文密码在磁盘上停留的时间窗口。
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    info("services.wifi", "已清理临时 profile 文件")
                except OSError as e:
                    error("services.wifi", f"清理临时文件失败：{e}")

    info("services.wifi", f"发起WiFi连接请求：{wifi_name}")
    try:
        subprocess.run(
            ["netsh", "wlan", "connect", "name=" + wifi_name],
            check=False,
            capture_output=True,
            timeout=15,
            creationflags=SUBPROCESS_NO_WINDOW,
        )
    except subprocess.CalledProcessError as e:
        # netsh wlan connect 的 exit code 不可靠，连接正在建立时也可能返回 1
        # 不直接抛异常，继续走下面的连接验证
        info("services.wifi", f"netsh connect 返回非零退出码（可忽略）：{e.returncode}")

    info("services.wifi", "等待WiFi连接稳定...")
    if not _interruptible_sleep(5, should_cancel):
        raise WiFiConnectionError(f"WiFi 连接已取消：{wifi_name}")

    if not is_wifi_connected(wifi_name):
        raise WiFiConnectionError(f"WiFi 已发起连接但未稳定连上：{wifi_name}")


def connect_wifi(wifi_name: str, password: str, should_cancel: CancelCheck = None) -> bool:
    """
    连接到指定的WiFi网络（向后兼容包装：捕获异常并返回 bool）

    内部使用 ``_do_connect_wifi`` 抛结构化异常；本函数为旧调用方
    （UI、测试）保留 ``bool`` 返回。新代码建议直接调用 ``_do_connect_wifi``。

    Args:
        wifi_name (str): WiFi网络名称
        password (str): WiFi密码
        should_cancel: 取消检查回调，None 表示不可取消

    Returns:
        bool: True表示连接成功（或已连接），False表示连接失败
    """
    try:
        _do_connect_wifi(wifi_name, password, should_cancel)
        info("services.wifi", f"WiFi连接成功：{wifi_name}")
        return True
    except WiFiProfileError as e:
        error("services.wifi", f"WiFi profile 异常：{e}", exc_info=False)
        return False
    except WiFiConnectionError as e:
        error("services.wifi", f"WiFi连接失败：{e}", exc_info=False)
        return False
    except Exception as e:
        error("services.wifi", f"WiFi连接异常：{e}", exc_info=False)
        return False


def auto_connect_wifi(cfg: dict[str, Any] | None = None, should_cancel: CancelCheck = None) -> bool:
    """
    自动连接WiFi（使用全局配置）

    从全局配置读取WiFi信息，尝试自动连接。
    包含重试逻辑，直到连接成功或达到最大重试次数。
    重试间隔采用指数退避，退避睡眠可被 should_cancel 中断（协作式取消）。

    Args:
        cfg (dict, optional): 配置字典快照，默认使用 get_config_snapshot()
        should_cancel: 取消检查回调，None 表示不可取消

    Returns:
        bool: True表示连接成功，False表示连接失败
    """
    if cfg is None:
        cfg = get_config_snapshot()
    wifi_name = cfg.get("WIFI_NAME", "")
    wifi_password = cfg.get("WIFI_PASSWORD", "")
    max_retry = cfg.get("MAX_WIFI_RETRY", 10)
    retry_interval = cfg.get("RETRY_INTERVAL", 5)

    # 未配置 WiFi 名称（如仅用有线 + 校园网认证的用户）时直接跳过：
    # 连空 SSID 毫无意义，重试 10 次只会白白拖慢任务链约两分钟
    if not wifi_name:
        info("services.wifi", "未配置 WiFi 名称，跳过 WiFi 连接（可在设置中填写）")
        return False

    info("services.wifi", f"开始自动连接WiFi：{wifi_name}")
    info(
        "services.wifi", f"最大重试次数：{max_retry}，基础重试间隔：{retry_interval}秒（指数退避）"
    )

    retry_count = 0
    while retry_count < max_retry:
        if should_cancel is not None and should_cancel():
            info("services.wifi", "WiFi 自动连接已取消", exc_info=False)
            return False

        if is_wifi_connected(wifi_name):
            info("services.wifi", f"WiFi已连接：{wifi_name}")
            return True

        retry_count += 1
        info("services.wifi", f"第{retry_count}次尝试连接WiFi：{wifi_name}")

        if connect_wifi(wifi_name, wifi_password, should_cancel):
            info("services.wifi", f"WiFi连接成功：{wifi_name}")
            return True

        if retry_count < max_retry:
            # 指数退避：1s → 2s → 4s → 8s → ... 上限 60s
            delay = min(retry_interval * (2 ** (retry_count - 1)), 60)
            info("services.wifi", f"等待{delay}秒后重试...")
            if not _interruptible_sleep(delay, should_cancel):
                info("services.wifi", "WiFi 自动连接已取消", exc_info=False)
                return False

    error("services.wifi", f"超过{max_retry}次重试，WiFi连接失败", exc_info=False)
    return False
