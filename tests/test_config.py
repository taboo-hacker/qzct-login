"""core/config.py 的单元测试——重点覆盖 change_master_password 和 save_config。"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

import core.config as cfg_module
from core.config import (
    MASTER_PASSWORD_KEY,
    change_master_password,
    global_config,
    save_config,
)
from core.encryption import (
    decrypt_data,
    encrypt_data,
    generate_derived_key_from_master_password,
    is_encrypted,
)


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """隔离配置文件目录，避免污染真实配置。"""
    monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))
    monkeypatch.setattr("core.encryption.KEY_FILE", str(tmp_path / "encryption_key.key"))
    monkeypatch.setattr("core.encryption.SALT_FILE", str(tmp_path / "salt.salt"))
    yield tmp_path


@pytest.fixture
def initialized_config(temp_config_dir):
    """初始化一个已加密的配置环境，返回 (old_password, derived_key)。"""
    from core.config import _get_config_dir

    _get_config_dir()

    old_password = "old_pass_123"
    derived_key, _ = generate_derived_key_from_master_password(old_password)

    global_config.clear()
    global_config.update(
        {
            "WIFI_NAME": "TestWiFi",
            "WIFI_PASSWORD": "wifi_secret",
            "USERNAME": "test_user",
            "PASSWORD": "login_secret",
            MASTER_PASSWORD_KEY: encrypt_data(old_password, derived_key),
        }
    )

    from core import config as config_module

    config_module.current_derived_key = derived_key

    return old_password, derived_key


class TestChangeMasterPassword:
    """change_master_password 的测试。"""

    def test_success_changes_password(self, initialized_config) -> None:
        old_password, old_key = initialized_config

        result = change_master_password(old_password, "new_pass_456")

        assert result is True

        encrypted_master = global_config[MASTER_PASSWORD_KEY]
        assert is_encrypted(encrypted_master)

        from core import config as config_module

        new_key = config_module.current_derived_key
        decrypted = decrypt_data(encrypted_master, new_key)
        assert decrypted == "new_pass_456"

        assert decrypt_data(global_config["WIFI_PASSWORD"], new_key) == "wifi_secret"
        assert decrypt_data(global_config["PASSWORD"], new_key) == "login_secret"

        from cryptography.fernet import InvalidToken

        with pytest.raises((InvalidToken, ValueError)):
            decrypt_data(encrypted_master, old_key)

    def test_wrong_old_password_returns_false(self, initialized_config) -> None:
        result = change_master_password("wrong_password", "new_pass")

        assert result is False

    def test_missing_master_password_key_returns_false(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key = b"fake_key"

        global_config.clear()
        global_config.update({"WIFI_NAME": "Test"})

        result = change_master_password("any_pass", "new_pass")

        assert result is False

    def test_unencrypted_master_password_returns_false(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key = b"fake_key"

        global_config.clear()
        global_config.update({MASTER_PASSWORD_KEY: "plaintext_password"})

        result = change_master_password("any_pass", "new_pass")

        assert result is False

    def test_save_failure_rolls_back_key(self, initialized_config) -> None:
        old_password, old_key = initialized_config

        # 保存旧配置快照用于验证回滚
        old_config_snapshot = global_config.snapshot()

        with patch("core.config.save_config", return_value=False):
            result = change_master_password(old_password, "new_pass_456")

        assert result is False

        from core import config as config_module

        assert config_module.current_derived_key == old_key

        # 验证 global_config 也被回滚到旧配置
        for field in ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]:
            assert global_config[field] == old_config_snapshot[field]

    def test_new_password_can_decrypt_all_fields(self, initialized_config) -> None:
        old_password, _ = initialized_config

        result = change_master_password(old_password, "brand_new_pass")

        assert result is True

        from core import config as config_module

        new_key = config_module.current_derived_key
        for field in ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]:
            encrypted_val = global_config[field]
            assert is_encrypted(encrypted_val)
            assert decrypt_data(encrypted_val, new_key) is not None


class TestSaveConfig:
    """save_config 的测试。"""

    def test_save_creates_config_file(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key, _ = generate_derived_key_from_master_password(
            "test_pass"
        )

        global_config.clear()
        global_config.update(
            {
                "WIFI_NAME": "MyWiFi",
                "WIFI_PASSWORD": "secret_pass",
                "USERNAME": "user1",
                "PASSWORD": "login_pass",
            }
        )

        result = save_config()

        assert result is True
        assert os.path.exists(cfg_module.CONFIG_FILE)

        with open(cfg_module.CONFIG_FILE, encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["WIFI_NAME"] == "MyWiFi"
        assert is_encrypted(saved["WIFI_PASSWORD"])
        assert is_encrypted(saved["PASSWORD"])

    def test_save_preserves_decrypt_failed_fields(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key, _ = generate_derived_key_from_master_password(
            "test_pass"
        )

        global_config.clear()
        global_config.update(
            {
                "WIFI_PASSWORD": "corrupted_data",
                "_DECRYPT_FAILED_FIELDS": ["WIFI_PASSWORD"],
            }
        )

        result = save_config()

        assert result is True

        with open(cfg_module.CONFIG_FILE, encoding="utf-8") as f:
            saved = json.load(f)

        # 解密失败的字段应被清空，防止将损坏数据重新加密后永久不可恢复
        assert saved["WIFI_PASSWORD"] == ""

    def test_save_failure_returns_false(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key, _ = generate_derived_key_from_master_password(
            "test_pass"
        )

        global_config.clear()
        global_config.update({"WIFI_NAME": "Test"})

        with (
            patch("builtins.open", side_effect=PermissionError("No access")),
            patch("PyQt5.QtWidgets.QMessageBox"),
        ):
            result = save_config()

        assert result is False

    def test_save_and_encrypts_sensitive_fields(self, temp_config_dir) -> None:
        from core import config as config_module

        config_module.current_derived_key, _ = generate_derived_key_from_master_password(
            "master_pass"
        )

        global_config.clear()
        global_config.update(
            {
                "WIFI_PASSWORD": "plain_wifi_pass",
                "PASSWORD": "plain_login_pass",
                "USERNAME": "plain_user",
            }
        )

        result = save_config()

        assert result is True

        with open(cfg_module.CONFIG_FILE, encoding="utf-8") as f:
            saved = json.load(f)

        assert is_encrypted(saved["WIFI_PASSWORD"])
        assert is_encrypted(saved["PASSWORD"])
        assert saved["USERNAME"] == "plain_user"
        assert "_DECRYPT_FAILED_FIELDS" not in saved
