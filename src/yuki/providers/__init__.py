"""Yuki 示例 provider 组装入口。"""

from yuki_kernel.providers import register_provider

from .api import ApiProvider
from .ollama import OllamaProvider

__all__ = ["ApiProvider", "OllamaProvider", "register_yuki_providers"]


def register_yuki_providers() -> None:
    register_provider("ollama", OllamaProvider)
    register_provider("api", ApiProvider)
