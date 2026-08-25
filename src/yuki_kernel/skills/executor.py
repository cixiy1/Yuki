"""工具执行器：python 模块与命令入口的加载和执行。"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, cast

from .types import Tool, ToolEntry


def require_entry(tool: Tool) -> ToolEntry:
    entry = tool.get("entry")
    if entry is None:
        raise ValueError("缺少执行入口")
    return entry


def run_handler(handler: Any, arguments: dict[str, Any]) -> str:
    if not callable(handler):
        return "handler 不可调用"
    try:
        result = cast(Callable[..., str], handler)(**arguments)
    except Exception as err:
        return f"工具执行失败：{err}"
    return f"{result}"


class ToolExecutor:
    def __init__(self):
        self.modules: dict[str, ModuleType] = {}
        self.instances: dict[str, Any] = {}

    def execute_python(self, tool: Tool, arguments: dict[str, Any]) -> str:
        try:
            entry = require_entry(tool)
        except ValueError as err:
            return str(err)
        module = entry["module"]
        module_path = Path(tool["package_dir"]) / module
        module_name = "_".join(
            ["_yuki_pkg", tool.get("package", "?"), module.removesuffix(".py")]
        ).replace("/", "_").replace("\\", "_")
        loaded = self.modules.get(module_name)
        if loaded is None:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                return f"无法加载模块：{module_path}"
            loader = spec.loader
            if loader is None:
                return f"无法加载模块：{module_path}"
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = loaded
            loader.exec_module(loaded)
            self.modules[module_name] = loaded

        handler = getattr(loaded, entry["handler"])
        if isinstance(handler, type):
            instance_key = f"{module_name}.{entry['handler']}"
            instance = self.instances.get(instance_key)
            if instance is None:
                try:
                    instance = handler()
                except Exception as err:
                    return f"工具执行失败：{err}"
                self.instances[instance_key] = instance
            method = entry.get("method", "run")
            return run_handler(getattr(instance, method, None), arguments)
        return run_handler(handler, arguments)

    @staticmethod
    def execute_command(tool: Tool, arguments: dict[str, Any]) -> str:
        try:
            entry = require_entry(tool)
        except ValueError as err:
            return str(err)
        command = [
            part.replace("{python}", sys.executable)
            for part in entry["command"]
        ]
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
        except Exception as err:
            return f"工具执行失败：{err}"
        if result.returncode != 0:
            return f"工具执行失败：{result.stderr.strip() or result.stdout.strip()}"
        return result.stdout.strip()
