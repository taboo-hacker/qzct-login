"""
版本号读取模块

从 pyproject.toml 读取项目版本号（单一数据源，避免多处硬编码），
主窗口底栏与"关于"对话框使用。结果进程内缓存（_cached_project_version）。

读取策略（三级回退）：
    1. 标准库 tomllib（Python 3.11+）解析
    2. 第三方 tomli（Python 3.10）
    3. 文本逐行匹配 version = "..."（无 TOML 库时兜底）
全部失败时返回 "1.0.0"。

打包说明：PyInstaller onefile 模式下 pyproject.toml 已由 spec 打入
数据区（sys._MEIPASS），frozen 分支负责定位。
"""

import os
import sys

from infra.logging import debug, error, warning

# 版本号缓存：首次读取后固定，避免重复磁盘 IO
_cached_project_version: str | None = None


def get_project_version() -> str:
    """
    从 pyproject.toml 中读取项目版本号

    功能说明：
        - 定位项目根目录下的 pyproject.toml 文件
        - 解析文件内容并提取 version 字段
        - 使用缓存机制避免重复读取
        - 如果读取失败，返回默认版本号 "1.0.0"

    返回值：
        str: 项目版本号

    异常：
        无（异常会被捕获并返回默认值）
    """
    global _cached_project_version
    if _cached_project_version is not None:
        return _cached_project_version

    try:
        if getattr(sys, "frozen", False):
            # PyInstaller onefile 将 datas 资源解压到 _MEIPASS 临时目录；
            # 未提供时退回到 exe 所在目录（onedir 场景）
            base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 依次搜索: 基目录 → 父目录 → 父目录的父目录
        candidates = [
            os.path.join(base_dir, "pyproject.toml"),
            os.path.join(os.path.dirname(base_dir), "pyproject.toml"),
        ]
        pyproject_path = None
        for p in candidates:
            if os.path.exists(p):
                pyproject_path = p
                break

        if pyproject_path is None:
            warning("main", "找不到 pyproject.toml 文件，使用默认版本号")
            _cached_project_version = "1.0.0"
            return _cached_project_version

        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli

                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)
            except ImportError:
                with open(pyproject_path, encoding="utf-8") as f:
                    content = f.read()
                for line in content.split("\n"):
                    if line.strip().startswith("version"):
                        version = line.split("=")[1].strip().strip('"').strip("'")
                        _cached_project_version = version
                        debug("main", f"从 pyproject.toml 读取到版本号: {version}")
                        return version
                _cached_project_version = "1.0.0"
                return _cached_project_version

        version_str: str = str(data.get("project", {}).get("version", "1.0.0"))
        _cached_project_version = version_str
        debug("main", f"从 pyproject.toml 读取到版本号: {version_str}")
        return version_str

    except Exception as e:
        error("main", f"读取 pyproject.toml 失败: {e}", exc_info=True)
        _cached_project_version = "1.0.0"
        return _cached_project_version
