"""core/config.py 的单元测试——覆盖 save_config / load_config 与旧版加密数据迁移。"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

import core.config as cfg_module
from core.config import global_config, load_config, save_config


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """隔离配置文件目录，避免污染真实配置。"""
    monkeypatch.setattr(cfg_module, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(cfg_module, "CONFIG_FILE", str(tmp_path / "config.json"))
    yield tmp_path


def _write_config_file(path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestSaveConfig:
    """save_config 测试（明文存储）。"""

    def test_save_writes_plaintext_passwords(self, temp_config_dir) -> None:
        cfg_module._get_config_dir()
        global_config.clear()
        global_config.update(
            {
                "WIFI_NAME": "TestWiFi",
                "WIFI_PASSWORD": "wifi_secret",
                "USERNAME": "test_user",
                "PASSWORD": "login_secret",
            }
        )

        assert save_config() is True

        saved = json.loads((temp_config_dir / "config.json").read_text(encoding="utf-8"))
        assert saved["WIFI_PASSWORD"] == "wifi_secret"
        assert saved["PASSWORD"] == "login_secret"
        assert "MASTER_PASSWORD" not in saved

    def test_save_failure_returns_false(self, temp_config_dir) -> None:
        """写入失败时返回 False 并提示错误。"""
        cfg_module._get_config_dir()
        with (
            patch("core.config.os.replace", side_effect=OSError("disk full")),
            patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical,
        ):
            assert save_config() is False
            mock_critical.assert_called_once()


class TestLoadConfig:
    """load_config 测试（含旧版加密数据迁移）。"""

    def test_load_plaintext_config(self, temp_config_dir) -> None:
        """明文配置正常加载。"""
        _write_config_file(
            temp_config_dir / "config.json",
            {
                "WIFI_NAME": "MyWiFi",
                "WIFI_PASSWORD": "plain_wifi",
                "USERNAME": "user1",
                "PASSWORD": "plain_login",
                "SHUTDOWN_HOUR": 22,
                "SHUTDOWN_MIN": 30,
            },
        )
        load_config()

        assert global_config["WIFI_NAME"] == "MyWiFi"
        assert global_config["WIFI_PASSWORD"] == "plain_wifi"
        assert global_config["PASSWORD"] == "plain_login"
        assert global_config["SHUTDOWN_HOUR"] == 22

    def test_load_migrates_legacy_encrypted_fields_to_empty(self, temp_config_dir) -> None:
        """旧版 ENC: 前缀加密数据无法解密，加载后清空并移除主密码配置项。"""
        _write_config_file(
            temp_config_dir / "config.json",
            {
                "WIFI_NAME": "MyWiFi",
                "WIFI_PASSWORD": "ENC:Z0FBQUFBQmxlZ3Y=",
                "USERNAME": "user1",
                "PASSWORD": "ENC:Z0FBQUFBQmxlZ3g=",
                "MASTER_PASSWORD": "ENC:Z0FBQUFBQmxlZ3k=",
            },
        )
        load_config()

        assert global_config["WIFI_PASSWORD"] == ""
        assert global_config["PASSWORD"] == ""
        assert "MASTER_PASSWORD" not in global_config

    def test_load_missing_file_uses_defaults(self, temp_config_dir) -> None:
        """配置文件不存在时使用默认配置，不弹窗不崩溃。"""
        load_config()

        assert global_config["WIFI_NAME"] == ""
        assert global_config["WIFI_PASSWORD"] == ""
        assert global_config["SHUTDOWN_HOUR"] == 23

    def test_load_corrupted_file_falls_back_to_defaults(self, temp_config_dir) -> None:
        """配置文件损坏时回退默认配置并提示。"""
        (temp_config_dir / "config.json").write_text("{not valid json", encoding="utf-8")
        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            load_config()
            mock_warning.assert_called_once()

        assert global_config["WIFI_NAME"] == ""

    def test_load_cleans_legacy_key_files(self, temp_config_dir) -> None:
        """加载时清理旧版加密密钥遗留文件。"""
        (temp_config_dir / "encryption_key.key").write_bytes(b"deadbeef")
        (temp_config_dir / "encryption_salt.key").write_bytes(b"salt")

        load_config()

        assert not (temp_config_dir / "encryption_key.key").exists()
        assert not (temp_config_dir / "encryption_salt.key").exists()

    def test_load_migrates_isp_suffix_to_isp_type(self, temp_config_dir) -> None:
        """旧版 ISP_SUFFIX 字段迁移为 ISP_TYPE。"""
        _write_config_file(temp_config_dir / "config.json", {"ISP_SUFFIX": "@cmcc"})

        load_config()

        assert global_config["ISP_TYPE"] == "cmcc"
        assert "ISP_SUFFIX" not in global_config

    def test_load_drops_unknown_isp_suffix(self, temp_config_dir) -> None:
        """未知 ISP_SUFFIX 无法映射时直接丢弃。"""
        _write_config_file(temp_config_dir / "config.json", {"ISP_SUFFIX": "@unknown"})

        load_config()

        assert global_config["ISP_TYPE"] == "telecom"  # 默认值
        assert "ISP_SUFFIX" not in global_config

    def test_load_migrates_legacy_date_rule_fields(self, temp_config_dir) -> None:
        """旧版 DATE_RULES 的 CUSTOM_HOLIDAYS/CUSTOM_WORKDAYS 迁移为新字段。"""
        _write_config_file(
            temp_config_dir / "config.json",
            {
                "DATE_RULES": {
                    "ENABLE_CUSTOM_RULE": True,
                    "WEEKLY_EXECUTE_DAYS": [1, 2],
                    "CUSTOM_HOLIDAYS": [
                        {"name": "旧假期", "start": "2026-05-01", "end": "2026-05-03"}
                    ],
                    "CUSTOM_WORKDAYS": [
                        {"name": "旧上班", "start": "2026-05-04", "end": "2026-05-05"}
                    ],
                }
            },
        )

        load_config()

        rules = global_config["DATE_RULES"]
        assert rules["CUSTOM_HOLIDAY_PERIODS"] == []  # 旧数据无法迁移，置空
        assert rules["CUSTOM_WORKDAY_PERIODS"] == []
        assert "CUSTOM_HOLIDAYS" not in rules
        assert "CUSTOM_WORKDAYS" not in rules
        assert rules["ENABLE_CUSTOM_RULE"] is True
        assert rules["WEEKLY_EXECUTE_DAYS"] == [1, 2]

    def test_load_fills_missing_date_rule_keys(self, temp_config_dir) -> None:
        """DATE_RULES 缺失的键从默认配置补齐。"""
        _write_config_file(
            temp_config_dir / "config.json",
            {"DATE_RULES": {"ENABLE_CUSTOM_RULE": True}},
        )

        load_config()

        rules = global_config["DATE_RULES"]
        assert rules["WEEKLY_EXECUTE_DAYS"] == [0, 1, 2, 3, 4]
        assert rules["CUSTOM_HOLIDAY_PERIODS"] == []
        assert rules["CUSTOM_WORKDAY_PERIODS"] == []
