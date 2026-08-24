from typing import Any


class Skills:
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "get_temperature",
                "description": "查询指定城市气温",
                "parameters": {
                    "type": "object",
                    "required": ["city"],
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "(城市)city参数必须用英文名称，例 New York、London"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_name",
                "description": "查询某个人的家庭所在城市",
                "parameters": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string",
                        }
                    }
                }
            }
        }
    ]

    @staticmethod
    def get_temperature(city: str):
        temp_dict = {
            "New York": "22°C",
            "London": "15°C",
            "Tokyo": "18°C"
        }
        return temp_dict.get(city, "Unknown city")

    @staticmethod
    def get_name(name: str):
        name_dict = {
            "张三": "纽约",
        }
        return name_dict.get(name, "Unknown name")
