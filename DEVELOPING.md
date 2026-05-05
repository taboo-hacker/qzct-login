# 开发指南

本文档面向开发者，介绍如何参与项目开发。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/taboo-hacker/qzct-login.git
cd qzct-login
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

## 代码规范

### 代码格式化

项目使用 **Black** 进行代码格式化：

```bash
black .
```

### 导入排序

使用 **isort** 进行导入排序：

```bash
isort .
```

### 代码检查

使用 **Ruff** 进行代码检查：

```bash
ruff check .
```

### 类型检查

使用 **MyPy** 进行类型检查：

```bash
mypy .
```

## 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行带覆盖率的测试

```bash
pytest tests/ -v --cov=. --cov-report=html
```

### 运行特定测试

```bash
pytest tests/test_system_core.py -v
pytest tests/test_business.py -v
```

## 项目结构

```
qzct-login/
├── main.py              # 程序入口
├── business.py          # 业务逻辑
├── system_core.py       # 系统核心
├── infrastructure.py    # 基础设施
├── concurrency.py       # 并发框架
├── constants.py         # 常量配置
├── exceptions.py        # 自定义异常
├── gui/                 # GUI 模块
│   ├── main_window.py
│   ├── style_manager.py
│   ├── dialogs/
│   └── widgets/
├── utils/               # 工具模块
│   ├── logger.py
│   └── version.py
└── tests/               # 测试模块
    ├── conftest.py
    ├── test_system_core.py
    ├── test_business.py
    ├── test_infrastructure.py
    └── test_concurrency.py
```

## 提交代码

### 提交前检查

1. 运行代码格式化：`black . && isort .`
2. 运行代码检查：`ruff check .`
3. 运行类型检查：`mypy .`
4. 运行测试：`pytest tests/ -v`

### 提交信息规范

使用约定式提交格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**：
- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**：

```
feat(wifi): 添加 WiFi 信号强度显示

- 在状态栏显示当前 WiFi 信号强度
- 添加信号强度图标

Closes #123
```

## 添加新功能

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码

遵循项目代码规范，添加必要的类型注解和文档字符串。

### 3. 编写测试

为新功能编写单元测试：

```python
# tests/test_new_feature.py
import pytest

def test_new_feature():
    result = new_function()
    assert result == expected_value
```

### 4. 更新文档

如果需要，更新 README.md 或相关文档。

### 5. 提交 PR

推送分支并创建 Pull Request。

## 调试技巧

### 启用调试日志

```python
from infrastructure import init_logger

init_logger(level=0)  # DEBUG 级别
```

### 使用断点

```python
import pdb; pdb.set_trace()
# 或
breakpoint()
```

### 查看 GUI 日志

程序运行时，日志会显示在界面底部的日志区域。

## 常见问题

### Q: 如何添加新的 ISP 支持？

在 `system_core.py` 中的 `ISP_MAPPING` 添加新条目：

```python
ISP_MAPPING = {
    "new_isp": "@new_isp",
    # ...
}
```

### Q: 如何修改登录服务器地址？

修改 `constants.py` 中的 `CAMPUS_LOGIN_CONFIG`：

```python
CAMPUS_LOGIN_CONFIG = {
    "login_url": "http://your-server:port/path",
    # ...
}
```

### Q: 如何添加新的日期规则？

在 `system_core.py` 的 `should_work_today()` 函数中添加新逻辑。

## 发布流程

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 创建 Git Tag：`git tag v1.x.x`
4. 推送 Tag：`git push origin v1.x.x`
5. GitHub Actions 自动构建发布
