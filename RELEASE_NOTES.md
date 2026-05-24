# Release Notes — v1.2.0

发布日期：2026-05-24

本次发布是一次**质量优先**的迭代：在不破坏现有接口的前提下，对并发框架、配置层、UI 体验、异常处理、依赖管理做了系统性重构与加固。

---

## 亮点（Top 5）

1. **并发框架重写** — 移除自建的 Queue + 50ms QTimer 轮询，直接用 Qt 原生 `pyqtSignal` 跨线程。删除 45 行胶水代码，消除了 50ms 延迟和持续 CPU 空载。
2. **系统托盘 + 关闭最小化** — 关闭主窗口默认隐藏到托盘而非退出；双击托盘恢复、右键菜单退出；任务完成时弹气泡通知。
3. **节假日动态化** — 集成 `chinese-calendar` 作为 `should_work_today` 的法定假日兜底。原硬编码节假日仅到 2026 年，现在 2027 年及以后将自动使用 chinesecalendar 数据（库每年更新）。
4. **WiFi 凭据安全加固** — 临时 WiFi profile 不再落到系统 temp 目录，限定 `~/.qzct/` 并 try/finally 即写即删；优先复用 Windows 已保存的 profile，避免重复明文落盘。
5. **暗色主题持久化** — 设置对话框中切换主题立即生效并写入配置，下次启动自动恢复（之前选了就忘）。

---

## 详细变更

### 🔴 性能与正确性

- **并发框架反模式移除**（[concurrency.py](concurrency.py)）
  - 删除 `_TaskMessage` / `_message_queue` / `_poll_timer` / `_process_messages` / `_emit_log` / `_emit_progress`
  - 工作线程直接 `self.finished.emit(name, result)`，Qt 用 `QueuedConnection` 自动 marshal 到主线程
  - **效果**：消除 50ms 信号延迟、QTimer 持续唤醒；代码净减 45 行

- **PBKDF2 600k 迭代移到后台线程**（[system_core.py:282](system_core.py:282)）
  - 用 `QEventLoop` 在后台 ThreadPoolExecutor 执行密钥派生，主线程继续处理 Qt 事件
  - **效果**：启动加载配置时 UI 不再冻结

- **窗口阴影 GPU 加速**（[main_window.py](gui/main_window.py)）
  - 删除 `paintEvent` 中 30 行手绘的 5 层同心圆角矩形阴影循环
  - 替换为单个 `QGraphicsDropShadowEffect`（blur=20, offset=(0,4), alpha=50）

- **HTTP 超时分离**（[business.py:312](business.py:312)）
  - `timeout=15` → `timeout=(3, 10)`，3 秒判定连接不通，10 秒判定服务器无响应

- **WiFi 重试改指数退避**（[business.py:242](business.py:242)）
  - 原固定 5 秒间隔 → `min(interval * 2^n, 60)`，最长 60 秒上限

- **`should_work_today` 法定假日兜底**（[system_core.py:880](system_core.py:880)）
  - 基础规则分支：硬编码节假日 → chinesecalendar 兜底 → 周末规则
  - 自定义规则分支：用户启用 ENABLE_CUSTOM_RULE 即完全接管，**不**引入兜底

### 🟡 架构与代码质量

- **`ConfigManager(dict)`**（[system_core.py:632](system_core.py:632)）
  - 替代裸 `global_config` dict，线程安全读写，可变值自动浅拷贝，`snapshot()` 用浅拷贝替代之前的 `deepcopy`
  - 新增 `replace_all()` 原子操作（clear+update 在单锁内）

- **`system_core` 解耦 Qt**（[system_core.py:13](system_core.py:13)）
  - 模块顶层不再 `from PyQt5.QtWidgets import ...`，改为 `_lazy_import_qt()` 函数内延迟导入
  - core 层现可在无 Qt 环境（如 CLI、测试）独立运行

- **`exceptions.py` 落地**（[business.py](business.py)）
  - `_do_connect_wifi()` 抛 `WiFiProfileError` / `WiFiConnectionError`
  - `parse_jsonp()` 抛 `JSONPParseError` 替代裸 `ValueError`
  - `campus_login()` 内部分类抛 `CampusNetworkError` / `CampusAuthError` / `JSONPParseError`
  - 公开签名仍返回 `bool`，向后兼容

- **`constants.py` 落地**（[business.py:13](business.py:13)）
  - `campus_login()` 使用 `CAMPUS_LOGIN_CONFIG` / `CAMPUS_LOGIN_HEADERS` 替代硬编码 URL / User-Agent

