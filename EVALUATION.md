# qzct-login 项目评估报告

> 评估日期：2026-08-11 · 基线：master @ ef88851（v1.4.0）
> 评估方式：4 个并行评审子代理（core/utils、services/infra、gui、tests/CI/docs）+ 独立静态检查 + 本机实测运行测试套件
> 本机环境：Python 3.12.12 + 全新 venv（`.venv-test/`，本文件所在目录）

---

## 1. 实测结果

| 指标 | 结果 |
| --- | --- |
| 测试套件 | ✅ **317 passed, 2 skipped**（10.73s，Windows + Python 3.12） |
| 总覆盖率 | 70.30%（branch 模式，`--cov` 实测） |
| 静态检查 | 无 eval/exec/pickle 危险用法；无 TODO/FIXME 残留 |
| 全量子进程调用 | 均为参数列表形式（`shell=True` 零使用），无命令注入 |

**覆盖率盲区**：`gui/main_window.py` 仅 14.14%、`main.py` 0%、`core/encryption.py` 53.59% —— 主窗口（最大 GUI 面）完全无测试。

---

## 2. 项目概览

| 维度 | 评价 |
| --- | --- |
| 定位 | PyQt5 校园网自动登录 + WiFi 自动连接 + 定时关机（衢州职业技术学院，Windows） |
| 规模 | 约 60 个源文件，生产代码约 3900 行，测试约 3300 行 |
| 技术栈 | Python 3.10+ / PyQt5 / requests / cryptography(Fernet+PBKDF2) / lunar-python / chinesecalendar / loguru |
| 架构 | 分层清晰：core（纯逻辑）→ infra（并发/日志）→ services（业务）→ gui；GUI 交互通过回调注入 core，可测性好 |
| 工程质量 | 291 个测试函数（参数化展开约 319）、ruff/black/isort/mypy 全配置、CI 矩阵 2 OS × 4 Python、pip-audit 依赖审计、PyInstaller + Wheel 双产物发布 |
| 总体结论 | **中上水平的学生/个人项目**：架构意识、测试习惯、安全底线（加密落盘、日志脱敏、无 shell 注入）都明显高于同规模项目均值；主要短板集中在"看起来做了、实际失效"的并发/日志/主题三处，以及安全模型的一个根本性设计缺陷 |

---

## 3. 值得肯定的地方

1. **分层与解耦**：core 层通过回调注入避免直接依赖 PyQt5，业务函数抛结构化异常（`CampusAuthError`/`WiFiProfileError`/`JSONPParseError`），测试友好。
2. **安全底线意识**：凭据加密落盘、日志 `_sanitize` 脱敏、日志/密钥文件权限收紧、临时 WiFi profile 即写即删、所有子进程参数列表调用。
3. **测试质量**：netsh/subprocess/time.sleep/临时文件全量 mock 且断言时序（test_wifi 尤其扎实）；conftest 配置隔离规范；加密有真实往返断言。
4. **工程配置**：原子配置写入（fsync + os.replace）、PBKDF2 参数符合 OWASP 建议（SHA256/600k/32B）、CI 矩阵与 pip-audit、构建产物 SHA256 校验。
5. **细节处理**：SSID 精确匹配防子串误判、WiFi 指数退避封顶 60s、timeout (3,10) 分离连接/响应、task_name 冲突去重、假期数据与国务院官方安排核对一致。

---

## 4. 问题清单（按严重度）

### 🔴 严重（功能失效 / 可导致崩溃或数据不安全）

