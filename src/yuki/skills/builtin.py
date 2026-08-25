"""内置工具注册表：只声明内置工具和提示词，具体实现放在 builtins/ 下。"""

BUILTIN_TOOLS = [
    {
        "name": "get_name",
        "description": "查询某个人的家庭所在城市",
        "parameters": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                }
            },
        },
        "entry": {
            "type": "python",
            "module": "builtins/people.py",
            "handler": "get_name",
        },
    },
]

BUILTIN_PROMPTS = [
    {
        "name": "builtin_identity",
        "description": "Yuki 的基础身份说明",
        "path": "builtins/prompts/identity.md",
    },
]
