"""
安全加密模块

提供基于主密码的密钥派生（PBKDF2）、数据加解密、密钥管理等功能。

本模块为纯函数模块，不依赖 PyQt5。所有需要 GUI 交互的弹窗逻辑
（如提示用户输入主密码）已上移到 ``gui/encryption_gui.py``，
通过回调函数注入到 ``load_and_update_encryption`` 等编排函数中。
"""

import base64
import getpass
import os
import sys
from collections.abc import Callable
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.constants import KEY_FILE, SALT_FILE
from infra.logging import error, info

MASTER_PASSWORD_KEY = "MASTER_PASSWORD"
ENCRYPTION_PREFIX = "ENC:"

# 回调类型约定（由 GUI 层注入）
PromptCallback = Callable[[], str]
ResetConfirmCallback = Callable[[str], bool]


def _restrict_file_permissions(filepath: str) -> None:
    """限制密钥文件权限，使其仅当前用户可读写。

    - POSIX 系统: chmod 0o600
    - Windows: 使用 icacls 移除除当前用户外的所有访问权限
    """
    try:
        if sys.platform == "win32":
            import subprocess

            # 移除继承的 ACE，仅保留当前用户完全控制
            subprocess.run(
                ["icacls", filepath, "/inheritance:r", "/grant:r", f"{getpass.getuser()}:F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        else:
            os.chmod(filepath, 0o600)
    except Exception as e:
        error("system_core", f"设置文件权限失败（非致命）: {e}")


def load_salt() -> bytes:
    """
    加载盐值

    Returns:
        bytes: 盐值
    """
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            return f.read()
    else:
        salt = os.urandom(16)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        _restrict_file_permissions(SALT_FILE)
        info("system_core", "生成新的盐值文件")
        return salt


def generate_derived_key_from_master_password(
    master_password: str, salt: bytes | None = None
) -> tuple[bytes, bytes]:
    """
    从主密码生成派生密钥

    PBKDF2 600k 迭代在后台线程执行，主线程用 QEventLoop 保持 UI 响应。
    如果 Qt 尚未初始化（CLI 环境），直接同步执行。

    Args:
        master_password: 主密码
        salt: 盐值，如为 None 则自动加载或生成

    Returns:
        tuple: (key, salt) 生成的派生密钥和使用的盐值
    """
    from concurrent.futures import ThreadPoolExecutor

    if salt is None:
        salt = load_salt()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_derive_key, master_password, salt)

        try:
            from PyQt5.QtCore import QEventLoop
            from PyQt5.QtWidgets import QApplication

            if QApplication.instance() is not None:
                loop = QEventLoop()
                future.add_done_callback(lambda _: loop.quit())
                if not future.done():
                    loop.exec()
            else:
                future.result()  # 无 Qt 环境，直接同步等待
        except ImportError:
            future.result()  # Qt 不可用，直接同步等待

        return future.result(), salt


def _do_derive_key(master_password: str, salt: bytes) -> bytes:
    """在后台线程执行 PBKDF2 密钥派生。"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def save_derived_key(key: bytes) -> None:
    """
    保存派生密钥

    Args:
        key: 派生密钥
    """
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    _restrict_file_permissions(KEY_FILE)
    info("system_core", "派生密钥已保存")


def load_derived_key() -> bytes | None:
    """
    加载派生密钥

    Returns:
        派生密钥，如果文件不存在则返回 None
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    return None


def encrypt_data(data: str, derived_key: bytes) -> str:
    """
    加密数据

    Args:
        data: 要加密的数据
        derived_key: 派生密钥

    Returns:
        加密后的数据（带 ENC: 前缀的 base64 编码）
    """
    if not data:
        return data
    f = Fernet(derived_key)
    encrypted = f.encrypt(data.encode())
    return ENCRYPTION_PREFIX + base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data: str, derived_key: bytes) -> str:
    """
    解密数据

    Args:
        encrypted_data: 加密的数据（带 ENC: 前缀的 base64 编码）
        derived_key: 派生密钥

    Returns:
        解密后的数据
    """
    if not encrypted_data:
        return encrypted_data
    # 兼容旧数据：无前缀的去掉前缀再解码
    raw = encrypted_data.removeprefix(ENCRYPTION_PREFIX)
    f = Fernet(derived_key)
    try:
        encrypted = base64.b64decode(raw.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        error("system_core", f"解密失败：{e}")
        raise


def is_encrypted(data: str) -> bool:
    """
    判断数据是否已加密

    通过检查 ENC: 前缀来判断数据是否经过加密。
    旧格式数据（无前缀）的迁移在 load_and_update_encryption 中完成。

    Args:
        data: 要检查的数据

    Returns:
        True 表示已加密，False 表示未加密
    """
    if not isinstance(data, str) or len(data) < 20:
        return False
    return data.startswith(ENCRYPTION_PREFIX)


def initialize_first_run(
    config: dict[str, Any],
    prompt_callback: PromptCallback | None = None,
) -> tuple[str, bytes]:
    """
    首次运行初始化

    Args:
        config: 配置字典
        prompt_callback: GUI 层注入的主密码输入回调。
            如为 None，则尝试延迟导入 GUI 弹窗（向后兼容）。

    Returns:
        tuple: (master_password, derived_key) 主密码和派生密钥
    """
    info("system_core", "首次运行，初始化加密系统")
    master_password = _get_master_password(prompt_callback)
    derived_key, _ = generate_derived_key_from_master_password(master_password)
    save_derived_key(derived_key)
    encrypted_master_password = encrypt_data(master_password, derived_key)
    config[MASTER_PASSWORD_KEY] = encrypted_master_password
    return master_password, derived_key


def load_and_decrypt_master_password(config: dict[str, Any]) -> tuple[str, bytes]:
    """
    加载并解密主密码

    Args:
        config: 配置字典

    Returns:
        tuple: (master_password, old_derived_key) 主密码和旧的派生密钥
    """
    old_derived_key = load_derived_key()
    if old_derived_key is None:
        raise Exception("派生密钥文件不存在")

    if MASTER_PASSWORD_KEY not in config:
        raise Exception("主密码配置项不存在")

    encrypted_master_password = config[MASTER_PASSWORD_KEY]
    master_password = decrypt_data(encrypted_master_password, old_derived_key)
    return master_password, old_derived_key


def _migrate_old_encryption_format(config: dict[str, Any], derived_key: bytes) -> None:
    """迁移旧格式加密数据（无 ENC: 前缀）到新格式。

    旧版加密数据没有 ENC: 前缀，新版 is_encrypted 只认前缀。
    此函数检查配置中的敏感字段，如果值看起来是旧格式加密数据
    （无前缀但可用当前密钥成功解密），则重新加密并加上前缀。

    Args:
        config: 配置字典（原地修改）
        derived_key: 当前派生密钥
    """
    sensitive_fields = ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]
    for field in sensitive_fields:
        if field not in config:
            continue
        val = config[field]
        if not isinstance(val, str) or not val or val.startswith(ENCRYPTION_PREFIX):
            continue
        # 尝试用当前密钥解密——成功说明是旧格式加密数据
        try:
            decrypted = decrypt_data(val, derived_key)
            # 重新加密，加上 ENC: 前缀
            config[field] = encrypt_data(decrypted, derived_key)
            info("system_core", f"迁移字段 {field} 到新加密格式")
        except Exception:
            # 解密失败说明不是加密数据或密钥不匹配，跳过
            pass


