"""内置工具契约。"""

from yuki_kernel.skills import ToolRegistry


def test_environment_info_available():
    registry = ToolRegistry(None)
    names = [tool["function"]["name"] for tool in registry.tools]
    prompt_names = [prompt["name"] for prompt in registry.prompts]

    assert "get_environment_info" in names
    assert "search_memory" in names
    assert "environment_guide" in prompt_names
    assert "yuki_identity" not in prompt_names
    assert "get_name_guide" not in prompt_names

    content = registry.execute("get_environment_info", {})
    assert "操作系统" in content
    assert "Python" in content


def test_scan_packages_returns_data_without_printing(weather_package, capsys):
    registry = ToolRegistry(None)

    scan = registry.scan_packages(weather_package)

    assert "weather" in scan.packages
    assert scan.skipped == []
    assert capsys.readouterr().out == ""


def test_scan_packages_missing_dir(tmp_path, capsys):
    registry = ToolRegistry(None)

    scan = registry.scan_packages(tmp_path / "nope")

    assert scan.packages == {}
    assert scan.skipped == [(str(tmp_path / "nope"), "目录不存在")]
    assert capsys.readouterr().out == ""


def test_preload_updates_available_packages_without_printing(weather_package, capsys):
    registry = ToolRegistry(weather_package, preload=["weather"])

    loaded = [package for package in registry.available_packages if package["loaded"]]
    assert [package["id"] for package in loaded] == ["weather"]
    assert capsys.readouterr().out == ""
