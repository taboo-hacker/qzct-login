#!/usr/bin/env python3
"""
qzct-login 本地构建脚本

用法:
    python build.py           # 构建 .exe
    python build.py --clean   # 清理构建产物后构建
    python build.py --verify  # 构建后验证产物
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SPEC_FILE = PROJECT_ROOT / "qzct-login.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
EXE_NAME = "qzct-login.exe"
EXE_PATH = DIST_DIR / EXE_NAME


def clean_build_artifacts() -> None:
    """清理构建产物"""
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            print(f"  清理 {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)


def build_exe() -> bool:
    """使用 PyInstaller 构建 .exe"""
    if not SPEC_FILE.exists():
        print(f"[ERROR] spec 文件不存在: {SPEC_FILE}", file=sys.stderr)
        return False

    print("[1/3] 构建 .exe (PyInstaller)...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC_FILE),
        "--noconfirm",
        "--clean",
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERROR] PyInstaller 构建失败", file=sys.stderr)
        return False

    if not EXE_PATH.exists():
        print(f"[ERROR] 产物未找到: {EXE_PATH}", file=sys.stderr)
        return False

    size_mb = EXE_PATH.stat().st_size / (1024 * 1024)
    print(f"  产物: {EXE_PATH} ({size_mb:.1f} MB)")
    return True


def generate_checksum() -> None:
    """生成 SHA256 校验和"""
    print("[2/3] 生成 SHA256 校验和...")
    sha256 = hashlib.sha256()
    with open(EXE_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    checksum_file = DIST_DIR / f"{EXE_NAME}.sha256"
    checksum_file.write_text(f"{sha256.hexdigest()}  {EXE_NAME}\n", encoding="utf-8")
    print(f"  校验和: {checksum_file}")
    print(f"  SHA256: {sha256.hexdigest()}")


def verify_build() -> bool:
    """验证构建产物"""
    print("[3/3] 验证构建产物...")
    if not EXE_PATH.exists():
        print("[ERROR] .exe 文件不存在", file=sys.stderr)
        return False

    size_mb = EXE_PATH.stat().st_size / (1024 * 1024)
    if size_mb < 30:
        print(f"[WARNING] 产物体积异常小: {size_mb:.1f} MB", file=sys.stderr)
    elif size_mb > 80:
        print(f"[ERROR] 产物体积过大: {size_mb:.1f} MB（超过 80MB 上限）", file=sys.stderr)
        return False
    else:
        print(f"  体积正常: {size_mb:.1f} MB")

    # 检查 SHA256 文件
    checksum_file = DIST_DIR / f"{EXE_NAME}.sha256"
    if checksum_file.exists():
        expected = checksum_file.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(EXE_PATH.read_bytes()).hexdigest()
        if expected == actual:
            print("  校验和匹配")
        else:
            print("[ERROR] 校验和不匹配", file=sys.stderr)
            return False
    else:
        print("  [WARNING] 未找到校验和文件")

    print("\n构建完成!")
    print(f"  产物: {EXE_PATH}")
    print(f"  校验和: {DIST_DIR / f'{EXE_NAME}.sha256'}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="qzct-login 构建脚本")
    parser.add_argument("--clean", action="store_true", help="清理构建产物后构建")
    parser.add_argument("--verify", action="store_true", help="构建后验证产物")
    args = parser.parse_args()

    if args.clean:
        clean_build_artifacts()

    if not build_exe():
        return 1

    generate_checksum()

    if args.verify and not verify_build():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
