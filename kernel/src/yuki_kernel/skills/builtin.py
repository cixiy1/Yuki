"""内置工具注册表：只声明内置工具和提示词，具体实现放在 builtins/ 下。"""

from .types import Tool

BUILTIN_TOOLS: list[Tool] = [
    {
        "name": "get_environment_info",
        "description": "获取当前操作系统、Python 版本、工作目录等环境信息；上下文已有环境信息时不要重复调用",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "entry": {
            "type": "python",
            "module": "builtins/environment.py",
            "handler": "get_environment_info",
        },
    },{
        "name": "terminal",
        "description": "在终端/terminal 中执行命令并返回标准输出与标准错误；适配各类 POSIX 终端。默认在降权沙箱中运行（无特权用户），可信环境下可传 sandbox: false 关闭降权。",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "要执行的命令字符串，经 /bin/sh -c 运行",
                },
                "sandbox": {
                    "type": "boolean",
                    "description": "是否降权执行，默认 true；设为 false 仅在可信环境关闭",
                    "default": True,
                },
            },
            "required": ["cmd"],
        },
        "entry": {
            "type": "python",
            "module": "builtins/terminal.py",
            "handler": "run_terminal",
        },
    },
]

BUILTIN_PROMPTS = [
    {
        "name": "environment_guide",
        "description": "命令生成前的环境信息使用提示",
        "path": "builtins/prompts/environment_guide.md",
    },
]