def load_and_update_encryption(
    config: dict[str, Any],
    prompt_callback: PromptCallback | None = None,
    reset_confirm_callback: ResetConfirmCallback | None = None,
) -> tuple[str, bytes]:
    """
    加载并更新加密系统

    Args:
        config: 配置字典
        prompt_callback: GUI 层注入的主密码输入回调（首次运行时调用）。
            如为 None，则尝试延迟导入 GUI 弹窗（向后兼容）。
        reset_confirm_callback: GUI 层注入的重置确认回调（解密失败时调用）。
            接收错误消息，返回 True 表示用户确认重置。
            如为 None，则尝试延迟导入 GUI 弹窗（向后兼容）。

    Returns:
        tuple: (master_password, derived_key) 主密码和派生密钥
    """
    old_derived_key = load_derived_key()
    if old_derived_key is None or MASTER_PASSWORD_KEY not in config:
        return initialize_first_run(config, prompt_callback)

    try:
        master_password, old_derived_key = load_and_decrypt_master_password(config)
        _migrate_old_encryption_format(config, old_derived_key)
        return master_password, old_derived_key
    except Exception as e:
        error("system_core", f"解密主密码失败：{e}")
        should_reset = _confirm_reset(str(e), reset_confirm_callback)
        if should_reset:
            return initialize_first_run(config, prompt_callback)
        else:
            raise Exception("用户取消重置主密码") from e


def _get_master_password(prompt_callback: PromptCallback | None = None) -> str:
    """获取主密码——优先使用回调，否则延迟导入 GUI 弹窗。"""
    if prompt_callback is not None:
        return prompt_callback()
    return _gui_prompt_for_master_password()


def _confirm_reset(
    error_msg: str,
    reset_confirm_callback: ResetConfirmCallback | None = None,
) -> bool:
    """确认是否重置——优先使用回调，否则延迟导入 GUI 弹窗。"""
    if reset_confirm_callback is not None:
        return reset_confirm_callback(error_msg)
    return _gui_confirm_reset(error_msg)


def _gui_prompt_for_master_password() -> str:
    """GUI 弹窗提示用户输入主密码（延迟导入 PyQt5）。"""
    from gui.encryption_gui import prompt_for_master_password

    return prompt_for_master_password()


def _gui_confirm_reset(error_msg: str) -> bool:
    """GUI 弹窗确认是否重置主密码（延迟导入 PyQt5）。"""
    from gui.encryption_gui import confirm_reset_master_password

    return confirm_reset_master_password(error_msg)
