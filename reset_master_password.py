#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置主密码测试脚本

当主密码无法解密时，使用此脚本重置主密码。
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import reset_master_password, load_config, global_config

def main():
    """
    主函数
    """
    print("=== 主密码重置工具 ===")
    print("此工具将帮助您重置主密码，解决解密失败的问题。")
    print("\n注意：重置主密码后，所有已加密的信息将无法恢复。")
    print("请确保您已经备份了重要的配置信息。")
    
    # 加载配置
    print("\n正在加载配置...")
    load_config()
    
    # 重置主密码
    print("\n正在重置主密码...")
    print("请按照提示输入新的主密码。")
    
    success = reset_master_password()
    
    if success:
        print("\n✅ 主密码重置成功！")
        print("您的主密码已更新，请使用新密码访问加密信息。")
    else:
        print("\n❌ 主密码重置失败！")
        print("请检查错误信息并重试。")

if __name__ == "__main__":
    main()