| # | 位置 | 问题 | 修复方向 |
| --- | --- | --- | --- |
| C1 | gui/log_sink.py:67,101 | **GUI 日志跨线程投递失效（已实测确认）**。loguru sink 在工作线程执行 `write()`，而 `QTimer.singleShot(0, lambda)` 从无事件循环的线程调用时回调永不执行 → WiFi/登录/关机等全部服务层日志在界面日志框静默丢失（文件日志正常）。 | 改为 QtLogSink 内部 `pyqtSignal(str)` 跨线程 emit（自动 QueuedConnection），或 `QMetaObject.invokeMethod` |
| C2 | services/tasks.py:18-33 + infra/concurrency.py:208-212 | **任务链不短路**：`task_check_condition` 返回 `need_work=False`（周末/节假日）后，WiFi/登录/关机步骤照常执行，"节假日不执行"的核心卖点形同虚设。 | 链在步骤完成时检查结果字段，`need_work=False` 直接触发链完成 |
| C3 | core/encryption.py:127-150 | **主密码形同虚设**：派生密钥明文落盘（`encryption_key.key`），且主密码本身用该密钥加密存于同目录 config.json —— 任何能读 `~/.qzct` 的进程无需主密码即可解密全部凭据。 | 改用 Windows DPAPI（`CryptProtectData`/keyring），或每次会话输入主密码、密钥不落盘 |
| C4 | infra/concurrency.py:111-153 | **超时/取消纸面化**：`result(timeout)` 超时后线程继续跑（WiFi 重试最长约 7 分钟）并占用 worker；`cancel_all` 只置一个从未被读取的死标志，运行中任务无法取消。 | 协作式取消：长循环（WiFi 退避、sleep）中检查 `ctx.is_cancelled()`；去掉内层嵌套 submit |
| C5 | gui/main_window.py:263-270 + infra/concurrency.py:206 | **重复执行可致进程 abort**：启动后 1 秒内点击"执行"会二次触发 `start_task_chain`，旧链 executor 被 `shutdown(wait=False)` 后，其运行中任务完成时信号触发 `_execute_chain_next` → 在已关闭线程池上 submit → 槽内 RuntimeError → PyQt5 直接 abort。 | `start_task_chain` 加防重入守卫；断开旧链信号后再 shutdown；`_execute_chain_next` 捕获 RuntimeError |

### 🟡 重要（安全短板 / 数据风险 / 文档严重漂移）

| # | 位置 | 问题 | 修复方向 |
| --- | --- | --- | --- |
| M1 | core/constants.py:13 + services/campus_login.py:116 | 登录走纯 HTTP（`http://192.168.51.2:801`），账号密码局域网明文传输；`verify=False` 注释是 HTTPS 时代残留（HTTP 下无效）。 | 门户支持 HTTPS 则切换；不支持则在文档/设置页明示风险 |
| M2 | services/wifi.py:83,147 | WiFi profile `protected=false` + `user=all`，密码明文持久化在系统级 profile（删除临时文件不能消除）。 | 尝试 `protected=true` + DPAPI；至少改 `user=current` 并提示 |
| M3 | core/config.py:377-385 | `change_master_password` 先写新密钥文件、再写配置，两步之间崩溃 → 密钥与密文永久不匹配，凭据不可恢复。 | 密钥与配置都走"临时文件 + os.replace"两步原子提交 |
| M4 | core/encryption.py:134-135,67-69 | 密钥/盐文件非原子直写，写中断即损坏；`_migrate_old_files` 迁移后不收紧权限、不删旧文件（密钥残留）。 | 原子写 + 迁移后 `_restrict_file_permissions` + 删除源文件 |
| M5 | core/encryption.py:308-310 | 密钥文件缺失时静默重建加密系统，旧密文随后解密失败被清空 —— 用户无感知数据丢失。 | 先弹确认并说明后果 |
| M6 | core/date_rules.py:49-56 | 硬编码调休上班日判断在自定义规则分支**之前**，用户启用自定义规则后调休日仍强制"上班"，与注释"完全遵守用户配置"矛盾。 | 自定义规则启用时先处理自定义分支 |
| M7 | utils/version.py:33-52 | 打包版（`sys.frozen`）找不到 pyproject.toml，版本号恒为 "1.0.0"。 | 打包时内嵌版本文件（spec datas 或构建期生成） |
| M8 | infra/concurrency.py:126-127 | `wrapped` 吞掉异常只 emit `error(str(e))`：submit 的 Future 恒成功、result 恒 None，调用方无法同步取结果，错误无堆栈。 | error 信号携带 traceback |
| M9 | gui/main_window.py:266-270 | `all_finished` 与 `progress` 信号声明并连接后**从未 emit**（grep 全仓库零匹配），进度上报与"全部完成"通路是死的。 | 链完成分支补 emit，或删除死信号与死槽 |
| M10 | gui/styling/theme_manager.py:68-71 | 主题切换只记录主题名不重绘，"伪主题切换"仅对新控件生效；各组件 `update_theme()` 是空壳。 | 实现 widget 树重绘广播，或文档化 |
| M11 | core/config.py:107-111,140-144 | `snapshot()` 文档说"浅拷贝"实现却是 deepcopy（误导）；`_clone_if_mutable` 只浅拷贝一层，嵌套 dict 内部对象与全局配置共享引用。 | 统一文档与实现；嵌套结构 deepcopy |
| M12 | gui/dialogs/settings_dialog.py:149-156 | 主题切换立即写 global_config，点"取消"不还原；用 `"********"` 文本判定解密失败，真实密码恰为 8 个星号会被静默丢弃。 | 记录初始主题、reject 时恢复；改独立 bool 标记 |
| M13 | CODE_WIKI.md / DEVELOPING.md | 文档停留在 v1.3.0 平铺结构：引用已删除的 `constants.py`/`concurrency.py`/`thread_pool.py`/`style_manager.py`、不存在的 `apply_global_theme`/`submit_chain` 等 API、Python 3.8+ 过时要求。 | 按 v1.4.0 实际代码整体重写 |
| M14 | .github/workflows/ci.yml:106 | 覆盖率无 `--cov-fail-under` 门禁；上传的 coverage.xml 无任何消费方；black 排除 tests 而 isort 检查 tests（口径不一）。 | 加阈值门禁（≥70%）、接入 Codecov 或删上传、统一 tests 处理 |
| M15 | tests/ | 盲区：`load_config` 编排、`MainWindow`、加密迁移函数无任何测试；两个 10 秒 sleep 用例拖慢进程退出、有 flake 风险；test_encryption_permissions 在 Windows CI 会真实执行 icacls。 | 补盲区测试、缩短/打补丁 sleep、mock icacls |

