# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec 文件 — qzct-login

用法:
    pyinstaller qzct-login.spec

产物:
    dist/qzct-login.exe  (单文件 onefile)
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ------------------------------------------------------------------
# Hidden imports — PyInstaller 静态分析无法检测的动态导入
# ------------------------------------------------------------------
hiddenimports = [
    # lunar-python 内部动态加载的模块
    "lunar_python",
    # chinesecalendar 数据文件
    "chinese_calendar",
    # loguru 内部模块
    "loguru",
    # cryptography 后端
    "cryptography",
    "cryptography.fernet",
    # tomllib/tomli 回退
    "tomllib",
    "tomli",
]

# 收集 lunar_python 全部子模块（它有大量动态导入）
hiddenimports += collect_submodules("lunar_python")

# ------------------------------------------------------------------
# 数据文件 — 非.py 资源
# ------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_data_files

datas = []
# 收集 chinese_calendar 和 lunar_python 的数据文件
datas += collect_data_files("chinese_calendar")
datas += collect_data_files("lunar_python")

# ------------------------------------------------------------------
# 二进制依赖
# ------------------------------------------------------------------
binaries = []

# ------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大模块以减小体积
        "tkinter",
        "test",
        "profile",
        "pstats",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="qzct-login",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # 使用 windowed 模式，不显示控制台
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 版本信息文件（如果存在）
    version=None,
)
