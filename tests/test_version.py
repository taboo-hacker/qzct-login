"""
utils/version.py 补充测试

覆盖 get_project_version 的所有路径分支。
"""

import sys
from unittest.mock import patch


class TestGetProjectVersion:
    """get_project_version 测试"""

    def teardown_method(self) -> None:
        """每个测试后重置缓存"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

    def test_returns_version_from_pyproject(self):
        """正常读取 pyproject.toml 中的版本号"""
        import utils.version as version_mod

        version_mod._cached_project_version = None
        version = version_mod.get_project_version()
        # 确保返回非空字符串
        assert isinstance(version, str)
        assert len(version) > 0
        assert version != "1.0.0"  # 实际版本不是默认值

    def test_uses_cache_on_second_call(self):
        """第二次调用使用缓存"""
        import utils.version as version_mod

        version_mod._cached_project_version = None
        v1 = version_mod.get_project_version()
        v2 = version_mod.get_project_version()
        assert v1 == v2

    def test_returns_cached_value_directly(self):
        """已有缓存时直接返回"""
        import utils.version as version_mod

        version_mod._cached_project_version = "9.9.9"
        assert version_mod.get_project_version() == "9.9.9"

    def test_returns_default_when_pyproject_not_found(self, tmp_path):
        """pyproject.toml 不存在时返回默认版本"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        # 模拟在一个没有 pyproject.toml 的目录
        with (
            patch.object(version_mod.os.path, "exists", return_value=False),
        ):
            result = version_mod.get_project_version()
            assert result == "1.0.0"

    def test_frozen_app_path(self):
        """frozen 应用从 sys.executable 目录查找"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        original_frozen = getattr(sys, "frozen", False)
        original_executable = sys.executable
        try:
            sys.frozen = True
            sys.executable = "/fake/path/app.exe"

            with patch.object(version_mod.os.path, "exists", return_value=False):
                result = version_mod.get_project_version()
                assert result == "1.0.0"
        finally:
            sys.frozen = original_frozen
            sys.executable = original_executable

    def test_exception_returns_default(self):
        """发生异常时返回默认版本"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        with patch.object(version_mod.os.path, "dirname", side_effect=RuntimeError("boom")):
            result = version_mod.get_project_version()
            assert result == "1.0.0"