### 🔵 建议（打磨项，按收益排序）

1. **UI/UX**：破坏性确认框默认按钮设 No（base_list_editor.py:154、main_window.py:322）；托盘单击 Trigger 恢复窗口；密码弹窗加显示/隐藏切换与最小长度校验；多个对话框固定尺寸改自适应（DPI 缩放裁切风险）；日历暗色主题下仍浅色。
2. **日志安全**：`append_colored` 未转义 HTML（日志含 `<`/`&` 会破坏格式甚至注入）；LogTextEdit 无块数上限（长会话内存增长）；StreamRedirector 全量转发 stdout/stderr 应在 sink 层统一脱敏。
3. **正确性**：lunar.py 除夕写死 (12,30)，农历小月漏判；闰月节日误判；parse_jsonp 的 `rfind(")")` 遇含 ")" 的 JSON 字符串值会切错；campus_login 成功分支 msg 未过 `_sanitize`。
4. **死代码清理**：6 个异常类零引用；settings 两个死属性；README/RELEASE_NOTES 测试数口径矛盾（291 vs 317）；`license = {text = "LICENSE"}` 元数据写法错误；`version` workflow_dispatch 输入是死参数。
5. **配置**：校园网协议参数（URL/callback/version）硬编码，换校区需改源码，建议可配置化；假期数据仅到 2026 年，2027 起 chinesecalendar 兜底会静默失效，建议外置数据文件。

---

## 5. 优化迭代路线图（建议）

### P0 · 功能修复轮（✅ 已完成，2026-08-11）
1. ✅ log_sink 改信号投递（C1）—— `pyqtSignal` 跨线程 QueuedConnection，服务层日志可靠上屏
2. ✅ 任务链按 `need_work` 短路（C2）—— 步骤返回 `chain_break` 提前成功终止链
3. ✅ `start_task_chain` 防重入 + 旧链信号生命周期（C5）—— `shutdown` 断开链信号 + 提交捕获 RuntimeError
4. ✅ 协作式取消检查点（C4）—— WiFi 重试/退避睡眠可中断；超时先置 ctx 取消标志
5. ✅ 打包版本号内嵌（M7）—— `_MEIPASS` 查找 + spec 打包 pyproject.toml
6. ✅ pytest 强制 PyQt5（qt_api=pyqt5）—— 修复环境同时装 PyQt5/PyQt6 时 pytest-qt 选错绑定导致跨线程信号失效

