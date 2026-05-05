"""
system_core.py 模块测试

测试加密模块、配置管理、日期判断等功能。
"""
import datetime
import os

import pytest

import system_core
from system_core import (
    LunarUtils,
    decrypt_data,
    encrypt_data,
    generate_derived_key_from_master_password,
    get_config_snapshot,
    is_encrypted,
    should_work_today,
)


class TestLunarUtils:
    """农历工具类测试"""

    def test_solar_to_lunar(self):
        """测试公历转农历"""
        date = datetime.date(2026, 1, 1)
        result = LunarUtils.solar_to_lunar(date)

        assert result is not None
        assert "lunar_year" in result
        assert "lunar_month" in result
        assert "lunar_day" in result
        assert result["lunar_year"] == 2025
        assert result["lunar_month"] == 11
        assert result["lunar_day"] == 12

    def test_get_solar_term(self):
        """测试获取节气"""
        li_chun = datetime.date(2026, 2, 4)
        result = LunarUtils.get_solar_term(li_chun)
        assert result == "立春"

    def test_get_solar_term_not_solar_term(self):
        """测试非节气日期"""
        normal_day = datetime.date(2026, 1, 15)
        result = LunarUtils.get_solar_term(normal_day)
        assert result == ""

    def test_get_festivals_solar(self):
        """测试获取公历节日"""
        new_year = datetime.date(2026, 1, 1)
        result = LunarUtils.get_festivals(new_year)
        assert "元旦" in result["solar"]

    def test_get_festivals_traditional(self):
        """测试获取传统节日"""
        spring_festival = datetime.date(2026, 2, 17)
        result = LunarUtils.get_festivals(spring_festival)
        assert len(result["traditional"]) > 0 or len(result["solar"]) > 0

    def test_get_lunar_info(self):
        """测试获取完整农历信息"""
        date = datetime.date(2026, 1, 1)
        result = LunarUtils.get_lunar_info(date)

        assert result is not None
        assert "lunar_year" in result
        assert "solar_term" in result
        assert "festivals" in result
        assert "yi_ji" in result


class TestEncryption:
    """加密模块测试"""

    def test_generate_derived_key_from_master_password(self):
        """测试从主密码生成派生密钥"""
        master_password = "test_password_123"
        key, salt = generate_derived_key_from_master_password(master_password)

        assert key is not None
        assert salt is not None
        assert len(salt) == 16
        assert isinstance(key, bytes)

    def test_generate_derived_key_deterministic(self):
        """测试相同密码和盐值生成相同密钥"""
        master_password = "test_password_123"
        salt = os.urandom(16)

        key1, _ = generate_derived_key_from_master_password(master_password, salt)
        key2, _ = generate_derived_key_from_master_password(master_password, salt)

        assert key1 == key2

    def test_encrypt_decrypt_data(self):
        """测试加密解密数据"""
        master_password = "test_password_123"
        key, _ = generate_derived_key_from_master_password(master_password)
        original_data = "sensitive_password"

        encrypted = encrypt_data(original_data, key)
        decrypted = decrypt_data(encrypted, key)

        assert encrypted != original_data
        assert decrypted == original_data

    def test_encrypt_empty_data(self):
        """测试加密空数据"""
        master_password = "test_password_123"
        key, _ = generate_derived_key_from_master_password(master_password)

        result = encrypt_data("", key)
        assert result == ""

    def test_decrypt_empty_data(self):
        """测试解密空数据"""
        master_password = "test_password_123"
        key, _ = generate_derived_key_from_master_password(master_password)

        result = decrypt_data("", key)
        assert result == ""

    def test_is_encrypted_true(self):
        """测试判断已加密数据"""
        master_password = "test_password_123"
        key, _ = generate_derived_key_from_master_password(master_password)
        encrypted = encrypt_data("test_data", key)

        assert is_encrypted(encrypted) is True

    def test_is_encrypted_false(self):
        """测试判断未加密数据"""
        plain_text = "plain_text_password"
        assert is_encrypted(plain_text) is False

    def test_is_encrypted_empty(self):
        """测试判断空数据"""
        assert is_encrypted("") is False
        assert is_encrypted(None) is False

    def test_decrypt_with_wrong_key(self):
        """测试使用错误密钥解密"""
        key1, _ = generate_derived_key_from_master_password("password1")
        key2, _ = generate_derived_key_from_master_password("password2")

        encrypted = encrypt_data("secret_data", key1)

        with pytest.raises(Exception):
            decrypt_data(encrypted, key2)


