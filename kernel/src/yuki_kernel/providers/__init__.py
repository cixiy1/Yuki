"""Provider 抽象、内置厂商与注册口。"""

from typing import Callable

from ..config import Settings
from .anthropic import AnthropicProvider
from .base import ChatChunk, Provider
from .openai import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "ChatChunk",
    "OpenAIProvider",
    "Provider",
    "register_provider",
    "create_provider",
]

_PROVIDERS: dict[str, Callable[[str, Settings], Provider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def register_provider(name: str, factory: Callable[[str, Settings], Provider]) -> None:
    _PROVIDERS[name] = factory


def create_provider(
    name: str,
    model: str,
    settings: Settings,
) -> Provider:
    factory = _PROVIDERS.get(name)
    if factory is None:
        raise ValueError(f"未注册的 provider：{name}，可选 {list(_PROVIDERS)}")
    return factory(model, settings)
