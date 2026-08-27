"""工具执行器：python 与 command 入口都经子进程执行，统一套一层 OS 级沙箱。"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from .sandbox import BasicSandbox, RunResult, Sandbox
from .types import Tool, ToolEntry

# python 工具在子进程内的引导脚本：加载模块、取 handler、调用、打印结果；
# 异常统一转成「工具执行失败：<err>」输出，保证调用方拿到稳定格式。
_PY_BOOTSTRAP = (
    "import importlib.util, json, sys, traceback\n"
    "try:\n"
    "    path, handler, method = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'run')\n"
    "    spec = importlib.util.spec_from_file_location('__yuki_tool__', path)\n"
    "    mod = importlib.util.module_from_spec(spec)\n"
    "    spec.loader.exec_module(mod)\n"
    "    obj = getattr(mod, handler)\n"
    "    if isinstance(obj, type):\n"
    "        obj = obj()\n"
    "    args = json.loads(sys.stdin.read() or '{}')\n"
    "    result = obj(**args) if method == 'run' else getattr(obj, method)(**args)\n"
    "    print(result)\n"
    "except Exception as err:\n"
    "    print('工具执行失败：' + str(err))\n"
)

_TIMEOUT = 30


def require_entry(tool: Tool) -> ToolEntry:
    entry = tool.get("entry")
    if entry is None:
        raise ValueError("缺少执行入口")
    return entry


def run_handler(handler: Any, arguments: dict[str, Any]) -> str:
    if not callable(handler):
        return "handler 不可调用"
    try:
        result = handler(**arguments)
    except Exception as err:  # noqa: BLE001 - 工具异常需回喂模型而非崩溃
        return f"工具执行失败：{err}"
    return f"{result}"


class ToolExecutor:
    def __init__(self, sandbox: Optional[Sandbox] = None):
        self.sandbox = sandbox or BasicSandbox()

    def _is_builtin(self, tool: Tool) -> bool:
        return tool.get("package") == "builtin"

    def _sandbox_run(self, tool: Tool, command: list[str], payload: str) -> str:
        """内置工具继承宿主环境与工作目录（内核自带、可信）；
        外置包工具按沙箱策略执行（清空环境、cwd 为包目录）。"""
        if self._is_builtin(tool):
            return self._to_result(
                self.sandbox.run(
                    command,
                    Path.cwd(),
                    payload,
                    timeout=_TIMEOUT,
                    env=dict(os.environ),
                )
            )
        return self._to_result(
            self.sandbox.run(command, Path(tool["package_dir"]), payload, timeout=_TIMEOUT)
        )

    def _to_result(self, run: RunResult) -> str:
        # 子进程异常已在引导脚本里转成「工具执行失败：...」打印到 stdout，
        # 故优先用 stdout；仅在 stdout 为空时回退 stderr。
        if run.stdout.strip():
            return run.stdout.strip()
        if run.returncode != 0:
            return f"工具执行失败：{run.stderr.strip()}"
        return run.stdout.strip()

    def execute_python(self, tool: Tool, arguments: dict[str, Any]) -> str:
        try:
            entry = require_entry(tool)
        except ValueError as err:
            return str(err)
        if entry.get("type") != "python":
            return f"入口类型不是 python：{entry.get('type')}"
        module = entry.get("module")
        handler = entry.get("handler")
        if not module or not handler:
            return "python 入口需要 module 和 handler"
        module_path = Path(tool["package_dir"]) / module
        if not module_path.is_file():
            return f"无法加载模块：{module_path}"
        command = [
            sys.executable,
            "-c",
            _PY_BOOTSTRAP,
            str(module_path),
            handler,
            entry.get("method", "run"),
        ]
        payload = json.dumps(arguments, ensure_ascii=False)
        return self._sandbox_run(tool, command, payload)

    def execute_command(self, tool: Tool, arguments: dict[str, Any]) -> str:
        try:
            entry = require_entry(tool)
        except ValueError as err:
            return str(err)
        if entry.get("type") != "command":
            return f"入口类型不是 command：{entry.get('type')}"
        command = [part.replace("{python}", sys.executable) for part in entry.get("command", [])]
        if not command:
            return "command 入口需要非空命令列表"
        payload = json.dumps(arguments, ensure_ascii=False)
        return self._sandbox_run(tool, command, payload)
