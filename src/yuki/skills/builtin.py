"""内置工具注册表：只声明内置工具和提示词，具体实现放在 builtins/ 下。"""

from .types import Tool

BUILTIN_TOOLS: list[Tool] = [
    {
        "name": "get_environment_info",
        "description": "获取当前操作系统、Python 版本、工作目录等环境信息，生成命令前先调用",
        "parameters": {
            "type": "object",
            "properties": {},
        },
        "entry": {
            "type": "python",
            "module": "builtins/environment.py",
            "handler": "get_environment_info",
        },
    },
]

BUILTIN_PROMPTS = [
    {
        "name": "builtin_identity",
        "description": "Yuki 的基础身份说明",
        "path": "builtins/prompts/identity.md",
    },
    {
        "name": "environment_guide",
        "description": "命令生成前的环境信息使用提示",
        "path": "builtins/prompts/environment_guide.md",
    },
]
