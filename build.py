#!/usr/bin/env python3
r"""
qzct-login 本地构建脚本

用法:
    python build.py           # 构建 .exe（自动尝试代码签名）
    python build.py --clean   # 清理构建产物后构建
    python build.py --verify  # 构建后验证产物

代码签名说明:
    构建完成后自动尝试使用当前用户证书库（Cert:\CurrentUser\My）中的
    QZCT 代码签名证书对 exe 签名（SHA256 + 时间戳），并把公开证书
    （qzct-signing-cert.cer）与用户一键安装脚本复制到 dist/ 随包分发。
    指纹可用环境变量 QZCT_CODE_SIGN_THUMBPRINT 指定；
    未找到证书时跳过签名（构建照常成功）。
"""

import argparse
import hashlib
import os
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

# 代码签名（可选）：证书存放在当前用户的证书库（Cert:\CurrentUser\My），
# 指纹可通过环境变量 QZCT_CODE_SIGN_THUMBPRINT 指定；未指定时自动按主题名查找
SIGNING_DIR = Path.home() / "qzct-signing"
CERT_FILE = SIGNING_DIR / "taboo-hacker-signing-cert.cer"
INSTALL_SCRIPT = SIGNING_DIR / "安装签名证书.bat"
TIMESTAMP_URL = "http://timestamp.digicert.com"


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


def _powershell_exe() -> str:
    """优先 PowerShell 7（pwsh），回退 Windows PowerShell 5.1。"""
    pwsh = shutil.which("pwsh")
    return pwsh if pwsh else "powershell"


def _run_powershell(script: str) -> str:
    """执行 PowerShell 脚本并返回标准输出（Windows-only）。"""
    exe = _powershell_exe()
    env = None
    if exe == "powershell":
        # 清理 PS7 模块目录：它们会污染 Windows PowerShell 5.1 的模块加载，
        # 导致 Microsoft.PowerShell.Security 类型冲突、Cert: 驱动不可用
        env = os.environ.copy()
        env["PSModulePath"] = ";".join(
            p
            for p in env.get("PSModulePath", "").split(";")
            if p and r"PowerShell\Modules" not in p and "WindowsApps" not in p
        )
    result = subprocess.run(
        [exe, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )
    return result.stdout.strip()


def _find_signing_thumbprint() -> str | None:
    """查找签名证书指纹：优先环境变量，其次自动查找 taboo-hacker 证书。"""
    thumbprint = os.environ.get("QZCT_CODE_SIGN_THUMBPRINT", "").strip()
    if thumbprint:
        return thumbprint
    script = (
        r"Get-ChildItem Cert:\CurrentUser\My | "
        "Where-Object { $_.Subject -like '*taboo-hacker*' -and $_.HasPrivateKey } | "
        "Select-Object -First 1 -ExpandProperty Thumbprint"
    )
    found = _run_powershell(script)
    return found or None


def sign_exe() -> bool:
    """对 exe 进行代码签名（可选步骤）。

    找到签名证书时签名并校验；未找到时跳过（构建照常成功，
    仅打印未签名提醒）。签名会改变文件内容，因此必须在
    generate_checksum() 之前执行。
    """
    thumbprint = _find_signing_thumbprint()
    if not thumbprint:
        print("[签名] 未找到代码签名证书，跳过（未签名 exe 在他人电脑会提示未知发布者）")
        return False

    print(f"[签名] 使用证书指纹 {thumbprint} 签名...")
    script = (
        rf"$cert = Get-ChildItem Cert:\CurrentUser\My | "
        f"Where-Object {{ $_.Thumbprint -eq '{thumbprint}' -and $_.HasPrivateKey }} | "
        f"Select-Object -First 1; "
        f"if ($cert) {{ "
        f"Set-AuthenticodeSignature -FilePath '{EXE_PATH}' -Certificate $cert "
        f"-HashAlgorithm SHA256 -TimestampServer '{TIMESTAMP_URL}' | Out-Null; "
        f"$sig = Get-AuthenticodeSignature '{EXE_PATH}'; "
        f"$sig.Status.ToString() + '|' + $sig.SignerCertificate.Thumbprint "
        f"}} else {{ 'CertNotFound' }}"
    )
    result = _run_powershell(script)
    # 自签名证书链不受系统信任，Status 可能为 UnknownError；
    # 只要签名存在且签名者指纹匹配即视为签名成功
    if "|" not in result:
        print(f"[ERROR] 签名失败或验证未通过：{result}", file=sys.stderr)
        return False
    status, signer_thumbprint = result.split("|", 1)
    if signer_thumbprint.strip().upper() != thumbprint.strip().upper():
        print(f"[ERROR] 签名者指纹不匹配：{signer_thumbprint}", file=sys.stderr)
        return False
    print(f"[签名] 签名完成，状态: {status}（签名者: taboo-hacker）")

    # 随 exe 一起分发：公开证书 + 用户一键安装脚本
    for src in (CERT_FILE, INSTALL_SCRIPT):
        if src.exists():
            dst = DIST_DIR / src.name
            shutil.copy2(src, dst)
            print(f"[签名] 已复制 {dst.name} 到 dist/")
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

    # 检查代码签名（确认签名存在且签名者指纹匹配）
    thumbprint = _find_signing_thumbprint()
    if thumbprint:
        script = (
            f"$sig = Get-AuthenticodeSignature '{EXE_PATH}'; "
            f"$sig.Status.ToString() + '|' + $sig.SignerCertificate.Thumbprint"
        )
        result = _run_powershell(script)
        if "|" in result:
            status, signer = result.split("|", 1)
            if signer.strip().upper() == thumbprint.strip().upper():
                print(f"  签名: 已签名（状态 {status}，证书指纹 {thumbprint}）")
            else:
                print(f"  [WARNING] 签名者指纹不匹配: {signer}")
        else:
            print(f"  [WARNING] 未检测到签名（{result}）")

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

    # 签名必须在生成校验和之前（签名会改变文件内容）
    sign_exe()

    generate_checksum()

    if args.verify and not verify_build():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
