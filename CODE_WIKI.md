# QZCT 校园登录助手 - 代码 Wiki

> 对应版本：v1.5.3（PySide6）· 最后更新：2026-08

## 目录

- [项目概览](#项目概览)
- [项目结构](#项目结构)
- [系统架构](#系统架构)
- [核心模块详解](#核心模块详解)
- [并发处理](#并发处理)
- [GUI 架构](#gui-架构)
- [配置与安全](#配置与安全)
- [运行与构建](#运行与构建)
- [开发规范](#开发规范)
- [新人上手路线](#新人上手路线)

---

## 项目概览

| 项 | 值 |
| --- | --- |
| 项目名称 | 校园网自动登录 + 定时关机工具（衢州职业技术学院） |
| 版本 | 1.5.3 |
| 语言 | Python 3.10+ |
| GUI 框架 | PySide6（Qt for Python，LGPL 许可；Qt 6.11 运行时） |
| 平台 | Windows（主要） |
| 许可证 | CC BY-NC-SA 4.0 |

### 功能特性

1. **WiFi 自动连接**：断线自动重连、指数退避、可中断（协作式取消）、临时 profile 即写即删
2. **校园网登录**：多 ISP（移动/电信/联通）、JSONP 响应解析、超时分段 (3,10)
3. **定时关机**：按配置时间设置 Windows 关机任务，可取消
4. **智能日期规则**：自定义规则（最高优先级）> 硬编码调休/节假日 > chinesecalendar 兜底 > 周末
5. **万年历**：嵌入主窗口标签页，农历/干支/宜忌/节气/节日 + 执行计划标记，适配亮暗主题
6. **运行日志**：Loguru 文件轮转 + GUI 实时显示（跨线程 Signal 投递）+ 日志脱敏
7. **主题系统**：亮色/暗色主题，全局 QSS 即时切换重绘
8. **单实例运行**（v1.5.2+）：QLocalServer 命名管道检测已有实例，二次启动唤起旧实例窗口后自行退出
9. **代码签名分发**（v1.5.2+）：构建脚本自动对 exe 做 Authenticode 签名（SHA256+时间戳），随包分发证书与一键安装脚本

## 项目结构

见 [DEVELOPING.md](DEVELOPING.md) 的项目结构章节（与本 Wiki 同步维护）。

## 系统架构

### 分层

| 层 | 职责 | 目录 |
| --- | --- | --- |
| GUI 层 | 界面、交互、主题 | `gui/` |
| 业务服务层 | WiFi / 登录 / 关机 | `services/` |
| 并发调度层 | 任务链、线程池、取消 | `infra/concurrency.py` |
| 核心逻辑层 | 配置、日期规则、农历 | `core/` |
| 基础设施层 | 日志、日期工具 | `infra/`、`utils/` |

### 一次任务执行的流程

```
程序启动
  → load_config()（读取 ~/.qzct/config.json，旧数据迁移）
  → 应用保存的主题（全局 QSS）
  → 构建界面（左卡片 + 右三标签页）
  → 1 秒后自动启动任务链
任务链（TaskChain，顺序执行）：
  1. 检查执行条件 → 今天无需执行时返回 chain_break，链提前成功结束
  2. 连接 WiFi（重试+退避，可协作取消）
  3. 校园网登录（JSONP 认证）
  4. 设置定时关机
每个任务在后台线程运行，通过 Qt Signal（QueuedConnection）回报主线程。
```

## 核心模块详解

### 1. main.py - 程序入口

- 安装 `sys.excepthook`（未捕获异常写日志，打包模式下写 crash.log）
- 创建 QApplication（高 DPI 由 Qt6 默认启用，无需额外设置）
- 应用默认浅色主题；主窗口加载配置后切换为保存的主题
- 注册单实例（`utils/single_instance.py`）：已有实例在运行时通知其显示窗口，本进程退出
- 允许 Ctrl+C 干净退出

### 2. core/config.py - 配置管理

- **`ConfigManager(dict)`**：线程安全配置字典（RLock）；`get`/取值对 list/dict 浅拷贝；`snapshot()` 深拷贝
- **`global_config`**：全局配置实例；**`get_config_snapshot()`** 供工作线程批量读取
- **`load_config()`**：读 JSON → 旧数据迁移（ENC: 加密字段清空、ISP_SUFFIX→ISP_TYPE、DATE_RULES 旧字段）→ schema 校验 → 假期新鲜度检查 → 原子替换
- **`save_config()`**：临时文件 + fsync + os.replace 原子写入
- **明文存储**：WiFi/登录密码明文保存于 `~/.qzct/config.json`（v1.4.1 起移除主密码加密体系）
- 旧版密钥遗留文件在启动时自动清理

### 3. core/date_rules.py - 日期判断

`should_work_today(date)` 优先级：

1. **自定义规则**（`ENABLE_CUSTOM_RULE=True`）：自定义工作日区间 → 自定义假期区间 → 每周执行日。完全遵守用户配置，硬编码数据与 chinesecalendar 不覆盖
2. **硬编码调休上班日**（COMPENSATORY_WORKDAYS）
3. **硬编码节假日**（HOLIDAY_PERIODS，含学校寒暑假）
4. **chinesecalendar 兜底**（法定假日 / 调休上班）
5. **周末规则**（周一至周五）

### 4. infra/concurrency.py - 并发框架

- **`TaskContext`**：任务上下文（日志缓冲、协作式取消标志 `is_cancelled()/cancel()`）
- **`TaskExecutor(QObject)`**：
  - `submit(func, name, *args)`：线程池执行，started/finished/error 三个 Signal 回报
  - `execute_chain(steps, on_complete)`：顺序任务链；步骤返回 `{chain_break: True}` 提前成功终止；任一步骤抛异常链失败终止
  - `cancel_all()`：置取消标志（任务函数需协作式检查）
  - `shutdown()`：断开链信号并关闭线程池（防关闭后提交崩溃）
- **`@task(name, timeout)`** 装饰器：注册任务、记录耗时日志、可选超时（超时先置取消标志）
- **`TaskChain`**：声明式链 API（add/on_success/on_error/execute）

### 5. infra/logging.py + gui/log_sink.py - 日志系统

- Loguru 后端；`init_logger(gui_widget, log_file, level)` 初始化
- 文件日志 `~/.qzct/qzct.log`（5MB 轮转×5），权限收紧至当前用户
- **`QtLogSink`**：跨线程日志投递用 **Signal**（emit 可发生在工作线程，槽在主线程执行，Qt 自动 QueuedConnection）。早期 `QTimer.singleShot` 实现曾在工作线程丢失日志
- `StreamRedirector`：stdout/stderr 转发到日志
- 登录模块对日志做密码脱敏（`_sanitize`）

### 6. services/ - 业务服务

| 模块 | 要点 |
| --- | --- |
| `wifi.py` | netsh 参数列表调用（无 shell）；SSID 精确匹配；临时 profile mkstemp + finally 删除；`auto_connect_wifi(cfg, should_cancel)` 指数退避（封顶 60s）+ 可中断睡眠 |
| `campus_login.py` | JSONP 切片解析（`parse_jsonp`）；timeout (3,10)；结构化异常 CampusNetworkError/CampusAuthError/JSONPParseError |
| `shutdown.py` | `shutdown /s /t <seconds>` 参数列表；returncode 1119 特判（已有关机任务） |
| `tasks.py` | 四个链式任务：检查条件（含 chain_break）、连接 WiFi、登录、设置关机 |

### 7. gui/ - 界面

- **main_window.py**：左侧"今日状态+任务操作"单卡片（220px），右侧三标签页（运行日志/设置/任务日历），底部状态行（退出/状态/关于/版本）。初始化顺序：日志 → 加载配置 → 应用主题 → 构建界面（设置面板读取加载后的配置）
- **settings_panel.py**：嵌入式设置面板（7 个子页，全部包在 QScrollArea 内），保存后发 `config_saved` 信号，主题切换发 `theme_changed`
- **calendar_view.py**：万年历视图（QCalendarWidget 主题调色板 + 主题色日期标记 + `update_theme()` 动态刷新）
- **tray_manager.py**：托盘（双击还原、右键退出、气泡通知）
- **styling/**：`qss.build_qss(theme)` 生成全局 QSS（卡片/徽标/按钮变体/输入控件/菜单/标签页/日历）；`ThemeManager.set_theme` 应用 QSS 立即重绘；`widgets` 组件工厂（`btnType` 属性接入 QSS）
- **dialogs/**：AboutDialog（紧凑版）、CalendarDialog/SettingsDialog（面板的对话框包装）

## 并发处理

- **线程模型**：主线程 = GUI；工作线程 = ThreadPoolExecutor（max_workers ≤16）
- **跨线程通信**：Qt Signal 自动 QueuedConnection（TaskExecutor 的 started/finished/error、QtLogSink 的 _log_message、SettingsPanel 的 config_saved/theme_changed）
- **取消**：协作式——`ctx.is_cancelled()` 在工作线程长循环/睡眠中检查（WiFi 重试、退避睡眠、连接后等待）
- **防重入**：`start_task_chain` 检查 `is_chain_active()`；`shutdown()` 先断开链信号再关池
- **链语义**：步骤抛异常→链失败终止；步骤返回 chain_break→链成功提前终止；普通 dict 返回不影响后续步骤

## GUI 架构

- **布局**：左卡片（状态徽标：蓝=需执行/灰=无需执行）+ 右 QTabWidget（运行日志 | 设置 | 任务日历）
- **主题**：light/dark 两套 ThemeColors；全局 QSS 由 `build_qss` 生成；切换即全界面重绘（含万年历调色板）
- **快捷键**：Ctrl+R 执行、Ctrl+, 设置页、Ctrl+K 日历页、F1 关于
- **托盘行为**：关闭按钮最小化到托盘；托盘菜单退出；无托盘时关闭直接退出

## 配置与安全

- 配置文件：`~/.qzct/config.json`（明文 JSON，原子写入）
- 敏感信息说明：账号密码明文存储（README 已注明）；登录走校园网 HTTP 明文（门户限制）
- 日志脱敏：登录参数中的账号/密码打码；日志文件权限 icacls 收紧
- 命令安全：所有 subprocess 均为参数列表调用，无 shell 拼接
- 依赖安全：CI 中 pip-audit 扫描全部依赖

## 运行与构建

- 源码运行：`python main.py`（依赖 `pip install -e ".[dev]"`）
- 构建 exe：`python build.py --clean --verify`（PyInstaller onefile，30-80MB 校验 + SHA256）
- 打包注意：spec 已将 pyproject.toml 打入数据区（frozen 模式从 `sys._MEIPASS` 读版本号）
- 代码签名：构建后自动用当前用户证书库中 taboo-hacker 证书签名（SHA256 + DigiCert 时间戳），
  并复制公开证书与一键安装脚本到 dist/；详见 DEVELOPING.md 的"代码签名"章节

## 开发规范

- 格式化：black（含 tests/）、isort；检查：ruff；类型：mypy（显式目录，PySide6 自带存根）
- 测试：pytest + pytest-qt（`qt_api = "pyside6"`），覆盖率门禁 70%
- CI：GitHub Actions（lint/security/test 矩阵 + release 构建 exe/wheel）
- 提交：约定式提交（feat/fix/docs/refactor/test/chore）
- 注释：模块/类/公共函数均需中文 docstring；行内注释解释"为什么"而非"做什么"

## 新人上手路线

按顺序读完即可独立开发，约半天工作量：

1. **跑起来**：按 README 装依赖 → `python main.py` 启动 → 界面上点一遍"立即执行/测试 WiFi/设置"
2. **读入口**：`main.py`（50 行）→ `gui/main_window.py` 的 `MainWindow.__init__` 与 `start_task_chain`
3. **读一条任务链**：`services/tasks.py`（4 个任务函数）→ `infra/concurrency.py`（TaskContext/TaskExecutor/TaskChain）
4. **读一个服务的完整实现**：`services/wifi.py`（netsh 调用、重试、协作式取消，注释最完整）
5. **按需深入**：
   - 改配置项 → `core/config.py`（DEFAULT_CONFIG）+ `core/config_validator.py` + `gui/dialogs/settings_panel.py`
   - 改日期/假期逻辑 → `core/date_rules.py`（优先级链）+ `core/holidays.py`（年度数据维护）
   - 改界面样式 → `gui/styling/`（themes.py 改配色 / qss.py 改样式规则，勿在控件里写死颜色）
   - 改日志 → `infra/logging.py`（门面）+ `utils/logger.py`（底层）+ `gui/log_sink.py`（跨线程投递）
6. **改完自测**：`black --check . && isort --check-only . && ruff check . && mypy core infra services gui utils main.py && pytest tests/ -q`

易踩的坑（都在代码注释中有标注，此处汇总）：

- **不要在构造 SettingsPanel 时调用 load_config()**（会重置全局配置导致设置页显示空白）
- **工作线程绝不直接操作 Qt 控件**，一律走 Signal（参考 QtLogSink）
- **execute_chain 不支持重入**；启动新链前先查 `is_chain_active()` 并关闭旧 executor
- **取消是协作式的**：新增长循环任务时记得轮询 `ctx.is_cancelled()`
- **DEFAULT_CONFIG 一律深拷贝后再修改**，防止测试间/运行期污染默认值
- **日期字符串统一 "YYYY-MM-DD"**，解析用 `infra.date_utils.parse_date_str`（失败返回 None 不抛异常）
