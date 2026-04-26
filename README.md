# QZCT 校园登录助手

<div align="center">

🚀 **自动登录校园网络，让网络连接更简单！**

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.3-green.svg)](pyproject.toml)
[![Python](https://img.shields.io/badge/Python-3.8%2B-yellow.svg)](requirements.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows-purple.svg)](README.md)

</div>

---

## 📖 简介

QZCT 校园登录助手是一款专为**衢州职业技术学院**校园网设计的自动化登录工具。基于 PyQt5 开发，采用极简商务风界面，支持 WiFi 自动连接、校园网认证、定时关机等核心功能。

> ⚡ **本项目采用 AI 辅助开发**，通过 Claude Code + DeepSeek API 进行代码审查与 UI 重构，实践 AI-First 开发理念。

---

## ✨ 功能特性

- ✅ **自动登录校园网** — 支持电信、移动、联通及校内资源
- ✅ **WiFi 自动连接** — 断线自动重连，可配置重试次数
- ✅ **定时关机** — 灵活设置关机时间
- ✅ **智能日期规则** — 支持国务院官方节假日、调休、自定义规则
- ✅ **农历日历** — 内置农历显示
- ✅ **安全加密存储** — 密码本地加密，主密码保护
- ✅ **运行日志** — 详细的任务执行记录
- ✅ **极简商务风界面** — 无边框圆角窗口，流畅拖动体验

---

## 🛠️ 技术栈

| 技术 | 说明 |
|------|------|
| Python 3.8+ | 编程语言 |
| PyQt5 | GUI 框架 |
| requests | 网络请求 |
| cryptography | 密码加密 |
| zhdate | 农历日期处理 |

---

## 🚀 快速开始

```bash
git clone https://github.com/taboo-hacker/qzct-login.git
cd qzct-login
pip install -r requirements.txt
python main.py
```

---

## 📁 项目结构

```
qzct-login/
├── main.py              # 主窗口程序（GUI + 主逻辑）
├── business.py           # 业务逻辑（WiFi、登录、关机）
├── system_core.py        # 系统核心（配置、加密、日期、农历）
├── infrastructure.py     # 基础设施（日志、线程池、工具）
├── config.json           # 配置文件（自动生成）
├── requirements.txt      # 项目依赖
├── pyproject.toml        # 项目配置
├── README.md             # 项目说明
└── LICENSE               # 许可证
```

---

## 🔄 更新日志

## 🔄 更新日志

### v1.0.3（2026-04-26）

- 🎨 **极简商务风 UI 重构** — 无边框圆角窗口、自定义阴影、流畅拖动体验
- 🧹 **代码审查与重构** — 通过 Claude Code + DeepSeek V4 Pro 修复 8 个 Bug
  - 修复节假日字段名不一致导致判断失效
  - 修复 DateRuleWidget 保存逻辑缺失
  - 修复 WiFi 连接判断逻辑漏洞
  - 清理约 530 行废弃的死代码
  - 修复硬编码文件路径问题
  - 修复 submit_parallel 信号连接泄漏
- 📝 **更新项目结构** — 四个核心模块文件
- 📝 **README 优化** — 精简结构，对齐 GitHub Profile 风格

### v1.0.2（2026-04-05）

- 🔧 **重构项目结构** — 将多个模块融合为 4 个核心文件
- 🔧 **修复重复日志输出** — 统一通过信号发送日志
- 🔧 **修复配置设置崩溃** — 移除对已删除文件的依赖
- 📝 **配置按钮中文化** — 保存和取消按钮改为中文
- 📝 **更新日志模块名** — 统一使用新文件名作为日志标识
- 🧹 **优化关于我们的 UI**

### v1.0.1（2026-04-05）

- 🔧 **重写加密解密逻辑** — 提升安全性

### v1.0.0（2026-04-05）

- 🎉 **初始版本发布**
- ✅ WiFi 自动连接与校园网登录
- ✅ 定时关机功能
- ✅ 主密码加密保护
- ✅ 图形化配置界面
---

## 📄 许可证

本项目采用 [CC BY-NC-SA 4.0](LICENSE) 许可协议。

---

## ⭐ Star History

<a href="https://star-history.com/#taboo-hacker/qzct-login&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=taboo-hacker/qzct-login&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=taboo-hacker/qzct-login&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=taboo-hacker/qzct-login&type=Date" />
  </picture>
</a>
