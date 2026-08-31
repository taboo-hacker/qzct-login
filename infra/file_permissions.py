"""
敏感文件权限收紧

config.json（含账号/WiFi 密码明文）与 qzct.log 在落盘后应立即收紧
到仅当前用户可读写。Windows 用 icacls 移除继承并只授予当前用户，
POSIX 用 chmod 600。收权失败只记 DEBUG 日志，不阻断调用方流程。
"""

import os
import sys


def restrict_file_permissions(filepath: str) -> None:
    """限制文件权限，使其仅当前用户可读写（Windows: icacls，POSIX: chmod 600）。

    Args:
        filepath: 目标文件路径，须已存在
    """
    try:
        if sys.platform == "win32":
            import getpass
            import subprocess

            subprocess.run(
                ["icacls", filepath, "/inheritance:r", "/grant:r", f"{getpass.getuser()}:F"],
                capture_output=True,
                timeout=10,
                check=False,
                # GUI 进程调用控制台程序避免闪黑框（分支内已确保 Windows）
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            os.chmod(filepath, 0o600)
    except Exception as e:
        # 收权是尽力而为的加固措施：失败不阻断初始化/保存流程，但留痕便于诊断
        from loguru import logger

        logger.debug(f"限制文件权限失败（忽略）：{filepath} -> {e}")
