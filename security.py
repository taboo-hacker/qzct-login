import os
import base64
import logging
from PyQt5.QtWidgets import QInputDialog, QApplication, QLineEdit, QMessageBox
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# 配置日志
def info(module_name, message):
    logging.info(message, extra={"logger_name": module_name})

def error(module_name, message):
    logging.error(message, extra={"logger_name": module_name})

# ==========================================
# 安全加密模块
# ==========================================
# 本模块负责加密和解密配置文件中的敏感信息，
# 如WiFi密码和校园网密码，提高系统安全性。
#
# 加密逻辑：
#     1. 首次运行时会要求用户设置主密码
#     2. 根据主密码通过KDF生成派生密钥
#     3. 派生密钥保存在encryption_key.key中
#     4. 使用派生密钥加密主密码并保存在config.json中
#     5. 每次运行时用派生密钥解密主密码
#     6. 用解密后的主密码重新生成新的派生密钥
#     7. 用新的派生密钥加密主密码、WIFI密码、校园网密码
#
# 注意事项：
#     - 主密码用于生成加密密钥，请勿遗忘
#     - 每次运行都会生成新的派生密钥
# ==========================================

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
        info("security", "生成新的盐值文件")
        return salt


def generate_derived_key_from_master_password(master_password, salt=None):
    """
    从主密码生成派生密钥
    
    Args:
        master_password (str): 主密码
        salt (bytes, optional): 盐值，如果为None则加载或生成新的盐值
        
    Returns:
        tuple: (key, salt) 生成的派生密钥和使用的盐值
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
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    return key, salt


def save_derived_key(key):
    """
    保存派生密钥
    
    Args:
        key (bytes): 派生密钥
    """
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    info("security", "派生密钥已保存")


def load_derived_key():
    """
    加载派生密钥
    
    Returns:
        bytes: 派生密钥，如果文件不存在则返回None
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    return None


