# QZCT 校园登录助手

🚀 自动登录校园网络，让您的网络连接更简单！

## 项目简介

QZCT 校园登录助手是一款专为校园网络设计的自动化工具，帮助您告别繁琐的手动登录操作。基于PyQt6开发的现代化图形界面，配合强大的定时任务系统，让您的网络连接从未如此简单。

### 为什么选择 QZCT？

- ⚡ **自动化登录**：无需每次手动输入账号密码
- ⏰ **定时任务**：灵活的定时设置，按时自动连接
- 🔒 **安全加密**：密码本地加密存储，保护您的隐私
- 📊 **状态监控**：实时显示网络连接状态
- 💻 **友好界面**：简洁直观的操作体验

## 功能特性

- 自动登录校园网络
- 定时任务管理
- 网络状态监控
- 安全的密码存储
- 友好的图形界面

## 技术栈

- Python 3.13+
- PyQt6 (GUI框架)
- requests (网络请求)
- cryptography (密码加密)

## 安装说明

### 1. 克隆仓库

```bash
git clone https://github.com/taboo-hacker/qzct-login.git
cd qzct-login
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python main_window.py
```

## 使用方法

1. 启动应用后，在主界面填写登录信息
2. 配置自动登录设置
3. 点击"开始"按钮启动自动登录服务
4. 应用会在后台自动处理登录任务

## 配置说明

配置文件为 `config.json`，包含以下主要设置：

- 登录凭证（加密存储）
- 定时任务设置
- 网络检测参数

## 项目结构

```
qzct-login/
├── __pycache__/          # 编译缓存
├── campus_login.py        # 校园登录模块
├── config.json            # 配置文件
├── config.py              # 配置管理
├── date_rules.py          # 日期规则处理
├── dialogs.py             # 对话框组件
├── encryption_key.key     # 加密密钥
├── encryption_salt.key    # 加密盐值
├── force_reset_master_password.py  # 强制重置主密码
├── logger.py              # 日志管理
├── lunar_utils.py         # 农历工具
├── main_window.py         # 主窗口
├── qzct_login.py          # QZCT登录模块
├── requirements.txt       # 依赖文件
├── reset_master_password.py  # 重置主密码
├── security.py            # 安全相关
├── shutdown.py            # 关机功能
├── tasks.py               # 任务管理
├── thread_pool.py         # 线程池
├── utils.py               # 工具函数
└── wifi.py                # WiFi管理
```

## 许可证

本项目采用 [CC BY-NC-SA 4.0](LICENSE)（知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议）。

### 许可证概要

- **署名 (BY)**：您必须给出适当的署名，提供指向本许可协议的链接，并且标明是否（对原始作品）作了修改
- **非商业性使用 (NC)**：您不得将本软件用于商业目的
- **相同方式共享 (SA)**：如果您再混合、转换、或者基于本软件进行创作，您必须在与本许可证相同的许可证下分发您的贡献

详细条款请查看 [LICENSE](LICENSE) 文件或访问 [creativecommons.org/licenses/by-nc-sa/4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 更新日志

### v1.1（2026-4-5）

- **🔧 重写加密解密逻辑**

v1.0（2026-4-5）

- 🎉 初始版本发布

## 联系方式

如有问题或建议，请联系项目维护者。
