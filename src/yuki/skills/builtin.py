"""内置工具：随代码分发，直接注册为 Python handler。"""

from typing import Any


def get_temperature(city: str) -> str:
    temp_dict = {
        "New York": "22°C",
        "London": "15°C",
        "Tokyo": "18°C",
    }
    return temp_dict.get(city, "Unknown city")


def get_name(name: str) -> str:
    name_dict = {
        "张三": "纽约",
    }
    return name_dict.get(name, "Unknown name")


BUILTIN_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_temperature",
        "description": "查询指定城市气温",
        "parameters": {
            "type": "object",
            "required": ["city"],
            "properties": {
                "city": {
                    "type": "string",
                    "description": "(城市)city参数必须用英文名称，例 New York、London",
                }
            },
        },
        "handler": get_temperature,
    },
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
        "handler": get_name,
    },
]
