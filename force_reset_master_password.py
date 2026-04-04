#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制重置主密码脚本

当主密码无法解密时，使用此脚本强制重置主密码。
此脚本会直接修改配置文件，不依赖于现有的解密逻辑。
"""

import sys
import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from PyQt5.QtWidgets import QInputDialog, QApplication, QLineEdit

# 配置文件路径
CONFIG_FILE = "config.json"
KEY_FILE = "encryption_key.key"
SALT_FILE = "encryption_salt.key"
MASTER_PASSWORD_KEY = "MASTER_PASSWORD"

def load_salt():
    """
    加载盐值
    
    从文件中加载盐值，如果文件不存在则生成新的。
    
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
        print("生成新的盐值文件")
        return salt

def generate_key_from_password(password, salt=None):
    """
    从用户密码生成加密密钥
    
    Args:
        password (str): 用户密码
        salt (bytes, optional): 盐值，如果为None则生成新的盐值
        
    Returns:
        tuple: (key, salt) 生成的密钥和使用的盐值
    """
    if salt is None:
        salt = load_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def save_derived_key(key):
    """
    保存派生密钥
    
    Args:
        key (bytes): 派生密钥
    """
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    print("派生密钥已保存")

def encrypt_master_password(password):
    """
    加密主密码
    
    Args:
        password (str): 主密码
    
    Returns:
        str: 加密后的主密码
    """
    # 使用当前密码生成的密钥加密主密码
    key, _ = generate_key_from_password(password)
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return base64.b64encode(encrypted).decode()

def prompt_for_master_password():
    """
    提示用户输入主密码
    
    Returns:
        str: 主密码
    """
    # 检查是否已经有应用程序实例
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    # 提示用户设置主密码
    while True:
        password, ok = QInputDialog.getText(
            None, 
            "设置主密码", 
            "请设置新的加密主密码（用于保护您的敏感信息）：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            # 用户取消，使用临时密码
            print("用户取消设置主密码，使用临时密码")
            return "temp_password"
        
        if not password:
            QInputDialog.getText(
                None, 
                "提示", 
                "主密码不能为空，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        # 确认密码
        confirm_password, ok = QInputDialog.getText(
            None, 
            "确认主密码", 
            "请再次输入主密码以确认：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            # 用户取消，使用临时密码
            print("用户取消确认主密码，使用临时密码")
            return "temp_password"
        
        if password != confirm_password:
            QInputDialog.getText(
                None, 
                "提示", 
                "两次输入的密码不一致，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        # 密码设置成功
        print("主密码设置成功")
        return password

def main():
    """
    主函数
    """
    print("=== 强制重置主密码工具 ===")
    print("此工具将强制重置主密码，解决解密失败的问题。")
    print("\n注意：重置主密码后，所有已加密的信息将无法恢复。")
    print("请确保您已经备份了重要的配置信息。")
    
    # 加载配置文件
    print("\n正在加载配置文件...")
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        print("配置文件不存在，创建默认配置")
        config = {}
    
    # 重置主密码
    print("\n正在重置主密码...")
    print("请按照提示输入新的主密码。")
    
    new_password = prompt_for_master_password()
    
    # 加密新的主密码
    encrypted_master_password = encrypt_master_password(new_password)
    config[MASTER_PASSWORD_KEY] = encrypted_master_password
    
    # 生成新的派生密钥
    key, _ = generate_key_from_password(new_password)
    save_derived_key(key)
    
    # 保存配置
    print("\n正在保存配置...")
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    print("\n✅ 主密码重置成功！")
    print("您的主密码已更新，请使用新密码访问加密信息。")

if __name__ == "__main__":
    main()