### P0.5 · UI 重构轮（✅ 已完成，2026-08-11；同日按反馈迭代 v2 / v3）
- **设计决策**：左操作/右日志两栏布局；主色商务蓝 #2E6BE6；主窗口重构 + 全局 QSS 统一（对话框自动继承风格）
- **v2 反馈修正**（依据视觉评审意见）：去掉菜单栏（设置/日历/关于移入底部状态行，快捷键保留）；左右两卡合并为单卡（内部分隔线分区）；左栏收窄至 240px、字号整体降一档、按钮高度统一；移除漂浮的"日历"/"退出程序"元素
- **v3 反馈修正**：万年历适配深色模式（主题调色板 + 主题色日期标记 + update_theme 动态刷新）；万年历从弹窗改为主窗口右侧"任务日历"标签页；关于对话框重写为紧凑简洁版（400px 宽，风格与全局 QSS 一致）；整体尺寸再收小（窗口 800×500、左栏 220px、字号再降一档、按钮 32/30/28）
- **v4 反馈修正**：右侧标签页定为「运行日志 / 设置 / 任务日历」三页（设置页为 SettingsPanel 嵌入版，保存后发信号刷新主界面；主题切换即时同步万年历）；底部状态行移除设置/日历按钮（Ctrl+, / Ctrl+K 快捷键保留直接切页）；关于保持弹窗
- **主题系统**：`ThemeManager.set_theme` 现在真实应用全局 QSS 并立即重绘（修复 M10 伪主题）；设置对话框取消时回滚主题（修复 M12）
- **附带修复**：日志 HTML 转义防注入（🔵2 部分）；black 排除 `.venv-test`；格式化 2 个遗留文件
- **新文件**：`gui/styling/qss.py`（QSS 生成器）、`tests/test_main_window.py`（主窗口冒烟测试）

### P0.6 · 加密体系移除轮（✅ 已完成，2026-08-11，按用户决定）
- **背景**：主密码加密实现存在缺陷——每次启动误报"密码识别错误"，且主密码可随时重置，保护形同虚设
- **处置**：删除 `core/encryption.py`、`gui/encryption_gui.py`、`gui/dialogs/password_dialog.py` 及相关测试；配置改为明文 JSON 保存；加载时自动迁移旧版 `ENC:` 数据（清空需重新填写）并清理遗留密钥文件；移除 cryptography 依赖
- **影响**：C3（密钥落盘）/M3/M4（原子写）/M5（静默重建）随加密体系删除而消失；**代价是 WiFi/登录密码明文存储于 `~/.qzct/config.json`**（README 已注明），M1/M2 的网络明文传输与 WiFi profile 问题仍在

### P1 · 安全加固轮（约 2-3 天）
6. ~~密钥不落盘（DPAPI/keyring）~~ 已通过移除加密体系解决（P0.6）
7. ~~`change_master_password` 原子写~~ 随加密体系移除
8. HTTP 明文风险处置 + WiFi profile protected 尝试（M1/M2）—— 仍待处理
9. ~~密钥缺失静默重建~~ 随加密体系移除

### P2 · 工程质量轮（约 2-3 天）
10. 死代码清理（all_finished/progress、6 个异常类）（M9）
11. 覆盖率门禁 + Codecov + black/isort 统一 tests（M14）
12. 测试补盲区：load_config、加密迁移（M15）—— MainWindow 冒烟测试已补（tests/test_main_window.py）
13. ✅ 主题系统真实重绘（M10）—— 已随 UI 重构轮完成
14. date_rules 优先级修复（M6）+ 自定义规则测试
15. CODE_WIKI/DEVELOPING 按 v1.4.0 重写（M13）

### P3 · 体验打磨轮（1 周内随缘推进）
16. 确认框默认 No、DPI 自适应、托盘单击、日历暗色（🔵1）
17. 日志 HTML 转义✅ + 块数上限 + sink 统一脱敏（🔵2）
18. lunar 除夕/闰月、parse_jsonp 边界（🔵3）
19. 协议参数可配置化、假期数据外置（🔵5）

---

## 6. 迭代节奏建议（2026-08-11 第二次更新）

- ✅ P0 修复轮、P0.5 UI 重构轮（含 v2 反馈迭代）、P0.6 加密移除轮均已完成：**289 个测试通过 + 1 跳过**、ruff/mypy/black/isort 全绿，conda 环境 qzct 验证。
- **下一步推荐 P1 剩余项**：M1（登录 HTTP 明文，受学校门户限制，至少提示用户）/M2（WiFi profile protected=true 尝试）；自用场景优先级可放低。
- P2 的文档重写（CODE_WIKI/DEVELOPING 漂移严重）建议在功能稳定后统一做一次。
