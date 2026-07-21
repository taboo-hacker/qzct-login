# Release Notes — v1.4.0

发布日期：2026-07-22

本次发布是一次**工程化深度治理**迭代：在不改变用户功能的前提下，对项目进行了三轮系统性深度审查，累计修复 133 个问题，覆盖数据安全、并发加固、CI/工程配置、功能正确性和代码质量五个维度。测试从 83 个增长到 317 个，覆盖率从 39% 提升到 73%，Ruff 和 MyPy strict 模式全程零错误。

---

## 亮点（Top 5）

1. **三层架构重构** — 将 5 个平铺在根目录的大文件拆分为 `core/`（配置、加密、常量、异常、假期逻辑）、`infra/`（并发框架、日期工具、日志系统）、`services/`（校园网登录、WiFi 连接、定时关机、任务定义）、`gui/`（主窗口、对话框、组件、样式系统）四个职责清晰的包，消除了循环依赖和模块加载副作用。
2. **加密安全加固** — 加密数据统一使用 `ENC:` 前缀标识，移除不可靠的启发式判断；主密码修改支持完整回滚（保存失败时连同 `global_config` 一并还原）；密钥文件权限保护（POSIX `0o600` / Windows icacls 限制继承）；旧格式自动一次性迁移。
3. **并发框架加固** — `TaskExecutor` 字典加锁保护、已完成 future 自动清理防泄漏、`task_name` 冲突自动追加序号、`task` 装饰器 `timeout` 参数落地实现、`execute_chain` 重入防护；`closeEvent` 修正为先询问后 shutdown 的正确顺序；测试 executor 持久化防 GC 回收。
4. **CI 三重门禁** — GitHub Actions CI 流水线实现 Ruff 0 错误 + MyPy strict 0 错误 + pytest 全通过三重门禁，Python 3.10-3.13 矩阵测试，pip-audit 安全审计，Linux 环境使用 xvfb + `QT_QPA_PLATFORM=offscreen` 支持 GUI 测试。
5. **PyInstaller 打包就绪** — 新建 `qzct-login.spec` + `build.py` 本地构建脚本，Release workflow 三阶段（pre-release-check → build-windows-exe → build-wheel），产物 43MB 单文件 exe + SHA256 校验。

---

## 详细变更

### 架构重构（三阶段）

**阶段一：紧急修复**
- 修复 `ThemeColors` 缺失字段导致的阻断 bug
- CI 移除 `continue-on-error`，增加 MyPy + 覆盖率 + 缓存 + Python 3.12
- Release workflow 改 `windows-latest` + 预发布门禁
- `requirements.txt` 补 `chinesecalendar` + 版本约束
- 取消主密码时 `raise SystemExit` 而非静默继续
- 批量清理死代码约 30 处
- 测试文件重命名为规范命名

**阶段二：安全加固**
- `encryption.py` 剥离 GUI 弹窗逻辑到 `gui/encryption_gui.py`
- `change_master_password` 用旧密码解密验证
- 校园网登录 GET → POST + 抑制 urllib3 警告
- WiFi 临时 XML 改用 `tempfile.mkstemp`
- `holiday_widget` 浅拷贝 → `deepcopy`
- CI 增加 pip-audit + `cryptography>=41.0.0`

**阶段三：架构演进**
- `infra/` 层与 Qt 解耦：`QtLogSink` 移到 `gui/log_sink.py`
- `ThreadPoolManager` 合并到 `TaskExecutor`
- `concurrency.py` → `infra/concurrency.py`
- 配置管理重构：`constants.py` → `core/constants.py`，`exceptions.py` → `core/exceptions.py`，假期数据提取到 `core/holidays.py`，移除模块加载副作用
- GUI 架构改进：`BaseListEditorWidget` 基类消除约 200 行重复，`TrayManager` 封装系统托盘，`MainWindow` 从 509 行减至 480 行
- 样式系统重构：4 个文件合并为 `gui/styling/` 包
- 类型标注完善：MyPy strict 模式 268 错误 → 0
- Python 版本策略提升至 `>=3.10`

### 数据安全防线（F1 / E1）

- `change_master_password` 完整回滚：保存旧配置快照，`save_config` 失败时连同 `global_config` 一并回滚
- `is_encrypted` 移除启发式判断，仅认 `ENC:` 前缀；新增 `_migrate_old_encryption_format` 迁移旧格式
- `save_config` 的 `assert` 改为显式 `if` 检查 + `return False`
- `settings_dialog` 重构为先收集到 `pending` dict，全部验证通过后统一写入
- `save_config` 检测到 `_DECRYPT_FAILED_FIELDS` 中字段时清空为 `""`，防止损坏数据被重新加密后永久不可恢复
- 加密密钥文件权限保护（POSIX `0o600` / Windows icacls 限制继承）
- Config Schema 验证（`core/config_validator.py`，15 个顶级字段 + 4 个 `DATE_RULES` 子字段）
- `config_validator` 用 `deepcopy` 防止 `DEFAULT_CONFIG` 被污染

### 并发与资源安全（F2 / E2）