def prompt_for_master_password():
    """
    提示用户输入主密码
    
    首次运行时要求用户设置主密码，后续运行时如果解密失败也会要求用户输入。
    
    Returns:
        str: 主密码
    """
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    while True:
        password, ok = QInputDialog.getText(
            None, 
            "设置主密码", 
            "请设置加密主密码（用于保护您的敏感信息）：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            info("security", "用户取消设置主密码，使用临时密码")
            return "temp_password"
        
        if not password:
            QInputDialog.getText(
                None, 
                "提示", 
                "主密码不能为空，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        confirm_password, ok = QInputDialog.getText(
            None, 
            "确认主密码", 
            "请再次输入主密码以确认：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            info("security", "用户取消确认主密码，使用临时密码")
            return "temp_password"
        
        if password != confirm_password:
            QInputDialog.getText(
                None, 
                "提示", 
                "两次输入的密码不一致，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        info("security", "主密码设置成功")
        return password


def prompt_for_verify_master_password():
    """
    提示用户输入主密码进行验证
    
    Returns:
        str: 主密码
    """
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    
    while True:
        password, ok = QInputDialog.getText(
            None, 
            "验证主密码", 
            "请输入主密码以验证身份：", 
            echo=QLineEdit.Password
        )
        
        if not ok:
            return None
        
        if not password:
            QInputDialog.getText(
                None, 
                "提示", 
                "主密码不能为空，请重新输入：", 
                echo=QLineEdit.Password
            )
            continue
        
        return password


def encrypt_data(data, derived_key):
    """
    加密数据
    
    Args:
        data (str): 要加密的数据
        derived_key (bytes): 派生密钥
    
    Returns:
        str: 加密后的数据（base64编码）
    """
    if not data:
        return data
    f = Fernet(derived_key)
    encrypted = f.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data, derived_key):
    """
    解密数据
    
    Args:
        encrypted_data (str): 加密的数据（base64编码）
        derived_key (bytes): 派生密钥
    
    Returns:
        str: 解密后的数据
    """
    if not encrypted_data:
        return encrypted_data
    f = Fernet(derived_key)
    try:
        encrypted = base64.b64decode(encrypted_data.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        error("security", f"解密失败：{e}")
        raise


def is_encrypted(data):
    """
    判断数据是否已加密
    
    Args:
        data (str): 要检查的数据
    
    Returns:
        bool: True表示已加密，False表示未加密
    """
    if not data:
        return False
    try:
        decoded = base64.b64decode(data.encode())
        return len(decoded) >= 44
    except:
        return False


def initialize_first_run(config):
    """
    首次运行初始化
    
    提示用户设置主密码，生成派生密钥并加密主密码。
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, derived_key) 主密码和派生密钥
    """
    info("security", "首次运行，初始化加密系统")
    master_password = prompt_for_master_password()
    derived_key, _ = generate_derived_key_from_master_password(master_password)
    save_derived_key(derived_key)
    encrypted_master_password = encrypt_data(master_password, derived_key)
    config[MASTER_PASSWORD_KEY] = encrypted_master_password
    return master_password, derived_key


def load_and_decrypt_master_password(config):
    """
    加载并解密主密码
    
    从配置中加载加密的主密码，用派生密钥解密。
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, old_derived_key) 主密码和旧的派生密钥
    """
    old_derived_key = load_derived_key()
    if old_derived_key is None:
        raise Exception("派生密钥文件不存在")
    
    if MASTER_PASSWORD_KEY not in config:
        raise Exception("主密码配置项不存在")
    
    encrypted_master_password = config[MASTER_PASSWORD_KEY]
    master_password = decrypt_data(encrypted_master_password, old_derived_key)
    return master_password, old_derived_key


def regenerate_derived_key(master_password):
    """
    重新生成派生密钥
    
    用解密后的主密码生成新的派生密钥。
    
    Args:
        master_password (str): 主密码
    
    Returns:
        bytes: 新的派生密钥
    """
    new_derived_key, _ = generate_derived_key_from_master_password(master_password)
    save_derived_key(new_derived_key)
    info("security", "派生密钥已重新生成")
    return new_derived_key


def reencrypt_sensitive_data(config, old_derived_key, new_derived_key):
    """
    重新加密敏感数据
    
    用新的派生密钥重新加密主密码、WIFI密码、校园网密码。
    
    Args:
        config (dict): 配置字典
        old_derived_key (bytes): 旧的派生密钥
        new_derived_key (bytes): 新的派生密钥
    """
    sensitive_fields = ["WIFI_PASSWORD", "PASSWORD", MASTER_PASSWORD_KEY]
    
    for field in sensitive_fields:
        if field in config and config[field]:
            # 解密数据
            if is_encrypted(config[field]):
                decrypted_data = decrypt_data(config[field], old_derived_key)
            else:
                decrypted_data = config[field]
            # 用新密钥重新加密
            config[field] = encrypt_data(decrypted_data, new_derived_key)
    
    info("security", "敏感数据已重新加密")


def load_and_update_encryption(config):
    """
    加载并更新加密系统
    
    解密主密码，生成新的派生密钥，重新加密敏感数据。
    
    Args:
        config (dict): 配置字典
    
    Returns:
        tuple: (master_password, new_derived_key) 主密码和新的派生密钥
    """
    # 检查是否是首次运行
    old_derived_key = load_derived_key()
    if old_derived_key is None or MASTER_PASSWORD_KEY not in config:
        return initialize_first_run(config)
    
    try:
        # 尝试解密主密码
        master_password, old_derived_key = load_and_decrypt_master_password(config)
    except Exception as e:
        error("security", f"解密主密码失败：{e}")
        # 解密失败时，询问用户是否重置密码
        reply = QMessageBox.question(
            None, 
            "解密失败", 
            "主密码解密失败，是否重置主密码？\n\n注意：重置后所有已加密信息将无法恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            return initialize_first_run(config)
        else:
            raise Exception("用户取消重置主密码")
    
    # 重新生成派生密钥
    new_derived_key = regenerate_derived_key(master_password)
    
    # 重新加密敏感数据
    reencrypt_sensitive_data(config, old_derived_key, new_derived_key)
    
    return master_password, new_derived_key
