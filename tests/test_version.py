"""
utils/version.py 补充测试

覆盖 get_project_version 的所有路径分支：
pyproject.toml 正常读取、缓存命中/未命中、文件缺失回退默认值 1.0.0、
PyInstaller frozen（含 onefile _MEIPASS）模式，以及异常兜底。
通过 patch os.path.exists / 修改 sys.frozen 等属性模拟各运行环境。
"""

import sys
from unittest.mock import patch


class TestGetProjectVersion:
    """get_project_version 测试：按版本来源（文件/缓存/frozen/异常）分组。"""

    def teardown_method(self) -> None:
        """每个测试后清空模块级缓存 _cached_project_version，避免用例间缓存串扰。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

    def test_returns_version_from_pyproject(self):
        """正常环境下应从项目 pyproject.toml 读取到真实版本号而非默认值。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None
        version = version_mod.get_project_version()
        # 确保返回非空字符串
        assert isinstance(version, str)
        assert len(version) > 0
        assert version != "1.0.0"  # 实际版本不是默认值

    def test_uses_cache_on_second_call(self):
        """第二次调用应命中缓存并返回与首次一致的结果。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None
        v1 = version_mod.get_project_version()
        v2 = version_mod.get_project_version()
        assert v1 == v2

    def test_returns_cached_value_directly(self):
        """缓存已有值（9.9.9）时直接返回缓存，不重新解析文件。"""
        import utils.version as version_mod

        version_mod._cached_project_version = "9.9.9"
        assert version_mod.get_project_version() == "9.9.9"

    def test_returns_default_when_pyproject_not_found(self, tmp_path):
        """pyproject.toml 不存在时应回退返回默认版本 1.0.0。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        # 模拟在一个没有 pyproject.toml 的目录
        with (
            patch.object(version_mod.os.path, "exists", return_value=False),
        ):
            result = version_mod.get_project_version()
            assert result == "1.0.0"

    def test_frozen_app_path(self):
        """frozen 应用应改从 sys.executable 所在目录查找，找不到时返回默认值。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        # 临时伪装成 PyInstaller 打包环境，finally 中恢复避免污染其他测试
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

    def test_frozen_app_reads_meipass_pyproject(self, tmp_path):
        """frozen onefile 模式应从 _MEIPASS 解包目录读取打包的 pyproject.toml（回归 M7）。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        # 构造带版本号 4.5.6 的临时 pyproject.toml 并挂到 sys._MEIPASS
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "x"\nversion = "4.5.6"\n', encoding="utf-8")

        original_frozen = getattr(sys, "frozen", False)
        original_meipass = getattr(sys, "_MEIPASS", None)
        original_executable = sys.executable
        try:
            sys.frozen = True
            sys._MEIPASS = str(tmp_path)
            sys.executable = "/fake/path/app.exe"
            result = version_mod.get_project_version()
            assert result == "4.5.6"
        finally:
            # 原本不存在 _MEIPASS 属性时需删除，而不是留一个假值
            sys.frozen = original_frozen
            sys.executable = original_executable
            if original_meipass is None:
                del sys._MEIPASS
            else:
                sys._MEIPASS = original_meipass

    def test_exception_returns_default(self):
        """版本探测过程抛出异常时应兜底返回默认版本 1.0.0。"""
        import utils.version as version_mod

        version_mod._cached_project_version = None

        with patch.object(version_mod.os.path, "dirname", side_effect=RuntimeError("boom")):
            result = version_mod.get_project_version()
            assert result == "1.0.0"
