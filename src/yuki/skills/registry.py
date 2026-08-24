"""工具注册表：统一内置工具与外置工具包的 schema 与执行。"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Union

from .builtin import BUILTIN_TOOLS
from .external import discover_packages, load_package

PathLike = Union[str, Path]


def to_function_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """把内部工具定义转成 OpenAI 兼容的函数 schema。"""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        },
    }


class ToolRegistry:
    """内置工具 + 外置工具包的注册表。

    - 内置工具：直接注册 Python handler。
    - 外置工具包：从 packages 目录加载 manifest，entry 支持 python 模块和命令。
    """

    def __init__(self, packages_dir: Optional[PathLike] = None):
        self._tools: dict[str, dict[str, Any]] = {}
        self._prompts: dict[str, dict[str, Any]] = {}
        self._modules: dict[str, Any] = {}
        self.load_builtin()
        if packages_dir is not None:
            self.load_packages(Path(packages_dir))

    @property
    def tools(self) -> list[dict[str, Any]]:
        return [to_function_schema(tool) for tool in self._tools.values()]

    @property
    def prompts(self) -> list[dict[str, Any]]:
        return list(self._prompts.values())

    def load_builtin(self) -> None:
        for tool in BUILTIN_TOOLS:
            self.register_tool(tool)

    def register_tool(self, tool: dict[str, Any]) -> None:
        name = tool["name"]
        if name in self._tools:
            raise ValueError(f"工具名冲突：{name}")
        self._tools[name] = tool

    def register_prompt(self, prompt: dict[str, Any]) -> None:
        name = prompt["name"]
        if name in self._prompts:
            raise ValueError(f"提示词名冲突：{name}")
        self._prompts[name] = prompt

    def load_packages(self, packages_dir: Path) -> None:
        if not packages_dir.is_dir():
            print(f"外置工具包目录不存在：{packages_dir}")
            return
        for package_dir in discover_packages(packages_dir):
            try:
                package = load_package(package_dir)
                for tool in package["tools"]:
                    self.register_tool(tool)
                for prompt in package["prompts"]:
                    self.register_prompt(prompt)
                print(f"已加载外置工具包：{package['id']}")
            except Exception as err:
                print(f"跳过外置工具包 {package_dir.name}：{err}")

    def system_prompt(self) -> str:
        """把外置包的提示词拼成系统消息。"""
        parts = []
        for prompt in self._prompts.values():
            parts.append(f"[{prompt['name']}]\n{prompt['content'].strip()}")
        return "\n\n".join(parts)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"
        if "entry" not in tool:
            return str(tool["handler"](**arguments))

        entry = tool["entry"]
        if entry["type"] == "python":
            return self._execute_python(tool, arguments)
        if entry["type"] == "command":
            return self._execute_command(tool, arguments)
        return f"Unknown entry type: {entry['type']}"

    def _execute_python(self, tool: dict[str, Any], arguments: dict[str, Any]) -> str:
        entry = tool["entry"]
        module_path = Path(tool["package_dir"]) / entry["module"]
        module_name = "_".join(
            ["_yuki_pkg", tool["package"], entry["module"].removesuffix(".py")]
        ).replace("/", "_").replace("\\", "_")
        module = self._modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                return f"无法加载模块：{module_path}"
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self._modules[module_name] = module

        handler = getattr(module, entry["handler"], None)
        if handler is None:
            return f"模块 {module_path} 中找不到函数：{entry['handler']}"
        return str(handler(**arguments))

    def _execute_command(self, tool: dict[str, Any], arguments: dict[str, Any]) -> str:
        entry = tool["entry"]
        command = [part.replace("{python}", sys.executable) for part in entry["command"]]
        try:
            result = subprocess.run(
                command,
                cwd=tool["package_dir"],
                input=json.dumps(arguments, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return "工具执行超时"
        if result.returncode != 0:
            return f"工具执行失败：{result.stderr.strip() or result.stdout.strip()}"
        return result.stdout.strip()