class TestConfigManagement:
    """配置管理测试"""

    def test_get_config_snapshot(self, sample_config):
        """测试获取配置快照"""


        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        snapshot = get_config_snapshot()

        assert snapshot == sample_config
        assert snapshot is not system_core.global_config

    def test_get_config_snapshot_is_deep_copy(self, sample_config):
        """测试配置快照是深拷贝"""

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        snapshot = get_config_snapshot()
        snapshot["WIFI_NAME"] = "ModifiedWiFi"

        assert system_core.global_config["WIFI_NAME"] == "TestWiFi"


class TestDateRules:
    """日期规则测试"""

    def test_should_work_today_weekday(self, sample_config):
        """测试普通工作日"""

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        monday = datetime.date(2026, 1, 5)
        result = should_work_today(monday)
        assert result is True

    def test_should_work_today_weekend(self, sample_config):
        """测试周末"""

        system_core.global_config.clear()
        system_core.global_config.update(sample_config)

        saturday = datetime.date(2026, 1, 3)
        sunday = datetime.date(2026, 1, 4)

        assert should_work_today(saturday) is False
        assert should_work_today(sunday) is False

    def test_should_work_today_holiday(self, sample_config):
        """测试节假日"""

        config = sample_config.copy()
        config["HOLIDAY_PERIODS"] = [
            {"name": "测试假期", "start": "2026-01-05", "end": "2026-01-07"}
        ]
        system_core.global_config.clear()
        system_core.global_config.update(config)

        holiday = datetime.date(2026, 1, 6)
        result = should_work_today(holiday)
        assert result is False

    def test_should_work_today_compensatory_workday(self, sample_config):
        """测试调休上班日"""

        config = sample_config.copy()
        config["COMPENSATORY_WORKDAYS"] = ["2026-01-04"]
        system_core.global_config.clear()
        system_core.global_config.update(config)

        compensatory_day = datetime.date(2026, 1, 4)
        result = should_work_today(compensatory_day)
        assert result is True

    def test_should_work_today_custom_rule_enabled(self, sample_config):
        """测试启用自定义规则"""

        config = sample_config.copy()
        config["DATE_RULES"] = {
            "ENABLE_CUSTOM_RULE": True,
            "WEEKLY_EXECUTE_DAYS": [0, 1, 2],
            "CUSTOM_HOLIDAY_PERIODS": [
                {"name": "自定义假期", "start": "2026-01-05", "end": "2026-01-06"}
            ],
            "CUSTOM_WORKDAY_PERIODS": [],
        }
        system_core.global_config.clear()
        system_core.global_config.update(config)

        wednesday = datetime.date(2026, 1, 7)
        result = should_work_today(wednesday)
        assert result is False

        thursday = datetime.date(2026, 1, 8)
        result = should_work_today(thursday)
        assert result is False


class TestISPMapping:
    """ISP 映射测试"""

    def test_isp_mapping_exists(self):
        """测试 ISP 映射存在"""
        from system_core import ISP_MAPPING

        assert "cmcc" in ISP_MAPPING
        assert "telecom" in ISP_MAPPING
        assert "unicom" in ISP_MAPPING
        assert "local" in ISP_MAPPING

    def test_isp_mapping_values(self):
        """测试 ISP 映射值"""
        from system_core import ISP_MAPPING

        assert ISP_MAPPING["cmcc"] == "@cmcc"
        assert ISP_MAPPING["telecom"] == "@telecom"
        assert ISP_MAPPING["unicom"] == "@unicom"
        assert ISP_MAPPING["local"] == "@local"
