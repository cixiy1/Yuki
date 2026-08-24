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

META_NAMES = {"list_packages", "load_package", "unload_package"}

META_TOOLS = [
    {
        "name": "list_packages",
        "description": "列出当前可用的外置工具包，包括包内工具和提示词",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "load_package",
        "description": "加载一个外置工具包，之后它的工具和提示词才进入上下文",
        "parameters": {
            "type": "object",
            "required": ["package_id"],
            "properties": {
                "package_id": {
                    "type": "string",
                    "description": "外置工具包的 id",
                }
            },
        },
    },
    {
        "name": "unload_package",
        "description": "卸载一个外置工具包，释放上下文空间",
        "parameters": {
            "type": "object",
            "required": ["package_id"],
            "properties": {
                "package_id": {
                    "type": "string",
                    "description": "外置工具包的 id",
                }
            },
        },
    },
]


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

    外置包默认只被发现不激活，模型通过元工具按需加载：
    - list_packages：查看可用包
    - load_package / unload_package：加载 / 卸载包
    """

    def __init__(
        self,
        packages_dir: Optional[PathLike] = None,
        available: Optional[list[str]] = None,
        preload: Optional[list[str]] = None,
    ):
        self._tools: dict[str, dict[str, Any]] = {}
        self._prompts: dict[str, dict[str, Any]] = {}
        self._packages: dict[str, dict[str, Any]] = {}
        self._active_packages: set[str] = set()
        self._modules: dict[str, Any] = {}
        self.load_builtin()
        if packages_dir is not None:
            self.scan_packages(Path(packages_dir), available=available)
        for package_id in preload or []:
            print(self.activate_package(package_id))

    @property
    def tools(self) -> list[dict[str, Any]]:
        schemas = [to_function_schema(tool) for tool in self._tools.values()]
        schemas += [to_function_schema(tool) for tool in META_TOOLS]
        return schemas

    @property
    def prompts(self) -> list[dict[str, Any]]:
        return list(self._prompts.values())

    @property
    def available_packages(self) -> list[dict[str, Any]]:
        return [
            {
                "id": package_id,
                "name": package["name"],
                "description": package["description"],
                "tools": [tool["name"] for tool in package["tools"]],
                "prompts": [prompt["name"] for prompt in package["prompts"]],
                "loaded": package_id in self._active_packages,
            }
            for package_id, package in self._packages.items()
        ]

    @property
    def active_packages(self) -> list[str]:
        return sorted(self._active_packages)

    def load_builtin(self) -> None:
        for tool in BUILTIN_TOOLS:
            self.register_tool(tool)

    def scan_packages(self, packages_dir: Path, available: Optional[list[str]] = None) -> None:
        if not packages_dir.is_dir():
            print(f"外置工具包目录不存在：{packages_dir}")
            return

        packages: dict[str, dict[str, Any]] = {}
        for package_dir in discover_packages(packages_dir):
            try:
                package = load_package(package_dir)
                packages[package["id"]] = package
                print(f"发现外置工具包：{package['id']}")
            except Exception as err:
                print(f"跳过外置工具包 {package_dir.name}：{err}")

        if available is not None:
            allowed = set(available)
            packages = {
                package_id: package
                for package_id, package in packages.items()
                if package_id in allowed
            }
        self._packages = packages
        if packages:
            print(f"可用外置工具包：{'、'.join(packages)}")
        else:
            print("可用外置工具包：无")

    def activate_package(self, package_id: str) -> str:
        if package_id in self._active_packages:
            return f"{package_id} 已加载"
        package = self._packages.get(package_id)
        if package is None:
            return f"未找到可用工具包：{package_id}"

        for tool in package["tools"]:
            if tool["name"] in self._tools or tool["name"] in META_NAMES:
                return f"加载 {package_id} 失败：工具名冲突 {tool['name']}"
        for prompt in package["prompts"]:
            if prompt["name"] in self._prompts:
                return f"加载 {package_id} 失败：提示词名冲突 {prompt['name']}"

        for tool in package["tools"]:
            self.register_tool(tool)
        for prompt in package["prompts"]:
            self.register_prompt(prompt)
        self._active_packages.add(package_id)

        tool_names = "、".join(tool["name"] for tool in package["tools"]) or "无"
        prompt_names = "、".join(prompt["name"] for prompt in package["prompts"]) or "无"
        return f"已加载 {package_id}：工具 {tool_names}；提示词 {prompt_names}"

    def deactivate_package(self, package_id: str) -> str:
        if package_id not in self._active_packages:
            return f"{package_id} 未加载"
        package = self._packages[package_id]
        for tool in package["tools"]:
            self._tools.pop(tool["name"], None)
        for prompt in package["prompts"]:
            self._prompts.pop(prompt["name"], None)
        self._active_packages.remove(package_id)
        return f"已卸载 {package_id}"

    def register_tool(self, tool: dict[str, Any]) -> None:
        name = tool["name"]
        if name in META_NAMES:
            raise ValueError(f"工具名 {name} 是保留名")
        if name in self._tools:
            raise ValueError(f"工具名冲突：{name}")
        self._tools[name] = tool

    def register_prompt(self, prompt: dict[str, Any]) -> None:
        name = prompt["name"]
        if name in self._prompts:
            raise ValueError(f"提示词名冲突：{name}")
        self._prompts[name] = prompt

    def system_prompt(self) -> str:
        """把已加载外置包的提示词拼成系统消息。"""
        parts = []
        for prompt in self._prompts.values():
            parts.append(f"[{prompt['name']}]\n{prompt['content'].strip()}")
        return "\n\n".join(parts)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if name in META_NAMES:
            return self._execute_meta(name, arguments)

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

    def _execute_meta(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "list_packages":
            return self._list_packages_text()
        if name == "load_package":
            return self.activate_package(str(arguments.get("package_id", "")))
        if name == "unload_package":
            return self.deactivate_package(str(arguments.get("package_id", "")))
        return f"Unknown meta tool: {name}"

    def _list_packages_text(self) -> str:
        lines = []
        for package in self.available_packages:
            state = "已加载" if package["loaded"] else "未加载"
            tools = "、".join(package["tools"]) or "无"
            prompts = "、".join(package["prompts"]) or "无"
            lines.append(
                f"{package['id']}：{package['description']}（工具：{tools}；提示词：{prompts}；状态：{state}）"
            )
        return "\n".join(lines) or "暂无可用工具包"

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
