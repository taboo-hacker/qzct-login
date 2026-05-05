# QZCT 校园登录助手

🚀 自动登录校园网络，让网络连接更简单！

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-blue.svg)](LICENSE)
[![Version: 1.1.0](https://img.shields.io/badge/Version-1.1.0-blue.svg)](pyproject.toml)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](pyproject.toml)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-purple.svg)](README.md)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 📖 简介

QZCT 校园登录助手是一款专为衢州职业技术学院校园网设计的自动化登录工具。基于 PyQt5 开发，采用极简商务风界面，支持 WiFi 自动连接、校园网认证、定时关机等核心功能。

⚡ 本项目采用 AI 辅助开发，通过 Claude Code + DeepSeek API 进行代码审查与 UI 重构，实践 AI-First 开发理念。

## ✨ 功能特性

- ✅ 自动登录校园网 — 支持电信、移动、联通及校内资源
- ✅ WiFi 自动连接 — 断线自动重连，可配置重试次数
- ✅ 定时关机 — 灵活设置关机时间
- ✅ 智能日期规则 — 支持国务院官方节假日、调休、自定义规则
- ✅ 农历日历 — 内置农历显示
- ✅ 安全加密存储 — 密码本地加密，主密码保护
- ✅ 运行日志 — 详细的任务执行记录
- ✅ 极简商务风界面 — 无边框圆角窗口，流畅拖动体验

## 🛠️ 技术栈

| 技术 | 说明 |
| --- | --- |
| Python 3.8+ | 编程语言 |
| PyQt5 | GUI 框架 |
| requests | 网络请求 |
| cryptography | 密码加密 |
| lunar-python | 农历日期处理 |
| loguru | 日志系统 |

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/taboo-hacker/qzct-login.git
cd qzct-login

# 安装依赖
pip install -e ".[dev]"

# 运行程序
python main.py
```

### 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码格式化
black . && isort .

# 代码检查
ruff check .

# 类型检查
mypy .
```

## 📁 项目结构

```
qzct-login/
├── main.py                     # 程序入口
├── business.py                 # 业务逻辑（WiFi、登录、关机）
├── system_core.py              # 系统核心（配置、加密、日期、农历）
├── infrastructure.py           # 基础设施（日志、线程池、工具）
├── concurrency.py              # 并发框架（TaskChain + TaskExecutor）
├── constants.py                # 常量配置
├── exceptions.py               # 自定义异常
├── gui/
│   ├── main_window.py          # 主窗口
│   ├── style_manager.py        # QSS 样式管理器
│   ├── dialogs/                # 对话框模块
│   └── widgets/                # 自定义组件
├── utils/
│   ├── version.py              # 版本管理
│   └── logger.py               # 日志工具
├── tests/                      # 测试模块
│   ├── conftest.py             # 测试配置
│   ├── test_system_core.py     # 系统核心测试
│   ├── test_business.py        # 业务逻辑测试
│   ├── test_infrastructure.py  # 基础设施测试
│   └── test_concurrency.py     # 并发框架测试
├── .github/
│   ├── workflows/              # GitHub Actions
│   └── ISSUE_TEMPLATE/         # Issue 模板
├── pyproject.toml              # 项目配置
├── README.md                   # 项目说明
├── DEVELOPING.md               # 开发指南
├── CONTRIBUTING.md             # 贡献指南
├── CODE_WIKI.md                # 代码 Wiki
└── LICENSE                     # 许可证
```

## 📚 文档

- [开发指南](DEVELOPING.md) - 如何参与项目开发
- [贡献指南](CONTRIBUTING.md) - 如何贡献代码
- [代码 Wiki](CODE_WIKI.md) - 项目架构和 API 文档

## 🔄 更新日志

### v1.2.0 (2026-05-05)

- ✨ 新增测试框架和单元测试
- ✨ 新增 CI/CD 配置（GitHub Actions）
- ✨ 新增常量配置模块（constants.py）
- ✨ 新增自定义异常模块（exceptions.py）
- 🔧 完善类型提示
- 🔧 更新 pyproject.toml 配置
- 📝 新增开发指南和贡献指南
- 📝 新增 Issue 和 PR 模板

### v1.1.0 (2026-04-28)

- ✨ 新增完整的 GUI 系统
- ✨ 新增多线程并发框架
- ✨ 新增工具模块
- 🔧 大幅重构代码

### v1.0.0 (2026-04-05)

- 🎉 初始版本发布

## 🤝 贡献

欢迎贡献代码！请查看 [贡献指南](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 [CC BY-NC-SA 4.0](LICENSE) 许可协议。

---

Made with ❤️ by QZCT Developer