- `TaskExecutor` 字典加锁保护 `save/load/change_master_password`
- `submit` 前清理已完成 future 防字典无限增长
- `task_name` 冲突时自动追加序号避免覆盖
- `task` 装饰器 `timeout` 参数落地用 `inner_future.result(timeout=)` 实现
- `execute_chain` 重入防护（`_chain_active` 加锁）
- `closeEvent` 修正为先询问后 shutdown
- 测试 executor 持久化为 `self._test_executors` 列表，`closeEvent` 统一清理
- `ConfigManager.snapshot()` 改 `deepcopy`
- `generate_derived_key` 线程池改 `with` 语句
- `shutdown.py` 和 `wifi.py` 所有 `subprocess.run`/`check_output` 加 `timeout=10-15`
- `log_sink` 监听 widget `destroyed` 信号清空引用，防止访问已删除 C++ 对象

### CI 与工程配置（F4 / E3）

- CI `pip-audit` 改为审计已安装全部依赖（`pip install -e ".[dev]"` + `pip-audit --strict --desc`）
- Linux 环境安装 xvfb + `QT_QPA_PLATFORM=offscreen` 支持 GUI 测试
- `cryptography` 版本上限 `<44.0.0` → `<50.0.0`
- `release.yml` PyPI 发布条件修正（shell 内检查 `$TWINE_PASSWORD`）
- `qzct-login.spec` excludes 移除 `unittest`/`pydoc`/`doctest`/`pdb`，`upx=False`
- `pyproject.toml` packages 改为 `[tool.setuptools.packages.find]` 自动发现
- `requirements.txt` 重写为从 `pyproject.toml` 派生的注释 + 依赖列表
- CI 增加 `timeout-minutes` 防卡死

### 功能正确性（E4 / F5）

- `log_sink` 无 widget 时缓冲日志，`set_gui_widget` 时自动 flush
- `encryption` 加 `ENC:` 前缀兼容旧格式
- `wifi` 精确匹配 SSID
- `shutdown` returncode 1119 不算错误
- `campus_login` 兼容 int/str 返回类型
- `load_config` 锁粒度优化：`load_and_update_encryption`（可能弹 GUI + IO）移到锁外
- `load_config` 配置自愈：缺失字段自动补全默认值

### 打包发布（阶段 C）

- 新建 `qzct-login.spec`：单文件模式，包含 `chinese_calendar`/`lunar_python` 数据文件
- `build.py` 本地构建脚本：`--clean` 清理 + `--verify` SHA256 校验
- Release workflow 三阶段：pre-release-check（三重门禁）→ build-windows-exe → build-wheel（可选 PyPI 发布）
- 产物：`qzct-login.exe` 43.0MB 单文件
- `main.py` 打包模式写 `crash.log`
- `holidays.py` 新增 `check_holiday_data_freshness` 检查数据时效性

### 日志系统（阶段 D）

- `loguru` 日志文件落盘：10MB 轮转 / zip 压缩 / 35 天保留
- `QtLogSink` 无 widget 时缓冲日志，widget 就绪后自动 flush
- `_lunar_cache` 限制 400 条防内存泄漏

### 测试体系

- 测试从 83 个增长到 **317 个**（+234 个）
- 覆盖率从 39% 提升到 **73.08%**
- 新增 19 个测试文件覆盖配置、加密、并发、服务、GUI 组件、样式、日志、版本等模块
- `conftest.py` 完善测试隔离：`reset_global_config` 还原 `current_derived_key` + 改用 `snapshot()`/`replace_all()`
- 参数化测试覆盖边界条件

### 代码质量

- Ruff **0 错误**（自动修复 243 处 + 手动 10 处）
- MyPy strict 模式 **0 错误**（42 源文件）
- 所有泛型类型补全类型参数（`dict[str, Any]`、`Future[Any]`、`Callable[..., Any]` 等）
- `contextlib.suppress` 替换 `try-except-pass`
- `raise ... from None` 明确异常链
- 海象运算符简化条件赋值
- `getpass.getuser` 替换硬编码用户名
- 日志中脱敏用户账号

---

## 向后兼容

- 配置文件结构兼容：新增 `THEME`、`_DECRYPT_FAILED_FIELDS` 字段，缺失时自动补全
- 加密数据兼容：旧格式（无 `ENC:` 前缀）在 `load_and_update_encryption` 中自动迁移
- 密钥文件兼容：`encryption_key.key`、`encryption_salt.key` 格式不变
- 所有公开函数签名不变

## 迁移说明

普通用户：直接覆盖安装即可，无需任何配置迁移。首次启动时旧格式加密数据会自动迁移。

开发者：
- 包导入路径已变更：`from core.config import ...`、`from infra.concurrency import ...`、`from services.campus_login import ...`
- `concurrency.py`、`constants.py`、`exceptions.py`、`infrastructure.py`、`system_core.py`、`business.py` 已删除，功能分别迁移到对应包中
- 样式系统统一在 `gui/styling/` 包下
- `ConfigManager` 是 `dict[str, Any]` 子类，所有 dict 操作仍可用

---

## 统计

| 指标 | v1.3.0 | v1.4.0 |
|---|---|---|
| 源文件数 | ~15（平铺） | 42（分层包） |
| 测试文件数 | 5 | 19 |
| 测试用例数 | 83 | 317 |
| 覆盖率 | ~39% | 73.08% |
| Ruff 错误 | — | 0 |
| MyPy strict 错误 | — | 0 |
| 深度审查修复问题数 | — | 133 |