- **`parse_jsonp` 移除正则**（[business.py:256](business.py:256)）
  - 改用 `find()` + `rfind()` 字符串切片，正确处理嵌套右括号

- **`requests.Session` 用 with 上下文**（[business.py](business.py)）
  - 移除手工 `try/finally session.close()`

- **`get_simplified_yi_ji` 哈希伪随机 fallback 删除**（[system_core.py](system_core.py)）
  - lunar-python 失败时返回空字典而非"伪造"宜忌数据

- **死代码清理**（[main_window.py](gui/main_window.py)）
  - 删除 `_log_write` / `_append_log` / `log_write` —— 日志通过 `QtLogSink` 直接进 GUI，原先靠字符串关键字猜 level 的逻辑彻底移除

- **`infrastructure.error/critical` 简化**（[infrastructure.py:249](infrastructure.py:249)）
  - 抽出 `has_active_exception` 共用，消除两份相同 if/else 分支

### 🟢 UI 体验

- **系统托盘**（[main_window.py:222](gui/main_window.py:222)）
  - 关闭窗口默认隐藏到托盘，弹气泡提示
  - 双击托盘恢复主窗口
  - 右键菜单"退出"真实终止
  - 任务链完成时调用 `showMessage()` 通知

- **自适应窗口**（[main_window.py:138](gui/main_window.py:138)）
  - 最小尺寸从固定 860×620 放宽到 750×540
  - 默认尺寸保持 860×620 不变（不影响习惯）

- **主题持久化**（[main.py:13](main.py:13)、[settings_dialog.py:155](gui/dialogs/settings_dialog.py:155)）
  - 主题选择写入 `global_config["THEME"]`，启动时自动恢复

- **键盘快捷键**（[main_window.py](gui/main_window.py)）
  - `Ctrl+R` — 执行任务
  - `Ctrl+,` — 打开设置
  - `Ctrl+K` — 任务日历
  - `F1` — 关于

- **按钮 loading 态**（[main_window.py:472](gui/main_window.py:472)）
  - 任务执行期间按钮文本切换为 `⟳ 运行中...`，完成后恢复"执行"

### 🧪 测试

- 测试套件从 87 个用例中 **5 failed → 0 failed**：
  - WiFi 测试 mock 数据类型修正（`bytes` → `str`，匹配业务代码 `encoding='gbk'`）
  - lunar-python 当前版本计算结果更新（2026-01-01 lunar_day: 12 → 13）
  - 周末测试 fixture 冲突修复（清空 COMPENSATORY_WORKDAYS，换用无调休数据的日期）
  - 自定义规则测试逻辑修正（原测试自相矛盾）

### 📦 依赖

- 新增 `chinese-calendar>=1.0.0,<2.0.0`
- 移除已弃用的 `cryptography.hazmat.backends.default_backend()` 写法

---

## 向后兼容

- ✅ 所有公开函数签名不变（`connect_wifi`、`campus_login` 仍返回 `bool`）
- ✅ 配置文件结构兼容（新增 `THEME` 字段，缺失时默认 `"light"`）
- ✅ 密钥文件（`encryption_key.key`、`encryption_salt.key`）和加密数据格式不变

## 迁移说明

普通用户：直接覆盖安装即可，无需任何配置迁移。

开发者：
- 如果你直接读取 `global_config`，无需修改——`ConfigManager` 是 dict 子类，所有 dict 操作仍可用
- 如果你写了 `_config_lock`，请删除——模块级锁已被 ConfigManager 内部 RLock 替代
- 如果你 catch 过 `ValueError` 来处理 JSONP 解析失败，请改为 catch `JSONPParseError`（或更宽的 `QZCTError`）

---

## 提交清单

| Commit | 范围 |
|---|---|
| `71affea` | 并发框架重构 + WiFi 安全 + timeout 分离 + 阴影 GPU |
| `b20da07` | ConfigManager + 系统托盘 + 自适应窗口 + 主题持久化 |
| `4282bf2` | chinesecalendar + PBKDF2 后台 + 指数退避 + Qt 解耦 |
| `ca6b08c` | constants/jsonp/yi_ji/死代码清扫 |
| `cffef80` | exceptions.py 落地 |
| `02a67c3` | UI 快捷键 + loading 态 |
| `1dd10a0` | baseline 测试修复 + custom_rule 兜底逻辑 bug 修复 |

**统计**：10 文件改动、+478 / −350 净增 128 行、87/87 测试通过。
