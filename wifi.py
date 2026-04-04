import os
import time
import subprocess
from config import global_config
from logger import info, error


# ==========================================
# WiFi连接模块（仅Windows）
# ==========================================
# 本模块负责Windows系统下的WiFi自动连接功能。
#
# 功能说明：
#     - 检测当前WiFi连接状态
#     - 创建WiFi配置文件（XML格式）
#     - 自动连接指定的WiFi网络
#     - 支持WPA2-PSK加密
#
# 使用方法：
#     1. 配置WIFI_NAME和WIFI_PASSWORD
#     2. 调用auto_connect_wifi()自动连接
#
# 注意事项：
#     - 仅支持Windows系统
#     - 需要WiFi适配器支持
#     - 配置文件为临时文件，连接成功后自动删除
#
# 重试策略：
#     - 最大重试次数：MAX_WIFI_RETRY（默认10次）
#     - 重试间隔：RETRY_INTERVAL（默认5秒）
# ==========================================


def is_wifi_connected(wifi_name: str) -> bool:
    """
    检查是否已连接到指定的WiFi网络
    
    使用netsh命令查询当前网络接口状态，判断是否已连接目标WiFi。
    
    Args:
        wifi_name (str): 要检查的WiFi名称（SSID）
    
    Returns:
        bool: True表示已连接，False表示未连接
    
    实现原理：
        执行 netsh wlan show interfaces 命令
        检查输出中是否包含目标WiFi名称
    
    使用示例：
        if is_wifi_connected("qzct-student_5G"):
            print("已连接到WiFi")
        else:
            print("未连接")
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
    
    生成符合Windows WLANProfile schema的XML配置文件。
    配置文件包含WiFi的SSID、加密方式和密码等信息。
    
    Args:
        wifi_name (str): WiFi网络名称（SSID）
        password (str): WiFi连接密码
    
    Returns:
        str: XML格式的WiFi配置文件内容
    
    加密方式：
        - 认证：WPA2PSK
        - 加密：AES
    
    使用示例：
        xml = create_windows_wifi_profile("MyWiFi", "password123")
        with open("profile.xml", "w") as f:
            f.write(xml)
    """
    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{wifi_name}</name>
    <SSIDConfig>
        <SSID>
            <name>{wifi_name}</name>
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
                <keyMaterial>{password}</keyMaterial>
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
    
    执行以下步骤：
        1. 创建临时WiFi配置文件
        2. 导入配置文件到系统
        3. 发起连接请求
        4. 清理临时文件
    
    Args:
        wifi_name (str): WiFi网络名称
        password (str): WiFi密码
    
    Returns:
        bool: True表示连接成功（或已连接），False表示连接失败
    
    错误处理：
        - CalledProcessError：命令执行失败
        - Exception：其他异常
    
    使用示例：
        if connect_wifi("qzct-student_5G", "password"):
            print("连接成功")
        else:
            print("连接失败")
    """
    temp_file = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(create_windows_wifi_profile(wifi_name, password))
            temp_file = f.name

        info("wifi", f"创建临时WiFi配置文件：{temp_file}")

        # 导入WiFi配置文件
        info("wifi", "导入WiFi配置文件到系统")
        subprocess.run(
            ["netsh", "wlan", "add", "profile", f"filename={temp_file}", "user=all"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 发起连接请求
        info("wifi", f"发起WiFi连接请求：{wifi_name}")
        subprocess.run(
            ["netsh", "wlan", "connect", "name=" + wifi_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
            info("wifi", f"清理临时配置文件：{temp_file}")
        
        # 等待连接稳定
        info("wifi", "等待WiFi连接稳定...")
        time.sleep(5)
        
        connected = is_wifi_connected(wifi_name)
        if connected:
            info("wifi", f"WiFi连接成功：{wifi_name}")
        else:
            error("wifi", f"WiFi连接失败：{wifi_name}")
        return connected
    except subprocess.CalledProcessError as e:
        error("wifi", f"WiFi连接命令执行失败：{str(e)}")
        return False
    except Exception as e:
        error("wifi", f"WiFi连接异常：{str(e)}")
        return False
    finally:
        # 确保临时文件被清理
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                info("wifi", f"清理临时配置文件：{temp_file}")
            except Exception as e:
                error("wifi", f"清理临时文件失败：{str(e)}")


def auto_connect_wifi():
    """
    自动连接WiFi（使用全局配置）
    
    从全局配置读取WiFi信息，尝试自动连接。
    包含重试逻辑，直到连接成功或达到最大重试次数。
    
    配置项依赖：
        - WIFI_NAME：WiFi网络名称
        - WIFI_PASSWORD：WiFi密码
        - MAX_WIFI_RETRY：最大重试次数
        - RETRY_INTERVAL：重试间隔（秒）
    
    抛出异常：
        TimeoutError：超过最大重试次数仍未连接
    
    使用示例：
        try:
            auto_connect_wifi()
            print("WiFi连接成功")
        except TimeoutError as e:
            print(f"WiFi连接失败：{e}")
    
    日志输出：
        - 开始尝试连接WiFi
        - 第N次尝试连接
        - 连接成功/失败状态
    """
    wifi_name = global_config["WIFI_NAME"]
    wifi_password = global_config["WIFI_PASSWORD"]
    max_retry = global_config["MAX_WIFI_RETRY"]
    retry_interval = global_config["RETRY_INTERVAL"]

    info("wifi", f"开始自动连接WiFi：{wifi_name}")
    info("wifi", f"最大重试次数：{max_retry}，重试间隔：{retry_interval}秒")

    retry_count = 0
    while retry_count < max_retry:
        if is_wifi_connected(wifi_name):
            info("wifi", f"WiFi已连接：{wifi_name}")
            return True
        
        retry_count += 1
        info("wifi", f"第{retry_count}次尝试连接WiFi：{wifi_name}")
        
        connect_wifi(wifi_name, wifi_password)
        
        if retry_count < max_retry:
            info("wifi", f"等待{retry_interval}秒后重试...")
            time.sleep(retry_interval)
    
    error("wifi", f"超过{max_retry}次重试，WiFi连接失败")
    raise TimeoutError(f"超过{max_retry}次重试，WiFi连接失败")
