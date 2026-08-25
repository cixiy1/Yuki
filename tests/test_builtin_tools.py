"""内置工具契约。"""

from yuki.skills import ToolRegistry


def test_environment_info_available():
    registry = ToolRegistry(None)
    names = [tool["function"]["name"] for tool in registry.tools]
    prompt_names = [prompt["name"] for prompt in registry.prompts]

    assert "get_environment_info" in names
    assert "environment_guide" in prompt_names
    assert "get_name_guide" not in prompt_names

    content = registry.execute("get_environment_info", {})
    assert "操作系统" in content
    assert "Python" in content
