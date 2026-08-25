"""Provider 抽象与注册口：具体提供商由外部实现并注册。"""

from typing import Callable

from ..config import Settings
from .base import ChatChunk, Provider

__all__ = ["ChatChunk", "Provider", "register_provider", "create_provider"]

_PROVIDERS: dict[str, Callable[[str, Settings], Provider]] = {}


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
