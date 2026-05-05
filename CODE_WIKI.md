# QZCT 校园登录助手 - 代码 Wiki

## 目录

- [项目概览](#项目概览)
- [项目结构](#项目结构)
- [系统架构](#系统架构)
- [核心模块详解](#核心模块详解)
- [关键类与函数](#关键类与函数)
- [并发处理](#并发处理)
- [GUI 架构](#gui-架构)
- [配置与安全](#配置与安全)
- [运行指南](#运行指南)
- [开发规范](#开发规范)

---

## 项目概览

### 基本信息

| 项 | 值 |
| --- | --- |
| **项目名称** | 校园网自动登录 + 定时关机工具 |
| **版本** | 1.1.0 |
| **语言** | Python 3.8+ |
| **平台** | Windows (主要) |
| **许可证** | CC BY-NC-SA 4.0 |

### 功能特性

1. **WiFi 自动连接**
   - 断线自动重连
   - 可配置重试次数和间隔
   - 支持临时 WiFi 配置

2. **校园网登录**
   - 支持多种 ISP（电信、移动、联通、校内）
   - JSONP 协议解析
   - 密码本地加密存储

3. **定时关机**
   - 可配置关机时间
   - 支持取消关机

4. **智能日期规则**
   - 国务院官方节假日
   - 调休上班日管理
   - 自定义日期规则
   - 农历日历

5. **安全加密**
   - 主密码保护
   - Fernet 对称加密
   - PBKDF2 密钥派生

6. **运行日志**
   - Loguru 日志系统
   - GUI 实时日志显示
   - 文件日志轮转

7. **GUI 界面**
   - 无边框圆角窗口
   - 极简商务风格
   - 流畅拖拽体验

---

## 项目结构

```
qzct-login/
├── main.py                          # 程序入口点
├── business.py                      # 业务逻辑核心
├── system_core.py                   # 系统核心（配置、加密、日期）
├── infrastructure.py                # 基础设施（日志、线程池、工具）
├── concurrency.py                   # 并发框架（TaskChain + TaskExecutor）
├── pyproject.toml                   # 项目配置
├── requirements.txt                 # 依赖声明
│
├── gui/                             # GUI 模块
│   ├── main_window.py               # 主窗口（无边框、三区布局）
│   ├── style_manager.py             # QSS 样式管理器
│   ├── style_helpers.py             # UI 组件工厂
│   ├── styles.py                    # 字体/间距/圆角常量
│   ├── themes.py                    # 亮色/暗色主题配色
│   ├── dialogs/                     # 对话框模块
│   │   ├── settings_dialog.py       # 配置设置对话框
│   │   ├── about_dialog.py          # 关于对话框
│   │   ├── calendar_dialog.py       # 日历对话框
│   │   ├── password_dialog.py       # 密码修改对话框
│   │   └── period_edit_dialog.py    # 时间段编辑对话框
│   └── widgets/                     # 自定义组件模块
│       ├── date_rule_widget.py      # 日期规则组件
│       ├── compensatory_widget.py   # 调休上班日管理组件
│       └── holiday_widget.py        # 节假日管理组件
│
└── utils/                           # 工具模块
    ├── version.py                   # 版本号读取
    └── logger.py                    # Loguru 日志封装
```

### 文件依赖关系图

```
main.py
├── gui/main_window.py
│   ├── gui/style_manager.py
│   ├── gui/style_helpers.py
│   ├── gui/dialogs/*
│   └── gui/widgets/*
├── business.py
│   ├── system_core.py
│   ├── infrastructure.py
│   └── concurrency.py
├── system_core.py
├── infrastructure.py
│   └── utils/logger.py
├── concurrency.py
└── utils/version.py
```

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI 层 (PyQt5)                            │
│  ┌─────────────────┐  ┌───────────────┐  ┌───────────────────┐ │
│  │  MainWindow     │  │   Dialogs     │  │    Widgets        │ │
│  └─────────────────┘  └───────────────┘  └───────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     业务逻辑层 (Business)                        │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ WiFi 连接   │  │ 校园网登录    │  │  定时关机         │   │
│  └─────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  并发调度层 (Concurrency)                        │
│  ┌─────────────────┐  ┌────────────────────────────────────┐   │
│  │  TaskChain      │  │      TaskExecutor                  │   │
│  └─────────────────┘  └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     系统核心层 (System Core)                     │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │ 配置管理    │  │   安全加密    │  │   日期/农历      │   │
│  └─────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  基础设施层 (Infrastructure)                     │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │   日志      │  │ 线程池管理    │  │     工具函数     │   │
│  └─────────────┘  └───────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 分层说明

| 层级 | 职责 | 文件 |
| --- | --- | --- |
| GUI 层 | 用户界面，交互逻辑 | `gui/` |
| 业务逻辑层 | WiFi、登录、关机等核心功能 | `business.py` |
| 并发调度层 | 任务链、并行执行、异步处理 | `concurrency.py` |
| 系统核心层 | 配置管理、安全加密、日期处理 | `system_core.py` |
| 基础设施层 | 日志、线程池、工具函数 | `infrastructure.py`, `utils/` |

---

## 核心模块详解

### 1. main.py - 程序入口

**职责**：
- 初始化 PyQt5 应用
- 配置全局主题
- 加载主窗口
- 全局异常捕获

**关键函数**：
- `main()` - 主入口函数
- `apply_global_theme(app)` - 应用全局主题

**工作流程**：
1. 设置异常处理钩子
2. 启用高 DPI 缩放
3. 创建 QApplication
4. 加载主题样式
5. 初始化并显示主窗口

---

### 2. system_core.py - 系统核心模块

#### 2.1 农历工具模块

**类**：`LunarUtils`

**功能**：
- 公历转农历
- 获取节气
- 获取节日
- 获取宜忌
- 获取完整农历信息

**常量**：
- `TRADITIONAL_FESTIVALS` - 传统节日映射
- `SOLAR_FESTIVALS` - 公历节日映射

**关键方法**：
| 方法 | 说明 |
| --- | --- |
| `solar_to_lunar(date)` | 公历转农历 |
| `get_solar_term(date)` | 获取节气 |
| `get_festivals(date)` | 获取节日 |
| `get_yi_ji(date)` | 获取宜忌 |
| `get_lunar_info(date)` | 获取完整信息 |

#### 2.2 安全加密模块

**加密方案**：
- 算法：Fernet (AES-128-CBC + HMAC-SHA256)
- 密钥派生：PBKDF2HMAC (SHA256, 600,000 iterations)
- 盐值：随机生成，持久化存储
- 配置目录：`~/.qzct/`

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `generate_derived_key_from_master_password()` | 从主密码生成派生密钥 |
| `encrypt_data(data, key)` | 加密数据 |
| `decrypt_data(encrypted, key)` | 解密数据 |
| `is_encrypted(data)` | 判断是否已加密 |
| `load_and_update_encryption(config)` | 加载并更新加密系统 |
| `initialize_first_run(config)` | 首次运行初始化 |
| `change_master_password(old, new)` | 修改主密码 |

**配置文件存储**：
- `encryption_key.key` - 派生密钥（可选）
- `encryption_salt.key` - 盐值（必须）
- `config.json` - 配置（含加密的敏感字段）

#### 2.3 配置文件管理

**默认配置** (`DEFAULT_CONFIG`)：
```python
{
    "WIFI_NAME": "",
    "WIFI_PASSWORD": "",
    "MAX_WIFI_RETRY": 10,
    "RETRY_INTERVAL": 5,
    "USERNAME": "",
    "PASSWORD": "",
    "ISP_TYPE": "telecom",
    "WAN_IP": "",
    "SHUTDOWN_HOUR": 23,
    "SHUTDOWN_MIN": 0,
    "AUTOSTART": False,
    "SHOW_LUNAR_CALENDAR": True,
    "HOLIDAY_PERIODS": [...],
    "COMPENSATORY_WORKDAYS": [...],
    "DATE_RULES": {...}
}
```

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `load_config()` | 加载配置（原地更新 `global_config`） |
| `save_config()` | 保存配置（原子写入，防止损坏） |
| `get_config_snapshot()` | 获取配置线程安全快照 |

**ISP 映射** (`ISP_MAPPING`)：
- `cmcc` → `@cmcc` (中国移动)
- `telecom` → `@telecom` (中国电信)
- `unicom` → `@unicom` (中国联通)
- `local` → `@local` (校内资源)

#### 2.4 日期判断模块

**函数**：`should_work_today(check_date=None)`

**判断逻辑**：
1. 检查是否为调休上班日 → 是则执行
2. 如启用自定义规则：
   - 检查是否在自定义工作日期间 → 是则执行
   - 检查是否在自定义节假日期间 → 否则不执行
   - 检查星期是否在执行列表中
3. 否则使用官方规则：
   - 检查是否在法定节假日 → 是则不执行
   - 检查星期是否为工作日 (周一至周五)

---

### 3. business.py - 业务逻辑模块

#### 3.1 自动关机模块

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `cancel_shutdown()` | 取消关机任务 |
| `set_shutdown_timer(seconds)` | 设置 `seconds` 秒后关机 |

**实现方式**：
- 使用 Windows 系统命令：`shutdown /s /t <秒数>`
- 取消命令：`shutdown /a`

#### 3.2 WiFi 连接模块

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `is_wifi_connected(wifi_name)` | 检查是否已连接 |
| `create_windows_wifi_profile(name, password)` | 创建 XML 配置 |
| `connect_wifi(name, password)` | 连接 WiFi |
| `auto_connect_wifi(cfg)` | 自动连接（重试循环） |

**实现方式**：
- 使用 `netsh` 命令管理 WiFi
- 临时 XML 配置文件
- 重试机制（可配置次数和间隔）

#### 3.3 校园网登录模块

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `parse_jsonp(jsonp_text, callback)` | 解析 JSONP 响应 |
| `campus_login(cfg)` | 执行校园网登录 |

**登录流程**：
1. 构建登录参数（用户名+ISP后缀、密码等）
2. 发送 GET 请求到认证服务器
3. 解析 JSONP 响应
4. 检查 `ret_code` 或 `result` 字段判断是否成功

**认证服务器**：`http://192.168.51.2:801/eportal/portal/login`

#### 3.4 完整任务链

**函数**：`run_tasks_once()`

**执行步骤**：
1. 检查今天是否需要执行
2. 连接 WiFi 网络
3. 登录校园网认证
4. 设置定时关机

---

### 4. infrastructure.py - 基础设施模块

#### 4.1 工具函数模块

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `parse_date_str(date_str)` | 解析 "YYYY-MM-DD" 字符串为 `date` 对象 |
| `is_date_in_period(check_date, period)` | 判断日期是否在期间内 |
| `format_period(period)` | 格式化期间为可读字符串 |

#### 4.2 日志系统模块

**日志级别映射** (`LOG_LEVEL_MAP`)：
- 0 → DEBUG
- 1 → INFO
- 2 → WARNING
- 3 → ERROR
- 4 → CRITICAL

**类**：`Logger`
- 封装 Loguru，保持向后兼容
- 支持 GUI 日志显示
- 支持文件日志轮转

**关键函数**：
| 函数 | 说明 |
| --- | --- |
| `init_logger(gui_widget, log_file, level)` | 初始化日志系统 |
| `debug/info/warning/error/critical(module, msg)` | 便捷日志函数 |

**类**：`StreamRedirector`
- 重定向 `stdout`/`stderr` 到日志系统

#### 4.3 线程池管理模块

**类**：`ThreadPoolManager`
- 单例模式
- 管理 `QThreadPool`
- 最大线程数：`min(cpu_count * 4, 16)`
- 栈大小：1 MB

---

### 5. concurrency.py - 并发框架模块

#### 5.1 核心类

##### TaskContext

任务上下文，提供：
- `log(message)` - 记录日志
- `set_progress(percent)` - 设置进度
- `cancel()` - 取消任务
- `is_cancelled()` - 检查是否取消

##### TaskExecutor

任务执行器，PyQt 信号驱动：
- `started` - 任务开始
- `finished` - 任务完成
- `error` - 任务出错
- `progress` - 进度更新
- `all_finished` - 所有任务完成

**方法**：
| 方法 | 说明 |
| --- | --- |
| `submit(func, task_name, *args, **kwargs)` | 提交单个任务 |
| `submit_chain(tasks, on_complete)` | 提交任务链 |
| `submit_parallel(tasks, on_complete)` | 并行提交多个任务 |
| `cancel_all()` | 取消所有任务 |
| `wait_for_all(timeout)` | 等待所有任务完成 |
| `shutdown(wait)` | 关闭执行器 |

##### TaskChain

任务链构建器，流式 API：
```python
chain = TaskChain()
chain.add(task1, "步骤1")
chain.add(task2, "步骤2")
chain.on_success(success_callback)
chain.on_error(error_callback)
chain.execute(executor)
```

#### 5.2 任务装饰器

**装饰器**：`@task(name, timeout)`
- 自动记录任务开始/完成
- 计算耗时
- 注册任务到注册表

**注册表函数**：
- `get_registered_task(name)` - 获取已注册任务
- `list_registered_tasks()` - 列出所有已注册任务

#### 5.3 内置任务

在 `business.py` 中定义的任务：
| 任务 | 说明 |
| --- | --- |
| `task_check_condition()` | 检查执行条件 |
| `task_connect_wifi()` | 连接 WiFi |
| `task_campus_login()` | 登录校园网 |
| `task_set_shutdown()` | 设置定时关机 |

---

## GUI 架构

### 主窗口结构

**类**：`MainWindow`

**布局**（三区布局）：
```
┌─────────────────────────────────────────────┐
│  TitleMenuBar (可拖拽)                        │
│  [校园网自动登录 + 定时关机] [设置 ▾] [帮助 ▾]│
├─────────────────────────────────────────────┤
│  ContentArea (可拖拽)                        │
│  ┌───────────────────────────────────────┐  │
│  │ 当前状态                             │  │
│  │ 日期、状态、规则来源、关机时间        │  │
│  └───────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│  BottomSection                               │
│  ┌───────────────────────────────────────┐  │
│  │ 运行日志 [LogTextEdit]                │  │
│  ├───────────────────────────────────────┤  │
│  │ [执行] [取消关机] [WiFi] [登录] [退出]│  │
│  │                        就绪 | 12:00:00│  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**窗口特性**：
- 无边框 (`FramelessWindowHint`)
- 半透明背景 (`WA_TranslucentBackground`)
- 圆角 (12px)
- 柔和阴影
- 支持拖拽移动

### 样式系统

**主题配色** (`gui/themes.py`)：
- `LightTheme` - 亮色主题
- `DarkTheme` - 暗色主题

**样式常量** (`gui/styles.py`)：
- `FontSize` - 字体大小常量
- `FontStyle` - 字体样式工厂
- `StyleConstants` - 通用样式常量

**样式管理器** (`gui/style_manager.py`)：
- `StyleManager.get_global_stylesheet()` - 获取全局 QSS
- `ThemeManager.set_theme(theme_name)` - 设置主题
- `ThemeManager.current_theme()` - 获取当前主题

**UI 组件工厂** (`gui/style_helpers.py`)：
- `create_button()` - 创建按钮
- `create_label()` - 创建标签
- `create_header_widget()` - 创建标题栏
- `create_card_widget()` - 创建卡片
- `create_tip_label()` - 创建提示标签
- `LogTextEdit` - 彩色日志文本框
- `BaseWidget` - 基础组件

### 对话框模块

| 对话框 | 文件 | 功能 |
| --- | --- | --- |
| `SettingsDialog` | `dialogs/settings_dialog.py` | 配置设置（WiFi/登录/关机/日期） |
| `AboutDialog` | `dialogs/about_dialog.py` | 关于对话框 |
| `CalendarDialog` | `dialogs/calendar_dialog.py` | 万年历对话框 |
| `PasswordDialog` | `dialogs/password_dialog.py` | 主密码修改 |
| `PeriodEditDialog` | `dialogs/period_edit_dialog.py` | 时间段编辑 |

### 自定义组件模块

| 组件 | 文件 | 功能 |
| --- | --- | --- |
| `DateRuleWidget` | `widgets/date_rule_widget.py` | 自定义日期规则 |
| `CompensatoryWidget` | `widgets/compensatory_widget.py` | 调休上班日管理 |
| `HolidayWidget` | `widgets/holiday_widget.py` | 节假日管理 |

---

## 配置与安全

### 配置文件

**位置**：`~/.qzct/config.json`

**字段说明**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `WIFI_NAME` | str | WiFi 名称 |
| `WIFI_PASSWORD` | str | WiFi 密码（加密存储） |
| `MAX_WIFI_RETRY` | int | 最大重试次数 |
| `RETRY_INTERVAL` | int | 重试间隔（秒） |
| `USERNAME` | str | 校园网账号 |
| `PASSWORD` | str | 校园网密码（加密存储） |
| `ISP_TYPE` | str | ISP 类型 (cmcc/telecom/unicom/local) |
| `WAN_IP` | str | 本机 IP（可选） |
| `SHUTDOWN_HOUR` | int | 关机小时 (0-23) |
| `SHUTDOWN_MIN` | int | 关机分钟 (0-59) |
| `AUTOSTART` | bool | 开机自启 |
| `SHOW_LUNAR_CALENDAR` | bool | 显示农历 |
| `HOLIDAY_PERIODS` | list | 法定节假日期间 |
| `COMPENSATORY_WORKDAYS` | list | 调休上班日 |
| `DATE_RULES` | dict | 自定义日期规则 |
| `MASTER_PASSWORD` | str | 加密的主密码（用于验证） |

### 安全设计

1. **主密码保护**
   - 用户首次运行设置主密码
   - 使用 PBKDF2HMAC 派生密钥
   - 派生密钥可选保存到 `encryption_key.key`

2. **密码加密存储**
   - 使用 Fernet (AES-128) 加密密码
   - 每次保存配置前加密，加载后解密
   - 仅在内存中保留明文密码

3. **原子写入**
   - 先写入临时文件 `config.json.tmp`
   - `fsync` 确保数据持久化
   - `os.replace` 原子替换原文件

4. **日志脱敏**
   - `_sanitize()` 函数移除密码明文
   - 正则替换 `user_password=<值>` 为 `user_password=***`

---

## 运行指南

### 环境要求

- Python 3.8+
- Windows 7+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/taboo-hacker/qzct-login.git
   cd qzct-login
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

### 使用流程

1. **首次运行**
   - 设置主密码（用于保护敏感信息）
   - 打开设置配置 WiFi、校园网账号、关机时间

2. **自动执行**
   - 程序启动后自动执行一次任务链
   - 检查日期规则、连接 WiFi、登录校园网、设置关机

3. **手动执行**
   - 点击「执行」按钮手动执行完整任务链
   - 点击「WiFi」或「登录」单独测试功能
   - 点击「取消关机」取消已设置的关机

4. **配置设置**
   - 点击「设置」菜单 →「配置设置」
   - 配置 WiFi、校园网账号、关机时间、日期规则等

5. **查看日历**
   - 点击「设置」菜单 →「任务日历」
   - 查看法定节假日、调休日、自定义规则

---

## 开发规范

### 代码风格

- 使用 Black 格式化（配置见 `pyproject.toml`）
- 最大行宽：100
- 目标 Python 版本：3.8+

### 模块导入规则

1. 标准库 → 第三方库 → 本地模块
2. 相对导入 vs 绝对导入：优先绝对导入
3. GUI 相关导入放在后面

### 日志规范

- 使用 `info()`/`error()` 等函数
- 第一个参数为模块名
- 避免在日志中输出密码

```python
from infrastructure import info, error

info("business", "WiFi 连接成功")
error("business", "登录失败", exc_info=True)
```

### 并发规范

- 使用 `TaskExecutor` 和 `TaskChain` 管理任务
- 工作线程中使用 `get_config_snapshot()` 获取配置
- 避免直接修改 `global_config`（非线程安全）

### 配置修改规范

```python
from system_core import global_config, save_config

# 修改配置
global_config["WIFI_NAME"] = "MyWiFi"

# 保存配置
save_config()
```

---

## 依赖关系

### 核心依赖

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| PyQt5 | >=5.15.0 | GUI 框架 |
| requests | >=2.25.0 | HTTP 请求 |
| cryptography | >=3.0.0 | 加密算法 |
| lunar-python | >=1.0.0 | 农历计算 |
| tomli | >=2.0.0 | TOML 解析 (Python < 3.11) |
| loguru | >=0.7.0 | 日志系统 |

### 开发依赖

| 依赖 | 用途 |
| --- | --- |
| black | 代码格式化 |
| flake8 | 代码检查 |
| pytest | 单元测试 |

---

## 更新日志

### v1.1.0 (2026-04-28)

- ✨ 新增完整 GUI 系统
- ✨ 新增 TaskChain 任务链框架
- ✨ 新增 Loguru 日志系统
- ✨ 新增 utils 工具模块
- 🔧 大幅重构 main.py
- 🔧 重构 infrastructure.py
- 📦 更新依赖和项目配置

### v1.0.3 (2026-04-26)

- 🎨 极简商务风格 UI 重构
- 🔧 修复 8 个 Bug
- 🧹 清理约 530 行死代码
- 📝 更新项目结构

---

## 联系方式

- 项目地址：[https://github.com/taboo-hacker/qzct-login](https://github.com/taboo-hacker/qzct-login)
- 许可证：CC BY-NC-SA 4.0

---

**文档版本**：1.0.0  
**最后更新**：2026-05-05
