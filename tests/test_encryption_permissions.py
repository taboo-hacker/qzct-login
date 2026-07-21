"""
D1 测试：加密密钥文件权限保护

测试 _restrict_file_permissions() 函数在 POSIX 和 Windows 上的行为。
"""

import os

import pytest

from core.encryption import (
    _restrict_file_permissions,
    load_salt,
    save_derived_key,
)


class TestRestrictFilePermissions:
    """_restrict_file_permissions() 测试"""

    def test_restrict_permissions_creates_no_error(self, tmp_path):
        """限制权限不应对已存在的文件报错"""
        test_file = tmp_path / "test_key.key"
        test_file.write_text("dummy content")

        # 不应抛出异常
        _restrict_file_permissions(str(test_file))

        # 文件仍然存在且内容不变
        assert test_file.exists()
        assert test_file.read_text() == "dummy content"

    def test_restrict_permissions_nonexistent_file(self, tmp_path):
        """对不存在的文件调用应静默处理（不抛异常）"""
        nonexistent = str(tmp_path / "nonexistent.key")

        # 不应抛出异常
        _restrict_file_permissions(nonexistent)

    @pytest.mark.skipif(os.name != "posix", reason="POSIX only")
    def test_posix_chmod_0600(self, tmp_path):
        """POSIX 系统上应设置 0o600 权限"""
        test_file = tmp_path / "test_key.key"
        test_file.write_text("data")
        test_file.chmod(0o644)

        _restrict_file_permissions(str(test_file))

        mode = test_file.stat().st_mode & 0o777
        assert mode == 0o600


class TestSaveDerivedKeyPermissions:
    """save_derived_key() 写文件后应限制权限"""

    def test_save_derived_key_restricts_permissions(self, tmp_path, monkeypatch):
        """save_derived_key 写入的密钥文件权限应被限制"""
        key_file = tmp_path / "derived_key.key"
        derived_key = b"0" * 32  # 32 bytes dummy key

        # patch encryption 模块中已绑定的 KEY_FILE 名字
        monkeypatch.setattr("core.encryption.KEY_FILE", str(key_file))

        save_derived_key(derived_key)

        assert key_file.exists()
        assert key_file.read_bytes() == derived_key

        # 在 POSIX 上验证权限
        if os.name == "posix":
            mode = key_file.stat().st_mode & 0o777
            assert mode == 0o600


class TestLoadSaltPermissions:
    """load_salt() 写入的 salt 文件权限应被限制"""

    def test_load_salt_creates_file_with_permissions(self, tmp_path, monkeypatch):
        """load_salt 在 salt 文件不存在时应创建并限制权限"""
        salt_file = tmp_path / "salt.key"

        # patch encryption 模块中已绑定的 SALT_FILE 名字
        monkeypatch.setattr("core.encryption.SALT_FILE", str(salt_file))

        salt = load_salt()

        assert salt_file.exists()
        assert len(salt) > 0

        if os.name == "posix":
            mode = salt_file.stat().st_mode & 0o777
            assert mode == 0o600
