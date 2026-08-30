# 开发指南

本文档面向开发者，介绍如何参与项目开发。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone http://localhost:18080/leo43991314520/qzct-login.git
cd qzct-login
```

（本地 git 服务地址；GitHub 镜像见 README。）

### 2. 创建虚拟环境

推荐 Python 3.11+（项目要求 >=3.10）：

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

也可以使用 conda（本仓库开发环境为 conda 环境 `qzct`）。

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

> 注意：项目 GUI 框架为 **PySide6**（LGPL）。若环境同时装了其他 Qt 绑定（PyQt5/PyQt6），测试已通过 `qt_api = "pyside6"` 强制使用 PySide6，不受影响。

## 代码规范

### 代码格式化（Black，含 tests/）

```bash
black .
```

### 导入排序（isort）

```bash
isort .
```

### 代码检查（Ruff）

```bash
ruff check .
```

### 类型检查（MyPy）

```bash
mypy .
```

> tests/ 已全量补齐类型注解，`mypy .` 全仓通过（backup/ 构建目录已 exclude）。
> PySide6 自带类型存根，类型检查是真实生效的（`warn_unused_ignores` 已开启）。

## 运行测试

### 运行所有测试（含覆盖率门禁 70%）

```bash
pytest tests/ -v --cov --cov-fail-under=70
```

### 运行特定测试

```bash
pytest tests/test_config.py -v
pytest tests/test_concurrency.py -v
pytest tests/test_main_window.py -v
```

## 项目结构

```
qzct-login/
├── main.py                     # 程序入口（excepthook / QApplication / 主题应用）
├── build.py                    # 本地构建脚本（PyInstaller + 校验和）
├── qzct-login.spec             # PyInstaller 打包配置（含 pyproject.toml 数据）
├── core/                       # 核心领域层（无 GUI 依赖）
│   ├── config.py               # 配置管理（ConfigManager / load / save，明文存储）
│   ├── config_validator.py     # 配置 schema 校验
│   ├── constants.py            # 常量（校园网协议 / 路径）
│   ├── exceptions.py           # 自定义异常（WiFi / 校园网登录两类）
│   ├── date_rules.py           # 日期判断（自定义规则优先级最高）
│   ├── holidays.py             # 2025/2026 假期与调休数据
│   └── lunar.py                # 农历工具（lunar-python 封装）
├── infra/                      # 基础设施层
│   ├── concurrency.py          # 并发框架（TaskContext / TaskExecutor / TaskChain）
│   ├── logging.py              # 日志系统（Logger / StreamRedirector / init_logger）
│   └── date_utils.py           # 日期工具（区间判断 / 解析）
├── services/                   # 业务服务层
│   ├── wifi.py                 # WiFi 连接（netsh，协作式取消）
│   ├── campus_login.py         # 校园网认证（JSONP 解析）
│   ├── shutdown.py             # 定时关机（shutdown 命令）
│   └── tasks.py                # 任务编排（@task 装饰函数 + 链式任务）
├── gui/                        # GUI 层
│   ├── main_window.py          # 主窗口（左卡片 + 右三标签页）
│   ├── tray_manager.py         # 系统托盘
│   ├── log_sink.py             # GUI 日志投递（跨线程 Signal）
│   ├── styling/                # 样式系统（qss / themes / theme_manager / widgets）
│   ├── dialogs/                # 对话框（about / calendar 包装 / settings 包装与面板 / period）
│   └── widgets/                # 组件（calendar_view / 列表编辑器 / 规则组件）
├── utils/                      # 工具模块
│   ├── version.py              # 版本读取（frozen 模式从 _MEIPASS）
│   ├── logger.py               # Loguru 封装
│   └── single_instance.py      # 单实例控制（QLocalServer 命名管道）
└── tests/                      # 测试（295+ 用例，pytest + pytest-qt）
```

## 提交代码

### 提交前检查（与 CI 一致）

```bash
black --check . && isort --check-only .
ruff check .
mypy .
pytest tests/ -q --cov --cov-fail-under=70
```

### 提交信息规范

约定式提交：`<type>(<scope>): <subject>`，type 为 feat/fix/docs/refactor/test/chore。

## 添加新功能

1. `git checkout -b feature/your-feature-name`
2. 编写代码（类型注解 + 文档字符串）
3. 编写测试（放在 `tests/test_*.py`，命名 `test_*`）
4. 更新 README 与相关文档
5. 推送分支并合并（本仓库历史为直接推 master 或开分支合并）

## 调试技巧

- 调试日志：`init_logger(level=0)`（DEBUG 级别）
- 断点：`breakpoint()`
- GUI 日志：主窗口"运行日志"标签页实时显示；文件日志在 `~/.qzct/qzct.log`
- 离屏渲染验证（不弹窗）：`QT_QPA_PLATFORM=offscreen python main.py`

## 常见问题

### Q: 如何添加新的 ISP 支持？

在 `core/config.py` 的 `ISP_MAPPING` 添加条目（键为配置值，值为登录后缀）。

### Q: 如何修改登录服务器地址？

修改 `core/constants.py` 的 `CAMPUS_LOGIN_CONFIG`（login_url/referer/callback 等）。

### Q: 如何添加新的日期规则？

默认数据在 `core/holidays.py`（假期区间与调休日）；用户侧自定义规则在设置面板的"日期规则"页；判定优先级见 `core/date_rules.py`。

### Q: 配置文件在哪里、什么格式？

`~/.qzct/config.json`，明文 JSON。旧版加密数据（ENC: 前缀）加载时自动清空，需重新填写。

## 代码签名

构建脚本会自动使用当前用户证书库（`Cert:\CurrentUser\My`）中 taboo-hacker 的
个人身份代码签名证书（全项目通用）对 exe 签名（SHA256 + DigiCert 时间戳），
并把 `taboo-hacker-signing-cert.cer` 与 `安装签名证书.bat` 复制到 `dist/` 随包分发。

- 证书生成（一次性）：
  `New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=taboo-hacker' -NotAfter (Get-Date).AddYears(10) -KeyExportPolicy Exportable -CertStoreLocation 'Cert:\CurrentUser\My'`
- 指纹可通过环境变量 `QZCT_CODE_SIGN_THUMBPRINT` 指定；不指定则自动按主题名查找
- 自签名证书链不受系统信任，`Get-AuthenticodeSignature` 状态显示 `UnknownError` 属正常，
  构建脚本按"签名存在 + 签名者指纹匹配"判定签名成功
- 用户侧：安装一次 `taboo-hacker-signing-cert.cer` 到"受信任的发布者"（双击 `安装签名证书.bat`），
  此后该证书签名的所有 exe 不再提示"未知发布者"
- 私钥仅存在于本机证书库，切勿把可导出私钥的 PFX 分发给他人

## 发布流程

1. 更新 `pyproject.toml` 版本号、README 徽章与更新日志
2. 全量验证（上面的提交前检查）后提交并推送 master（origin + github 两个远端）
3. `python build.py --clean --verify` 构建并签名 exe
4. 在 GitHub 发布 Release（触发 `.github/workflows/release.yml` 构建 exe/wheel），
   或手动触发 workflow_dispatch
