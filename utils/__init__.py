"""
工具模块包

提供与业务无关的通用工具：
    - version.py         版本号读取（pyproject.toml 单一数据源）
    - logger.py          Loguru 底层配置（sink / 轮转 / 权限）
    - single_instance.py 单实例控制（QLocalServer 命名管道）
"""
