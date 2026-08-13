# QZCT 校园登录助手

🚀 自动登录校园网络，让网络连接更简单！

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-blue.svg)](LICENSE)
[![Version: 1.5.1](https://img.shields.io/badge/Version-1.5.1-blue.svg)](pyproject.toml)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](pyproject.toml)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-purple.svg)](README.md)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 📖 简介

QZCT 校园登录助手是一款专为衢州职业技术学院校园网设计的自动化登录工具。基于 PySide6（Qt for Python，LGPL 许可）开发，采用极简商务风界面，支持 WiFi 自动连接、校园网认证、定时关机等核心功能。

💻 本项目最初由开发者逐行手写完成。
⚡ 后期通过 DeepSeek Harness（DSH）接入 DeepSeek API，由 AI 智能体进行代码审查、重构优化与版本迭代维护，实践 Agentic Coding（智能体编程）开发理念。

## ✨ 功能特性

- ✅ 自动登录校园网 — 支持电信、移动、联通及校内资源
- ✅ WiFi 自动连接 — 断线自动重连，可配置重试次数
- ✅ 定时关机 — 灵活设置关机时间
- ✅ 智能日期规则 — 支持国务院官方节假日、调休、自定义规则
- ✅ 农历日历 — 内置农历显示
- ✅ 配置本地存储 — 配置保存在用户目录（`~/.qzct/config.json`），账号密码为明文存储
- ✅ 运行日志 — 详细的任务执行记录
- ✅ 简洁商务风界面 — 卡片式两栏布局（状态/操作 + 运行日志），亮色/暗色主题即时切换

## 🛠️ 技术栈

| 技术 | 说明 |
| --- | --- |
| Python 3.10+ | 编程语言 |
| PySide6 | GUI 框架（LGPL 许可） |
| requests | 网络请求 |
| lunar-python | 农历日期处理 |
| loguru | 日志系统 |

## 🚀 快速开始

### 方式一：下载可执行文件（推荐普通用户）

1. 前往 [Releases 页面](https://github.com/taboo-hacker/qzct-login/releases) 下载最新的 `qzct-login.exe`
2. 双击运行即可，无需安装 Python 环境
3. （可选）校验文件完整性：`certutil -hashfile qzct-login.exe SHA256`

### 方式二：从源码运行

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
mypy core infra services gui utils main.py

# 本地构建 .exe
python build.py --clean --verify
```

## 📁 项目结构

```
qzct-login/
├── main.py                     # 程序入口
├── build.py                    # 本地构建脚本
├── qzct-login.spec             # PyInstaller 打包配置
├── core/                       # 核心业务逻辑
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   ├── exceptions.py           # 自定义异常
│   ├── date_rules.py           # 日期规则
│   ├── holidays.py             # 假期数据
│   └── lunar.py                # 农历功能
├── infra/                      # 基础设施
│   ├── concurrency.py          # 并发框架（TaskChain + TaskExecutor）
│   ├── logging.py              # 日志系统
│   └── date_utils.py           # 日期工具
├── services/                   # 业务服务
│   ├── campus_login.py         # 校园网登录
│   ├── wifi.py                 # WiFi 连接
│   ├── shutdown.py             # 定时关机
│   └── tasks.py                # 任务链
├── gui/
│   ├── main_window.py          # 主窗口
│   ├── tray_manager.py         # 系统托盘管理
│   ├── log_sink.py             # GUI 日志转发
│   ├── styling/                # 样式系统
│   │   ├── constants.py        # 字体/样式常量
│   │   ├── qss.py              # 全局 QSS 样式表生成
│   │   ├── theme_manager.py    # 主题管理器（切换即全界面重绘）
│   │   ├── themes.py           # 主题配色定义
│   │   └── widgets.py          # 组件工厂
│   ├── dialogs/                # 对话框模块
│   └── widgets/                # 自定义组件
├── utils/
│   ├── version.py              # 版本管理
│   └── logger.py               # 日志工具（Loguru 配置）
├── tests/                      # 测试模块（296 个测试用例）
├── .github/
│   └── workflows/              # GitHub Actions (CI + Release)
├── pyproject.toml              # 项目配置
├── README.md                   # 项目说明
└── LICENSE                     # 许可证
```

## 📚 文档

- [开发指南](DEVELOPING.md) - 如何参与项目开发
- [贡献指南](CONTRIBUTING.md) - 如何贡献代码
- [代码 Wiki](CODE_WIKI.md) - 项目架构和 API 文档

## 🔄 更新日志

### v1.5.1 (2026-08-13)

- 🔧 修复：设置面板在配置加载前构建，导致显示默认空值、保存时覆盖已保存的配置（调整初始化顺序）
- 🔧 修复：ISP_SUFFIX 旧字段迁移从未生效（迁移条件恒为假，迁移基于配置文件实际字段判断）
- 🔧 修复：自定义日期规则启用后，硬编码调休上班日仍强制判为上班（自定义规则改为最高优先级）
- 🧹 清理：删除从未发射的 progress/all_finished 信号、5 个零引用异常类、进度与取消死标志等死代码
- 🛡️ CI 门禁：覆盖率阈值 70%（--cov-fail-under）；black 纳入 tests 目录，与 isort 口径统一
- 📝 文档：CODE_WIKI、DEVELOPING 按 v1.5.0 实际代码重写（PySide6、新结构、真实 API）
- 🧪 测试用例扩充至 296 个（295 通过 + 1 跳过），新增配置迁移与日期规则优先级回归用例

### v1.5.0 (2026-08-13)

- ✨ 从 PyQt5 迁移到 PySide6 6.11（官方 Qt for Python，LGPL 许可，分发更自由；Qt 6 运行时持续维护，Windows 11 原生风格与高 DPI 支持）
- ✨ mypy 类型检查真实生效：PySide6 自带类型存根，迁移中修复 9 处类型问题（日志组件类型收窄、对话框 parent 类型等）
- 🔧 适配 Qt6：移除 Qt5 高 DPI 兼容代码（Qt6 默认启用）、托盘图标/激活/通知枚举改作用域写法、并发框架信号连接按信号精确断开（消除 PySide6 RuntimeWarning）
- 🧪 291 个测试用例全部通过；CI Linux 依赖补充 libgl1

### v1.4.1 (2026-08-11)

- 🔧 修复：GUI 日志跨线程投递失效（WiFi/登录/关机等服务层日志在界面日志框静默丢失），改用 Qt 信号跨线程投递
- 🔧 修复：节假日/周末仍会执行 WiFi 连接、校园网登录与定时关机（任务链不按"需执行"条件短路）
- 🔧 修复：启动 1 秒内重复点击"执行"可能导致进程崩溃（任务链防重入 + 关闭后断开旧链信号）
- 🔧 修复：任务超时/取消后线程仍继续运行、占用工作线程（WiFi 重试与退避睡眠支持协作式取消）
- 🔧 修复：打包版版本号恒显示 1.0.0（从 PyInstaller 解压目录读取 pyproject.toml）
- 🔧 修复：环境同时安装多套 Qt 绑定时测试失败（pytest 强制指定 Qt 绑定）
- 🗑️ 移除：主密码加密体系（原实现反复误报"密码识别错误"且主密码可随时重置，保护形同虚设）；账号密码改为明文存储于 `~/.qzct/config.json`，旧版加密数据自动迁移清空
- ✨ 重构 UI：简洁商务风卡片式两栏布局，全局 QSS 样式系统，亮色/暗色主题即时切换
- ✨ 主界面改为标签页结构：运行日志 / 设置 / 任务日历，设置与万年历不再以弹窗形式打开
- ✨ 万年历完整适配深色模式（主题调色板 + 动态刷新）
- ✨ 精简"关于"对话框，与整体风格统一
- 🧪 测试用例 290 个（289 通过 + 1 跳过），新增任务链短路、协作取消、日志跨线程投递、配置明文存储等回归用例
- 🔧 其他：清理死代码、black 排除本地测试虚拟环境、格式化遗留文件

### v1.4.0 (2026-07-22)

- 🔧 三轮深度审查，修复 133 个问题
- 🧪 测试用例扩充至 290 个

### v1.3.0 (2026-05-24)

- ✨ 新增系统托盘 — 关闭最小化、双击恢复、任务完成气泡通知
- ✨ 新增暗色主题切换持久化（启动时自动恢复）
- ✨ 新增键盘快捷键 — Ctrl+R 执行、Ctrl+, 设置、Ctrl+K 日历、F1 关于
- ✨ 集成 chinese-calendar 作为 2027 年起的法定假日兜底
- 🔧 并发框架重构 — 移除 Queue+QTimer 轮询，改用 Qt 原生跨线程信号
- 🔧 拆出 ConfigManager(dict 子类) — 线程安全 + 浅拷贝 snapshot 替代 deepcopy
- 🔧 PBKDF2 600k 迭代移到后台线程，启动不再卡 UI
- 🔧 WiFi 重试改指数退避；登录请求 timeout 改 (3,10) 分离 connect/read
- 🔧 临时 WiFi profile 限定 `~/.qzct/`，netsh 加载后即写即删
- 🔧 窗口阴影从 paintEvent 手绘改 QGraphicsDropShadowEffect GPU 加速
- 🔧 system_core 模块解耦 Qt 依赖（函数内延迟导入）
- 🔧 业务函数抛结构化异常（WiFiProfileError / CampusAuthError / JSONPParseError）
- 🔧 constants.py / exceptions.py 在 business.py 中落地
- 🔧 删除手工阴影、Queue 协议、log_write 等死代码（净减约 100 行）
- 🐛 自定义规则分支不再被 chinesecalendar 兜底覆盖（用户意图优先）
- 🧪 修复 5 个 baseline 测试失败，87/87 全部通过

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
