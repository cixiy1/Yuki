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

# 示例：工具函数 + 使用说明提示词（未启用，避免内置提示词常驻占上下文）
# 1. 在 builtins/prompts/ 下创建 get_name_guide.md
# 2. 在 BUILTIN_PROMPTS 注册：
# {
#     "name": "get_name_guide",
#     "description": "get_name 的使用注意事项",
#     "path": "builtins/prompts/get_name_guide.md",
# }

BUILTIN_PROMPTS = [
    {
        "name": "builtin_identity",
        "description": "Yuki 的基础身份说明",
        "path": "builtins/prompts/identity.md",
    },
]
