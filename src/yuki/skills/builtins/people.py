"""内置工具实现。"""


def get_name(name: str) -> str:
    name_dict = {
        "张三": "纽约",
    }
    return name_dict.get(name, "Unknown name")
