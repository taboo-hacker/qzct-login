import os
import sys
from infrastructure import warning, debug, error

_cached_project_version = None

def get_project_version():
    """
    从 pyproject.toml 中读取项目版本号
    
    功能说明：
        - 定位项目根目录下的 pyproject.toml 文件
        - 解析文件内容并提取 version 字段
        - 使用缓存机制避免重复读取
        - 如果读取失败，返回默认版本号 "1.0.0"
    
    参数：
        无
    
    返回值：
        str: 项目版本号
    
    异常：
        无（异常会被捕获并返回默认值）
    """
    global _cached_project_version
    if _cached_project_version is not None:
        return _cached_project_version
    
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        pyproject_path = os.path.join(base_dir, 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            parent_dir = os.path.dirname(base_dir)
            pyproject_path = os.path.join(parent_dir, 'pyproject.toml')
        
        if not os.path.exists(pyproject_path):
            warning("main", "找不到 pyproject.toml 文件，使用默认版本号")
            _cached_project_version = "1.0.0"
            return _cached_project_version
        
        try:
            import tomllib
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    data = tomli.load(f)
            except ImportError:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('version'):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        _cached_project_version = version
                        debug("main", f"从 pyproject.toml 读取到版本号: {version}")
                        return version
                _cached_project_version = "1.0.0"
                return _cached_project_version
        
        version = data.get('project', {}).get('version', '1.0.0')
        _cached_project_version = version
        debug("main", f"从 pyproject.toml 读取到版本号: {version}")
        return version
    
    except Exception as e:
        error("main", f"读取 pyproject.toml 失败: {e}", exc_info=True)
        _cached_project_version = "1.0.0"
        return _cached_project_version
